"""Audit profile picker: size from sitemaps and the crawl, the free default, budgets per size, request words with their
negations and the option, options never configured, the CLI contract (exit codes, JSON out, injection), drift against
profiles.md, tools.md and plugin.json, and seo-audit step 5's headless Chrome renderer.
Run: python3 -m unittest discover -s tests"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
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

    def test_a_refused_vendor_or_paid_phrase_is_no_paid_request(self):
        for request, chosen_by in (("don't use Semrush", "default"), ("do not use Ahrefs", "default"),
                                   ("audit it without Ahrefs", "default"), ("we can't use paid tools", "default"),
                                   ("never use paid data", "request")):
            with self.subTest(request=request):
                profile, picked_by, _, questions = self.pick(request)
                self.assertEqual((profile, picked_by, questions), ("full-free", chosen_by, []))

    def test_a_refused_vendor_leaves_the_budgets_to_decide(self):
        self.assertEqual(self.pick("don't use Semrush", budget=budgets(dataforseo_monthly_usd=25))[:2],
                         ("paid-small", "budgets"))

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
                 "no paid tools": {"free"}, "a thorough audit": {"full"}, "audit it thoroughly": {"full"},
                 "I don't want paid tools": {"free"}, "I do not want paid tools": {"free"},
                 "never use paid tools": {"free"}, "avoid paid tools": {"free"},
                 "skip paid tools": {"free"}, "no need for paid tools": {"free"},
                 "free tools, not paid tools": {"free"}, "use free tools": {"free"},
                 "a free audit please": {"free"}, "the free stack is enough": {"free"}, "no paid-for tools": {"free"},
                 "we run it with paid search campaigns": set(), "Do a quick SEO audit of example.com": {"quick"},
                 "quick review of the homepage": {"quick"}, "audit our quick checkout flow": set(),
                 "quick checks please": {"quick"}, "spot-checks of /pricing": {"quick"}, "a quick check-up": {"quick"},
                 "use Semrush": {"paid"}, "use Ahrefs and DataForSEO": {"paid"}, "use SE Ranking": {"paid"}}
        for text, intents in cases.items():
            with self.subTest(text=text):
                self.assertEqual(ap.request_intents(text), frozenset(intents))

    def test_a_negated_paid_phrase_is_ignored(self):
        cases = {"don't use Semrush": set(), "Don’t use Semrush": set(), "dont use semrush": set(),
                 "do not use DataForSEO": set(), "without Ahrefs": set(), "never use paid data": {"free"},
                 "we can't use paid tools": set(), "we won't use SE Ranking": set(),
                 "we cannot use paid tools": set(), "We cannot use Semrush": set(),
                 "we cant use paid tools": set(), "we wont use Semrush": set(), "we shouldnt use paid tools": set(),
                 # overlapping paid phrases ("use paid" + "paid tools") share the first one's window
                 "I don't want to use paid tools": set(), "no need to use paid tools": set(),
                 # a clause break ends the negation, and so do three other words in between
                 "No problem, use paid tools": {"paid"}, "Don't skimp: use paid tools": {"paid"},
                 "don't use Semrush, use DataForSEO": {"paid"}, "use paid tools but not Semrush": {"paid"},
                 "no one here minds if we use paid tools": {"paid"},
                 # only paid phrases are checked: a negated depth or free phrase still counts
                 "not a deep dive, just a quick look": {"full", "quick"}, "don't stick to free tools": {"free"}}
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

    def test_options_never_configured_pick_exactly_as_the_defaults(self):
        # a fresh install: no CLAUDE_PLUGIN_OPTION_* variable at all, or the empty ones a hook might pass on
        defaults = {"AUDIT_PROFILE": "auto", **{key.upper(): "0" for key in ap.REPORTED_BUDGETS}}
        empty = dict.fromkeys(defaults, "")
        args = ("--sitemap", self.sitemap(5400), "--connected", "dfs-mcp")
        outputs = {name: json.loads(self.run_picker(*args, options=options).stdout)
                   for name, options in (("absent", None), ("defaults", defaults), ("empty", empty))}
        absent = outputs["absent"]
        self.assertEqual((absent["profile"], absent["chosen_by"], absent["audit_profile_option"], absent["budgets"],
                          absent["options_exported"]), ("full-free", "default", "auto", ZEROS, False))
        self.assertTrue(absent["reasons"][1].endswith(" (none exported to Bash: defaults)"), absent["reasons"])
        for name in ("defaults", "empty"):
            with self.subTest(options=name):
                out = outputs[name]
                self.assertTrue(out["options_exported"])
                self.assertEqual(out["reasons"][1] + " (none exported to Bash: defaults)", absent["reasons"][1])
                for key in JSON_KEYS:
                    if key not in ("options_exported", "reasons"):
                        self.assertEqual(out[key], absent[key], key)
                self.assertEqual(out["reasons"][2:], absent["reasons"][2:])

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

    def test_profiles_md_negation_row_is_the_picker_table(self):
        section = self.read("references", "profiles.md").split("## 5. Request words and option values")[1]
        row = re.search(r"^\| negation \| (.+) \|$", section.split("\n## ")[0], re.M)
        self.assertIsNotNone(row, "profiles.md §5 has no negation row")
        self.assertEqual(re.findall(r"`([^`]+)`", row.group(1)), [*ap.NEGATIONS, "*" + ap.NEGATION_SUFFIX])
        self.assertIn(f"{ap.NEGATION_WINDOW_WORDS} words", section)

    def test_plugin_json_defaults_are_what_absent_options_read_as(self):
        config = json.loads(self.read(".claude-plugin", "plugin.json"))["userConfig"]
        self.assertEqual(ap.read_profile_option({}), config["audit_profile"]["default"])
        read = cg.read_options({})
        for key in cg.OPTION_DEFAULTS:
            with self.subTest(option=key):
                self.assertEqual(read[key], config[key]["default"])

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


SHELLS = [shell for shell in ("bash", "zsh") if shutil.which(shell)]  # the Bash tool runs the user's shell
# Its content arrives after the load event, as a single-page app's fetched data does
JS_PAGE = """<!doctype html><html lang="en"><head><title>Raw title</title></head><body><div id="app"></div>
<script>setTimeout(function () { document.title = "Rendered title"; document.getElementById("app").innerHTML =
"<h1>Hello from JS</h1><p>" + "word ".repeat(200) + "</p>"; }, 1500);</script></body></html>"""


class RenderStepTest(unittest.TestCase):
    """seo-audit step 5's commands, run as written: find Chrome or Chromium, then render or skip with a note."""

    @staticmethod
    def read_step():
        with open(os.path.join(ROOT, "skills", "seo-audit", "SKILL.md"), encoding="utf-8") as fh:
            return fh.read().split("\n5. **JavaScript sites.**")[1].split("\n6. **")[0]

    @classmethod
    def setUpClass(cls):
        cls.blocks = [textwrap.dedent(block) for block in re.findall(r"```bash\n(.*?)\n *```", cls.read_step(), re.S)]

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        os.mkdir(os.path.join(self.tmp, "seo-work"))

    def run_block(self, shell, index, env, url="https://example.com/"):
        script = self.blocks[index].replace("<template>", "home").replace("URL", shlex.quote(url))
        return subprocess.run([shell, "-c", script + '\necho "found=$CHROME"'], cwd=self.tmp,
                              env={**env, "TMPDIR": self.tmp}, capture_output=True, text=True, timeout=60)

    def stub_chrome(self, body='echo "<html><body><h1>stub</h1></body></html>"'):
        """A Chrome stand-in that records its arguments, and whether its --user-data-dir existed while it ran."""
        path = os.path.join(self.tmp, "chrome-stub")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nprintf "%s\\n" "$@" > "$0.args"\n'
                     'for a; do case "$a" in --user-data-dir=*) [ -d "${a#*=}" ] && echo yes > "$0.profile";; esac; done\n'
                     + body + "\n")
        os.chmod(path, 0o755)
        return path

    def test_the_step_finds_chrome_then_renders(self):
        self.assertEqual(len(self.blocks), 3, "step 5 needs a find block, a render block and the render_diff block")
        self.assertIn("render_diff.py", self.blocks[2])

    def test_chrome_given_in_the_environment_is_used(self):
        stub = self.stub_chrome()
        for shell in SHELLS:
            with self.subTest(shell=shell):
                found = self.run_block(shell, 0, {**os.environ, "CHROME": stub})
                self.assertEqual(found.stdout.strip(), f"found={stub}", found.stderr)

    def test_a_chromium_on_the_path_is_found(self):
        bin_dir = os.path.join(self.tmp, "bin")
        os.mkdir(bin_dir)
        shutil.copy(self.stub_chrome(), os.path.join(bin_dir, "chromium"))
        env = {k: v for k, v in os.environ.items() if k != "CHROME"}
        for shell in SHELLS:
            with self.subTest(shell=shell):
                found = self.run_block(shell, 0, {**env, "PATH": bin_dir + os.pathsep + env["PATH"]})
                path = found.stdout.strip().removeprefix("found=")
                self.assertTrue(path and os.access(path, os.X_OK), found.stdout + found.stderr)  # or the installed app

    def test_render_runs_headless_with_a_timeout_and_a_fresh_profile(self):
        stub = self.stub_chrome()
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc = self.run_block(shell, 1, {**os.environ, "CHROME": stub})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                with open(os.path.join(self.tmp, "seo-work", "rendered-home.html"), encoding="utf-8") as fh:
                    self.assertIn("<h1>stub</h1>", fh.read())
                with open(stub + ".args", encoding="utf-8") as fh:
                    args = fh.read().split("\n")[:-1]
                self.assertEqual(args[-2:], ["--dump-dom", "https://example.com/"])
                self.assertIn("--headless", args)
                for flag in ("--virtual-time-budget", "--timeout"):  # settle scripts; cap real time
                    self.assertTrue(any(re.fullmatch(flag + r"=\d+", arg) for arg in args), args)
                profile = next(arg for arg in args if arg.startswith("--user-data-dir="))
                self.assertTrue(os.path.exists(stub + ".profile"), "the profile didn't exist while Chrome ran")
                self.assertFalse(os.path.exists(profile.split("=", 1)[1]), "the profile is left behind")
                os.remove(stub + ".profile")

    def test_a_page_that_never_settles_is_killed_at_the_cap(self):
        stub = self.stub_chrome(body="exec sleep 30")
        cap = "' 60 \"$CHROME\""
        self.assertIn(cap, self.blocks[1], "the render block caps Chrome at 60 seconds of real time")
        self.blocks = [self.blocks[0], self.blocks[1].replace(cap, "' 1 \"$CHROME\""), self.blocks[2]]
        for shell in SHELLS:
            with self.subTest(shell=shell):
                started = time.monotonic()
                proc = self.run_block(shell, 1, {**os.environ, "CHROME": stub})
                self.assertLess(time.monotonic() - started, 15, "Chrome was not killed at the cap")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(os.path.getsize(os.path.join(self.tmp, "seo-work", "rendered-home.html")), 0)

    def test_the_find_and_render_blocks_run_in_one_bash_call(self):
        step = self.read_step()
        self.assertIn("one Bash call", step, "a variable set in one Bash call is gone in the next")
        bin_dir = os.path.join(self.tmp, "bin")
        os.mkdir(bin_dir)
        shutil.copy(self.stub_chrome(), os.path.join(bin_dir, "chromium"))
        env = {k: v for k, v in os.environ.items() if k != "CHROME"}
        self.blocks = [self.blocks[0] + "\n" + self.blocks[1]]
        proc = self.run_block(SHELLS[0], 0, {**env, "PATH": bin_dir + os.pathsep + env["PATH"]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertGreater(os.path.getsize(os.path.join(self.tmp, "seo-work", "rendered-home.html")), 0)

    def test_no_chrome_skips_with_a_note_and_writes_nothing(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                proc = self.run_block(shell, 1, {**os.environ, "CHROME": ""})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("JavaScript rendering not checked", proc.stdout)
                self.assertEqual(os.listdir(os.path.join(self.tmp, "seo-work")), [])

    def test_installed_chrome_renders_javascript_for_render_diff(self):
        env = {k: v for k, v in os.environ.items() if k != "CHROME"}
        chrome = self.run_block(SHELLS[0], 0, env).stdout.strip().removeprefix("found=")
        if not chrome:
            self.skipTest("no Chrome or Chromium installed")
        page = os.path.join(self.tmp, "page.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(JS_PAGE)
        proc = self.run_block(SHELLS[0], 1, {**env, "CHROME": chrome}, url="file://" + page)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rendered = os.path.join(self.tmp, "seo-work", "rendered-home.html")
        diff = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "render_diff.py"), "--raw", page,
                               "--rendered", rendered, "--base-url", "https://example.com/"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(diff.returncode, 0, diff.stderr)
        report = json.loads(diff.stdout)
        self.assertEqual((report["rendered"]["title"], report["rendered"]["h1"]), ("Rendered title", ["Hello from JS"]))
        self.assertIn("title changes after JavaScript", report["warnings"])


if __name__ == "__main__":
    unittest.main()
