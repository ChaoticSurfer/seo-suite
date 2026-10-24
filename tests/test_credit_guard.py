"""Credit guard: hook contract (exit codes, JSON out), naming variants, cache, clamp, budgets, ledger, circuit breaker.
Run: python3 -m unittest discover -s tests"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GUARD = os.path.join(ROOT, "scripts", "credit_guard.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import credit_guard as cg  # noqa: E402

with open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as _fh:
    HOOKS = json.load(_fh)["hooks"]
MATCHER = re.compile(HOOKS["PreToolUse"][0]["matcher"])  # same syntax in JavaScript and Python for this pattern

PAID_VARIANTS = {
    "mcp__semrush__execute_report": "semrush",
    "mcp__semrush-key__execute_report": "semrush",
    "mcp__plugin_seo-suite-semrush_semrush__execute_report": "semrush",
    "mcp__claude_ai_Semrush__execute_report": "semrush",
    "mcp__ahrefs__site-explorer-organic-keywords": "ahrefs",
    "mcp__plugin_seo-suite-ahrefs_ahrefs__site-explorer-organic-keywords": "ahrefs",
    "mcp__claude_ai_Ahrefs__site-explorer-organic-keywords": "ahrefs",
    "mcp__dataforseo__api_request": "dataforseo",
    "mcp__dfs-mcp__api_request": "dataforseo",
    "mcp__plugin_seo-suite-dataforseo_dataforseo__api_request": "dataforseo",
    "mcp__claude_ai_DataForSEO__api_request": "dataforseo",
    "mcp__plugin_semrush-tools_dataforseo__api_request": "dataforseo",  # server key wins over the plugin name
    "mcp__similarweb__get_traffic": "similarweb",
    "mcp__claude_ai_Similarweb__get_traffic": "similarweb",
    "mcp__se-ranking__keywords": "seranking",
    "mcp__claude_ai_SE_Ranking__keywords": "seranking",
    "mcp__keywords-everywhere__volume": "keywords-everywhere",
    "mcp__claude_ai_Keywords_Everywhere__volume": "keywords-everywhere",
    "mcp__alsoasked__search": "alsoasked",
    "mcp__claude_ai_AlsoAsked__search": "alsoasked",
    "mcp__otterly__prompts": "otterly",
    "mcp__claude_ai_Otterly_AI__prompts": "otterly",
    "mcp__screaming-frog__sf_crawl": "screaming-frog",
    "mcp__claude_ai_Screaming_Frog__sf_crawl": "screaming-frog",
    "mcp__sitebulb__audit_report_summary": "sitebulb",
    "mcp__claude_ai_Sitebulb__audit_report_summary": "sitebulb",
    "mcp__lumar__analyze_run_crawl": "lumar",
    "mcp__plugin_lumar-analytics_lumar__analyze_run_crawl": "lumar",
}
UNRELATED = ["Bash", "Read", "WebSearch", "mcp__plugin_vercel_vercel__list_projects", "mcp__linear__get_issue",
             "mcp__pdfs__read", "mcp__claude-in-chrome__navigate"]

BUDGETS = {"SEMRUSH_MONTHLY_UNITS": "50000", "AHREFS_MONTHLY_UNITS": "200000", "DATAFORSEO_MONTHLY_USD": "50",
           "OTHER_MONTHLY_USD": "20"}

SEMRUSH_TOOL = "mcp__plugin_seo-suite-semrush_semrush__execute_report"
SEMRUSH_INPUT = {"report": "phrase_related", "params": {"phrase": "english tutor", "database": "uk",
                                                        "export_columns": "Ph,Nq,Kd", "display_limit": 500}}


def semrush_call(**overrides):
    payload = {"session_id": "run-1", "tool_use_id": "toolu_sem1", "tool_name": SEMRUSH_TOOL,
               "tool_input": json.loads(json.dumps(SEMRUSH_INPUT)), "agent_id": "agent-a", "agent_type": "seo-test",
               "mcp_server": {"name": "plugin:seo-suite-semrush:semrush", "source": "plugin"}}
    payload.update(overrides)
    return payload


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_PLUGIN_")}
        self.env["CLAUDE_PLUGIN_DATA"] = self.tmp.name
        for key, value in BUDGETS.items():
            self.env["CLAUDE_PLUGIN_OPTION_" + key] = value
        self.state = os.path.join(self.tmp.name, "credit-guard")
        self.ledger = os.path.join(self.state, "ledger.jsonl")

    def run_guard(self, event, payload, raw=None):
        stdin = raw if raw is not None else json.dumps(payload)
        proc = subprocess.run([sys.executable, GUARD, event], input=stdin, capture_output=True, text=True,
                              env=self.env, timeout=30)
        out = json.loads(proc.stdout) if proc.stdout.strip() else None
        return proc.returncode, out, proc.stderr

    def pre(self, payload):
        code, out, err = self.run_guard("pre", payload)
        self.assertEqual(code, 0, err)
        return out["hookSpecificOutput"] if out else None

    def ledger_entries(self):
        if not os.path.exists(self.ledger):
            return []
        with open(self.ledger, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def seed_ledger(self, *entries):
        os.makedirs(self.state, exist_ok=True)
        with open(self.ledger, "a", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry) + "\n")

    def settled(self, cost, bucket="semrush", session="run-1", tool_use_id="toolu_old", when=None):
        when = when or cg.utc_now()
        return {"ts": when.isoformat(timespec="seconds"), "month": when.strftime("%Y-%m"), "event": "settle",
                "bucket": bucket, "vendor": bucket, "cost": cost, "session_id": session, "tool_use_id": tool_use_id}


class NamingTest(unittest.TestCase):
    def test_every_naming_variant_is_matched_and_identified(self):
        for name, vendor in PAID_VARIANTS.items():
            with self.subTest(tool=name):
                self.assertTrue(MATCHER.search(name), "hooks.json matcher misses it")
                self.assertEqual(cg.identify(name, None), (vendor, name.split("__", 2)[2]))

    def test_unrelated_tools_are_ignored(self):
        for name in UNRELATED:
            with self.subTest(tool=name):
                self.assertIsNone(MATCHER.search(name))
                self.assertIsNone(cg.identify(name, None))

    def test_mcp_server_name_is_used_when_present(self):
        self.assertEqual(cg.identify("mcp__custom__execute_report", {"name": "plugin:seo-suite-semrush:semrush"}),
                         ("semrush", "execute_report"))

    def test_hooks_file_shape(self):
        for event, arg in (("PreToolUse", "pre"), ("PostToolUse", "post"), ("PostToolUseFailure", "post-failure"),
                           ("PostToolBatch", "batch")):
            hook = HOOKS[event][0]["hooks"][0]
            self.assertEqual(hook["command"], "python3")
            self.assertEqual(hook["args"], ["${CLAUDE_PLUGIN_ROOT}/scripts/credit_guard.py", arg])
        self.assertEqual(HOOKS["PreToolUse"][0]["hooks"][0]["onFailure"], "block")
        self.assertNotIn("matcher", HOOKS["PostToolBatch"][0])  # PostToolBatch has no matcher support


class PreTest(GuardCase):
    def test_paid_variants_get_a_decision(self):
        for name in ("mcp__semrush__execute_report", "mcp__semrush-key__execute_report",
                     "mcp__claude_ai_Semrush__execute_report", SEMRUSH_TOOL):
            with self.subTest(tool=name):
                out = self.pre(semrush_call(tool_name=name, tool_use_id="t-" + name, mcp_server=None))
                self.assertEqual(out["permissionDecision"], "allow")

    def test_free_tools_pass_without_opinion(self):
        free = [
            ("mcp__plugin_seo-suite-semrush_semrush__get_report_schema", {"report": "phrase_related"}),
            ("mcp__semrush__keyword_research", {}),
            ("mcp__plugin_seo-suite-ahrefs_ahrefs__subscription-info-limits-and-usage", {}),
            ("mcp__ahrefs__rank-tracker-overview", {"project_id": 1}),
            ("mcp__ahrefs__gsc-keywords", {"project_id": 1}),
            ("mcp__dataforseo__docs_search", {"url": "x"}),
            ("mcp__dataforseo__api_request", {"method": "GET", "path": "/v3/appendix/user_data"}),
            ("mcp__dataforseo__api_request", {"method": "GET", "path": "/v3/serp/google/organic/task_get/advanced/1"}),
            ("mcp__screaming-frog__sf_crawl", {"crawl_url": "https://example.test/"}),
            ("mcp__lumar__analyze_list_projects", {}),
        ]
        for name, tool_input in free:
            with self.subTest(tool=name):
                code, out, err = self.run_guard("pre", {"tool_name": name, "tool_input": tool_input})
                self.assertEqual((code, out), (0, None), err)
        self.assertEqual(self.ledger_entries(), [])

    def test_ahrefs_anonymous_queries_is_billed(self):
        out = self.pre({"tool_name": "mcp__ahrefs__gsc-anonymous-queries", "tool_input": {"limit": 10},
                        "tool_use_id": "t1", "session_id": "s"})
        self.assertIsNotNone(out)

    def test_clamp_keeps_every_other_field(self):
        out = self.pre(semrush_call())
        expected = json.loads(json.dumps(SEMRUSH_INPUT))
        expected["params"]["display_limit"] = 50
        self.assertEqual(out["permissionDecision"], "allow")  # 40 x 50 = 2,000 units, under 5% of 50,000
        self.assertEqual(out["updatedInput"], expected)
        self.assertIn("2,000 units", out["permissionDecisionReason"])
        self.assertIn("display_limit", out["additionalContext"])

    def test_zero_limit_means_vendor_default_and_is_clamped(self):
        call = semrush_call()
        call["tool_input"]["params"]["display_limit"] = 0
        self.assertEqual(self.pre(call)["updatedInput"]["params"]["display_limit"], 50)

    def test_missing_semrush_limit_is_denied_with_schema_hint(self):
        call = semrush_call()
        del call["tool_input"]["params"]["display_limit"]
        out = self.pre(call)
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("get_report_schema", out["permissionDecisionReason"])

    def test_fixed_price_report_needs_no_limit(self):
        out = self.pre(semrush_call(tool_input={"report": "backlinks_overview", "params": {"target": "example.test"}}))
        self.assertEqual(out["permissionDecision"], "allow")
        self.assertNotIn("updatedInput", out)

    def test_ahrefs_missing_limit_is_added(self):
        tool_input = {"target": "example.test", "select": "keyword,volume,keyword_difficulty", "country": "gb",
                      "order_by": "volume:desc"}
        out = self.pre({"tool_name": "mcp__plugin_seo-suite-ahrefs_ahrefs__site-explorer-organic-keywords",
                        "tool_input": tool_input, "tool_use_id": "t1", "session_id": "s"})
        self.assertEqual(out["updatedInput"], {**tool_input, "limit": 50})
        self.assertIn("1,050 units", out["permissionDecisionReason"])  # 50 rows x (1 + 10 + 10)

    def test_dataforseo_task_limit_is_clamped_inside_data(self):
        tool_input = {"method": "POST", "path": "/v3/dataforseo_labs/google/keyword_ideas/live",
                      "data": [{"keywords": ["english tutor"], "location_code": 2826, "limit": 700}]}
        out = self.pre({"tool_name": "mcp__dataforseo__api_request", "tool_input": tool_input, "tool_use_id": "t1",
                        "session_id": "s"})
        expected = json.loads(json.dumps(tool_input))
        expected["data"][0]["limit"] = 50
        self.assertEqual(out["updatedInput"], expected)
        self.assertIn("$0.0180", out["permissionDecisionReason"])  # 0.012 + 50 x 0.00012

    def test_cache_hit_denies_with_path(self):
        self.pre(semrush_call())
        executed = semrush_call()
        executed["tool_input"]["params"]["display_limit"] = 50
        executed["tool_response"] = [{"type": "text", "text": "Keyword;Search Volume\nenglish tutor near me;1300"}]
        code, out, err = self.run_guard("post", executed)
        self.assertEqual(code, 0, err)
        out = self.pre(semrush_call(tool_use_id="toolu_sem2"))  # the unclamped request maps to the same cache entry
        self.assertEqual(out["permissionDecision"], "deny")
        path = re.search(r"Read (\S+\.json)", out["permissionDecisionReason"]).group(1)
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["response"], executed["tool_response"])

    def test_expired_cache_is_not_used(self):
        executed = semrush_call()
        executed["tool_input"]["params"]["display_limit"] = 50
        executed["tool_response"] = "Keyword;Search Volume\nx;10"
        self.run_guard("post", executed)
        path = cg.cache_file(self.state, "semrush", cg.cache_key("semrush", "execute_report", executed["tool_input"]))
        with open(path, encoding="utf-8") as fh:
            record = json.load(fh)
        record["fetched_at"] = (cg.utc_now() - dt.timedelta(days=31)).isoformat()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh)
        self.assertEqual(self.pre(semrush_call(tool_use_id="t2"))["permissionDecision"], "allow")

    def test_semrush_cache_never_exceeds_30_days(self):
        options = dict(cg.OPTION_DEFAULTS, cache_ttl_days=90)
        self.assertEqual(cg.cache_ttl_days("semrush", "keywords", options), 30)
        self.assertEqual(cg.cache_ttl_days("dataforseo", "keywords", options), 90)

    def test_zero_budget_denies(self):
        self.env["CLAUDE_PLUGIN_OPTION_SEMRUSH_MONTHLY_UNITS"] = "0"
        out = self.pre(semrush_call())
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("semrush_monthly_units is 0", out["permissionDecisionReason"])

    def test_unset_budget_denies(self):
        del self.env["CLAUDE_PLUGIN_OPTION_AHREFS_MONTHLY_UNITS"]
        out = self.pre({"tool_name": "mcp__ahrefs__site-explorer-metrics", "tool_input": {"target": "example.test"},
                        "tool_use_id": "t1", "session_id": "s"})
        self.assertEqual(out["permissionDecision"], "deny")

    def test_over_monthly_budget_denies_with_maths(self):
        self.seed_ledger(self.settled(49000, session="other-run"))
        out = self.pre(semrush_call())
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("49,000 units of 50,000 units", out["permissionDecisionReason"])
        self.assertIn("1,000 units remain", out["permissionDecisionReason"])

    def test_last_month_does_not_count(self):
        self.seed_ledger(self.settled(49000, when=cg.utc_now() - dt.timedelta(days=40)))
        self.assertEqual(self.pre(semrush_call())["permissionDecision"], "allow")

    def test_per_run_cap_denies_but_other_runs_do_not_count(self):
        self.seed_ledger(self.settled(12000, session="run-1"), self.settled(20000, session="run-0", tool_use_id="t0"))
        out = self.pre(semrush_call())  # 12,000 + 2,000 > 25% of 50,000
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("per-run", out["permissionDecisionReason"])
        self.assertEqual(self.pre(semrush_call(session_id="run-2"))["permissionDecision"], "allow")

    def test_in_flight_reservation_counts(self):
        self.seed_ledger(self.settled(46500, session="other-run"))
        self.assertEqual(self.pre(semrush_call(tool_use_id="a"))["permissionDecision"], "allow")
        out = self.pre(semrush_call(tool_use_id="b", tool_input={**SEMRUSH_INPUT, "report": "phrase_questions"}))
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("2,000 units in flight", out["permissionDecisionReason"])

    def requests(self):
        path = os.path.join(self.state, "requests.jsonl")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_above_threshold_is_deferred_and_recorded(self):
        self.env["CLAUDE_PLUGIN_OPTION_ASK_ABOVE_PCT"] = "1"  # 500 units
        out = self.pre(semrush_call())
        self.assertEqual(out["permissionDecision"], "deny")  # never "ask": runs don't stop for questions
        reason = out["permissionDecisionReason"]
        self.assertIn("deferred: estimated 2,000 units > ask_above_pct 1%", reason)
        self.assertIn(os.path.join(self.state, "requests.jsonl"), reason)
        self.assertIn("end-of-run questions", reason)
        [request] = self.requests()
        self.assertEqual(sorted(request), sorted([
            "ts", "session_id", "agent_id", "vendor", "bucket", "tool", "call", "input_summary", "estimate",
            "currency", "price_known", "threshold", "reason", "request_key"]))
        self.assertEqual((request["vendor"], request["estimate"], request["currency"], request["threshold"],
                          request["price_known"], request["session_id"]), ("semrush", 2000, "units", 500, True, "run-1"))
        self.assertIn('"display_limit": 50', request["input_summary"])
        self.assertEqual(self.ledger_entries(), [])  # nothing reserved for a call that didn't run

    def test_repeated_deferral_is_recorded_once_per_run(self):
        self.env["CLAUDE_PLUGIN_OPTION_ASK_ABOVE_PCT"] = "1"
        self.pre(semrush_call())
        out = self.pre(semrush_call(tool_use_id="toolu_again"))
        self.assertIn("Already recorded", out["permissionDecisionReason"])
        self.pre(semrush_call(session_id="run-2"))
        self.assertEqual([r["session_id"] for r in self.requests()], ["run-1", "run-2"])

    def test_threshold_zero_defers_every_paid_call(self):
        self.env["CLAUDE_PLUGIN_OPTION_ASK_ABOVE_PCT"] = "0"
        out = self.pre({"tool_name": "mcp__dataforseo__api_request", "tool_use_id": "t1", "session_id": "s",
                        "tool_input": {"method": "POST", "path": "/v3/serp/google/organic/task_post",
                                       "data": [{"keyword": "english tutor", "location_code": 2826}]}})
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("deferred", out["permissionDecisionReason"])
        self.assertEqual(self.requests()[0]["currency"], "usd")

    def test_unknown_semrush_report_is_deferred(self):
        out = self.pre(semrush_call(tool_input={"report": "snapshot_info_new", "params": {"limit": 10}}))
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("no known price", out["permissionDecisionReason"])
        self.assertFalse(self.requests()[0]["price_known"])

    def test_hard_denies_win_over_deferral(self):
        self.env["CLAUDE_PLUGIN_OPTION_ASK_ABOVE_PCT"] = "1"
        self.seed_ledger(self.settled(49000, session="other-run"))
        out = self.pre(semrush_call())
        self.assertIn("over the monthly semrush budget", out["permissionDecisionReason"])
        self.assertEqual(self.requests(), [])

    def test_guard_never_asks(self):
        with open(GUARD, encoding="utf-8") as fh:
            self.assertNotIn('pre_output("ask"', fh.read())

    def test_malformed_stdin_fails_closed(self):
        code, out, err = self.run_guard("pre", None, raw="{not json")
        self.assertEqual(code, 2)
        self.assertIn("failed closed", err)

    def test_corrupt_ledger_fails_closed(self):
        os.makedirs(self.state, exist_ok=True)
        with open(self.ledger, "w", encoding="utf-8") as fh:
            fh.write('{"event": "settle"\n')
        code, out, err = self.run_guard("pre", semrush_call())
        self.assertEqual(code, 2)
        self.assertIn("line 1 of " + self.ledger, err)

    def test_bad_option_fails_closed(self):
        self.env["CLAUDE_PLUGIN_OPTION_MAX_ROWS"] = "lots"
        code, out, err = self.run_guard("pre", semrush_call())
        self.assertEqual(code, 2)
        self.assertIn("max_rows", err)


class EstimateTest(unittest.TestCase):
    def plan(self, vendor, tool, tool_input):
        return cg.plan_call(vendor, tool, tool_input, 50)

    def test_semrush_historical_costs_more(self):
        tool_input = {"report": "domain_organic", "params": {"display_limit": 10, "display_date": "20260115"}}
        self.assertEqual(self.plan("semrush", "execute_report", tool_input).cost, 500)

    def test_ahrefs_where_and_order_by_fields_are_billed(self):
        tool_input = {"select": "keyword,best_position", "where": json.dumps({"field": "volume", "is": ["gte", 100]}),
                      "order_by": "traffic:desc", "limit": 100}
        plan = self.plan("ahrefs", "site-explorer-organic-keywords", tool_input)
        self.assertEqual(plan.cost, 50 * (1 + 1 + 10 + 10))
        self.assertEqual(plan.tool_input["limit"], 50)

    def test_ahrefs_minimum_is_50_units(self):
        self.assertEqual(self.plan("ahrefs", "site-explorer-metrics", {"select": "org_keywords"}).cost, 50)

    def test_dataforseo_serp_standard_depth_and_tasks(self):
        tool_input = {"method": "POST", "path": "/v3/serp/google/organic/task_post",
                      "data": [{"keyword": "a", "depth": 100}, {"keyword": "b"}]}
        plan = self.plan("dataforseo", "api_request", tool_input)
        self.assertAlmostEqual(plan.cost, 0.0006 * 5 + 0.0006)
        self.assertEqual(plan.tool_input["data"][0]["depth"], 50)
        self.assertEqual(plan.tool_input["data"][1], {"keyword": "b"})

    def test_dataforseo_live_bills_only_the_first_task(self):
        tool_input = {"method": "POST", "path": "/v3/serp/google/organic/live/advanced",
                      "data": [{"keyword": "a"}, {"keyword": "b"}]}
        self.assertAlmostEqual(self.plan("dataforseo", "api_request", tool_input).cost, 0.002)

    def test_dataforseo_on_page_crawl_gets_a_page_cap(self):
        tool_input = {"method": "POST", "path": "v3/on_page/task_post",
                      "data": {"target": "example.test", "enable_javascript": True}}
        plan = self.plan("dataforseo", "api_request", tool_input)
        self.assertEqual(plan.tool_input["data"], {"target": "example.test", "enable_javascript": True,
                                                   "max_crawl_pages": 50})
        self.assertAlmostEqual(plan.cost, 50 * (0.00015 + 0.00135))

    def test_unknown_endpoint_has_unknown_price(self):
        plan = self.plan("dataforseo", "api_request", {"method": "POST", "path": "/v3/merchant/google/products/task_post"})
        self.assertIsNone(plan.cost)
        self.assertFalse(plan.free)


class PostTest(GuardCase):
    def test_post_records_ledger_and_cache(self):
        call = semrush_call()
        call["tool_input"]["params"]["display_limit"] = 50
        call["tool_response"] = "Keyword;Search Volume\nenglish tutor near me;1300"
        code, out, err = self.run_guard("post", call)
        self.assertEqual(code, 0, err)
        status = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertNotIn("\n", status)
        self.assertIn("this month: 2,000 units of 50,000 units", status)
        [entry] = self.ledger_entries()
        self.assertEqual((entry["event"], entry["bucket"], entry["cost"], entry["estimated"]), ("settle", "semrush", 2000, True))
        self.assertEqual((entry["month"], entry["session_id"], entry["agent_id"], entry["tool_use_id"]),
                         (cg.utc_now().strftime("%Y-%m"), "run-1", "agent-a", "toolu_sem1"))
        self.assertTrue(re.search(r"cached at (\S+\.json)", status))

    def test_settle_replaces_reservation(self):
        self.pre(semrush_call())
        call = semrush_call()
        call["tool_input"]["params"]["display_limit"] = 50
        call["tool_response"] = "x;1"
        self.run_guard("post", call)
        entries = self.ledger_entries()
        spent = cg.totals(entries, "semrush", cg.utc_now().strftime("%Y-%m"), "run-1", cg.utc_now())
        self.assertEqual([e["event"] for e in entries], ["reserve", "settle"])
        self.assertEqual((spent.month, spent.in_flight), (2000, 0))

    def test_dataforseo_actual_cost_is_recorded(self):
        response = [{"type": "text", "text": json.dumps({"status_code": 20000, "cost": 0.0123,
                                                          "tasks": [{"status_code": 20000, "result": []}]})}]
        call = {"tool_name": "mcp__dataforseo__api_request", "tool_use_id": "t1", "session_id": "s",
                "tool_input": {"method": "POST", "path": "/v3/serp/google/organic/live/advanced",
                               "data": [{"keyword": "a"}]}, "tool_response": response}
        self.run_guard("post", call)
        [entry] = self.ledger_entries()
        self.assertEqual((entry["cost"], entry["estimated"]), (0.0123, False))

    def test_semrush_error_costs_nothing_and_is_not_cached(self):
        call = semrush_call(tool_response="ERROR 132 :: API UNITS BALANCE IS ZERO")
        call["tool_input"]["params"]["display_limit"] = 50
        code, out, err = self.run_guard("post", call)
        self.assertEqual(self.ledger_entries()[0]["cost"], 0)
        self.assertNotIn("cached at", out["hookSpecificOutput"]["additionalContext"])
        self.assertFalse(os.path.exists(os.path.join(self.state, "cache")))

    def test_failure_keeps_estimate_and_skips_cache(self):
        call = semrush_call(error="MCP error -32000: upstream timeout")
        call["tool_input"]["params"]["display_limit"] = 50
        code, out, err = self.run_guard("post-failure", call)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUseFailure")
        [entry] = self.ledger_entries()
        self.assertEqual((entry["status"], entry["cost"]), ("failed", 2000))
        self.assertFalse(os.path.exists(os.path.join(self.state, "cache")))

    def test_concurrent_posts_do_not_corrupt_the_ledger(self):
        procs = []
        for n in range(20):
            call = semrush_call(tool_use_id=f"toolu_{n}", tool_response=f"row;{n}")
            call["tool_input"]["params"]["phrase"] = f"phrase {n}"
            call["tool_input"]["params"]["display_limit"] = 10
            procs.append(subprocess.Popen([sys.executable, GUARD, "post"], stdin=subprocess.PIPE,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=self.env))
            procs[-1].stdin.write(json.dumps(call))
            procs[-1].stdin.close()
        for proc in procs:
            self.assertEqual(proc.wait(timeout=60), 0, proc.stderr.read())
            proc.stderr.close()
        entries = self.ledger_entries()  # every line parses
        self.assertEqual(sorted(e["tool_use_id"] for e in entries), sorted(f"toolu_{n}" for n in range(20)))
        self.assertEqual(sum(e["cost"] for e in entries), 20 * 400)


class BatchTest(GuardCase):
    def batch(self, *calls, session="run-1"):
        return self.run_guard("batch", {"session_id": session, "hook_event_name": "PostToolBatch",
                                        "tool_calls": list(calls)})

    def test_non_vendor_batch_is_silent(self):
        self.assertEqual(self.batch({"tool_name": "Read", "tool_use_id": "r1", "tool_response": "x"})[:2], (0, None))

    def test_breaker_blocks_when_this_batch_crossed_the_run_cap(self):
        self.seed_ledger(self.settled(12000, tool_use_id="old"), self.settled(1000, tool_use_id="toolu_new"))
        code, out, err = self.batch({"tool_name": SEMRUSH_TOOL, "tool_use_id": "toolu_new", "tool_response": "x"})
        self.assertEqual(code, 0, err)
        self.assertEqual(out["decision"], "block")
        self.assertIn("this run", out["reason"])

    def test_breaker_blocks_when_month_crossed(self):
        self.seed_ledger(self.settled(50500, session="elsewhere", tool_use_id="toolu_new"))
        code, out, err = self.batch({"tool_name": SEMRUSH_TOOL, "tool_use_id": "toolu_new", "tool_response": "x"},
                                    session="elsewhere")
        self.assertIn("this month", out["reason"])

    def test_breaker_ignores_batches_that_spent_nothing(self):
        self.seed_ledger(self.settled(60000, tool_use_id="old"))
        code, out, err = self.batch({"tool_name": SEMRUSH_TOOL, "tool_use_id": "denied-call", "tool_response": "x"})
        self.assertEqual((code, out), (0, None), err)


class SessionStartTest(unittest.TestCase):
    def run_hook(self, key):
        hook = HOOKS["SessionStart"][0]["hooks"][0]
        with tempfile.TemporaryDirectory() as tmp:
            env_file = os.path.join(tmp, "env.sh")
            env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_PLUGIN_")}
            env["CLAUDE_ENV_FILE"] = env_file
            if key:
                env["CLAUDE_PLUGIN_OPTION_PSI_API_KEY"] = key
            subprocess.run([sys.executable] + hook["args"], env=env, check=True, timeout=30)
            if not os.path.exists(env_file):
                return None
            with open(env_file, encoding="utf-8") as fh:
                return fh.read()

    def test_psi_key_is_exported_for_bash(self):
        self.assertEqual(self.run_hook("AIzaTest-key_123"), "export PSI_API_KEY=AIzaTest-key_123\n")

    def test_no_key_writes_nothing(self):
        self.assertIsNone(self.run_hook(""))


if __name__ == "__main__":
    unittest.main()
