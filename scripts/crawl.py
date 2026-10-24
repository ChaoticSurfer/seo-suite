#!/usr/bin/env python3
"""Crawl a site breadth-first (same host, obeying Googlebot's robots.txt rules) and report site-wide issues.

Usage:
  crawl.py https://example.com --max-pages 300 --csv pages.csv
  crawl.py https://example.com --sitemap-urls urls.txt     # from sitemap_check.py --urls-out; enables orphan detection
Outputs JSON: totals, site-level findings, per-page finding counts, and the worst pages.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from page_audit import audit_page
from robots_check import group_for, is_allowed, parse_robots
from schema_rules import validate_json_ld
from seo_lib import (
    SEVERITY_ORDER, USER_AGENT, Finding, PageFacts, extract_page, fetch, is_indexable, normalize_url, print_json, registrable_host,
    site_root, sort_findings,
)

ASSET_EXT = re.compile(r"\.(jpe?g|png|gif|webp|avif|svg|ico|pdf|zip|gz|mp4|webm|mp3|css|js|json|xml|txt|woff2?|ttf)$", re.I)
DEEP_CLICK_DEPTH = 3
NEAR_DUPLICATE_JACCARD = 0.9  # share of identical 5-word shingles; template boilerplate alone rarely reaches this
NEAR_DUPLICATE_MAX_PAGES = 600  # pairwise comparison cost grows with the square of the page count
SHINGLE_WORDS = 5


def crawlable(url: str, start_host: str, robots_group: dict | None, path_prefix: str = "/") -> bool:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or registrable_host(url) != start_host or ASSET_EXT.search(parts.path):
        return False
    if not (parts.path or "/").startswith(path_prefix):
        return False
    path = parts.path or "/"
    return is_allowed(robots_group, path + (f"?{parts.query}" if parts.query else ""))[0]


def crawl(start: str, max_pages: int, workers: int, delay: float, path_prefix: str = "/",
          user_agent: str = USER_AGENT) -> tuple[dict[str, PageFacts], dict[str, int], dict[str, set[str]], list[str]]:
    robots = fetch(urllib.parse.urljoin(site_root(start), "/robots.txt"))
    group = group_for(parse_robots(robots.text if robots.status == 200 else ""), "Googlebot")
    host = registrable_host(start)
    pages: dict[str, PageFacts] = {}
    depth = {start: 0}
    inlinks: dict[str, set[str]] = defaultdict(set)
    blocked: list[str] = []
    frontier = [start]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while frontier and len(pages) < max_pages:
            batch = frontier[: max_pages - len(pages)]
            frontier = []
            for url, facts in zip(batch, pool.map(lambda u: extract_page(fetch(u, user_agent=user_agent)), batch)):
                pages[url] = facts
                for link in facts.internal_links:
                    target = link["href"]
                    inlinks[target].add(url)
                    if target in depth:
                        continue
                    depth[target] = depth[url] + 1
                    if crawlable(target, host, group, path_prefix):
                        frontier.append(target)
                    elif registrable_host(target) == host and not ASSET_EXT.search(urllib.parse.urlsplit(target).path):
                        blocked.append(target)
            time.sleep(delay)
    return pages, depth, inlinks, blocked


def soft_404_probe(start: str) -> Finding | None:
    """Request a URL that cannot exist; anything but 404/410 means missing pages look like real ones."""
    probe = urllib.parse.urljoin(site_root(start), f"/seo-suite-404-probe-{int(time.time())}")
    result = fetch(probe)
    if result.status in (404, 410) or result.status is None:
        return None
    landing = result.final_url if result.redirect_chain else probe
    return Finding("soft-404", "high", f"A non-existent URL answered {result.status} (via {len(result.redirect_chain)} redirects) instead of 404/410", landing)


def _content_hash(facts: PageFacts) -> str:
    return hashlib.sha1(re.sub(r"\W+", " ", facts.visible_text.lower()).encode()).hexdigest()


def _shingles(text: str) -> set[int]:
    words = re.findall(r"\w+", text.lower())
    return {hash(" ".join(words[i:i + SHINGLE_WORDS])) for i in range(max(len(words) - SHINGLE_WORDS + 1, 0))}


def near_duplicates(pages: dict[str, PageFacts]) -> list[tuple[str, str, float]]:
    """Pairs of pages whose body text is ≥90% the same (Jaccard over 5-word shingles), exact copies excluded."""
    items = [(u, _shingles(f.visible_text)) for u, f in list(pages.items())[:NEAR_DUPLICATE_MAX_PAGES]]
    items = [(u, s) for u, s in items if len(s) >= 50]
    pairs = []
    for i, (url_a, a) in enumerate(items):
        for url_b, b in items[i + 1:]:
            if min(len(a), len(b)) / max(len(a), len(b)) < NEAR_DUPLICATE_JACCARD:
                continue  # sizes too different to reach the threshold
            score = len(a & b) / len(a | b)
            if NEAR_DUPLICATE_JACCARD <= score < 1.0:
                pairs.append((url_a, url_b, round(score, 3)))
    return sorted(pairs, key=lambda p: -p[2])


def site_findings(pages: dict[str, PageFacts], depth: dict[str, int], inlinks: dict[str, set[str]],
                  blocked: list[str], sitemap_urls: list[str]) -> list[Finding]:
    out: list[Finding] = []
    sample = lambda items: ", ".join(list(items)[:5])

    broken = {u: f.status for u, f in pages.items() if f.status is None or f.status >= 400}
    if broken:
        refs = [f"{u} [{s}] ← {next(iter(inlinks[u]), 'start')}" for u, s in list(broken.items())[:5]]
        out.append(Finding("broken-internal-links", "high", f"{len(broken)} internally linked URLs return errors", "; ".join(refs)))
    redirected = [u for u, f in pages.items() if f.redirect_chain]
    if redirected:
        out.append(Finding("links-to-redirects", "medium", f"{len(redirected)} internally linked URLs redirect; update links to the final URL", sample(redirected)))

    indexable = {u: f for u, f in pages.items() if is_indexable(f) and not f.redirect_chain}
    for label, key in (("titles", lambda f: f.title), ("meta descriptions", lambda f: f.meta_description),
                       ("body content", _content_hash)):
        groups = defaultdict(list)
        for url, facts in indexable.items():
            value = key(facts)
            if value:
                groups[value].append(url)
        dupes = [urls for urls in groups.values() if len(urls) > 1]
        if dupes:
            severity = "high" if label == "body content" else "medium"
            out.append(Finding(f"duplicate-{label.split()[-1]}", severity,
                               f"{sum(len(d) for d in dupes)} indexable pages share {label} in {len(dupes)} groups",
                               " | ".join(sample(d) for d in dupes[:3])))

    near = near_duplicates(indexable)
    if near:
        out.append(Finding("near-duplicate-content", "medium", f"{len(near)} pairs of indexable pages are ≥{NEAR_DUPLICATE_JACCARD:.0%} identical",
                           "; ".join(f"{a} ≈ {b} ({s})" for a, b, s in near[:5])))

    deep = [u for u in indexable if depth.get(u, 0) > DEEP_CLICK_DEPTH]
    if deep:
        out.append(Finding("deep-pages", "medium", f"{len(deep)} indexable pages are more than {DEEP_CLICK_DEPTH} clicks from the start URL", sample(deep)))
    single = [u for u in indexable if len(inlinks.get(u, ())) == 1 and depth.get(u, 0) > 0]
    if single:
        out.append(Finding("weakly-linked", "low", f"{len(single)} indexable pages have only one internal inlink", sample(single)))

    for url, facts in pages.items():
        target = facts.canonical
        if target and target in pages and target != url:
            tf = pages[target]
            if tf.status != 200 or tf.redirect_chain or not is_indexable(tf):
                out.append(Finding("canonical-to-bad-target", "high", f"{url} canonicalizes to a non-200 / redirecting / noindex URL", target))
        if not is_indexable(facts) and facts.status == 200 and len(inlinks.get(url, ())) >= 10:
            out.append(Finding("noindex-heavily-linked", "medium", f"noindex page has {len(inlinks[url])} internal inlinks", url))

    for url, facts in pages.items():
        for alt in facts.hreflang:
            other = pages.get(alt["href"])
            if other and other is not facts and not any(h["href"].rstrip("/") == url.rstrip("/") for h in other.hreflang):
                out.append(Finding("hreflang-no-return", "high", f"{alt['href']} does not link back to {url} (hreflang ignored without return links)"))
                break

    if blocked:
        out.append(Finding("robots-blocked-links", "info", f"{len(set(blocked))} internal URLs are linked but disallowed for Googlebot", sample(dict.fromkeys(blocked))))
    if sitemap_urls:
        linked = set(depth)
        orphans = [u for u in sitemap_urls if u not in linked]
        if orphans:
            out.append(Finding("orphan-pages", "medium", f"{len(orphans)} sitemap URLs were not reached through internal links (orphans, or beyond --max-pages)", sample(orphans)))
        missing = [u for u in indexable if u not in set(sitemap_urls)]
        if missing:
            out.append(Finding("not-in-sitemap", "low", f"{len(missing)} indexable crawled pages are missing from the sitemap", sample(missing)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("start")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.5, help="seconds to pause between crawl waves")
    ap.add_argument("--sitemap-urls", help="file with one sitemap URL per line (enables orphan checks)")
    ap.add_argument("--csv", help="write one row per crawled page to this CSV")
    ap.add_argument("--links-csv", help="write every internal link edge (source, target, anchor, rel) to this CSV")
    ap.add_argument("--path-prefix", default="/", help="only follow URLs under this path (crawl one section)")
    ap.add_argument("--user-agent", default=USER_AGENT, help="User-Agent header (e.g. to compare what bots are served)")
    args = ap.parse_args()

    pages, depth, inlinks, blocked = crawl(normalize_url(args.start), args.max_pages, args.workers, args.delay,
                                           args.path_prefix, args.user_agent)
    sitemap_urls = []
    if args.sitemap_urls:
        with open(args.sitemap_urls, encoding="utf-8") as fh:
            sitemap_urls = [normalize_url(line.strip()) for line in fh if line.strip()]

    per_page: dict[str, list[Finding]] = {u: audit_page(f) for u, f in pages.items()}
    counts = Counter((f.id, f.severity) for fs in per_page.values() for f in fs)
    examples = defaultdict(list)
    for url, fs in per_page.items():
        for f in fs:
            if len(examples[f.id]) < 3:
                examples[f.id].append(url)
    page_issue_summary = sorted(
        ({"id": i, "severity": s, "pages": n, "examples": examples[i]} for (i, s), n in counts.items()),
        key=lambda row: (SEVERITY_ORDER[row["severity"]], -row["pages"]),
    )
    worst = sorted(per_page.items(), key=lambda kv: sorted(SEVERITY_ORDER[f.severity] for f in kv[1])[:3] or [9])[:10]

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["url", "depth", "status", "final_url", "indexable", "title", "title_len", "description_len",
                             "h1_count", "canonical", "word_count", "inlinks", "internal_outlinks", "schema_types",
                             "download_ms", "issues"])
            for url, f in pages.items():
                types, _ = validate_json_ld(f.json_ld)
                writer.writerow([url, depth.get(url), f.status, f.final_url, is_indexable(f), f.title, len(f.title),
                                 len(f.meta_description), sum(1 for lvl, _ in f.headings if lvl == 1), f.canonical,
                                 f.word_count, len(inlinks.get(url, ())), len(f.internal_links), ";".join(sorted(set(types))),
                                 f.elapsed_ms, ";".join(sorted({x.id for x in per_page[url]}))])

    if args.links_csv:
        with open(args.links_csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["source", "target", "anchor", "rel"])
            for url, f in pages.items():
                for link in f.internal_links:
                    writer.writerow([url, link["href"], link["text"], link["rel"]])

    statuses = Counter(str(f.status) for f in pages.values())
    print_json({
        "start": args.start, "pages_crawled": len(pages), "hit_page_limit": len(pages) >= args.max_pages,
        "status_counts": dict(statuses), "indexable_pages": sum(1 for f in pages.values() if is_indexable(f)),
        "max_depth": max(depth.get(u, 0) for u in pages) if pages else 0,
        "site_findings": sort_findings(site_findings(pages, depth, inlinks, blocked, sitemap_urls)
                                       + [f for f in [soft_404_probe(args.start)] if f]),
        "page_issue_summary": page_issue_summary,
        "worst_pages": [{"url": u, "top_issues": [f.id for f in sort_findings(fs)[:5]]} for u, fs in worst],
        "csv": args.csv, "links_csv": args.links_csv,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
