#!/usr/bin/env python3
"""Find opportunities in a Google Search Console (or Bing Webmaster) performance export.

Accepts the UI export (Queries.csv / Pages.csv) or an API/Looker export with query + page columns.
Usage:
  gsc_analyze.py Queries.csv --brand "acme|acme corp"
  gsc_analyze.py query_page.csv                          # query+page rows -> cannibalization check
  gsc_analyze.py last_28d.csv --compare previous_28d.csv # what lost clicks, and why
Outputs JSON: striking-distance keywords, CTR under-performers (against this site's own CTR curve),
question queries, brand split, cannibalization, and period-over-period movers with a cause.
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from collections import defaultdict

from seo_lib import print_json

COLUMN_ALIASES = {
    "query": {"query", "queries", "top queries", "search query", "keyword"},
    "page": {"page", "pages", "top pages", "url", "landing page", "address"},
    "clicks": {"clicks", "url clicks"},
    "impressions": {"impressions"},
    "ctr": {"ctr", "url ctr"},
    "position": {"position", "average position", "avg. position", "avg position"},
}
# Fallback CTR by rounded position when the site has too little data of its own (conservative blend of public studies).
DEFAULT_CTR = {1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018}
MIN_ROWS_FOR_OWN_CURVE = 5
QUESTION = re.compile(r"^(how|what|why|when|where|who|which|can|is|are|does|do|should|will)\b", re.I)


def _number(value: str) -> float:
    value = (value or "").strip().replace(",", "")
    if value.endswith("%"):
        return float(value[:-1]) / 100
    return float(value) if value else 0.0


def load_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        mapping = {}
        for header in reader.fieldnames or []:
            for canonical, aliases in COLUMN_ALIASES.items():
                if header.strip().lower() in aliases:
                    mapping[header] = canonical
        missing = {"clicks", "impressions", "position"} - set(mapping.values())
        if missing:
            raise SystemExit(f"{path}: missing columns {sorted(missing)}; found {reader.fieldnames}")
        if not {"query", "page"} & set(mapping.values()):
            raise SystemExit(f"{path}: no query or page column (found {reader.fieldnames}); a Countries/Devices/Dates "
                             "export cannot be analysed. Export Queries.csv or Pages.csv, or a query+page API export.")
        rows = []
        for raw in reader:
            row = {canonical: raw[header] for header, canonical in mapping.items()}
            for key in ("clicks", "impressions", "ctr", "position"):
                if key in row:
                    row[key] = _number(row[key])
            if "ctr" not in row:
                row["ctr"] = row["clicks"] / row["impressions"] if row["impressions"] else 0.0
            rows.append(row)
    return merge_split_rows(rows)


def key_of(row: dict) -> str:
    return " | ".join(row[k] for k in ("query", "page") if k in row)


def merge_split_rows(rows: list[dict]) -> list[dict]:
    """API/Looker exports with a date, device or country column split one query+page over several rows: sum them back."""
    groups = defaultdict(list)
    for row in rows:
        groups[key_of(row)].append(row)
    merged = []
    for items in groups.values():
        if len(items) == 1:
            merged.append(items[0])
            continue
        clicks = sum(r["clicks"] for r in items)
        impressions = sum(r["impressions"] for r in items)
        merged.append({**items[0], "clicks": clicks, "impressions": impressions, "ctr": clicks / impressions,
                       "position": sum(r["position"] * r["impressions"] for r in items) / impressions})
    return merged


def ctr_curve(rows: list[dict]) -> dict[int, float]:
    buckets = defaultdict(list)
    for row in rows:
        if row["impressions"] >= 20:
            buckets[max(1, round(row["position"]))].append(row["ctr"])
    curve = dict(DEFAULT_CTR)
    for pos, ctrs in buckets.items():
        if len(ctrs) >= MIN_ROWS_FOR_OWN_CURVE:
            curve[pos] = statistics.median(ctrs)
    return curve


def expected_ctr(curve: dict[int, float], position: float) -> float:
    return curve.get(max(1, round(position)), 0.01)


def striking_distance(rows, curve, low: float, high: float, min_impressions: int, target_position: int = 3):
    out = []
    for row in rows:
        if low <= row["position"] <= high and row["impressions"] >= min_impressions:
            gain = row["impressions"] * (expected_ctr(curve, target_position) - row["ctr"])
            out.append({**_view(row), "est_extra_clicks_at_pos3": round(max(gain, 0))})
    return sorted(out, key=lambda r: -r["est_extra_clicks_at_pos3"])[:50]


def ctr_underperformers(rows, curve, min_impressions: int):
    out = []
    for row in rows:
        if row["position"] <= 10 and row["impressions"] >= min_impressions:
            expected = expected_ctr(curve, row["position"])
            if row["ctr"] < expected * 0.5:
                out.append({**_view(row), "expected_ctr": round(expected, 4),
                            "missed_clicks": round(row["impressions"] * (expected - row["ctr"]))})
    return sorted(out, key=lambda r: -r["missed_clicks"])[:50]


def cannibalization(rows):
    by_query = defaultdict(list)
    for row in rows:
        by_query[row["query"]].append(row)
    out = []
    for query, items in by_query.items():
        total = sum(r["impressions"] for r in items)
        contenders = [r for r in items if total and r["impressions"] / total >= 0.1]
        if len(contenders) > 1 and total >= 100:
            out.append({"query": query, "impressions": total,
                        "pages": [{"page": r["page"], "share": round(r["impressions"] / total, 2), "position": round(r["position"], 1),
                                   "clicks": r["clicks"]} for r in sorted(contenders, key=lambda r: -r["impressions"])]})
    return sorted(out, key=lambda r: -r["impressions"])[:30]


def compare(current, previous):
    prev = {key_of(r): r for r in previous}
    movers = []
    for row in current:
        old = prev.get(key_of(row))
        if not old:
            continue
        delta = row["clicks"] - old["clicks"]
        if abs(delta) < 5:
            continue
        similar_rank = abs(row["position"] - old["position"]) < 1
        if delta > 0:
            cause = None  # the causes below explain losses only
        elif row["position"] - old["position"] >= 1:
            cause = "rankings dropped"
        elif similar_rank and old["impressions"] and row["impressions"] / old["impressions"] < 0.8:
            cause = "fewer impressions at similar rank (demand/seasonality, SERP feature or AI Overview taking space)"
        elif similar_rank and old["ctr"] and row["ctr"] / old["ctr"] < 0.8:
            cause = "CTR fell at similar rank (snippet change, new SERP feature/AI Overview, competitor rich result)"
        else:
            cause = "mixed"
        movers.append({"key": key_of(row), "clicks_now": row["clicks"], "clicks_before": old["clicks"], "delta": delta,
                       "position_now": round(row["position"], 1), "position_before": round(old["position"], 1),
                       "impressions_now": row["impressions"], "impressions_before": old["impressions"], "likely_cause": cause})
    lost_keys = [k for k in prev if k not in {key_of(r) for r in current}]
    return {
        "clicks_now": sum(r["clicks"] for r in current), "clicks_before": sum(r["clicks"] for r in previous),
        "losers": sorted([m for m in movers if m["delta"] < 0], key=lambda m: m["delta"])[:30],
        "winners": sorted([m for m in movers if m["delta"] > 0], key=lambda m: -m["delta"])[:15],
        "disappeared": [{"key": k, "clicks_before": prev[k]["clicks"]} for k in sorted(lost_keys, key=lambda k: -prev[k]["clicks"])[:20]],
    }


def _view(row: dict) -> dict:
    return {**{k: row[k] for k in ("query", "page") if k in row}, "clicks": row["clicks"], "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4), "position": round(row["position"], 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--compare", help="previous-period export with the same columns")
    ap.add_argument("--brand", help="regex matching branded queries")
    ap.add_argument("--min-impressions", type=int, default=50)
    ap.add_argument("--striking-from", type=float, default=4)
    ap.add_argument("--striking-to", type=float, default=20)
    args = ap.parse_args()

    rows = load_rows(args.csv)
    curve = ctr_curve(rows)
    report = {
        "rows": len(rows), "clicks": sum(r["clicks"] for r in rows), "impressions": sum(r["impressions"] for r in rows),
        "ctr_curve_used": {p: round(c, 4) for p, c in sorted(curve.items())},
        "striking_distance": striking_distance(rows, curve, args.striking_from, args.striking_to, args.min_impressions),
        "ctr_underperformers": ctr_underperformers(rows, curve, args.min_impressions),
    }
    if any("query" in r for r in rows):
        report["question_queries"] = [_view(r) for r in sorted(rows, key=lambda r: -r["impressions"]) if QUESTION.match(r["query"])][:40]
        if args.brand:
            brand = re.compile(args.brand, re.I)
            branded = [r for r in rows if brand.search(r["query"])]
            report["brand_split"] = {"branded_clicks": sum(r["clicks"] for r in branded),
                                     "non_branded_clicks": sum(r["clicks"] for r in rows) - sum(r["clicks"] for r in branded)}
        if all("page" in r for r in rows):
            report["cannibalization"] = cannibalization(rows)
    if args.compare:
        report["period_comparison"] = compare(rows, load_rows(args.compare))
    print_json(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
