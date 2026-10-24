#!/usr/bin/env python3
"""Verify a migration redirect map: every old URL must 301/308 to its mapped new URL in one hop,
and that new URL must be a 200, indexable, self-canonical page.

Usage:
  redirect_check.py map.csv                 # CSV with columns old,new (header names: old/source/from, new/target/to)
  redirect_check.py map.csv --workers 8
Outputs JSON: totals and every row that fails, with the reason.
"""
from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ThreadPoolExecutor

from seo_lib import Finding, extract_page, fetch, is_indexable, print_json, to_uri

OLD_HEADERS = {"old", "source", "from", "old_url", "source_url"}
NEW_HEADERS = {"new", "target", "to", "new_url", "target_url", "destination"}


def load_map(path: str) -> list[tuple[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = {h.strip().lower(): h for h in reader.fieldnames or []}
        old_col = next((headers[h] for h in headers if h in OLD_HEADERS), None)
        new_col = next((headers[h] for h in headers if h in NEW_HEADERS), None)
        if not old_col or not new_col:
            raise SystemExit(f"need old/new columns, got {reader.fieldnames}")
        # DictReader fills the cells of a short row with None.
        pairs = [((row[old_col] or "").strip(), (row[new_col] or "").strip()) for row in reader]
        return [(old, new) for old, new in pairs if old]


def check(pair: tuple[str, str]) -> dict:
    old, expected = pair
    result = fetch(old)
    facts = extract_page(result)
    problems = [result.error] if result.error else []
    if not facts.redirect_chain:
        problems.append(f"no redirect (HTTP {facts.status})")
    else:
        if len(facts.redirect_chain) > 1:
            problems.append(f"{len(facts.redirect_chain)} hops")
        temporary = [s for _, s in facts.redirect_chain if s in (302, 303, 307)]
        if temporary:
            problems.append(f"temporary redirect {temporary}")
    if not expected:
        problems.append("no new URL in the map")
    elif facts.final_url.rstrip("/") != to_uri(expected).rstrip("/"):  # fetch() returns final_url in to_uri() form
        problems.append(f"lands on {facts.final_url}")
    if facts.status != 200:
        problems.append(f"target HTTP {facts.status}")
    elif not is_indexable(facts):
        problems.append("target is noindex")
    elif facts.canonical and facts.canonical.rstrip("/") != facts.final_url.rstrip("/"):
        problems.append(f"target canonicalizes to {facts.canonical}")
    return {"old": old, "expected": expected, "final": facts.final_url, "status": facts.status,
            "chain": facts.redirect_chain, "problems": problems}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map_csv")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    pairs = load_map(args.map_csv)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(check, pairs))
    failures = [r for r in results if r["problems"]]
    findings = [Finding("redirect-map-failure", "high", f"{len(failures)}/{len(results)} mapped redirects fail",
                        "; ".join(f"{r['old']}: {', '.join(r['problems'])}" for r in failures[:5]))] if failures else []
    print_json({"checked": len(results), "passed": len(results) - len(failures), "failed": len(failures),
                "findings": findings, "failures": failures})
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
