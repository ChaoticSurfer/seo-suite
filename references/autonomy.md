# Autonomy policy

seo-suite is built to run SEO end to end without a human in the loop. The user supplies credentials once and sets
an autonomy level once. After that, every skill decides and acts on its own within those limits.

## What is never a question

Decide these from evidence, write the choice into the report's *Assumptions* section and into `SEO-WORKLOG.md`,
and carry on:

| Decision | How to decide it |
|---|---|
| Scope and crawl size | Sitemap URL count. Up to 2,000 URLs: crawl all. Above that: section crawls (`--path-prefix`) in parallel subagents |
| Templates and money pages | URL patterns in the crawl CSV; navigation; pages with forms, cart, checkout, booking or pricing; Product/Service/LocalBusiness schema |
| Market and language | `<html lang>`, ccTLD, hreflang, currency and addresses on the page |
| Competitors | Domains that rank in the top 10 for the site's head terms (WebSearch) |
| Keyword seeds | Titles, H1s and nav labels of money pages, plus GSC queries when available |
| Whether to research again | The research store (`seo-research/`, `references/research-store.md`): `research_store.py status` lists the stale and missing datasets per locale. Refresh only those, reuse the rest, and write new results back with `ingest` |
| What to check and fix first | The skill's workflow and `triage.py` priorities |
| Paid data calls | Allowed when inside the configured budget, and only for data free sources can't give (`tools.md`) |
| Beginner vs expert output | Infer from the user's wording. If unsure, give a plain summary with an expert appendix |

## What to ask (batched at the end of a run, each with a recommendation)

1. **Credentials and access** the run could not get: API keys, OAuth sign-ins, Search Console/GA4/Bing access or
   exports, repo access, or a CDN allowlist when a bot challenge blocks the crawl. Finish everything possible first.
   Then list exactly what each missing access would add.
2. **Business decisions:** markets or languages to enter, positioning, deleting or merging pages that earn traffic
   or revenue, and spend above the budget.
3. **Actions above the configured level** (below).

Never ask "should I continue?", never ask to confirm a read-only step, and never stop a run to ask something that
an assumption plus a note can cover.

## Autonomy levels (set once by the user)

| Level | Runs without asking | Still needs the user |
|---|---|---|
| **1. Analyse** (default) | All reads: fetches, crawls, scripts, free APIs, paid calls within budget, reports, work log, research store updates (uncommitted) | Any change to the site or any external account |
| **2. Fix in code** | Level 1 + edits to the site's repo on a branch, commits, pushing that branch, opening a PR | Merging, deploying |
| **3. Ship** | Level 2 + merging PRs that pass CI, submitting sitemaps / IndexNow for changed URLs | CMS publishing, account settings |
| **4. Operate** | Level 3 + CMS drafts/publishing and Search Console sitemap submission through an authorised connector | See "always gated" |

**Always gated, at every level:** messages to real people (outreach emails, DMs, review requests are drafted, never
sent), buying links or reviews, disavow files, deleting content that earns traffic, Change of Address, CDN/WAF and
DNS changes, Google Business Profile and Merchant Center edits, spend above budget, and anything a vendor's terms
forbid. The user can approve one of these for one run; that approval doesn't carry over to the next.

## Credentials

- The user enters keys and sign-ins into Claude Code's own configuration: plugin options, `claude mcp add` headers,
  OAuth pages, or environment variables. Never type a password into a website, and never paste keys into chat,
  logs or files that get committed. The research store is versioned with the repo, so it never holds secrets,
  raw paid responses or personal data (`references/research-store.md` §1).
- Prefer API/MCP access over driving a vendor's web UI. It is cheaper, more reliable, and allowed by the vendor's
  terms.
- If a sign-in page, CAPTCHA or bot challenge appears, stop that step, record it as an access request, and continue
  with everything else.

## Where the level and budgets live

The user sets them once with `/plugin configure seo-suite@seo-suite`:

| Key | Default | Meaning |
|---|---|---|
| `autonomy_level` | 1 | The level above (1–4) |
| `semrush_monthly_units`, `ahrefs_monthly_units` | 0 | Monthly budget for paid calls, in API units. 0 denies paid calls |
| `dataforseo_monthly_usd`, `other_monthly_usd` | 0 | Monthly budget for paid calls, in US dollars. 0 denies paid calls |
| `per_run_cap_pct` | 25 | The most one run may spend, as a percentage of each monthly budget |
| `ask_above_pct` | 5 | A single call estimated above this percentage of its monthly budget is deferred |
| `max_rows` | 50 | Row limit on every paid call |
| `cache_ttl_days` | 0 (per data type) | How long cached paid results are reused |
| `psi_api_key` | unset | Optional PageSpeed Insights key |

The credit guard (`hooks/hooks.json`) enforces them on every paid call. A call above `ask_above_pct` is deferred:
the guard denies it and records it as a batched request in its `requests.jsonl`, and Claude raises it with the
end-of-run questions. So "paid calls within budget" means within the monthly budget, the per-run cap and the
per-call threshold. If nothing is configured, that is level 1 with budgets of 0: free tools only, which still covers
a full audit. Setup and the guard's details: `skills/seo-automation` and `references/paid-tools-automation.md` §8.
