# seo-suite

A Claude Code plugin that does SEO end to end, from a five-minute page check to a full audit, migration, or
AI-search visibility programme. It is built so the free path always works and paid tools are an upgrade
with a stated reason.

## What's inside

- **22 skills.** The `seo-suite` router plus audit, technical, onpage, content, blog-builder, blog-review,
  blog-system, keywords, schema, ai-search, local, international, ecommerce, media, links, migration, analytics,
  competitors, programmatic, strategy and automation.
- **3 agents.** `seo-site-auditor` collects data and `seo-serp-researcher` runs SERP batches in parallel, both on
  Sonnet; `seo-content-reviewer` grades pages on the session's model. No agent uses Haiku.
- **Scripts.** Python standard library only, no installs. They cover page audit, crawler, robots,
  sitemaps, PageSpeed/CrUX, keyword ideas, Search Console analysis, log analysis, redirect-map QA,
  content scoring, competitor comparison, render diff, SERP-overlap clustering, code-based triage (P0–P3), AI-visibility
  statistics with confidence intervals, translation checks across a post's language versions (`translation_check.py`)
  and AI-text quality heuristics with no AI-detection score (`ai_text_check.py`). `build_audit.py` audits a static
  build folder offline, and `causal_claims.py` flags report sentences that call a change the cause of a metric move.
- **claude-seo, used where it is better** (`claude_seo.py`). On first need seo-suite clones
  [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) into its own data folder, pulls its latest main
  before every use, and runs its tools: the Playwright renderer for JavaScript sites, its Search Console client
  (Search Analytics, URL Inspection, sitemaps; never the Indexing API) and its drift rules between crawls. It is not
  added as a second plugin.
- **A schema check on every edit** (`schema_hook.py`). After each Edit or Write of a markup file, JSON-LD that doesn't
  parse, a leftover placeholder or a missing `@type` goes back to Claude to fix; Google's missing fields come back as
  advice. Other files are skipped at once.
- **A shared research store** (`research_store.py`). Keyword, search-results and Search Console research is kept
  in one folder per site, so it is done once: every skill reads it first, re-fetches only what has gone stale, and
  writes new findings back.
- **A credit guard** (`credit_guard.py`). It runs as a hook around every paid API call. It reuses cached results,
  limits rows and keeps spending inside the monthly budgets you set. Every budget starts at 0, so paid calls are
  off until you choose otherwise.
- **Audit profiles** (`audit_profile.py`). An audit picks its tool stack and depth by fixed rules: the free
  big-website stack by default at every size, the paid list for the site's size only when a DataForSEO or other-tools
  budget (or Ahrefs, on big sites) is above 0, `audit_profile` is `paid`, or you ask for it, and a quick one-URL check
  only on request (`references/profiles.md`).
- **3 optional connectors** for Semrush, Ahrefs and DataForSEO, each the vendor's official MCP server.
- **References.**
  - `google-rules.md`: dated, verified Google and Bing rules, with an explicit list of unverified items.
  - `tools.md`: the default free stack every run uses, the labels (Main, Cross-check, Reserve) and the rules behind
    every list. `tools-paid.md`: the paid stacks for small and big sites, each category's Reserve table, the
    credit-guard limits, why each paid tool is worth it and how to spend less on it. `tools-sources.md`: their sources.
  - `guide-beginner.md` and `guide-expert.md`: the same SEO pillars at two depths. The router picks one
    for the user's level.
  - `autonomy.md`: what Claude decides on its own, what it asks, and the autonomy levels.
  - `paid-tools-automation.md`: how Semrush, Ahrefs and DataForSEO are automated, and the credit guard in detail.
  - `research-store.md`: the research store's layout, freshness rules and commands.
  - `ai-content-review.md`: review notes for AI-written and AI-translated content.
  - `scripts.md`: every script, its inputs and its output.
  - `worklog.md`: the `SEO-WORKLOG.md` entry format that every task appends to.

## Install

In Claude Code:

```
/plugin install seo-suite --marketplace ChaoticSurfer/seo-suite
```

Or from a terminal:

```bash
claude plugin marketplace add ChaoticSurfer/seo-suite
claude plugin install seo-suite@seo-suite
```

You need Python 3.9 or newer. The scripts use only the standard library, so there is nothing else to install by hand.
Rendering, the Search Console API and technical drift use claude-seo, which seo-suite installs itself the first time a
run needs it (a venv and Chromium, about 150 MB). That needs git and Python 3.11–3.14.

## Connect paid data (optional)

Everything works on free data. To add a paid source, install its connector:

```
/plugin install seo-suite-semrush@seo-suite
/plugin install seo-suite-ahrefs@seo-suite
/plugin install seo-suite-dataforseo@seo-suite
```

Then sign in: `/mcp` for Semrush and Ahrefs, and `/plugin configure seo-suite-dataforseo@seo-suite` for
DataForSEO's API login. Set the monthly budgets with `/plugin configure seo-suite@seo-suite`. Until you do, the
credit guard blocks every paid call.

[INTEGRATIONS.md](INTEGRATIONS.md) lists every tool the plugin works with, free and paid, how each one connects,
and what it costs.

## How much it does on its own

A run goes end to end without stopping to ask. Claude makes the SEO decisions itself and asks only for access it
lacks (a sign-in, an export) and for real business decisions, all together at the end. What it may change depends
on the autonomy level you set with `/plugin configure seo-suite@seo-suite`:

| Level | Runs without asking |
|---|---|
| **1. Analyse** (default) | Fetches, crawls, scripts, free APIs, paid calls within budget, reports, the work log |
| **2. Fix in code** | Level 1, plus edits, commits and pull requests in the site's repo |
| **3. Ship** | Level 2, plus merging pull requests that pass CI, and submitting sitemaps or IndexNow for changed URLs |
| **4. Operate** | Level 3, plus publishing to a CMS and Search Console sitemap submission through an authorised connector |

Some actions always need your OK, at every level: messages to real people, disavow files, deleting pages that earn
traffic, DNS and CDN changes, Business Profile and Merchant Center edits, and spending above budget. The run prepares
each one exactly and lists it at the end; Claude carries out the items you approve. Buying reviews or ranking links,
and anything a vendor's terms forbid, are never done. The full list is in [references/autonomy.md](references/autonomy.md).

## Use

Ask in plain words: "audit example.com", "why did traffic drop in September", "add Product schema",
"get us cited in ChatGPT", "teach me SEO". You can also call a skill directly: `/seo-suite:seo-audit`.

Scripts run on their own too. `<plugin-dir>` is your clone, `~/.claude/skills/seo-suite` for a local copy, or
`~/.claude/plugins/cache/seo-suite/seo-suite/<version>/` after a marketplace install:

```bash
python3 <plugin-dir>/scripts/page_audit.py https://example.com/
```

## Tests

```bash
python3 -m unittest discover -s <plugin-dir>/tests
```

`test_docs.py` fails if a skill references a script or flag that doesn't exist, or a section of `google-rules.md`
has gone unchecked for about six months. `test_scripts.py` fails if a script can emit a finding id that has no triage
row. GitHub Actions runs the suite on every push (`.github/workflows/tests.yml`) and prints the test count in the job
summary.

## Read next

- [COMPARISON.md](COMPARISON.md): how this plugin compares with 11 other Claude Code SEO plugins, what it can't
  do, and which data only Semrush, Ahrefs or similar tools can provide.
- [INTEGRATIONS.md](INTEGRATIONS.md): every tool the plugin connects to, how each connects, what it costs, and
  what is planned.
- [references/tools.md](references/tools.md) and [references/tools-paid.md](references/tools-paid.md): the free
  stack, then the paid stacks, the case for each paid tool and how to keep the bill down.
- [references/guide-beginner.md](references/guide-beginner.md) and
  [references/guide-expert.md](references/guide-expert.md): SEO strategy at two depths.

## Manage

- Installed from the marketplace: `claude plugin disable seo-suite@seo-suite`, or
  `claude plugin uninstall seo-suite@seo-suite`.
- A local copy in `~/.claude/skills/seo-suite` loads automatically as `seo-suite@skills-dir`. Delete the folder
  to remove it.

## Licence

MIT
