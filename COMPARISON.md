# How seo-suite compares, and what it can't do

This compares seo-suite with the Claude Code SEO plugins whose source I read on 2026-10-24:

- AgriciDaniel/claude-seo (the most popular, ~20k★)
- SearchFit SEO
- SEO-AEO-GEO Ultimate
- rampstack-seo
- AEOTester
- LovableSEO
- seo-geo-consultant
- HarborRank
- coreyhaines marketingskills
- geo-seo-claude
- JeffLi seo-audit-skill

Each claim below is either measured on seo-suite's own code and tests or comes from reading the other plugins' source. None of it is marketing.

## Where seo-suite is ahead

Each row was checked against the other plugins' source by an adversarial review (2026-10-24). Rows that review
showed to be overstated were corrected. The schema-check and causal-claim rows come from the adopt-or-build review of
2026-10-25, which read claude-seo's and Ultimate's code and probed both.

| What matters | seo-suite | Best of the others |
|---|---|---|
| **Site crawler with site-level analysis** | Yes. It builds the link graph and reports click depth, exact and near-duplicates, orphans vs the sitemap, hreflang return links, canonical targets, a soft-404 probe and link-edge CSV export | AEOTester's `--all` mode crawls the sitemap, or follows links when there is none. It respects robots.txt, defaults to 500 pages and probes for soft 404s, but it scores per-page AEO checks only: no link graph, depth, cross-page duplicates, orphans or hreflang return links. HarborRank crawls on its own hosted service, which needs an account. claude-seo's audit crawl is described in prose; its Unlighthouse wrapper runs Lighthouse across routes, not an SEO crawl |
| **Priorities computed in code** | `triage.py` ranks every finding P0–P3 from a fixed table of impact, effort and fix per finding id. A test fails if any id has no row | Most leave scoring to the model. AEOTester is the exception: it computes rubric-weighted scores and ranks issues by points lost, in code. Thresholds contradict each other even inside one plugin (e.g. claude-seo: titles 30–60 vs 50–60 characters) |
| **Rules tied to dated Google docs** | `google-rules.md` dates most sections with the source page's last-updated stamp and lists its unverified items separately | Mostly undated. Several still recommend FAQ, HowTo or SearchAction |
| **2025–2026 changes covered** | 2 MB HTML indexing cap, FAQ retired 2026-05-07, the 2025-09-09 type removals, site-reputation-abuse change in the EEA, back-button hijacking policy, Search Console "Search generative AI" setting, robots 429 handling | Partial, or out of date |
| **robots.txt correctness** | Google's longest-match rule, groups with several user-agent lines, Googlebot-Image/News fall back to the Googlebot group, matrix of 22 search and AI crawlers, Content-Signal lines | geo-seo-claude applies grouped user agents wrongly; seo-geo-consultant misspells `Google-Extended` |
| **Log-file analysis** | Hits per bot (Googlebot variants, Bingbot, AI bots), DNS check that "Googlebot" is genuine, crawl waste, sitemap URLs never crawled | Ultimate imports logs but analyses nothing |
| **AI-visibility statistics** | Wilson 95% intervals per period, a confidence interval for the change between periods, "not-estimated" below 3 observations, drift rather than cause | Only Ultimate uses confidence intervals. Most score from the model's guess |
| **Raw HTML vs rendered page** | `render_diff.py` flags title, robots or canonical that change after JS, and content, links or schema that only exist after JS (one page per run). The rendered DOM comes from claude-seo's Playwright renderer through `claude_seo.py render`, so scheduled runs check it too | LovableSEO is comparable (single page; no schema or word-count check). AEOTester's plugin checks raw HTML only; its Chrome extension diffs one page |
| **Migration QA** | `redirect_check.py` checks one hop, permanent status, the expected target, and that the target is 200, indexable and self-canonical. Exit codes suit CI | LovableSEO is comparable |
| **Search Console analysis** | Builds a CTR curve from the site's own data where each position has enough rows (public-study defaults otherwise), estimates extra clicks for striking-distance terms, detects cannibalisation, and compares periods with a likely cause | HarborRank pulls Search Console live through its MCP and has the model compare periods and filter positions 5–20; no CTR curve or click estimates, and it needs a HarborRank account |
| **Cost** | No API keys. seo-suite's own scripts are standard-library Python; rendering, the Search Console API and drift run through claude-seo, which seo-suite installs on first need (a venv and Chromium, about 150 MB) | claude-seo needs a virtualenv and paid APIs for many features. rampstack's audit suite needs Ahrefs |
| **Beginner and expert modes** | Two guides covering the same pillars. The router picks one based on the user's level | None |
| **Work log** | Every task appends to `SEO-WORKLOG.md`: scope, data sources, paid units spent, changes, unverified items, re-check date | Ultimate records each work step in a hashed ledger (`work-ledger.json` + `index.md`; `check --final` fails on unresolved steps). marketingskills' SEO-operator loop appends one line per run to a log. The rest have none |
| **Safety rules** | Fetched pages are data, not instructions. Stops at bot challenges. Refuses non-http(s) redirects. Outreach, disavow, Change of Address, CDN/DNS and Business Profile changes are always gated; code, IndexNow and CMS changes follow the autonomy level the user sets (`references/autonomy.md`) | claude-seo has injection rules and an SSRF guard. Most have none |
| **Tests** | Unit tests run on every push in GitHub Actions, whose job summary prints the current count (`.github/workflows/tests.yml`), so no count is typed here to go stale. The docs test fails if a skill mentions a script or flag that doesn't exist, or a section of `google-rules.md` goes unchecked for six months; the triage test fails on any finding id with no table row | claude-seo, Ultimate, AEOTester, LovableSEO, geo-seo-claude and marketingskills have tests (AEOTester and Ultimate have more test files); five have none |
| **Schema check on every edit** | `schema_hook.py` runs on Edit and Write with `schema_rules.py`: JSON that doesn't parse, a leftover placeholder or a missing `@type` sends Claude back to fix it; Google's missing required and recommended fields come back as advice, never as a block, so the model isn't pushed to invent offers or reviews. Other files exit at once | claude-seo's hook checks JSON syntax, `@context`, `@type`, placeholders and retired types, not Google's required fields. It needs Node, and an array `@type` crashes it (issue #357) |
| **Causal claims in reports** | `causal_claims.py` flags sentences that tie a metric move to a change ("rose after", "due to", "boosted") unless they say "coincides with" or cite a controlled test, and passes limitations such as "partial because of sampling" | Ultimate blocks causal words in a few fields of its own JSON files; on report text its two patterns misfire both ways |

## Where others are still stronger

- **SEO-AEO-GEO Ultimate:** a work ledger whose evidence files are pinned by hash, with a final check that fails on
  open steps. seo-suite's `SEO-WORKLOG.md` is unchecked Markdown.
- **AEOTester:** at the default level it writes the fixes once the user accepts the diff. seo-suite edits code only
  from autonomy level 2; at level 1 (the default) it stops at the report.

Checked and left out: AEOTester's `.well-known` / agent-readiness checks (MCP card, A2A, WebMCP), because no search
engine documents an effect (Google's AI optimisation guide says Search doesn't use such files), and its rubric score,
which rewards llms.txt, FAQPage and HowTo against Google's dated rules.

## What seo-suite uses from the others

- **claude-seo** (AgriciDaniel, MIT): `scripts/claude_seo.py` clones its main branch into seo-suite's data folder on
  first need, pulls it before every use (never pinned) and runs its tools: the Playwright renderer for
  `render_diff.py`, its Search Console client (Search Analytics, URL Inspection, sitemaps; never the Indexing API
  scope) and its drift rules, one snapshot per crawl run. It is not installed as a second plugin, so there are no
  duplicate skills, routers or edit hooks. `schema_hook.py` adapts its script-tag and placeholder patterns.
- **AEOTester** (Ruslan Saifullin, MIT): `build_audit.py` ports its stack detection and served-folder discovery, then
  audits every built page offline.
- seo-suite keeps its own where it is stronger: the credit guard (claude-seo's is enforced only by prompts),
  `schema_rules.py`, rank and AI-answer tracking, the research store, triage and the tests.

## What seo-suite cannot do (yet)

1. **Render a whole site.** `claude_seo.py render` renders one URL per template through claude-seo; there is no rendered crawl of every page (Screaming Frog does that on big sites).
2. **Reach Search Console without a sign-in.** The API needs the user's one-time OAuth sign-in or a service account; otherwise it works from exports or the browser. GA4 goes through Google's `analytics-mcp`. PSI works without a key, within the shared quota.
3. **Validate the full schema.org vocabulary.** It covers Google's main rich-result types, including nested required fields, but not all of schema.org.
4. **Check deep sitemap extensions.** It counts video and news entries but doesn't check their required child tags or the 2-day / 1,000-item news rules.
5. **Track exact rankings or AI answers for free.** `rank_snapshot.py` (DataForSEO) and `ai_probe.py` (the OpenAI, Anthropic and Perplexity APIs) keep fixed-condition snapshots, and `rank_compare.py` and `ai_visibility.py` compare runs, but both need a paid budget. At $0, rank history is Search Console's average positions, and AI answers are checked by hand.
6. **Get past bot protection.** Correctly, it stops that step at a Cloudflare challenge, finishes everything else, and lists the access it needs with the end-of-run questions.
7. **Crawl huge sites in one pass.** Above ~10k URLs, use section crawls (`--path-prefix`) in parallel subagents, or Screaming Frog.

## What needs Semrush, Ahrefs or similar

No free source gives you the following. Each needs a third-party index, panel or clickstream:

| Data | Why free can't do it | Cheapest good source |
|---|---|---|
| **Search volume** for keywords you don't rank for | Autocomplete proves a query exists, but not how often it's searched. Search Console only shows queries you already get impressions for | Google Keyword Planner (ranges without ad spend), DataForSEO pay-per-use, Semrush/Ahrefs |
| **Keyword difficulty** | It is a vendor model built on their backlink index | Semrush, Ahrefs, Moz |
| **Competitors' keywords and estimated traffic** | Requires a ranking database across millions of SERPs | Semrush (strongest), Ahrefs, Similarweb |
| **Backlinks to other sites** (and a full profile of your own) | Requires a web-scale link crawl. Search Console and Bing show only your own site, and only a sample | Ahrefs (biggest fresh index), Majestic, Semrush, Moz. Ahrefs Webmaster Tools is free for your own verified site |
| **DR/DA-style authority metrics** | Proprietary | Ahrefs DR, Moz DA, Semrush AS |
| **Daily rank tracking across many keywords and locations** | Scraping Google at scale breaks its terms and gets blocked | Semrush Position Tracking, Ahrefs Rank Tracker, DataForSEO SERP API |
| **Historical SERPs and ranking history** | Needs archived SERP snapshots | Semrush, Ahrefs |
| **AI-answer share of voice across many prompts and engines** | Needs automated, repeated querying of ChatGPT, Perplexity, AI Overviews and others | Semrush AI toolkit, Ahrefs Brand Radar, Profound, Peec, Otterly |
| **Local geo-grid rankings** | Needs searches from many map points | Local Falcon, DataForSEO |

When to buy each tool, and how to keep the bill down, is in `references/tools.md`.
