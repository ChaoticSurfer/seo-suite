"""blog_system_check.py against recorded sites: one built to the blog-system rules, one with the defects they catch.

Run: python3 -m unittest discover -s tests
"""
import json
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import blog_system_check as bsc  # noqa: E402
from seo_lib import FetchResult, to_uri  # noqa: E402
from triage import FINDING_TABLE, collect  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "blog-system")
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


def recorded_site(name: str):
    """A fetch() stand-in that serves fixtures/blog-system/<name>/ by path and query, on any host; the rest is 404."""
    folder = os.path.join(FIXTURES, name)
    with open(os.path.join(folder, "routes.json"), encoding="utf-8") as fh:
        routes = json.load(fh)
    requested = []

    def fetch(url: str) -> FetchResult:
        requested.append(url)
        parts = url.split("://", 1)[1]
        path = "/" + parts.split("/", 1)[1] if "/" in parts else "/"
        route = routes.get(path)
        if route is None:
            return FetchResult(url, to_uri(url), 404, {"content-type": "text/html"}, b"<html><title>Not found</title></html>", [], 0)
        with open(os.path.join(folder, route["file"]), "rb") as fh:
            body = fh.read()
        headers = {"content-type": route.get("type", "text/html; charset=utf-8"), **route.get("headers", {})}
        return FetchResult(url, to_uri(url), route.get("status", 200), headers, body, [], 0)

    fetch.requested = requested
    return fetch


def run(name: str, start: str = "https://example.com/blog", **options) -> dict:
    options.setdefault("money_pages", ["https://example.com/tours/kazbegi"])
    options.setdefault("indexnow_key_location", "https://example.com/indexnow-key.txt")
    return bsc.check_blog(start, recorded_site(name), now=NOW, **options)


def finding_ids(report: dict) -> set:
    return {f["id"] for f in report["findings"]}


class GoodBlogTest(unittest.TestCase):
    def setUp(self):
        self.report = run("good")

    def test_no_findings(self):
        self.assertEqual(self.report["findings"], [])

    def test_every_rule_checked_and_passing(self):
        statuses = {r["id"]: r["status"] for r in self.report["rules"]}
        self.assertEqual(set(statuses.values()), {"pass"}, statuses)

    def test_samples_posts_from_every_index_page(self):
        self.assertEqual([p["url"] for p in self.report["pages"]["posts"]],
                         ["https://example.com/blog/post-a", "https://example.com/blog/post-b", "https://example.com/blog/post-c"])
        self.assertEqual([p["url"] for p in self.report["pages"]["pagination"]], ["https://example.com/blog?page=2"])

    def test_local_build_checked_against_production_urls(self):
        site = recorded_site("good")
        report = bsc.check_blog("http://localhost:3000/blog", site, now=NOW, production_url="https://example.com",
                                money_pages=["https://example.com/tours/kazbegi"],
                                indexnow_key_location="https://example.com/indexnow-key.txt")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["url"], "https://example.com/blog")
        self.assertTrue(all(url.startswith("http://localhost:3000/") for url in site.requested), site.requested)

    def test_unset_options_leave_rules_not_checked(self):
        report = run("good", money_pages=[], indexnow_key_location=None)
        statuses = {r["id"]: r["status"] for r in report["rules"]}
        self.assertEqual(statuses["blog-money-pages-link-posts"], "not_checked")
        self.assertEqual(statuses["blog-indexnow-key"], "not_checked")


class BadBlogTest(unittest.TestCase):
    EXPECTED = {
        # pagination
        "blog-pagination-canonical-to-first", "blog-pagination-title-duplicate", "blog-pagination-out-of-range-200",
        # post template
        "blog-post-schema-missing", "schema-missing-recommended", "blog-post-breadcrumb-missing",
        "blog-post-modified-before-published", "blog-post-date-no-timezone", "blog-post-date-mismatch",
        "blog-post-date-future", "blog-post-author-generic", "blog-post-author-no-url", "blog-post-byline-missing", "blog-author-page-error", "lcp-lazy", "img-no-dimensions",
        "blog-post-image-no-srcset", "blog-post-lcp-not-prioritised", "blog-post-url-style",
        # links
        "blog-related-posts-identical", "blog-twin-links-missing", "blog-money-page-no-post-links",
        # archives
        "blog-archive-empty-200", "blog-archive-thin-indexable",
        # sitemap, feed, IndexNow
        "not-in-sitemap", "blog-sitemap-post-no-lastmod", "blog-sitemap-lastmod-mismatch", "blog-feed-missing",
        "blog-indexnow-key-invalid",
    }

    def setUp(self):
        self.report = run("bad")

    def test_finds_exactly_the_planted_defects(self):
        self.assertEqual(finding_ids(self.report), self.EXPECTED)

    def test_failing_rules(self):
        statuses = {r["id"]: r["status"] for r in self.report["rules"]}
        for rule in ("blog-pagination-self-canonical", "blog-post-dates", "blog-post-byline", "blog-post-lcp-image",
                     "blog-language-twin-links", "blog-archive-thin-noindex", "blog-sitemap-real-lastmod", "blog-feed"):
            self.assertEqual(statuses[rule], "fail", rule)
        self.assertEqual(statuses["blog-index-indexable"], "pass")

    def test_findings_name_the_page(self):
        lazy = next(f for f in self.report["findings"] if f["id"] == "lcp-lazy")
        self.assertIn("https://example.com/blog/post-a", lazy["evidence"])
        twins = next(f for f in self.report["findings"] if f["id"] == "blog-twin-links-missing")
        self.assertIn("https://example.com/ka/blog/post-a", twins["evidence"])


class BrokenIndexTest(unittest.TestCase):
    def test_unreachable_index_stops_with_one_finding(self):
        report = bsc.check_blog("https://example.com/nothing-here", recorded_site("good"), now=NOW)
        self.assertEqual(finding_ids(report), {"blog-index-error"})
        statuses = {r["id"]: r["status"] for r in report["rules"]}
        self.assertEqual(statuses["blog-index-indexable"], "fail")
        self.assertEqual(statuses["blog-post-dates"], "not_checked")


class NoPaginationTest(unittest.TestCase):
    def test_posts_only_in_the_sitemap_need_a_page_2(self):
        good = recorded_site("good")
        index_without_pages = (b'<html><head><title>Travel blog</title><link rel="canonical" href="https://example.com/blog">'
                               b'</head><body><h1>Travel blog</h1><a href="/blog/post-a">A</a></body></html>')

        def fetch(url):
            if url == "https://example.com/blog":
                return FetchResult(url, url, 200, {"content-type": "text/html"}, index_without_pages, [], 0)
            return good(url)

        report = bsc.check_blog("https://example.com/blog", fetch, now=NOW)
        missing = next(f for f in report["findings"] if f["id"] == "blog-pagination-missing")
        self.assertIn("https://example.com/blog/post-b", missing["evidence"])
        statuses = {r["id"]: r["status"] for r in report["rules"]}
        self.assertEqual(statuses["blog-pagination-crawlable"], "fail")
        self.assertEqual(statuses["blog-pagination-self-canonical"], "not_checked")


class DatesTest(unittest.TestCase):
    def test_same_instant_in_two_zones_agrees(self):
        self.assertFalse(bsc.dates_disagree("2026-10-10T12:00:00+04:00", "2026-10-10T08:00:00Z"))

    def test_date_only_compares_the_day(self):
        self.assertTrue(bsc.dates_disagree("2026-10-22T00:00:00", "2026-10-21"))
        self.assertFalse(bsc.dates_disagree("2026-10-21T23:00:00", "2026-10-21"))

    def test_lastmod_tolerates_a_day_of_time_zone(self):
        self.assertFalse(bsc.lastmod_disagrees("2026-10-05", "2026-10-05T09:00:00+04:00"))
        self.assertTrue(bsc.lastmod_disagrees("2026-09-27", "2026-10-22T00:00:00"))


class TriageTest(unittest.TestCase):
    def test_every_finding_id_has_a_triage_row(self):
        ids = {fid for rule in bsc.RULES for fid in rule["findings"]}
        self.assertEqual(ids - set(FINDING_TABLE), set())

    def test_triage_reads_the_report(self):
        report = run("bad")
        rows = collect(report, "blog-system.json")
        self.assertEqual({r["id"] for r in rows}, BadBlogTest.EXPECTED)
        self.assertTrue(all(r["url"] == "https://example.com/blog" for r in rows))


if __name__ == "__main__":
    unittest.main()
