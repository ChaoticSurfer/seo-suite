#!/usr/bin/env python3
"""Credit guard for paid SEO MCP tools: cache, row-limit clamp, budgets and a circuit breaker, run by Claude Code hooks.

Usage (hooks/hooks.json runs it in exec form with the hook's JSON on stdin):
  credit_guard.py pre            PreToolUse. Free tool: no opinion. Cache hit: deny, naming the cached file to read.
                                 Missing or oversized row limit: clamp it (updatedInput keeps every other field).
                                 Over the monthly budget or the per-run cap: deny with the maths. Above the per-call
                                 threshold (or a Semrush report of unknown price): deny as deferred and append it to
                                 requests.jsonl for the end-of-run questions; runs never stop to ask. Otherwise allow.
                                 Any internal error: exit 2 (fail closed).
  credit_guard.py post           PostToolUse. Record the spend in the ledger, cache the raw response, report budget status.
  credit_guard.py post-failure   PostToolUseFailure. Record the estimate as possibly spent.
  credit_guard.py batch          PostToolBatch. Stop the agentic loop when this batch pushed a run or month past its cap.

Budgets are plugin options read from CLAUDE_PLUGIN_OPTION_<KEY>. A monthly budget of 0 (the default) denies that
vendor's paid calls. per_run_cap_pct and ask_above_pct are percentages of the monthly budget of the same bucket
(semrush, ahrefs, dataforseo, other). Prices are a static table from vendor docs checked 2026-10-24. A call whose
price is unknown is budgeted at the per-call threshold. PostToolUse cannot refund spend, so prevention happens in pre.
State: ${CLAUDE_PLUGIN_DATA}/credit-guard/ (ledger.jsonl, requests.jsonl, cache/), or
~/.claude/plugins/data/seo-suite/credit-guard/.

Scripts that call paid APIs themselves, which no hook sees (rank_snapshot.py, ai_probe.py), use script_check,
script_reserve and script_settle: the same options, ledger, monthly budgets and per-run caps. They find the state through
SEO_SUITE_DATA and their run through SEO_SUITE_SESSION_ID, both exported to Bash at SessionStart.
"""
from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import uuid
from typing import Any, Iterator, NamedTuple

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt


class GuardError(Exception):
    """A configuration or state problem the user has to fix; pre turns it into a block."""


# ---------------------------------------------------------------------------------------------------------------------
# Vendors and budgets

# vendor: (regex searched in the MCP server name, budget bucket; None = the vendor makes no per-call charge)
VENDORS: dict[str, tuple[str, str | None]] = {
    "semrush": (r"semrush", "semrush"),
    "ahrefs": (r"ahrefs", "ahrefs"),
    "dataforseo": (r"data[-_ ]?for[-_ ]?seo|(?:^|[_:-])dfs(?=[-_]|$)", "dataforseo"),  # DataForSEO's docs name it dfs-mcp
    "similarweb": (r"similar[-_ ]?web", "other"),
    "seranking": (r"se[-_ ]?ranking", "other"),
    "keywords-everywhere": (r"keywords?[-_ ]?everywhere", "other"),
    "alsoasked": (r"also[-_ ]?asked", "other"),
    "otterly": (r"otterly", "other"),
    "lumar": (r"lumar", "other"),
    "screaming-frog": (r"screaming[-_ ]?frog", None),  # licensed desktop app, runs locally
    "sitebulb": (r"sitebulb", None),  # licensed, read-only MCP
}

# bucket: (currency, monthly budget option)
BUCKETS: dict[str, tuple[str, str]] = {
    "semrush": ("units", "semrush_monthly_units"),
    "ahrefs": ("units", "ahrefs_monthly_units"),
    "dataforseo": ("usd", "dataforseo_monthly_usd"),
    "other": ("usd", "other_monthly_usd"),
}

OPTION_DEFAULTS: dict[str, float] = {
    "semrush_monthly_units": 0.0,
    "ahrefs_monthly_units": 0.0,
    "dataforseo_monthly_usd": 0.0,
    "other_monthly_usd": 0.0,
    "per_run_cap_pct": 25.0,
    "ask_above_pct": 5.0,
    "max_rows": 50.0,
    "cache_ttl_days": 0.0,  # 0 = use DATA_TYPE_TTL_DAYS
}

# Semrush documents methods at 1,000-10,000 units per request whose MCP report ids aren't public, so a Semrush call of
# unknown price is deferred to the user rather than budgeted silently.
DEFER_WHEN_PRICE_UNKNOWN = frozenset({"semrush"})
REQUEST_INPUT_SUMMARY_CHARS = 300

# A reservation made in pre counts toward the budget until post settles it, or until it is this old (declined prompts).
RESERVATION_MINUTES = 30

# Cache freshness by data type, from vendor refresh cycles: volumes monthly; SERPs, rankings and link deltas weekly.
DATA_TYPE_TTL_DAYS: dict[str, float] = {
    "keywords": 30,
    "serp": 7,
    "positions": 7,
    "domain": 7,
    "backlinks": 7,
    "audit": 1,
    "ai_visibility": 30,
    "default": 7,
}
SEMRUSH_MAX_CACHE_DAYS = 30  # Semrush terms: API data may not be cached for more than one month

# ---------------------------------------------------------------------------------------------------------------------
# Semrush MCP: discovery tools + get_report_schema are treated as free (Semrush's own skills warn only before
# execute_report; no doc states a price for them). execute_report bills the API report it runs.

SEMRUSH_FREE_TOOLS = frozenset({
    "domain_overview", "organic_research", "keyword_research", "competitors_research", "backlinks_research",
    "audience_research", "traffic_overview", "paid_search_research", "shopping_research", "position_tracking",
    "site_audit", "projects", "get_report_schema",
})
SEMRUSH_LIMIT_KEYS = ("display_limit", "limit")  # execute_report's schema isn't public; these are the API's names


class SemrushPrice(NamedTuple):
    units: int
    per: str  # "line" or "request"
    historical: int | None = None  # units per line when display_date asks for history; None = 5x
    max_lines: int | None = None  # lines returned without a row limit; None = needs a limit


SEMRUSH_REPORTS: dict[str, SemrushPrice] = {
    # keyword reports
    "phrase_this": SemrushPrice(10, "line", 50, 1),
    "phrase_these": SemrushPrice(10, "line", 50, 100),
    "phrase_all": SemrushPrice(10, "line", None, 150),  # one line per regional database
    "phrase_organic": SemrushPrice(10, "line", 50),
    "phrase_adwords": SemrushPrice(20, "line"),
    "phrase_fullsearch": SemrushPrice(20, "line"),
    "phrase_related": SemrushPrice(40, "line"),
    "phrase_questions": SemrushPrice(40, "line"),
    "phrase_kdi": SemrushPrice(50, "line", None, 100),
    "phrase_adwords_historical": SemrushPrice(100, "line"),
    # domain and URL reports
    "domain_organic": SemrushPrice(10, "line", 50),
    "domain_organic_unique": SemrushPrice(10, "line", 50),
    "domain_organic_subdomains": SemrushPrice(10, "line", 50),
    "domain_adwords": SemrushPrice(20, "line", 100),
    "domain_adwords_unique": SemrushPrice(40, "line"),
    "domain_organic_organic": SemrushPrice(40, "line", 200),
    "domain_adwords_adwords": SemrushPrice(40, "line", 200),
    "domain_adwords_historical": SemrushPrice(100, "line"),
    "domain_domains": SemrushPrice(80, "line", 400),
    "domain_shopping": SemrushPrice(30, "line", 150),
    "domain_shopping_unique": SemrushPrice(60, "line", 300),
    "domain_shopping_shopping": SemrushPrice(60, "line", 300),
    "domain_rank": SemrushPrice(10, "line", 50, 1),
    "domain_ranks": SemrushPrice(10, "line", None, 150),
    "domain_rank_history": SemrushPrice(10, "line"),
    "rank": SemrushPrice(10, "line"),
    "rank_difference": SemrushPrice(20, "line"),
    "url_rank": SemrushPrice(10, "line", 50, 1),
    "url_ranks": SemrushPrice(10, "line", None, 150),
    "url_rank_history": SemrushPrice(10, "line"),
    "url_organic": SemrushPrice(10, "line", 50),
    "url_adwords": SemrushPrice(20, "line", 100),
    # MCP report ids from Semrush's skills, priced as the API report they mirror [assumed, not documented]
    "resource_organic": SemrushPrice(10, "line", 50),
    "resource_organic_unique": SemrushPrice(10, "line", 50),
    "resource_adwords": SemrushPrice(20, "line", 100),
    # backlinks
    "backlinks_overview": SemrushPrice(40, "request"),
    "backlinks_ascore_profile": SemrushPrice(100, "request"),
    "backlinks_categories": SemrushPrice(50, "request"),
    **{name: SemrushPrice(40, "line") for name in (
        "backlinks", "backlinks_refdomains", "backlinks_refips", "backlinks_tld", "backlinks_geo", "backlinks_anchors",
        "backlinks_pages", "backlinks_competitors", "backlinks_matrix", "backlinks_comparison",
        "backlinks_categories_profile", "backlinks_historical",
    )},
    # Projects and Site Audit (read-only through the MCP)
    "list_projects": SemrushPrice(100, "request"),
    "snapshots": SemrushPrice(100, "request"),
    "info": SemrushPrice(100, "request"),
    "meta_issues": SemrushPrice(100, "request"),
    "issue_details": SemrushPrice(100, "request"),
    "page_info": SemrushPrice(1000, "request"),
}
SEMRUSH_AUDIT_REPORTS = frozenset({"list_projects", "snapshots", "info", "meta_issues", "issue_details", "page_info"})
SEMRUSH_ERROR = re.compile(r"\bERROR\s+\d+\s*::")  # e.g. "ERROR 132 :: API UNITS BALANCE IS ZERO": no data, no units

# ---------------------------------------------------------------------------------------------------------------------
# Ahrefs (API v3 metering, shared by the MCP): units = max(50, rows x sum of unique field costs in select/where/order_by)

AHREFS_FREE_PREFIXES = ("rank-tracker-", "management-", "subscription-info", "web-analytics-", "social-media-",
                        "public-", "gsc-")
AHREFS_FREE_TOOLS = frozenset({"doc", "site-audit-projects", "keywords-explorer-service-notices"})
AHREFS_BILLED_DESPITE_PREFIX = frozenset({"gsc-anonymous-queries"})
AHREFS_MIN_UNITS = 50
AHREFS_FIXED_UNITS = {"site-audit-issues": 50, "site-audit-page-explorer": 50, "site-audit-page-content": 50}
AHREFS_CONTENT_HELPER_UNITS = (1000, 500)  # topics, plus scoring a target_url
AHREFS_LIST_TOOLS = frozenset({  # list endpoints whose default limit is 1,000 rows
    "site-explorer-all-backlinks", "site-explorer-anchors", "site-explorer-broken-backlinks",
    "site-explorer-linkeddomains", "site-explorer-linked-anchors-external", "site-explorer-linked-anchors-internal",
    "site-explorer-organic-competitors", "site-explorer-organic-keywords", "site-explorer-paid-pages",
    "site-explorer-refdomains", "site-explorer-top-pages", "site-explorer-best-by-external-links",
    "site-explorer-best-by-internal-links", "keywords-explorer-overview", "keywords-explorer-matching-terms",
    "keywords-explorer-related-terms", "keywords-explorer-search-suggestions",
})
AHREFS_SINGLE_ROW_TOOLS = frozenset({
    "site-explorer-metrics", "site-explorer-domain-rating", "site-explorer-backlinks-stats",
    "site-explorer-outlinks-stats",
})
AHREFS_FIELD_UNITS: dict[str, int] = {
    **{name: 10 for name in (
        "traffic", "org_traffic", "sum_traffic", "volume", "keyword_difficulty", "difficulty", "value", "cost",
        "org_cost", "paid_traffic", "paid_cost", "traffic_potential", "intents", "global_volume", "parent_volume",
        "top_keyword_volume", "traffic_domain", "org_traffic_top_by_country",
    )},
    **{name: 5 for name in (
        "refdomains", "referring_domains", "all_positions", "refdomains_source", "class_c", "dofollow_refdomains",
        "live_refdomains", "all_time_refdomains",
    )},
    "volume_monthly_history": 24,  # 2 units per month; 12 months assumed
}

# ---------------------------------------------------------------------------------------------------------------------
# DataForSEO v3 MCP: docs_* tools are free; api_request bills by endpoint path (USD, October 2026 prices).

DFS_FREE_TOOLS = frozenset({"docs_index", "docs_list_sections", "docs_search"})
DFS_FREE_ENDPOINT = re.compile(r"(?:^|/)(?:appendix/user_data|tasks_ready|task_get)(?:/|$)")
DFS_LIVE_ENDPOINT = re.compile(r"(?:^|/)live(?:/|$)")  # the MCP sends only the first task of a Live request
DFS_LIMIT_ENDPOINTS = re.compile(  # list endpoints that take `limit` and return 100-1,000 items without it
    r"^dataforseo_labs/.*(?:ranked_keywords|keyword_suggestions|keyword_ideas|related_keywords|keywords_for_site"
    r"|competitors_domain|domain_intersection|page_intersection|serp_competitors|relevant_pages|subdomains)"
    r"|^backlinks/(?:backlinks|referring_domains|referring_networks|anchors|domain_pages|domain_pages_summary"
    r"|competitors|domain_intersection|page_intersection)/"
)
DFS_LABS_DOMAIN = re.compile(r"ranked_keywords|competitors|intersection|subdomains|relevant_pages|domain_|historical_rank")
DFS_MAX_ITEMS = 1000  # items per response when nothing bounds them
SEARCH_OPERATOR = re.compile(
    r"\b(?:site|inurl|intitle|intext|allinurl|allintitle|allintext|inanchor|allinanchor|filetype|related|cache):", re.I)


class DfsPrice(NamedTuple):
    pattern: str
    kind: str  # serp | task | items | pages
    base: float  # USD per task (serp: per 10 results; pages: per page)
    per_item: float = 0.0
    limit_field: str | None = None


DFS_PRICES = (
    DfsPrice(r"^serp/.+/task_post$", "serp", 0.0006, limit_field="depth"),
    DfsPrice(r"^serp/.+/live(?:/|$)", "serp", 0.002, limit_field="depth"),
    DfsPrice(r"^keywords_data/google_ads/.+/task_post$", "task", 0.06),  # up to 1,000 keywords per task
    DfsPrice(r"^keywords_data/google_ads/.+/live$", "task", 0.09),
    DfsPrice(r"^dataforseo_labs/", "items", 0.012, 0.00012, "limit"),
    DfsPrice(r"^backlinks/", "items", 0.024, 0.000036, "limit"),
    DfsPrice(r"^ai_optimization/llm_mentions/", "items", 0.1, 0.001, "limit"),
    DfsPrice(r"^on_page/task_post$", "pages", 0.00015, limit_field="max_crawl_pages"),
    DfsPrice(r"^on_page/instant_pages$", "pages", 0.00015),
)
DFS_PAGE_ADDONS = {"load_resources": 0.0003, "enable_javascript": 0.00135}
DFS_BROWSER_RENDERING_PER_PAGE = 0.0051

# Lumar reads are free; crawls draw credits per URL.
LUMAR_PAID_TOOLS = frozenset({"analyze_run_crawl", "analyze_resume_crawl", "analyze_create_single_page_request",
                              "lumar_act"})


# ---------------------------------------------------------------------------------------------------------------------
# Identification

def vendor_for(server: str) -> str | None:
    """The vendor whose pattern ends rightmost in the server name (the server key comes after any plugin name)."""
    best, best_end = None, -1
    for vendor, (pattern, _) in VENDORS.items():
        for match in re.finditer(pattern, server, re.I):
            if match.end() > best_end:
                best, best_end = vendor, match.end()
    return best


def identify(tool_name: str, mcp_server: Any) -> tuple[str, str] | None:
    """(vendor, tool) for mcp__<server>__<tool>, mcp__plugin_<plugin>_<server>__<tool> and mcp__claude_ai_<name>__<tool>."""
    if not tool_name.startswith("mcp__"):
        return None
    server, sep, tool = tool_name[len("mcp__"):].partition("__")
    if not sep or not tool:
        return None
    names = [server]
    if isinstance(mcp_server, dict) and mcp_server.get("name"):
        names.insert(0, str(mcp_server["name"]))
    for name in names:
        vendor = vendor_for(name)
        if vendor:
            return vendor, tool
    return None


def tool_id(vendor: str, tool: str) -> str:
    tool = tool.lower()
    return tool.replace("_", "-") if vendor == "ahrefs" else tool


# ---------------------------------------------------------------------------------------------------------------------
# Plans: what a call costs and the input it should run with

@dataclasses.dataclass
class Plan:
    tool_input: dict
    label: str = ""
    cost: float | None = None  # None = price unknown
    data_type: str = "default"
    changes: list[str] = dataclasses.field(default_factory=list)
    deny: str | None = None
    free: bool = False


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"\s*-?\d+\s*", value):
        return int(value)
    return None


def clamp_limits(obj: Any, keys: tuple[str, ...], max_rows: int) -> tuple[Any, list[int], list[str]]:
    """Copy of obj with every `keys` field (at any depth) capped at max_rows. 0 or less means "vendor default" and is
    capped too. Returns (copy, effective limits, change notes)."""
    limits: list[int] = []
    changes: list[str] = []

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        out = {}
        for key, value in node.items():
            if key in keys and not isinstance(value, (dict, list)):
                number = as_int(value)
                if number is None or number <= 0 or number > max_rows:
                    new = str(max_rows) if isinstance(value, str) else max_rows
                    changes.append(f"{key} {value!r} -> {max_rows}")
                    out[key] = new
                    limits.append(max_rows)
                else:
                    out[key] = value
                    limits.append(number)
            else:
                out[key] = walk(value)
        return out

    return walk(obj), limits, changes


def iter_strings(node: Any, key: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, str(k))
    elif isinstance(node, list):
        for item in node:
            yield from iter_strings(item, key)
    elif isinstance(node, str):
        yield key, node


def find_semrush_report(tool_input: dict) -> str | None:
    strings = list(iter_strings(tool_input))
    named = [value for key, value in strings if "report" in key.lower()]
    if named:
        return named[0]
    known = [value for _, value in strings if value in SEMRUSH_REPORTS]
    return known[0] if known else None


def semrush_data_type(report: str | None) -> str:
    if not report:
        return "default"
    if report.startswith("phrase_"):
        return "keywords"
    if report.startswith("backlinks"):
        return "backlinks"
    if report in SEMRUSH_AUDIT_REPORTS:
        return "audit"
    return "domain"


def plan_semrush(tool: str, tool_input: dict, max_rows: int) -> Plan:
    if tool in SEMRUSH_FREE_TOOLS:
        return Plan(tool_input, free=True)
    if tool != "execute_report":
        return Plan(tool_input, label=tool)
    report = find_semrush_report(tool_input)
    clamped, limits, changes = clamp_limits(tool_input, SEMRUSH_LIMIT_KEYS, max_rows)
    plan = Plan(clamped, label=f"execute_report {report or '(report id not found)'}",
                data_type=semrush_data_type(report), changes=changes)
    price = SEMRUSH_REPORTS.get(report or "")
    needs_limit = price is None or (price.per == "line" and price.max_lines is None)
    if needs_limit and not limits:
        plan.deny = (
            f"credit-guard: Semrush execute_report ({report or 'unidentified report'}) has no row limit, and an "
            f"unlimited report returns up to 10,000 lines at 10-80 units each. Call get_report_schema for this report "
            f"and pass its row-limit field (display_limit or limit) at {max_rows} or less."
        )
        return plan
    if price is None:
        return plan
    if price.per == "request":
        plan.cost = float(price.units)
        return plan
    lines = max(limits) if limits else price.max_lines
    if price.max_lines:
        lines = min(lines, price.max_lines)
    historical = any(key == "display_date" and value.strip() for key, value in iter_strings(tool_input))
    per_line = (price.historical or price.units * 5) if historical else price.units
    plan.cost = float(per_line * lines)
    return plan


def ahrefs_fields(tool_input: dict) -> set[str]:
    fields: set[str] = set()
    for key in ("select", "order_by"):
        value = tool_input.get(key)
        items = value if isinstance(value, list) else str(value or "").split(",")
        for item in items:
            name = str(item).split(":")[0].strip()
            if name:
                fields.add(name)
    where = tool_input.get("where")
    if where:
        text = where if isinstance(where, str) else json.dumps(where)
        fields |= set(re.findall(r'"field"\s*:\s*"([^"]+)"', text))
    return fields


def ahrefs_field_units(name: str) -> int:
    if name in AHREFS_FIELD_UNITS:
        return AHREFS_FIELD_UNITS[name]
    if name.startswith("ai_responses"):
        return 10
    if name.startswith("refdomains"):
        return 5
    return 1


def ahrefs_data_type(name: str) -> str:
    if name.startswith("serp-overview"):
        return "serp"
    if name.startswith("keywords-explorer"):
        return "keywords"
    if any(word in name for word in ("backlink", "refdomain", "anchor", "linked")):
        return "backlinks"
    if name.startswith("site-audit"):
        return "audit"
    if name.startswith("brand-radar"):
        return "ai_visibility"
    return "domain"


def plan_ahrefs(tool: str, tool_input: dict, max_rows: int) -> Plan:
    if tool not in AHREFS_BILLED_DESPITE_PREFIX and (tool in AHREFS_FREE_TOOLS or tool.startswith(AHREFS_FREE_PREFIXES)):
        return Plan(tool_input, free=True)
    plan = Plan(tool_input, label=tool, data_type=ahrefs_data_type(tool))
    if tool.startswith("content-helper"):
        base, scoring = AHREFS_CONTENT_HELPER_UNITS
        plan.cost = float(base + (scoring if tool_input.get("target_url") else 0))
        return plan
    if tool in AHREFS_FIXED_UNITS:
        plan.cost = float(AHREFS_FIXED_UNITS[tool])
        return plan
    clamped, limits, changes = clamp_limits(tool_input, ("limit",), max_rows)
    if not limits and tool in AHREFS_LIST_TOOLS:
        clamped = {**clamped, "limit": max_rows}
        limits = [max_rows]
        changes.append(f"limit missing (Ahrefs default 1,000 rows) -> {max_rows}")
    plan.tool_input, plan.changes = clamped, changes
    targets = tool_input.get("targets")
    if limits:
        rows = max(limits)
    elif tool.startswith("batch-analysis") and isinstance(targets, list) and targets:
        rows = len(targets)
    elif tool in AHREFS_SINGLE_ROW_TOOLS:
        rows = 1
    else:
        return plan
    per_row = sum(ahrefs_field_units(name) for name in ahrefs_fields(tool_input)) or 1
    plan.cost = float(max(AHREFS_MIN_UNITS, rows * per_row))
    return plan


def dfs_endpoint(tool_input: dict) -> str:
    raw = str(tool_input.get("path") or tool_input.get("url") or "")
    path = re.sub(r"^https?://[^/]+", "", raw).split("?")[0].strip("/").lower()
    path = re.sub(r"\.ai$", "", path)
    return re.sub(r"^v3/", "", path)


def dfs_data_type(endpoint: str) -> str:
    if endpoint.startswith("serp/"):
        return "serp"
    if endpoint.startswith("keywords_data/"):
        return "keywords"
    if endpoint.startswith("dataforseo_labs/"):
        return "domain" if DFS_LABS_DOMAIN.search(endpoint) else "keywords"
    if endpoint.startswith("backlinks/"):
        return "backlinks"
    if endpoint.startswith("on_page/"):
        return "audit"
    if endpoint.startswith("ai_optimization/"):
        return "ai_visibility"
    return "default"


def dfs_tasks(data: Any) -> list | None:
    """The request's task list; None when the body can't be read."""
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    if isinstance(data, str):
        try:
            return dfs_tasks(json.loads(data))
        except json.JSONDecodeError:
            return None
    return None


def dfs_task_cost(rule: DfsPrice, endpoint: str, task: dict, limits: list[int]) -> float:
    if rule.kind == "task":
        return rule.base
    if rule.kind == "serp":
        depth = max(limits) if limits else 10
        price = rule.base * math.ceil(depth / 10)
        if not DFS_LIVE_ENDPOINT.search(endpoint) and as_int(task.get("priority")) == 2:
            price *= 2
        price *= 5 ** len(SEARCH_OPERATOR.findall(str(task.get("keyword") or "")))
        return price + rule.base * (bool(task.get("load_async_ai_overview")) + bool(task.get("calculate_rectangles")))
    if rule.kind == "items":
        if limits:
            items = max(limits)
        elif "/summary/" in f"/{endpoint}/":
            items = 1
        else:
            listed = task.get("keywords") or task.get("targets")
            items = len(listed) if isinstance(listed, list) and listed else DFS_MAX_ITEMS
        price = rule.base + rule.per_item * items
        return price * 2 if task.get("include_clickstream_data") else price
    pages = max(limits) if limits else 1
    if task.get("enable_browser_rendering"):
        per_page = DFS_BROWSER_RENDERING_PER_PAGE
    else:
        per_page = rule.base + sum(cost for flag, cost in DFS_PAGE_ADDONS.items() if task.get(flag))
    return per_page * pages


def plan_dataforseo(tool: str, tool_input: dict, max_rows: int) -> Plan:
    if tool in DFS_FREE_TOOLS:
        return Plan(tool_input, free=True)
    if tool != "api_request":
        return Plan(tool_input, label=tool)
    endpoint = dfs_endpoint(tool_input)
    if DFS_FREE_ENDPOINT.search(endpoint):
        return Plan(tool_input, free=True)
    plan = Plan(tool_input, label=f"api_request {endpoint}", data_type=dfs_data_type(endpoint))
    rule = next((r for r in DFS_PRICES if re.search(r.pattern, endpoint)), None)
    tasks = dfs_tasks(tool_input.get("data"))
    if rule is None or tasks is None or not all(isinstance(task, dict) for task in tasks):
        return plan
    billed = (tasks or [{}])[:1] if DFS_LIVE_ENDPOINT.search(endpoint) else (tasks or [{}])
    add_missing = rule.kind == "pages" or (rule.kind == "items" and DFS_LIMIT_ENDPOINTS.search(endpoint))
    new_tasks, total = [], 0.0
    for index, task in enumerate(billed):
        limits: list[int] = []
        if rule.limit_field:
            task, limits, changes = clamp_limits(task, (rule.limit_field,), max_rows)
            if not limits and add_missing:
                task = {**task, rule.limit_field: max_rows}
                limits = [max_rows]
                changes.append(f"{rule.limit_field} missing -> {max_rows}")
            plan.changes += [f"task {index}: {change}" for change in changes]
        new_tasks.append(task)
        total += dfs_task_cost(rule, endpoint, task, limits)
    plan.cost = total
    if plan.changes:
        data = tool_input.get("data")
        rebuilt: Any = new_tasks + tasks[len(new_tasks):]
        if isinstance(data, dict) or (isinstance(data, str) and isinstance(json.loads(data), dict)):
            rebuilt = new_tasks[0]
        plan.tool_input = {**tool_input, "data": json.dumps(rebuilt) if isinstance(data, str) else rebuilt}
    return plan


def plan_lumar(tool: str, tool_input: dict, max_rows: int) -> Plan:
    if tool not in LUMAR_PAID_TOOLS:
        return Plan(tool_input, free=True)
    return Plan(tool_input, label=tool, data_type="audit")


def plan_unpriced(tool: str, tool_input: dict, max_rows: int) -> Plan:
    return Plan(tool_input, label=tool)


PLANNERS = {"semrush": plan_semrush, "ahrefs": plan_ahrefs, "dataforseo": plan_dataforseo, "lumar": plan_lumar}


def plan_call(vendor: str, tool: str, tool_input: dict, max_rows: int) -> Plan:
    if VENDORS[vendor][1] is None:
        return Plan(tool_input, free=True)
    return PLANNERS.get(vendor, plan_unpriced)(tool_id(vendor, tool), tool_input, max_rows)


# ---------------------------------------------------------------------------------------------------------------------
# Options, state, ledger and cache

def read_options(env: Any) -> dict[str, float]:
    options = {}
    for key, default in OPTION_DEFAULTS.items():
        raw = str(env.get("CLAUDE_PLUGIN_OPTION_" + key.upper(), "")).strip()
        if not raw:
            options[key] = default
            continue
        try:
            value = float(raw)
        except ValueError:
            raise GuardError(f"plugin option {key}={raw!r} is not a number") from None
        if not math.isfinite(value) or value < 0:
            raise GuardError(f"plugin option {key}={raw!r} must be 0 or more")
        options[key] = value
    if options["max_rows"] < 1:
        raise GuardError("plugin option max_rows must be at least 1")
    return options


def bucket_limits(bucket: str, options: dict[str, float]) -> tuple[float, float, float]:
    """(monthly budget, per-run cap, per-call threshold above which a call is deferred) in the bucket's currency."""
    monthly = options[BUCKETS[bucket][1]]
    return monthly, monthly * options["per_run_cap_pct"] / 100, monthly * options["ask_above_pct"] / 100


def unknown_price_estimate(bucket: str, options: dict[str, float]) -> float:
    """An unknown price is budgeted at the per-call threshold (the default 5% when the threshold is 0 = defer all)."""
    pct = options["ask_above_pct"] or OPTION_DEFAULTS["ask_above_pct"]
    return options[BUCKETS[bucket][1]] * pct / 100


def state_dir(env: Any) -> str:
    base = env.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".claude", "plugins", "data",
                                                         "seo-suite")
    return os.path.join(base, "credit-guard")


def ledger_path(state: str) -> str:
    return os.path.join(state, "ledger.jsonl")


def requests_path(state: str) -> str:
    return os.path.join(state, "requests.jsonl")


@contextlib.contextmanager
def locked(state: str) -> Iterator[None]:
    """Exclusive lock for ledger reads and writes; hooks for parallel tool calls run concurrently."""
    os.makedirs(state, exist_ok=True)
    with open(os.path.join(state, ".lock"), "a+") as handle:
        if fcntl:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        else:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def read_jsonl(path: str) -> list[dict]:
    """Every entry of a JSONL state file (ledger or requests); a corrupt line is an error, not a skip."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                raise GuardError(f"line {number} of {path} is not valid JSON; fix or delete that line "
                                 f"(paid calls stay blocked until then)") from None
    return entries


def append_jsonl(path: str, entry: dict) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


@dataclasses.dataclass
class Totals:
    month: float = 0.0
    run: float = 0.0
    in_flight: float = 0.0


def totals(entries: list[dict], bucket: str, month: str, session_id: str, now: dt.datetime) -> Totals:
    """Settled spend plus live reservations (pre allowed it, post hasn't settled it yet)."""
    settled: dict[str, dict] = {}
    reserved: dict[str, dict] = {}
    for entry in entries:
        if entry.get("bucket") == bucket:
            (settled if entry.get("event") == "settle" else reserved)[entry.get("tool_use_id")] = entry
    cutoff = now - dt.timedelta(minutes=RESERVATION_MINUTES)
    live = [e for tid, e in reserved.items() if tid not in settled and dt.datetime.fromisoformat(e["ts"]) > cutoff]
    result = Totals()
    for entry in list(settled.values()) + live:
        if entry.get("month") != month:
            continue
        cost = float(entry.get("cost") or 0)
        result.month += cost
        if entry.get("session_id") == session_id:
            result.run += cost
        if entry.get("event") != "settle":
            result.in_flight += cost
    return result


def cache_key(vendor: str, tool: str, tool_input: dict) -> str:
    canonical = json.dumps(tool_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(f"{vendor}\n{tool}\n{canonical}".encode("utf-8")).hexdigest()


def cache_file(state: str, vendor: str, key: str) -> str:
    return os.path.join(state, "cache", vendor, key + ".json")


def cache_ttl_days(vendor: str, data_type: str, options: dict[str, float]) -> float:
    days = options["cache_ttl_days"] or DATA_TYPE_TTL_DAYS.get(data_type, DATA_TYPE_TTL_DAYS["default"])
    return min(days, SEMRUSH_MAX_CACHE_DAYS) if vendor == "semrush" else days


def cache_lookup(path: str, days: float, now: dt.datetime) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            record = json.load(handle)
        fetched = dt.datetime.fromisoformat(record["fetched_at"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise GuardError(f"cache file {path} is unreadable; delete it") from None
    return record if now - fetched < dt.timedelta(days=days) else None


def write_cache(path: str, record: dict) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=1, default=str)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return "\n".join(response_text(item) for item in response)
    if isinstance(response, dict):
        if isinstance(response.get("text"), str):
            return response["text"]
        if "content" in response:
            return response_text(response["content"])
        return json.dumps(response, default=str)
    return "" if response is None else str(response)


def parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def actual_cost(vendor: str, response: Any) -> float | None:
    """The real charge when the response shows it."""
    text = response_text(response)
    if vendor == "semrush" and SEMRUSH_ERROR.search(text[:2000]):
        return 0.0  # Semrush: requests that return no data don't consume units
    if vendor == "dataforseo":
        data = parse_json(text)
        cost = data.get("cost") if isinstance(data, dict) else None
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            return float(cost)
    return None


def cacheable(vendor: str, response: Any) -> bool:
    text = response_text(response).strip()
    if not text:
        return False
    if vendor == "semrush" and SEMRUSH_ERROR.search(text[:2000]):
        return False
    if vendor == "dataforseo":
        data = parse_json(text)
        if isinstance(data, dict):
            tasks = data.get("tasks") if isinstance(data.get("tasks"), list) else []
            codes = [data.get("status_code")] + [t.get("status_code") for t in tasks if isinstance(t, dict)]
            if any(isinstance(code, int) and code >= 40000 for code in codes):
                return False
    return True


# ---------------------------------------------------------------------------------------------------------------------
# Hook handlers

def money(amount: float, currency: str) -> str:
    if currency == "usd":
        return f"${amount:,.2f}" if amount >= 1 else f"${amount:.4f}"
    return f"{amount:,.0f} units"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def ledger_entry(event: str, payload: dict, vendor: str, bucket: str, label: str, cost: float, estimated: bool,
                 status: str, now: dt.datetime) -> dict:
    return {
        "ts": now.isoformat(timespec="seconds"),
        "month": now.strftime("%Y-%m"),
        "event": event,
        "status": status,
        "vendor": vendor,
        "bucket": bucket,
        "currency": BUCKETS[bucket][0],
        "cost": round(cost, 6),
        "estimated": estimated,
        "call": label,
        "tool": payload.get("tool_name"),
        "tool_use_id": payload.get("tool_use_id") or f"missing-{uuid.uuid4().hex}",
        "session_id": payload.get("session_id"),
        "agent_id": payload.get("agent_id"),
        "agent_type": payload.get("agent_type"),
    }


def request_entry(payload: dict, vendor: str, bucket: str, plan: Plan, key: str, estimate: float, known: bool,
                  threshold: float, reason: str, now: dt.datetime) -> dict:
    """One requests.jsonl line: a paid call deferred to the user's end-of-run questions."""
    summary = json.dumps(plan.tool_input, sort_keys=True, ensure_ascii=False, default=str)
    if len(summary) > REQUEST_INPUT_SUMMARY_CHARS:
        summary = summary[:REQUEST_INPUT_SUMMARY_CHARS - 3] + "..."
    return {
        "ts": now.isoformat(timespec="seconds"),
        "session_id": payload.get("session_id"),
        "agent_id": payload.get("agent_id"),
        "vendor": vendor,
        "bucket": bucket,
        "tool": payload.get("tool_name"),
        "call": plan.label,
        "input_summary": summary,
        "estimate": round(estimate, 6),
        "currency": BUCKETS[bucket][0],
        "price_known": known,
        "threshold": round(threshold, 6),
        "reason": reason,
        "request_key": key,
    }


def record_request(path: str, request: dict) -> bool:
    """Append a deferred request unless this run already recorded the same call. Caller holds the lock."""
    for entry in read_jsonl(path):
        if entry.get("session_id") == request["session_id"] and entry.get("request_key") == request["request_key"]:
            return False
    append_jsonl(path, request)
    return True


def pre_output(decision: str, reason: str, updated_input: dict | None = None, context: str | None = None) -> dict:
    output: dict[str, Any] = {"hookEventName": "PreToolUse", "permissionDecision": decision,
                              "permissionDecisionReason": reason}
    if updated_input is not None:
        output["updatedInput"] = updated_input
    if context:
        output["additionalContext"] = context
    return {"hookSpecificOutput": output}


def tool_input_of(payload: dict) -> dict:
    tool_input = payload.get("tool_input")
    if tool_input is None:
        return {}
    if not isinstance(tool_input, dict):
        raise GuardError("tool_input is not a JSON object")
    return tool_input


def handle_pre(payload: dict, env: Any, now: dt.datetime) -> dict | None:
    found = identify(str(payload.get("tool_name") or ""), payload.get("mcp_server"))
    if not found:
        return None
    vendor, tool = found
    options = read_options(env)
    plan = plan_call(vendor, tool, tool_input_of(payload), int(options["max_rows"]))
    if plan.free:
        return None
    if plan.deny:
        return pre_output("deny", plan.deny)
    bucket = VENDORS[vendor][1]
    currency, budget_option = BUCKETS[bucket]
    state = state_dir(env)
    key = cache_key(vendor, tool_id(vendor, tool), plan.tool_input)
    path = cache_file(state, vendor, key)
    days = cache_ttl_days(vendor, plan.data_type, options)
    hit = cache_lookup(path, days, now)
    if hit:
        return pre_output("deny", (
            f"credit-guard: this exact {vendor} call ({plan.label}) was cached at {hit['fetched_at']} and stays fresh "
            f"for {days:g} days. Read {path} instead; it costs nothing. If fresh data is truly needed, delete that file "
            f"and call again."))
    monthly, run_cap, threshold = bucket_limits(bucket, options)
    if monthly <= 0:
        return pre_output("deny", (
            f"credit-guard: paid {vendor} calls are off because {budget_option} is 0. Use free or cached data. The user "
            f"sets the budget once with /plugin configure seo-suite@seo-suite (seo-suite@skills-dir for a local "
            f"copy); list it in the end-of-run questions."))
    known = plan.cost is not None
    estimate = plan.cost if known else unknown_price_estimate(bucket, options)
    shown = money(estimate, currency) + ("" if known else " (price unknown, budgeted at the per-call threshold)")
    with locked(state):
        spent = totals(read_jsonl(ledger_path(state)), bucket, now.strftime("%Y-%m"), payload.get("session_id"), now)
        if spent.month + estimate > monthly:
            return pre_output("deny", (
                f"credit-guard: over the monthly {bucket} budget. This month {money(spent.month, currency)} of "
                f"{money(monthly, currency)} is used (including {money(spent.in_flight, currency)} in flight); this call "
                f"({plan.label}) is estimated at {shown}; {money(max(monthly - spent.month, 0), currency)} remain. Use "
                f"cached or free data or a smaller row limit; raising {budget_option} is the user's decision."))
        if spent.run + estimate > run_cap:
            return pre_output("deny", (
                f"credit-guard: over the per-run {bucket} cap ({options['per_run_cap_pct']:g}% of the monthly budget = "
                f"{money(run_cap, currency)}). This run used {money(spent.run, currency)}; this call ({plan.label}) is "
                f"estimated at {shown}. Finish with cached or free data; raising per_run_cap_pct is the user's decision."))
        above_threshold = threshold <= 0 or estimate > threshold
        if above_threshold or (not known and vendor in DEFER_WHEN_PRICE_UNKNOWN):
            if above_threshold:
                why = (f"estimated {shown} > ask_above_pct {options['ask_above_pct']:g}% of the monthly {bucket} "
                       f"budget ({money(threshold, currency)})")
            else:
                why = f"{plan.label} has no known price, and some Semrush methods cost 1,000-10,000 units per request"
            request = request_entry(payload, vendor, bucket, plan, key, estimate, known, threshold, why, now)
            recorded = record_request(requests_path(state), request)
            return pre_output("deny", (
                f"credit-guard: deferred: {why}. {'Recorded' if recorded else 'Already recorded'} as a batched request "
                f"in {requests_path(state)}; continue with free sources and include it in the end-of-run questions."))
        append_jsonl(ledger_path(state), ledger_entry("reserve", payload, vendor, bucket, plan.label, estimate,
                                                       True, "allowed", now))
    reason = (f"credit-guard: {vendor} {plan.label} is estimated at {shown}. {bucket} this month: "
              f"{money(spent.month, currency)} of {money(monthly, currency)}; this run: {money(spent.run, currency)} of "
              f"{money(run_cap, currency)}.")
    context = None
    if plan.changes:
        context = "credit-guard clamped row limits to max_rows: " + "; ".join(plan.changes) + "."
        reason += " " + context
    return pre_output("allow", reason, plan.tool_input if plan.changes else None, context)


def handle_post(payload: dict, env: Any, now: dt.datetime, failed: bool = False) -> dict | None:
    found = identify(str(payload.get("tool_name") or ""), payload.get("mcp_server"))
    if not found:
        return None
    vendor, tool = found
    options = read_options(env)
    plan = plan_call(vendor, tool, tool_input_of(payload), int(options["max_rows"]))
    if plan.free:
        return None
    bucket = VENDORS[vendor][1]
    currency = BUCKETS[bucket][0]
    response = payload.get("tool_response")
    actual = None if failed else actual_cost(vendor, response)
    estimate = plan.cost if plan.cost is not None else unknown_price_estimate(bucket, options)
    cost = actual if actual is not None else estimate
    state = state_dir(env)
    with locked(state):
        entries = read_jsonl(ledger_path(state))
        entry = ledger_entry("settle", payload, vendor, bucket, plan.label, cost, actual is None,
                             "failed" if failed else "ok", now)
        append_jsonl(ledger_path(state), entry)
        spent = totals(entries + [entry], bucket, now.strftime("%Y-%m"), payload.get("session_id"), now)
    monthly, run_cap, _ = bucket_limits(bucket, options)
    line = (f"credit-guard: {vendor} {plan.label} {'cost' if actual is not None else 'estimated at'} "
            f"{money(cost, currency)}. {bucket} this month: {money(spent.month, currency)} of {money(monthly, currency)}; "
            f"this run: {money(spent.run, currency)} of {money(run_cap, currency)}.")
    if failed:
        line += (" The call failed; its estimate stays in the ledger in case the vendor charged it. Read the error "
                 "before retrying, and don't repeat the same call unchanged.")
    elif cacheable(vendor, response):
        path = cache_file(state, vendor, cache_key(vendor, tool_id(vendor, tool), plan.tool_input))
        write_cache(path, {
            "vendor": vendor, "tool": payload.get("tool_name"), "call": plan.label, "data_type": plan.data_type,
            "fetched_at": now.isoformat(timespec="seconds"), "tool_input": plan.tool_input, "response": response,
        })
        line += f" Raw response cached at {path}."
    event = "PostToolUseFailure" if failed else "PostToolUse"
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": line}}


def handle_post_failure(payload: dict, env: Any, now: dt.datetime) -> dict | None:
    return handle_post(payload, env, now, failed=True)


def handle_batch(payload: dict, env: Any, now: dt.datetime) -> dict | None:
    batch: dict[str, set[str]] = {}  # bucket -> tool_use_ids of this batch's paid vendor calls
    for call in payload.get("tool_calls") or []:
        found = identify(str(call.get("tool_name") or ""), None) if isinstance(call, dict) else None
        if found and VENDORS[found[0]][1]:
            batch.setdefault(VENDORS[found[0]][1], set()).add(call.get("tool_use_id"))
    if not batch:
        return None
    options = read_options(env)
    state = state_dir(env)
    with locked(state):
        entries = read_jsonl(ledger_path(state))
    crossed = []
    for bucket, ids in sorted(batch.items()):
        if not any(e.get("event") == "settle" and e.get("bucket") == bucket and e.get("tool_use_id") in ids
                   for e in entries):
            continue  # nothing in this batch spent from this bucket (free, cached or denied calls)
        currency = BUCKETS[bucket][0]
        monthly, run_cap, _ = bucket_limits(bucket, options)
        spent = totals(entries, bucket, now.strftime("%Y-%m"), payload.get("session_id"), now)
        if spent.month > monthly:
            crossed.append(f"{bucket} spent {money(spent.month, currency)} this month against a budget of "
                           f"{money(monthly, currency)}")
        if spent.run > run_cap:
            crossed.append(f"{bucket} spent {money(spent.run, currency)} this run against a cap of "
                           f"{money(run_cap, currency)}")
    if not crossed:
        return None
    return {"decision": "block", "reason": (
        "credit-guard circuit breaker: " + "; ".join(crossed) + ". The run stops here. Make no more paid calls; "
        "report the overspend and what it bought in the end-of-run questions for the user.")}


# ---------------------------------------------------------------------------------------------------------------------
# Scripts the hooks never see (rank_snapshot.py, ai_probe.py): the same options, ledger and limits, before each batch

SCRIPT_SESSION_ENV = "SEO_SUITE_SESSION_ID"  # exported at SessionStart, so a script's spend counts in its session
SCRIPT_DATA_ENV = "SEO_SUITE_DATA"  # the hooks' CLAUDE_PLUGIN_DATA, exported at SessionStart (Bash has none)


class BudgetStop(Exception):
    """A script's next batch would pass a monthly budget or the per-run cap: the script stops before spending."""


def script_state_dir(env: Any) -> str:
    data = env.get(SCRIPT_DATA_ENV)
    return os.path.join(data, "credit-guard") if data else state_dir(env)


def script_run_id(env: Any) -> str:
    """The run a script's spend counts in: its Claude Code session when known, else this process alone."""
    return env.get(SCRIPT_SESSION_ENV) or f"script-{uuid.uuid4().hex}"


def check_script_spend(entries: list[dict], options: dict[str, float], run_id: str, vendor: str, bucket: str,
                       call: str, estimate: float, now: dt.datetime) -> None:
    """Raise BudgetStop when the estimate would pass the bucket's monthly budget or per-run cap, as pre denies."""
    currency, budget_option = BUCKETS[bucket]
    monthly, run_cap, _ = bucket_limits(bucket, options)
    if monthly <= 0:
        raise BudgetStop(f"paid {vendor} calls are off because {budget_option} is 0. The user sets the budget once "
                         f"with /plugin configure seo-suite@seo-suite; list it in the end-of-run questions.")
    spent = totals(entries, bucket, now.strftime("%Y-%m"), run_id, now)
    if spent.month + estimate > monthly:
        raise BudgetStop(f"over the monthly {bucket} budget. This month {money(spent.month, currency)} of "
                         f"{money(monthly, currency)} is used (including {money(spent.in_flight, currency)} in flight); "
                         f"{call} is estimated at {money(estimate, currency)}; "
                         f"{money(max(monthly - spent.month, 0), currency)} remain. Raising {budget_option} is the "
                         f"user's decision.")
    if spent.run + estimate > run_cap:
        raise BudgetStop(f"over the per-run {bucket} cap ({options['per_run_cap_pct']:g}% of the monthly budget = "
                         f"{money(run_cap, currency)}). This run used {money(spent.run, currency)}; {call} is estimated "
                         f"at {money(estimate, currency)}. Raising per_run_cap_pct is the user's decision.")


def script_check(env: Any, run_id: str, vendor: str, bucket: str, call: str, estimate: float,
                 now: dt.datetime) -> None:
    """Check a whole run before its first batch, writing nothing."""
    options = read_options(env)
    state = script_state_dir(env)
    with locked(state):
        check_script_spend(read_jsonl(ledger_path(state)), options, run_id, vendor, bucket, call, estimate, now)


def script_reserve(env: Any, run_id: str, vendor: str, bucket: str, call: str, estimate: float,
                   now: dt.datetime) -> dict:
    """Check the next batch and reserve its estimate in the ledger; returns the entry script_settle settles."""
    options = read_options(env)
    state = script_state_dir(env)
    payload = {"tool_name": "script", "tool_use_id": f"script-{uuid.uuid4().hex}", "session_id": run_id}
    with locked(state):
        check_script_spend(read_jsonl(ledger_path(state)), options, run_id, vendor, bucket, call, estimate, now)
        entry = ledger_entry("reserve", payload, vendor, bucket, call, estimate, True, "allowed", now)
        append_jsonl(ledger_path(state), entry)
    return entry


def script_settle(env: Any, reservation: dict, cost: float, estimated: bool, status: str, now: dt.datetime) -> dict:
    """Record what a reserved batch cost. estimated=False only when the vendor's own figure gave the cost."""
    payload = {key: reservation[key] for key in ("tool_use_id", "session_id")} | {"tool_name": reservation["tool"]}
    entry = ledger_entry("settle", payload, reservation["vendor"], reservation["bucket"], reservation["call"], cost,
                         estimated, status, now)
    state = script_state_dir(env)
    with locked(state):
        append_jsonl(ledger_path(state), entry)
    return entry


HANDLERS = {"pre": handle_pre, "post": handle_post, "post-failure": handle_post_failure, "batch": handle_batch}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in HANDLERS:
        print(f"usage: credit_guard.py {{{'|'.join(HANDLERS)}}} < hook-input.json", file=sys.stderr)
        return 2
    event = argv[1]
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise GuardError("hook input is not a JSON object")
        output = HANDLERS[event](payload, os.environ, utc_now())
    except Exception as exc:  # pre fails closed on any internal error; the other events surface the traceback
        if event != "pre":
            raise
        print(f"credit-guard failed closed ({type(exc).__name__}: {exc}). No paid SEO call runs until this is fixed.",
              file=sys.stderr)
        return 2
    if output is not None:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
