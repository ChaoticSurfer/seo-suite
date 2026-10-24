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

## Why it is the strongest free option

| What matters | seo-suite | Best of the others |
|---|---|---|
| **Real site crawler** | Yes. Its output covers links, depth, duplicates, near-duplicates, orphans, hreflang return links, soft-404 probe and canonical targets | None ships one. claude-seo only describes a "500-page crawl" in prose |
| **Scores and priorities computed in code** | `triage.py` uses a fixed table (impact, effort, fix per finding id) to rank P0–P3, and a test fails if any finding has no row | The model does the arithmetic. Thresholds contradict each other even inside one plugin |
| **Thresholds tied to dated Google docs** | `google-rules.md` cites each rule with its source and update date, and lists 16 unverified items separately | Mostly undated. Several still recommend FAQ, HowTo or SearchAction, or use the `en-UK` code |
| **2025–2026 changes covered** | 2 MB HTML indexing cap, FAQ retired 2026-05-07, the 2025-09-09 type removals, site-reputation-abuse change in the EEA, back-button hijacking policy, Search Console "Search generative AI" setting, robots 429 handling | Partial, or out of date |
| **robots.txt correctness** | Google's longest-match rule, groups with several user-agent lines, Googlebot-Image/News fall back to the Googlebot group, matrix of 22 search and AI crawlers, Content-Signal lines | geo-seo-claude applies grouped user agents wrongly; seo-geo-consultant misspells `Google-Extended` |
| **Log-file analysis** | Hits per bot (Googlebot variants, Bingbot, AI bots), DNS check that "Googlebot" is genuine, crawl waste, sitemap URLs never crawled | ultimate only imports logs and analyses nothing |
| **AI-visibility statistics** | Wilson 95% intervals, "not-estimated" below 3 observations, changes reported as drift rather than cause | Only ultimate uses confidence intervals. Most score from the model's guess |
| **Raw HTML vs rendered page** | `render_diff.py` flags title, robots or canonical that change after JS, and content, links or schema that only exist after JS | AEOTester and LovableSEO do one page at a time |
| **Migration QA** | `redirect_check.py` checks one hop, permanent status, the expected target, and that the target is 200, indexable and self-canonical. Exit codes suit CI | LovableSEO is comparable |
| **Search Console analysis** | Builds a CTR curve from the site's own data (not industry averages), estimates extra clicks for striking-distance terms, detects cannibalisation, and compares periods with a likely cause | HarborRank does this, but on a paid server whose logic you can't inspect |
| **Cost** | No installs, no API keys, standard-library Python | claude-seo needs a virtualenv and paid APIs for many features. rampstack's audit suite needs Ahrefs |
| **Beginner and expert modes** | Two guides covering the same pillars. The router picks one based on the user's level | None |
| **Work log** | Every task appends to `SEO-WORKLOG.md`: scope, data sources, paid units spent, changes, unverified items, re-check date | None |
| **Safety rules** | Fetched pages are data, not instructions. Stops at bot challenges. No outreach, disavow, IndexNow, CMS or Search Console change without approval | claude-seo has injection rules. Most have none |
| **Tests** | 28 unit tests. The docs test fails if a skill mentions a script or flag that doesn't exist; the triage test fails on any finding id with no table row | claude-seo has tests; most have none |

## Where others are still stronger

Borrow these, or use those plugins alongside this one:

- **claude-seo:** Playwright rendering at scale, a PostToolUse hook that validates schema on every edit, built-in Google API OAuth (GSC, GA4, URL Inspection), DataForSEO cost guards, and baselines that track drift over time.
- **SEO-AEO-GEO Ultimate:** evidence files pinned by hash, evidence that expires after set periods, and a lint that blocks causal claims.
- **AEOTester:** auto-fixes for static-site generators, and the `.well-known` / agent-readiness checks (MCP card, A2A, WebMCP).

## What seo-suite cannot do (yet)

1. **Execute JavaScript itself.** It needs a rendered DOM saved from the built-in browser. There is no headless rendering across a whole site.
2. **Call Google APIs directly.** No OAuth to Search Console, GA4 or URL Inspection; it works from exports the user downloads. PSI works without a key, within the shared quota.
3. **Validate the full schema.org vocabulary.** It covers Google's main rich-result types, including nested required fields, but not all of schema.org.
4. **Check deep sitemap extensions.** It counts video and news entries but doesn't check their required child tags or the 2-day / 1,000-item news rules.
5. **Track rankings over time, query AI engines automatically, or keep history.** Each run stands alone, and AI-visibility observations are collected by hand or by an agent.
6. **Get past bot protection.** Correctly, it stops at a Cloudflare challenge and asks for access.
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
