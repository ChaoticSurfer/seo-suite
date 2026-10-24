#!/usr/bin/env python3
"""Fetch and evaluate robots.txt the way Google does (RFC 9309 + Google's longest-match rule).

Usage:
  robots_check.py https://example.com                     # search + AI crawler access matrix for "/"
  robots_check.py https://example.com --path /blog/ --path /cart?x=1
  robots_check.py --file robots.txt --path /private/      # test a draft before deploying
Outputs JSON: size, sitemaps, groups, per-bot verdict per path, and findings.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse

from seo_lib import Finding, fetch, print_json, site_root, sort_findings

ROBOTS_MAX_BYTES = 500 * 1024  # Google ignores rules after the first 500 KiB.

# Product token -> what it controls. Tokens are matched case-insensitively.
CRAWLERS = {
    "Googlebot": "Google Search crawling (also feeds AI Overviews / AI Mode — no separate opt-out)",
    "Googlebot-Image": "Google Images (falls back to the Googlebot group)",
    "Googlebot-News": "Google News (falls back to the Googlebot group)",
    "Storebot-Google": "Google Shopping / Merchant crawling",
    "Google-Extended": "Gemini model training & grounding; does NOT affect Google Search or AI Overviews",
    "Bingbot": "Bing Search, and therefore Copilot and many ChatGPT search results",
    "OAI-SearchBot": "ChatGPT search results / citations",
    "ChatGPT-User": "ChatGPT fetching a page a user asked about (robots.txt may not apply)",
    "GPTBot": "OpenAI model training",
    "OAI-AdsBot": "ChatGPT ad landing-page safety checks",
    "ClaudeBot": "Anthropic model training",
    "Claude-SearchBot": "Claude search results / citations",
    "Claude-User": "Claude fetching a page a user asked about",
    "PerplexityBot": "Perplexity search index",
    "Perplexity-User": "Perplexity fetching on a user's request (generally ignores robots.txt)",
    "Applebot": "Apple Spotlight / Siri / Safari suggestions",
    "Applebot-Extended": "Apple model training",
    "CCBot": "Common Crawl (training data for many models)",
    "Bytespider": "ByteDance crawler / training",
    "meta-externalagent": "Meta AI training and retrieval",
    "DuckAssistBot": "DuckDuckGo AI answers",
    "YandexBot": "Yandex Search",
}


def parse_robots(text: str) -> list[dict]:
    """Return groups: [{"agents": [...], "rules": [("allow"|"disallow", pattern)]}]."""
    groups: list[dict] = []
    current: dict | None = None
    last_was_agent = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or not last_was_agent:
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(value.lower())
            last_was_agent = True
            continue
        last_was_agent = False
        if key in ("allow", "disallow") and current is not None:
            current["rules"].append((key, value))
    return groups


def sitemaps_in(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*sitemap\s*:\s*(\S+)", text, re.I | re.M)]


def content_signals(text: str) -> list[str]:
    """Content-Signal lines (e.g. 'search=yes, ai-train=no') — a published preference, not an access control."""
    return [m.group(1).strip() for m in re.finditer(r"^\s*content-signal\s*:\s*(.+)$", text, re.I | re.M)]


def group_for(groups: list[dict], user_agent: str) -> dict | None:
    """Google picks the most specific matching user-agent group; all groups naming it are merged."""
    ua = user_agent.lower()
    exact = [g for g in groups if ua in g["agents"]]
    if exact:
        return {"agents": [ua], "rules": [r for g in exact for r in g["rules"]]}
    if ua.startswith("googlebot-"):  # Googlebot-Image/-News/-Video obey the googlebot group when not named
        return group_for(groups, "googlebot")
    star = [g for g in groups if "*" in g["agents"]]
    if star:
        return {"agents": ["*"], "rules": [r for g in star for r in g["rules"]]}
    return None


def _pattern_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.compile(body + ("$" if anchored else ""))


def is_allowed(group: dict | None, path: str) -> tuple[bool, str]:
    """Longest matching pattern wins; on equal length, allow wins. Empty disallow matches nothing."""
    if group is None:
        return True, "no matching group"
    best: tuple[int, bool, str] | None = None
    for kind, pattern in group["rules"]:
        if not pattern:
            continue
        if _pattern_regex(pattern).match(path):
            candidate = (len(pattern), kind == "allow", f"{kind}: {pattern}")
            if best is None or candidate[:2] > best[:2]:
                best = candidate
    return (True, "no rule matched") if best is None else (best[1], best[2])


def evaluate(text: str, paths: list[str]) -> dict:
    groups = parse_robots(text)
    matrix = {}
    for bot, purpose in CRAWLERS.items():
        group = group_for(groups, bot)
        matrix[bot] = {
            "purpose": purpose,
            "group": group["agents"][0] if group else None,
            "paths": {p: dict(zip(("allowed", "rule"), is_allowed(group, p))) for p in paths},
        }
    return {"groups": groups, "sitemaps": sitemaps_in(text), "matrix": matrix}


def findings_for(text: str, size: int, status: int | None, evaluation: dict) -> list[Finding]:
    out: list[Finding] = []
    if status and (500 <= status < 600 or status == 429):
        out.append(Finding("robots-5xx", "critical", f"robots.txt returns {status}: Google stops crawling for 12 h, then uses its cached copy for up to 30 days"))
    elif status and status >= 400:
        out.append(Finding("robots-missing", "info", f"robots.txt returns {status}: everything is crawlable"))
    if size > ROBOTS_MAX_BYTES:
        out.append(Finding("robots-too-big", "high", f"robots.txt is {size} bytes; Google ignores content after 500 KiB"))
    if not evaluation["sitemaps"]:
        out.append(Finding("robots-no-sitemap", "low", "No Sitemap: line in robots.txt"))
    google = evaluation["matrix"]["Googlebot"]["paths"].get("/", {})
    if google and not google["allowed"]:
        out.append(Finding("robots-blocks-google", "critical", "Googlebot is disallowed from '/'", google["rule"]))
    for bot in ("Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"):
        verdict = evaluation["matrix"][bot]["paths"].get("/", {})
        if verdict and not verdict["allowed"]:
            out.append(Finding("robots-blocks-answer-engine", "medium",
                               f"{bot} blocked from '/': the site cannot be cited by {CRAWLERS[bot].split(' /')[0]}", verdict["rule"]))
    if re.search(r"^\s*(noindex|crawl-delay)\s*:", text, re.I | re.M):
        out.append(Finding("robots-unsupported", "low", "noindex:/crawl-delay: lines are ignored by Google (Bing and Anthropic honour crawl-delay)"))
    for group in evaluation["groups"]:
        for kind, pattern in group["rules"]:
            if kind == "disallow" and re.search(r"\.(css|js)(\$|\*|$)", pattern):
                out.append(Finding("robots-blocks-assets", "high", "CSS/JS disallowed — Google cannot render pages properly", pattern))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site", nargs="?")
    ap.add_argument("--file", help="evaluate a local robots.txt instead of fetching")
    ap.add_argument("--path", action="append", help="URL path to test (repeatable); default '/'")
    args = ap.parse_args()
    if not args.site and not args.file:
        ap.error("give a site URL or --file")
    paths = args.path or ["/"]
    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        status, source = 200, args.file
    else:
        source = urllib.parse.urljoin(site_root(args.site), "/robots.txt")
        result = fetch(source)
        if result.error:
            print_json({"robots_url": source, "error": result.error})
            return 2
        status = result.status
        text = result.text if status == 200 else ""
    size = len(text.encode())
    evaluation = evaluate(text, paths)
    print_json({
        "robots_url": source, "status": status, "bytes": size, "sitemaps": evaluation["sitemaps"],
        "content_signals": content_signals(text),
        "matrix": evaluation["matrix"], "findings": sort_findings(findings_for(text, size, status, evaluation)),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
