---
name: seo-analytics
description: Search performance analysis, traffic-drop diagnosis and SEO reporting. Use for "why did our traffic drop", "organic traffic fell", "lost rankings", "analyse my Search Console export", "find quick wins in GSC", "striking distance keywords", "low CTR pages", "keyword cannibalisation", "compare this month vs last", "branded vs non-branded", "did the Google update hit us", "analyse server logs / Googlebot crawl", "build an SEO dashboard / KPI report", "did my SEO change work", "rank tracking". Uses gsc_analyze.py, log_analyze.py and Looker Studio (free); explains when Semrush/Ahrefs rank tracking is worth paying for. Not for crawling the site for defects (seo-technical / seo-audit), keyword discovery for new content (seo-keywords), or competitor research (seo-competitors).
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
| Search Console Performance export(s). UI export: `Queries.csv` / `Pages.csv` (top 1,000 rows only). API or Looker Studio export with query+page rows: needed for cannibalisation. API limit: 25k rows/request, ~50k rows/day/type (google-rules §11) | A connector or the API, or exports in `seo-work/` | **Ask — batched at the end.** Carry on with the drop tree's technical, update-date and SERP branches, plus logs if present |
| Comparison windows | Choose them yourself: **two windows of equal length, aligned on weekdays**, with the last 2–3 days excluded (GSC data lags) | The last 28 days vs the previous 28, plus YoY when 16 months exist |
| Brand regex: brand name plus misspellings (example below) | Site name, Organization schema, domain, and the brand variants in GSC queries, in every alphabet the brand is written in | The domain name without the TLD |
| Optional: Bing Webmaster export (same shape; works with gsc_analyze), GA4 organic landing-page report, server access logs (`.log` / `.gz`) | A connector, or files in the project or `seo-work/` | **Ask — batched at the end**, saying what each adds |
| The dates of site changes, deploys and migrations | Git history, `SEO-WORKLOG.md`, sitemap `lastmod` | "None found", noted |
| For drops: when it started, which section/country/device, and whether conversions dropped too | The GSC daily series and its page/country/device dimensions; GA4 conversions | Conversions `[needs data]` without GA4 |

Brand regex example: `acme|acme ?corp|აკმე`.

## Workflow

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

### D. Measuring whether an SEO change worked

1. **Pre-register.** Before the change, write down in the worklog:
   - Changed URLs.
   - **Control URLs** (similar, unchanged).
   - Metric (clicks/impressions/CTR/position for the target queries).
   - Expected direction.
   - Window: ≥4 weeks after indexing; check the re-crawl date in URL Inspection.
2. Export equal windows before and after for both groups, then run `gsc_analyze.py after.csv --compare before.csv` for each group.
3. Report the treatment change *minus* the control change. With few pages or low clicks, say "inconclusive". Never claim causation from a single before/after.

### Rank tracking

- **Free:** Search Console average position per query (impression-weighted, all locations). Fine for trends; not a "where am I right now" view.
- **Paid:** daily positions for a fixed keyword list, by location/device, with SERP features. Justify it when:
  - local or multi-city ranks matter,
  - the client contract needs rank reports, or
  - you must track keywords with no impressions yet.

  Options: Semrush Position Tracking, Ahrefs Rank Tracker, SE Ranking, or the DataForSEO SERP API for scripted checks (tools.md).

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

## Data: free vs paid

**Free covers almost everything here.** Search Console (+API), Bing Webmaster (+ its AI Performance report, if available; google-rules §10), GA4, Looker Studio, server logs, the Google Search Status Dashboard, Google Trends.

**Paid adds** (see `${CLAUDE_PLUGIN_ROOT}/references/tools.md`):
- **Semrush / Ahrefs.**
  - *Competitor* visibility history and keyword movement (your own data is better in GSC).
  - Their algorithm-volatility sensors (Semrush Sensor) to see whether a drop is industry-wide.
  - Justified for the "is it just us?" question during an update.
  - Cost tactic: check the free Sensor page and a single competitor's Organic Research history instead of a full project.
- **Rank trackers:** see above. Track only money keywords and limit locations/devices to the ones that matter. Most tools bill per keyword × location × device × frequency, so prefer weekly over daily for non-volatile sets.
- **Screaming Frog Log File Analyser** (`## Screaming Frog`). Useful if logs are huge and the user prefers a GUI. `log_analyze.py` covers the core questions free.

Label third-party traffic numbers `[vendor data]` / `[estimate]`. They are modelled, not measured.

## Output

1. `seo-work/gsc.json` and friends, plus a short findings summary:
   - Top 10 striking-distance opportunities: query, page, est. extra clicks `[estimate]`.
   - Top CTR fixes.
   - Cannibalisation decisions.
2. Drop diagnosis: the tree with ✅/❌ and evidence per branch, the most likely explanation in "consistent with" language, and next actions routed to the right skill.
3. A KPI/dashboard spec (Looker Studio data sources, fields, filters) or a monthly report draft.
4. Experiment record (pre-registration + result).
5. **Assumptions:** the windows, brand regex, data sources and change dates you decided, each with its evidence. Then the questions batched for the user (missing exports or access), each with a recommendation.

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
- Scripts run.
- Findings with evidence tags.
- Diagnosis verdict.
- Pre-registered experiments.
- Paid-tool usage.
- The date to re-check (e.g. "re-pull GSC on 2026-11-21 for the title test").
