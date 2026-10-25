#!/usr/bin/env python3
"""AI-answer probe: run a frozen, versioned prompt set through official APIs and log one row per answer for
ai_visibility.py. Each engine stands in for its consumer app; it is not a copy of it:
  openai      main          OpenAI Responses API with web_search (OpenAI: its search API uses ChatGPT search's
                            models and tool)
  perplexity  cross-check   Perplexity Agent API with web_search (Perplexity: API results can differ from its app)
  anthropic   optional      Claude API with the web_search tool
Consumer apps (chatgpt.com, perplexity.ai, claude.ai, gemini.google.com, Copilot) are never automated. Gemini answers
grounded with Google Search and Grounding with Bing output are never stored: their terms forbid it.

Prompt set (JSON). It is frozen: changing a prompt, the brand, the competitors or the locale changes its id, so give
it a new version.
  {"version": "2026-10-25.1", "brand": {"name": "Acme", "domain": "acme.ge", "aliases": ["აკმე", "Акме"]},
   "competitors": [{"name": "Rival", "domain": "rival.ge", "aliases": []}],
   "locale": {"country": "GE", "city": "Tbilisi", "region": "Tbilisi", "timezone": "Asia/Tbilisi"},
   "repeats": 3,
   "engines": {"openai": {"model": "gpt-5-mini"}, "perplexity": {"effort": "fast@2026-10-16.0"},
               "anthropic": {"model": "claude-haiku-5-5", "max_uses": 1}},
   "prompts": [{"id": "brand-ka-1", "class": "brand", "lang": "ka", "text": "რა არის Acme?"}]}
Classes: brand, category, comparison, problem. Write ka and ru prompts natively; never machine-translate them.
A name or alias counts as a mention as a whole word, ignoring case and separators ("Acme-Tutors" = "acme tutors").

Usage:
  ai_probe.py plan PROMPTS.json [--engines openai,perplexity] [--repeats 3]   # free: probes, estimate, budget
  ai_probe.py run PROMPTS.json --out seo-work/ai/observations-DATE.csv [--engines ...] [--repeats N] [--delay 1]
Keys come from SEO_SUITE_OPENAI_API_KEY, SEO_SUITE_PERPLEXITY_API_KEY and SEO_SUITE_ANTHROPIC_API_KEY, plugin options
exported at SessionStart. Spend counts against other_monthly_usd. The whole run is checked before the first call, each
prompt's batch per engine is reserved in the credit guard's ledger and settled with what it cost, and the run stops at
the monthly budget or the per-run cap. Rows go to --out, never into an existing file; the answers go to
<out>.answers.jsonl beside it, for accuracy review. Output is JSON on stdout.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
import unicodedata

import credit_guard as cg
from rank_snapshot import ApiError, belongs, domain_of, request_json
from seo_lib import print_json

ENGINES = {
    "openai": {"url": "https://api.openai.com/v1/responses", "key": "SEO_SUITE_OPENAI_API_KEY",
               "option": "openai_api_key", "role": "main: API stand-in for ChatGPT search"},
    "perplexity": {"url": "https://api.perplexity.ai/v1/agent", "key": "SEO_SUITE_PERPLEXITY_API_KEY",
                   "option": "perplexity_api_key", "role": "cross-check: API stand-in for Perplexity"},
    "anthropic": {"url": "https://api.anthropic.com/v1/messages", "key": "SEO_SUITE_ANTHROPIC_API_KEY",
                  "option": "anthropic_api_key", "role": "optional: API stand-in for Claude"},
}
DEFAULT_ENGINES = ("openai", "perplexity")  # the owner's choice on 2026-10-25: ChatGPT main, Perplexity cross-check
REFUSED_ENGINES = {
    "gemini": "not probed: answers grounded with Google Search may not be cached, analysed or stored (Gemini API "
              "Additional Terms, Grounded Results)",
    "bing": "not probed: Grounding with Bing output may not be stored or used to evaluate AI models (its terms)",
    "copilot": "not probed: Copilot has no API and its terms forbid bots; use Bing Webmaster Tools' AI Performance "
               "export instead",
    "chatgpt": "the consumer ChatGPT app is never automated; the openai engine is its API stand-in",
    "claude": "the consumer claude.ai app is never automated; the anthropic engine is its API stand-in",
    "google": "AI Overviews and AI Mode come from rank_snapshot.py's DataForSEO snapshots [vendor data]; seo-suite never "
              "fetches google.com",
}
CLASSES = ("brand", "category", "comparison", "problem")
# USD per 1M tokens (input, output), from the vendors' pricing pages checked 2026-10-24.
TOKEN_PRICES = {
    "openai": {"gpt-5-mini": (0.25, 2.00), "gpt-5.4-mini": (0.75, 4.50), "gpt-5.5": (5.00, 30.00),
               "gpt-6-luna": (0.10, 0.50)},
    "anthropic": {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00),
                  "claude-opus-5-5": (4.00, 20.00)},
}
PERPLEXITY_PRESET_PRICE = (0.25, 2.50)  # a preset's model isn't documented: priced as perplexity/sonar [estimate]
SEARCH_PRICES = {"openai": 0.01, "perplexity": 0.0025, "anthropic": 0.01}  # USD per search call
PROBE_TOKENS = (10_000, 1_000)  # input and output tokens per probe [estimate], as in references/tools.md
# [estimate] as references/tools.md sizes routine probes. The Responses API documents no search cap, so each batch
# settles with the searches that really ran, and the next batch's check uses that spend.
OPENAI_SEARCHES_PER_PROBE = 1
ANTHROPIC_TOOL = "web_search_20250305"  # the basic tool: every current model takes it, with no code execution step
ANTHROPIC_VERSION = "2023-06-01"  # the Messages API version header
ANTHROPIC_MAX_TOKENS = 4096
DEFAULT_REPEATS = 3
DEFAULT_DELAY_SECONDS = 1.0  # Perplexity's Agent API allows 1 request a second at usage tier 0
PERPLEXITY_EFFORT = re.compile(r"[a-z]+@\d{4}-\d{2}-\d{2}\.\d+")
CITATION_MARKER = re.compile(r"\[(?:web:)?(\d+)\]")  # [1] from the fast preset, [web:1] from low and above
CSV_COLUMNS = ["query", "engine", "run", "date", "mentioned", "cited", "cited_url", "competitors_mentioned", "locale",
               "lang", "prompt_class", "prompt_id", "prompt_set", "surface", "model_id", "tool_version", "search_calls",
               "cited_domains", "source_domains", "answer_sha256", "cost_usd"]
LABEL = ("Each engine is an API stand-in for its consumer app, not the app itself. OpenAI says its search API uses the "
         "models and tool of ChatGPT search; Perplexity says API results can differ from its app. Show citations "
         "whenever answers are shown to a client.")


@dataclasses.dataclass
class Answer:
    text: str
    citations: list[str]
    sources: list[str]
    search_calls: int
    model_id: str
    tool_version: str
    input_tokens: int = 0
    output_tokens: int = 0
    vendor_cost: float | None = None  # the vendor's own figure for this request, when it gives one


def unique(values) -> list:
    return list(dict.fromkeys(value for value in values if value))


# --------------------------------------------------------------------------------------------------------- prompt set

def load_prompt_set(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"{path}: file not found") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: not valid JSON ({exc})") from None

    def need(ok, what: str) -> None:
        if not ok:
            raise SystemExit(f"{path}: {what}")

    def text_list(value) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)

    def entity(value, where: str) -> dict:
        need(isinstance(value, dict) and isinstance(value.get("name"), str) and value["name"].strip()
             and isinstance(value.get("domain"), str) and value["domain"].strip(),
             f"{where} needs a name and a domain")
        need(text_list(value.get("aliases", [])), f"{where} aliases must be a list of names")
        domain = domain_of(value["domain"])
        return {"name": value["name"].strip(), "domain": domain,
                "names": unique([value["name"].strip(), *value.get("aliases", []), domain])}

    need(isinstance(data, dict), "expected a prompt-set object (see ai_probe.py's docstring)")
    need(isinstance(data.get("version"), str) and data["version"].strip(), "version must be a non-empty string")
    brand = entity(data.get("brand"), "brand")
    need(isinstance(data.get("competitors", []), list), "competitors must be a list")
    competitors = [entity(item, f"competitors[{n}]") for n, item in enumerate(data.get("competitors", []))]
    locale = data.get("locale")
    need(isinstance(locale, dict) and isinstance(locale.get("country"), str)
         and re.fullmatch(r"[A-Za-z]{2}", locale["country"]), "locale.country must be an ISO 3166-1 alpha-2 code, e.g. GE")
    need(all(isinstance(locale.get(k, ""), str) for k in ("city", "region", "timezone")),
         "locale city, region and timezone must be strings")
    locale = {"country": locale["country"].upper(), **{k: locale[k] for k in ("city", "region", "timezone")
                                                         if locale.get(k)}}
    repeats = data.get("repeats", DEFAULT_REPEATS)
    need(isinstance(repeats, int) and not isinstance(repeats, bool) and repeats >= 1, "repeats must be 1 or more")
    need(isinstance(data.get("engines", {}), dict), "engines must be an object")
    prompts = data.get("prompts")
    need(isinstance(prompts, list) and prompts, "prompts must be a non-empty list")
    ids = set()
    for number, prompt in enumerate(prompts):
        where = f"prompts[{number}]"
        need(isinstance(prompt, dict), f"{where} must be an object")
        need(isinstance(prompt.get("id"), str) and prompt["id"].strip() and prompt["id"] not in ids,
             f"{where} needs an id used once")
        need(prompt.get("class") in CLASSES, f"{where} class must be one of {', '.join(CLASSES)}")
        need(isinstance(prompt.get("lang"), str) and re.fullmatch(r"[a-z]{2,3}", prompt["lang"]),
             f"{where} lang must be a language code, e.g. ka")
        need(isinstance(prompt.get("text"), str) and prompt["text"].strip(), f"{where} needs a text")
        ids.add(prompt["id"])
    frozen = {"brand": brand, "competitors": competitors, "locale": locale,
              "prompts": [{k: p[k] for k in ("id", "class", "lang", "text")} for p in prompts]}
    digest = hashlib.sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"path": path, "version": data["version"].strip(), "id": f"{data['version'].strip()}@{digest[:12]}",
            "repeats": repeats, "engines": data.get("engines", {}), **frozen}


def parse_engines(text: str) -> list[str]:
    return unique(name.strip().lower() for name in text.split(","))


def check_engines(pset: dict, engines: list[str]) -> None:
    """Only the three official APIs, each with its model or preset pinned and priced."""
    for engine in engines:
        if engine in REFUSED_ENGINES:
            raise SystemExit(f"{engine}: {REFUSED_ENGINES[engine]}")
        if engine not in ENGINES:
            raise SystemExit(f"unknown engine {engine!r}; use {', '.join(ENGINES)}")
        config = pset["engines"].get(engine)
        if not isinstance(config, dict):
            raise SystemExit(f"{pset['path']}: engines.{engine} is missing; pin its model (see ai_probe.py's docstring)")
        if engine == "perplexity":
            effort = config.get("effort")
            if not (isinstance(effort, str) and PERPLEXITY_EFFORT.fullmatch(effort)):
                raise SystemExit(f"{pset['path']}: engines.perplexity.effort must be a pinned version such as "
                                 f"fast@2026-10-16.0, not {effort!r}; a response's effort field names the version")
            continue
        if config.get("model") not in TOKEN_PRICES[engine]:
            raise SystemExit(f"{pset['path']}: engines.{engine}.model {config.get('model')!r} has no price in "
                             f"ai_probe.py ({', '.join(TOKEN_PRICES[engine])}); add it from the vendor's pricing page")
        max_uses = config.get("max_uses", 1)
        if engine == "anthropic" and not (isinstance(max_uses, int) and not isinstance(max_uses, bool) and max_uses >= 1):
            raise SystemExit(f"{pset['path']}: engines.anthropic.max_uses must be 1 or more")


# ---------------------------------------------------------------------------------------------------------- requests

def build_request(engine: str, prompt: dict, pset: dict, key: str) -> tuple[str, dict, dict]:
    config, locale = pset["engines"][engine], pset["locale"]
    if engine == "openai":
        body = {"model": config["model"], "input": prompt["text"],
                "tools": [{"type": "web_search", "user_location": {"type": "approximate", **locale}}],
                "tool_choice": "required", "include": ["web_search_call.action.sources"]}
        return ENGINES[engine]["url"], {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body
    if engine == "perplexity":
        location = {k: locale[k] for k in ("country", "city", "region") if k in locale}
        body = {"effort": config["effort"], "input": prompt["text"],
                "tools": [{"type": "web_search", "user_location": location}]}
        return ENGINES[engine]["url"], {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body
    body = {"model": config["model"], "max_tokens": ANTHROPIC_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt["text"]}],
            "tools": [{"type": ANTHROPIC_TOOL, "name": "web_search", "max_uses": config.get("max_uses", 1),
                       "user_location": {"type": "approximate", **locale}}]}
    headers = {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}
    return ENGINES[engine]["url"], headers, body


def parse_openai(response: dict) -> Answer:
    texts, citations, sources, searches = [], [], [], 0
    for item in response.get("output") or []:
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            if action.get("type", "search") == "search":  # open_page and find_in_page actions aren't billed searches
                searches += 1
            sources += [source.get("url") for source in action.get("sources") or []]
        elif item.get("type") == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    texts.append(part.get("text", ""))
                    citations += [note.get("url") for note in part.get("annotations") or []
                                  if note.get("type") == "url_citation"]
    usage = response.get("usage") or {}
    return Answer("\n".join(texts), unique(citations), unique(sources), searches, response.get("model", ""),
                  "web_search", usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def parse_perplexity(response: dict) -> Answer:
    """Citations: the search results the answer's [n] markers point to, or every result when it has no markers
    (Perplexity calls the results the source of truth for citations)."""
    output = response.get("output") or []
    results = [r for item in output if item.get("type") == "search_results" for r in item.get("results") or []]
    texts = [part.get("text", "") for item in output if item.get("type") == "message"
             for part in item.get("content") or [] if part.get("type") == "output_text"]
    text = "\n".join(texts)
    by_id = {result.get("id"): result.get("url") for result in results if result.get("url")}
    marked = [by_id[int(n)] for n in CITATION_MARKER.findall(text) if int(n) in by_id]
    usage = response.get("usage") or {}
    searches = ((usage.get("tool_calls_details") or {}).get("search_web") or {}).get("invocation")
    cost = (usage.get("cost") or {}).get("total_cost")
    return Answer(text, unique(marked or by_id.values()), unique(r.get("url") for r in results),
                  searches if searches is not None else sum(1 for i in output if i.get("type") == "search_results"),
                  response.get("model", ""), response.get("effort", ""), usage.get("input_tokens", 0),
                  usage.get("output_tokens", 0), float(cost) if cost is not None else None)


def parse_anthropic(response: dict) -> Answer:
    texts, citations, sources = [], [], []
    for block in response.get("content") or []:
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
            citations += [c.get("url") for c in block.get("citations") or [] if c.get("type") == "web_search_result_location"]
        elif block.get("type") == "web_search_tool_result" and isinstance(block.get("content"), list):  # else an error
            sources += [r.get("url") for r in block["content"] if r.get("type") == "web_search_result"]
    usage = response.get("usage") or {}
    return Answer("".join(texts), unique(citations), unique(sources),
                  (usage.get("server_tool_use") or {}).get("web_search_requests", 0), response.get("model", ""),
                  ANTHROPIC_TOOL, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


PARSERS = {"openai": parse_openai, "perplexity": parse_perplexity, "anthropic": parse_anthropic}


def parse_answer(engine: str, response: dict) -> Answer:
    return PARSERS[engine](response)


# ------------------------------------------------------------------------------------------------------------- costs

def token_prices(engine: str, pset: dict) -> tuple[float, float]:
    return PERPLEXITY_PRESET_PRICE if engine == "perplexity" else TOKEN_PRICES[engine][pset["engines"][engine]["model"]]


def probe_estimate(engine: str, pset: dict) -> float:
    price_in, price_out = token_prices(engine, pset)
    searches = {"openai": OPENAI_SEARCHES_PER_PROBE, "perplexity": 1,
                "anthropic": pset["engines"].get("anthropic", {}).get("max_uses", 1)}[engine]
    return PROBE_TOKENS[0] * price_in / 1e6 + PROBE_TOKENS[1] * price_out / 1e6 + searches * SEARCH_PRICES[engine]


def answer_cost(engine: str, pset: dict, answer: Answer) -> tuple[float, bool]:
    """(USD, estimated): the vendor's own figure when it gives one, else the reported usage at the table's prices."""
    if answer.vendor_cost is not None:
        return round(answer.vendor_cost, 6), False
    price_in, price_out = token_prices(engine, pset)
    usd = (answer.input_tokens * price_in + answer.output_tokens * price_out) / 1e6
    return round(usd + answer.search_calls * SEARCH_PRICES[engine], 6), True


# -------------------------------------------------------------------------------------------------------------- rows

def normalise(text: str) -> str:
    return " ".join(re.sub(r"[\W_]+", " ", unicodedata.normalize("NFKC", text).casefold()).split())


def names_mentioned(text: str, names: list[str]) -> bool:
    haystack = f" {normalise(text)} "
    return any(f" {normalise(name)} " in haystack for name in names if normalise(name))


def observation_row(prompt: dict, pset: dict, engine: str, run: int, date: str, answer: Answer, cost_usd: float) -> dict:
    brand, config = pset["brand"], pset["engines"][engine]
    brand_urls = [url for url in answer.citations if belongs(domain_of(url), brand["domain"])]
    values = {
        "query": prompt["text"], "engine": engine, "run": run, "date": date,
        "mentioned": int(names_mentioned(answer.text, brand["names"])), "cited": int(bool(brand_urls)),
        "cited_url": brand_urls[0] if brand_urls else "",
        "competitors_mentioned": ";".join(c["domain"] for c in pset["competitors"]
                                          if names_mentioned(answer.text, c["names"])),
        "locale": "-".join(filter(None, (pset["locale"]["country"], pset["locale"].get("city")))),
        "lang": prompt["lang"], "prompt_class": prompt["class"], "prompt_id": prompt["id"], "prompt_set": pset["id"],
        "surface": "api", "model_id": answer.model_id or config.get("model") or config.get("effort"),
        "tool_version": answer.tool_version or config.get("effort", ""), "search_calls": answer.search_calls,
        "cited_domains": ";".join(unique(domain_of(url) for url in answer.citations)),
        "source_domains": ";".join(unique(domain_of(url) for url in answer.sources)),
        "answer_sha256": hashlib.sha256(answer.text.encode("utf-8")).hexdigest(), "cost_usd": cost_usd}
    return {column: values[column] for column in CSV_COLUMNS}


# ----------------------------------------------------------------------------------------------------------- commands

def prepare(args) -> tuple[dict, list[str], int]:
    pset = load_prompt_set(args.prompts)
    engines = parse_engines(args.engines)
    check_engines(pset, engines)
    return pset, engines, args.repeats or pset["repeats"]


def cmd_plan(args, env, now) -> dict:
    pset, engines, repeats = prepare(args)
    probes = len(pset["prompts"]) * repeats
    per_engine = {engine: {"probes": probes, "estimate_usd": round(probes * probe_estimate(engine, pset), 4),
                           "key_configured": bool(env.get(ENGINES[engine]["key"])), "role": ENGINES[engine]["role"]}
                  for engine in engines}
    estimate = sum(engine["estimate_usd"] for engine in per_engine.values())
    try:
        cg.script_check(env, cg.script_run_id(env), "ai_probe", "other", "this run", estimate, now)
        budget = {"fits": True}
    except cg.BudgetStop as stop:
        budget = {"fits": False, "reason": str(stop)}
    return {"prompt_set": pset["id"], "probes": probes * len(engines), "per_engine": per_engine,
            "estimate_usd": round(estimate, 4),
            "budget": {"bucket": "other", "other_monthly_usd": cg.read_options(env)["other_monthly_usd"], **budget},
            "estimate_note": f"[estimate] {PROBE_TOKENS[0]:,} tokens in and {PROBE_TOKENS[1]:,} out per probe; runs "
                             f"record what each answer really cost.", "label": LABEL}


def cmd_run(args, env, now) -> dict:
    pset, engines, repeats = prepare(args)
    if os.path.exists(args.out):
        raise SystemExit(f"{args.out} already exists; write each run to a new file, so a period never mixes two runs")
    run_id = cg.script_run_id(env)
    estimate = sum(len(pset["prompts"]) * repeats * probe_estimate(engine, pset) for engine in engines)
    probes = len(pset["prompts"]) * repeats * len(engines)
    try:
        cg.script_check(env, run_id, "ai_probe", "other", f"ai_probe.py {probes} probes ({pset['id']})", estimate, now)
    except cg.BudgetStop as stop:
        raise SystemExit(f"ai_probe.py: {stop} Nothing was called.") from None
    keys = {engine: env.get(ENGINES[engine]["key"]) for engine in engines}
    for engine, key in keys.items():
        if not key:
            raise SystemExit(f"{engine}: no API key. The user sets {ENGINES[engine]['option']} once with /plugin "
                             f"configure seo-suite@seo-suite; it reaches Bash as {ENGINES[engine]['key']} at the next "
                             f"session start.")
    answers_path = re.sub(r"\.csv$", "", args.out) + ".answers.jsonl"
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    date, written, spent, calls = now.strftime("%Y-%m-%d"), 0, 0.0, 0
    with open(args.out, "w", encoding="utf-8", newline="") as out, open(answers_path, "w", encoding="utf-8") as log:
        writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for prompt in pset["prompts"]:
            for engine in engines:
                call = f"ai_probe.py {engine} {prompt['id']} x{repeats}"
                try:
                    reservation = cg.script_reserve(env, run_id, engine, "other", call,
                                                    repeats * probe_estimate(engine, pset), cg.utc_now())
                except cg.BudgetStop as stop:
                    raise SystemExit(f"ai_probe.py stopped after {written} rows: {stop} The rows so far are in "
                                     f"{args.out}.") from None
                batch_cost, estimated, in_flight, failure = 0.0, False, False, None
                try:
                    for run in range(1, repeats + 1):
                        if calls:
                            time.sleep(args.delay)
                        calls += 1
                        in_flight = True
                        url, headers, body = build_request(engine, prompt, pset, keys[engine])
                        answer = parse_answer(engine, request_json("POST", url, headers, body))
                        cost, cost_estimated = answer_cost(engine, pset, answer)
                        batch_cost, estimated, in_flight = batch_cost + cost, estimated or cost_estimated, False
                        row = observation_row(prompt, pset, engine, run, date, answer, cost)
                        writer.writerow(row)
                        out.flush()
                        log.write(json.dumps({"answer_sha256": row["answer_sha256"], "prompt_id": prompt["id"],
                                              "prompt_set": pset["id"], "engine": engine, "run": run, "date": date,
                                              "model_id": row["model_id"], "text": answer.text,
                                              "citations": answer.citations}, ensure_ascii=False) + "\n")
                        log.flush()
                        written += 1
                except ApiError as error:
                    failure = error
                finally:
                    if in_flight:  # the call that failed may still have been charged
                        batch_cost, estimated = batch_cost + probe_estimate(engine, pset), True
                    cg.script_settle(env, reservation, round(batch_cost, 6), estimated,
                                     "failed" if in_flight else "ok", cg.utc_now())
                spent += batch_cost
                if failure:
                    raise SystemExit(f"{engine} {prompt['id']}: {failure}. The run stopped after {written} rows; they "
                                     f"are in {args.out}, and the spend is in the credit guard's ledger.")
    return {"prompt_set": pset["id"], "probes": probes, "rows_written": written, "cost_usd": round(spent, 6),
            "engines": {engine: {"model": pset["engines"][engine].get("model") or pset["engines"][engine]["effort"],
                                 "role": ENGINES[engine]["role"]} for engine in engines},
            "out": args.out, "answers": answers_path, "label": LABEL,
            "next": f"ai_visibility.py {args.out} --brand-domain {pset['brand']['domain']} --compare <the last run's CSV>"}


COMMANDS = {"plan": cmd_plan, "run": cmd_run}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = ap.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="free: probe count, estimate and whether the budget fits")
    run = commands.add_parser("run", help="run the prompt set through the APIs (paid)")
    run.add_argument("--out", required=True, help="new CSV for the rows, e.g. seo-work/ai/observations-2026-10-25.csv")
    run.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="seconds between calls")
    for command in (plan, run):
        command.add_argument("prompts", help="prompt-set JSON")
        command.add_argument("--engines", default=",".join(DEFAULT_ENGINES), help="comma list of openai, perplexity, "
                                                                                    "anthropic")
        command.add_argument("--repeats", type=int, help="runs per prompt and engine (default: the set's repeats)")
    args = ap.parse_args()
    if args.repeats is not None and args.repeats < 1:
        raise SystemExit("--repeats must be 1 or more")
    print_json(COMMANDS[args.command](args, os.environ, cg.utc_now()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
