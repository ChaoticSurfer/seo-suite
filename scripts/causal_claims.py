#!/usr/bin/env python3
"""Flag sentences in reports and SEO-WORKLOG.md that claim a change caused a metric move.

seo-suite's rule: a change "coincides with" a metric move; it "caused" it only when a controlled test showed that.
A sentence is flagged when it names a metric (traffic, clicks, CTR, rankings, mentions, citations ...) and a causal
verb or connective ("caused", "drove", "due to", "thanks to", "boosted", "rose after" ...), unless it says
"coincides with", denies the cause ("no evidence", "cannot be attributed", "not caused") or cites a controlled test.
Limitations without a metric ("partial because of sampling") pass. Code blocks and quotes are skipped: they are other
people's words.

Usage:
  causal_claims.py report.md [more.md ...]       Every sentence of each file.
  causal_claims.py SEO-WORKLOG.md --newest-entry Only the first "## " entry (the log keeps the newest on top).
Prints JSON {files, count, claims: [{file, line, sentence}]}; exit 1 when any sentence is flagged.
"""
from __future__ import annotations

import argparse
import re
import sys

from seo_lib import print_json

CAUSAL_RE = re.compile(
    r"\b(?:caus(?:es|ed|ing)|drove|drives?|driven by|led to|leads? to|result(?:ed|s)? in|because of|due to|thanks to"
    r"|boost(?:ed|s)?|lift(?:ed|s)?|made \w+ (?:jump|rise|grow|fall|drop|climb)"
    r"|(?:rose|fell|dropped|grew|jumped|climbed|declined|increased|decreased|improved|recovered|spiked)"
    r" (?:right |soon |shortly )?(?:after|once|following))\b", re.IGNORECASE)
METRIC_RE = re.compile(
    r"\b(?:traffic|clicks?|impressions?|ctr|rankings?|ranks?|positions?|visibility|mentions?|citations?|conversions?"
    r"|sessions?|revenue|sign-?ups?|referrals?|uplift|share of voice)\b", re.IGNORECASE)
ALLOWED_RE = re.compile(
    r"\b(?:coincid(?:es|ed|ing) with|controlled (?:test|experiment)|a/b test|split test|holdout|no evidence"
    r"|cannot be attributed|can't be attributed|not attributable|not (?:the )?caus\w*)", re.IGNORECASE)
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
MARKDOWN_LEAD_RE = re.compile(r"^\s*(?:[-*+]|\d+\.|#+)\s*")


def is_causal_claim(sentence: str) -> bool:
    return bool(CAUSAL_RE.search(sentence) and METRIC_RE.search(sentence) and not ALLOWED_RE.search(sentence))


def checked_lines(text: str, newest_entry: bool) -> list[tuple[int, str]]:
    """(line number, text) of the prose lines to check: no code blocks or quotes; with newest_entry, the first entry."""
    lines, in_code, entries_seen = [], False, 0
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if line.startswith("## "):
            entries_seen += 1
            if newest_entry and entries_seen > 1:
                break
        if in_code or line.lstrip().startswith(">") or (newest_entry and entries_seen == 0):
            continue
        lines.append((number, MARKDOWN_LEAD_RE.sub("", line)))
    return lines


def causal_claims(text: str, newest_entry: bool = False) -> list[dict]:
    claims = []
    for number, line in checked_lines(text, newest_entry):
        for sentence in SENTENCE_END_RE.split(line.replace("**", "")):
            if is_causal_claim(sentence):
                claims.append({"line": number, "sentence": sentence.strip()})
    return claims


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="Markdown reports or SEO-WORKLOG.md")
    ap.add_argument("--newest-entry", action="store_true", help="check only the first '## ' entry of each file")
    args = ap.parse_args()
    claims = []
    for path in args.files:
        with open(path, encoding="utf-8") as fh:
            claims += [{"file": path, **claim} for claim in causal_claims(fh.read(), args.newest_entry)]
    print_json({"files": args.files, "count": len(claims), "claims": claims})
    return 1 if claims else 0


if __name__ == "__main__":
    sys.exit(main())
