#!/usr/bin/env python3
"""Score AI-answer visibility from logged observations, with Wilson 95% confidence intervals.

AI answers vary run to run, so one check proves nothing. Freeze a query set first, run each query
several times per engine, and log one CSV row per answer:
  query,engine,run,date,mentioned,cited,cited_url,competitors_mentioned
  "best english tutor tbilisi",perplexity,1,2026-10-24,1,0,,"preply;italki"
mentioned/cited are 1/0. competitors_mentioned is ';'-separated.
ai_probe.py writes these rows from the official APIs, with more columns this script also reads when present:
  locale, lang, prompt_class (brand/category/comparison/problem), prompt_id, prompt_set (version@hash), surface
  ("api"), model_id, tool_version, search_calls, cited_domains and source_domains (';'), answer_sha256, cost_usd.
With them it adds rates per engine, language and prompt class, AI share of voice (answers naming a brand / answers
naming any tracked brand), mentions without a citation, and the domains cited where a competitor is named and we
aren't (PR and listing targets). --compare refuses two files from different prompt sets.
Usage:
  ai_visibility.py observations.csv [--brand-domain example.com] [--compare earlier.csv]
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict

from seo_lib import print_json, registrable_host

Z_95 = 1.96
TRUTHY = ("1", "true", "yes", "y")
MIN_RUNS_FOR_RATE = 3


def wilson(successes: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + Z_95 ** 2 / n
    centre = (p + Z_95 ** 2 / (2 * n)) / denom
    margin = Z_95 * math.sqrt(p * (1 - p) / n + Z_95 ** 2 / (4 * n * n)) / denom
    return (round(max(0.0, centre - margin), 3), round(min(1.0, centre + margin), 3))


def difference_ci(hits_now: int, n_now: int, hits_before: int, n_before: int) -> dict:
    """Newcomb's hybrid-score 95% CI for rate_now − rate_before (built from the two Wilson intervals)."""
    if n_now < MIN_RUNS_FOR_RATE or n_before < MIN_RUNS_FOR_RATE:
        return {"difference": "not-estimated (fewer than 3 observations in a period)"}
    p1, p2 = hits_now / n_now, hits_before / n_before
    (l1, u1), (l2, u2) = wilson(hits_now, n_now), wilson(hits_before, n_before)
    diff = p1 - p2
    low = diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    high = diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return {"difference": round(diff, 3), "ci95": [round(low, 3), round(high, 3)], "detectable_change": low > 0 or high < 0}


def rate(successes: int, n: int) -> dict:
    if n < MIN_RUNS_FOR_RATE:
        return {"n": n, "rate": "not-estimated (fewer than 3 observations)"}
    low, high = wilson(successes, n)
    return {"n": n, "hits": successes, "rate": round(successes / n, 3), "ci95": [low, high]}


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["mentioned"] = (row.get("mentioned") or "0").strip().lower() in TRUTHY
        row["cited"] = (row.get("cited") or "0").strip().lower() in TRUTHY
    return rows


def split_list(value: str | None) -> list[str]:
    return [item.strip().lower() for item in (value or "").split(";") if item.strip()]


def rates(items: list[dict]) -> dict:
    return {"mention_rate": rate(sum(r["mentioned"] for r in items), len(items)),
            "citation_rate": rate(sum(r["cited"] for r in items), len(items))}


def share_of_voice(rows: list[dict]) -> dict:
    """AI share of voice: of the answers naming any tracked brand (ours or a competitor), the share naming each one."""
    tracked = [r for r in rows if r["mentioned"] or split_list(r.get("competitors_mentioned"))]
    named = Counter(c for r in tracked for c in set(split_list(r.get("competitors_mentioned"))))
    shares = {"brand": rate(sum(r["mentioned"] for r in tracked), len(tracked))}
    shares.update({competitor: rate(count, len(tracked)) for competitor, count in named.most_common(15)})
    return {"answers_naming_a_tracked_brand": len(tracked), "shares": shares,
            "note": "Shares don't add up to 1: one answer can name several brands. They depend on the prompt set, "
                    "engines and competitor list, so compare them only within one prompt set."}


def is_own(domain: str, brand: str | None) -> bool:
    return bool(brand) and (domain == brand or domain.endswith("." + brand))


def summarize(rows: list[dict], brand_domain: str | None) -> dict:
    by_engine = defaultdict(list)
    for row in rows:
        by_engine[row["engine"].strip().lower()].append(row)
    engines = {engine: rates(items) for engine, items in sorted(by_engine.items())}
    by_query = defaultdict(list)
    for row in rows:
        by_query[row["query"]].append(row)
    never = [q for q, items in by_query.items() if not any(r["mentioned"] or r["cited"] for r in items)]
    competitors = Counter(c for r in rows for c in split_list(r.get("competitors_mentioned")))
    cited_urls = Counter((r.get("cited_url") or "").strip() for r in rows if (r.get("cited_url") or "").strip())
    mentions = [r for r in rows if r["mentioned"]]
    uncited = sum(1 for r in mentions if not r["cited"])
    report = {"observations": len(rows), "queries": len(by_query), "overall": rates(rows),
              "by_engine": engines, "queries_never_visible": never, "competitor_mentions": competitors.most_common(15),
              "most_cited_urls": cited_urls.most_common(15),
              "mentioned_not_cited": {"hits": uncited, "of_mentions": len(mentions), "share": rate(uncited, len(mentions))}}
    brand = brand_domain.lower().removeprefix("www.") if brand_domain else None
    if brand:
        report["cited_urls_off_brand"] = [u for u, _ in cited_urls.most_common() if not is_own(registrable_host(u), brand)][:15]
    if rows and all(r.get("lang") and r.get("prompt_class") for r in rows):
        segments = defaultdict(list)
        for row in rows:
            segments[f"{row['engine'].strip().lower()}|{row['lang']}|{row['prompt_class']}"].append(row)
        report["by_segment"] = {segment: rates(items) for segment, items in sorted(segments.items())}
    if competitors:
        report["share_of_voice"] = {"overall": share_of_voice(rows),
                                    "by_engine": {engine: share_of_voice(items) for engine, items in sorted(by_engine.items())}}
    if any("cited_domains" in r for r in rows):
        gap = Counter(domain for r in rows if not r["mentioned"] and split_list(r.get("competitors_mentioned"))
                      for domain in set(split_list(r.get("cited_domains"))) if not is_own(domain, brand))
        report["citation_source_gap"] = gap.most_common(15)
    if any(r.get("surface") == "api" for r in rows):
        report["engines_are"] = ("API stand-ins for the consumer apps (ai_probe.py), not the apps; read the engine's "
                                 "model_id and tool_version per row")
    return report


def engines_of(rows: list[dict]) -> set[str]:
    return {r["engine"].strip().lower() for r in rows}


def check_same_prompt_set(now_rows: list[dict], before_rows: list[dict]) -> None:
    now = {r["prompt_set"] for r in now_rows if r.get("prompt_set")}
    before = {r["prompt_set"] for r in before_rows if r.get("prompt_set")}
    if now and before and now != before:
        raise SystemExit(f"the two files come from different prompt sets ({', '.join(sorted(now))} against "
                         f"{', '.join(sorted(before))}); compare only runs of one frozen set")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--brand-domain")
    ap.add_argument("--compare", help="earlier observations CSV with the same frozen query set")
    args = ap.parse_args()
    now_rows = load(args.csv)
    current = summarize(now_rows, args.brand_domain)
    if args.compare:
        before_rows = load(args.compare)
        check_same_prompt_set(now_rows, before_rows)
        earlier = summarize(before_rows, args.brand_domain)
        # Only engines both runs used: an engine added or dropped would read as a change in visibility.
        common = engines_of(now_rows) & engines_of(before_rows)
        now_same = [r for r in now_rows if r["engine"].strip().lower() in common]
        before_same = [r for r in before_rows if r["engine"].strip().lower() in common]
        diffs = {metric: difference_ci(sum(r[field] for r in now_same), len(now_same), sum(r[field] for r in before_same), len(before_same))
                 for metric, field in (("mention_rate", "mentioned"), ("citation_rate", "cited"))}
        current["comparison"] = {"engines_compared": sorted(common), "earlier_overall": earlier["overall"],
                                 "change_now_minus_before": diffs,
                                 "note": "A change is detectable only when the CI for the difference excludes 0. Overlapping per-period "
                                         "intervals do NOT rule a change out. Either way, report it as observational drift, never as caused by an action."}
    print_json(current)
    return 0


if __name__ == "__main__":
    sys.exit(main())
