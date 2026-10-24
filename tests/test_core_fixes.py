"""Regression tests for the verified seo_lib / page_audit / schema_rules / render_diff fixes.

Run: python3 -m unittest discover -s tests
The fetch tests talk to a throwaway HTTP server on 127.0.0.1 (first free port in 19000–19099).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from page_audit import audit_page  # noqa: E402
from robots_check import group_for, is_allowed, parse_robots  # noqa: E402
from schema_rules import validate_json_ld  # noqa: E402
from seo_lib import FetchResult, extract_page, fetch, is_indexable, load_local, normalize_url, title_pixel_width  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
PAGE_URL = "https://example.com/page"
RELCANON_HTML = (b'<!doctype html><html lang="en"><head><title>Relative canonical page</title>'
                 b'<link rel="canonical" href="./"></head><body><h1>Hi</h1><p>' + b"word " * 80 + b"</p></body></html>")


def page(html: str, url: str = PAGE_URL, headers: dict | None = None):
    return extract_page(FetchResult(url, url, 200, headers or {"content-type": "text/html"}, html.encode(), [], 0))


def page_bytes(body: bytes, content_type: str = "text/html"):
    return extract_page(FetchResult(PAGE_URL, PAGE_URL, 200, {"content-type": content_type}, body, [], 0))


def ids(findings) -> set:
    return {f.id for f in findings}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _raw(self, data: bytes):
        self.wfile.write(data)
        self.close_connection = True

    def _html(self, body: bytes, status: int = 200, headers: tuple = ()):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        base = f"http://127.0.0.1:{self.server.server_port}"
        if self.path == "/dup-xrobots":
            self._html(b"<title>x</title>", headers=(("X-Robots-Tag", "noindex"), ("X-Robots-Tag", "max-image-preview:large")))
        elif self.path == "/dup-link":
            self._html(b"<title>x</title>", headers=(("Link", f'<{base}/dup-link>; rel="canonical"'),
                                                     ("Link", "<https://cdn.example.net>; rel=preconnect")))
        elif self.path.startswith("/caf"):
            self._html(b"<title>" + self.path.encode("ascii") + b"</title>")  # echoes the path as it arrived on the wire
        elif self.path == "/redirect-raw-utf8":
            self._raw(b"HTTP/1.1 301 Moved Permanently\r\nLocation: /caf\xc3\xa9\r\nContent-Length: 0\r\n\r\n")
        elif self.path == "/stall":
            self._raw(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 1000\r\n\r\n<html>")
            time.sleep(2)
        elif self.path in ("/truncated-chunked", "/truncated-404"):
            status = b"200 OK" if self.path == "/truncated-chunked" else b"404 Not Found"
            self._raw(b"HTTP/1.1 " + status + b"\r\nContent-Type: text/html\r\nTransfer-Encoding: chunked\r\n\r\n20\r\nabc")
        elif self.path == "/raw-deflate":
            packer = zlib.compressobj(wbits=-zlib.MAX_WBITS)
            self._html(packer.compress(b"<title>Deflated</title>") + packer.flush(), headers=(("Content-Encoding", "deflate"),))
        elif self.path == "/bad-gzip":
            self._html(b"this is not gzip", headers=(("Content-Encoding", "gzip"),))
        elif self.path == "/loop-a":
            self._redirect("/loop-b")
        elif self.path == "/loop-b":
            self._redirect("/loop-a")
        elif self.path == "/challenge":
            self._html(b"<title>Just a moment...</title>", status=403, headers=(("cf-mitigated", "challenge"),))
        elif self.path == "/relcanon-redirect":
            self._redirect("/relcanon/")
        elif self.path == "/relcanon/":
            self._html(RELCANON_HTML)
        else:
            self._html(b"<title>missing</title>", status=404)


def setUpModule():
    global SERVER, BASE
    for port in range(19000, 19100):
        try:
            SERVER = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            break
        except OSError:
            continue
    else:
        raise RuntimeError("no free port in 19000-19099 for the test server")
    SERVER.daemon_threads = True
    threading.Thread(target=SERVER.serve_forever, daemon=True).start()
    BASE = f"http://127.0.0.1:{SERVER.server_port}"


def tearDownModule():
    SERVER.shutdown()
    SERVER.server_close()


def run_script(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, args[0]), *args[1:]], capture_output=True, text=True, timeout=60)


class FetchTest(unittest.TestCase):
    def test_repeated_headers_are_combined(self):
        result = fetch(f"{BASE}/dup-xrobots")
        self.assertIn("noindex", result.headers["x-robots-tag"])
        self.assertIn("max-image-preview:large", result.headers["x-robots-tag"])
        self.assertFalse(is_indexable(extract_page(result)))
        self.assertIn("noindex", ids(audit_page(extract_page(result))))

    def test_link_canonical_survives_a_later_link_header(self):
        facts = extract_page(fetch(f"{BASE}/dup-link"))
        self.assertEqual((facts.canonical, facts.canonical_count), (f"{BASE}/dup-link", 1))

    def test_non_ascii_url_is_percent_encoded(self):
        result = fetch(f"{BASE}/café")
        self.assertEqual((result.status, result.error), (200, ""))
        self.assertEqual(extract_page(result).title, "/caf%C3%A9")

    def test_raw_utf8_location_is_followed(self):
        result = fetch(f"{BASE}/redirect-raw-utf8")
        self.assertEqual((result.status, result.final_url), (200, f"{BASE}/caf%C3%A9"))

    def test_bad_host_is_an_error_not_a_crash(self):
        self.assertTrue(fetch("http://a..b.example/").error)

    def test_read_timeout_is_an_error_not_a_crash(self):  # socket.timeout is not TimeoutError on Python 3.9
        result = fetch(f"{BASE}/stall", timeout=0.5)
        self.assertEqual(result.status, None)
        self.assertTrue(result.error)

    def test_cut_off_chunked_body_is_an_error_not_a_crash(self):
        for path in ("/truncated-chunked", "/truncated-404"):
            with self.subTest(path=path):
                self.assertTrue(fetch(f"{BASE}{path}").error)

    def test_raw_deflate_body_is_decoded(self):
        result = fetch(f"{BASE}/raw-deflate")
        self.assertEqual(extract_page(result).title, "Deflated")

    def test_undecodable_body_is_an_error_not_a_crash(self):
        result = fetch(f"{BASE}/bad-gzip")
        self.assertEqual(result.status, None)
        self.assertIn("gzip", result.error)


class UrlEncodingTest(unittest.TestCase):
    def test_normalize_url_percent_encodes_path_and_query_and_punycodes_host(self):
        self.assertEqual(normalize_url("https://Example.com/café/a b?q=é&x=1"), "https://example.com/caf%C3%A9/a%20b?q=%C3%A9&x=1")
        self.assertEqual(normalize_url("https://example.com/caf%C3%A9/"), "https://example.com/caf%C3%A9/")
        self.assertEqual(normalize_url("https://ქართული.ge/გვერდი"), "https://xn--lododh2atk.ge/%E1%83%92%E1%83%95%E1%83%94%E1%83%A0%E1%83%93%E1%83%98")

    def test_extracted_urls_are_percent_encoded(self):
        facts = page('<head><link rel="canonical" href="/café"></head><body><a href="/about us.html">About</a></body>')
        self.assertEqual(facts.canonical, "https://example.com/caf%C3%A9")
        self.assertEqual([l["href"] for l in facts.internal_links], ["https://example.com/about%20us.html"])


class CharsetTest(unittest.TestCase):
    CP1251_HTML = '<html><head><meta charset="windows-1251"><title>Привет мир</title></head><body></body></html>'

    def test_meta_charset_is_used_when_the_header_has_none(self):
        self.assertEqual(page_bytes(self.CP1251_HTML.encode("cp1251")).title, "Привет мир")

    def test_quoted_header_charset(self):
        body = "<title>Привет мир</title>".encode("cp1251")
        self.assertEqual(page_bytes(body, 'text/html; charset="windows-1251"').title, "Привет мир")

    def test_unknown_charset_falls_back_instead_of_crashing(self):
        self.assertEqual(page_bytes("<title>Hello</title>".encode(), "text/html; charset=foo").title, "Hello")

    def test_saved_file_is_sniffed_unless_it_is_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy, utf8 = os.path.join(tmp, "legacy.html"), os.path.join(tmp, "rendered.html")
            with open(legacy, "wb") as fh:
                fh.write(self.CP1251_HTML.encode("cp1251"))
            with open(utf8, "wb") as fh:  # a rendered DOM saved as UTF-8 keeps the page's original <meta charset>
                fh.write(self.CP1251_HTML.encode("utf-8"))
            self.assertEqual(extract_page(load_local(legacy, PAGE_URL)).title, "Привет мир")
            self.assertEqual(extract_page(load_local(utf8, PAGE_URL)).title, "Привет мир")

    def test_utf8_bom_is_stripped(self):
        result = FetchResult("u", "u", 200, {"content-type": "text/plain"}, b"\xef\xbb\xbfUser-agent: *\nDisallow: /private/\n", [], 0)
        self.assertFalse(result.text.startswith("﻿"))
        self.assertFalse(is_allowed(group_for(parse_robots(result.text), "Googlebot"), "/private/x")[0])


class HeadDetectionTest(unittest.TestCase):
    def test_omitted_head_tag_still_counts_as_head(self):
        facts = page('<!doctype html><html lang=en><meta charset=utf-8><title>T</title>'
                     '<link rel=canonical href=https://example.com/page><script src=/app.js></script><h1>Hi</h1>')
        self.assertEqual((facts.canonical_count, facts.canonical_in_body), (1, False))
        self.assertEqual(facts.head_blocking_scripts, ["/app.js"])

    def test_body_element_inside_head_closes_it(self):
        facts = page('<html><head><title>T</title><img src=pixel.gif alt="">'
                     '<link rel="canonical" href="https://example.com/other-page"></head><body></body></html>')
        self.assertEqual((facts.canonical_count, facts.canonical_in_body), (0, True))

    def test_noscript_pixel_and_title_text_do_not_close_head(self):
        facts = page('<html><head><title>T</title><noscript><img src="https://px.example/tr"></noscript>'
                     '<link rel="canonical" href="https://example.com/page"></head><body><link rel="canonical" href="/b"></body></html>')
        self.assertEqual((facts.canonical_count, facts.canonical_in_body), (1, True))


class BaseHrefTest(unittest.TestCase):
    def test_base_href_resolves_relative_urls(self):
        facts = page('<head><base href="https://example.com/en/"><link rel="canonical" href="page"></head>'
                     '<body><a href="about">About</a><img src="img/hero.jpg"></body>')
        self.assertEqual(facts.canonical, "https://example.com/en/page")
        self.assertEqual([l["href"] for l in facts.internal_links], ["https://example.com/en/about"])
        self.assertEqual(facts.images[0]["src"], "https://example.com/en/img/hero.jpg")
        self.assertIn("canonical-elsewhere", ids(audit_page(facts)))

    def test_cross_host_base_does_not_change_internal_external_split(self):
        facts = page('<head><base href="https://cdn.other.net/"></head><body><a href="https://example.com/a">A</a></body>')
        self.assertEqual([l["href"] for l in facts.internal_links], ["https://example.com/a"])

    def test_link_header_resolves_against_the_page_not_base(self):
        facts = page('<head><base href="https://cdn.other.net/"></head>',
                     headers={"content-type": "text/html", "link": '</page>; rel="canonical"'})
        self.assertEqual(facts.canonical, "https://example.com/page")


class ParserTest(unittest.TestCase):
    def test_same_canonical_declared_twice_is_not_multiple(self):
        facts = page('<head><link rel="canonical" href="https://example.com/page"></head>',
                     headers={"content-type": "text/html", "link": '<https://example.com/page>; rel="canonical"'})
        self.assertEqual(facts.canonical_count, 1)
        self.assertNotIn("canonical-multiple", ids(audit_page(facts)))

    def test_self_closing_svg_does_not_hide_later_text(self):
        facts = page('<body><svg viewBox="0 0 1 1"/><p>After a self closing svg this paragraph still counts</p><a href="/a">Link A</a></body>')
        self.assertEqual(facts.paragraphs, ["After a self closing svg this paragraph still counts"])
        self.assertEqual(facts.internal_links[0]["text"], "Link A")

    def test_nested_and_unclosed_anchors_are_kept(self):
        facts = page('<body><a href="/one">One <a href="/two">Two</a><p><a href="/three">Three</p></body>')
        self.assertEqual([l["href"] for l in facts.internal_links],
                         ["https://example.com/one", "https://example.com/two", "https://example.com/three"])
        self.assertEqual(facts.internal_links[0]["text"], "One")

    def test_picture_with_modern_source_is_not_legacy(self):
        block = '<picture><source type="image/avif" srcset="/a{0}.avif"><img src="/a{0}.jpg" alt="a"></picture>'
        facts = page("<body>" + "".join(block.format(i) for i in range(5)) + "</body>")
        self.assertNotIn("img-legacy-formats", ids(audit_page(facts)))
        legacy = page("<body>" + "".join(f'<img src="/b{i}.jpg" alt="b">' for i in range(5)) + "</body>")
        self.assertIn("img-legacy-formats", ids(audit_page(legacy)))

    def test_cjk_title_width_counts_full_width_characters(self):
        self.assertGreater(title_pixel_width("東京の格安ホテル予約サイトで人気の宿泊施設を比較してお得に予約する方法"), 600)


class RobotsDirectivesTest(unittest.TestCase):
    def audit(self, meta: str = "", header: str = ""):
        tag = f'<meta name="robots" content="{meta}">' if meta else ""
        facts = page(f"<head>{tag}</head>", headers={"content-type": "text/html", "x-robots-tag": header})
        return is_indexable(facts), ids(audit_page(facts))

    def test_max_image_preview_none_is_not_noindex(self):
        indexable, found = self.audit(meta="max-image-preview:none")
        self.assertTrue(indexable)
        self.assertNotIn("noindex", found)

    def test_rules_for_other_crawlers_are_ignored(self):
        indexable, found = self.audit(header="bingbot: noindex, googlebot: nosnippet")
        self.assertTrue(indexable)
        self.assertNotIn("noindex", found)
        self.assertIn("snippet-blocked", found)

    def test_googlebot_and_unscoped_rules_apply(self):
        self.assertFalse(self.audit(header="googlebot: noindex")[0])
        self.assertFalse(self.audit(header="none")[0])
        self.assertIn("snippet-blocked", self.audit(header="max-snippet:0")[1])
        self.assertFalse(self.audit(header="unavailable_after: Friday, 25-Jun-10 15:00:00 PST, noindex")[0])


class HreflangTest(unittest.TestCase):
    def test_codes_google_does_not_support_are_invalid(self):
        for code, invalid in (("es-419", True), ("fil", True), ("en-GB", False), ("zh-Hant-TW", False), ("x-default", False)):
            with self.subTest(code=code):
                facts = page(f'<head><link rel="alternate" hreflang="{code}" href="https://example.com/page"></head>')
                self.assertEqual("hreflang-invalid" in ids(audit_page(facts)), invalid)


class SchemaRulesTest(unittest.TestCase):
    def required(self, block) -> list:
        return [f.message for f in validate_json_ld([{"@context": "https://schema.org", **block}])[1] if f.id == "schema-missing-required"]

    def test_carousel_list_item_needs_no_name(self):
        items = [{"@type": "ListItem", "position": i, "url": f"https://example.com/{i}"} for i in (1, 2)]
        self.assertEqual(self.required({"@type": "ItemList", "itemListElement": items}), [])

    def test_breadcrumb_name_may_come_from_item(self):
        crumbs = [{"@type": "ListItem", "position": 1, "item": {"@id": "https://e.com/", "name": "Home"}},
                  {"@type": "ListItem", "position": 2, "name": "Shoes"}]
        self.assertEqual(self.required({"@type": "BreadcrumbList", "itemListElement": crumbs}), [])

    def test_breadcrumb_crumbs_still_need_name_and_item(self):
        crumbs = [{"@type": "ListItem", "position": 1, "name": "Home"}, {"@type": "ListItem", "position": 2, "item": "https://e.com/x"}]
        messages = self.required({"@type": "BreadcrumbList", "itemListElement": crumbs})
        self.assertEqual(len(messages), 2)
        self.assertTrue(any("'item'" in m for m in messages) and any("'name'" in m for m in messages))

    def test_educational_organization_is_an_organization(self):
        org = {"@type": "EducationalOrganization", "name": "Example University", "url": "https://example.edu"}
        self.assertEqual(self.required(org), [])
        _, findings = validate_json_ld([{"@context": "https://schema.org", **org, "aggregateRating": {"ratingValue": 5}}])
        self.assertIn("schema-self-serving-review", ids(findings))


class PageAuditCliTest(unittest.TestCase):
    def test_fetch_failure_emits_a_fetch_failed_finding(self):
        proc = run_script("page_audit.py", f"{BASE}/loop-a")
        self.assertEqual(proc.returncode, 2)
        report = json.loads(proc.stdout)
        self.assertIn("redirect loop", report["error"])
        self.assertEqual([(f["id"], f["severity"]) for f in report["findings"]], [("fetch-failed", "critical")])

    def test_saved_file_gets_no_transport_header_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "big.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("<html><head><title>Big saved page</title></head><body><p>" + "word " * 4000 + "</p></body></html>")
            report = json.loads(run_script("page_audit.py", "--file", path, "--base-url", PAGE_URL).stdout)
        found = {f["id"] for f in report["findings"]}
        self.assertFalse(found & {"no-compression", "no-hsts"})


class RenderDiffCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rendered = os.path.join(self.tmp.name, "rendered.html")
        with open(self.rendered, "wb") as fh:
            fh.write(RELCANON_HTML)

    def tearDown(self):
        self.tmp.cleanup()

    def test_failed_or_challenged_raw_fetch_is_not_diffed(self):
        for path in ("/loop-a", "/challenge"):
            with self.subTest(path=path):
                proc = run_script("render_diff.py", f"{BASE}{path}", "--rendered", self.rendered)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("error", json.loads(proc.stdout))

    def test_url_or_raw_is_required(self):
        proc = run_script("render_diff.py", "--rendered", self.rendered)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("give a URL or --raw", proc.stderr)

    def test_rendered_side_resolves_against_the_final_url(self):
        proc = run_script("render_diff.py", f"{BASE}/relcanon-redirect", "--rendered", self.rendered)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("canonical", json.loads(proc.stdout)["changes"])


if __name__ == "__main__":
    unittest.main()
