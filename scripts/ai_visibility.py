#!/usr/bin/env python3
"""Score AI-answer visibility from logged observations, with Wilson 95% confidence intervals.

AI answers vary run to run, so one check proves nothing. Freeze a query set first, run each query
several times per engine (ChatGPT, Perplexity, Google AI Overviews/AI Mode, Copilot, Claude, Gemini),
and log one CSV row per answer:
  query,engine,run,date,mentioned,cited,cited_url,competitors_mentioned
  "best english tutor tbilisi",perplexity,1,2026-10-24,1,0,,"preply;italki"
mentioned/cited are 1/0. competitors_mentioned is ';'-separated.
Usage:
  ai_visibility.py observations.csv [--brand-domain example.com] [--compare earlier.csv]
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict

from seo_lib import print_json

Z_95 = 1.96
MIN_RUNS_FOR_RATE = 3


def wilson(successes: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + Z_95 ** 2 / n
    centre = (p + Z_95 ** 2 / (2 * n)) / denom
    margin = Z_95 * math.sqrt(p * (1 - p) / n + Z_95 ** 2 / (4 * n * n)) / denom
    return (round(max(0.0, centre - margin), 3), round(min(1.0, centre + margin), 3))


def rate(successes: int, n: int) -> dict:
    if n < MIN_RUNS_FOR_RATE:
        return {"n": n, "rate": "not-estimated (fewer than 3 observations)"}
    low, high = wilson(successes, n)
    return {"n": n, "hits": successes, "rate": round(successes / n, 3), "ci95": [low, high]}


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["mentioned"] = row.get("mentioned", "0").strip() in ("1", "true", "yes")
        row["cited"] = row.get("cited", "0").strip() in ("1", "true", "yes")
    return rows


def summarize(rows: list[dict], brand_domain: str | None) -> dict:
    by_engine = defaultdict(list)
    for row in rows:
        by_engine[row["engine"].strip().lower()].append(row)
    engines = {}
    for engine, items in sorted(by_engine.items()):
        engines[engine] = {"mention_rate": rate(sum(r["mentioned"] for r in items), len(items)),
                           "citation_rate": rate(sum(r["cited"] for r in items), len(items))}
    by_query = defaultdict(list)
    for row in rows:
        by_query[row["query"]].append(row)
    never = [q for q, items in by_query.items() if not any(r["mentioned"] or r["cited"] for r in items)]
    competitors = Counter(c.strip().lower() for r in rows for c in (r.get("competitors_mentioned") or "").split(";") if c.strip())
    cited_urls = Counter(r["cited_url"].strip() for r in rows if r.get("cited_url", "").strip())
    report = {"observations": len(rows), "queries": len(by_query), "overall": {
        "mention_rate": rate(sum(r["mentioned"] for r in rows), len(rows)),
        "citation_rate": rate(sum(r["cited"] for r in rows), len(rows))},
        "by_engine": engines, "queries_never_visible": never, "competitor_mentions": competitors.most_common(15),
        "most_cited_urls": cited_urls.most_common(15)}
    if brand_domain:
        report["cited_urls_off_brand"] = [u for u, _ in cited_urls.most_common() if brand_domain not in u][:15]
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--brand-domain")
    ap.add_argument("--compare", help="earlier observations CSV with the same frozen query set")
    args = ap.parse_args()
    current = summarize(load(args.csv), args.brand_domain)
    if args.compare:
        earlier = summarize(load(args.compare), args.brand_domain)
        current["comparison"] = {"earlier_overall": earlier["overall"],
                                 "note": "Overlapping confidence intervals mean no detectable change. Report as observational drift, never as caused by a change."}
    print_json(current)
    return 0


if __name__ == "__main__":
    sys.exit(main())
