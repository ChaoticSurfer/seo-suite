"""Audit profile picker: size from sitemaps and the crawl, the free default, budgets per size, request words and the
option, the CLI contract (exit codes, JSON out, injection) and drift against profiles.md, tools.md and plugin.json.
Run: python3 -m unittest discover -s tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PICKER = os.path.join(ROOT, "scripts", "audit_profile.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import audit_profile as ap  # noqa: E402
import credit_guard as cg  # noqa: E402

ZEROS = dict.fromkeys(ap.REPORTED_BUDGETS, 0.0)
NONE = frozenset()
JSON_KEYS = ["profile", "label", "stack", "cross_checks", "report", "crawl", "competitors", "chosen_by", "size_class",
             "indexable_urls", "size_source", "audit_profile_option", "options_exported", "budgets", "reasons",
             "questions"]


def budgets(**values):
    return {**ZEROS, **{key: float(value) for key, value in values.items()}}


def crawl_report(pages, hit, indexable):
    return {"start": "https://example.com/", "pages_crawled": pages, "hit_page_limit": hit,
            "indexable_pages": indexable}


class SizeTest(unittest.TestCase):
    def test_boundary_is_2000_sitemap_urls(self):
        self.assertEqual(ap.measure_size([{"total_urls": 2000}], None)[:3], ("small", 2000, "sitemap"))
        self.assertEqual(ap.measure_size([{"total_urls": 2001}], None)[:3], ("big", 2001, "sitemap"))

    def test_reports_from_several_hosts_are_summed(self):
        self.assertEqual(ap.measure_size([{"total_urls": 1500}, {"total_urls": 600}], None)[:3],
                         ("big", 2100, "sitemap"))

    def test_crawl_that_hit_its_limit_escalates_a_small_sitemap(self):
        size, _, source, reason = ap.measure_size([{"total_urls": 300}], crawl_report(2001, True, 1800))
        self.assertEqual((size, source), ("big", "crawl-limit"))
        self.assertIn("2,001", reason)
        self.assertTrue(reason.endswith("big, the sitemap under-lists the site"), reason)

    def test_crawl_limit_with_fewer_indexable_pages_than_the_sitemap_blames_non_indexable_pages(self):
        reason = ap.measure_size([{"total_urls": 1900}], crawl_report(2001, True, 1200))[3]
        self.assertTrue(reason.endswith("big, more than 2,000 crawlable pages, though fewer are indexable"), reason)

    def test_crawl_limit_with_no_sitemap_never_blames_the_sitemap(self):
        size, _, source, reason = ap.measure_size([{"total_urls": 0}], crawl_report(2001, True, 1500))
        self.assertEqual((size, source), ("big", "crawl-limit"))
        self.assertTrue(reason.endswith("big, more than 2,000 crawlable pages"), reason)

    def test_crawl_count_when_there_is_no_sitemap(self):
        self.assertEqual(ap.measure_size([], crawl_report(400, False, 340))[:3], ("small", 340, "crawl"))

    def test_crawl_stopped_by_robots_is_ignored(self):
        stopped = {"start": "https://example.com/", "pages_crawled": 0, "site_findings": [{"id": "robots-5xx"}]}
        size, urls, source, reason = ap.measure_size([{"total_urls": 0}], stopped)
        self.assertEqual((size, urls, source), ("small", None, "unknown"))
        self.assertIn("the whole-site crawl fetched no pages", reason)

    def test_empty_sitemaps_wait_for_the_crawl(self):
        self.assertEqual(ap.measure_size([{"total_urls": 0}], None)[3],
                         "no sitemap URLs and no crawl yet: small depth until the crawl is read")

    def test_no_inputs_is_small_until_measured(self):
        self.assertEqual(ap.measure_size([], None)[:3], ("small", None, "unknown"))


class PickTest(unittest.TestCase):
    def pick(self, request="", option="auto", budget=None, connected=NONE, size="small"):
        return ap.pick(ap.request_intents(request), option, budget or ZEROS, connected, size)

    def test_default_is_full_free_at_both_sizes(self):
        for size in ("small", "big"):
            with self.subTest(size=size):
                profile, chosen_by, reasons, questions = self.pick(size=size)
                self.assertEqual((profile, chosen_by, questions), ("full-free", "default", []))
                self.assertEqual(reasons[-1], "full-free (chosen by default)")

    def test_dataforseo_budget_picks_the_paid_list_for_the_size(self):
        for size in ("small", "big"):
            with self.subTest(size=size):
                self.assertEqual(self.pick(budget=budgets(dataforseo_monthly_usd=25), size=size)[:2],
                                 (f"paid-{size}", "budgets"))

    def test_other_budget_picks_paid_for_se_ranking(self):
        for size in ("small", "big"):
            with self.subTest(size=size):
                self.assertEqual(self.pick(budget=budgets(other_monthly_usd=12), size=size)[0], f"paid-{size}")

    def test_semrush_budget_alone_stays_free(self):
        for size in ("small", "big"):
            with self.subTest(size=size):
                profile, chosen_by, reasons, _ = self.pick(budget=budgets(semrush_monthly_units=5000), size=size)
                self.assertEqual((profile, chosen_by), ("full-free", "default"))
                self.assertIn(f"semrush_monthly_units 5,000 picks no paid list on a {size} site: that vendor's paid "
                              "rows are Reserve there", reasons)

    def test_ahrefs_budget_counts_only_on_big_sites(self):
        ahrefs = budgets(ahrefs_monthly_units=320000)
        self.assertEqual(self.pick(budget=ahrefs, size="big")[:2], ("paid-big", "budgets"))
        self.assertEqual(self.pick(budget=ahrefs, size="small")[:2], ("full-free", "default"))

    def test_quick_words_beat_budgets(self):
        self.assertEqual(self.pick("Quick check of example.com", budget=budgets(dataforseo_monthly_usd=25))[:2],
                         ("quick", "request"))

    def test_full_words_override_option_quick(self):
        profile, chosen_by, reasons, _ = self.pick("Run a deep audit", option="quick")
        self.assertEqual((profile, chosen_by), ("full-free", "default"))
        self.assertTrue(any("override audit_profile=quick" in reason for reason in reasons), reasons)

    def test_no_paid_words_beat_budgets(self):
        self.assertEqual(self.pick("audit it, no paid tools", budget=budgets(dataforseo_monthly_usd=25))[:2],
                         ("full-free", "request"))

    def test_refusing_paid_tools_never_picks_paid(self):
        for request in ("I don't want paid tools", "never use paid tools", "avoid paid tools",
                        "free tools, not paid tools", "use free tools", "a free audit please", "skip paid tools",
                        "We do not want paid tools", "no need for paid tools"):
            for budget in (budgets(dataforseo_monthly_usd=25), ZEROS):
                with self.subTest(request=request, budget=budget["dataforseo_monthly_usd"]):
                    profile, chosen_by, _, questions = self.pick(request, budget=budget)
                    self.assertEqual((profile, chosen_by, questions), ("full-free", "request", []))

    def test_paid_search_campaigns_are_not_a_request_for_paid_tools(self):
        request = "we run it with paid search campaigns"
        self.assertEqual(self.pick(request, budget=budgets(dataforseo_monthly_usd=25))[:2], ("paid-small", "budgets"))
        _, chosen_by, _, questions = self.pick(request)
        self.assertEqual((chosen_by, questions), ("default", []))

    def test_quick_wording_beats_budgets(self):
        dataforseo = budgets(dataforseo_monthly_usd=25)
        for request in ("Do a quick SEO audit of example.com", "quick review of the homepage", "quick checks please"):
            with self.subTest(request=request):
                self.assertEqual(self.pick(request, budget=dataforseo)[:2], ("quick", "request"))

    def test_a_quick_checkout_flow_gets_the_full_audit(self):
        self.assertEqual(self.pick("audit our quick checkout flow", budget=budgets(dataforseo_monthly_usd=25))[:2],
                         ("paid-small", "budgets"))

    def test_naming_a_paid_vendor_asks_for_paid(self):
        self.assertEqual(self.pick("use Ahrefs and DataForSEO", budget=budgets(dataforseo_monthly_usd=25))[:2],
                         ("paid-small", "request"))
        profile, chosen_by, reasons, questions = self.pick("use Semrush", budget=budgets(semrush_monthly_units=5000))
        self.assertEqual((profile, chosen_by, len(questions)), ("full-free", "fallback", 1))
        self.assertIn("semrush_monthly_units 5,000 picks no paid list on a small site: that vendor's paid rows are "
                      "Reserve there", reasons)

    def test_option_full_free_beats_budgets(self):
        self.assertEqual(self.pick(option="full-free", budget=budgets(dataforseo_monthly_usd=25), size="big")[:2],
                         ("full-free", "option"))

    def test_paid_words_without_a_budget_fall_back_with_one_question(self):
        profile, chosen_by, _, questions = self.pick("Use paid tools for this audit")
        self.assertEqual((profile, chosen_by), ("full-free", "fallback"))
        self.assertEqual(len(questions), 1)
        self.assertIn("Budget settings", questions[0])

    def test_option_paid_with_only_ahrefs_on_a_small_site_falls_back(self):
        self.assertEqual(self.pick(option="paid", budget=budgets(ahrefs_monthly_units=320000))[:2],
                         ("full-free", "fallback"))

    def test_connected_server_without_a_budget_is_a_question_only_by_default(self):
        questions = self.pick(connected=frozenset({"dfs-mcp"}))[3]
        self.assertEqual(len(questions), 1)
        self.assertIn("dataforseo_monthly_usd", questions[0])
        self.assertEqual(self.pick("free only, please", connected=frozenset({"dfs-mcp"}))[3], [])

    def test_connected_ahrefs_mcp_asks_nothing(self):
        self.assertEqual(self.pick(connected=frozenset({"plugin_seo-suite-ahrefs_ahrefs"}), size="big")[3], [])

    def test_connected_dataforseo_still_asks_on_big_sites(self):
        questions = self.pick(connected=frozenset({"dfs-mcp", "plugin_seo-suite-ahrefs_ahrefs"}), size="big")[3]
        self.assertEqual(len(questions), 1)
        self.assertIn("dataforseo_monthly_usd", questions[0])

    def test_pick_ignores_the_environment(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_AUDIT_PROFILE": "quick",
                                          "CLAUDE_PLUGIN_OPTION_DATAFORSEO_MONTHLY_USD": "25"}):
            self.assertEqual(ap.pick(frozenset(), "auto", ZEROS, frozenset(), "small")[0], "full-free")


class PhraseTest(unittest.TestCase):
    def test_phrases(self):
        cases = {"Any quick wins?": set(), "unpaid tools are fine": set(), "Free only. Don’t spend": {"free"},
                 "  QUICK\n   Check  please": {"quick"}, "a spot-check of /pricing": {"quick"},
                 "no paid tools": {"free", "paid"}, "a thorough audit": {"full"}, "audit it thoroughly": {"full"},
                 "I don't want paid tools": {"free", "paid"}, "I do not want paid tools": {"free", "paid"},
                 "never use paid tools": {"free", "paid"}, "avoid paid tools": {"free", "paid"},
                 "skip paid tools": {"free", "paid"}, "no need for paid tools": {"free", "paid"},
                 "free tools, not paid tools": {"free", "paid"}, "use free tools": {"free"},
                 "a free audit please": {"free"}, "the free stack is enough": {"free"}, "no paid-for tools": {"free"},
                 "we run it with paid search campaigns": set(), "Do a quick SEO audit of example.com": {"quick"},
                 "quick review of the homepage": {"quick"}, "audit our quick checkout flow": set(),
                 "quick checks please": {"quick"}, "spot-checks of /pricing": {"quick"}, "a quick check-up": {"quick"},
                 "use Semrush": {"paid"}, "use Ahrefs and DataForSEO": {"paid"}, "use SE Ranking": {"paid"}}
        for text, intents in cases.items():
            with self.subTest(text=text):
                self.assertEqual(ap.request_intents(text), frozenset(intents))


class SettingsTest(unittest.TestCase):
    def test_depth_and_stack(self):
        quick = ap.profile_settings("quick", "big")
        self.assertEqual((quick["crawl"], quick["competitors"], quick["cross_checks"]), ({"mode": "none"}, 0, False))
        self.assertEqual(ap.profile_settings("full-free", "small")["crawl"], {"mode": "site", "max_pages": 2001})
        big = ap.profile_settings("full-free", "big")
        self.assertEqual((big["crawl"], big["competitors"]), ({"mode": "sections", "max_pages": 2000}, 10))
        self.assertEqual(ap.profile_settings("paid-big", "big")["stack"], "big")


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, name, content):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def run_picker(self, *args, options=None, request="Audit example.com"):
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_PLUGIN_")}
        env.update({"CLAUDE_PLUGIN_OPTION_" + key: value for key, value in (options or {}).items()})
        return subprocess.run([sys.executable, PICKER, "--request-file", self.write("request.txt", request), *args],
                              env=env, capture_output=True, text=True, timeout=30)

    def sitemap(self, total, site="https://example.com/"):
        return self.write(f"sitemap-{total}.json", {"site": site, "files": [], "total_urls": total, "findings": []})

    def test_exported_budget_on_a_big_site_picks_paid_big(self):
        proc = self.run_picker("--sitemap", self.sitemap(5400),
                               options={"AUDIT_PROFILE": "auto", "DATAFORSEO_MONTHLY_USD": "25"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(list(out), JSON_KEYS)
        self.assertEqual((out["profile"], out["chosen_by"], out["options_exported"]), ("paid-big", "budgets", True))
        self.assertEqual(out["budgets"]["dataforseo_monthly_usd"], 25.0)
        self.assertEqual(out["reasons"][0], "5,400 sitemap URLs > 2,000: big")

    def test_bad_option_exits_2(self):
        proc = self.run_picker(options={"AUDIT_PROFILE": "deep"})
        self.assertEqual((proc.returncode, proc.stdout), (2, ""))
        self.assertIn("audit_profile", proc.stderr)

    def test_bad_budget_exits_2(self):
        self.assertEqual(self.run_picker(options={"DATAFORSEO_MONTHLY_USD": "abc"}).returncode, 2)

    def test_ignore_options_keeps_the_run_going(self):
        proc = self.run_picker("--ignore-options", options={"AUDIT_PROFILE": "deep"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual((out["profile"], out["audit_profile_option"], out["options_exported"]),
                         ("full-free", "auto", True))
        self.assertTrue(any("plugin options ignored (--ignore-options)" in r for r in out["reasons"]), out["reasons"])

    def test_page_data_never_picks_a_profile(self):
        proc = self.run_picker("--sitemap", self.sitemap(300, "https://x.test/quick-check-use-paid-tools"),
                               request="Audit x.test")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual((out["profile"], out["chosen_by"]), ("full-free", "default"))
        self.assertNotIn("quick-check", proc.stdout)

    def test_refusal_with_a_budget_stays_free(self):
        proc = self.run_picker("--sitemap", self.sitemap(1200), options={"DATAFORSEO_MONTHLY_USD": "25"},
                               request="Audit example.com. I don't want paid tools.")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual((out["profile"], out["chosen_by"], out["questions"]), ("full-free", "request", []))
        self.assertIn("dataforseo_monthly_usd 25 not used: the request asks for free tools", out["reasons"])

    def test_missing_sitemap_file_fails_loudly(self):
        proc = self.run_picker("--sitemap", os.path.join(self.tmp, "missing.json"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")


class DriftTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_profiles_md_names_every_id_and_option(self):
        doc = self.read("references", "profiles.md")
        for name in [*ap.PROFILES, *ap.OPTION_VALUES]:
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", doc)

    def test_profiles_md_phrase_table_is_the_picker_table(self):
        doc, heading = self.read("references", "profiles.md"), "## 5. Request words and option values"
        self.assertIn(heading, doc)
        section = doc.split(heading)[1].split("\n## ")[0]
        for intent, phrases in ap.REQUEST_WORDS.items():
            with self.subTest(intent=intent):
                row = re.search(rf"^\| {intent} \| (.+) \|$", section, re.M)
                self.assertIsNotNone(row, f"profiles.md §5 has no {intent} row")
                self.assertEqual(re.findall(r"`([^`]+)`", row.group(1)), list(phrases))

    def test_beginner_guide_phrase_is_quick(self):
        phrases = re.findall(r'"([^"]+)" → \*\*seo-audit\*\*', self.read("references", "guide-beginner.md"))
        self.assertTrue(phrases, "guide-beginner.md no longer sends a phrase to seo-audit")
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(ap.request_intents(phrase), frozenset({"quick"}))

    def test_router_sends_quick_checks_to_seo_audit(self):
        router = self.read("skills", "seo-suite", "SKILL.md")
        line = re.search(r'^- "(Quick check of one page)" → (.+)$', router, re.M)
        self.assertIsNotNone(line, "the router's quick start lost its quick-check line")
        self.assertEqual(ap.request_intents(line.group(1)), frozenset({"quick"}))
        self.assertTrue(line.group(2).startswith("`seo-audit`"), line.group(2))

    def test_tools_md_still_has_the_stacks_the_profiles_point_to(self):
        tools = self.read("references", "tools.md")
        self.assertIn("### Default: big website, free only", tools)
        self.assertEqual((tools.count("**Small sites**"), tools.count("**Big sites**")), (5, 5))

    def test_plugin_option_matches_the_picker(self):
        option = json.loads(self.read(".claude-plugin", "plugin.json"))["userConfig"]["audit_profile"]
        self.assertEqual((option["options"], option["default"]), (list(ap.OPTION_VALUES), "auto"))

    def test_paid_list_vendors_are_guarded(self):
        for vendors in ap.PAID_LIST_VENDORS.values():
            for vendor in vendors:
                with self.subTest(vendor=vendor):
                    self.assertIsNotNone(cg.VENDORS[vendor][1])


if __name__ == "__main__":
    unittest.main()
