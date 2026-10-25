#!/usr/bin/env python3
"""Measure a page's content against a target keyword: placement, readability, structure,
answer-readiness for AI/featured snippets, and trust (E-E-A-T) signals visible in the HTML.

These are measurable proxies, not a ranking score. Judge quality and intent match yourself.
Usage:
  content_score.py https://example.com/post --keyword "core web vitals"
  content_score.py --file draft.html --keyword "..."      # score a draft before publishing
  content_score.py --file blog_posts.csv --key SLUG --fields title,excerpt,content --base-url URL --keyword "..."
                                                          # a post kept as data: a JSON, CSV or TSV entry
Outputs JSON: placement checks, readability, structure, trust signals, top phrases.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from collections import Counter

from schema_rules import iter_typed_nodes, node_types
from seo_lib import PageFacts, content_fields, extract_page, fetch, is_content_file, load_draft_file, print_json

STOPWORDS = set("""a an the and or but if then of to in on at by for with from as is are was were be been being it its this that
these those you your we our they their he she his her i me my not no do does did can could will would should may might
have has had so than too very just also more most such into over about out up down what which who when where why how all any
each other some only own same both few""".split())
ANSWER_PARAGRAPH_WORDS = (40, 80)  # concise, self-contained passages are what snippets and AI answers lift


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 3]


def syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups) - (1 if word.endswith("e") and len(groups) > 1 else 0)
    return max(count, 1)


def flesch_reading_ease(text: str) -> float | None:
    sents = sentences(text)
    words = re.findall(r"[A-Za-z]+", " ".join(sents))  # only words inside the sentences being counted
    if len(words) < 100 or not sents:
        return None
    return round(206.835 - 1.015 * (len(words) / len(sents)) - 84.6 * (sum(map(syllables, words)) / len(words)), 1)


def ngrams(text: str, n: int) -> list[str]:
    """Word n-grams that never cross punctuation, so 'speed, performance' is not a phrase."""
    grams = []
    for chunk in re.split(r"[.!?,;:()\[\]\"“”|/]+", text.lower()):
        tokens = re.findall(r"\w[\w'-]*", chunk)
        grams += [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)
                  if tokens[i] not in STOPWORDS and tokens[i + n - 1] not in STOPWORDS
                  and not any(t.isdigit() for t in tokens[i:i + n])]
    return grams


def top_phrases(text: str, n: int, limit: int = 25) -> list[tuple[str, int]]:
    return Counter(ngrams(text, n)).most_common(limit)


def keyword_pattern(keyword: str) -> re.Pattern:
    """Whole-word, case-insensitive match so 'ai' does not match inside 'maintain'."""
    return re.compile(r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)")


def contains(haystack: str, keyword: str) -> bool:
    return bool(keyword_pattern(keyword).search(haystack.lower()))


def body_text(f: PageFacts) -> str:
    """Paragraph copy when the page has <p> text; otherwise all visible text (which includes nav/footer)."""
    return " ".join(f.paragraphs) or f.visible_text


def keyword_placement(f: PageFacts, keyword: str) -> dict:
    first_100 = " ".join(body_text(f).split()[:100])
    slug = urllib.parse.unquote(urllib.parse.urlsplit(f.final_url).path).replace("-", " ").replace("_", " ")
    occurrences = len(keyword_pattern(keyword).findall(f.visible_text.lower()))
    return {
        "in_title": contains(f.title, keyword), "in_h1": any(contains(t, keyword) for lvl, t in f.headings if lvl == 1),
        "in_first_100_words": contains(first_100, keyword), "in_url": contains(slug, keyword),
        "in_meta_description": contains(f.meta_description, keyword),
        "in_h2_h3": sum(1 for lvl, t in f.headings if lvl in (2, 3) and contains(t, keyword)),
        "exact_occurrences": occurrences,
        "per_1000_words": round(occurrences * 1000 / f.word_count, 1) if f.word_count else 0,
    }


def trust_signals(f: PageFacts) -> dict:
    nodes = [node for _, node in iter_typed_nodes(f.json_ld)]
    has = lambda prop: any(node.get(prop) for node in nodes)
    links = " ".join(l["href"].lower() + " " + l["text"].lower() for l in f.internal_links)
    text = f.visible_text[:5000]
    return {
        "author_in_schema": has("author"), "date_published_in_schema": has("datePublished"),
        "date_modified_in_schema": has("dateModified"),
        "visible_byline": bool(re.search(r"\b(?i:by|written by|author:|reviewed by)\s+[A-Z][a-z]+", text)),
        "visible_updated_date": bool(re.search(r"\b(updated|last updated|published)\b[^.]{0,30}\b(20\d\d)\b", text, re.I)),
        "about_page_linked": "about" in links, "contact_page_linked": "contact" in links,
        "privacy_policy_linked": "privacy" in links,
        "outbound_citations": len([l for l in f.external_links if "nofollow" not in l["rel"]]),
        "organization_or_person_schema": any(t in ("Organization", "Person") for n in nodes for t in node_types(n)),
    }


def structure(f: PageFacts) -> dict:
    lengths = [len(p.split()) for p in f.paragraphs]
    question_headings = [t for lvl, t in f.headings if lvl in (2, 3) and (t.endswith("?") or re.match(r"(how|what|why|when|which|can|is|do|does)\b", t, re.I))]
    low, high = ANSWER_PARAGRAPH_WORDS
    return {
        "word_count": f.word_count, "headings": [f"h{lvl}: {t}" for lvl, t in f.headings][:40],
        "question_headings": question_headings, "paragraphs": len(lengths),
        "avg_paragraph_words": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "long_paragraphs_over_150_words": sum(1 for n in lengths if n > 150),
        "answer_sized_paragraphs": sum(1 for n in lengths if low <= n <= high),
        "first_paragraph_words": lengths[0] if lengths else 0, "lists": f.list_count, "tables": f.table_count,
        "images": len(f.images),
    }


def score_page(f: PageFacts, keyword: str | None) -> dict:
    body = body_text(f)
    sents = sentences(body)
    report = {
        "url": f.final_url, "status": f.status, "title": f.title,
        "readability": {"flesch_reading_ease": flesch_reading_ease(body),
                        "avg_sentence_words": round(sum(len(s.split()) for s in sents) / len(sents), 1) if sents else None,
                        "note": "Flesch is English-only; 60–70 is plain English. Match the audience, not a number."},
        "structure": structure(f), "trust_signals": trust_signals(f),
        "top_bigrams": top_phrases(f.visible_text, 2), "top_trigrams": top_phrases(f.visible_text, 3, 15),
    }
    if keyword:
        report["keyword"] = keyword
        report["placement"] = keyword_placement(f, keyword)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--key", help="with a JSON, CSV or TSV --file: the post's entry (its slug, or a dotted key)")
    ap.add_argument("--fields", type=content_fields, help="with --key: the fields to read, e.g. title,excerpt,content")
    ap.add_argument("--base-url", default="https://localhost/")
    ap.add_argument("--keyword")
    args = ap.parse_args()
    if not args.url and not args.file:
        ap.error("give a URL or --file")
    if (args.key or args.fields) and not (args.file and is_content_file(args.file)):
        ap.error("--key and --fields pick an entry of a JSON, CSV or TSV --file")
    try:
        result = load_draft_file(args.file, args.base_url, args.key, args.fields) if args.file else fetch(args.url)
    except ValueError as err:
        ap.error(str(err))
    if result.error:
        print_json({"url": args.url, "error": result.error})
        return 2
    if result.status >= 400:
        print_json({"url": result.final_url, "status": result.status,
                    "error": f"HTTP {result.status} — not scoring an error page (check page_audit for bot challenges)"})
        return 2
    print_json(score_page(extract_page(result), args.keyword))
    return 0


if __name__ == "__main__":
    sys.exit(main())
