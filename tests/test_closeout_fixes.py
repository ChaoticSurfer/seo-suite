"""Regression tests for the close-out fixes: IDN hosts, to_uri, X-Robots-Tag scopes, charset sniffing, load_local,
fetch max_bytes, crawl robots redirects, nested sitemap indexes, triage rows, redirect_check, log_analyze hostnames,
gsc_analyze exports without query/page, and the ProductGroup/gtin/breadcrumb schema rules.

Run: python3 -m unittest discover -s tests
The fetch and CLI tests talk to a throwaway HTTP server on 127.0.0.1 (a free port).
"""
from __future__ import annotations

import contextlib
import http.server
import io
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import crawl  # noqa: E402
import gsc_analyze  # noqa: E402
import log_analyze  # noqa: E402
import redirect_check  # noqa: E402
import seo_lib  # noqa: E402
import sitemap_check  # noqa: E402
from page_audit import audit_page  # noqa: E402
from robots_check import group_for, parse_robots  # noqa: E402
from schema_rules import validate_json_ld  # noqa: E402
from seo_lib import FetchResult, extract_page, fetch, googlebot_robots_directives, is_indexable, load_local, normalize_url, to_uri  # noqa: E402
from triage import FINDING_TABLE  # noqa: E402

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
PAGE = (200, [], b"<html><head><title>A page</title></head><body><h1>A page</h1></body></html>")


class Site:
    """Serve {raw request path: (status, [(header, value), ...], body)} on 127.0.0.1; /echo-host answers with the Host
    header it received. Other paths get 404."""

    def __init__(self):
        self.routes, self.requests = {}, []
        site = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                site.requests.append(self.path)
                if self.path.endswith("/echo-host"):
                    status, headers, body = 200, [("Content-Type", "text/plain")], self.headers["Host"].encode("latin-1")
                else:
                    status, headers, body = site.routes.get(self.path, (404, [], b"missing"))
                self.send_response(status)
                if not any(name.lower() == "content-type" for name, _ in headers):
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                for name, value in headers:
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.url = f"http://127.0.0.1:{self.port}"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def redirect(location: str) -> tuple:
    return 301, [("Location", location)], b""


def xml(body: str) -> tuple:
    return 200, [("Content-Type", "application/xml")], body.encode()


def urlset(*locs: str) -> str:
    return f'<urlset xmlns="{SITEMAP_NS}">' + "".join(f"<url><loc>{loc}</loc></url>" for loc in locs) + "</urlset>"


def sitemapindex(*locs: str) -> str:
    return f'<sitemapindex xmlns="{SITEMAP_NS}">' + "".join(f"<sitemap><loc>{loc}</loc></sitemap>" for loc in locs) + "</sitemapindex>"


def run_cli(module, *argv: str) -> tuple[int, dict]:
    out = io.StringIO()
    with mock.patch.object(sys, "argv", [module.__name__, *argv]), contextlib.redirect_stdout(out):
        code = module.main()
    return code, json.loads(out.getvalue())


def ids(findings: list) -> list[str]:
    return [f["id"] if isinstance(f, dict) else f.id for f in findings]


def page_bytes(body: bytes, content_type: str = "text/html"):
    url = "https://example.com/page"
    return extract_page(FetchResult(url, url, 200, {"content-type": content_type}, body, [], 0))


def closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class IdnHostTest(unittest.TestCase):
    def test_host_header_is_idna_encoded_and_final_url_is_punycode(self):
        connect = socket.create_connection
        with Site() as site, mock.patch("socket.create_connection",  # every host resolves to the test server
                                        lambda address, *a, **k: connect(("127.0.0.1", site.port), *a, **k)):
            for host, wire in (("пример.рф", "xn--e1afmkfd.xn--p1ai"), ("München.de", "xn--mnchen-3ya.de")):
                with self.subTest(host=host):
                    url = f"http://{host}:{site.port}/echo-host"
                    result = fetch(url)
                    self.assertEqual((result.status, result.error), (200, ""))
                    self.assertEqual(result.body.decode("ascii"), f"{wire}:{site.port}")
                    self.assertEqual(result.final_url, f"http://{wire}:{site.port}/echo-host")  # one host form everywhere

    def test_userinfo_and_port_are_kept(self):
        self.assertEqual(seo_lib._ascii_host("http://user:pw@München.de:8080/p?q=1"), "http://user:pw@xn--mnchen-3ya.de:8080/p?q=1")


class ToUriTest(unittest.TestCase):
    def test_only_what_http_client_refuses_is_encoded(self):
        self.assertEqual(to_uri("https://e.com/list?f[a]=1&g={x}|^`\"<>\\"), "https://e.com/list?f[a]=1&g={x}|^`\"<>\\")
        self.assertEqual(to_uri("https://e.com/a b\x7f\x01é"), "https://e.com/a%20b%7F%01%C3%A9")
        self.assertEqual(to_uri("https://e.com/100%25%zz"), "https://e.com/100%25%zz")  # a stray % is left as written

    def test_lower_case_escapes_and_raw_unicode_are_one_url(self):
        forms = {normalize_url(u) for u in ("https://e.com/café/", "https://e.com/caf%c3%a9/", "https://e.com/caf%C3%A9/")}
        self.assertEqual(forms, {"https://e.com/caf%C3%A9/"})
        facts = page_bytes('<body><a href="/café/">A</a><a href="/caf%c3%a9/">B</a></body>'.encode())
        self.assertEqual({l["href"] for l in facts.internal_links}, {"https://example.com/caf%C3%A9/"})

    def test_robots_rules_with_printable_ascii_still_match(self):
        group = group_for(parse_robots("User-agent: *\nDisallow: /*[\nDisallow: /*|\n"), "Googlebot")
        for path in ("/list?f[a]=1", "/a|b"):
            with self.subTest(path=path):
                self.assertFalse(crawl.crawlable(normalize_url("https://e.com" + path), "e.com", group))

    def test_sitemap_sample_of_200_urls_is_not_non_200(self):
        with Site() as site:
            site.routes.update({"/bracket?f[a]=1": PAGE, "/a|b": PAGE, "/caf%C3%A9/": PAGE})
            locs = [f"{site.url}/bracket?f[a]=1", f"{site.url}/a|b", f"{site.url}/caf%c3%a9/", f"{site.url}/café/"]
            site.routes["/sitemap.xml"] = xml(urlset(*locs))
            _, report = run_cli(sitemap_check, site.url + "/sitemap.xml", "--sample", "10")
        self.assertEqual([r["status"] for r in report["sample"]], [200] * 4)
        self.assertNotIn("sitemap-non-200", ids(report["findings"]))


class XRobotsTagTest(unittest.TestCase):
    def test_unscoped_header_after_a_scoped_one_still_applies(self):
        with Site() as site:
            site.routes["/xrt"] = (200, [("X-Robots-Tag", "bingbot: nofollow"), ("X-Robots-Tag", "noindex")], PAGE[2])
            result = fetch(site.url + "/xrt")
        self.assertEqual(result.headers["x-robots-tag"], "bingbot: nofollow\nnoindex")
        facts = extract_page(result)
        self.assertFalse(is_indexable(facts))
        self.assertIn("noindex", ids(audit_page(facts)))

    def test_scope_ends_with_its_header(self):
        self.assertEqual(googlebot_robots_directives("", "bingbot: noindex\nnosnippet"), ", nosnippet")
        self.assertEqual(googlebot_robots_directives("", "googlebot: nosnippet\nbingbot: noindex"), ", nosnippet")
        self.assertEqual(googlebot_robots_directives("", "bingbot: noindex, nofollow"), "")  # one header: scope lasts


class CharsetTest(unittest.TestCase):
    HTML = '<html><head><meta charset="{0}"><title>Hello world</title></head><body></body></html>'

    def test_meta_utf16_is_read_as_utf8(self):
        for label in ("utf-16", "UTF-16LE", "utf-16be"):
            with self.subTest(label=label):
                self.assertEqual(page_bytes(self.HTML.format(label).encode()).title, "Hello world")

    def test_non_text_codecs_are_skipped_not_a_crash(self):
        for label in ("hex", "base64", "rot13", "zip"):
            with self.subTest(label=label):
                self.assertEqual(page_bytes(self.HTML.format(label).encode()).title, "Hello world")
                self.assertEqual(page_bytes(b"<title>Hello world</title>", f"text/html; charset={label}").title, "Hello world")

    def test_header_utf16_is_still_honoured(self):
        self.assertEqual(page_bytes("<title>Привет</title>".encode("utf-16-le"), "text/html; charset=utf-16le").title, "Привет")


class LoadLocalTest(unittest.TestCase):
    def test_unicode_base_url_matches_extracted_urls(self):
        base = "https://example.ge/ბლოგი/"
        html = (f'<html lang="ka"><head><title>ბლოგი</title><link rel="canonical" href="{base}">'
                f'<link rel="alternate" hreflang="ka" href="{base}"><link rel="alternate" hreflang="x-default" href="{base}">'
                "</head><body><h1>ბლოგი</h1></body></html>")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ka.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            result = load_local(path, base)
        self.assertEqual(result.final_url, to_uri(base))
        found = ids(audit_page(extract_page(result)))
        self.assertNotIn("hreflang-no-self", found)
        self.assertNotIn("canonical-elsewhere", found)


class MaxBytesTest(unittest.TestCase):
    def test_both_reads_obey_max_bytes(self):
        with Site() as site:
            site.routes.update({"/ok": (200, [], b"x" * 1000), "/gone": (404, [], b"x" * 1000)})
            self.assertEqual(len(fetch(site.url + "/ok", max_bytes=100).body), 100)
            self.assertEqual(len(fetch(site.url + "/gone", max_bytes=100).body), 100)

    def test_sitemap_over_15_mb_is_parsed(self):
        padding = "<!--" + "x" * seo_lib.MAX_BODY_BYTES + "-->"
        with Site() as site:
            site.routes["/big.xml"] = xml(f'<urlset xmlns="{SITEMAP_NS}">{padding}<url><loc>https://x.com/a</loc></url></urlset>')
            _, report = run_cli(sitemap_check, site.url + "/big.xml", "--sample", "0")
        self.assertEqual(report["total_urls"], 1)
        self.assertNotIn("sitemap-invalid-xml", ids(report["findings"]))


class CrawlRobotsRedirectTest(unittest.TestCase):
    def crawl_report(self, routes: dict) -> dict:
        with Site() as site:
            site.routes.update({"/": PAGE, **{p: redirect(loc) for p, loc in routes.items()}})
            return run_cli(crawl, site.url + "/", "--delay", "0")[1]

    def test_robots_lost_in_redirects_means_no_rules(self):
        cases = {
            "loop": {"/robots.txt": "/robots2.txt", "/robots2.txt": "/robots.txt"},
            "too many hops": {"/robots.txt": "/r1", **{f"/r{i}": f"/r{i + 1}" for i in range(1, 12)}},
            "non-http target": {"/robots.txt": "ftp://127.0.0.1/robots.txt"},
        }
        for name, routes in cases.items():
            with self.subTest(name):
                report = self.crawl_report(routes)
                self.assertEqual(report["pages_crawled"], 1)
                self.assertNotIn("robots-5xx", ids(report["site_findings"]))

    def test_network_error_after_a_redirect_still_stops(self):
        report = self.crawl_report({"/robots.txt": f"http://127.0.0.1:{closed_port()}/robots.txt"})
        self.assertEqual(report["pages_crawled"], 0)
        self.assertIn("robots-5xx", ids(report["site_findings"]))


class NestedSitemapIndexTest(unittest.TestCase):
    def test_nested_index_is_found_in_either_order_and_a_submitted_one_is_read(self):
        for order in (("a", "b"), ("b", "a")):
            with self.subTest(order=order), Site() as site:
                robots = "".join(f"Sitemap: {site.url}/{name}.xml\n" for name in order)
                site.routes.update({
                    "/robots.txt": (200, [("Content-Type", "text/plain")], robots.encode()),
                    "/a.xml": xml(sitemapindex(f"{site.url}/b.xml", f"{site.url}/leaf1.xml")),
                    "/b.xml": xml(sitemapindex(f"{site.url}/leaf2.xml")),
                    "/leaf1.xml": xml(urlset("https://x.com/1")), "/leaf2.xml": xml(urlset("https://x.com/2")),
                })
                _, report = run_cli(sitemap_check, site.url, "--sample", "0")
                self.assertEqual(report["total_urls"], 2)
                self.assertEqual(ids(report["findings"]).count("sitemap-nested-index"), 1)
                self.assertIn("/leaf2.xml", site.requests)


class TriageRowsTest(unittest.TestCase):
    def test_new_finding_ids_have_rows(self):
        expected = {"missing-url-server-error": (2, 2), "sitemap-compression-error": (3, 1), "sitemap-unsupported-format": (3, 1),
                    "sitemap-nested-index": (3, 1), "sitemap-files-skipped": (1, 1)}
        self.assertEqual({k: FINDING_TABLE[k][:2] for k in expected}, expected)


class RedirectCheckEncodingTest(unittest.TestCase):
    def test_brackets_pipes_and_lower_case_escapes_land_where_mapped(self):
        with Site() as site, tempfile.TemporaryDirectory() as tmp:
            site.routes.update({
                "/old-bracket": redirect("/new?filter[color]=red"), "/new?filter[color]=red": PAGE,
                "/pipe": redirect("/a|b"), "/a|b": PAGE,
                "/old-wp": redirect("/caf%c3%a9/"), "/old-caf%C3%A9": redirect("/caf%C3%A9/"), "/caf%C3%A9/": PAGE,
            })
            path = os.path.join(tmp, "map.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("old,new\n" + "".join(f"{site.url}{old},{site.url}{new}\n" for old, new in (
                    ("/old-bracket", "/new?filter[color]=red"), ("/pipe", "/a|b"), ("/old-wp", "/caf%c3%a9/"),
                    ("/old-café", "/café/"))))
            code, report = run_cli(redirect_check, path)
        self.assertEqual((code, report["passed"]), (0, 4), report["failures"])


class LogAnalyzeHostnameTest(unittest.TestCase):
    HOST = "crawl-66-249-66-1.googlebot.com"

    def test_hostname_in_the_ip_field_is_unverifiable(self):
        with mock.patch("socket.gethostbyaddr", side_effect=AssertionError("no DNS lookup for a hostname")):
            self.assertIsNone(log_analyze.verify_ip(self.HOST, log_analyze.VERIFIED_DOMAINS["Googlebot"]))

    def test_report_survives_a_hostname_in_the_ip_field(self):
        line = f'{self.HOST} - - [10/Oct/2026:13:55:36 +0000] "GET / HTTP/1.1" 200 512 "-" "Mozilla/5.0 (compatible; Googlebot/2.1)"\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "access.log")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(line)
            code, report = run_cli(log_analyze, path, "--verify-dns")
        self.assertEqual(code, 0)
        self.assertEqual(report["bots"]["Googlebot"]["unverifiable_ips"], [self.HOST])
        self.assertEqual(report["bots"]["Googlebot"]["unverified_ips"], [])


class GscExportTest(unittest.TestCase):
    def load(self, text: str) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "export.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            return gsc_analyze.load_rows(path)

    def test_export_without_query_or_page_is_refused(self):
        for first in ("Country", "Device", "Date"):
            with self.subTest(first=first), self.assertRaises(SystemExit) as ctx:
                self.load(f"{first},Clicks,Impressions,CTR,Position\nx,10,100,10%,3\ny,5,100,5%,4\n")
            self.assertIn("no query or page column", str(ctx.exception))

    def test_pages_export_still_loads(self):
        self.assertEqual(len(self.load("Top pages,Clicks,Impressions,CTR,Position\nhttps://x.test/a,10,100,10%,3\n")), 1)


class SchemaRulesCloseoutTest(unittest.TestCase):
    @staticmethod
    def messages(block: dict, finding_id: str) -> list[str]:
        return [f.message for f in validate_json_ld([{"@context": "https://schema.org", **block}])[1] if f.id == finding_id]

    def test_product_group_id_may_live_on_the_variants(self):
        group = {"@type": "ProductGroup", "name": "Tee", "variesBy": ["https://schema.org/color"],
                 "hasVariant": [{"@type": "Product", "name": "Tee red", "inProductGroupWithID": "tee", "offers": {"price": 1}}]}
        self.assertEqual(self.messages(group, "schema-missing-required"), [])
        self.assertTrue(any("productGroupID" in m for m in self.messages(group, "schema-missing-recommended")))

    def test_any_gtin_variant_satisfies_the_gtin_recommendation(self):
        product = {"@type": "Product", "name": "Tee", "image": "i", "description": "d", "sku": "s", "brand": "b",
                   "offers": {"@type": "Offer", "price": 1}}
        product_messages = lambda p: [m for m in self.messages(p, "schema-missing-recommended") if m.startswith("Product ")]
        self.assertTrue(any("gtin" in m for m in product_messages(product)))
        for key in ("gtin", "gtin8", "gtin12", "gtin13", "gtin14"):
            with self.subTest(key=key):
                self.assertEqual(product_messages({**product, key: "4006381333931"}), [])

    def test_last_breadcrumb_needs_no_item(self):
        crumbs = [{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://e.com/"},
                  {"@type": "ListItem", "position": 2, "name": "Shoes"}]
        _, findings = validate_json_ld([{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs}])
        self.assertEqual([f.message for f in findings if "'item'" in f.message], [])


if __name__ == "__main__":
    unittest.main()
