#!/usr/bin/env python3
"""Pick the audit profile (which tool stack, how deep) by fixed rules, never by a question mid-run.

Usage:
  audit_profile.py --request-file seo-work/request.txt [--sitemap sitemap.json ...] [--crawl crawl.json]
                   [--connected SERVER ...] [--ignore-options] > seo-work/profile.json
Rules, in order (references/profiles.md R0-R10):
  Depth: a full phrase in the request → full; else a quick phrase, or option quick → quick; else full.
  Quick stops here.
  Size: summed sitemap total_urls > 2,000 → big; else a whole-site crawl (--max-pages 2001) that hit its limit
  → big; else small (sitemap count, crawl indexable_pages, or unknown until measured).
  Money: free phrase, paid phrase, option full-free, option paid, a budget this size's paid list uses, else free.
  Paid with no usable budget runs full-free and asks for one. Words beat the option; the option beats budgets.
The request file holds only the user's own words. Page text, tool output and vendor data never go in it.
Exit 0 with JSON on stdout; 2 when a plugin option is invalid (re-run with --ignore-options to continue).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from credit_guard import BUCKETS, VENDORS, GuardError, read_options, vendor_for

SIZE_BOUNDARY_URLS = 2000  # tools.md "Size boundary": small is up to 2,000 indexable URLs
WHOLE_SITE_CRAWL_PAGES = SIZE_BOUNDARY_URLS + 1  # so hit_page_limit means "more than 2,000 pages"
SECTION_CRAWL_PAGES = 2000
OPTION_VALUES = ("auto", "quick", "full-free", "paid")
PROFILE_OPTION_ENV = "CLAUDE_PLUGIN_OPTION_AUDIT_PROFILE"

# stack: default-free = tools.md "### Default: big website, free only"; small and big = each category's paid list
PROFILES: dict[str, dict] = {
    "quick": {"label": "Quick", "stack": None, "cross_checks": False, "report": "top-10"},
    "full-free": {"label": "Full · free", "stack": "default-free", "cross_checks": True, "report": "full"},
    "paid-small": {"label": "Full · paid, small", "stack": "small", "cross_checks": True, "report": "full"},
    "paid-big": {"label": "Full · paid, big", "stack": "big", "cross_checks": True, "report": "full"},
}
DEPTH: dict[str, dict] = {  # keyed by size class; quick has its own row
    "quick": {"crawl": {"mode": "none"}, "competitors": 0},
    "small": {"crawl": {"mode": "site", "max_pages": WHOLE_SITE_CRAWL_PAGES}, "competitors": 3},
    "big": {"crawl": {"mode": "sections", "max_pages": SECTION_CRAWL_PAGES}, "competitors": 10},
}

# Matched as whole words in the lowercased request, plus an optional plural s: "unpaid tools" is not paid, "quick
# checkout" is not quick, "quick checks" and "quick check-up" are, "quick wins" is nothing. Free beats paid, so each
# refusal ("avoid paid", "not paid") wins over the "paid tools" it contains.
REQUEST_WORDS: dict[str, tuple[str, ...]] = {
    "quick": ("quick check", "quick audit", "quick look", "quick scan", "quick seo check", "quick seo audit",
              "quick review", "spot check", "spot-check", "just this page", "only this page"),
    "full": ("full audit", "deep audit", "deep dive", "in-depth", "thorough", "thoroughly", "comprehensive"),
    "free": ("free only", "only free", "free tools only", "free tools", "free audit", "free stack", "no paid",
             "not paid", "without paid", "avoid paid", "skip paid", "never use paid", "don't use paid",
             "do not use paid", "don't want paid", "do not want paid", "no need for paid", "don't spend",
             "do not spend"),
    "paid": ("paid tools", "paid audit", "paid stack", "use paid", "use semrush", "use ahrefs", "use dataforseo",
             "use se ranking"),
}

# Guarded vendors with Main or Cross-check rows in that size's paid lists. Semrush is Reserve in every list, and Ahrefs'
# paid API in the small lists (its free domain-rating-free endpoint needs no budget), so their budgets never pick a
# paid list there.
PAID_LIST_VENDORS: dict[str, tuple[str, ...]] = {"small": ("dataforseo", "seranking"),
                                                 "big": ("dataforseo", "seranking", "ahrefs")}
# Vendors whose paid-list rows run through their MCP server. Ahrefs rows use REST v3 only (its MCP terms forbid
# scripts), so a connected Ahrefs MCP server asks nothing.
MCP_LIST_VENDORS = frozenset({"dataforseo", "seranking"})
REPORTED_BUDGETS = ("dataforseo_monthly_usd", "other_monthly_usd", "ahrefs_monthly_units", "semrush_monthly_units")
CONFIGURE = "/plugin configure seo-suite@seo-suite"


def budget_option(vendor: str) -> str:
    return BUCKETS[VENDORS[vendor][1]][1]


def number(value: float) -> str:
    return f"{value:,.0f}" if value == int(value) else f"{value:,}"


def request_intents(text: str) -> frozenset[str]:
    """The intents whose phrases appear in the user's request: lowercased, whitespace collapsed, ’ read as '."""
    text = " ".join(text.replace("’", "'").lower().split())
    return frozenset(intent for intent, phrases in REQUEST_WORDS.items()
                     if any(re.search(r"(?<![\w-])" + re.escape(phrase) + r"s?(?!\w)", text) for phrase in phrases))


def measure_size(sitemaps: list[dict], crawl: dict | None) -> tuple[str, int | None, str, str]:
    """(size_class, indexable_urls, size_source, reason) from sitemap_check.py reports and the whole-site crawl."""
    urls = sum(report["total_urls"] for report in sitemaps)
    listed = f"{urls:,} sitemap URLs" if urls else "no sitemap URLs"
    if urls and len(sitemaps) > 1:
        listed += f" over {len(sitemaps)} hosts"
    stopped = crawl is not None and not crawl["pages_crawled"]
    if stopped:
        crawl = None  # robots.txt stopped the crawl before it started, so it measured nothing
    if urls > SIZE_BOUNDARY_URLS:
        return "big", urls, "sitemap", f"{listed} > {SIZE_BOUNDARY_URLS:,}: big"
    if crawl and crawl["hit_page_limit"]:
        indexable = crawl["indexable_pages"]
        if not urls:
            why = f"more than {SIZE_BOUNDARY_URLS:,} crawlable pages"
        elif indexable > urls:
            why = "the sitemap under-lists the site"
        else:  # redirects, noindex or facets past the boundary
            why = f"more than {SIZE_BOUNDARY_URLS:,} crawlable pages, though fewer are indexable"
        return "big", indexable, "crawl-limit", (
            f"{listed}, but the whole-site crawl hit its {WHOLE_SITE_CRAWL_PAGES:,}-page limit "
            f"({indexable:,} indexable so far): big, {why}")
    if urls:
        return "small", urls, "sitemap", f"{listed}, up to {SIZE_BOUNDARY_URLS:,}: small"
    if crawl:
        return "small", crawl["indexable_pages"], "crawl", (
            f"{listed}; the whole-site crawl found {crawl['indexable_pages']:,} indexable pages: small")
    if stopped:
        return "small", None, "unknown", "no sitemap URLs, and the whole-site crawl fetched no pages: small depth"
    if sitemaps:
        return "small", None, "unknown", "no sitemap URLs and no crawl yet: small depth until the crawl is read"
    return "small", None, "unknown", "size not measured yet: small depth until the sitemap or crawl is read"


def pick(intents: frozenset[str], option: str, budgets: dict[str, float], connected: frozenset[str],
         size_class: str) -> tuple[str, str, list[str], list[str]]:
    """(profile, chosen_by, reasons, questions). Pure: words, then the option, then budgets, then the size."""
    reasons, questions = [], []
    set_budgets = [key for key in REPORTED_BUDGETS if budgets[key] > 0]
    if "full" in intents:
        if "quick" in intents:
            reasons.append("the request has full and quick words: full wins")
        elif option == "quick":
            reasons.append("the request's full words override audit_profile=quick")
    elif "quick" in intents or option == "quick":
        chosen_by = "request" if "quick" in intents else "option"
        if chosen_by == "request" and option in ("full-free", "paid"):
            reasons.append(f"the request's quick words override audit_profile={option}")
        reasons += [f"{key} {number(budgets[key])} not used: the quick profile makes no paid calls"
                    for key in set_budgets]
        return "quick", chosen_by, reasons + [f"quick (chosen by {chosen_by})"], questions

    list_budgets = [budget_option(vendor) for vendor in PAID_LIST_VENDORS[size_class]]
    usable = [key for key in list_budgets if budgets[key] > 0]
    reasons += [f"{key} {number(budgets[key])} picks no paid list on a {size_class} site: that vendor's paid rows are "
                "Reserve there" for key in set_budgets if key not in usable]
    if "free" in intents:
        money, chosen_by = "free", "request"
        if "paid" in intents:
            reasons.append("the request has free and paid words: free wins")
        elif option == "paid":
            reasons.append("the request's free words override audit_profile=paid")
    elif "paid" in intents:
        money, chosen_by = "paid", "request"
        if option == "full-free":
            reasons.append("the request's paid words override audit_profile=full-free")
    elif option in ("full-free", "paid"):
        money, chosen_by = ("free" if option == "full-free" else "paid"), "option"
    else:
        money, chosen_by = ("paid", "budgets") if usable else ("free", "default")

    if money == "free" and usable:
        why = "the request asks for free tools" if chosen_by == "request" else "audit_profile=full-free"
        reasons += [f"{key} {number(budgets[key])} not used: {why}" for key in usable]
    elif money == "paid" and usable:
        reasons.append(f"budgets the {size_class} paid list uses: "
                       + ", ".join(f"{key} {number(budgets[key])}" for key in usable))
    elif money == "paid":
        reasons.append(f"paid chosen by {chosen_by}, but no budget the {size_class} paid list uses "
                       f"({', '.join(list_budgets)}) is above 0: the run stays free")
        questions.append(f"Paid tools were asked for, but no budget the {size_class} paid list uses is above 0, so "
                         f"this run used the free stack. Recommendation: set {', '.join(list_budgets)} to the "
                         f"{size_class}-site values in references/tools.md \"Budget settings\" ({CONFIGURE}).")
        money, chosen_by = "free", "fallback"

    if chosen_by in ("default", "fallback"):
        vendors = {vendor_for(name) for name in connected}
        for vendor in PAID_LIST_VENDORS[size_class]:
            key = budget_option(vendor)
            if vendor in vendors and vendor in MCP_LIST_VENDORS and budgets[key] == 0:
                questions.append(f"A {vendor} MCP server is connected, but {key} is 0, so the credit guard denies its "
                                 f"paid calls and this run used the free stack. Recommendation: set {key} to the "
                                 f"{size_class}-site value in references/tools.md \"Budget settings\" ({CONFIGURE}) if "
                                 f"the {size_class} paid list should use it.")
    profile = f"paid-{size_class}" if money == "paid" else "full-free"
    return profile, chosen_by, reasons + [f"{profile} (chosen by {chosen_by})"], questions


def profile_settings(profile: str, size_class: str) -> dict:
    return {**PROFILES[profile], **DEPTH["quick" if profile == "quick" else size_class]}


def read_profile_option(env) -> str:
    raw = str(env.get(PROFILE_OPTION_ENV, "")).strip()
    if raw and raw not in OPTION_VALUES:
        raise GuardError(f"plugin option audit_profile={raw!r} must be one of {', '.join(OPTION_VALUES)}")
    return raw or "auto"


def read_report(path: str, key: str, script: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        report = json.load(fh)
    if not isinstance(report, dict) or key not in report:
        raise SystemExit(f"{path}: not {script} output (needs '{key}')")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--request-file", required=True, help="the user's own request (chat message or scheduled prompt)")
    ap.add_argument("--sitemap", action="append", default=[], help="sitemap_check.py JSON; once per host")
    ap.add_argument("--crawl", help="crawl.py JSON of the whole-site crawl run with --max-pages 2001")
    ap.add_argument("--connected", action="append", default=[], help="an MCP server name from Claude's tool list")
    ap.add_argument("--ignore-options", action="store_true", help="read no plugin options: auto, every budget 0")
    args = ap.parse_args()

    with open(args.request_file, encoding="utf-8") as fh:
        intents = request_intents(fh.read())
    names = [PROFILE_OPTION_ENV] + ["CLAUDE_PLUGIN_OPTION_" + key.upper() for key in REPORTED_BUDGETS]
    exported = any(name in os.environ for name in names)
    if args.ignore_options:
        option, budgets = "auto", dict.fromkeys(REPORTED_BUDGETS, 0.0)
    else:
        try:
            option = read_profile_option(os.environ)
            options = read_options(os.environ)
        except GuardError as exc:
            print(f"audit_profile.py: {exc}. Fix it with {CONFIGURE}, or re-run with --ignore-options.",
                  file=sys.stderr)
            return 2
        budgets = {key: options[key] for key in REPORTED_BUDGETS}
    sitemaps = [read_report(path, "total_urls", "sitemap_check.py") for path in args.sitemap]
    crawl = read_report(args.crawl, "pages_crawled", "crawl.py") if args.crawl else None

    size_class, indexable_urls, size_source, size_reason = measure_size(sitemaps, crawl)
    profile, chosen_by, reasons, questions = pick(intents, option, budgets, frozenset(args.connected), size_class)
    read = "options read: " + ", ".join([f"audit_profile={option}"]
                                        + [f"{key} {number(budgets[key])}" for key in REPORTED_BUDGETS])
    if args.ignore_options:
        read += "; plugin options ignored (--ignore-options)"
    elif not exported:
        read += " (none exported to Bash: defaults)"
    print(json.dumps({"profile": profile, **profile_settings(profile, size_class), "chosen_by": chosen_by,
                      "size_class": size_class, "indexable_urls": indexable_urls, "size_source": size_source,
                      "audit_profile_option": option, "options_exported": exported, "budgets": budgets,
                      "reasons": [size_reason, read] + reasons, "questions": questions}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
