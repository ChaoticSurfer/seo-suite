---
name: seo-strategy
description: SEO strategy, roadmap and budgeting. Use for "build an SEO strategy", "SEO plan for next quarter", "where should we focus SEO", "is SEO worth it for us", "how much traffic could we get", "SEO roadmap", "topical authority plan", "site architecture for SEO", "what SEO tools should we buy", "SEO budget", "SEO KPIs / OKRs", "prioritise our SEO backlog", "SEO for a new website / launch". Turns business goals into KPIs, honest opportunity ranges, a topical map, architecture, a quarterly P0–P3 roadmap (from triage.py), resourcing, a tool stack per budget tier and a risk register. Not for running the audit itself (seo-audit / seo-technical), keyword discovery (seo-keywords), or one-off page fixes (seo-onpage).
---

# Strategy: from business goal to a quarterly SEO plan

Decide **what** to do in SEO, **in what order**, **with what budget**, and **how we'll know it worked**.
Every number is a range with its evidence tag. Every priority comes from data (triage, GSC, SERPs), not taste.

## When to use / not

Use it for:
- New strategies and quarterly planning.
- Choosing a market or topic focus.
- Budget and tool decisions.
- KPI design.
- Pre-launch planning.
- Re-prioritising a backlog.

Not for:
- Executing audits → seo-audit / seo-technical.
- Building keyword lists → seo-keywords.
- Writing content → seo-content.
- Links → seo-links.

This skill orchestrates those and consumes their outputs.

## Inputs to gather

Ask; never assume:

- **Business model:**
  - What a conversion is (lead / sale / signup / booking) and its value.
  - Target customers and markets (countries/languages).
  - Seasonality.
- **Current state:**
  - Site, CMS/framework.
  - GSC access (16 months of data).
  - GA4.
  - Past SEO work.
  - Known penalties/migrations.
- **Constraints:**
  - Team: writers, devs, hours per week.
  - Budget for tools and content.
  - Deadline.
  - Brand/legal limits (YMYL: health, finance, legal → higher E-E-A-T bar; google-rules §4).
- **Competitors** the business cares about.

## Workflow

1. **Baseline.** These are independent, so run them in parallel:
   - `seo-site-auditor` agent on the site: robots, sitemap, crawl, psi, triage → `seo-work/triage.json`.
   - seo-analytics on GSC exports: non-branded clicks, top clusters, striking distance, YoY trend.
   - seo-competitors on 20–50 core keywords: who wins and with which page types.
   - seo-ai-search quick check: AI crawler access (robots matrix) and a small AI-visibility sample.
2. **Goals → KPIs.** For each business goal:
   - One lagging KPI: non-branded organic conversions/revenue, or non-branded clicks to money pages.
   - 2–3 leading KPIs:
     - Indexed money pages.
     - Impressions/positions for target clusters.
     - CWV pass rate.
     - Referring domains from relevant sites.
     - AI citation rate on a frozen query set.

   Set baselines from measured data and targets as ranges.
3. **Opportunity sizing** (honest ranges):
   - **With GSC data:** impressions for target queries × the CTR gain from moving to a target position. gsc_analyze's `est_extra_clicks_at_pos3` gives a per-query `[estimate]`. Sum for an upper bound; use 30–50% of it as a realistic case (heuristic).
   - **For new topics:** volume is `[needs data]` without Keyword Planner (active Ads spend for exact numbers) or a paid tool. Give relative demand (autocomplete presence, Google Trends) or vendor volumes tagged `[vendor data]`.
   - Convert to conversions with the site's own organic conversion rate (GA4).
   - Never promise rankings or dates.
4. **Topical map and architecture:**
   - Take clusters from seo-keywords (one primary page per intent cluster).
   - Group them into pillars matching business offerings.
   - Map each cluster to an existing URL (optimise), a new URL (create), or a merge (consolidate).
   - Architecture rules:
     - Money pages ≤3 clicks deep (heuristic).
     - URL folders mirror pillars.
     - Breadcrumbs.
     - Hub pages link to every cluster page (seo-links).
     - One URL per intent (avoid cannibalisation).
     - International: subfolder/ccTLD with hreflang (google-rules §6).
5. **Prioritise.**
   - Merge into one backlog:
     - Technical items from `triage.py` (already P0–P3 by lookup).
     - Content items, scored by opportunity (striking distance first, then gaps, then new clusters).
     - Link items.
   - Ordering rule:
     - P0 technical blockers before anything else (nothing ranks if it can't be indexed).
     - Then quick wins: striking distance, CTR fixes, internal links to money pages.
     - Then compounding work: new clusters, digital PR.
   - Effort comes from the user's real capacity.
6. **Quarterly roadmap:**
   - 12 weeks.
   - Each line: owner, effort, KPI it moves, done-definition.
   - Weeks 1–2: P0/P1 fixes + measurement setup (Looker Studio, worklog, pre-registered tests).
   - Weeks 3–8: striking-distance optimisation + 1 pillar.
   - Weeks 9–12: next pillar + a link/PR asset.
   - Review at week 6 and week 12.
7. **Tool stack and budget.** Pick the tier that matches the budget (details and current prices: `${CLAUDE_PLUGIN_ROOT}/references/tools.md`):
   - **$0/mo:**
     - Search Console + Bing Webmaster + GA4 + Looker Studio.
     - The seo-suite scripts (crawl, audit, PSI/CrUX, autocomplete keywords, logs).
     - Ahrefs Webmaster Tools (own-site backlinks + site audit).
     - Screaming Frog free (500 URLs) if a GUI is wanted.
     - Google Trends, Keyword Planner (ranges).

     Enough for most small sites: the limits are competitor data and exact volumes.
   - **~$150/mo:**
     - ONE all-in-one suite at its entry tier: **Semrush** *or* **Ahrefs**, never both.
     - Pick Semrush if keyword research, local/position tracking and content tools matter most. Pick Ahrefs if links and competitor top pages matter most.
     - Plus a Screaming Frog licence if the site is >500 URLs.
     - Justification: competitor keyword lists, keyword difficulty/volume, backlink gap. Things free tools cannot see.
   - **~$500+/mo:**
     - The suite's higher tier (more projects, history, API access), or DataForSEO pay-as-you-go for scripted SERP/volume/backlink pulls.
     - An AI-visibility tracker if AI answers are a key channel.
     - Optionally Similarweb for market sizing.
     - Justify each line by the decision it enables. Cancel anything not used monthly.
8. **Risk register.** Per risk: likelihood, impact, mitigation, early-warning metric.
   - Core/spam updates (diversify; quality first; monitor the Status Dashboard).
   - AI Overviews/AI Mode lowering CTR on informational queries (target commercial/transactional intents, earn citations, track impressions vs clicks).
   - Site migrations/redesigns (seo-migration checklist; google-rules §9).
   - Bot protection blocking crawlers (`bot-challenge`).
   - Scaled/AI content risk (google-rules §4).
   - Dependency on one page/keyword.
   - Tracking/consent breakage.
9. **Cadence.**
   - Weekly: worklog + GSC anomaly glance.
   - Monthly: KPI report (seo-analytics).
   - Quarterly: re-baseline (crawl + triage + competitor SERPs + AI visibility), refresh the roadmap.
   - After each confirmed core update: a drop/gain review.

## Checks

| Check | Rule | Source |
|---|---|---|
| Plan respects spam policies | no scaled low-value content, link schemes, doorway pages, site reputation abuse | google-rules §4 [Google doc] |
| People-first | content made for the audience, not search engines; no word-count targets | google-rules §4 [Google doc] |
| YMYL topics | higher trust bar: real authors, sources, reviews | google-rules §4 [Google doc] |
| Technical eligibility first | crawlable, 200, indexable | google-rules §1 [Google doc] |
| AI search | no special "AI optimisation" needed beyond SEO; llms.txt not used by Google | google-rules §10 [Google doc] |
| One URL per intent | avoids cannibalisation | heuristic |
| Forecasts | ranges + evidence tags; no guaranteed rankings | heuristic |

## Data: free vs paid

The free path: GSC/Bing/GA4 + seo-suite scripts + WebSearch SERPs + Trends + Keyword Planner ranges. It is enough to build a defensible plan for your own site.

Paid tools add:
- **Market-level demand:** keyword volumes, difficulty.
- **Competitor keyword/backlink inventories.**
- **Exact local SERPs.**

Buy them when the plan depends on *competitor* or *market* data. See the tier list above and `tools.md` `## Cost-optimisation playbook`:
- Monthly billing during the research phase, then downgrade.
- One seat.
- Scheduled exports instead of ad-hoc pulls.
- Caching exports in `seo-work/`.

## Output

`SEO-STRATEGY.md` (or a shared doc if the user prefers), containing:

1. Goals, KPIs, baselines `[measured]`, target ranges.
2. Opportunity sizing with method and evidence tags.
3. Topical map (pillar → clusters → URL action) and architecture diagram (Mermaid).
4. Prioritised backlog (P0–P3 + content + links) and the 12-week roadmap table.
5. Tool stack and monthly budget with a justification per paid line.
6. Risk register and review cadence.
7. Open questions / `[needs data]` items.

## Pitfalls & myths

- **"SEO in 30 days."** Most changes need weeks to be crawled and re-evaluated. Set expectations in quarters.
- **Strategy without baselines** can't be evaluated. Measure first.
- **Chasing head terms only** ignores striking-distance wins that pay off in weeks.
- **Buying every tool.** One suite well used beats three unused, and tools don't fix sites.
- **Content volume as a KPI** ("40 posts/month") invites scaled-content problems. Measure outcomes.
- **Treating AI search as separate magic.** Google says AEO/GEO is SEO (google-rules §10). Allow answer-engine crawlers, be citable, measure.

## Log the work

Append to `SEO-WORKLOG.md` (`${CLAUDE_PLUGIN_ROOT}/references/worklog.md`):
- Strategy version and date.
- Inputs and baselines (file paths).
- Decisions and their reasons.
- Chosen tool tier and cost.
- The next review date.
