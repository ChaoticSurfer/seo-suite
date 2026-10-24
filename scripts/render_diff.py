#!/usr/bin/env python3
"""Compare what crawlers get in the raw HTML with what the browser renders after JavaScript.

Get the rendered DOM from a real browser (e.g. run `document.documentElement.outerHTML` in the built-in
browser and save it), then:
  render_diff.py https://example.com/page --rendered rendered.html
  render_diff.py --raw raw.html --rendered rendered.html --base-url https://example.com/page
Anything present only after rendering is invisible to non-rendering crawlers (most AI bots) and
delayed for Googlebot. A canonical/robots/title that changes after JS is a conflict Google may resolve badly.
"""
from __future__ import annotations

import argparse
import sys

from schema_rules import validate_json_ld
from seo_lib import Finding, PageFacts, extract_page, fetch, load_local, print_json

CRITICAL_FIELDS = ("title", "meta_robots", "canonical")


def snapshot(f: PageFacts) -> dict:
    types, _ = validate_json_ld(f.json_ld)
    return {
        "title": f.title, "meta_description": f.meta_description, "meta_robots": f.meta_robots, "canonical": f.canonical,
        "h1": [t for lvl, t in f.headings if lvl == 1], "word_count": f.word_count,
        "internal_links": len(f.internal_links), "schema_types": sorted(set(types)), "hreflang": len(f.hreflang),
        "images": len(f.images),
    }


def diff(raw: dict, rendered: dict) -> dict:
    changes = {k: {"raw": raw[k], "rendered": rendered[k]} for k in raw if raw[k] != rendered[k]}
    warnings = [f"{k} changes after JavaScript" for k in CRITICAL_FIELDS if k in changes]
    if rendered["word_count"] and raw["word_count"] < 0.5 * rendered["word_count"]:
        warnings.append(f"Only {raw['word_count']} of {rendered['word_count']} words are in the raw HTML")
    if rendered["internal_links"] and raw["internal_links"] < 0.5 * rendered["internal_links"]:
        warnings.append(f"Only {raw['internal_links']} of {rendered['internal_links']} internal links are in the raw HTML")
    missing_schema = sorted(set(rendered["schema_types"]) - set(raw["schema_types"]))
    if missing_schema:
        warnings.append(f"Structured data injected by JS only: {missing_schema}")
    if "noindex" in raw["meta_robots"].lower() and "noindex" not in rendered["meta_robots"].lower():
        warnings.append("Raw HTML is noindex and JS removes it — Google may never render it, so the page stays out")
    return {"changes": changes, "warnings": warnings}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--raw", help="saved raw HTML (instead of fetching url)")
    ap.add_argument("--rendered", required=True, help="saved rendered DOM HTML")
    ap.add_argument("--base-url", default="https://localhost/")
    args = ap.parse_args()
    if not args.url and not args.raw:
        ap.error("give a URL or --raw")
    base = args.url or args.base_url
    raw_result = load_local(args.raw, base) if args.raw else fetch(args.url)
    if raw_result.error:
        print_json({"url": base, "error": raw_result.error})
        return 2
    if raw_result.status >= 400:
        print_json({"url": raw_result.final_url, "status": raw_result.status,
                    "error": f"HTTP {raw_result.status} — raw fetch failed, not diffing an error/challenge page (check page_audit for bot challenges)"})
        return 2
    raw = extract_page(raw_result)
    rendered = extract_page(load_local(args.rendered, raw_result.final_url))  # same base as the raw side, after redirects
    raw_snap, rendered_snap = snapshot(raw), snapshot(rendered)
    result = diff(raw_snap, rendered_snap)
    findings = [Finding("js-dependent-seo", "high", w) for w in result["warnings"]]
    print_json({"url": base, "raw": raw_snap, "rendered": rendered_snap, **result, "findings": findings})
    return 0


if __name__ == "__main__":
    sys.exit(main())
