#!/usr/bin/env python3
"""Cluster keywords by shared ranking URLs (SERP overlap) — the deterministic half of keyword clustering.

Input JSON: {"keyword": ["https://top1", "https://top2", ...up to 10], ...} — collect it with WebSearch
(e.g. via parallel seo-serp-researcher agents) or export it from Semrush/Ahrefs/DataForSEO.
Usage:
  serp_cluster.py serps.json [--same-page 4] [--interlink 2]
Rules (heuristic, widely used): ≥4 shared top-10 URLs → target with ONE page; 2–3 shared → separate pages that
interlink; <2 → unrelated. Clusters are connected components of the "same page" graph.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse

from seo_lib import normalize_url, print_json


def _key(url: str) -> str:
    parts = urllib.parse.urlsplit(normalize_url(url))
    query = f"?{parts.query}" if parts.query else ""  # watch?v=…, viewtopic.php?t=… are distinct results
    return f"{(parts.hostname or '').removeprefix('www.')}{parts.path.rstrip('/')}{query}"


def overlaps(serps: dict[str, list[str]]) -> dict[tuple[str, str], int]:
    sets = {kw: {_key(u) for u in urls[:10]} for kw, urls in serps.items()}
    keywords = list(sets)
    return {(a, b): len(sets[a] & sets[b]) for i, a in enumerate(keywords) for b in keywords[i + 1:]}


def clusters(keywords: list[str], shared: dict[tuple[str, str], int], same_page: int) -> list[list[str]]:
    parent = {kw: kw for kw in keywords}

    def find(kw: str) -> str:
        while parent[kw] != kw:
            parent[kw] = parent[parent[kw]]
            kw = parent[kw]
        return kw

    for (a, b), n in shared.items():
        if n >= same_page:
            parent[find(a)] = find(b)
    groups: dict[str, list[str]] = {}
    for kw in keywords:
        groups.setdefault(find(kw), []).append(kw)
    return sorted(groups.values(), key=lambda g: -len(g))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("serps_json")
    ap.add_argument("--same-page", type=int, default=4, help="shared URLs to merge keywords into one page")
    ap.add_argument("--interlink", type=int, default=2, help="shared URLs to suggest interlinking")
    args = ap.parse_args()
    with open(args.serps_json, encoding="utf-8") as fh:
        serps = json.load(fh)
    shared = overlaps(serps)
    groups = clusters(list(serps), shared, args.same_page)
    cluster_of = {kw: i for i, g in enumerate(groups) for kw in g}
    interlinks = sorted({tuple(sorted((cluster_of[a], cluster_of[b]))) for (a, b), n in shared.items()
                         if args.interlink <= n < args.same_page and cluster_of[a] != cluster_of[b]})
    print_json({
        "keywords": len(serps), "clusters": [{"id": i, "keywords": g} for i, g in enumerate(groups)],
        "interlink_clusters": [{"from": a, "to": b} for a, b in interlinks],
        "note": "Pick each cluster's head term by search volume (needs data) or GSC impressions; one URL per cluster.",
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
