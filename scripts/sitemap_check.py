#!/usr/bin/env python3
"""Validate XML sitemaps (index files followed recursively) and spot-check the URLs they list.

Usage:
  sitemap_check.py https://example.com                 # sitemaps declared in robots.txt, else /sitemap.xml
  sitemap_check.py https://example.com/sitemap.xml --sample 100
  sitemap_check.py URL --urls-out urls.txt             # also write every listed URL (feed crawl.py --seed-file)
Outputs JSON: per-file stats, sample results and findings.
"""
from __future__ import annotations

import argparse
import gzip
import random
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from robots_check import sitemaps_in
from seo_lib import Finding, extract_page, fetch, is_indexable, print_json, same_site, site_root, sort_findings

MAX_URLS_PER_FILE = 50_000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_FILES = 200
SITEMAP_TIMEOUT_S = 90  # large sitemap files are slow to serve
W3C_DATETIME = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?)?)?$")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(body: bytes) -> tuple[str, list[dict]]:
    """Return ("urlset"|"sitemapindex", entries) where entries carry loc/lastmod and extension counts."""
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    root = ET.fromstring(body)
    kind = _local(root.tag)
    entries = []
    for node in root:
        entry = {"loc": "", "lastmod": "", "images": 0, "videos": 0, "news": 0, "alternates": 0}
        for child in node:
            name = _local(child.tag)
            if name in ("loc", "lastmod"):
                entry[name] = (child.text or "").strip()
            elif name == "image":
                entry["images"] += 1
            elif name == "video":
                entry["videos"] += 1
            elif name == "news":
                entry["news"] += 1
            elif name == "link":
                entry["alternates"] += 1
        entries.append(entry)
    return kind, entries


def file_findings(url: str, size: int, kind: str, entries: list[dict], site: str) -> list[Finding]:
    out = []
    if size > MAX_UNCOMPRESSED_BYTES:
        out.append(Finding("sitemap-too-big", "high", f"{url} is {size} bytes uncompressed (limit 50 MB)"))
    if len(entries) > MAX_URLS_PER_FILE:
        out.append(Finding("sitemap-too-many", "high", f"{url} lists {len(entries)} URLs (limit 50,000)"))
    if not entries:
        out.append(Finding("sitemap-empty", "medium", f"{url} has no entries"))
    off_site = [e["loc"] for e in entries if e["loc"] and not same_site(e["loc"], site)]
    if off_site and kind == "urlset":
        out.append(Finding("sitemap-cross-host", "medium", f"{len(off_site)} URLs on another host (needs cross-site verification in Search Console)", off_site[0]))
    lastmods = [e["lastmod"] for e in entries if e["lastmod"]]
    bad = [lm for lm in lastmods if not W3C_DATETIME.match(lm)]
    if bad:
        out.append(Finding("sitemap-bad-lastmod", "medium", f"{len(bad)} lastmod values are not W3C Datetime", bad[0]))
    now = datetime.now(timezone.utc).isoformat()
    future = [lm for lm in lastmods if W3C_DATETIME.match(lm) and lm[:10] > now[:10]]
    if future:
        out.append(Finding("sitemap-future-lastmod", "medium", f"{len(future)} lastmod dates are in the future", future[0]))
    if len(lastmods) > 20 and len(set(lastmods)) == 1:
        out.append(Finding("sitemap-uniform-lastmod", "medium", "Every lastmod is identical — Google ignores lastmod it can't trust; emit the real modification date"))
    if entries and not lastmods and kind == "urlset":
        out.append(Finding("sitemap-no-lastmod", "low", f"{url} has no lastmod values"))
    http_urls = [e["loc"] for e in entries if e["loc"].startswith("http://")]
    if http_urls and site.startswith("https://"):
        out.append(Finding("sitemap-http-urls", "high", f"{len(http_urls)} http:// URLs on an https site", http_urls[0]))
    return out


def check_sample(urls: list[str]) -> tuple[list[dict], list[Finding]]:
    rows, out = [], []
    for url in urls:
        facts = extract_page(fetch(url))
        canonical_mismatch = bool(facts.canonical) and facts.canonical.rstrip("/") != facts.final_url.rstrip("/")
        rows.append({"url": url, "status": facts.status, "final_url": facts.final_url, "indexable": is_indexable(facts),
                     "canonical_mismatch": canonical_mismatch})
    bad_status = [r for r in rows if r["status"] != 200 or r["final_url"] != r["url"]]
    if bad_status:
        out.append(Finding("sitemap-non-200", "high", f"{len(bad_status)}/{len(rows)} sampled URLs redirect or error; sitemaps should list only final 200 URLs",
                           ", ".join(f"{r['url']} [{r['status']}]" for r in bad_status[:5])))
    noindex = [r["url"] for r in rows if r["status"] == 200 and not r["indexable"]]
    if noindex:
        out.append(Finding("sitemap-noindex", "high", f"{len(noindex)} sampled URLs are noindex (mixed signals)", ", ".join(noindex[:5])))
    canon = [r["url"] for r in rows if r["canonical_mismatch"]]
    if canon:
        out.append(Finding("sitemap-non-canonical", "medium", f"{len(canon)} sampled URLs canonicalize elsewhere", ", ".join(canon[:5])))
    return rows, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="site root or a sitemap URL")
    ap.add_argument("--sample", type=int, default=30, help="URLs to fetch and verify (0 to skip)")
    ap.add_argument("--urls-out", help="write every listed page URL to this file")
    args = ap.parse_args()

    site = site_root(args.url)
    if urllib.parse.urlsplit(args.url).path.strip("/"):
        queue = [args.url]
    else:
        robots = fetch(urllib.parse.urljoin(site, "/robots.txt"))
        queue = sitemaps_in(robots.text) if robots.status == 200 else []
        queue = queue or [urllib.parse.urljoin(site, "/sitemap.xml")]

    files, findings, page_urls, seen = [], [], [], set()
    while queue and len(seen) < MAX_FILES:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        result = fetch(url, timeout=SITEMAP_TIMEOUT_S)
        if result.status != 200:
            findings.append(Finding("sitemap-unreachable", "high", f"{url} returned {result.status or result.error}"))
            continue
        try:
            kind, entries = parse_sitemap(result.body)
        except (ET.ParseError, OSError) as err:
            findings.append(Finding("sitemap-invalid-xml", "high", f"{url} is not valid XML: {err}"))
            continue
        files.append({"url": url, "kind": kind, "entries": len(entries), "bytes": len(result.body),
                      "with_lastmod": sum(1 for e in entries if e["lastmod"]),
                      "image_entries": sum(e["images"] for e in entries), "video_entries": sum(e["videos"] for e in entries),
                      "news_entries": sum(e["news"] for e in entries), "hreflang_links": sum(e["alternates"] for e in entries)})
        findings += file_findings(url, len(result.body), kind, entries, site)
        if kind == "sitemapindex":
            queue += [e["loc"] for e in entries if e["loc"]]
        else:
            page_urls += [e["loc"] for e in entries if e["loc"]]

    duplicates = len(page_urls) - len(set(page_urls))
    if duplicates:
        findings.append(Finding("sitemap-duplicates", "low", f"{duplicates} URLs listed more than once"))
    if args.urls_out:
        with open(args.urls_out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(dict.fromkeys(page_urls)))
    unique = list(dict.fromkeys(page_urls))
    sample_rows, sample_findings = check_sample(random.Random(0).sample(unique, min(args.sample, len(unique)))) if args.sample else ([], [])
    print_json({"site": site, "files": files, "total_urls": len(unique), "sample": sample_rows,
                "findings": sort_findings(findings + sample_findings)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
