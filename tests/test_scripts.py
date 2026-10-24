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
from ai_visibility import wilson  # noqa: E402
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
        {"query": "brand", "page": "/", "clicks": 300, "impressions": 1000, "ctr": 0.3, "position": 1.1},
    ]

    def test_striking_distance_finds_page_two_terms(self):
        rows = striking_distance(self.ROWS, ctr_curve(self.ROWS), 4, 20, 50)
        self.assertEqual({r["page"] for r in rows}, {"/a", "/b"})

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
                emitted |= {f"duplicate-{w}" for w in ("titles", "descriptions", "content")} if "duplicate-{" in source else set()
        emitted.discard("duplicate-")
        self.assertEqual(sorted(emitted - set(FINDING_TABLE)), [])

    def test_priority_rules(self):
        self.assertEqual(priority(5, 1, 0), "P0")
        self.assertEqual(priority(3, 1, 0.5), "P1")
        self.assertEqual(priority(4, 4, 0), "P2")
        self.assertEqual(priority(1, 1, 0), "park")


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


if __name__ == "__main__":
    unittest.main()
