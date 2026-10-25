"""Posts stored as entries of JSON, CSV or TSV content files, read by translation_check.py, ai_text_check.py and
content_score.py through the one reader in seo_lib.py.

Run: python3 -m unittest discover -s tests
The fixtures in tests/fixtures/content/ have the shapes of Geotour's real files, with handmade text and invented ids:
blog_posts.csv and blog_posts.json are a Supabase blog_posts table export (the English rows, TinyMCE HTML in the
content column), blog/ka.json and blog/ru.json are locale translation files keyed by slug (updated_at, title, excerpt,
content), and dictionary-ka.json is a TS dictionary rendered to JSON (MoneyTalks' nested keys). Planted defects in
what-to-eat-in-georgia: an English paragraph left in the Georgian content, the "90 km" dropped from the Russian
content, and the Russian title left in English. tbilisi-sulphur-baths has a model leftover in its English content.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_lib import content_entry_page, extract_page, load_draft_file, read_content_entry  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
CONTENT = os.path.join(os.path.dirname(__file__), "fixtures", "content")
ROWS_CSV = os.path.join(CONTENT, "blog_posts.csv")
ROWS_JSON = os.path.join(CONTENT, "blog_posts.json")
KA = os.path.join(CONTENT, "blog", "ka.json")
RU = os.path.join(CONTENT, "blog", "ru.json")
DICTIONARY_KA = os.path.join(CONTENT, "dictionary-ka.json")
HTML_DRAFT = os.path.join(os.path.dirname(__file__), "fixtures", "blog", "en.html")
FOOD = "what-to-eat-in-georgia"
BATHS = "tbilisi-sulphur-baths"
POST_FIELDS = "title,excerpt,content"
URL = "https://geotour.test/blog/what-to-eat-in-georgia/"


def run_script(name: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *args], capture_output=True, text=True,
                          timeout=60)


def by_id(findings, finding_id):
    return [f for f in findings if f["id"] == finding_id]


class ContentEntryReaderTest(unittest.TestCase):
    def test_a_locale_translation_file_entry_by_slug(self):
        entry = read_content_entry(KA, FOOD)
        self.assertEqual(entry["title"], "რა ვჭამოთ საქართველოში: 15 კერძი")
        self.assertEqual(read_content_entry(RU, BATHS)["title"], "Серные бани Тбилиси: какую выбрать")

    def test_a_rendered_ts_dictionary_by_dotted_key(self):
        self.assertTrue(read_content_entry(DICTIONARY_KA, "seo.home")["title"].startswith("ორიგინალური საჩუქრები"))
        page = content_entry_page(read_content_entry(DICTIONARY_KA, "design"), ["customBody"], "dictionary design")
        self.assertEqual(page.count("<p>"), 2, "plain text is split into paragraphs at blank lines")
        listed = content_entry_page(read_content_entry(DICTIONARY_KA, "seo"), ["keywords"], "dictionary seo")
        self.assertIn("<li>საჩუქარი</li><li>ჩარჩო</li>", listed)

    def test_a_supabase_rows_export_by_slug_csv_and_json(self):
        for path in (ROWS_CSV, ROWS_JSON):
            with self.subTest(export=os.path.basename(path)):
                entry = read_content_entry(path, BATHS)
                self.assertEqual(entry["title"], "Tbilisi Sulphur Baths: Which One to Choose")
                self.assertIn("</p>\n<h2>Which bath to choose</h2>", entry["content"], "the HTML keeps its newlines")

    def test_errors_name_the_file_and_what_is_wrong(self):
        with self.assertRaisesRegex(ValueError, r"ka\.json.*'no-such-post'"):
            read_content_entry(KA, "no-such-post")
        with self.assertRaisesRegex(ValueError, r"blog_posts\.csv.*no row with slug 'no-such-post'"):
            read_content_entry(ROWS_CSV, "no-such-post")
        with tempfile.TemporaryDirectory() as tmp:
            twice = os.path.join(tmp, "rows.csv")
            with open(twice, "w", encoding="utf-8") as fh:
                fh.write("slug,title\na,One\na,Two\n")
            with self.assertRaisesRegex(ValueError, "2 rows with slug 'a'"):
                read_content_entry(twice, "a")
            no_slug = os.path.join(tmp, "titles.csv")
            with open(no_slug, "w", encoding="utf-8") as fh:
                fh.write("id,title\n1,One\n")
            with self.assertRaisesRegex(ValueError, "no slug column"):
                read_content_entry(no_slug, "1")
            mixed = os.path.join(tmp, "rows.json")
            with open(mixed, "w", encoding="utf-8") as fh:
                json.dump([{"slug": "a", "title": "One"}, "a"], fh)
            with self.assertRaisesRegex(ValueError, "only objects"):
                read_content_entry(mixed, "a")
        with self.assertRaisesRegex(ValueError, r"must be an object"):
            read_content_entry(KA, f"{FOOD}.title")  # a text, not an entry with fields
        entry = read_content_entry(KA, FOOD)
        with self.assertRaisesRegex(ValueError, r"ka what-to-eat-in-georgia has no field 'meta'"):
            content_entry_page(entry, ["title", "meta"], "ka what-to-eat-in-georgia")
        with self.assertRaisesRegex(ValueError, r"dictionary seo field 'home' must be text, not dict"):
            content_entry_page(read_content_entry(DICTIONARY_KA, "seo"), ["home"], "dictionary seo")

    def test_the_entry_becomes_the_page_a_blog_template_renders(self):
        result = load_draft_file(ROWS_CSV, URL, FOOD, POST_FIELDS.split(","))
        facts = extract_page(result)
        self.assertEqual((result.status, facts.final_url), (200, URL))
        self.assertEqual(facts.title, "What to Eat in Georgia: 15 Dishes")
        self.assertTrue(facts.meta_description.startswith("Khinkali, three kinds of khachapuri"))
        self.assertEqual(facts.headings[:3], [(1, "What to Eat in Georgia: 15 Dishes"), (2, "Bread and dumplings"),
                                              (3, "1. Khinkali")])
        self.assertIn('"the one everyone photographs"', facts.visible_text)

    def test_html_drafts_load_as_before_and_content_files_need_key_and_fields(self):
        self.assertEqual(load_draft_file(HTML_DRAFT, URL).status, 200)
        with self.assertRaisesRegex(ValueError, "--key and --fields"):
            load_draft_file(KA, URL)
        with self.assertRaisesRegex(ValueError, "--key and --fields"):
            load_draft_file(KA, URL, FOOD, None)


class ContentFileCliTest(unittest.TestCase):
    def test_translation_check_compares_the_db_row_with_the_locale_json(self):
        result = run_script("translation_check.py", "--files", f"en:{ROWS_CSV}", f"ka:{KA}", f"ru:{RU}",
                            "--key", FOOD, "--fields", POST_FIELDS, "--source", "en",
                            "--base-url", "https://geotour.test/{lang}/blog/what-to-eat-in-georgia/")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["source"], "en")
        self.assertEqual([v["detected_language"] for v in report["cluster"]], ["en", "ka", "ru"])
        findings = report["findings"]
        left = by_id(findings, "translation-untranslated-block")
        self.assertEqual(len(left), 1)
        self.assertIn("/ka/", left[0]["message"])
        self.assertIn("How to eat them", left[0]["evidence"])
        missing = by_id(findings, "translation-number-missing")
        self.assertEqual([f["evidence"] for f in missing], ["90"])
        self.assertIn("/ru/", missing[0]["message"])
        title = by_id(findings, "translation-metadata-not-translated")
        self.assertEqual(len(title), 1)
        self.assertIn("/ru/", title[0]["message"])
        self.assertIn("title identical to ['en']", title[0]["evidence"])
        self.assertEqual(by_id(findings, "translation-body-language-mismatch"), [])

    def test_translation_check_needs_key_and_fields_for_a_content_file(self):
        result = run_script("translation_check.py", "--files", f"en:{ROWS_CSV}", f"ka:{KA}")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--key and --fields", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_ai_text_check_reads_an_entry(self):
        result = run_script("ai_text_check.py", "--file", ROWS_CSV, "--key", BATHS, "--fields", "title,content")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["file"], report["key"], report["language"]), (ROWS_CSV, BATHS, "en"))
        self.assertEqual(len(by_id(report["findings"], "ai-text-model-leftover")), 1)
        georgian = json.loads(run_script("ai_text_check.py", "--file", KA, "--key", FOOD, "--fields", "content").stdout)
        self.assertEqual(georgian["language"], "ka")
        self.assertEqual(by_id(georgian["findings"], "ai-text-model-leftover"), [])

    def test_ai_text_check_refuses_a_key_for_an_html_file(self):
        result = run_script("ai_text_check.py", "--file", HTML_DRAFT, "--key", FOOD, "--fields", "content")
        self.assertEqual(result.returncode, 2)
        self.assertIn("JSON, CSV or TSV", result.stderr)

    def test_content_score_scores_an_entry(self):
        result = run_script("content_score.py", "--file", ROWS_JSON, "--key", FOOD, "--fields", POST_FIELDS,
                            "--base-url", URL, "--keyword", "what to eat in georgia")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        placement = report["placement"]
        self.assertEqual((placement["in_title"], placement["in_h1"], placement["in_meta_description"],
                          placement["in_url"]), (True, True, False, True))
        self.assertIn("h2: Where to try them", report["structure"]["headings"])
        self.assertEqual(report["structure"]["lists"], 1)

    def test_content_score_needs_key_and_fields_for_a_content_file(self):
        result = run_script("content_score.py", "--file", ROWS_JSON, "--keyword", "x")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--key and --fields", result.stderr)


if __name__ == "__main__":
    unittest.main()
