"""causal_claims.py: flags report sentences that pair a metric movement with a causal claim ("caused", "due to",
"rose after"). Changes "coincide with" metric moves unless a controlled test showed the cause.
The first sentences are the probe that showed SEO-AEO-GEO Ultimate's regexes misfire on real report text.
Run: python3 -m unittest discover -s tests
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "causal_claims.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from causal_claims import is_causal_claim  # noqa: E402

CAUSAL = [
    "The optimization caused traffic growth.",
    "Clicks rose due to the title change.",
    "The title rewrite boosted CTR by 40%.",
    "Mentions rose after we added FAQ schema.",
    "The new schema made citations jump.",
    "Traffic fell after the core update.",
    "Rankings improved thanks to the new internal links.",
    "The redirect fix resulted in 300 more impressions a day.",
]
NOT_CAUSAL = [
    "Data is partial because of GSC sampling.",
    "Access gaps due to rate limiting on Perplexity.",
    "No change in visibility between runs.",
    "This is a point-in-time observational record, not a causal result.",
    "The CTR rise coincides with the title rewrite on 2026-10-02.",
    "In a controlled test (50/50 split), the new titles drove a 12% CTR lift.",
    "Crawl stopped because of a Cloudflare challenge.",
    "There is no evidence the update caused the traffic drop.",
]


class CausalClaimTest(unittest.TestCase):
    def test_causal_claims_about_metrics_are_flagged(self):
        for sentence in CAUSAL:
            with self.subTest(sentence=sentence):
                self.assertTrue(is_causal_claim(sentence))

    def test_limitations_denials_and_controlled_tests_pass(self):
        for sentence in NOT_CAUSAL:
            with self.subTest(sentence=sentence):
                self.assertFalse(is_causal_claim(sentence))

    def run_cli(self, text: str, *flags: str):
        path = os.path.join(tempfile.mkdtemp(), "SEO-WORKLOG.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        proc = subprocess.run([sys.executable, SCRIPT, path, *flags], capture_output=True, text=True, timeout=30)
        return proc, json.loads(proc.stdout)

    def test_the_cli_names_file_line_and_sentence_and_exits_1(self):
        text = ("# Report\n\n- **Key findings:**\n  - Clicks rose due to the title change. The sitemap is valid.\n"
                "```\nTraffic fell after the core update.\n```\n> Traffic fell after the core update, a blog says.\n")
        proc, report = self.run_cli(text)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(report["count"], 1, "code blocks and quotes are other people's words")
        (claim,) = report["claims"]
        self.assertEqual((claim["line"], claim["sentence"]), (4, "Clicks rose due to the title change."))

    def test_newest_entry_checks_only_the_top_entry_of_the_work_log(self):
        log = ("# SEO work log\n\n## 2026-10-25 — Re-check\n\n- **Key findings:** The CTR rise coincides with the "
               "title rewrite.\n\n## 2026-10-01 — Audit\n\n- **Key findings:** Traffic fell after the core update.\n")
        proc, report = self.run_cli(log, "--newest-entry")
        self.assertEqual((proc.returncode, report["count"]), (0, 0))
        proc, report = self.run_cli(log)
        self.assertEqual((proc.returncode, report["count"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
