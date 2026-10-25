"""Rank tracking: rank_snapshot.py (DataForSEO Standard queue, snapshots, share of voice, the free Search Console
path) and rank_compare.py (alerts and change impact against control pages).

Run: python3 -m unittest discover -s tests
No network and no keys. The DataForSEO fixtures in tests/fixtures/rank/ are shaped after DataForSEO's documented
task_post, tasks_ready and task_get/advanced responses; no live call was made to record them.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "rank")
sys.path.insert(0, SCRIPTS)

import credit_guard as cg  # noqa: E402
import rank_compare as rc  # noqa: E402
import rank_snapshot as rs  # noqa: E402

SET = os.path.join(FIXTURES, "keyword-set.json")
KW1, KW2, KW3 = "ინგლისურის რეპეტიტორი თბილისში", "ielts მომზადება", "ინგლისურის კურსები ონლაინ"


def fixture(name: str):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


def fixture_serps() -> list[dict]:
    return [serp for n in (1, 2, 3) for serp in rs.parse_task_get(fixture(f"task_get-{n}.json"))]


def run_main(module, *args) -> tuple[int, dict | None, str]:
    """A script's main() in this process with sys.argv set; returns (exit code, JSON stdout, SystemExit message)."""
    out = io.StringIO()
    with mock.patch.object(sys, "argv", [module.__name__ + ".py", *args]), contextlib.redirect_stdout(out):
        try:
            code = module.main()
            message = ""
        except SystemExit as stop:
            code, message = (stop.code if isinstance(stop.code, int) else 1), ("" if isinstance(stop.code, int)
                                                                                 else str(stop.code))
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else None), message


class FakeDataForSEO:
    """Answers request_json like api.dataforseo.com would, from the fixtures, and records every request."""

    def __init__(self, ready_after: int = 1):
        self.calls: list[tuple[str, str, dict, object]] = []
        self.ready_after = ready_after  # tasks_ready shows the tasks from this poll on
        self.polls = 0

    def __call__(self, method, url, headers, body=None, timeout=120):
        self.calls.append((method, url, headers, body))
        path = url.split("/v3/", 1)[1]
        if path == "serp/google/organic/task_post":
            return fixture("task_post.json")
        if path == "serp/google/organic/tasks_ready":
            self.polls += 1
            ready = fixture("tasks_ready.json")
            if self.polls < self.ready_after:
                ready["tasks"][0]["result"] = ready["tasks"][0]["result"][3:]  # only another run's task
            return ready
        if path.startswith("serp/google/organic/task_get/advanced/"):
            number = int(path.rsplit("-", 1)[1])
            return fixture(f"task_get-{number}.json")
        raise AssertionError(f"unexpected request {method} {url}")

    def paths(self, method=None):
        return [url.split("/v3/", 1)[1] for m, url, _, _ in self.calls if method in (None, m)]


class NoNetwork:
    def __call__(self, *args, **kwargs):
        raise AssertionError("no request may be made")


class KeywordSetTest(unittest.TestCase):
    def write_set(self, **changes) -> str:
        data = fixture("keyword-set.json")
        data.update(changes)
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(data, handle, ensure_ascii=False)
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_fixture_set_loads_with_fixed_conditions(self):
        kset = rs.load_keyword_set(SET)
        self.assertEqual((kset["location_code"], kset["language_code"], kset["device"], kset["depth"]),
                         (2268, "ka", "mobile", 20))
        self.assertEqual([k["keyword"] for k in kset["keywords"]], [KW1, KW2, KW3])
        self.assertEqual(kset["competitors"], ["rival.example", "market.example"])

    def test_the_us_state_of_georgia_is_refused(self):
        with self.assertRaises(SystemExit) as stop:
            rs.load_keyword_set(self.write_set(location_code=21143))
        self.assertIn("2268", str(stop.exception))

    def test_bad_device_and_missing_fields_name_the_file(self):
        for changes in ({"device": "tablet"}, {"keywords": []}, {"version": ""}):
            with self.subTest(changes=changes), self.assertRaises(SystemExit) as stop:
                rs.load_keyword_set(self.write_set(**changes))
            self.assertIn(".json", str(stop.exception))

    def test_duplicate_keywords_are_refused(self):
        with self.assertRaises(SystemExit):
            rs.load_keyword_set(self.write_set(keywords=["a b", "A  b"]))

    def test_language_must_be_in_dataforseos_google_list(self):
        for code in ("ge", "kat", "KA"):  # ge is the country code; Georgian is ka
            with self.subTest(code=code), self.assertRaises(SystemExit) as stop:
                rs.load_keyword_set(self.write_set(language_code=code))
            self.assertIn("Georgian is ka", str(stop.exception))
        for code in ("ka", "ru", "en", "zh-TW", "pt-BR", "sr-Latn", "es-419"):
            with self.subTest(code=code):
                self.assertEqual(rs.load_keyword_set(self.write_set(language_code=code))["language_code"], code)


class RequestTest(unittest.TestCase):
    def setUp(self):
        self.kset = rs.load_keyword_set(SET)

    def test_tasks_carry_the_sets_conditions(self):
        tasks = rs.build_tasks(self.kset, "seo-suite|ge-ka-mobile-v1")
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0], {"keyword": KW1, "location_code": 2268, "language_code": "ka", "device": "mobile",
                                    "depth": 20, "priority": 1, "tag": "seo-suite|ge-ka-mobile-v1",
                                    "load_async_ai_overview": True})

    def test_no_ai_overview_flag_when_the_set_does_not_ask(self):
        self.kset["ai_overview"] = False
        self.assertNotIn("load_async_ai_overview", rs.build_tasks(self.kset, "t")[0])

    def test_posts_hold_at_most_100_tasks(self):
        tasks = [{"keyword": f"k{n}"} for n in range(250)]
        self.assertEqual([len(body) for body in rs.post_bodies(tasks)], [100, 100, 50])

    def test_estimate_is_the_guards_price(self):
        tasks = rs.build_tasks(self.kset, "t")
        # depth 20 = 2 SERPs at $0.0006, plus one base price for the AI Overview: $0.0018 a task
        self.assertAlmostEqual(rs.estimate_usd(tasks, 50), 0.0054)
        plan = cg.plan_call("dataforseo", "api_request", {"path": "/v3/serp/google/organic/task_post", "data": tasks}, 50)
        self.assertAlmostEqual(rs.estimate_usd(tasks, 50), plan.cost)

    def test_depth_above_max_rows_fails_loudly(self):
        self.kset["depth"] = 100
        with self.assertRaises(SystemExit) as stop:
            rs.estimate_usd(rs.build_tasks(self.kset, "t"), 50)
        self.assertIn("max_rows", str(stop.exception))

    def test_credentials_come_from_the_environment(self):
        headers = rs.dfs_headers({"DATAFORSEO_LOGIN": "login@test.invalid", "DATAFORSEO_PASSWORD": "pw"})
        self.assertEqual(headers["Authorization"], "Basic bG9naW5AdGVzdC5pbnZhbGlkOnB3")
        with self.assertRaises(SystemExit) as stop:
            rs.dfs_headers({})
        self.assertIn("DATAFORSEO_LOGIN", str(stop.exception))


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.kset = rs.load_keyword_set(SET)
        self.rows = [rs.snapshot_row(serp, self.kset) for serp in fixture_serps()]

    def test_task_get_is_parsed_per_task(self):
        serps = fixture_serps()
        self.assertEqual([s["keyword"] for s in serps], [KW1, KW2, KW3])
        self.assertTrue(all(s["status_code"] == 20000 for s in serps))

    def test_our_and_competitor_positions(self):
        self.assertEqual([r["position"] for r in self.rows], [2, 8, None])
        self.assertEqual(self.rows[0]["url"], "https://www.tutors.example/ka/tbilisi/")
        self.assertEqual([r["competitors"]["rival.example"] for r in self.rows], [1, 3, 1])
        self.assertEqual([r["competitors"]["market.example"] for r in self.rows], [3, 2, 3])

    def test_a_competitors_subdomain_counts_for_it_but_its_best_position_wins(self):
        self.assertIn("blog.rival.example", [r["domain"] for r in self.rows[0]["results"]])
        self.assertEqual(rs.position_of(self.rows[0], "rival.example"), 1)

    def test_ai_overview_references(self):
        self.assertEqual([r["ai_overview"] for r in self.rows], [True, False, True])
        self.assertEqual(self.rows[0]["ai_overview_domains"], ["rival.example", "tutors.example", "wiki.example"])
        self.assertEqual([r["ai_overview_cited"] for r in self.rows], [True, False, False])

    def test_features_and_people_also_ask(self):
        self.assertEqual(self.rows[0]["features"], ["ai_overview", "organic", "people_also_ask"])
        self.assertEqual(self.rows[0]["paa"], ["რა ღირს ინგლისურის რეპეტიტორი?", "როგორ ავირჩიო რეპეტიტორი?"])
        self.assertEqual(self.rows[1]["paa"], [])

    def test_a_failed_task_is_kept_as_an_error_row(self):
        response = fixture("task_get-2.json")
        response["tasks"][0].update(status_code=40102, status_message="No Search Results.", result=None)
        [serp] = rs.parse_task_get(response)
        row = rs.snapshot_row(serp, self.kset)
        self.assertEqual((row["error"], row["position"], row["results"]), ("No Search Results.", None, []))

    def test_research_store_shapes(self):
        serps, details = rs.store_files(self.rows)
        self.assertEqual(serps[KW1][:2], ["https://www.rival.example/tbilisi/", "https://www.tutors.example/ka/tbilisi/"])
        self.assertEqual(len(serps[KW2]), 8)
        self.assertEqual(details[KW1]["features"], ["ai_overview", "organic", "people_also_ask"])
        self.assertEqual(details[KW1]["paa"][0], "რა ღირს ინგლისურის რეპეტიტორი?")
        self.assertEqual(details[KW1]["results"][1], {"url": "https://www.tutors.example/ka/tbilisi/",
                                                      "title": "Tutors Example: English tutors in Tbilisi"})

    def test_research_store_ingests_the_files_unchanged(self):
        serps, details = rs.store_files(self.rows)
        with tempfile.TemporaryDirectory() as tmp:
            for name, data in (("serps.json", serps), ("details.json", details)):
                with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False)
            store = os.path.join(tmp, "seo-research")
            store_script = os.path.join(SCRIPTS, "research_store.py")
            for args in (["init", "--site", "https://www.tutors.example/", "--locales", "ka"],
                         ["ingest", "serps", os.path.join(tmp, "serps.json"), "--locale", "ka",
                          "--details", os.path.join(tmp, "details.json"), "--as-of", "2026-10-25"]):
                proc = subprocess.run([sys.executable, store_script, *args, "--dir", store], capture_output=True,
                                      text=True, timeout=60)
                self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(os.path.join(store, "competitors.json"), encoding="utf-8") as fh:
                self.assertIn("rival.example", fh.read())


class MetricsTest(unittest.TestCase):
    CURVE = {1: 0.3, 2: 0.15, 3: 0.1}

    def rows(self):
        def row(keyword, volume, *domains):
            return {"keyword": keyword, "volume": volume,
                    "results": [{"position": n, "domain": d, "url": f"https://{d}/{n}"} for n, d in enumerate(domains, 1)]}
        return [row("a", 100, "a.example", "b.example", "us.example"), row("b", 300, "us.example", "a.example")]

    def test_share_of_voice_is_volume_weighted_clicks_over_all_clicks(self):
        rows = self.rows()
        # (100 × 0.1 + 300 × 0.3) / (400 × (0.3 + 0.15 + 0.1)) = 100 / 220
        self.assertAlmostEqual(rs.share_of_voice(rows, "us.example", self.CURVE, 3), 100 / 220)
        self.assertAlmostEqual(rs.share_of_voice(rows, "a.example", self.CURVE, 3), 75 / 220)
        self.assertAlmostEqual(rs.share_of_voice(rows, "b.example", self.CURVE, 3), 15 / 220)

    def test_missing_volumes_weigh_keywords_equally(self):
        rows = self.rows()
        for row in rows:
            row["volume"] = None
        # (0.1 + 0.3) / (2 × 0.55)
        self.assertAlmostEqual(rs.share_of_voice(rows, "us.example", self.CURVE, 3), 0.4 / 1.1)

    def test_visibility_is_ctr_over_number_one_everywhere(self):
        rows = self.rows()
        self.assertAlmostEqual(rs.visibility(rows, "us.example", self.CURVE), (0.1 + 0.3) / (2 * 0.3) * 100)
        self.assertEqual(rs.visibility(rows, "nobody.example", self.CURVE), 0.0)

    def test_fixture_snapshot_metrics(self):
        kset = rs.load_keyword_set(SET)
        snapshot = rs.build_snapshot(kset, fixture_serps(), {"date": "2026-10-25"})
        metrics = snapshot["metrics"]
        curve = rs.DEFAULT_CTR
        denominator = 740 * sum(rs.ctr_at(curve, p) for p in range(1, 21))
        self.assertAlmostEqual(metrics["share_of_voice"]["tutors.example"],
                               round((390 * curve[2] + 210 * curve[8]) / denominator, 4))
        self.assertAlmostEqual(metrics["share_of_voice"]["rival.example"],
                               round((390 * curve[1] + 210 * curve[3] + 140 * curve[1]) / denominator, 4))
        self.assertEqual(metrics["top_domains"][0]["domain"], "rival.example")
        self.assertEqual((metrics["ranked"], metrics["top3"], metrics["top10"]), (2, 1, 2))
        self.assertEqual(metrics["ai_overview"]["serps_with_ai_overview"], 2)
        self.assertEqual(metrics["ai_overview"]["citation_share"]["tutors.example"], 0.5)
        self.assertEqual(metrics["ai_overview"]["citation_share"]["rival.example"], 1.0)
        self.assertIn("search volume", metrics["weighting"])

    def test_a_fitted_curve_never_values_a_lower_position_more(self):
        curve = {**rs.DEFAULT_CTR, 1: 0.04}  # an AI Overview above position 1 drags its own CTR down
        snapshot = rs.build_snapshot(rs.load_keyword_set(SET), fixture_serps(), {"date": "2026-10-25"}, curve, "fitted")
        stored = [snapshot["meta"]["ctr_curve"][str(p)] for p in range(1, 21)]
        self.assertEqual(len(snapshot["meta"]["ctr_curve"]), 20)  # every position up to depth, none hidden
        self.assertEqual(stored, sorted(stored, reverse=True))
        self.assertTrue(all(value <= 100 for value in snapshot["metrics"]["visibility_pct"].values()),
                        snapshot["metrics"]["visibility_pct"])
        shares = {entry["domain"]: entry["share"] for entry in snapshot["metrics"]["top_domains"]}
        self.assertGreaterEqual(shares["rival.example"], shares["market.example"])  # rival ranks better

    def test_own_gsc_export_fits_the_curve(self):
        gsc = os.path.join(FIXTURES, "gsc-queries.csv")
        curve, source = rs.ctr_curve_from(gsc)
        self.assertIn("gsc-queries.csv", source)
        self.assertEqual(set(rs.DEFAULT_CTR) - set(curve), set())
        self.assertEqual(rs.ctr_curve_from(None)[1], "default curve (gsc_analyze.DEFAULT_CTR)")


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "rank")
        self.env = {"CLAUDE_PLUGIN_DATA": self.tmp.name, "CLAUDE_PLUGIN_OPTION_DATAFORSEO_MONTHLY_USD": "25",
                    "SEO_SUITE_SESSION_ID": "session-1", "DATAFORSEO_LOGIN": "login@test.invalid",
                    "DATAFORSEO_PASSWORD": "pw"}
        patches = [mock.patch.dict(os.environ, self.env, clear=False), mock.patch.object(rs.time, "sleep")]
        for name in ("SEO_SUITE_DATA", "CLAUDE_PLUGIN_OPTION_PER_RUN_CAP_PCT", "CLAUDE_PLUGIN_OPTION_MAX_ROWS"):
            if name in os.environ:
                patches.append(mock.patch.dict(os.environ, {name: ""}))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def ledger(self) -> list[dict]:
        path = os.path.join(self.tmp.name, "credit-guard", "ledger.jsonl")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_budget_zero_stops_before_any_request(self):
        os.environ["CLAUDE_PLUGIN_OPTION_DATAFORSEO_MONTHLY_USD"] = "0"
        with mock.patch.object(rs, "request_json", NoNetwork()):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("dataforseo_monthly_usd is 0", message)
        self.assertIn("rank_snapshot.py gsc", message)  # the free path
        self.assertEqual(self.ledger(), [])

    def test_over_the_per_run_cap_stops_before_posting(self):
        os.environ["CLAUDE_PLUGIN_OPTION_DATAFORSEO_MONTHLY_USD"] = "0.02"  # cap 25% = $0.005 < $0.0054
        with mock.patch.object(rs, "request_json", NoNetwork()):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("per-run", message)

    def test_full_run_posts_polls_fetches_and_records_spend(self):
        fake = FakeDataForSEO(ready_after=2)
        with mock.patch.object(rs, "request_json", fake):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out, "--poll-seconds", "1")
        self.assertEqual(code, 0, message)
        posts = [(url, headers, body) for method, url, headers, body in fake.calls if method == "POST"]
        self.assertEqual(len(posts), 1)
        url, headers, body = posts[0]
        self.assertTrue(url.startswith("https://api.dataforseo.com/v3/serp/google/organic/task_post"))
        self.assertTrue(headers["Authorization"].startswith("Basic "))
        self.assertEqual([task["keyword"] for task in body], [KW1, KW2, KW3])
        self.assertEqual(fake.polls, 2)
        self.assertEqual(sorted(p for p in fake.paths("GET") if "task_get" in p),
                         [f"serp/google/organic/task_get/advanced/10250900-1111-0066-0000-00000000000{n}"
                          for n in (1, 2, 3)])
        reserve, settle = self.ledger()
        self.assertEqual((reserve["event"], reserve["bucket"], reserve["session_id"]), ("reserve", "dataforseo",
                                                                                         "session-1"))
        self.assertEqual((settle["event"], settle["cost"], settle["estimated"]), ("settle", 0.0054, False))
        self.assertEqual(settle["tool_use_id"], reserve["tool_use_id"])
        for kind in ("snapshot", "serps", "details", "tasks"):
            self.assertTrue(os.path.exists(out["files"][kind]), kind)
        with open(out["files"]["snapshot"], encoding="utf-8") as fh:
            snapshot = json.load(fh)
        self.assertEqual(snapshot["meta"]["source"], "DataForSEO Google Organic SERP API, Standard queue [vendor data]")
        self.assertEqual(snapshot["meta"]["cost_usd"], 0.0054)
        self.assertEqual([r["position"] for r in snapshot["rows"]], [2, 8, None])

    def test_a_task_refused_at_posting_becomes_an_error_row(self):
        fake = FakeDataForSEO()
        refused = fixture("task_post.json")
        refused["tasks"][2].update(status_code=40501, status_message="Invalid Field: 'keyword'.", id=None)

        def answer(method, url, headers, body=None, timeout=120):
            return refused if url.endswith("task_post") else fake(method, url, headers, body, timeout)

        with mock.patch.object(rs, "request_json", answer):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out)
        self.assertEqual(code, 0, message)
        with open(out["files"]["snapshot"], encoding="utf-8") as fh:
            rows = json.load(fh)["rows"]
        self.assertEqual(rows[2]["error"], "Invalid Field: 'keyword'.")
        self.assertEqual(out["metrics"]["errors"], 1)
        self.assertEqual(len(fake.paths("GET")) - fake.polls, 2)  # only the two created tasks are fetched

    def test_same_set_and_day_is_not_bought_twice(self):
        with mock.patch.object(rs, "request_json", FakeDataForSEO()):
            self.assertEqual(run_main(rs, "run", SET, "--out-dir", self.out)[0], 0)
        with mock.patch.object(rs, "request_json", NoNetwork()):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("already", message)

    def test_a_set_posted_today_is_not_posted_again_before_its_snapshot(self):
        with mock.patch.object(rs, "request_json", FakeDataForSEO(ready_after=99)):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out, "--wait-minutes", "0")
        self.assertNotEqual(code, 0)
        tasks_file = message.split("--resume ")[1].split()[0]
        with open(tasks_file, encoding="utf-8") as fh:
            first_ids = [task["id"] for task in json.load(fh)["tasks"]]
        again = FakeDataForSEO(ready_after=99)
        with mock.patch.object(rs, "request_json", again):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out, "--wait-minutes", "0")
        self.assertNotEqual(code, 0)
        self.assertEqual(again.paths("POST"), [])  # nothing bought twice
        self.assertIn("--resume " + tasks_file, message)
        self.assertEqual(len(self.ledger()), 2)  # the first run's reserve and settle only
        with open(tasks_file, encoding="utf-8") as fh:
            self.assertEqual([task["id"] for task in json.load(fh)["tasks"]], first_ids)  # the paid ids are kept

    def test_slow_queue_ends_with_a_free_resume(self):
        fake = FakeDataForSEO(ready_after=99)
        with mock.patch.object(rs, "request_json", fake):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out, "--wait-minutes", "0")
        self.assertNotEqual(code, 0)
        self.assertIn("--resume", message)
        tasks_file = message.split("--resume ")[1].split()[0]
        self.assertTrue(os.path.exists(tasks_file))
        resumed = FakeDataForSEO()
        with mock.patch.object(rs, "request_json", resumed):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out, "--resume", tasks_file)
        self.assertEqual(code, 0, message)
        self.assertEqual(resumed.paths("POST"), [])  # resuming posts nothing, so it costs nothing
        self.assertEqual(len(self.ledger()), 2)  # only the first run's reserve and settle

    def test_a_network_error_while_waiting_ends_with_a_free_resume(self):
        fake = FakeDataForSEO()

        def answer(method, url, headers, body=None, timeout=120):
            if url.endswith("tasks_ready"):
                raise rs.ApiError(f"{url}: HTTP 502: bad gateway")
            return fake(method, url, headers, body, timeout)

        with mock.patch.object(rs, "request_json", answer):
            code, out, message = run_main(rs, "run", SET, "--out-dir", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("HTTP 502", message)
        self.assertIn("--resume", message)
        self.assertEqual([e["event"] for e in self.ledger()], ["reserve", "settle"])  # the posting was recorded

    def test_connector_path_plan_then_parse(self):
        with mock.patch.object(rs, "request_json", NoNetwork()):
            code, plan, message = run_main(rs, "plan", SET)
        self.assertEqual(code, 0, message)
        self.assertEqual(len(plan["task_post_bodies"]), 1)
        self.assertAlmostEqual(plan["estimate_usd"], 0.0054)
        self.assertIn("noAiMode", " ".join(plan["connector_steps"]))
        responses = [os.path.join(FIXTURES, f"task_get-{n}.json") for n in (1, 2, 3)]
        code, out, message = run_main(rs, "parse", SET, *responses, "--out-dir", self.out)
        self.assertEqual(code, 0, message)
        self.assertEqual(out["metrics"]["ranked"], 2)
        self.assertTrue(os.path.exists(out["files"]["serps"]))

    def test_parse_refuses_a_response_for_another_set(self):
        response = fixture("task_get-1.json")
        response["tasks"][0]["data"]["device"] = "desktop"
        path = os.path.join(self.tmp.name, "other.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(response, fh, ensure_ascii=False)
        code, out, message = run_main(rs, "parse", SET, path, "--out-dir", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("desktop", message)


class FreeGscTest(unittest.TestCase):
    def test_own_positions_from_search_console_and_what_paid_adds(self):
        code, out, message = run_main(rs, "gsc", SET, os.path.join(FIXTURES, "gsc-queries.csv"))
        self.assertEqual(code, 0, message)
        by_keyword = {row["keyword"]: row for row in out["keywords"]}
        self.assertEqual(by_keyword[KW1]["gsc_position"], 3.2)
        self.assertEqual(by_keyword[KW2]["clicks"], 3)
        self.assertIsNone(by_keyword[KW3]["gsc_position"])  # no impressions: only a snapshot can say where it ranks
        self.assertEqual(out["summary"]["with_impressions"], 2)
        self.assertIn("not a fixed-condition", out["label"])
        self.assertTrue(any("competitor" in line for line in out["paid_adds"]["what"]))
        self.assertAlmostEqual(out["paid_adds"]["estimate_usd_per_run"], 0.0054)


def snapshot(rows: dict, version="v1", date="2026-10-01", depth=20) -> dict:
    """A minimal rank_snapshot.py snapshot: rows given as {keyword: (position, url, ai_cited)}."""
    return {"meta": {"set_version": version, "site": "tutors.example", "location_code": 2268, "language_code": "ka",
                     "device": "mobile", "depth": depth, "date": date},
            "rows": [{"keyword": keyword, "position": position, "url": url, "ai_overview": cited is not None,
                      "ai_overview_cited": bool(cited)} for keyword, (position, url, cited) in rows.items()]}


class CompareAlertTest(unittest.TestCase):
    def runs(self):
        u = "https://www.tutors.example/ka/"
        snaps = [snapshot({"a": (12, u + "a/", False), "b": (5, u + "b/", None), "c": (2, u + "c/", None),
                           "d": (None, None, None)}, date="2026-10-01"),
                 snapshot({"a": (8, u + "a/", False), "b": (9, u + "b/", None), "c": (2, u + "c/", None),
                           "d": (None, None, None)}, date="2026-10-15"),
                 snapshot({"a": (7, u + "a/", True), "b": (4, u + "b/", None), "c": (4, u + "c/", None),
                           "d": (9, u + "d/", None)}, date="2026-10-29")]
        return rc.snapshot_runs(rc.check_snapshots(snaps, ["s1", "s2", "s3"]))

    def alerts(self):
        found = rc.alerts(self.runs(), rc.not_ranked_position(20))
        return {(a["key"], a["alert"]) for group in ("alerts", "pending") for a in found[group]}, found

    def test_a_move_of_three_held_for_two_runs_alerts(self):
        keys, found = self.alerts()
        self.assertIn(("a", "moved_up"), keys)
        self.assertNotIn(("b", "moved_down"), keys)  # down 4, then back: not held

    def test_a_single_move_waits_for_confirmation(self):
        keys, found = self.alerts()
        self.assertIn(("b", "pending_move"), keys)
        self.assertIn(("d", "pending_move"), keys)

    def test_top_3_and_top_10_entry_and_exit(self):
        keys, found = self.alerts()
        self.assertIn(("c", "left_top_3"), keys)
        self.assertIn(("d", "entered_top_10"), keys)
        self.assertNotIn(("b", "entered_top_3"), keys)  # 9 -> 4 stays outside the top 3

    def test_ai_citation_change(self):
        keys, found = self.alerts()
        self.assertIn(("a", "ai_citation_gained"), keys)

    def test_thresholds_are_labelled_as_judgement(self):
        keys, found = self.alerts()
        self.assertIn("judgement", found["thresholds"]["basis"])
        self.assertEqual((found["thresholds"]["move_positions"], found["thresholds"]["held_runs"]), (3, 2))

    def test_two_runs_give_pending_moves_only(self):
        found = rc.alerts(self.runs()[:2], rc.not_ranked_position(20))
        self.assertEqual([a for a in found["alerts"] if a["alert"].startswith("moved")], [])
        self.assertIn("b", {a["key"] for a in found["pending"]})

    def test_snapshots_of_different_sets_are_refused(self):
        with self.assertRaises(SystemExit) as stop:
            rc.check_snapshots([snapshot({"a": (1, None, None)}), snapshot({"a": (1, None, None)}, version="v2")],
                               ["s1", "s2"])
        self.assertIn("s2", str(stop.exception))

    def test_snapshots_with_another_ai_overview_or_competitor_list_are_refused(self):
        for key, value in (("ai_overview", False), ("competitors", ["rival.example"])):
            first, second = snapshot({"a": (1, None, None)}), snapshot({"a": (1, None, None)})
            first["meta"].update(ai_overview=True, competitors=["rival.example", "market.example"])
            second["meta"].update(first["meta"], **{key: value})
            with self.subTest(key=key), self.assertRaises(SystemExit) as stop:
                rc.check_snapshots([first, second], ["s1", "s2"])
            self.assertIn(key, str(stop.exception))


class CompareImpactTest(unittest.TestCase):
    def test_changed_keywords_against_controls(self):
        u = "https://www.tutors.example/ka/"
        before = {f"t{n}": (10, u + "changed/", None) for n in range(3)}
        before.update({f"c{n}": (6, u + f"control-{n}/", None) for n in range(4)})
        after = {f"t{n}": (5, u + "changed/", None) for n in range(3)}
        after.update({f"c{n}": (6 if n else 8, u + f"control-{n}/", None) for n in range(4)})
        runs = rc.snapshot_runs(rc.check_snapshots([snapshot(before), snapshot(after, date="2026-10-29")], ["b", "a"]))
        result = rc.impact(runs[0], runs[-1], {rc.page_key(u + "changed/")}, None, rc.not_ranked_position(20))
        self.assertEqual((result["changed"]["keys"], result["control"]["keys"]), (3, 4))
        self.assertEqual(result["changed"]["positions_gained"], 5.0)
        self.assertEqual(result["control"]["positions_gained"], -0.5)
        self.assertEqual(result["difference"]["positions_gained"], 5.5)
        self.assertEqual(result["verdict"], "ahead of controls")

    def test_too_few_keywords_is_inconclusive(self):
        u = "https://www.tutors.example/ka/"
        runs = rc.snapshot_runs(rc.check_snapshots([snapshot({"a": (9, u + "x/", None), "b": (5, u + "y/", None)}),
                                                    snapshot({"a": (3, u + "x/", None), "b": (5, u + "y/", None)})],
                                                   ["b", "a"]))
        result = rc.impact(runs[0], runs[-1], {rc.page_key(u + "x/")}, None, rc.not_ranked_position(20))
        self.assertTrue(result["verdict"].startswith("inconclusive"))

    def test_gsc_pages_before_and_after(self):
        files = [os.path.join(FIXTURES, f"gsc-pages-{name}.csv") for name in ("before", "after", "later")]
        code, out, message = run_main(rc, "gsc", *files, "--changed", os.path.join(FIXTURES, "changed-urls.txt"))
        self.assertEqual(code, 0, message)
        impact = out["change_impact"]
        self.assertEqual((impact["changed"]["clicks_before"], impact["changed"]["clicks_after"]), (60, 110))
        self.assertEqual((impact["control"]["clicks_before"], impact["control"]["clicks_after"]), (70, 70))
        self.assertAlmostEqual(impact["difference"]["clicks_change_pct"], 83.3)
        self.assertEqual(impact["verdict"], "ahead of controls")
        self.assertIn(("https://www.tutors.example/ka/tbilisi/", "entered_top_3"),
                      {(a["key"], a["alert"]) for a in out["alerts"]})
        self.assertIn("judgement", out["thresholds"]["basis"])
        self.assertEqual(out["position_basis"], rs.GSC_LABEL)  # GSC averages, never read as snapshot ranks

    def test_gsc_needs_a_page_column(self):
        queries = os.path.join(FIXTURES, "gsc-queries.csv")
        code, out, message = run_main(rc, "gsc", queries, queries, "--changed",
                                      os.path.join(FIXTURES, "changed-urls.txt"))
        self.assertNotEqual(code, 0)
        self.assertIn("page", message)

    def test_snapshot_mode_from_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for n, rows in enumerate(({"k": (12, None, None)}, {"k": (8, None, None)}, {"k": (8, None, None)})):
                path = os.path.join(tmp, f"s{n}.snapshot.json")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(snapshot(rows, date=f"2026-10-0{n + 1}"), fh)
                paths.append(path)
            code, out, message = run_main(rc, "snapshots", *paths)
        self.assertEqual(code, 0, message)
        self.assertIn(("k", "moved_up"), {(a["key"], a["alert"]) for a in out["alerts"]})
        self.assertNotIn("change_impact", out)  # no --changed list: alerts only
        self.assertNotIn("position_basis", out)  # snapshot ranks need no Search Console label


if __name__ == "__main__":
    unittest.main()
