#!/usr/bin/env python3
"""Audit one page: indexability, head tags, content shape, media, links, schema, transport.

Usage:
  page_audit.py https://example.com/page
  page_audit.py --file saved.html --base-url https://example.com/page   # offline / rendered DOM
  page_audit.py URL --facts            # also print the extracted facts
Outputs JSON: {"url", "summary", "findings": [...]} sorted by severity.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse

from schema_rules import validate_json_ld
from seo_lib import (
    GOOGLEBOT_HTML_INDEX_BYTES, SEVERITY_ORDER, TITLE_MAX_PX, Finding, PageFacts, extract_page, fetch, is_indexable, load_local, print_json,
    registrable_host, sort_findings, title_pixel_width,
)

HREFLANG_PATTERN = re.compile(r"^(x-default|[a-z]{2,3}(-[a-z]{4})?(-([a-z]{2}|\d{3}))?)$", re.I)
INVALID_HREFLANG_REGIONS = {"uk": "GB", "eu": None, "un": None}  # reserved codes Google ignores
GENERIC_ANCHORS = {"click here", "here", "read more", "more", "learn more", "this", "link", "continue"}
MODERN_IMAGE_EXT = (".webp", ".avif", ".svg")


def bot_challenge(headers: dict[str, str]) -> str:
    """Name the CDN when the response is a bot challenge rather than the page."""
    return "Cloudflare" if headers.get("cf-mitigated") == "challenge" else ""


def audit_page(f: PageFacts) -> list[Finding]:
    out: list[Finding] = []
    add = lambda *args: out.append(Finding(*args))

    # --- reachability & indexability
    if f.status is None:
        add("fetch-failed", "critical", "Page could not be fetched", f.final_url)
        return out
    challenge = bot_challenge(f.response_headers)
    if challenge:
        add("bot-challenge", "critical",
            f"{challenge} answered with a bot challenge, so this audit saw no content. Verified Googlebot/Bingbot are usually let "
            "through, but confirm with Search Console URL Inspection, and check that answer-engine crawlers you want "
            "(OAI-SearchBot, Claude-SearchBot, PerplexityBot) are not challenged too. To audit anyway, save the rendered "
            "page from a browser and re-run with --file.", f.final_url)
        return out
    if f.status >= 400:
        add("http-error", "critical", f"Final response is HTTP {f.status}", f.final_url)
        return out
    if len(f.redirect_chain) > 1:
        add("redirect-chain", "medium", f"{len(f.redirect_chain)} redirect hops before the final URL; link to the final URL directly",
            " -> ".join(f"{u} [{s}]" for u, s in f.redirect_chain))
    if any(s in (302, 307) for _, s in f.redirect_chain):
        add("temporary-redirect", "low", "Chain contains a 302/307; use 301/308 if the move is permanent")
    directives = f"{f.meta_robots}, {f.x_robots_tag}".lower()
    if "noindex" in directives or re.search(r"\bnone\b", directives):
        add("noindex", "high", "Page is noindex — confirm this is intentional", f"meta='{f.meta_robots}' header='{f.x_robots_tag}'")
    if "max-image-preview:large" not in directives.replace(" ", "") and "noindex" not in directives:
        add("no-large-image-preview", "info", "No max-image-preview:large — Google Discover shows large images only with it")
    if "nosnippet" in directives or "max-snippet:0" in directives.replace(" ", ""):
        add("snippet-blocked", "medium", "nosnippet/max-snippet:0 also keeps the page out of Google AI Overviews and featured snippets")
    if urllib.parse.urlsplit(f.final_url).scheme != "https":
        add("not-https", "high", "Final URL is not HTTPS", f.final_url)

    # --- title & description
    title_px = title_pixel_width(f.title)
    if not f.title:
        add("title-missing", "high", "No <title>")
    else:
        if f.title_count > 1:
            add("title-multiple", "medium", f"{f.title_count} <title> elements")
        if title_px > TITLE_MAX_PX:
            add("title-long", "low", f"Title ≈{title_px}px (> ~{TITLE_MAX_PX}px) will likely truncate on desktop (no hard limit; Google truncates by width)", f.title)
        if len(f.title) < 25:
            add("title-short", "low", "Title under 25 chars — usually room for a descriptive qualifier", f.title)
    if not f.meta_description:
        add("description-missing", "medium", "No meta description (Google will pick page text for the snippet)")
    elif len(f.meta_description) > 160:
        add("description-long", "info", f"Meta description is {len(f.meta_description)} chars; Google has no limit but truncates to device width (~150–160 chars on desktop)")
    elif len(f.meta_description) < 70:
        add("description-short", "low", f"Meta description is only {len(f.meta_description)} chars")

    # --- canonical & hreflang
    if f.canonical_in_body:
        add("canonical-in-body", "medium", "rel=canonical found outside <head> — Google ignores it there")
    if f.canonical_count == 0:
        add("canonical-missing", "medium", "No rel=canonical")
    elif f.canonical_count > 1:
        add("canonical-multiple", "high", f"{f.canonical_count} canonical tags — Google may ignore all of them")
    elif f.canonical.rstrip("/") != f.final_url.rstrip("/"):
        severity = "high" if registrable_host(f.canonical) != registrable_host(f.final_url) else "info"
        add("canonical-elsewhere", severity, "Canonical points to another URL — page will not be indexed itself", f.canonical)
    if f.canonical.startswith("http://") and f.final_url.startswith("https://"):
        add("canonical-http", "high", "Canonical uses http:// on an https page", f.canonical)
    if f.hreflang:
        codes = [h["hreflang"] for h in f.hreflang]
        for code in codes:
            region = code.split("-")[-1].lower() if "-" in code else ""
            if not HREFLANG_PATTERN.match(code) or region in INVALID_HREFLANG_REGIONS:
                fix = INVALID_HREFLANG_REGIONS.get(region)
                add("hreflang-invalid", "high", f"Invalid hreflang '{code}'" + (f" (use -{fix})" if fix else ""))
        if len(codes) != len(set(c.lower() for c in codes)):
            add("hreflang-duplicate", "medium", "Duplicate hreflang values")
        if not any(h["href"].rstrip("/") == f.final_url.rstrip("/") for h in f.hreflang):
            add("hreflang-no-self", "medium", "hreflang set does not include this page itself")
        if "x-default" not in (c.lower() for c in codes):
            add("hreflang-no-x-default", "low", "No x-default alternate")

    # --- document basics
    if not f.viewport:
        add("viewport-missing", "high", "No meta viewport — fails mobile-friendliness (mobile-first indexing)")
    if not f.lang:
        add("lang-missing", "low", "<html> has no lang attribute")
    if not f.charset_declared:
        add("charset-missing", "low", "No <meta charset>")
    if f.html_bytes > GOOGLEBOT_HTML_INDEX_BYTES:
        add("html-truncated", "critical", f"HTML is {f.html_bytes // 1024} KB uncompressed: Googlebot indexes only the first 2 MB")
    elif f.html_bytes > GOOGLEBOT_HTML_INDEX_BYTES // 2:
        add("html-heavy", "low", f"HTML is {f.html_bytes // 1024} KB — half of Googlebot's 2 MB indexing cut-off")

    # --- content shape
    h1s = [text for level, text in f.headings if level == 1]
    if not h1s:
        add("h1-missing", "medium", "No <h1>")
    elif len(h1s) > 1:
        add("h1-multiple", "info", f"{len(h1s)} <h1> elements (allowed, but one clear main heading is easier to parse)", " | ".join(h1s[:4]))
    levels = [level for level, _ in f.headings]
    if any(b - a > 1 for a, b in zip(levels, levels[1:])):
        add("heading-skip", "info", "Heading levels skip (e.g. h2 → h4)")
    if f.word_count < 50 and len(f.internal_links) < 3:
        add("likely-client-rendered", "high",
            "Almost no text or links in the raw HTML — content is probably rendered by JavaScript. Googlebot renders JS later; "
            "most AI crawlers (GPTBot, ClaudeBot, PerplexityBot) do not. Re-run on the rendered DOM and consider SSR/SSG.")
    elif f.word_count < 250:
        add("thin-content", "low", f"Only ~{f.word_count} words of visible text (fine for some page types; check intent)")

    # --- images
    no_alt = [i["src"] for i in f.images if "alt" not in i]
    if no_alt:
        add("img-alt-missing", "medium", f"{len(no_alt)} <img> without an alt attribute", ", ".join(no_alt[:5]))
    no_dims = [i["src"] for i in f.images if not (i.get("width") and i.get("height"))]
    if no_dims:
        add("img-no-dimensions", "low", f"{len(no_dims)} <img> without width/height (layout shift / CLS risk)", ", ".join(no_dims[:5]))
    if f.images and f.images[0].get("loading", "").lower() == "lazy":
        add("lcp-lazy", "medium", "First image is loading=lazy — if it is the LCP element this delays LCP", f.images[0]["src"])
    legacy = [i["src"] for i in f.images if i["src"] and not urllib.parse.urlsplit(i["src"]).path.lower().endswith(MODERN_IMAGE_EXT)
              and not i.get("srcset")]
    if len(legacy) > 3:
        add("img-legacy-formats", "info", f"{len(legacy)} images without srcset or WebP/AVIF")

    # --- links
    if not f.internal_links:
        add("no-internal-links", "high", "Page has no crawlable internal <a href> links (dead end for crawlers)")
    nofollow_internal = [l["href"] for l in f.internal_links if "nofollow" in l["rel"].lower()]
    if nofollow_internal:
        add("internal-nofollow", "medium", f"{len(nofollow_internal)} internal links are rel=nofollow", ", ".join(nofollow_internal[:5]))
    empty = [l["href"] for l in f.internal_links + f.external_links if not l["text"]]
    if empty:
        add("anchor-empty", "low", f"{len(empty)} links have no anchor text or image alt", ", ".join(empty[:5]))
    generic = [l["text"] for l in f.internal_links if l["text"].lower() in GENERIC_ANCHORS]
    if generic:
        add("anchor-generic", "low", f"{len(generic)} internal links use generic anchors like '{generic[0]}'")

    # --- performance & transport hints
    if f.head_blocking_scripts:
        add("render-blocking-js", "low", f"{len(f.head_blocking_scripts)} synchronous <script src> in <head>", ", ".join(f.head_blocking_scripts[:5]))
    if f.response_headers.get("content-encoding", "") not in ("gzip", "br", "deflate", "zstd") and f.html_bytes > 10_000:
        add("no-compression", "medium", "HTML served without gzip/brotli compression")
    if f.final_url.startswith("https://") and "strict-transport-security" not in f.response_headers:
        add("no-hsts", "low", "No Strict-Transport-Security header")
    if f.elapsed_ms > 1500:
        add("slow-response", "medium", f"HTML took {f.elapsed_ms} ms to download (from this machine; confirm with PSI/CrUX TTFB)")
    if f.final_url.startswith("https://"):
        insecure = [i["src"] for i in f.images if i["src"].startswith("http://")]
        if insecure:
            add("mixed-content", "medium", f"{len(insecure)} images loaded over http://", ", ".join(insecure[:3]))

    # --- social & structured data
    missing_og = [k for k in ("og:title", "og:description", "og:image") if k not in f.open_graph]
    if missing_og:
        add("og-missing", "low", f"Missing Open Graph tags: {missing_og}")
    for err in f.json_ld_errors:
        add("schema-parse-error", "high", f"JSON-LD block does not parse: {err}")
    types, schema_findings = validate_json_ld(f.json_ld)
    out.extend(schema_findings)
    if not types and not f.microdata_types:
        add("schema-none", "info", "No structured data found")
    return out


def summarize(f: PageFacts) -> dict:
    types, _ = validate_json_ld(f.json_ld)
    return {
        "status": f.status, "final_url": f.final_url, "indexable": is_indexable(f), "title": f.title,
        "title_px": title_pixel_width(f.title), "meta_description": f.meta_description, "canonical": f.canonical,
        "h1": [t for lvl, t in f.headings if lvl == 1], "word_count": f.word_count,
        "internal_links": len(f.internal_links), "external_links": len(f.external_links), "images": len(f.images),
        "schema_types": sorted(set(types)), "hreflang_count": len(f.hreflang), "html_kb": f.html_bytes // 1024,
        "download_ms": f.elapsed_ms,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--file", help="audit a saved HTML file (e.g. rendered DOM) instead of fetching")
    ap.add_argument("--base-url", default="https://localhost/", help="URL the saved file was served from")
    ap.add_argument("--facts", action="store_true", help="include the full extracted facts")
    ap.add_argument("--fail-on", choices=("critical", "high", "medium", "low"), help="exit 1 if any finding is this severe (for CI)")
    args = ap.parse_args()
    if not args.url and not args.file:
        ap.error("give a URL or --file")
    result = load_local(args.file, args.base_url) if args.file else fetch(args.url)
    if result.error:
        print_json({"url": args.url, "error": result.error})
        return 2
    facts = extract_page(result)
    findings = sort_findings(audit_page(facts))
    report = {"url": facts.url, "summary": summarize(facts), "findings": findings}
    if args.facts:
        report["facts"] = facts.to_dict()
    print_json(report)
    if args.fail_on and any(SEVERITY_ORDER[f.severity] <= SEVERITY_ORDER[args.fail_on] for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
