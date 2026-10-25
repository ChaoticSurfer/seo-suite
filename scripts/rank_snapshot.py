#!/usr/bin/env python3
"""Rank snapshots: where the site and its competitors rank for a fixed keyword set, with share of voice, visibility and
AI Overview references, from DataForSEO's Google Organic SERP API in the Standard queue. seo-suite never queries
google.com itself: these are vendor-collected results [vendor data].

A keyword set (JSON) fixes the conditions, so its snapshots stay comparable:
  {"version": "ge-ka-mobile-v1", "site": "example.ge", "location_code": 2268, "language_code": "ka",
   "device": "mobile", "depth": 20, "ai_overview": true, "competitors": ["rival.ge"],
   "keywords": [{"keyword": "ინგლისურის რეპეტიტორი", "volume": 390}, "a keyword without a volume"]}
Changing the conditions, the competitors or the keywords means a new version: share of voice compares only within one.
Georgia is 2268 (Tbilisi 1007469, Batumi 1007466); 21143 is the US state and is refused.

Usage:
  rank_snapshot.py plan SET                      # free: task_post bodies and the estimate, for the DataForSEO connector
  rank_snapshot.py run SET [--out-dir seo-work/rank] [--gsc Queries.csv] [--wait-minutes 45] [--poll-seconds 60]
  rank_snapshot.py run SET --resume TASKS_FILE   # free: fetch the tasks a run posted but couldn't wait for
  rank_snapshot.py parse SET task_get.json ...   # task_get/advanced responses saved through the connector
  rank_snapshot.py gsc SET Queries.csv           # the free default: own positions from a Search Console export
run reads DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD from the environment. Before posting it checks
dataforseo_monthly_usd, per_run_cap_pct and the credit guard's ledger, records the spend there, and stops at either
limit. A snapshot writes <version>-<date>.snapshot.json, plus .serps.json and .details.json for
`research_store.py ingest serps`. --gsc fits the CTR curve from the site's own export. Output is JSON on stdout.
"""
from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict

import credit_guard as cg
from gsc_analyze import DEFAULT_CTR, ctr_curve, expected_ctr, load_rows
from seo_lib import print_json, registrable_host

DFS_API = "https://api.dataforseo.com/v3/"
ORGANIC = "serp/google/organic/"
TASKS_PER_POST = 100  # DataForSEO refuses more in one POST (error 40006)
DEFAULT_DEPTH = 20  # two billed SERPs of 10 results
DEFAULT_WAIT_MINUTES = 45  # the Standard queue's target turnaround
DEFAULT_POLL_SECONDS = 60  # tasks_ready allows 20 calls a minute
DEFAULT_OUT_DIR = os.path.join("seo-work", "rank")
DEVICES = ("desktop", "mobile")
LOCATION_TRAPS = {21143: "the US state of Georgia; the country Georgia is 2268"}
# Every language_code in DataForSEO's Google SERP list (languages_serp_google_2026_04_06.csv): a typo fails here, before
# anything is reserved or posted.
GOOGLE_LANGUAGES = frozenset({
    "ach", "af", "ak", "am", "ar", "az", "ban", "be", "bem", "bg", "bn", "bs", "ca", "ceb", "ckb", "crs", "cs",
    "cy", "da", "de", "ee", "el", "en", "es", "es-419", "et", "eu", "fa", "fi", "fil", "fo", "fr", "fy", "ga",
    "gaa", "gl", "gu", "ha", "he", "hi", "hr", "ht", "hu", "hy", "id", "ig", "is", "it", "iw", "ja", "ka", "kg",
    "kk", "km", "kn", "ko", "kri", "ky", "lg", "ln", "lo", "loz", "lt", "lua", "lv", "mfe", "mg", "mi", "mk", "ml",
    "mn", "mr", "ms", "mt", "my", "ne", "nl", "no", "nso", "ny", "nyn", "om", "pa", "pcm", "pl", "ps", "pt",
    "pt-BR", "pt-PT", "qu", "rm", "rn", "ro", "ru", "rw", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "sr-Latn",
    "sr-ME", "st", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "tum", "uk", "ur", "uz",
    "vi", "wo", "xh", "yo", "zh-CN", "zh-TW", "zu"
})
TASK_OK, TASK_CREATED = 20000, 20100
SOURCE = "DataForSEO Google Organic SERP API, Standard queue [vendor data]"
DEFAULT_CURVE_SOURCE = "default curve (gsc_analyze.DEFAULT_CTR)"
TOP_DOMAINS = 15
RETRY_AFTER_SECONDS = (30, 60)  # (when the header is missing or unreadable, the most this script waits)
GSC_LABEL = ("Search Console average position: the topmost position averaged over impressions, across the countries "
             "and devices in the export, 2-3 days behind. It is not a fixed-condition snapshot rank; show the two side "
             "by side, never averaged.")
PAID_ADDS = [
    "A fixed-condition rank for every tracked keyword in this location, language and device, including keywords "
    "with no impressions yet",
    "Every competitor's position and share of voice from the same SERPs, at no extra cost",
    "AI Overview presence and the domains it cites, ours included",
]


class ApiError(Exception):
    """A paid API answered with an error or couldn't be reached; the caller records the spend, then stops."""


def retry_after(value: str | None) -> float:
    default, most = RETRY_AFTER_SECONDS
    return min(float(value), most) if value and re.fullmatch(r"\d+(\.\d+)?", value.strip()) else default


def request_json(method: str, url: str, headers: dict, body=None, timeout: float = 120):
    """One JSON request to a vendor API. A 429 is retried once after its Retry-After; any other failure raises."""
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    for attempt in (1, 2):
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:300]
            if err.code == 429 and attempt == 1:
                time.sleep(retry_after(err.headers.get("Retry-After")))
                continue
            raise ApiError(f"{url}: HTTP {err.code}: {detail}") from None
        except json.JSONDecodeError as err:
            raise ApiError(f"{url}: the answer is not JSON ({err})") from None
        except (OSError, http.client.HTTPException) as err:  # URLError, TLS, timeouts, a cut-off body
            raise ApiError(f"{url}: {getattr(err, 'reason', err)}") from None
    raise AssertionError("unreachable: the second attempt returns or raises")


# ---------------------------------------------------------------------------------------------------------------- set

def clean_keyword(text: str) -> str:
    return " ".join(str(text).lower().split())


def domain_of(value: str) -> str:
    """A host or URL as one domain form: lower case, punycode, no www."""
    return registrable_host(value if "://" in value else "https://" + value.strip().strip("/"))


def belongs(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def load_keyword_set(path: str) -> dict:
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

    need(isinstance(data, dict), "expected a keyword-set object (see rank_snapshot.py's docstring)")
    version, site = data.get("version"), data.get("site")
    need(isinstance(version, str) and version.strip(), "version must be a non-empty string")
    need(isinstance(site, str) and site.strip(), "site must be the site's domain, e.g. example.ge")
    location, language, device = data.get("location_code"), data.get("language_code"), data.get("device")
    need(is_count(location), "location_code must be a DataForSEO location code, e.g. 2268 for Georgia")
    need(location not in LOCATION_TRAPS, f"location_code {location} is {LOCATION_TRAPS.get(location)}")
    need(isinstance(language, str) and language in GOOGLE_LANGUAGES,
         f"language_code {language!r} is not in DataForSEO's Google language list (Georgian is ka, Russian ru, "
         f"English en)")
    need(device in DEVICES, f"device must be one of {', '.join(DEVICES)}")
    depth, ai_overview = data.get("depth", DEFAULT_DEPTH), data.get("ai_overview", False)
    need(is_count(depth) and 10 <= depth <= 700, "depth must be a whole number from 10 to 700")
    need(isinstance(ai_overview, bool), "ai_overview must be true or false")
    competitors = data.get("competitors", [])
    need(isinstance(competitors, list) and all(isinstance(c, str) and c.strip() for c in competitors),
         "competitors must be a list of domains")
    keywords = data.get("keywords")
    need(isinstance(keywords, list) and keywords, "keywords must be a non-empty list")
    parsed, seen = [], set()
    for number, item in enumerate(keywords):
        entry = item if isinstance(item, dict) else {"keyword": item}
        keyword, volume = entry.get("keyword"), entry.get("volume")
        need(isinstance(keyword, str) and keyword.strip(), f"keywords[{number}] needs a keyword string")
        clean = clean_keyword(keyword)
        need(clean not in seen, f"keywords[{number}] {keyword!r} is listed twice")
        need(volume is None or (is_count(volume) and volume >= 0), f"keywords[{number}] volume must be 0 or more")
        seen.add(clean)
        parsed.append({"keyword": clean, "volume": volume})
    return {"version": version.strip(), "site": domain_of(site), "location_code": location, "language_code": language,
            "device": device, "depth": depth, "ai_overview": ai_overview,
            "competitors": [domain_of(c) for c in competitors], "keywords": parsed}


# ----------------------------------------------------------------------------------------------------------- requests

def task_tag(kset: dict) -> str:
    return f"seo-suite|{kset['version']}"[:255]


def build_tasks(kset: dict, tag: str) -> list[dict]:
    tasks = []
    for item in kset["keywords"]:
        task = {"keyword": item["keyword"], "location_code": kset["location_code"],
                "language_code": kset["language_code"], "device": kset["device"], "depth": kset["depth"],
                "priority": 1, "tag": tag}
        if kset["ai_overview"]:
            task["load_async_ai_overview"] = True
        tasks.append(task)
    return tasks


def post_bodies(tasks: list[dict]) -> list[list[dict]]:
    return [tasks[start:start + TASKS_PER_POST] for start in range(0, len(tasks), TASKS_PER_POST)]


def estimate_usd(tasks: list[dict], max_rows: int) -> float:
    """The credit guard's own price for posting these tasks (depth, AI Overview and operators included)."""
    deepest = max(task["depth"] for task in tasks)
    if deepest > max_rows:
        raise SystemExit(f"depth {deepest} is above max_rows {max_rows}, the row limit the credit guard applies to "
                         f"every paid call; lower depth in the keyword set or raise max_rows")
    plan = cg.plan_call("dataforseo", "api_request", {"method": "POST", "path": ORGANIC + "task_post", "data": tasks},
                        max_rows)
    return round(plan.cost, 6)


def dfs_headers(env) -> dict:
    login = env.get("DATAFORSEO_LOGIN") or env.get("DATAFORSEO_USERNAME")
    password = env.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise SystemExit("run needs DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in the environment, the names the "
                         "DataForSEO connector uses. Without them, use `rank_snapshot.py plan` with the connector's "
                         "api_request, then `rank_snapshot.py parse`.")
    token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def checked(response, url: str) -> dict:
    """A DataForSEO answer whose own status is OK; 40000 and above (auth, balance, daily limit) is an error."""
    code = response.get("status_code") if isinstance(response, dict) else None
    if not isinstance(code, int) or code >= 40000:
        message = response.get("status_message") if isinstance(response, dict) else response
        raise ApiError(f"{url}: DataForSEO status {code}: {message}")
    return response


# ------------------------------------------------------------------------------------------------------------ parsing

def parse_task_get(response) -> list[dict]:
    """The SERPs in one saved task_get/advanced response, or a list of them: one dict per task."""
    serps = []
    for answer in response if isinstance(response, list) else [response]:
        if not isinstance(answer, dict) or not isinstance(answer.get("tasks"), list):
            raise SystemExit("not a DataForSEO task_get answer: expected an object with a tasks list")
        for task in answer["tasks"]:
            data = task.get("data") or {}
            result = (task.get("result") or [None])[0] or {}
            serps.append({"id": task.get("id"), "keyword": clean_keyword(result.get("keyword") or data.get("keyword", "")),
                          "status_code": task.get("status_code"), "status_message": task.get("status_message", ""),
                          "location_code": data.get("location_code"), "language_code": data.get("language_code"),
                          "device": data.get("device"), "check_url": result.get("check_url"),
                          "datetime": result.get("datetime"), "item_types": result.get("item_types") or [],
                          "items": result.get("items") or []})
    return serps


def refused_serp(error: dict) -> dict:
    """A keyword DataForSEO refused at posting (not charged): kept in the snapshot as an error row."""
    return {"id": None, "keyword": error["keyword"], "status_code": error["status_code"],
            "status_message": error["status_message"] or "refused at posting", "location_code": None,
            "language_code": None, "device": None, "check_url": None, "datetime": None, "item_types": [], "items": []}


def ai_overview_domains(items: list[dict]) -> list[str]:
    """Domains of every ai_overview_reference inside the AI Overview, top level or nested, in order of appearance."""
    found: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "ai_overview_reference" and (node.get("domain") or node.get("url")):
                domain = domain_of(node.get("domain") or node["url"])
                if domain not in found:
                    found.append(domain)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for item in items:
        if item.get("type") == "ai_overview":
            walk(item)
    return found


def position_of(row: dict, domain: str) -> int | None:
    positions = [r["position"] for r in row["results"] if belongs(r["domain"], domain)]
    return min(positions) if positions else None


def url_of(row: dict, domain: str) -> str | None:
    best = position_of(row, domain)
    return next((r["url"] for r in row["results"] if r["position"] == best and belongs(r["domain"], domain)), None)


def snapshot_row(serp: dict, kset: dict) -> dict:
    volume = next(k["volume"] for k in kset["keywords"] if k["keyword"] == serp["keyword"])
    items = serp["items"] if serp["status_code"] == TASK_OK else []
    results = sorted(({"position": item["rank_group"], "absolute": item.get("rank_absolute"),
                       "domain": domain_of(item.get("domain") or item["url"]), "url": item["url"],
                       "title": item.get("title") or ""}
                      for item in items if item.get("type") == "organic" and item.get("url")
                      and is_count(item.get("rank_group"))), key=lambda r: r["position"])
    referenced = ai_overview_domains(items)
    row = {"keyword": serp["keyword"], "volume": volume, "results": results}
    row.update({
        "position": position_of(row, kset["site"]), "url": url_of(row, kset["site"]),
        "competitors": {domain: position_of(row, domain) for domain in kset["competitors"]},
        "ai_overview": any(item.get("type") == "ai_overview" for item in items),
        "ai_overview_domains": referenced,
        "ai_overview_cited": any(belongs(domain, kset["site"]) for domain in referenced),
        "features": sorted(set(serp["item_types"]) or {item["type"] for item in items if item.get("type")})
        if items else [],
        "paa": [element["title"] for item in items if item.get("type") == "people_also_ask"
                for element in item.get("items") or [] if element.get("title")],
        "check_url": serp["check_url"]})
    if serp["status_code"] != TASK_OK:
        row["error"] = serp["status_message"] or f"DataForSEO status {serp['status_code']}"
    return row


# ------------------------------------------------------------------------------------------------------------ metrics

def ctr_at(curve: dict[int, float], position: int | None) -> float:
    return 0.0 if position is None else expected_ctr(curve, position)


def keyword_weights(rows: list[dict]) -> list[float]:
    """Search volume when every keyword has one, else equal weights (a partial volume list would drop keywords)."""
    if all(row.get("volume") is not None for row in rows):
        return [float(row["volume"]) for row in rows]
    return [1.0] * len(rows)


def share_of_voice(rows: list[dict], domain: str, curve: dict[int, float], depth: int) -> float:
    """Ahrefs/SISTRIX-style: Σ weight × CTR(the domain's position) / Σ weight × Σ CTR(1..depth). A domain's
    estimated clicks over the estimated clicks to every ranked result; named domains don't add up to 1."""
    weights = keyword_weights(rows)
    total = sum(weights) * sum(ctr_at(curve, position) for position in range(1, depth + 1))
    if not total:
        return 0.0
    return sum(weight * ctr_at(curve, position_of(row, domain)) for weight, row in zip(weights, rows)) / total


def visibility(rows: list[dict], domain: str, curve: dict[int, float]) -> float:
    """Semrush-style anchors, in %: 0 = no keyword ranks, 100 = position 1 for every keyword."""
    if not rows:
        return 0.0
    return sum(ctr_at(curve, position_of(row, domain)) for row in rows) / (len(rows) * ctr_at(curve, 1)) * 100


def metrics(rows: list[dict], kset: dict, curve: dict[int, float], curve_source: str) -> dict:
    ok = [row for row in rows if "error" not in row]
    named = [kset["site"]] + kset["competitors"]

    def canonical(host: str) -> str:
        return next((domain for domain in named if belongs(host, domain)), host)

    ranked = [row["position"] for row in ok if row["position"] is not None]
    hosts = sorted({canonical(result["domain"]) for row in ok for result in row["results"]})
    top = [{"domain": host, "share": round(share_of_voice(ok, host, curve, kset["depth"]), 4),
            "keywords_ranked": sum(1 for row in ok if position_of(row, host) is not None)} for host in hosts]
    top.sort(key=lambda entry: (-entry["share"], entry["domain"]))
    with_aio = [row for row in ok if row["ai_overview"]]
    cited = Counter(canonical(domain) for row in with_aio for domain in row["ai_overview_domains"])
    weighted = all(row.get("volume") is not None for row in ok)
    return {
        "keywords": len(rows), "errors": len(rows) - len(ok), "ranked": len(ranked),
        "top3": sum(1 for p in ranked if p <= 3), "top10": sum(1 for p in ranked if p <= 10),
        "average_position_when_ranked": round(sum(ranked) / len(ranked), 1) if ranked else None,
        "weighting": "search volume from the keyword set" if weighted
        else "equal weights: some keywords have no volume in the set",
        "ctr_curve_source": curve_source,
        "visibility_pct": {domain: round(visibility(ok, domain, curve), 1) for domain in named},
        "share_of_voice": {domain: round(share_of_voice(ok, domain, curve, kset["depth"]), 4) for domain in named},
        "top_domains": top[:TOP_DOMAINS],
        "ai_overview": {"serps_with_ai_overview": len(with_aio),
                        "cited_us": sum(1 for row in with_aio if row["ai_overview_cited"]),
                        "citation_share": {domain: round(count / len(with_aio), 4)
                                           for domain, count in cited.most_common()}},
        "estimate_note": "Share of voice and visibility are estimates from a CTR curve [estimate]; positions are "
                         "vendor-collected [vendor data].",
    }


def non_increasing(curve: dict[int, float], depth: int) -> dict[int, float]:
    """Positions 1..depth with no position worth more than the one above it, so visibility stays within 0-100%."""
    out, ceiling = {}, float("inf")
    for position in range(1, depth + 1):
        ceiling = min(ceiling, expected_ctr(curve, position))
        out[position] = ceiling
    return out


def ctr_curve_from(path: str | None) -> tuple[dict[int, float], str]:
    if not path:
        return dict(DEFAULT_CTR), DEFAULT_CURVE_SOURCE
    return ctr_curve(load_rows(path)), (f"fitted from {path} by gsc_analyze.ctr_curve: the site's own median CTR per "
                                        f"position, the default curve where its data is thin")


def build_snapshot(kset: dict, serps: list[dict], meta: dict, curve: dict[int, float] | None = None,
                   curve_source: str = DEFAULT_CURVE_SOURCE) -> dict:
    """One dated snapshot of the whole set; refuses SERPs from other conditions and a set with missing keywords."""
    wanted = {item["keyword"] for item in kset["keywords"]}
    by_keyword = {}
    for serp in serps:
        conditions = (serp["location_code"], serp["language_code"], serp["device"])
        expected = (kset["location_code"], kset["language_code"], kset["device"])
        if any(got is not None and got != want for got, want in zip(conditions, expected)):
            raise SystemExit(f"{serp['keyword']!r}: the SERP is for {'/'.join(map(str, conditions))}, not the set's "
                             f"{'/'.join(map(str, expected))}")
        if serp["keyword"] not in wanted:
            raise SystemExit(f"{serp['keyword']!r} is not in keyword set {kset['version']}")
        by_keyword[serp["keyword"]] = serp
    missing = [item["keyword"] for item in kset["keywords"] if item["keyword"] not in by_keyword]
    if missing:
        raise SystemExit(f"no SERP for {len(missing)} of the set's keywords (first: {missing[0]!r}); a snapshot needs "
                         f"the whole set, so share of voice stays comparable")
    rows = [snapshot_row(by_keyword[item["keyword"]], kset) for item in kset["keywords"]]
    curve = non_increasing(curve or dict(DEFAULT_CTR), kset["depth"])
    conditions = {key: kset[key] for key in ("site", "location_code", "language_code", "device", "depth",
                                              "ai_overview", "competitors")}
    return {"meta": {"set_version": kset["version"], **conditions, "keywords": len(rows), "source": SOURCE,
                     "ctr_curve": {str(p): round(c, 4) for p, c in sorted(curve.items())}, **meta},
            "rows": rows, "metrics": metrics(rows, kset, curve, curve_source)}


def store_files(rows: list[dict]) -> tuple[dict, dict]:
    """serps.json and details.json in the shapes `research_store.py ingest serps --details` reads."""
    serps, details = {}, {}
    for row in rows:
        if "error" in row:
            continue
        top = row["results"][:10]
        serps[row["keyword"]] = [result["url"] for result in top]
        details[row["keyword"]] = {"results": [{"url": r["url"], "title": r["title"]} for r in top],
                                   "features": row["features"], "paa": row["paa"]}
    return serps, details


# ---------------------------------------------------------------------------------------------------------- the files

def out_paths(out_dir: str, kset: dict, date: str) -> dict[str, str]:
    stem = os.path.join(out_dir, re.sub(r"[^A-Za-z0-9._-]+", "-", kset["version"]) + "-" + date)
    return {kind: f"{stem}.{kind}.json" for kind in ("snapshot", "serps", "details", "tasks")}


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def read_json(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"{path}: file not found") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: not valid JSON ({exc})") from None


def write_snapshot(paths: dict[str, str], kset: dict, snapshot: dict) -> dict:
    serps, details = store_files(snapshot["rows"])
    for kind, data in (("snapshot", snapshot), ("serps", serps), ("details", details)):
        write_json(paths[kind], data)
    files = {kind: path for kind, path in paths.items() if os.path.exists(path)}
    return {"set_version": kset["version"], "date": snapshot["meta"]["date"], "files": files,
            "metrics": snapshot["metrics"], "cost_usd": snapshot["meta"].get("cost_usd", 0.0),
            "next": f"research_store.py ingest serps {paths['serps']} --locale <the store locale for "
                    f"{kset['language_code']}> --details {paths['details']} --as-of {snapshot['meta']['date']}"}


# ----------------------------------------------------------------------------------------------------------- commands

def wait_for_tasks(ids: set[str], headers: dict, wait_minutes: float, poll_seconds: float) -> set[str]:
    deadline = time.monotonic() + wait_minutes * 60
    ready: set[str] = set()
    url = DFS_API + ORGANIC + "tasks_ready"
    while True:
        for task in checked(request_json("GET", url, headers), url).get("tasks") or []:
            ready |= {result.get("id") for result in task.get("result") or []} & ids
        if ready >= ids or time.monotonic() >= deadline:
            return ready
        time.sleep(poll_seconds)


def fetch_serps(ids: list[str], headers: dict) -> list[dict]:
    serps = []
    for task_id in ids:
        url = DFS_API + ORGANIC + "task_get/advanced/" + task_id
        serps += parse_task_get(checked(request_json("GET", url, headers), url))
    return serps


def post_tasks(kset: dict, tasks: list[dict], headers: dict, env, run_id: str, max_rows: int, now) -> dict:
    """Reserve the run's estimate, post every batch, and settle the ledger with DataForSEO's own cost figures."""
    estimate = estimate_usd(tasks, max_rows)
    call = f"rank_snapshot.py {len(tasks)} SERP tasks ({kset['version']})"
    reservation = cg.script_reserve(env, run_id, "dataforseo", "dataforseo", call, estimate, now)
    posted, errors, spent, failure = [], [], 0.0, None
    try:
        for body in post_bodies(tasks):
            url = DFS_API + ORGANIC + "task_post"
            try:
                response = checked(request_json("POST", url, headers, body), url)
            except ApiError as error:
                failure, spent = error, spent + estimate_usd(body, max_rows)  # it may have been charged
                break
            spent += float(response.get("cost") or 0)
            for task in response.get("tasks") or []:
                keyword = clean_keyword((task.get("data") or {}).get("keyword", ""))
                if task.get("status_code") == TASK_CREATED:
                    posted.append({"id": task["id"], "keyword": keyword})
                else:
                    errors.append({"keyword": keyword, "status_code": task.get("status_code"),
                                   "status_message": task.get("status_message")})
    finally:
        cg.script_settle(env, reservation, round(spent, 6), failure is not None, "failed" if failure else "ok",
                         cg.utc_now())
    return {"posted": posted, "errors": errors, "cost_usd": round(spent, 6), "failure": failure}


def free_fetch(step, set_path: str, tasks_path: str):
    """tasks_ready and task_get cost nothing, so a failure there stops the run with the free resume command."""
    try:
        return step()
    except ApiError as error:
        raise SystemExit(f"{error}. Nothing more was charged; fetch the posted tasks later for free: "
                         f"rank_snapshot.py run {set_path} --resume {tasks_path}") from None


def cmd_plan(args, env, now) -> dict:
    kset = load_keyword_set(args.set)
    tasks = build_tasks(kset, task_tag(kset))
    return {"set_version": kset["version"], "tasks": len(tasks),
            "estimate_usd": estimate_usd(tasks, int(cg.read_options(env)["max_rows"])),
            "task_post_bodies": post_bodies(tasks),
            "connector_steps": [
                "POST each body with the DataForSEO connector's api_request: method POST, path "
                "/v3/serp/google/organic/task_post, noAiMode true. The credit guard prices and records each call.",
                "Wait about 5 minutes, then GET /v3/serp/google/organic/tasks_ready (free) until it lists every task "
                "id from the POST answers.",
                "GET /v3/serp/google/organic/task_get/advanced/<id> for each id (free for 30 days) with noAiMode "
                "true, so depth and fields stay whole, and save each answer as a JSON file.",
                f"rank_snapshot.py parse {args.set} <the saved files> --out-dir {DEFAULT_OUT_DIR}"]}


def cmd_run(args, env, now) -> dict:
    kset = load_keyword_set(args.set)
    curve, curve_source = ctr_curve_from(args.gsc)
    if args.resume:
        posted = read_json(args.resume)
        if not isinstance(posted, dict) or not isinstance(posted.get("tasks"), list) or "date" not in posted:
            raise SystemExit(f"{args.resume}: not a rank_snapshot.py .tasks.json file")
        if posted.get("set_version") != kset["version"]:
            raise SystemExit(f"{args.resume}: posted for set {posted.get('set_version')!r}, not {kset['version']!r}")
        paths = out_paths(args.out_dir, kset, posted["date"])
        serps, not_ready = [], []
        for serp in free_fetch(lambda: fetch_serps([task["id"] for task in posted["tasks"]], dfs_headers(env)),
                               args.set, args.resume):
            (serps if serp["status_code"] == TASK_OK else not_ready).append(serp)
        if not_ready:
            first = not_ready[0]
            raise SystemExit(f"{len(not_ready)} tasks aren't ready (first: {first['keyword']!r}, DataForSEO status "
                             f"{first['status_code']}: {first['status_message']}). Try again later: rank_snapshot.py "
                             f"run {args.set} --resume {args.resume}")
    else:
        options = cg.read_options(env)
        date = now.strftime("%Y-%m-%d")
        paths = out_paths(args.out_dir, kset, date)
        if os.path.exists(paths["snapshot"]):
            raise SystemExit(f"{paths['snapshot']} already exists: set {kset['version']} was snapshotted today. "
                             f"Reuse it; to buy a fresh one, delete it first.")
        if os.path.exists(paths["tasks"]) and read_json(paths["tasks"]).get("tasks"):
            raise SystemExit(f"{paths['tasks']} already exists: set {kset['version']} was posted today and paid for. "
                             f"Fetch it for free: rank_snapshot.py run {args.set} --resume {paths['tasks']}")
        tasks = build_tasks(kset, task_tag(kset))
        max_rows, run_id = int(options["max_rows"]), cg.script_run_id(env)
        try:
            cg.script_check(env, run_id, "dataforseo", "dataforseo", f"{len(tasks)} SERP tasks",
                            estimate_usd(tasks, max_rows), now)
            headers = dfs_headers(env)
            result = post_tasks(kset, tasks, headers, env, run_id, max_rows, now)
        except cg.BudgetStop as stop:
            raise SystemExit(f"rank_snapshot.py: {stop} The free path still works: rank_snapshot.py gsc {args.set} "
                             f"<a Search Console Queries export>.") from None
        posted = {"set_version": kset["version"], "date": date, "posted_at": now.isoformat(timespec="seconds"),
                  "run_id": run_id, "tag": task_tag(kset), "cost_usd": result["cost_usd"],
                  "tasks": result["posted"], "errors": result["errors"]}
        write_json(paths["tasks"], posted)
        if result["failure"]:
            raise SystemExit(f"{result['failure']}. The tasks posted before it are in {paths['tasks']}; the spend is in "
                             f"the credit guard's ledger.")
        if not result["posted"]:
            raise SystemExit(f"DataForSEO created no task: {result['errors'][:3]}")
        ids = {task["id"] for task in result["posted"]}
        ready = free_fetch(lambda: wait_for_tasks(ids, headers, args.wait_minutes, args.poll_seconds), args.set,
                           paths["tasks"])
        if ready != ids:
            raise SystemExit(f"{len(ids - ready)} of {len(ids)} tasks are still in DataForSEO's queue after "
                             f"{args.wait_minutes:g} minutes. Fetching them later costs nothing (results stay 30 days): "
                             f"rank_snapshot.py run {args.set} --resume {paths['tasks']}")
        serps = free_fetch(lambda: fetch_serps([task["id"] for task in result["posted"]], headers), args.set,
                           paths["tasks"])
    serps += [refused_serp(error) for error in posted["errors"]]
    meta = {"date": posted["date"], "run_id": posted["run_id"], "tag": posted["tag"], "cost_usd": posted["cost_usd"],
            "post_errors": posted["errors"]}
    return write_snapshot(paths, kset, build_snapshot(kset, serps, meta, curve, curve_source))


def cmd_parse(args, env, now) -> dict:
    kset = load_keyword_set(args.set)
    curve, curve_source = ctr_curve_from(args.gsc)
    serps = [serp for path in args.responses for serp in parse_task_get(read_json(path))]
    dates = sorted(serp["datetime"][:10] for serp in serps if serp.get("datetime"))
    date = dates[0] if dates else now.strftime("%Y-%m-%d")
    snapshot = build_snapshot(kset, serps, {"date": date, "source_files": len(args.responses)}, curve, curve_source)
    return write_snapshot(out_paths(args.out_dir, kset, date), kset, snapshot)


def cmd_gsc(args, env, now) -> dict:
    """The free default: the set's own positions from Search Console, and what a paid snapshot would add."""
    kset = load_keyword_set(args.set)
    rows = load_rows(args.export)
    if not any("query" in row for row in rows):
        raise SystemExit(f"{args.export}: no query column; export Queries.csv, or a query+page export")
    by_query = defaultdict(list)
    for row in rows:
        by_query[clean_keyword(row["query"])].append(row)
    keywords = []
    for item in kset["keywords"]:
        found = by_query.get(item["keyword"], [])
        clicks, impressions = sum(r["clicks"] for r in found), sum(r["impressions"] for r in found)
        position = sum(r["position"] * r["impressions"] for r in found) / impressions if impressions else None
        top_page = max(found, key=lambda r: r["impressions"]).get("page") if found else None
        keywords.append({"keyword": item["keyword"], "volume": item["volume"], "clicks": round(clicks),
                         "impressions": round(impressions), "ctr": round(clicks / impressions, 4) if impressions else None,
                         "gsc_position": round(position, 1) if position is not None else None, "top_page": top_page})
    positions = [k["gsc_position"] for k in keywords if k["gsc_position"] is not None]
    options = cg.read_options(env)
    return {"set_version": kset["version"], "export": args.export, "label": GSC_LABEL, "keywords": keywords,
            "summary": {"tracked": len(keywords), "with_impressions": len(positions),
                        "top3": sum(1 for p in positions if p <= 3), "top10": sum(1 for p in positions if p <= 10)},
            "paid_adds": {"what": PAID_ADDS,
                          "estimate_usd_per_run": estimate_usd(build_tasks(kset, task_tag(kset)),
                                                               int(options["max_rows"])),
                          "budget_option": "dataforseo_monthly_usd",
                          "budget_now": options["dataforseo_monthly_usd"]}}


COMMANDS = {"plan": cmd_plan, "run": cmd_run, "parse": cmd_parse, "gsc": cmd_gsc}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = ap.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="free: task_post bodies and the estimate, for the DataForSEO connector")
    plan.add_argument("set", help="keyword-set JSON")
    run = commands.add_parser("run", help="post, wait, fetch and snapshot through the REST API (paid)")
    run.add_argument("set", help="keyword-set JSON")
    run.add_argument("--resume", help="a run's .tasks.json: fetch its tasks (free) instead of posting new ones")
    run.add_argument("--wait-minutes", type=float, default=DEFAULT_WAIT_MINUTES)
    run.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parse = commands.add_parser("parse", help="snapshot from task_get/advanced responses saved through the connector")
    parse.add_argument("set", help="keyword-set JSON")
    parse.add_argument("responses", nargs="+", help="saved task_get/advanced JSON answers")
    for command in (run, parse):
        command.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
        command.add_argument("--gsc", help="the site's Search Console export, to fit the CTR curve")
    gsc = commands.add_parser("gsc", help="free: own positions for the set from a Search Console export")
    gsc.add_argument("set", help="keyword-set JSON")
    gsc.add_argument("export", help="Queries.csv, or a query+page export")
    args = ap.parse_args()
    print_json(COMMANDS[args.command](args, os.environ, cg.utc_now()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
