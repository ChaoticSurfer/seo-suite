#!/usr/bin/env python3
"""Validate sitemaps (XML, RSS/Atom or text; index files followed) and spot-check the URLs they list.

Usage:
  sitemap_check.py https://example.com                 # sitemaps declared in robots.txt, else /sitemap.xml
  sitemap_check.py https://example.com/sitemap.xml --sample 100
  sitemap_check.py URL --urls-out urls.txt             # also write every listed URL (feed crawl.py --sitemap-urls)
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
import zlib
from datetime import datetime, timezone

from robots_check import google_visible_robots, sitemaps_in
from seo_lib import Finding, extract_page, fetch, is_indexable, print_json, site_root, sort_findings, to_uri

MAX_URLS_PER_FILE = 50_000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_FILES = 200
SITEMAP_TIMEOUT_S = 90  # large sitemap files are slow to serve
W3C_DATETIME = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2}))?)?)?$")  # a time needs a zone
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


class UnsupportedSitemapFormat(ValueError):
    """Well-formed XML whose root element is not a sitemap format Google reads."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _entry(loc: str = "", lastmod: str = "") -> dict:
    return {"loc": loc, "lastmod": lastmod, "images": 0, "videos": 0, "news": 0, "alternates": 0}


def _atom_link(entry: ET.Element) -> str:
    """An Atom entry's URL is the href of its rel=alternate link (a link without rel is alternate)."""
    for link in entry.iter(ATOM_NS + "link"):
        if link.get("rel", "alternate") == "alternate":
            return link.get("href", "").strip()
    return ""


def decompress(body: bytes) -> bytes:
    """Sitemaps may be served gzipped (.xml.gz) without a Content-Encoding header; Google's limits apply uncompressed."""
    return gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body


def parse_sitemap(xml: bytes) -> tuple[str, list[dict]]:
    """Return (kind, entries) for an uncompressed sitemap: kind is urlset|sitemapindex|rss|feed|text.

    Entries carry loc/lastmod and extension counts. Raises UnsupportedSitemapFormat for any other XML root.
    """
    if xml.removeprefix(b"\xef\xbb\xbf").lstrip().startswith((b"http://", b"https://")):  # text sitemap: one URL per line
        return "text", [_entry(line.strip()) for line in xml.decode("utf-8-sig", "replace").splitlines() if line.strip()]
    root = ET.fromstring(xml)
    if root.tag == "rss":  # RSS 2.0 / mRSS: the channel's own <link> is not a listed URL
        return "rss", [_entry((item.findtext("link") or "").strip()) for item in root.iter("item")]
    if root.tag == ATOM_NS + "feed":
        return "feed", [_entry(_atom_link(e), (e.findtext(ATOM_NS + "updated") or "").strip()) for e in root.iter(ATOM_NS + "entry")]
    if root.tag not in (SITEMAP_NS + "urlset", SITEMAP_NS + "sitemapindex"):
        raise UnsupportedSitemapFormat(f"root element <{root.tag}> is not <urlset>/<sitemapindex> with "
                                       f'xmlns="{SITEMAP_NS.strip("{}")}", RSS 2.0 <rss> or an Atom 1.0 <feed>')
    kind = _local(root.tag)
    entries = []
    for node in root:
        entry = _entry()
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


def _is_w3c_datetime(value: str) -> bool:
    """W3C Datetime that is also a real date and time (no month 13, no hour 25)."""
    if not W3C_DATETIME.match(value):
        return False
    if len(value) < 10:  # YYYY or YYYY-MM
        return True
    try:  # fractional seconds dropped and Z spelled +00:00 so Python 3.9's fromisoformat accepts it
        datetime.fromisoformat(re.sub(r"\.\d+", "", value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def file_findings(url: str, kind: str, entries: list[dict], site: str) -> list[Finding]:
    """Findings for one parsed file; `url` is the file's final (post-redirect) URL."""
    out = []
    if len(entries) > MAX_URLS_PER_FILE:
        out.append(Finding("sitemap-too-many", "high", f"{url} lists {len(entries)} URLs (limit 50,000)"))
    if not entries:
        out.append(Finding("sitemap-empty", "medium", f"{url} has no entries"))
    file_host = urllib.parse.urlsplit(url).hostname  # fetch() gives the final URL a punycode host, so compare locs in that form
    off_site = [e["loc"] for e in entries if e["loc"] and urllib.parse.urlsplit(to_uri(e["loc"])).hostname != file_host]
    if off_site and kind != "sitemapindex":
        out.append(Finding("sitemap-cross-host", "medium", f"{len(off_site)} URLs on another host than the sitemap file (www and non-www differ; "
                           "needs cross-site verification in Search Console)", off_site[0]))
    lastmods = [e["lastmod"] for e in entries if e["lastmod"]]
    bad = [lm for lm in lastmods if not _is_w3c_datetime(lm)]
    if bad:
        out.append(Finding("sitemap-bad-lastmod", "medium", f"{len(bad)} lastmod values are not W3C Datetime", bad[0]))
    now = datetime.now(timezone.utc).isoformat()
    future = [lm for lm in lastmods if _is_w3c_datetime(lm) and lm[:10] > now[:10]]
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
    bad_status = [r for r in rows if r["status"] != 200 or r["final_url"] != to_uri(r["url"])]  # fetch() returns to_uri() form
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
        queue = sitemaps_in(google_visible_robots(robots.text)) if robots.status == 200 else []
        queue = queue or [urllib.parse.urljoin(site, "/sitemap.xml")]

    files, findings, page_urls, seen, listed_in_index = [], [], [], set(), set()
    submitted, kinds, nested_indexes = set(queue), {}, {}  # kinds: url -> kind; nested_indexes: url -> None (ordered set)
    while queue and len(seen) < MAX_FILES:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        result = fetch(url, timeout=SITEMAP_TIMEOUT_S, max_bytes=MAX_UNCOMPRESSED_BYTES + 1)  # one byte over shows a too-big file
        if result.status != 200:
            findings.append(Finding("sitemap-unreachable", "high", f"{url} returned {result.status or result.error}"))
            continue
        try:
            xml = decompress(result.body)
        except (OSError, EOFError, zlib.error) as err:  # bad header, truncated stream, corrupt deflate data
            findings.append(Finding("sitemap-compression-error", "high", f"{url} could not be decompressed: {err}"))
            continue
        if len(xml) > MAX_UNCOMPRESSED_BYTES:
            # A plain file is read only one byte past the limit, so its real size is unknown; a gzipped one is complete.
            size = "larger than 50 MB" if len(result.body) > MAX_UNCOMPRESSED_BYTES else f"{len(xml)} bytes"
            findings.append(Finding("sitemap-too-big", "high", f"{url} is {size} uncompressed (limit 50 MB)"))
            continue
        try:
            kind, entries = parse_sitemap(xml)
        except ET.ParseError as err:
            findings.append(Finding("sitemap-invalid-xml", "high", f"{url} is not valid XML: {err}"))
            continue
        except UnsupportedSitemapFormat as err:
            findings.append(Finding("sitemap-unsupported-format", "high", f"{url} is not a sitemap Google reads: {err}"))
            continue
        files.append({"url": url, "kind": kind, "entries": len(entries), "bytes": len(xml),
                      "with_lastmod": sum(1 for e in entries if e["lastmod"]),
                      "image_entries": sum(e["images"] for e in entries), "video_entries": sum(e["videos"] for e in entries),
                      "news_entries": sum(e["news"] for e in entries), "hreflang_links": sum(e["alternates"] for e in entries)})
        findings += file_findings(result.final_url, kind, entries, site)
        kinds[url] = kind
        if kind == "sitemapindex":
            children = [e["loc"] for e in entries if e["loc"]]
            # An index listed in another index is nested, whichever of the two was read first.
            if url in listed_in_index:
                nested_indexes[url] = None
            nested_indexes.update(dict.fromkeys(c for c in children if kinds.get(c) == "sitemapindex"))
            listed_in_index.update(children)
            if url in submitted:  # Google reads an index submitted directly, but not one it only finds inside another index
                queue += children
        else:
            page_urls += [e["loc"] for e in entries if e["loc"]]
    for url in nested_indexes:
        findings.append(Finding("sitemap-nested-index", "high", f"{url} is a sitemap index listed in another index; Google does not read nested indexes"))
    skipped = [u for u in dict.fromkeys(queue) if u not in seen]
    if skipped:
        findings.append(Finding("sitemap-files-skipped", "info", f"{len(skipped)} sitemap files not checked (limit {MAX_FILES}); total_urls and --urls-out are incomplete", skipped[0]))

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
