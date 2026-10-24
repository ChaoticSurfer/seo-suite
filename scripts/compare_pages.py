#!/usr/bin/env python3
"""Compare your page with the pages that outrank it: size, structure, schema, trust signals, and the
phrases competitors share that your page never mentions (a content-gap list).

Usage:
  compare_pages.py https://you.com/page https://rival1.com/a https://rival2.com/b --keyword "best crm for startups"
The first URL is yours. Find rivals with a WebSearch for the keyword (top organic results).
For a brief before your page exists, pass only rivals with --no-own-page (returns their shared phrases).
"""
from __future__ import annotations

import argparse
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor

from content_score import ngrams, score_page, top_phrases
from page_audit import summarize
from seo_lib import extract_page, fetch, print_json

MIN_COMPETITORS_SHARING_PHRASE = 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+", help="your URL first, then competitors")
    ap.add_argument("--keyword")
    ap.add_argument("--no-own-page", action="store_true", help="all URLs are competitors (brief for a page that doesn't exist yet)")
    args = ap.parse_args()
    if len(args.urls) < 2:
        ap.error("need at least two URLs")

    with ThreadPoolExecutor(max_workers=6) as pool:
        pages = list(pool.map(lambda u: extract_page(fetch(u)), args.urls))
    rows = []
    for facts in pages:
        score = score_page(facts, args.keyword)
        rows.append({
            "url": facts.final_url, "status": facts.status, **{k: v for k, v in summarize(facts).items() if k in
                                                              ("title", "word_count", "schema_types", "internal_links", "external_links", "images")},
            "headings": len([h for h in facts.headings if h[0] in (2, 3)]), "question_headings": len(score["structure"]["question_headings"]),
            "lists": facts.list_count, "tables": facts.table_count, "flesch": score["readability"]["flesch_reading_ease"],
            "trust": {k: v for k, v in score["trust_signals"].items() if v},
            "placement": score.get("placement"),
        })

    own_pages, rivals = ([], pages) if args.no_own_page else (pages[:1], pages[1:])
    rival_rows = rows if args.no_own_page else rows[1:]
    mine = set(ngrams(own_pages[0].visible_text, 2) + ngrams(own_pages[0].visible_text, 3)) if own_pages else set()
    phrase_sites: dict[str, int] = {}
    for facts in rivals:
        phrases = {p for p, _ in top_phrases(facts.visible_text, 2, 80) + top_phrases(facts.visible_text, 3, 60)}
        for phrase in phrases:
            phrase_sites[phrase] = phrase_sites.get(phrase, 0) + 1
    needed = min(MIN_COMPETITORS_SHARING_PHRASE, len(rivals))
    gap = sorted((p for p, n in phrase_sites.items() if n >= needed and p not in mine),
                 key=lambda p: (-phrase_sites[p], p))  # ties by phrase: set order changes with each run's hash seed
    rival_words = [r["word_count"] for r in rival_rows if r["status"] == 200]
    print_json({
        "keyword": args.keyword, "yours": None if args.no_own_page else rows[0], "competitors": rival_rows,
        "median_competitor_words": statistics.median(rival_words) if rival_words else None,
        # A brief keeps every shared phrase, so a template list from another run can be subtracted from it in full.
        "content_gap_phrases" if own_pages else "shared_competitor_phrases": gap[:60] if own_pages else gap,
        "note": "Gap phrases are subtopics rivals cover and you don't. Add only those that serve the searcher; length is not a ranking factor.",
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
