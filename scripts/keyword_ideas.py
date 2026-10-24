#!/usr/bin/env python3
"""Expand seed keywords through public autocomplete (Google, Bing, YouTube) and group them by intent and theme.

Autocomplete shows what people actually type, ordered roughly by popularity, but gives NO search volume.
Pair the output with Search Console impressions, Google Ads Keyword Planner ranges, or a paid tool for volume.

Usage:
  keyword_ideas.py "seo audit"
  keyword_ideas.py "english tutor" --hl en --gl gb --sources google,bing,youtube --deep
Outputs JSON: keywords [{keyword, sources, modifier, intent}], clusters {theme: [keywords]}.
"""
from __future__ import annotations

import argparse
import json
import re
import string
import sys
import time
import urllib.parse
from collections import Counter, defaultdict

from seo_lib import fetch, print_json

QUESTION_PREFIXES = ["how", "what", "why", "when", "where", "who", "which", "can", "is", "does", "should"]
COMMERCIAL_SUFFIXES = ["best", "vs", "review", "price", "cost", "cheap", "near me", "for beginners", "alternative", "free", "online"]
INTENT_PATTERNS = [  # first match wins
    ("transactional", r"\b(buy|price|prices|pricing|cost|cheap|discount|coupon|deal|order|hire|book|near me|for sale|subscription)\b"),
    ("commercial", r"\b(best|top|vs|versus|review|reviews|compare|comparison|alternative|alternatives|rated)\b"),
    ("informational", r"\b(how|what|why|when|where|who|which|guide|tutorial|examples?|meaning|definition|ideas|tips|is|does|can)\b"),
    ("navigational", r"\b(login|log in|sign in|app|website|official|contact|phone number)\b"),
]
STOPWORDS = set("a an the to for of in on and or with without is are be do does can how what why when where who which my your near me vs".split())


def suggest(source: str, query: str, hl: str, gl: str) -> list[str]:
    if source == "google":
        url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "hl": hl, "gl": gl, "q": query})
    elif source == "youtube":
        url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "ds": "yt", "hl": hl, "gl": gl, "q": query})
    elif source == "bing":
        url = "https://api.bing.com/osjson.aspx?" + urllib.parse.urlencode({"query": query, "market": f"{hl}-{gl.upper()}"})
    else:
        raise ValueError(f"unknown source {source}")
    result = fetch(url, timeout=10)
    if result.status != 200:
        return []
    try:
        return [s for s in json.loads(result.text)[1] if isinstance(s, str)]
    except (json.JSONDecodeError, IndexError):
        return []


def classify_intent(keyword: str) -> str:
    for intent, pattern in INTENT_PATTERNS:
        if re.search(pattern, keyword):
            return intent
    return "unclear"


def theme_of(keyword: str, seed_tokens: set[str]) -> str:
    tokens = [t for t in re.findall(r"[\w']+", keyword.lower()) if t not in seed_tokens and t not in STOPWORDS]
    return tokens[0] if tokens else "(head term)"


def expand(seed: str, sources: list[str], hl: str, gl: str, deep: bool, delay: float) -> dict[str, dict]:
    queries = [(seed, "seed")]
    queries += [(f"{seed} {c}", f"+{c}") for c in string.ascii_lowercase]
    queries += [(f"{p} {seed}", f"{p}+") for p in QUESTION_PREFIXES]
    queries += [(f"{seed} {s}", f"+{s}") for s in COMMERCIAL_SUFFIXES]
    if deep:
        queries += [(f"{seed} {c}{d}", f"+{c}{d}") for c in "abcdefghilmnoprstw" for d in "aeiou"]
    found: dict[str, dict] = {}
    for query, modifier in queries:
        for source in sources:
            for keyword in suggest(source, query, hl, gl):
                keyword = keyword.strip().lower()
                entry = found.setdefault(keyword, {"keyword": keyword, "sources": [], "modifier": modifier,
                                                   "intent": classify_intent(keyword)})
                if source not in entry["sources"]:
                    entry["sources"].append(source)
            time.sleep(delay)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("seed", nargs="+", help="one or more seed phrases")
    ap.add_argument("--hl", default="en", help="interface language, e.g. en, ka, de")
    ap.add_argument("--gl", default="us", help="country, e.g. us, gb, ge")
    ap.add_argument("--sources", default="google,bing", help="comma list of google,bing,youtube")
    ap.add_argument("--deep", action="store_true", help="also try two-letter suffixes (≈90 more requests per source)")
    ap.add_argument("--delay", type=float, default=0.25)
    args = ap.parse_args()
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    keywords: dict[str, dict] = {}
    for seed in args.seed:
        keywords.update({k: v for k, v in expand(seed, sources, args.hl, args.gl, args.deep, args.delay).items() if k not in keywords})
    seed_tokens = {t for s in args.seed for t in re.findall(r"[\w']+", s.lower())}
    clusters = defaultdict(list)
    for kw in keywords:
        clusters[theme_of(kw, seed_tokens)].append(kw)
    ordered = dict(sorted(clusters.items(), key=lambda kv: -len(kv[1])))
    print_json({
        "seeds": args.seed, "locale": f"{args.hl}-{args.gl}", "sources": sources, "total": len(keywords),
        "intent_counts": dict(Counter(v["intent"] for v in keywords.values())),
        "multi_source": [k for k, v in keywords.items() if len(v["sources"]) > 1][:50],
        "clusters": ordered,
        "keywords": list(keywords.values()),
        "note": "No search volume: autocomplete only proves the query is typed. Validate with GSC impressions / Keyword Planner / a paid tool.",
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
