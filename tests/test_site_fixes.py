"""Regression tests for crawl.py, robots_check.py and sitemap_check.py. Run: python3 -m unittest discover -s tests"""
import contextlib
import gzip
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import crawl  # noqa: E402
import robots_check  # noqa: E402
import sitemap_check  # noqa: E402
from robots_check import evaluate, findings_for, group_for, is_allowed, parse_robots  # noqa: E402
from seo_lib import FetchResult, extract_page  # noqa: E402
from sitemap_check import file_findings, parse_sitemap  # noqa: E402

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class LocalSite:
    """Serve {path: (status, headers, body)} on 127.0.0.1; unlisted paths get routes["*"] (default 404)."""

    def __init__(self, routes: dict):
        self.routes, self.requests = routes, []
        site = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                site.requests.append(self.path)
                status, headers, body = site.routes.get(self.path) or site.routes.get("*", (404, {}, b""))
                self.send_response(status)
                for name, value in {"Content-Type": "text/html; charset=utf-8", **headers}.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def page(title: str, body: str = "", head: str = "") -> tuple[int, dict, bytes]:
    return 200, {}, f"<html><head><title>{title}</title>{head}</head><body>{body}</body></html>".encode()


def xml(body: str) -> tuple[int, dict, bytes]:
    return 200, {"Content-Type": "application/xml"}, body.encode()


def run_cli(module, *argv: str) -> dict:
    out = io.StringIO()
    with mock.patch.object(sys, "argv", [module.__name__, *argv]), contextlib.redirect_stdout(out):
        module.main()
    return json.loads(out.getvalue())


def ids(findings: list) -> list[str]:
    return [f["id"] if isinstance(f, dict) else f.id for f in findings]


def facts_for(url: str, html: str):
    return extract_page(FetchResult(url, url, 200, {"content-type": "text/html"}, html.encode(), [], 0))


class RobotsFixesTest(unittest.TestCase):
    def robots_file_report(self, content: bytes) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "robots.txt")
            with open(path, "wb") as fh:
                fh.write(content)
            return run_cli(robots_check, "--file", path)

    def test_utf8_bom_does_not_hide_the_first_group(self):
        report = self.robots_file_report(b"\xef\xbb\xbfUser-agent: *\nDisallow: /\n")
        self.assertIn("robots-blocks-google", ids(report["findings"]))

    def test_sitemap_line_between_user_agents_keeps_one_group(self):
        for between in ("Sitemap: https://example.com/sitemap.xml", "Crawl-delay: 5"):
            groups = parse_robots(f"User-agent: Googlebot\n{between}\nUser-agent: Bingbot\nDisallow: /\n")
            self.assertFalse(is_allowed(group_for(groups, "Googlebot"), "/")[0], between)
            self.assertFalse(is_allowed(group_for(groups, "Bingbot"), "/")[0], between)

    def test_rules_and_paths_compare_percent_encoded(self):
        encoded_rule = group_for(parse_robots("User-agent: *\nDisallow: /caf%c3%a9/\n"), "Googlebot")
        self.assertFalse(is_allowed(encoded_rule, "/café/")[0])
        self.assertFalse(is_allowed(encoded_rule, "/caf%C3%A9/")[0])
        raw_rule = group_for(parse_robots("User-agent: *\nDisallow: /foo/bar/ツ\n"), "Googlebot")
        self.assertFalse(is_allowed(raw_rule, "/foo/bar/%E3%83%84")[0])
        self.assertTrue(is_allowed(raw_rule, "/foo/bar/x")[0])

    def test_asset_rules_only_count_for_the_group_googlebot_obeys(self):
        other_bot = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /*.js$\nDisallow: /*.css$\n"
        overridden = "User-agent: *\nDisallow: /*.js$\n\nUser-agent: Googlebot\nAllow: /\n"
        for text in (other_bot, overridden):
            found = ids(findings_for(text, len(text), 200, evaluate(text, ["/"])))
            self.assertNotIn("robots-blocks-assets", found, text)
        blocked = "User-agent: Googlebot\nDisallow: /static/*.js\n"
        self.assertIn("robots-blocks-assets", ids(findings_for(blocked, len(blocked), 200, evaluate(blocked, ["/"]))))

    def test_rules_after_500_kib_are_ignored(self):
        filler = b"Disallow: /x\n" * (robots_check.ROBOTS_MAX_BYTES // 13 + 10)
        report = self.robots_file_report(b"User-agent: *\n" + filler + b"Disallow: /\n")
        self.assertIn("robots-too-big", ids(report["findings"]))
        self.assertNotIn("robots-blocks-google", ids(report["findings"]))

    def test_user_agent_with_version_matches_its_product_token(self):
        groups = parse_robots("User-agent: Googlebot/2.1\nDisallow: /\n")
        self.assertFalse(is_allowed(group_for(groups, "Googlebot"), "/")[0])
        self.assertTrue(is_allowed(group_for(parse_robots("User-agent: * x\nDisallow: /a\n"), "Bingbot"), "/b")[0])
        self.assertFalse(is_allowed(group_for(parse_robots("User-agent: * x\nDisallow: /a\n"), "Bingbot"), "/a")[0])


class CrawlFixesTest(unittest.TestCase):
    def test_robots_5xx_stops_the_crawl(self):
        routes = {"/robots.txt": (503, {}, b"User-agent: *\nDisallow: /private/\n"),
                  "/": page("Home", '<a href="/private/p.html">p</a>'), "/private/p.html": page("P")}
        with LocalSite(routes) as site:
            report = run_cli(crawl, site.url + "/", "--delay", "0")
        self.assertEqual(report["pages_crawled"], 0)
        self.assertIn("robots-5xx", ids(report["site_findings"]))
        self.assertNotIn("/private/p.html", site.requests)

    def test_bom_robots_rules_are_obeyed(self):
        routes = {"/robots.txt": (200, {"Content-Type": "text/plain"}, b"\xef\xbb\xbfUser-agent: *\nDisallow: /a.html\n"),
                  "/": page("Home", '<a href="/a.html">a</a>'), "/a.html": page("A")}
        with LocalSite(routes) as site:
            run_cli(crawl, site.url + "/", "--delay", "0")
        self.assertNotIn("/a.html", site.requests)

    def test_soft_404_probe_flags_only_2xx_answers(self):
        for status, expected in ((403, None), (400, None), (410, None), (200, "soft-404"), (503, "missing-url-server-error")):
            with LocalSite({"*": (status, {}, b"<html><body>gone</body></html>")}) as site:
                finding = crawl.soft_404_probe(site.url + "/")
            self.assertEqual(finding.id if finding else None, expected, status)

    def test_path_prefix_links_are_not_reported_as_robots_blocked(self):
        routes = {"/robots.txt": (200, {"Content-Type": "text/plain"}, b"User-agent: *\nDisallow: /private/\n"),
                  "/deep/a.html": page("A", '<a href="/">home</a> <a href="/deep/b.html">b</a> <a href="/private/x.html">x</a>'),
                  "/deep/b.html": page("B")}
        with LocalSite(routes) as site:
            report = run_cli(crawl, site.url + "/deep/a.html", "--path-prefix", "/deep", "--delay", "0")
        blocked = [f for f in report["site_findings"] if f["id"] == "robots-blocked-links"]
        self.assertEqual([f["evidence"] for f in blocked], [site.url + "/private/x.html"])

    def test_self_link_is_not_an_inlink(self):
        routes = {"/hub.html": page("Hub", '<a href="/self.html">s</a>'),
                  "/self.html": page("Self", '<a href="/self.html#top">me</a>')}
        with LocalSite(routes) as site:
            report = run_cli(crawl, site.url + "/hub.html", "--delay", "0")
        weak = [f for f in report["site_findings"] if f["id"] == "weakly-linked"]
        self.assertEqual([f["evidence"] for f in weak], [site.url + "/self.html"])

    def test_redirecting_start_url_is_not_a_link_to_a_redirect(self):
        routes = {"/": (301, {"Location": "/home.html"}, b""), "/home.html": page("Home", '<a href="/about.html">a</a>'),
                  "/about.html": page("About")}
        with LocalSite(routes) as site:
            report = run_cli(crawl, site.url + "/", "--delay", "0")
        self.assertEqual(report["pages_crawled"], 2)
        self.assertNotIn("links-to-redirects", ids(report["site_findings"]))

    def test_variants_canonicalized_to_the_original_are_not_duplicates(self):
        html = ('<html><head><title>Same</title><meta name="description" content="Same description">{}</head>'
                '<body><p>' + "identical body text " * 40 + '</p></body></html>')
        clean, variant = "https://x.com/canon", "https://x.com/canon?ref=footer"
        canonical = f'<link rel="canonical" href="{clean}">'
        pages = {clean: facts_for(clean, html.format(canonical)), variant: facts_for(variant, html.format(canonical))}
        found = ids(crawl.site_findings(pages, {clean: 0, variant: 1}, {}, [], []))
        for dup in ("duplicate-content", "duplicate-titles", "duplicate-descriptions"):
            self.assertNotIn(dup, found)
        uncanonicalized = {clean: facts_for(clean, html.format("")), variant: facts_for(variant, html.format(""))}
        self.assertIn("duplicate-content", ids(crawl.site_findings(uncanonicalized, {clean: 0, variant: 1}, {}, [], [])))


def urlset(*locs: str, lastmod: str = "2026-01-01") -> str:
    urls = "".join(f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>" for loc in locs)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="{SITEMAP_NS}">{urls}</urlset>'


def sitemapindex(*locs: str) -> str:
    return f'<sitemapindex xmlns="{SITEMAP_NS}">' + "".join(f"<sitemap><loc>{loc}</loc></sitemap>" for loc in locs) + "</sitemapindex>"


class SitemapFixesTest(unittest.TestCase):
    def sitemap_report(self, routes: dict, path: str) -> dict:
        with LocalSite(routes) as site:
            return run_cli(sitemap_check, site.url + path, "--sample", "0")

    def test_gzip_sitemap_size_is_checked_uncompressed(self):
        body = gzip.compress(urlset(*(f"https://x.com/p{i}" for i in range(100))).encode())
        with mock.patch.object(sitemap_check, "MAX_UNCOMPRESSED_BYTES", 2000):
            self.assertLess(len(body), 2000)
            report = self.sitemap_report({"/sm.xml.gz": (200, {"Content-Type": "application/gzip"}, body)}, "/sm.xml.gz")
        self.assertIn("sitemap-too-big", ids(report["findings"]))

    def test_truncated_or_corrupt_gzip_is_a_finding_not_a_traceback(self):
        good = gzip.compress(urlset(*(f"https://x.com/p{i}" for i in range(50))).encode())
        for broken in (good[: len(good) // 2], good[:10] + b"\xff" * 20 + good[30:]):
            report = self.sitemap_report({"/sm.xml.gz": (200, {"Content-Type": "application/gzip"}, broken)}, "/sm.xml.gz")
            self.assertEqual(ids(report["findings"]), ["sitemap-compression-error"])

    def test_text_rss_and_atom_sitemaps_list_their_urls(self):
        kind, entries = parse_sitemap(b"\xef\xbb\xbfhttps://x.com/a\n\nhttps://x.com/b\n")
        self.assertEqual((kind, [e["loc"] for e in entries]), ("text", ["https://x.com/a", "https://x.com/b"]))
        rss = (b'<rss version="2.0"><channel><title>T</title><link>https://x.com/</link>'
               b'<item><title>A</title><link>https://x.com/a</link></item></channel></rss>')
        kind, entries = parse_sitemap(rss)
        self.assertEqual((kind, [e["loc"] for e in entries], entries[0]["alternates"]), ("rss", ["https://x.com/a"], 0))
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><title>T</title><link href="https://x.com/"/>'
                b'<entry><link rel="alternate" href="https://x.com/a"/><updated>2026-01-02T10:00:00Z</updated></entry></feed>')
        kind, entries = parse_sitemap(atom)
        self.assertEqual((kind, entries[0]["loc"], entries[0]["lastmod"]), ("feed", "https://x.com/a", "2026-01-02T10:00:00Z"))

    def test_missing_or_wrong_namespace_is_reported(self):
        for open_tag, close_tag in (("<urlset>", "</urlset>"), ("<html>", "</html>"),
                                    ('<urlset xmlns="http://www.google.com/schemas/sitemap/0.84">', "</urlset>")):
            body = f"{open_tag}<url><loc>https://x.com/a</loc></url>{close_tag}"
            report = self.sitemap_report({"/sitemap.xml": xml(body)}, "/sitemap.xml")
            self.assertEqual(ids(report["findings"]), ["sitemap-unsupported-format"], open_tag)
            self.assertEqual(report["total_urls"], 0)

    def test_www_and_apex_are_different_hosts(self):
        entries = [{"loc": "https://www.example.com/a", "lastmod": "2026-01-01"}]
        found = ids(file_findings("https://example.com/sitemap.xml", "urlset", entries, "https://example.com"))
        self.assertIn("sitemap-cross-host", found)
        same = [{"loc": "https://example.com/a", "lastmod": "2026-01-01"}]
        self.assertNotIn("sitemap-cross-host", ids(file_findings("https://example.com/sitemap.xml", "urlset", same, "https://example.com")))

    def test_nested_sitemap_index_is_reported_and_not_followed(self):
        routes = {"/index1.xml": xml(sitemapindex("{site}/index2.xml")), "/index2.xml": xml(sitemapindex("{site}/leaf.xml")),
                  "/leaf.xml": xml(urlset("https://x.com/a"))}
        with LocalSite({}) as site:
            site.routes.update({p: (s, h, b.replace(b"{site}", site.url.encode())) for p, (s, h, b) in routes.items()})
            report = run_cli(sitemap_check, site.url + "/index1.xml", "--sample", "0")
        self.assertIn("sitemap-nested-index", ids(report["findings"]))
        self.assertNotIn("/leaf.xml", site.requests)

    def test_lastmod_needs_a_zone_with_a_time_and_a_real_date(self):
        entries = [{"loc": "https://x.com/a", "lastmod": lm} for lm in
                   ("2026-01-02T10:00", "2026-01-02T10:00:00", "2026-13-45", "2026-01-02T25:61:00Z",
                    "2026-01-02T10:00:00Z", "2026-01-02T10:00:00.123+02:00", "2026-01", "2026-01-02")]
        found = {f.id: f for f in file_findings("https://x.com/sitemap.xml", "urlset", entries, "https://x.com")}
        self.assertTrue(found["sitemap-bad-lastmod"].message.startswith("4 "))
        self.assertNotIn("sitemap-future-lastmod", found)

    def test_files_beyond_the_cap_are_reported(self):
        routes = {"/index.xml": xml(sitemapindex(*(f"{{site}}/s{i}.xml" for i in range(3))))}
        routes.update({f"/s{i}.xml": xml(urlset(f"https://x.com/{i}")) for i in range(3)})
        with LocalSite({}) as site, mock.patch.object(sitemap_check, "MAX_FILES", 2):
            site.routes.update({p: (s, h, b.replace(b"{site}", site.url.encode())) for p, (s, h, b) in routes.items()})
            report = run_cli(sitemap_check, site.url + "/index.xml", "--sample", "0")
        self.assertIn("sitemap-files-skipped", ids(report["findings"]))


if __name__ == "__main__":
    unittest.main()
