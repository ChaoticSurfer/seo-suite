---
name: seo-analytics
description: Search performance analysis and reporting. Use for traffic drops, Google update impact, Search Console quick wins (striking distance, low CTR, cannibalisation), server logs, rank tracking and snapshots, dashboards, and whether an SEO change worked. Not for crawling for defects (seo-technical, seo-audit) or keyword discovery (seo-keywords).
---

# Analytics: measure, diagnose, report

Turn first-party data (Search Console, Bing Webmaster, GA4, server logs) into decisions. Diagnose drops with
a fixed decision tree instead of guessing, and measure changes honestly.

## When to use / not

Use it for:
- Search Console, Bing Webmaster and GA4 exports.
- Traffic drops and algorithm-update questions.
- CTR optimisation targets.
- Cannibalisation.
- Crawl-log analysis.
- KPI dashboards.
- Before/after tests.

Not for:
- Finding on-site defects → seo-technical, seo-audit. This skill *calls* them when the drop tree points there.
- Keyword ideas for new pages → seo-keywords.
- Competitor visibility → seo-competitors.

## Inputs: decide, don't ask

Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Search Console Performance export(s). UI export: `Queries.csv` / `Pages.csv` (top 1,000 rows only). API or Looker Studio export with query+page rows: needed for cannibalisation. API limit: 25k rows/request, ~50k rows/day/type (google-rules §11) | The Search Console API through `claude_seo.py gsc-export` (below) once the user has signed in; else exports in `seo-work/`, or Search Console in the browser while the user is signed in | **Ask — batched at the end** for the one-time sign-in, or for exports. Carry on with the drop tree's technical, update-date and SERP branches, plus logs if present |
| Comparison windows | Choose them yourself: **two windows of equal length, aligned on weekdays**, with the last 2–3 days excluded (GSC data lags) | The last 28 days vs the previous 28, plus YoY when 16 months exist |
| Brand regex: brand name plus misspellings (example below) | Site name, Organization schema, domain, and the brand variants in GSC queries, in every alphabet the brand is written in | The domain name without the TLD |
| Optional: Bing Webmaster export (same shape; works with gsc_analyze), GA4 organic landing-page report, server access logs (`.log` / `.gz`) | A connector, or files in the project or `seo-work/` | **Ask — batched at the end**, saying what each adds |
| The dates of site changes, deploys and migrations | Git history, `SEO-WORKLOG.md`, sitemap `lastmod` | "None found", noted |
| For drops: when it started, which section/country/device, and whether conversions dropped too | The GSC daily series and its page/country/device dimensions; GA4 conversions | Conversions `[needs data]` without GA4 |

Brand regex example: `acme|acme ?corp|აკმე`.

## Workflow

**Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`):

```bash
mkdir -p seo-work
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export keywords --format csv > seo-work/store-keywords.csv
```

- `datasets.gsc` gives the age of the newest GSC data per locale (TTL 7 days). Fresh: reuse the export it came from, the newest GSC file in `seo-work/`, instead of asking for another. Stale or missing: pull it from the API (below), or ask for a new export, as in Inputs.
- The store keeps per-query totals, not daily rows, so A–D still run on the export files.
- The keywords' `cluster_id` and `target_url` give the cluster grouping for C and the primary page for the cannibalisation decisions in A6.
- No store yet (`status` exits with "no research store here"): create it with `init --site URL --locales …` (research-store §9).

**Search Console through the API.** `claude_seo.py` runs claude-seo's Search Console client (installed on first use) and writes the rows as the same CSV a UI export gives, so every step below reads it unchanged. Always name the property: claude-seo's default property can belong to another site. Set the dates yourself, as in Inputs:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/claude_seo.py" gsc-export --property sc-domain:example.com --start-date 2026-09-22 --end-date 2026-10-19 --dimensions query,page -o seo-work/query_page.csv > seo-work/gsc-export.json
```

- Add `--country GEO --device mobile` for a market's rows, and `--dimensions query` or `page` for a Queries- or Pages-shaped file.
- Sitemaps and their errors: `claude_seo.py run gsc_query.py sitemaps --property sc-domain:example.com --json`. Index verdicts per URL: seo-technical step 1.
- Exit 1 with no sign-in: add the one-time sign-in to the questions batched at the end (INTEGRATIONS.md, Search Console). It asks only for `webmasters.readonly`, never the Indexing API.
- GA4 stays on Google's `analytics-mcp` server.

### A. Opportunity analysis (GSC/Bing export)

1. Run the analysis:

   ```bash
   mkdir -p seo-work
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gsc_analyze.py" Queries.csv --brand "brand|brnd" --min-impressions 50 > seo-work/gsc.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gsc_analyze.py" query_page.csv --brand "brand" > seo-work/gsc-qp.json   # cannibalisation
   ```

   Flags: `--striking-from 4 --striking-to 20` (defaults); raise `--min-impressions` on big sites.

2. Read `striking_distance` (positions 4–20, sorted by `est_extra_clicks_at_pos3` `[estimate]`). These are the pages to improve first. Hand each to seo-onpage / seo-content with its query.

3. Read `ctr_underperformers`. Top-10 queries whose CTR is below half of **this site's own** median CTR for that position (`ctr_curve_used`; it falls back to defaults when there is too little data).
   - Causes: weak title/snippet, a SERP feature or AI Overview above the result, or an intent mismatch.
   - Inspect the live SERP with WebSearch before rewriting.

4. `question_queries`: material for FAQ sections and answer-first passages (seo-content, seo-ai-search).

5. `brand_split`: report non-branded clicks separately. Branded demand is not SEO performance.

6. `cannibalization`: a query where 2+ pages each take ≥10% of impressions. Decide per case: merge + 301, differentiate the intent, or point internal links at the primary page. Not every split is a problem: if both pages rank well, leave them.

### B. Period comparison and traffic-drop diagnosis

1. Run the comparison:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gsc_analyze.py" last_28d.csv --compare prev_28d.csv > seo-work/gsc-compare.json
   ```

   Each loser gets a `likely_cause`:
   - "rankings dropped"
   - "fewer impressions at similar rank" (demand, or a SERP feature)
   - "CTR fell at similar rank"

   These are heuristics: phrase them as "consistent with".

2. Walk the **drop tree in order** and stop at the first branch the evidence supports. Record the evidence for each branch:
   1. **Is the drop real?**
      - GSC clicks vs GA4 organic sessions: compare trend direction, not levels. The totals won't match exactly (attribution, consent, non-HTML files, time zones); Google only says the general trends should be similar (google-rules §11) [Google doc].
      - A drop in GA4 only → tracking/consent/tag issue, not SEO.
      - Check year-over-year to rule out seasonality.
   2. **Technical.** Run in parallel:
      - `robots_check.py`
      - `sitemap_check.py`
      - `page_audit.py` on the top losing URLs
      - `crawl.py` on the affected section

      Look for:
      - noindex, canonical changes, 5xx/429, robots blocks, redirect changes, a bot challenge (`bot-challenge`).
      - Deploys on the drop date.
      - The Search Console Page indexing report for jumps in "Excluded" (seo-technical).
   3. **Algorithm update.** Compare the drop date with the Google Search Status Dashboard (`https://status.search.google.com/` → ranking incidents; fetch it). Shape matters:
      - A site-wide step change on an update date coincides with a systems re-evaluation (core / spam; the helpful content system was folded into core in March 2024, so "helpful content update" only applies to drops before then). See google-rules §4.
      - Section-specific changes point to page-level issues.
      - Never say "penalised" unless Search Console shows a **manual action**.
   4. **Seasonality / demand.** YoY in GSC (16 months of data; google-rules §11), plus Google Trends for the head terms. Impressions down at a stable position = demand.
   5. **SERP displacement.** Position stable but CTR down. WebSearch the queries:
      - AI Overview present? New features (video, PAA, shopping, forums)? Ads?
      - Is the Search Console "Search generative AI performance" report available? (google-rules §10)
   6. **Competitors.** Position lost to specific URLs → seo-competitors (compare_pages on the winners). Check the Wayback CDX for when their page changed.
3. Use log data when available:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/log_analyze.py" access.log access.log.1.gz --verify-dns --sitemap-urls seo-work/urls.txt > seo-work/logs.json
   ```

   Look for:
   - Googlebot hits per day collapsing (crawl capacity issue: 5xx/429 or a slow server; google-rules §1).
   - Errors served to bots.
   - Parameter-URL share (crawl waste).
   - Sitemap paths never crawled.
   - Fake "Googlebot" IPs (`unverified_ips`: the reverse DNS name is missing or outside Google's domains, or doesn't resolve back to the IP). `unverifiable_ips` are IPs where the forward lookup failed or the log's host field isn't an IP; they aren't proof of a fake. Check them against Google's published IP ranges before blocking.
   - Whether AI bots (OAI-SearchBot, Claude-SearchBot, PerplexityBot) reach the site at all.

### C. Reporting and dashboards

- **KPIs.** Separate leading from lagging:
  - Leading: indexed pages (GSC), impressions, avg position for target clusters, CWV pass rate, crawl errors.
  - Lagging: non-branded clicks, organic conversions/revenue (GA4), AI-citation rate (seo-ai-search).
- **Free dashboard:** Looker Studio with the native Search Console connector (Site + URL impression tables) and the GA4 connector. Pages:
  - Overview.
  - Non-branded trend (regex filter).
  - Clusters (URL-path grouping).
  - Opportunities (positions 4–20).
  - CWV (the CrUX connector, or psi.py snapshots).
- **Monthly report:** what changed, why (evidence-tagged), what we did (from SEO-WORKLOG.md), what's next.

### D. Measuring whether an SEO change worked: iterate on evidence

1. **Baseline.** Before the change, export Search Console Pages (or query+page) for the last 28 days. If snapshots run, keep the latest snapshot of the affected keyword set.
2. **Log the change** in `SEO-WORKLOG.md`, pre-registered:
   - The changed URLs, also saved one per line in `seo-work/changes/<date>-changed.txt`.
   - **Control URLs:** similar pages left unchanged, in a `--controls` file. Without one, every other page is a control.
   - The metric: clicks and impressions decide; position explains.
   - The expected direction.
   - The check dates: +14 and +28 days after Google re-crawled the pages (URL Inspection).
3. **Compare at +14 and +28 days,** with equal windows aligned on weekdays and the last 2–3 days left out:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rank_compare.py" gsc baseline.csv plus14.csv plus28.csv --changed seo-work/changes/2026-10-01-changed.txt > seo-work/change-impact.json
   ```

   With snapshots, `rank_compare.py snapshots` with the same `--changed` file also compares the positions the changed keywords gained against the control keywords.

   If a Google core update rolled out between the baseline and a check window (Search Status Dashboard), don't decide on that window: controls don't absorb an update's uneven effect. Move the check to a full week after the rollout ends, with a new baseline if the update began after the change.
4. **Decide on clicks and impressions.** `change_impact.verdict` is the changed pages' change minus the controls', from the first file to the last:
   - "ahead of controls" (clicks 10+ points ahead, impressions not behind): keep the change and apply the pattern to similar pages.
   - "behind controls" (clicks 10+ points behind): revert it, or try the next variant.
   - "no clear difference": keep a quality fix; otherwise try the next variant.
   - "inconclusive" (fewer than 50 clicks before, or a group with no pages): wait for more data, or widen the test to more pages.

   The margins are judgement, not a Google rule (`thresholds` in the output). Report "coincides with", never "caused".
5. **Log the decision** and the next check date, then start again at step 1 with the next change.

### Rank tracking

Two sources, kept apart: show them side by side and never average them.
- **Search Console, free, own site only:** the topmost position averaged over impressions, across every location and device, 2–3 days behind. It is the default at every budget.
- **Snapshots, paid:** `rank_snapshot.py` buys DataForSEO Google Organic SERPs in the Standard queue under fixed conditions: one location, language and device per keyword set, depth 20 by default. One snapshot gives our position, every competitor's position, share of voice, visibility and the domains an AI Overview cites [vendor data]. seo-suite never queries google.com itself.

1. **Keyword set.** Write `seo-work/rank/<market>-<lang>-<device>.json` in the format of `rank_snapshot.py`'s docstring: the money keywords and a sample of the mid tier, volumes from the research store, the competitors from seo-competitors, and a version. Georgia is location 2268 (Tbilisi 1007469, Batumi 1007466); 21143 is the US state, which the script refuses. A change to the keywords or the conditions needs a new version.
2. **The free default** (budgets 0):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rank_snapshot.py" gsc seo-work/rank/ge-ka-mobile.json Queries.csv > seo-work/rank/gsc-positions.json
   ```

   It gives the set's own Search Console position, clicks and impressions per keyword, and `paid_adds`: what a snapshot would add and what one run costs. Report both.
3. **A paid snapshot** (`dataforseo_monthly_usd` above 0):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rank_snapshot.py" run seo-work/rank/ge-ka-mobile.json --out-dir seo-work/rank --gsc Queries.csv
   ```

   - With `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` in the environment (read from the Keychain at launch, never written in a file; seo-automation step A3), `run` posts up to 100 tasks a call, polls the free `tasks_ready`, fetches each result free and writes the snapshot. It checks the budget and the credit guard's ledger first, records the spend there, and refuses to post or snapshot one set twice on one day: a set already posted today ends with its free `--resume` command.
   - Without them, `rank_snapshot.py plan` prints the `task_post` bodies for the DataForSEO connector's `api_request`, where the credit guard prices each call. `rank_snapshot.py parse` then turns the saved `task_get/advanced` answers into the same snapshot.
   - If the queue takes longer than `--wait-minutes`, the run ends with a `--resume` command. Resuming fetches the posted tasks free; results stay 30 days.
   - `--gsc` fits the CTR curve behind share of voice and visibility from the site's own export for the same country and device. Fit it once per keyword-set version: save that export as `seo-work/rank/<version>-ctr.csv` and pass the same file to every run of the version. A new export changes share of voice and visibility even when no position moved. Refit quarterly, with a new version.
   - Cadence: the money tier daily, the full set weekly, and every keyword daily during a migration or a Google core update.
4. **Write the SERPs back** with the command in the output's `next` field: `research_store.py ingest serps <snapshot>.serps.json --locale ka --details <snapshot>.details.json --as-of <date>`.
5. **Alerts** over the last three snapshots of one set:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rank_compare.py" snapshots seo-work/rank/ge-ka-mobile-v1-2026-10-11.snapshot.json seo-work/rank/ge-ka-mobile-v1-2026-10-18.snapshot.json seo-work/rank/ge-ka-mobile-v1-2026-10-25.snapshot.json
   ```

   - It flags a move of 3+ positions held for 2 runs, entering or leaving the top 3 or top 10, and an AI Overview citation gained or lost.
   - A move seen once is `pending`: re-check it on the next run before acting on it.
   - The thresholds are judgement, not a Google rule. Hold alerts while a Google update rolls out (Search Status Dashboard), and compare only a full week after it ends.

### E. Write back to the research store

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest gsc query_page.csv --as-of "$PERIOD_END"
```

- Ingest the most complete export of the current period only: `last_28d.csv` in B, `after.csv` in D. A query+page CSV gives every row; a `gsc_analyze.py` JSON gives only its top lists. A Queries.csv without pages needs `--locale` when the store has more than one locale.
- Set `--as-of` to the last day that export covers (`$PERIOD_END`). Without it the store dates a file by its modification time, so a comparison file saved later would replace the current values (research-store §3).
- Never ingest the `--compare` file (`prev_28d.csv`, `before.csv`) unless you give it its own `--as-of`.
- Read the new queries for people's names before the store is committed (research-store §1).
- A cannibalisation decision that names the primary page of a stored cluster: `set-status --cluster ID --status published --url PRIMARY_URL`.

## Checks

| Check | Rule | Source |
|---|---|---|
| Comparison windows equal length, weekday-aligned, last 2–3 days excluded | GSC data lags 2–3 days | google-rules §11 [Google doc] |
| GSC retention | 16 months | google-rules §11 [Google doc] |
| "Penalty" claims | only with a Manual actions report entry | google-rules §4 [Google doc] |
| AI Overviews/AI Mode traffic | counted inside Performance → Web; no separate clicks | google-rules §10 [Google doc] |
| Googlebot crawl rate drop | coincides with 5xx/429/slow responses | google-rules §1 [Google doc] |
| CTR expectations | site's own curve first; defaults are heuristic | heuristic |
| Cannibalisation threshold | ≥2 pages ≥10% impressions, ≥100 impressions | heuristic |
| Rank alerts | a move of 3+ positions held for 2 runs; entering or leaving the top 3 or top 10; AI Overview citation gained or lost | judgement |
| Snapshot rank vs Search Console position | side by side, never averaged: one is a fixed-condition check, the other an average over impressions | judgement |

## Data: free vs paid

**Free covers almost everything here.** Search Console (+API), Bing Webmaster (+ its AI Performance report, if available; google-rules §10), GA4, Looker Studio, server logs, the Google Search Status Dashboard, Google Trends.

**Paid adds** (see `${CLAUDE_PLUGIN_ROOT}/references/tools-paid.md`):
- **Semrush / Ahrefs.**
  - *Competitor* visibility history and keyword movement (your own data is better in GSC).
  - Their algorithm-volatility sensors (Semrush Sensor) to see whether a drop is industry-wide.
  - Justified for the "is it just us?" question during an update.
  - Cost tactic: check the free Sensor page and a single competitor's Organic Research history instead of a full project.
- **Rank snapshots** (`rank_snapshot.py`, DataForSEO Standard queue, from `dataforseo_monthly_usd`): $0.0006 per 10 results a keyword, plus one base price for the AI Overview. 50 money keywords daily at depth 10 is about $0.03 a day; 450 keywords weekly at depth 20 about $0.54 a run; about $3.20 a month per market and language, plus $0.90 for AI Overviews on the money tier. What free can't give: a fixed-condition rank for keywords with no impressions yet, every competitor's position and share of voice, and AI Overview citations.
- **Rank trackers** (Semrush Position Tracking, Ahrefs Rank Tracker, SE Ranking): only when stakeholders already read them. Track only money keywords and the locations and devices that matter. Most tools bill per keyword × location × device × frequency, so prefer weekly over daily for non-volatile sets.
- **Screaming Frog Log File Analyser** (`## Screaming Frog`). Useful if logs are huge and the user prefers a GUI. `log_analyze.py` covers the core questions free.

Label third-party traffic numbers `[vendor data]` / `[estimate]`. They are modelled, not measured.

## Output

1. `seo-work/gsc.json` and friends, plus a short findings summary:
   - Top 10 striking-distance opportunities: query, page, est. extra clicks `[estimate]`.
   - Top CTR fixes.
   - Cannibalisation decisions.
2. Drop diagnosis: the tree with ✅/❌ and evidence per branch, the most likely explanation in "consistent with" language, and next actions routed to the right skill.
3. A KPI/dashboard spec (Looker Studio data sources, fields, filters) or the monthly report.
4. Experiment record (pre-registration, the `change_impact` result at +14 and +28 days, and the decision).
5. Rank report: Search Console positions beside snapshot positions per keyword, share of voice and visibility against the competitors, AI Overview citations, and the alerts with the pending moves to re-check.
6. **Assumptions:** the windows, brand regex, data sources and change dates you decided, each with its evidence, and which store data was reused and how old it was (e.g. "GSC: store data 5 days old, its export reused"). Then the questions batched for the user (missing exports or access, a budget stop), each with a recommendation.

## Pitfalls & myths

- **Average position** is impression-weighted across all queries/locations. A new page-2 ranking can *lower* the average while traffic rises.
- **UI exports cap at 1,000 rows** and hide anonymised queries, so totals won't match the chart.
- **A drop on an update date is not proof the update caused it.** Rule out technical and tracking causes first.
- **YoY beats MoM** for seasonal businesses.
- **Clicks falling while impressions hold** is often AI Overviews or another SERP feature, not a ranking loss.
- **GA4 "organic"** depends on consent mode and channel grouping, so check config changes on the drop date.
- **Don't optimise CTR with clickbait titles.** Google may rewrite them (google-rules §3).

## Log the work

Append to `SEO-WORKLOG.md` (`${CLAUDE_PLUGIN_ROOT}/references/worklog.md`):
- Exports used (date ranges).
- Store data reused (with its age) and the GSC export ingested.
- Scripts run.
- Findings with evidence tags.
- Diagnosis verdict.
- Pre-registered experiments, their `change_impact` verdicts and the decisions.
- Keyword-set versions and snapshot files.
- Paid-tool usage, with the spend `rank_snapshot.py` recorded.
- The date to re-check (e.g. "re-pull GSC on 2026-11-21 for the title test").
