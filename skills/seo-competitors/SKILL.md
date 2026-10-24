---
name: seo-competitors
description: Competitor and SERP analysis. Use for "who are my SEO competitors", "why does X outrank me", "compare my page with the top results", "competitor content gap", "keyword gap vs competitors", "what is ranking for <keyword>", "SERP features for <keyword>", "competitor backlinks", "how much traffic does competitor get", "what did competitor change on their page", "monitor competitor sites". Finds real SERP competitors (not just business rivals), compares pages with compare_pages.py, inventories SERP features and intent, tracks competitor page changes via the Wayback Machine, and states exactly when Semrush/Ahrefs/Similarweb are worth paying for. Not for keyword discovery from seeds (seo-keywords), link building execution (seo-links), or your own traffic analysis (seo-analytics).
---

# Competitors: who actually wins the SERP, and why

Find the domains and pages that rank for *your* target queries, measure how they differ from yours, and
turn the differences into concrete fixes, without inventing traffic or authority numbers.

## When to use / not

Use it for:
- SERP competitor identification.
- Page-vs-page comparison.
- SERP-feature and intent analysis.
- Content/keyword gaps.
- Backlink gaps (paid).
- Traffic estimates (paid, labelled).
- Change monitoring.

Not for:
- Generating keyword lists from seeds → seo-keywords.
- Doing the outreach → seo-links.
- Your own GSC performance → seo-analytics.

## Inputs to gather

- **Your domain**, and the target keyword set (10–100). Pull it from seo-keywords output or the GSC striking-distance list, or ask.
- **Market:** country + language (`--gl`/`--hl` equivalents for searches), device focus.
- **Business rivals** the user already knows. Useful, but verify them against the SERP.
- **Optional:** paid tool access (Semrush/Ahrefs/Similarweb) and any credit budget.

## Workflow

1. **Collect SERPs (parallel).**
   - Split the keyword set into batches of ~10 and launch one `seo-serp-researcher` agent per batch, in parallel.
   - Each returns, per keyword: top-10 organic URLs, page type (guide / category / product / tool / forum / video / local pack), SERP features (AI Overview, featured snippet, PAA, video, images, shopping, local pack, forums/"Discussions"), and dominant intent.
   - WebSearch results approximate the SERP; they are not a personalised, location-exact Google SERP. Tag them `[measured: WebSearch sample]`.
2. **Identify SERP competitors.**
   - Count domain appearances across all keywords. The top 5–10 domains by share of top-10 slots are your real competitors.
   - Separate:
     - Direct business competitors.
     - Content publishers/aggregators.
     - Marketplaces/UGC (Reddit, YouTube, Wikipedia).
   - You compete with the publishers for clicks but not for customers. Strategy differs: outrank vs. get listed/mentioned.
3. **Intent and format check.** If 7+ of the top 10 are a different page type than yours (e.g. lists vs your product page), the fix is format, not optimisation (heuristic). Report this first.
4. **Page-level comparison.** For each priority keyword:

   ```bash
   mkdir -p seo-work
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compare_pages.py" https://you.com/page https://rival1.com/a https://rival2.com/b https://rival3.com/c \
     --keyword "target keyword" > seo-work/compare-<slug>.json
   ```

   Read:
   - Word count vs `median_competitor_words` (context only: length is not a ranking factor; google-rules §4).
   - Headings and question headings.
   - Lists/tables.
   - Schema types.
   - Trust signals (author, dates, citations).
   - Keyword placement.
   - `content_gap_phrases` (subtopics 2+ rivals cover that you don't).

   Run comparisons for different keywords in parallel.
5. **Technical/experience gap** (optional):
   - `psi.py` on your URL and the top 2 rivals: field CWV `[measured: CrUX]`.
   - `page_audit.py` on rivals to see their schema and indexability setup.
6. **Content/keyword gap.**
   - **Free:** `keyword_ideas.py` on the rivals' main topics + the SERP batches. Any keyword where rivals rank top-10 and you don't appear is a gap `[measured: WebSearch sample]`.
   - **Paid:** see the next section.
7. **Backlink gap** (paid only). Referring domains linking to 2+ competitors but not you → feed to seo-links.
8. **Change monitoring.** When a rival suddenly outranks you:
   - Fetch the Wayback Machine CDX API: `https://web.archive.org/cdx/search/cdx?url=rival.com/page&output=json&limit=20&from=2025&fl=timestamp,statuscode,digest`.
   - Changed `digest` values show when the page content changed.
   - Fetch `https://web.archive.org/web/<timestamp>/rival.com/page` to diff old vs new (titles, headings, sections added).
   - Report: "ranking gain coincides with page update on <date>".
9. **Synthesise.**
   - Per keyword: why they win (format, depth, freshness, authority, UX, SERP features), with evidence tags.
   - A short list of actions routed to seo-content / seo-onpage / seo-schema / seo-links / seo-technical.

## Checks

| Check | Rule | Source |
|---|---|---|
| Intent/format match with the SERP majority | ≥7/10 same type → match it | heuristic |
| Length | no preferred word count; cover what searchers need | google-rules §4 [Google doc] |
| Original value vs summarising rivals | "adds value beyond others" is a helpful-content question | google-rules §4 [Google doc] |
| SERP features you can win | featured snippet / PAA: answer-first passages; video: watch page; images | google-rules §3, §8 [Google doc] |
| AI Overview present | eligibility = indexed + snippet-eligible; no special markup | google-rules §10 [Google doc] |
| Rival rich results | valid supported types only (FAQ/HowTo no longer shown) | google-rules §5 [Google doc] |
| Scraping/copying rival content | violates the scraping and scaled-content policies | google-rules §4 [Google doc] |

## Data: free vs paid

**Free:**
- WebSearch SERP samples.
- `compare_pages.py`, `keyword_ideas.py`, `page_audit.py`, `psi.py` (CrUX field data for rivals' URLs/origins).
- Wayback CDX.
- Google Trends for demand comparison.
- Rivals' public sitemaps (`sitemap_check.py https://rival.com --sample 0 --urls-out rival-urls.txt` gives their inventory and publishing cadence from lastmod).

**Paid** (`${CLAUDE_PLUGIN_ROOT}/references/tools.md`):
- **Semrush** (`## Semrush`).
  - Organic Research: a rival's ranking keywords and estimated traffic `[vendor data]`.
  - **Keyword Gap** (up to 5 domains): missing/weak/untapped keywords.
  - Position history around update dates.
  - Justified when you need *their* full keyword list rather than samples.
  - Cost tactic: one Keyword Gap export per quarter, filtered to positions 1–20 and your topics before exporting; use the right country database only.
- **Ahrefs** (`## Ahrefs`).
  - Site Explorer (Organic keywords, Top pages).
  - **Content Gap**, **Link Intersect**.
  - Justified for content + backlink gap together.
  - Cost tactic: Top pages by traffic + Content Gap, limited to rivals' top 50 pages. Avoid repeated full exports.
- **Similarweb** (`## Other paid tools`). Total traffic and channel-mix estimates (organic vs paid vs referral) for market sizing.
- **DataForSEO SERP API** (`## DataForSEO`). Exact, location-specific SERPs with feature parsing, at scale and pay-per-call. Justified when WebSearch samples aren't precise enough (local, multi-city, daily).

Never present vendor traffic or keyword numbers as measurements. They are `[vendor data]`/`[estimate]` and can be off by multiples, especially for small sites.

## Output

1. **Competitor map:** domain, type (business / publisher / UGC), share of top-10 slots across the keyword set, top overlapping keywords.
2. **SERP table per keyword:** intent, dominant format, features present, can we win it (yes/no/how).
3. **Page comparison summary per priority keyword:** your metrics vs median rival, gap phrases worth covering, missing schema/trust signals, routed actions.
4. **Gap list:** keywords rivals rank for that you don't (free sample or paid export), clustered and handed to seo-keywords/seo-strategy.
5. **Change log** for rivals that jumped (Wayback evidence).

## Pitfalls & myths

- **Your business rivals are not necessarily your SERP competitors.** Use the SERP.
- **"They rank because they're longer."** Correlation, not cause. Match intent and add something new instead of padding.
- **Copying rival headings verbatim** produces commodity content. Cover the gap topics *better* (first-hand data, tools, examples).
- **Vendor DR/DA/traffic** are models. A site with "lower DA" outranking you is normal.
- **WebSearch ≠ the user's live Google SERP** (location, personalisation, AI Overviews vary). Re-check key SERPs in a browser if decisions hinge on them.
- **Don't scrape rivals aggressively.** Fetch a handful of pages, respect robots.txt, and stop on CAPTCHA.

## Log the work

Append to `SEO-WORKLOG.md` (`${CLAUDE_PLUGIN_ROOT}/references/worklog.md`):
- Keyword set and market.
- Competitor list.
- Comparison files.
- Gap decisions.
- Paid-tool units/credits used.
- When to re-run (quarterly, or after the next core update).
