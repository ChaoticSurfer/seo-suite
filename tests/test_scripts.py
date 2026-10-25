"""Unit tests for the pure logic in scripts/. Run: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gsc_analyze import cannibalization, ctr_curve, striking_distance  # noqa: E402
from keyword_ideas import classify_intent  # noqa: E402
from page_audit import audit_page  # noqa: E402
from robots_check import evaluate, group_for, is_allowed, parse_robots  # noqa: E402
from schema_rules import validate_json_ld  # noqa: E402
import ai_visibility as av  # noqa: E402
from ai_visibility import difference_ci, wilson  # noqa: E402
from content_score import ngrams  # noqa: E402
from triage import collect  # noqa: E402
from render_diff import diff  # noqa: E402
from seo_lib import extract_page, load_local, normalize_url, title_pixel_width  # noqa: E402
from triage import FINDING_TABLE, priority  # noqa: E402
from serp_cluster import clusters, overlaps  # noqa: E402
from content_score import contains  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class RobotsTest(unittest.TestCase):
    ROBOTS = """
User-agent: *
Disallow: /private/
Allow: /private/public-page
Disallow: /*.pdf$
Disallow: /search?

User-agent: GPTBot
User-agent: CCBot
Disallow: /

Sitemap: https://example.com/sitemap.xml
"""

    def setUp(self):
        self.groups = parse_robots(self.ROBOTS)

    def test_longest_match_wins(self):
        star = group_for(self.groups, "Googlebot")
        self.assertFalse(is_allowed(star, "/private/x")[0])
        self.assertTrue(is_allowed(star, "/private/public-page")[0])

    def test_wildcards_and_anchor(self):
        star = group_for(self.groups, "Googlebot")
        self.assertFalse(is_allowed(star, "/files/a.pdf")[0])
        self.assertTrue(is_allowed(star, "/files/a.pdf?download=1")[0])
        self.assertFalse(is_allowed(star, "/search?q=x")[0])

    def test_grouped_user_agents_share_rules(self):
        self.assertFalse(is_allowed(group_for(self.groups, "CCBot"), "/")[0])
        self.assertFalse(is_allowed(group_for(self.groups, "gptbot"), "/blog")[0])

    def test_equal_length_allow_wins(self):
        group = group_for(parse_robots("User-agent: *\nDisallow: /page\nAllow: /page"), "x")
        self.assertTrue(is_allowed(group, "/page")[0])

    def test_matrix_lists_sitemap(self):
        self.assertEqual(evaluate(self.ROBOTS, ["/"])["sitemaps"], ["https://example.com/sitemap.xml"])


class SchemaTest(unittest.TestCase):
    def test_product_needs_offer_review_or_rating(self):
        _, findings = validate_json_ld([{"@context": "https://schema.org", "@type": "Product", "name": "X"}])
        self.assertIn("schema-missing-required", [f.id for f in findings])

    def test_graph_nodes_and_subtypes(self):
        blocks = [{"@context": "https://schema.org", "@graph": [{"@type": "Dentist", "name": "D"}]}]
        types, findings = validate_json_ld(blocks)
        self.assertEqual(types, ["Dentist"])
        self.assertTrue(any("address" in f.message for f in findings))

    def test_nested_and_self_serving(self):
        event = {"@context": "https://schema.org", "@type": "Event", "name": "E", "startDate": "2026-11-01", "location": {"@type": "Place", "name": "Hall"}}
        _, findings = validate_json_ld([event])
        self.assertTrue(any("location.address" in f.message for f in findings))
        org = {"@context": "https://schema.org", "@type": "Dentist", "name": "D", "address": "x", "aggregateRating": {"ratingValue": 5}}
        self.assertIn("schema-self-serving-review", [f.id for f in validate_json_ld([org])[1]])

    def test_googlebot_image_falls_back_to_googlebot(self):
        groups = parse_robots("User-agent: Googlebot\nDisallow: /private/\nUser-agent: *\nDisallow: /")
        self.assertFalse(is_allowed(group_for(groups, "Googlebot-Image"), "/private/x")[0])
        self.assertTrue(is_allowed(group_for(groups, "Googlebot-Image"), "/public")[0])

    def test_faq_flagged_as_limited(self):
        _, findings = validate_json_ld([{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}])
        self.assertIn("schema-limited-type", [f.id for f in findings])


class PageAuditTest(unittest.TestCase):
    def test_fixture_page(self):
        facts = extract_page(load_local(os.path.join(FIXTURES, "bad_page.html"), "https://example.com/bad"))
        ids = {f.id for f in audit_page(facts)}
        for expected in ("noindex", "canonical-multiple", "img-alt-missing", "hreflang-invalid", "viewport-missing",
                         "schema-parse-error", "lcp-lazy", "internal-nofollow", "anchor-generic"):
            self.assertIn(expected, ids)
        self.assertEqual(facts.title, "Bad page")

    def test_title_width_is_monotonic(self):
        self.assertLess(title_pixel_width("iiii"), title_pixel_width("WWWW"))


class GscTest(unittest.TestCase):
    ROWS = [
        {"query": "seo audit", "page": "/a", "clicks": 10, "impressions": 1000, "ctr": 0.01, "position": 8.2},
        {"query": "seo audit", "page": "/b", "clicks": 5, "impressions": 500, "ctr": 0.01, "position": 9.0},
        {"query": "seo audit checklist", "page": "/c", "clicks": 1, "impressions": 400, "ctr": 0.0025, "position": 14.0},
        {"query": "brand", "page": "/", "clicks": 300, "impressions": 1000, "ctr": 0.3, "position": 1.1},
    ]

    def test_striking_distance_finds_page_two_terms(self):
        rows = striking_distance(self.ROWS, ctr_curve(self.ROWS), 4, 20, 50)
        self.assertEqual({r["page"] for r in rows}, {"/a", "/b", "/c"})  # page one and page two; not the #1 brand row

    def test_cannibalization(self):
        self.assertEqual(cannibalization(self.ROWS)[0]["query"], "seo audit")


class KeywordTest(unittest.TestCase):
    def test_intent(self):
        self.assertEqual(classify_intent("best seo tools"), "commercial")
        self.assertEqual(classify_intent("seo audit price"), "transactional")
        self.assertEqual(classify_intent("how to do seo"), "informational")


class TriageTest(unittest.TestCase):
    def test_every_emitted_finding_id_has_a_triage_row(self):
        import re
        emitted = set()
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py"):
                with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
                    source = fh.read()
                emitted |= set(re.findall(r'(?:Finding\(|add\()"([a-z0-9-]+)"', source))
        from crawl import DUPLICATE_CHECKS, duplicate_id
        emitted |= {duplicate_id(label) for label, _ in DUPLICATE_CHECKS}  # the one id built at runtime
        self.assertEqual(sorted(emitted - set(FINDING_TABLE)), [])

    def test_priority_rules(self):
        self.assertEqual(priority(5, 1, 0), "P0")
        self.assertEqual(priority(3, 1, 0.5), "P1")
        self.assertEqual(priority(4, 4, 0), "P2")
        self.assertEqual(priority(1, 1, 0), "park")


class ReviewRegressionTest(unittest.TestCase):
    def test_triage_keeps_same_finding_on_different_pages(self):
        a = {"url": "https://x.com/a", "findings": [{"id": "title-missing", "severity": "high", "message": "No <title>"}]}
        b = {**a, "url": "https://x.com/b"}
        rows = collect(a, "a.json") + collect(b, "b.json")
        keys = {(r["source"], r["id"], r["severity"], r["message"], r["evidence"]) for r in rows}
        self.assertEqual(len(keys), 2)
        self.assertEqual({r["url"] for r in rows}, {"https://x.com/a", "https://x.com/b"})

    def test_fetch_refuses_non_http_schemes(self):
        from seo_lib import fetch
        self.assertIn("refusing non-http(s)", fetch("file:///etc/passwd").error)

    def test_ngrams_do_not_cross_punctuation(self):
        self.assertNotIn("speed performance", ngrams("Core speed, performance matters.", 2))
        self.assertIn("core speed", ngrams("Core speed, performance matters.", 2))

    def test_difference_ci_detects_large_change_only(self):
        self.assertTrue(difference_ci(18, 20, 2, 20)["detectable_change"])
        self.assertFalse(difference_ci(6, 10, 5, 10)["detectable_change"])


class MiscTest(unittest.TestCase):
    def test_serp_clusters_merge_on_overlap(self):
        serps = {"a": [f"https://x.com/{i}" for i in range(10)], "b": [f"https://www.x.com/{i}/" for i in range(5)],
                 "c": ["https://y.com/1"]}
        groups = clusters(list(serps), overlaps(serps), 4)
        self.assertIn(sorted(["a", "b"]), [sorted(g) for g in groups])

    def test_keyword_match_is_whole_word(self):
        self.assertFalse(contains("we maintain sites", "ai"))
        self.assertTrue(contains("AI search is new", "ai"))

    def test_wilson_interval_brackets_rate(self):
        low, high = wilson(3, 10)
        self.assertTrue(low < 0.3 < high)

    def test_normalize_url(self):
        self.assertEqual(normalize_url("HTTPS://Example.com#top"), "https://example.com/")

    def test_render_diff_flags_js_only_content(self):
        raw = {"title": "A", "meta_description": "", "meta_robots": "", "canonical": "", "h1": [], "word_count": 10,
               "internal_links": 1, "schema_types": [], "hreflang": 0, "images": 0}
        rendered = {**raw, "word_count": 900, "internal_links": 40, "schema_types": ["Product"]}
        self.assertEqual(len(diff(raw, rendered)["warnings"]), 3)


class AiVisibilityTest(unittest.TestCase):
    """ai_visibility.py on rows with ai_probe.py's extra columns: share of voice, segments, the citation gap."""
    CSV = ("query,engine,run,date,mentioned,cited,cited_url,competitors_mentioned,lang,prompt_class,prompt_set,"
           "cited_domains\n"
           "best tutor,openai,1,2026-10-25,1,0,,rival.example,en,category,v1@a,rival.example\n"
           "best tutor,openai,2,2026-10-25,0,0,,rival.example;market.example,en,category,v1@a,reviews.example\n"
           "best tutor,openai,3,2026-10-25,1,1,https://tutors.example/a,,en,category,v1@a,tutors.example\n"
           "რეპეტიტორი,perplexity,1,2026-10-25,0,0,,,ka,category,v1@a,blog.example\n")

    def rows(self, text=None):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
            fh.write(text or self.CSV)
        self.addCleanup(os.unlink, fh.name)
        return av.load(fh.name)

    def test_share_of_voice_counts_answers_naming_any_tracked_brand(self):
        sov = av.share_of_voice(self.rows())
        self.assertEqual(sov["answers_naming_a_tracked_brand"], 3)  # the fourth answer names nobody
        self.assertEqual((sov["shares"]["brand"]["hits"], sov["shares"]["rival.example"]["hits"],
                          sov["shares"]["market.example"]["hits"]), (2, 2, 1))
        self.assertEqual(sov["shares"]["brand"]["rate"], 0.667)
        self.assertEqual(len(sov["shares"]["brand"]["ci95"]), 2)

    def test_segments_by_engine_language_and_class(self):
        report = av.summarize(self.rows(), "tutors.example")
        self.assertEqual(set(report["by_segment"]), {"openai|en|category", "perplexity|ka|category"})
        self.assertEqual(report["by_segment"]["openai|en|category"]["mention_rate"]["n"], 3)

    def test_mentioned_but_not_cited_and_the_citation_source_gap(self):
        report = av.summarize(self.rows(), "tutors.example")
        self.assertEqual(report["mentioned_not_cited"]["hits"], 1)
        self.assertEqual(report["citation_source_gap"], [("reviews.example", 1)])

    def test_old_rows_without_the_new_columns_still_work(self):
        report = av.summarize(self.rows("query,engine,run,date,mentioned,cited,cited_url,competitors_mentioned\n"
                                        "q,perplexity,1,2026-10-24,1,0,,preply\n"), None)
        self.assertNotIn("by_segment", report)
        self.assertEqual(report["competitor_mentions"], [("preply", 1)])

    def test_compare_refuses_different_prompt_sets(self):
        other = self.rows(self.CSV.replace("v1@a", "v1@b"))
        with self.assertRaises(SystemExit) as stop:
            av.check_same_prompt_set(self.rows(), other)
        self.assertIn("v1@b", str(stop.exception))
        av.check_same_prompt_set(self.rows(), self.rows())

    def test_compare_counts_only_the_engines_both_files_ran(self):
        import contextlib
        import io
        import json
        import tempfile
        from unittest import mock
        header = "query,engine,run,date,mentioned,cited,cited_url,competitors_mentioned,prompt_set\n"
        before = "".join(f"q{q},{engine},{run},2026-09-25,{int(q < 2)},0,,,v1@a\n"
                         for engine in ("openai", "perplexity") for q in range(10) for run in (1, 2, 3))
        added = "".join(f"q{q},anthropic,{run},2026-10-25,{int(q < 9)},0,,,v1@a\n" for q in range(10) for run in (1, 2, 3))
        paths = []
        for text in (header + before + added, header + before):
            with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
                fh.write(text)
            self.addCleanup(os.unlink, fh.name)
            paths.append(fh.name)
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["ai_visibility.py", paths[0], "--compare", paths[1]]), \
                contextlib.redirect_stdout(out):
            av.main()
        comparison = json.loads(out.getvalue())["comparison"]
        self.assertEqual(comparison["engines_compared"], ["openai", "perplexity"])
        mention = comparison["change_now_minus_before"]["mention_rate"]
        self.assertEqual((mention["difference"], mention["detectable_change"]), (0.0, False))


if __name__ == "__main__":
    unittest.main()
