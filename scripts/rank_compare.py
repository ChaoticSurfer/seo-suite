#!/usr/bin/env python3
"""Rank alerts and change impact: did the pages we changed move, measured against unchanged control pages?

Usage (files oldest first: the baseline, then +14 days, then +28 days):
  rank_compare.py snapshots BASE.snapshot.json NEXT.snapshot.json [...] [--changed urls.txt] [--controls urls.txt]
  rank_compare.py gsc base.csv next.csv [...] [--changed urls.txt] [--controls urls.txt]
snapshots: rank_snapshot.py snapshots of one keyword-set version. gsc: Search Console Pages exports (or query+page
exports) of equal windows aligned on weekdays, with the last 2-3 days left out.
Alerts, judgement thresholds rather than a Google or vendor rule: a move of 3+ positions held over the last 2 runs;
entering or leaving the top 3 or top 10 between the last two runs; an AI Overview citation gained or lost. A move seen
once is listed as pending until the next run confirms it.
Change impact (with --changed): the changed group's change minus the control group's, from the first file to the
last. Snapshots compare positions; Search Console compares clicks and impressions, which decide. Report it as
"coincides with", never "caused". --changed and --controls are text files with one URL per line (# starts a comment).
Without --controls, every other page we rank with (snapshots) or every other page in the exports (gsc) is a control.
Output is JSON on stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from gsc_analyze import load_rows
from rank_snapshot import GSC_LABEL
from seo_lib import normalize_url, print_json
from serp_cluster import _key as page_key

MOVE_POSITIONS = 3
HELD_RUNS = 2
LINES = (3, 10)
MIN_GROUP_KEYS = 3
MIN_CHANGED_CLICKS = 50
POSITION_MARGIN = 3.0
CLICKS_MARGIN_PCT = 10.0
THRESHOLDS = {"move_positions": MOVE_POSITIONS, "held_runs": HELD_RUNS, "lines": list(LINES),
              "min_keys_per_group": MIN_GROUP_KEYS, "min_changed_clicks_before": MIN_CHANGED_CLICKS,
              "position_margin": POSITION_MARGIN, "clicks_margin_pct": CLICKS_MARGIN_PCT,
              "basis": "judgement, not a Google or vendor rule: tune them per site"}
SAME_SET = ("set_version", "site", "location_code", "language_code", "device", "depth", "ai_overview", "competitors")
NOTE = ("Observational: a difference against controls coincides with the change; it doesn't prove the change caused "
        "it. Google updates, seasonality and SERP features move both groups.")


def read_json(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"{path}: file not found") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: not valid JSON ({exc})") from None


def read_url_list(path: str) -> set[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            urls = [line.strip() for line in fh if line.strip() and not line.lstrip().startswith("#")]
    except FileNotFoundError:
        raise SystemExit(f"{path}: file not found") from None
    if not urls:
        raise SystemExit(f"{path}: no URLs (one per line)")
    return {page_key(url) for url in urls}


def check_snapshots(snapshots: list[dict], names: list[str]) -> list[dict]:
    """Snapshots compare only within one keyword-set version and its conditions."""
    first = snapshots[0]["meta"]
    for snapshot, name in zip(snapshots[1:], names[1:]):
        differ = [f"{key} {snapshot['meta'].get(key)!r}" for key in SAME_SET if snapshot["meta"].get(key) != first.get(key)]
        if differ:
            raise SystemExit(f"{name}: {', '.join(differ)} differs from {names[0]}; compare only snapshots of one "
                             f"keyword-set version")
    return snapshots


def not_ranked_position(depth: int) -> int:
    """Where a keyword outside the snapshot's depth counts in the maths: one past the last position checked."""
    return depth + 1


def snapshot_runs(snapshots: list[dict]) -> list[dict[str, dict]]:
    return [{row["keyword"]: {"position": row["position"], "url": row.get("url"), "ai_overview": row["ai_overview"],
                              "ai_cited": row["ai_overview_cited"]}
             for row in snapshot["rows"] if "error" not in row} for snapshot in snapshots]


def gsc_runs(paths: list[str]) -> list[dict[str, dict]]:
    """Per page: clicks, impressions and the impression-weighted position, from each export."""
    runs = []
    for path in paths:
        rows = load_rows(path)
        if not all("page" in row for row in rows):
            raise SystemExit(f"{path}: no page column; change impact needs Pages.csv or a query+page export")
        pages = defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0, "weighted": 0.0})
        for row in rows:
            page = pages[normalize_url(row["page"])]
            page["clicks"] += row["clicks"]
            page["impressions"] += row["impressions"]
            page["weighted"] += row["position"] * row["impressions"]
        runs.append({url: {"url": url, "clicks": round(v["clicks"]), "impressions": round(v["impressions"]),
                           "position": round(v["weighted"] / v["impressions"], 1) if v["impressions"] else None}
                     for url, v in pages.items()})
    return runs


def alert(key: str, kind: str, before, now) -> dict:
    return {"key": key, "alert": kind, "from": before, "to": now}


def alerts(runs: list[dict[str, dict]], not_ranked: int | None) -> dict:
    """not_ranked: the position a snapshot's unranked keyword counts as; None for Search Console (skip the key)."""
    def position(obs: dict):
        return obs["position"] if obs["position"] is not None else not_ranked

    last, previous = runs[-1], runs[-2]
    base = runs[-1 - HELD_RUNS] if len(runs) > HELD_RUNS else None
    found, pending = [], []
    for key in sorted(set(last) & set(previous)):
        now_obs, before_obs = last[key], previous[key]
        now, before = position(now_obs), position(before_obs)
        if now is None or before is None:
            continue
        held = False
        if base is not None and key in base and position(base[key]) is not None:
            start = position(base[key])
            moves = (before - start, now - start)
            if all(move <= -MOVE_POSITIONS for move in moves):
                found.append(alert(key, "moved_up", base[key]["position"], now_obs["position"]))
                held = True
            elif all(move >= MOVE_POSITIONS for move in moves):
                found.append(alert(key, "moved_down", base[key]["position"], now_obs["position"]))
                held = True
        if not held and abs(now - before) >= MOVE_POSITIONS:
            pending.append(alert(key, "pending_move", before_obs["position"], now_obs["position"]))
        for line in LINES:
            if before > line >= now:
                found.append(alert(key, f"entered_top_{line}", before_obs["position"], now_obs["position"]))
            elif now > line >= before:
                found.append(alert(key, f"left_top_{line}", before_obs["position"], now_obs["position"]))
        if "ai_cited" in now_obs:
            if now_obs["ai_cited"] != before_obs["ai_cited"]:
                kind = "ai_citation_gained" if now_obs["ai_cited"] else "ai_citation_lost"
                found.append(alert(key, kind, before_obs["ai_cited"], now_obs["ai_cited"]))
            if now_obs["ai_overview"] != before_obs["ai_overview"]:
                kind = "ai_overview_appeared" if now_obs["ai_overview"] else "ai_overview_gone"
                found.append(alert(key, kind, before_obs["ai_overview"], now_obs["ai_overview"]))
    return {"thresholds": THRESHOLDS, "alerts": found, "pending": pending}


def split_groups(first: dict, last: dict, changed: set[str], controls: set[str] | None) -> tuple[list, list]:
    keys = sorted(set(first) & set(last))

    def pages(key: str) -> set[str]:
        return {page_key(obs["url"]) for obs in (first[key], last[key]) if obs.get("url")}

    changed_keys = [key for key in keys if pages(key) & changed]
    if controls:
        control_keys = [key for key in keys if pages(key) & controls and key not in changed_keys]
    else:
        control_keys = [key for key in keys if pages(key) and key not in changed_keys]
    return changed_keys, control_keys


def impact(first: dict, last: dict, changed: set[str], controls: set[str] | None, not_ranked: int) -> dict:
    """Snapshots: mean positions gained by the changed keywords minus those gained by the control keywords."""
    changed_keys, control_keys = split_groups(first, last, changed, controls)

    def position(obs: dict) -> int:
        return obs["position"] if obs["position"] is not None else not_ranked

    def group(keys: list[str]) -> dict:
        if not keys:
            return {"keys": 0, "positions_gained": None}
        before = sum(position(first[key]) for key in keys) / len(keys)
        after = sum(position(last[key]) for key in keys) / len(keys)
        return {"keys": len(keys), "mean_position_before": round(before, 1), "mean_position_after": round(after, 1),
                "positions_gained": round(before - after, 1), "examples": keys[:10]}

    result = {"changed": group(changed_keys), "control": group(control_keys)}
    if min(len(changed_keys), len(control_keys)) < MIN_GROUP_KEYS:
        result["verdict"] = f"inconclusive: fewer than {MIN_GROUP_KEYS} keywords in a group"
        return result
    difference = round(result["changed"]["positions_gained"] - result["control"]["positions_gained"], 1)
    result["difference"] = {"positions_gained": difference}
    result["verdict"] = ("ahead of controls" if difference >= POSITION_MARGIN else
                         "behind controls" if difference <= -POSITION_MARGIN else "no clear difference")
    return result


def change_pct(before: float, after: float) -> float | None:
    return round((after - before) / before * 100, 1) if before else None


def gsc_impact(first: dict, last: dict, changed: set[str], controls: set[str] | None) -> dict:
    """Search Console: clicks and impressions of the changed pages against the control pages."""
    changed_keys, control_keys = split_groups(first, last, changed, controls)

    def group(keys: list[str]) -> dict:
        clicks = (sum(first[k]["clicks"] for k in keys), sum(last[k]["clicks"] for k in keys))
        impressions = (sum(first[k]["impressions"] for k in keys), sum(last[k]["impressions"] for k in keys))
        return {"pages": len(keys), "clicks_before": clicks[0], "clicks_after": clicks[1],
                "clicks_change_pct": change_pct(*clicks), "impressions_before": impressions[0],
                "impressions_after": impressions[1], "impressions_change_pct": change_pct(*impressions),
                "examples": keys[:10]}

    result = {"changed": group(changed_keys), "control": group(control_keys)}
    if not changed_keys or not control_keys:
        result["verdict"] = "inconclusive: a group has no page present in both the first and last export"
        return result
    if result["changed"]["clicks_before"] < MIN_CHANGED_CLICKS:
        result["verdict"] = f"inconclusive: the changed pages had fewer than {MIN_CHANGED_CLICKS} clicks before"
        return result
    clicks = round((result["changed"]["clicks_change_pct"] or 0) - (result["control"]["clicks_change_pct"] or 0), 1)
    impressions = round((result["changed"]["impressions_change_pct"] or 0)
                        - (result["control"]["impressions_change_pct"] or 0), 1)
    result["difference"] = {"clicks_change_pct": clicks, "impressions_change_pct": impressions}
    result["verdict"] = ("ahead of controls" if clicks >= CLICKS_MARGIN_PCT and impressions >= 0 else
                         "behind controls" if clicks <= -CLICKS_MARGIN_PCT else "no clear difference")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("snapshots", "gsc"))
    ap.add_argument("files", nargs="+", help="two or more files, oldest first")
    ap.add_argument("--changed", help="text file of the changed URLs, one per line")
    ap.add_argument("--controls", help="text file of the control URLs (default: every other page)")
    args = ap.parse_args()
    if len(args.files) < 2:
        raise SystemExit("give at least two files, oldest first: the baseline and a later run")
    changed = read_url_list(args.changed) if args.changed else None
    controls = read_url_list(args.controls) if args.controls else None
    if args.mode == "snapshots":
        snapshots = check_snapshots([read_json(path) for path in args.files], args.files)
        runs, not_ranked = snapshot_runs(snapshots), not_ranked_position(snapshots[0]["meta"]["depth"])
        labels = [snapshot["meta"]["date"] for snapshot in snapshots]
    else:
        runs, not_ranked, labels = gsc_runs(args.files), None, list(args.files)
    report = {"mode": args.mode, "runs": labels, **alerts(runs, not_ranked), "note": NOTE}
    if args.mode == "gsc":
        report["position_basis"] = GSC_LABEL
    if changed:
        report["change_impact"] = (impact(runs[0], runs[-1], changed, controls, not_ranked) if args.mode == "snapshots"
                                   else gsc_impact(runs[0], runs[-1], changed, controls))
    print_json(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
