"""Regression tests for the loose ends after the close-out: one (punycode) host form everywhere, charset labels that
cannot decode a page, --path-prefix in the frontier's form, redirect_check's comparison, sitemap-too-big wording,
compare_pages --no-own-page ordering and cap, and robots_check on a robots.txt lost in redirects.

Run: python3 -m unittest discover -s tests
The fetch and CLI tests reuse test_closeout_fixes' throwaway HTTP server on 127.0.0.1 (a free port). IDN hosts are
routed to it by patching socket.create_connection, so no DNS or hosts-file entry is needed.
"""
from __future__ import annotations

import gzip
import os
import socket
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))  # for test_closeout_fixes when this file is run on its own

import compare_pages  # noqa: E402
import crawl  # noqa: E402
import redirect_check  # noqa: E402
import robots_check  # noqa: E402
import sitemap_check  # noqa: E402
import test_closeout_fixes as closeout  # noqa: E402  (Site, run_cli, ids, ...; no TestCase is imported by name)
from page_audit import audit_page  # noqa: E402
from seo_lib import FetchResult, extract_page, fetch, normalize_url, registrable_host, same_site, to_uri  # noqa: E402

UNICODE_HOST, PUNYCODE_HOST = "пример.рф", "xn--e1afmkfd.xn--p1ai"


def routed_to(site: closeout.Site):
    """Connect every host to the test server, as if DNS pointed it there."""
    connect = socket.create_connection
    return mock.patch("socket.create_connection", lambda address, *a, **k: connect(("127.0.0.1", site.port), *a, **k))


class OneHostFormTest(unittest.TestCase):
    def test_to_uri_punycodes_the_host_and_keeps_userinfo_and_port(self):
        self.assertEqual(to_uri("http://user:pw@München.de:8080/über?q=é"), "http://user:pw@xn--mnchen-3ya.de:8080/%C3%BCber?q=%C3%A9")
        self.assertEqual(to_uri("https://xn--mnchen-3ya.de/a"), "https://xn--mnchen-3ya.de/a")

    def test_host_idna_cannot_encode_is_kept_and_fetch_reports_it(self):
        self.assertEqual(to_uri("http://ü..de/é"), "http://ü..de/%C3%A9")
        result = fetch("http://ü..de/")
        self.assertIsNone(result.status)
        self.assertTrue(result.error)

    def test_unicode_and_punycode_urls_are_one_site(self):
        self.assertEqual(registrable_host(normalize_url("https://www.München.de/")), "xn--mnchen-3ya.de")
        self.assertTrue(same_site(normalize_url("https://xn--mnchen-3ya.de/a"), normalize_url("https://münchen.de/")))

    def idn_site(self, site: closeout.Site) -> str:
        """Home page that writes its own URLs in both forms; returns the Unicode start URL."""
        uni, puny = f"http://{UNICODE_HOST}:{site.port}", f"http://{PUNYCODE_HOST}:{site.port}"
        home = (f'<html><head><title>Пример</title><link rel="canonical" href="{puny}/">'
                f'<link rel="alternate" hreflang="ru" href="{puny}/"><link rel="alternate" hreflang="x-default" href="{uni}/">'
                f'</head><body><h1>Пример</h1><a href="{puny}/a">A</a><a href="{uni}/b">B</a>'
                f'<a href="http://другой.рф:{site.port}/x">other site</a></body></html>')
        site.routes.update({"/": (200, [], home.encode()), "/a": closeout.PAGE, "/b": closeout.PAGE})
        return uni + "/"

    def test_page_that_writes_its_own_urls_in_punycode_matches_itself(self):
        with closeout.Site() as site, routed_to(site):
            facts = extract_page(fetch(self.idn_site(site)))
            host_seen = fetch(f"http://{UNICODE_HOST}:{site.port}/echo-host").body.decode("ascii")
        puny = f"http://{PUNYCODE_HOST}:{site.port}"
        self.assertEqual(host_seen, f"{PUNYCODE_HOST}:{site.port}")
        self.assertEqual(facts.final_url, puny + "/")
        self.assertEqual(facts.canonical, puny + "/")
        self.assertEqual([l["href"] for l in facts.internal_links], [puny + "/a", puny + "/b"])
        self.assertEqual([l["href"] for l in facts.external_links], [f"http://xn--c1abqtis.xn--p1ai:{site.port}/x"])
        found = closeout.ids(audit_page(facts))
        self.assertNotIn("canonical-elsewhere", found)
        self.assertNotIn("hreflang-no-self", found)

    def test_crawl_of_an_idn_site_reaches_links_in_both_forms(self):
        with closeout.Site() as site, routed_to(site):
            _, report = closeout.run_cli(crawl, self.idn_site(site), "--delay", "0")
        self.assertEqual(report["pages_crawled"], 3)
        issues = {row["id"] for row in report["page_issue_summary"]}
        self.assertFalse(issues & {"canonical-elsewhere", "hreflang-no-self"}, issues)

    def test_redirect_to_the_punycode_host_lands_on_the_unicode_mapping(self):
        with closeout.Site() as site, routed_to(site), tempfile.TemporaryDirectory() as tmp:
            site.routes.update({"/old": closeout.redirect(f"http://{PUNYCODE_HOST}:{site.port}/new"), "/new": closeout.PAGE})
            path = os.path.join(tmp, "map.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(f"old,new\nhttp://{UNICODE_HOST}:{site.port}/old,http://{UNICODE_HOST}:{site.port}/new\n")
            code, report = closeout.run_cli(redirect_check, path)
        self.assertEqual((code, report["passed"]), (0, 1), report["failures"])

    def test_sitemap_on_the_unicode_host_is_not_cross_host_from_its_punycode_url(self):
        entries = [sitemap_check._entry("https://münchen.de/a"), sitemap_check._entry("https://xn--mnchen-3ya.de/b")]
        found = closeout.ids(sitemap_check.file_findings("https://xn--mnchen-3ya.de/sitemap.xml", "urlset", entries,
                                                         "https://xn--mnchen-3ya.de"))
        self.assertNotIn("sitemap-cross-host", found)


class UndecodableCharsetTest(unittest.TestCase):
    HTML = '<html><head><meta charset="{0}"><title>Hello world</title></head><body></body></html>'

    def test_undefined_and_idna_labels_fall_back_instead_of_crashing(self):
        url = "https://example.com/page"
        for label in ("undefined", "idna"):
            with self.subTest(label=label):
                meta = FetchResult(url, url, 200, {"content-type": "text/html"}, self.HTML.format(label).encode(), [], 0)
                header = FetchResult(url, url, 200, {"content-type": f"text/html; charset={label}"},
                                     b"<title>Hello world</title>", [], 0)
                self.assertEqual(extract_page(meta).title, "Hello world")
                self.assertEqual(extract_page(header).title, "Hello world")

    def test_crawl_survives_a_page_with_charset_undefined(self):
        with closeout.Site() as site:
            site.routes.update({"/": (200, [], b'<html><body><a href="/u">u</a></body></html>'),
                                "/u": (200, [("Content-Type", "text/html; charset=undefined")], closeout.PAGE[2])})
            _, report = closeout.run_cli(crawl, site.url + "/", "--delay", "0")
        self.assertEqual(report["pages_crawled"], 2)


class PathPrefixFormTest(unittest.TestCase):
    def test_prefix_matches_whatever_escape_case_or_raw_unicode_it_is_written_in(self):
        section = (200, [], b'<html><body><a href="/caf%c3%a9/a/">a</a><a href="/caf%c3%a9/b/">b</a>'
                            b'<a href="/other/">other</a></body></html>')
        for prefix in ("/caf%c3%a9/", "/caf%C3%A9/", "/café/"):
            with self.subTest(prefix=prefix), closeout.Site() as site:
                site.routes.update({"/caf%C3%A9/": section, "/caf%C3%A9/a/": closeout.PAGE, "/caf%C3%A9/b/": closeout.PAGE,
                                    "/other/": closeout.PAGE})
                _, report = closeout.run_cli(crawl, site.url + "/caf%c3%a9/", "--delay", "0", "--path-prefix", prefix)
                self.assertEqual(report["pages_crawled"], 3)
                self.assertNotIn("/other/", site.requests)


class SitemapTooBigTest(unittest.TestCase):
    def report(self, body: bytes) -> list[dict]:
        with closeout.Site() as site, mock.patch.object(sitemap_check, "MAX_UNCOMPRESSED_BYTES", 1000):
            site.routes["/big.xml"] = (200, [("Content-Type", "application/xml")], body)
            _, report = closeout.run_cli(sitemap_check, site.url + "/big.xml", "--sample", "0")
        return [f for f in report["findings"] if f["id"] == "sitemap-too-big"]

    def test_plain_file_cut_off_at_the_read_limit_does_not_quote_the_read_size(self):
        (finding,) = self.report(closeout.urlset(*[f"https://x.com/{i}" for i in range(100)]).encode())
        self.assertIn("is larger than 50 MB uncompressed", finding["message"])
        self.assertNotIn("bytes", finding["message"])

    def test_gzipped_file_quotes_its_real_uncompressed_size(self):
        xml = closeout.urlset(*[f"https://x.com/{i}" for i in range(100)]).encode()
        (finding,) = self.report(gzip.compress(xml))
        self.assertIn(f"is {len(xml)} bytes uncompressed", finding["message"])


class ComparePagesBriefTest(unittest.TestCase):
    WORDS = " ".join(f"word{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(100))  # 100 distinct, no stopwords

    def run_compare(self, *argv: str) -> dict:
        bodies = {"https://own.test/": "<html><body><p>nothing in common here</p></body></html>"}
        fetched = lambda u: FetchResult(u, u, 200, {"content-type": "text/html"},
                                        bodies.get(u, f"<html><body><p>{self.WORDS}</p></body></html>").encode(), [], 0)
        with mock.patch.object(compare_pages, "fetch", side_effect=fetched):
            return closeout.run_cli(compare_pages, *argv)[1]

    def test_brief_lists_every_shared_phrase_in_a_stable_order(self):
        phrases = self.run_compare("https://a.test/", "https://b.test/", "--no-own-page")["shared_competitor_phrases"]
        self.assertGreater(len(phrases), 60)
        self.assertEqual(phrases, sorted(phrases))  # every phrase is on both pages, so the tie-break is the whole order

    def test_gap_list_against_your_page_keeps_the_cap(self):
        gap = self.run_compare("https://own.test/", "https://a.test/", "https://b.test/")["content_gap_phrases"]
        self.assertEqual(gap, sorted(gap))
        self.assertEqual(len(gap), 60)


class RobotsRedirectFailureTest(unittest.TestCase):
    def run_robots(self, routes: dict) -> tuple[int, dict]:
        with closeout.Site() as site:
            site.routes.update({p: closeout.redirect(loc) for p, loc in routes.items()})
            return closeout.run_cli(robots_check, site.url + "/")

    def test_robots_lost_in_redirects_is_reported_like_a_404(self):
        cases = {
            "loop": {"/robots.txt": "/robots2.txt", "/robots2.txt": "/robots.txt"},
            "too many hops": {"/robots.txt": "/r1", **{f"/r{i}": f"/r{i + 1}" for i in range(1, 12)}},
            "non-http target": {"/robots.txt": "ftp://127.0.0.1/robots.txt"},
        }
        for name, routes in cases.items():
            with self.subTest(name):
                code, report = self.run_robots(routes)
                self.assertEqual(code, 0)
                missing = [f for f in report["findings"] if f["id"] == "robots-missing"]
                self.assertEqual(len(missing), 1)
                self.assertIn("everything is crawlable", missing[0]["message"])
                self.assertTrue(missing[0]["evidence"])
                self.assertTrue(report["matrix"]["Googlebot"]["paths"]["/"]["allowed"])

    def test_network_error_after_a_redirect_still_exits_2(self):
        code, report = self.run_robots({"/robots.txt": f"http://127.0.0.1:{closeout.closed_port()}/robots.txt"})
        self.assertEqual(code, 2)
        self.assertTrue(report["error"])


if __name__ == "__main__":
    unittest.main()
