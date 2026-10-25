"""AI-answer probe: ai_probe.py runs a frozen prompt set through the official OpenAI, Perplexity and Anthropic APIs
and writes rows ai_visibility.py reads.

Run: python3 -m unittest discover -s tests
No network and no keys. The response fixtures in tests/fixtures/rank/ are shaped after each vendor's documented
example (OpenAI Responses web_search, Perplexity Agent API search_results, Anthropic web_search_tool_result); no
live call was made to record them.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "rank")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ai_probe as ap  # noqa: E402
import ai_visibility as av  # noqa: E402

PROMPTS = os.path.join(FIXTURES, "ai-prompts.json")
KEYS = {"SEO_SUITE_OPENAI_API_KEY": "sk-test-openai", "SEO_SUITE_PERPLEXITY_API_KEY": "pplx-test",
        "SEO_SUITE_ANTHROPIC_API_KEY": "sk-ant-test"}


def fixture(name: str):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


def run_main(*args) -> tuple[int, dict | None, str]:
    out = io.StringIO()
    with mock.patch.object(sys, "argv", ["ai_probe.py", *args]), contextlib.redirect_stdout(out):
        try:
            code, message = ap.main(), ""
        except SystemExit as stop:
            code, message = (stop.code, "") if isinstance(stop.code, int) else (1, str(stop.code))
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else None), message


class FakeVendors:
    """Answers request_json like the three APIs would, from the fixtures, and records every request."""
    RESPONSES = {"api.openai.com": "openai-response.json", "api.perplexity.ai": "perplexity-response.json",
                 "api.anthropic.com": "anthropic-response.json"}

    def __init__(self, fail_on: int | None = None):
        self.calls: list[tuple[str, str, dict, dict]] = []
        self.fail_on = fail_on

    def __call__(self, method, url, headers, body=None, timeout=120):
        self.calls.append((method, url, headers, body))
        if self.fail_on is not None and len(self.calls) == self.fail_on:
            raise ap.ApiError(f"{url}: HTTP 500: upstream error")
        return fixture(self.RESPONSES[url.split("/")[2]])

    def hosts(self):
        return [url.split("/")[2] for _, url, _, _ in self.calls]


class NoNetwork:
    def __call__(self, *args, **kwargs):
        raise AssertionError("no request may be made")


class PromptSetTest(unittest.TestCase):
    def write_set(self, change) -> str:
        data = fixture("ai-prompts.json")
        change(data)
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(data, handle, ensure_ascii=False)
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_set_id_pins_version_and_content(self):
        pset = ap.load_prompt_set(PROMPTS)
        self.assertTrue(pset["id"].startswith("2026-10-25.1@"))
        self.assertEqual(ap.load_prompt_set(PROMPTS)["id"], pset["id"])
        edited = self.write_set(lambda d: d["prompts"][0].update(text="What is Tutors Example, really?"))
        self.assertNotEqual(ap.load_prompt_set(edited)["id"], pset["id"])
        model_only = self.write_set(lambda d: d["engines"]["openai"].update(model="gpt-5.4-mini"))
        self.assertEqual(ap.load_prompt_set(model_only)["id"], pset["id"])  # models are recorded per row instead

    def test_classes_and_duplicate_ids_are_checked(self):
        for change in (lambda d: d["prompts"][0].update({"class": "navigational"}),
                       lambda d: d["prompts"][1].update(id="brand-en-1"),
                       lambda d: d["locale"].update(country="Georgia")):
            with self.subTest(), self.assertRaises(SystemExit):
                ap.load_prompt_set(self.write_set(change))

    def test_perplexity_effort_must_be_pinned_to_a_version(self):
        path = self.write_set(lambda d: d["engines"]["perplexity"].update(effort="fast"))
        with self.assertRaises(SystemExit) as stop:
            ap.check_engines(ap.load_prompt_set(path), ["perplexity"])
        self.assertIn("fast@", str(stop.exception))

    def test_a_model_without_a_price_fails_loudly(self):
        path = self.write_set(lambda d: d["engines"]["openai"].update(model="gpt-unknown"))
        with self.assertRaises(SystemExit) as stop:
            ap.check_engines(ap.load_prompt_set(path), ["openai"])
        self.assertIn("gpt-unknown", str(stop.exception))


class EngineRuleTest(unittest.TestCase):
    def test_consumer_apps_and_grounded_gemini_or_bing_are_refused(self):
        pset = ap.load_prompt_set(PROMPTS)
        for engine, why in (("gemini", "Grounded"), ("bing", "Bing"), ("chatgpt", "consumer"),
                            ("copilot", "Copilot"), ("google", "google.com")):
            with self.subTest(engine=engine), self.assertRaises(SystemExit) as stop:
                ap.check_engines(pset, [engine])
            self.assertIn(why, str(stop.exception))

    def test_only_the_official_api_hosts_are_called(self):
        self.assertEqual({urlsplit_host(engine["url"]) for engine in ap.ENGINES.values()},
                         {"api.openai.com", "api.perplexity.ai", "api.anthropic.com"})

    def test_default_engines_are_chatgpt_main_and_perplexity_cross_check(self):
        self.assertEqual(ap.DEFAULT_ENGINES, ("openai", "perplexity"))


def urlsplit_host(url: str) -> str:
    return url.split("/")[2]


class RequestTest(unittest.TestCase):
    def setUp(self):
        self.pset = ap.load_prompt_set(PROMPTS)
        self.prompt = self.pset["prompts"][1]

    def test_openai_responses_with_web_search_and_location(self):
        url, headers, body = ap.build_request("openai", self.prompt, self.pset, "sk-test-openai")
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertEqual(headers["Authorization"], "Bearer sk-test-openai")
        self.assertEqual(body["model"], "gpt-5-mini")
        self.assertEqual(body["input"], self.prompt["text"])
        self.assertEqual(body["tools"], [{"type": "web_search", "user_location": {
            "type": "approximate", "country": "GE", "city": "Tbilisi", "region": "Tbilisi", "timezone": "Asia/Tbilisi"}}])
        self.assertEqual((body["tool_choice"], body["include"]), ("required", ["web_search_call.action.sources"]))
        self.assertNotIn("temperature", body)

    def test_perplexity_agent_api_with_a_pinned_effort(self):
        url, headers, body = ap.build_request("perplexity", self.prompt, self.pset, "pplx-test")
        self.assertEqual(url, "https://api.perplexity.ai/v1/agent")
        self.assertEqual(headers["Authorization"], "Bearer pplx-test")
        self.assertEqual(body["effort"], "fast@2026-10-16.0")
        self.assertEqual(body["tools"], [{"type": "web_search", "user_location": {
            "country": "GE", "city": "Tbilisi", "region": "Tbilisi"}}])

    def test_anthropic_messages_with_basic_web_search(self):
        url, headers, body = ap.build_request("anthropic", self.prompt, self.pset, "sk-ant-test")
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual((headers["x-api-key"], headers["anthropic-version"]), ("sk-ant-test", "2023-06-01"))
        self.assertEqual(body["model"], "claude-haiku-5-5")
        self.assertEqual(body["messages"], [{"role": "user", "content": self.prompt["text"]}])
        self.assertEqual(body["tools"], [{"type": "web_search_20250305", "name": "web_search", "max_uses": 1,
                                          "user_location": {"type": "approximate", "country": "GE", "city": "Tbilisi",
                                                            "region": "Tbilisi", "timezone": "Asia/Tbilisi"}}])
        self.assertNotIn("temperature", body)


class ParseTest(unittest.TestCase):
    def test_openai_citations_sources_and_usage(self):
        answer = ap.parse_answer("openai", fixture("openai-response.json"))
        self.assertTrue(answer.text.startswith("Tutors Example is"))
        self.assertEqual(answer.citations, ["https://www.rival.example/reviews/", "https://forum.example/thread/1"])
        self.assertEqual(answer.sources, ["https://www.tutors.example/ka/", "https://www.rival.example/",
                                          "https://forum.example/thread/1"])
        self.assertEqual((answer.search_calls, answer.model_id, answer.tool_version), (1, "gpt-5-mini-2025-08-07",
                                                                                        "web_search"))
        self.assertEqual((answer.input_tokens, answer.output_tokens, answer.vendor_cost), (9000, 800, None))

    def test_perplexity_markers_map_to_search_results(self):
        answer = ap.parse_answer("perplexity", fixture("perplexity-response.json"))
        self.assertEqual(answer.citations, ["https://tutors.example/ka/ielts/", "https://blog.example/ielts-tbilisi"])
        self.assertEqual(len(answer.sources), 3)
        self.assertEqual((answer.search_calls, answer.tool_version, answer.vendor_cost), (1, "fast@2026-10-16.0",
                                                                                          0.0021))

    def test_perplexity_without_markers_cites_every_result(self):
        response = fixture("perplexity-response.json")
        response["output"][1]["content"][0]["text"] = "No markers here."
        self.assertEqual(len(ap.parse_answer("perplexity", response).citations), 3)

    def test_anthropic_citations_and_search_count(self):
        answer = ap.parse_answer("anthropic", fixture("anthropic-response.json"))
        self.assertEqual(answer.citations, ["https://www.rival.example/ka/"])
        self.assertEqual(answer.sources, ["https://www.rival.example/ka/", "https://courses.example/english/"])
        self.assertEqual((answer.search_calls, answer.model_id, answer.tool_version), (1, "claude-haiku-5-5",
                                                                                        "web_search_20250305"))

    def test_cost_from_usage_or_the_vendors_figure(self):
        pset = ap.load_prompt_set(PROMPTS)
        openai = ap.parse_answer("openai", fixture("openai-response.json"))
        self.assertEqual(ap.answer_cost("openai", pset, openai), (round(9000 * 0.25e-6 + 800 * 2e-6 + 0.01, 6), True))
        perplexity = ap.parse_answer("perplexity", fixture("perplexity-response.json"))
        self.assertEqual(ap.answer_cost("perplexity", pset, perplexity), (0.0021, False))
        anthropic = ap.parse_answer("anthropic", fixture("anthropic-response.json"))
        self.assertEqual(ap.answer_cost("anthropic", pset, anthropic)[0], round(6000 * 0.1e-6 + 700 * 0.5e-6 + 0.01, 6))


class MentionTest(unittest.TestCase):
    def test_aliases_in_every_script_match_whole_words(self):
        names = ["Tutors Example", "ტუტორს ექსამფლი", "Тьюторс Экзампл", "tutors.example"]
        for text in ("I'd pick TUTORS EXAMPLE.", "ტუტორს ექსამფლი-ს კურსები", "Школа «Тьюторс Экзампл»",
                     "see tutors.example/ka", "Tutors-Example is fine"):
            with self.subTest(text=text):
                self.assertTrue(ap.names_mentioned(text, names))
        for text in ("Tutors Examples are everywhere", "Tutor Example", "контенттьюторс экзампл"):
            with self.subTest(text=text):
                self.assertFalse(ap.names_mentioned(text, names))


class RowTest(unittest.TestCase):
    def rows(self):
        pset = ap.load_prompt_set(PROMPTS)
        out = []
        for engine, name in (("openai", "openai-response.json"), ("perplexity", "perplexity-response.json"),
                             ("anthropic", "anthropic-response.json")):
            answer = ap.parse_answer(engine, fixture(name))
            out.append(ap.observation_row(pset["prompts"][2], pset, engine, 1, "2026-10-25", answer,
                                          ap.answer_cost(engine, pset, answer)[0]))
        return out

    def test_mentioned_cited_and_competitors(self):
        openai, perplexity, anthropic = self.rows()
        self.assertEqual((openai["mentioned"], openai["cited"], openai["competitors_mentioned"]), (1, 0, "rival.example"))
        self.assertEqual(openai["cited_domains"], "rival.example;forum.example")
        self.assertEqual(openai["source_domains"], "tutors.example;rival.example;forum.example")
        self.assertEqual((perplexity["mentioned"], perplexity["cited"], perplexity["cited_url"]),
                         (1, 1, "https://tutors.example/ka/ielts/"))
        self.assertEqual((anthropic["mentioned"], anthropic["cited"], anthropic["competitors_mentioned"]),
                         (0, 0, "rival.example"))

    def test_rows_carry_the_documented_columns(self):
        openai = self.rows()[0]
        self.assertEqual(list(openai), ap.CSV_COLUMNS)
        self.assertEqual(ap.CSV_COLUMNS[:8], ["query", "engine", "run", "date", "mentioned", "cited", "cited_url",
                                              "competitors_mentioned"])  # the original ai_visibility.py columns
        self.assertEqual((openai["locale"], openai["lang"], openai["prompt_class"], openai["surface"]),
                         ("GE-Tbilisi", "ru", "comparison", "api"))
        self.assertEqual(len(openai["answer_sha256"]), 64)

    def test_ai_visibility_reads_the_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "obs.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=ap.CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(self.rows())
            report = av.summarize(av.load(path), "tutors.example")
        self.assertEqual(report["observations"], 3)
        self.assertEqual(set(report["by_engine"]), {"openai", "perplexity", "anthropic"})
        self.assertEqual(report["mentioned_not_cited"]["hits"], 1)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "ai-observations.csv")
        env = {"CLAUDE_PLUGIN_DATA": self.tmp.name, "CLAUDE_PLUGIN_OPTION_OTHER_MONTHLY_USD": "12",
               "SEO_SUITE_SESSION_ID": "session-1", "SEO_SUITE_DATA": "", "CLAUDE_PLUGIN_OPTION_PER_RUN_CAP_PCT": "",
               **KEYS}
        for patch in (mock.patch.dict(os.environ, env), mock.patch.object(ap.time, "sleep")):
            patch.start()
            self.addCleanup(patch.stop)

    def ledger(self):
        path = os.path.join(self.tmp.name, "credit-guard", "ledger.jsonl")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def read_rows(self):
        with open(self.out, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_plan_estimates_without_calling_anything(self):
        with mock.patch.object(ap, "request_json", NoNetwork()):
            code, plan, message = run_main("plan", PROMPTS)
        self.assertEqual(code, 0, message)
        self.assertEqual(plan["probes"], 4 * 2 * 2)  # prompts × default engines × repeats
        self.assertEqual(set(plan["per_engine"]), {"openai", "perplexity"})
        self.assertTrue(plan["budget"]["fits"])

    def test_run_writes_rows_answers_and_ledger_spend(self):
        fake = FakeVendors()
        with mock.patch.object(ap, "request_json", fake):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out)
        self.assertEqual(code, 0, message)
        self.assertEqual(len(fake.calls), 16)
        self.assertEqual(fake.hosts()[:4], ["api.openai.com", "api.openai.com", "api.perplexity.ai",
                                            "api.perplexity.ai"])
        rows = self.read_rows()
        self.assertEqual(len(rows), 16)
        self.assertEqual({row["prompt_set"] for row in rows}, {ap.load_prompt_set(PROMPTS)["id"]})
        with open(summary["answers"], encoding="utf-8") as fh:
            answers = [json.loads(line) for line in fh]
        self.assertEqual(len(answers), 16)
        self.assertEqual(answers[0]["answer_sha256"], rows[0]["answer_sha256"])
        entries = self.ledger()
        settles = [e for e in entries if e["event"] == "settle"]
        self.assertEqual(len(settles), 8)  # one batch per prompt and engine
        self.assertEqual({e["bucket"] for e in entries}, {"other"})
        self.assertEqual({e["vendor"] for e in settles}, {"openai", "perplexity"})
        self.assertAlmostEqual(sum(e["cost"] for e in settles), summary["cost_usd"], places=6)
        self.assertAlmostEqual(summary["cost_usd"], 4 * 2 * (0.01385 + 0.0021), places=6)

    def test_budget_zero_stops_before_any_call(self):
        os.environ["CLAUDE_PLUGIN_OPTION_OTHER_MONTHLY_USD"] = "0"
        with mock.patch.object(ap, "request_json", NoNetwork()):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("other_monthly_usd is 0", message)
        self.assertFalse(os.path.exists(self.out))

    def test_a_run_over_the_per_run_cap_never_starts(self):
        os.environ["CLAUDE_PLUGIN_OPTION_OTHER_MONTHLY_USD"] = "0.5"  # cap $0.125; 16 probes are estimated at $0.176
        with mock.patch.object(ap, "request_json", NoNetwork()):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("per-run", message)
        self.assertEqual(self.ledger(), [])

    def test_a_missing_key_names_the_plugin_option(self):
        os.environ["SEO_SUITE_PERPLEXITY_API_KEY"] = ""
        with mock.patch.object(ap, "request_json", NoNetwork()):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("perplexity_api_key", message)

    def test_anthropic_runs_only_when_asked(self):
        fake = FakeVendors()
        with mock.patch.object(ap, "request_json", fake):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out, "--engines", "anthropic",
                                              "--repeats", "1")
        self.assertEqual(code, 0, message)
        self.assertEqual(set(fake.hosts()), {"api.anthropic.com"})
        self.assertEqual(len(self.read_rows()), 4)

    def test_a_failed_call_keeps_its_estimate_and_the_rows_so_far(self):
        fake = FakeVendors(fail_on=3)
        with mock.patch.object(ap, "request_json", fake):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("HTTP 500", message)
        self.assertEqual(len(self.read_rows()), 2)
        failed = [e for e in self.ledger() if e["event"] == "settle" and e["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertTrue(failed[0]["estimated"])
        self.assertGreater(failed[0]["cost"], 0)

    def test_an_existing_output_file_is_never_mixed_into(self):
        with open(self.out, "w", encoding="utf-8") as fh:
            fh.write("query\n")
        with mock.patch.object(ap, "request_json", NoNetwork()):
            code, summary, message = run_main("run", PROMPTS, "--out", self.out)
        self.assertNotEqual(code, 0)
        self.assertIn("exists", message)


if __name__ == "__main__":
    unittest.main()
