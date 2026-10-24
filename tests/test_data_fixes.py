"""Regression tests for the data scripts: log_analyze, psi, redirect_check, gsc_analyze.
Run: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import log_analyze  # noqa: E402
import psi  # noqa: E402
import redirect_check  # noqa: E402
from gsc_analyze import cannibalization, compare, load_rows  # noqa: E402
from seo_lib import FetchResult, to_uri  # noqa: E402

GOOGLEBOT_V6 = "2001:4860:4801:10::1"
GOOGLEBOT_V6_HOST = "crawl-2001-4860-4801-0010-0000-0000-0000-0001.googlebot.com"


def run_main(module, argv: list[str]) -> tuple[int, dict]:
    out = io.StringIO()
    with mock.patch.object(sys, "argv", [module.__name__] + argv), contextlib.redirect_stdout(out):
        code = module.main()
    return code, json.loads(out.getvalue())


class VerifyDnsTest(unittest.TestCase):
    def verify(self, ip, host, forward):
        """forward: the addresses getaddrinfo returns for host, or the error it raises."""
        if isinstance(forward, Exception):
            getaddrinfo = mock.patch("socket.getaddrinfo", side_effect=forward)
        else:
            getaddrinfo = mock.patch("socket.getaddrinfo", return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (a, 0))
                                                                          for a in forward])
        with mock.patch("socket.gethostbyaddr", return_value=(host, [], [ip])), getaddrinfo, \
                mock.patch("socket.gethostbyname_ex", side_effect=socket.gaierror(8, "no A record")):  # IPv4-only lookup
            return log_analyze.verify_ip(ip, log_analyze.VERIFIED_DOMAINS["Googlebot"])

    def test_ipv6_only_googlebot_is_genuine(self):
        self.assertIs(self.verify(GOOGLEBOT_V6, GOOGLEBOT_V6_HOST, [GOOGLEBOT_V6]), True)

    def test_addresses_are_compared_normalized(self):
        self.assertIs(self.verify("2001:4860:4801:0010:0000:0000:0000:0001", GOOGLEBOT_V6_HOST, [GOOGLEBOT_V6]), True)

    def test_failed_forward_lookup_is_unverifiable_not_fake(self):
        self.assertIsNone(self.verify(GOOGLEBOT_V6, GOOGLEBOT_V6_HOST, socket.gaierror(8, "nodename nor servname")))

    def test_foreign_domain_and_mismatched_forward_are_fake(self):
        self.assertIs(self.verify("203.0.113.9", "googlebot.com.attacker.test", ["203.0.113.9"]), False)
        self.assertIs(self.verify("203.0.113.9", "crawl-66-249-66-1.googlebot.com", ["66.249.66.1"]), False)

    def test_report_keeps_unverifiable_out_of_fake_list(self):
        verdicts = {"66.249.66.1": True, "203.0.113.9": False, GOOGLEBOT_V6: None}
        line = '{ip} - - [10/Oct/2026:13:55:36 +0000] "GET / HTTP/1.1" 200 512 "-" "Mozilla/5.0 (compatible; Googlebot/2.1)"\n'
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "access.log")
            with open(log, "w", encoding="utf-8") as fh:
                fh.writelines(line.format(ip=ip) for ip in verdicts)
            with mock.patch.object(log_analyze, "verify_ip", side_effect=lambda ip, _: verdicts[ip]):
                _, report = run_main(log_analyze, [log, "--verify-dns"])
        googlebot = report["bots"]["Googlebot"]
        self.assertEqual(googlebot["unverified_ips"], ["203.0.113.9"])
        self.assertEqual(googlebot["unverifiable_ips"], [GOOGLEBOT_V6])


def crux(**percentiles) -> dict:
    keys = {"lcp": "LARGEST_CONTENTFUL_PAINT_MS", "inp": "INTERACTION_TO_NEXT_PAINT", "cls": "CUMULATIVE_LAYOUT_SHIFT_SCORE"}
    return {"metrics": {keys[k]: {"percentile": v} for k, v in percentiles.items()}}


class PsiTest(unittest.TestCase):
    def test_missing_inp_is_judged_on_lcp_and_cls(self):
        self.assertIs(psi.field_metrics(crux(lcp=1800, cls=5))["passes_core_web_vitals"], True)
        self.assertIs(psi.field_metrics(crux(lcp=4500, cls=5))["passes_core_web_vitals"], False)

    def test_missing_lcp_or_cls_is_not_assessable(self):
        self.assertIsNone(psi.field_metrics(crux(inp=100, cls=5))["passes_core_web_vitals"])
        self.assertIsNone(psi.field_metrics(crux(lcp=1800, inp=100))["passes_core_web_vitals"])

    def psi_report(self, origin, audits=None):
        body = json.dumps({"originLoadingExperience": origin, "lighthouseResult": {"audits": audits or {}}}).encode()
        response = FetchResult("https://psi.test", "https://psi.test", 200, {"content-type": "application/json"}, body, [], 0)
        with mock.patch.object(psi, "fetch", return_value=response):
            return run_main(psi, ["https://example.test/"])[1]

    def test_no_cwv_fail_without_an_assessment(self):
        self.assertEqual(self.psi_report(crux(lcp=1800, cls=5))["findings"], [])
        self.assertEqual(self.psi_report(crux(inp=900))["findings"], [])
        self.assertEqual([f["id"] for f in self.psi_report(crux(lcp=4500, cls=5))["findings"]], ["cwv-fail"])

    def test_lcp_element_comes_from_lighthouse_13_insight(self):
        node = {"type": "node", "selector": "main > img.hero", "nodeLabel": "Hero image"}
        audits = {"lcp-breakdown-insight": {"details": {"type": "list", "items": [{"type": "table", "items": []}, node]}}}
        self.assertEqual(self.psi_report(crux(lcp=1800, cls=5), audits)["lcp_element"], node)
        self.assertEqual(psi.lcp_element({"audits": {}}), {})


class RedirectCheckTest(unittest.TestCase):
    def test_short_row_is_reported_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "map.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("old,new\nhttps://old.test/a,https://new.test/a\nhttps://old.test/dropped\n")
            pairs = redirect_check.load_map(path)
        self.assertEqual(pairs, [("https://old.test/a", "https://new.test/a"), ("https://old.test/dropped", "")])
        landed = FetchResult("https://old.test/dropped", "https://new.test/", 200, {}, b"", [("https://old.test/dropped", 301)], 0)
        with mock.patch.object(redirect_check, "fetch", return_value=landed):
            self.assertIn("no new URL in the map", redirect_check.check(pairs[1])["problems"])

    def test_unicode_urls_are_sent_and_compared_percent_encoded(self):
        target = "https://new.test/caf%C3%A9"
        html = f'<html><head><link rel="canonical" href="{target}"></head><body>x</body></html>'.encode()
        landed = FetchResult("https://old.test/caf%C3%A9", target, 200, {"content-type": "text/html"}, html,
                             [("https://old.test/caf%C3%A9", 301)], 0)
        with mock.patch.object(redirect_check, "fetch", return_value=landed) as fetch:
            result = redirect_check.check(("https://old.test/café", "https://new.test/café"))
        fetch.assert_called_once_with("https://old.test/café")  # fetch() percent-encodes it before http.client sees it
        self.assertEqual(result["problems"], [])

    def test_to_uri_keeps_encoded_urls_and_punycodes_unicode_hosts(self):
        self.assertEqual(to_uri("https://x.test/a%20b?q=1&r=a/b"), "https://x.test/a%20b?q=1&r=a/b")
        self.assertEqual(to_uri("https://bücher.test/über uns"), "https://xn--bcher-kva.test/%C3%BCber%20uns")


class GscSplitRowsTest(unittest.TestCase):
    def load(self, text: str) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "export.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            return load_rows(path)

    def test_device_and_date_rows_merge_into_one_query_page(self):
        rows = self.load("date,query,page,device,clicks,impressions,ctr,position\n"
                         "2026-10-01,seo audit,https://x.test/a,MOBILE,6,600,1%,4\n"
                         "2026-10-01,seo audit,https://x.test/a,DESKTOP,4,500,0.8%,6\n"
                         "2026-10-02,seo audit,https://x.test/a,MOBILE,2,400,0.5%,9\n")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["clicks"], rows[0]["impressions"]), (12, 1500))
        self.assertAlmostEqual(rows[0]["ctr"], 12 / 1500)
        self.assertAlmostEqual(rows[0]["position"], (4 * 600 + 6 * 500 + 9 * 400) / 1500)
        self.assertEqual(cannibalization(rows), [])

    def test_compare_uses_every_split_row(self):
        header = "query,page,device,clicks,impressions,position\n"
        before = self.load(header + "seo audit,https://x.test/a,MOBILE,30,1000,3\nseo audit,https://x.test/a,DESKTOP,30,1000,3\n")
        now = self.load(header + "seo audit,https://x.test/a,MOBILE,20,1000,3\nseo audit,https://x.test/a,DESKTOP,20,1000,3\n")
        self.assertEqual([m["delta"] for m in compare(now, before)["losers"]], [-20])


class GscLikelyCauseTest(unittest.TestCase):
    @staticmethod
    def row(query, clicks, impressions, position):
        return {"query": query, "clicks": clicks, "impressions": impressions, "ctr": clicks / impressions, "position": position}

    def test_causes_explain_losses_only(self):
        before = [self.row("seo tool", 20, 1000, 5.0), self.row("seo audit", 60, 1000, 3.0)]
        now = [self.row("seo tool", 50, 1000, 2.0), self.row("seo audit", 100, 1000, 4.5)]
        self.assertEqual([m["likely_cause"] for m in compare(now, before)["winners"]], [None, None])

    def test_similar_rank_causes_need_a_similar_rank(self):
        before = [self.row("rank up", 50, 2000, 8.0), self.row("rank same", 50, 2000, 4.0), self.row("rank down", 50, 2000, 4.0)]
        now = [self.row("rank up", 30, 1000, 5.0), self.row("rank same", 30, 1000, 4.3), self.row("rank down", 30, 1000, 6.0)]
        causes = {m["key"]: m["likely_cause"] for m in compare(now, before)["losers"]}
        self.assertEqual(causes["rank up"], "mixed")
        self.assertTrue(causes["rank same"].startswith("fewer impressions at similar rank"))
        self.assertEqual(causes["rank down"], "rankings dropped")


if __name__ == "__main__":
    unittest.main()
