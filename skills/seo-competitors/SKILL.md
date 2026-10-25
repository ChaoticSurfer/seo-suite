---
name: seo-competitors
description: Competitor and SERP analysis. Use for "who are my SEO competitors", "why does X outrank me", content and keyword gaps, SERP features, competitor traffic and page changes. Finds real SERP competitors, compares pages, tracks changes via the Wayback Machine. Not for keyword discovery (seo-keywords) or link building (seo-links).
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

## Inputs: decide, don't ask

Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Your domain | The request | — |
| Target keyword set (10–100) | seo-keywords output or the GSC striking-distance list; otherwise titles, H1s and nav labels of money pages, expanded with `keyword_ideas.py` | ~20 head terms from the money pages |
| **Market:** country + language (`--gl`/`--hl` equivalents for searches), device focus | `<html lang>`, ccTLD, hreflang, currency, addresses; device split in GSC/GA4 | The copy's language and its main country; mobile |
| Business rivals the user already knows | Useful if named, but verify them against the SERP | The SERP competitors from step 2 |
| Optional: paid tool access (Semrush/Ahrefs/Similarweb) and any credit budget | The configured budget and connectors (`references/autonomy.md`) | Budget 0: the free path. Access the plan needs: **ask — batched at the end**, saying what it adds |

## Workflow

**Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`):

```bash
mkdir -p seo-work
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export clusters --locale en --format json > seo-work/store-clusters-en.json
```

- **Keyword set:** the clusters' head keywords for the market's locale, before the Inputs fallbacks.
- **SERPs:** reuse the fresh snapshots in `seo-research/serps/<locale>/` (fetched within the `serps` TTL of 30 days). Step 1 collects only the set's keywords listed in `gaps.<locale>.needs_serp`.
- **Competitors:** with fresh SERPs, `seo-research/competitors.json` (`keywords_shared`: the stored SERPs each domain appears in) is the starting count for step 2.
- No store yet (`status` exits with "no research store here"): create it with `init --site URL --locales …` (research-store §9).

1. **Collect SERPs (parallel).**
   - Split the keyword set into batches of at most 10 and launch one `seo-serp-researcher` agent per batch, in parallel. Give each batch the market and an output path such as `seo-work/serps-en-1.json`, numbered per batch: the agent writes that details file and `seo-work/serps-en-1.serps.json` beside it, for step 10. Without a path it returns the table only.
   - Each returns, per keyword: top-10 organic URLs, page type (guide / category / product / tool / forum / video / local pack), SERP features (AI Overview, featured snippet, PAA, video, images, shopping, local pack, forums/"Discussions"), and dominant intent.
   - WebSearch results approximate the SERP; they are not a personalised, location-exact Google SERP. Tag them `[measured: WebSearch sample]`.
2. **Identify SERP competitors.**
   - Count domain appearances across all keywords. The top 5–10 domains by share of top-10 slots are your real competitors.
   - Separate:
     - Direct business competitors.
     - Content publishers/aggregators.
     - Marketplaces/UGC (Reddit, YouTube, Wikipedia).
   - You compete with the publishers for clicks but not for customers. Strategy differs: outrank vs. get listed/mentioned.
   - **Who is winning: share of voice.** When seo-analytics keeps rank snapshots for this market (`seo-work/rank/*.snapshot.json` from `rank_snapshot.py`), read them before counting slots. They cost nothing extra here.
     - `metrics.top_domains`: each domain's share of the estimated clicks across the keyword set, best first [estimate]. `metrics.share_of_voice` and `metrics.visibility_pct` give the same for us and the named competitors.
     - `metrics.ai_overview.citation_share`: how often each domain is cited when an AI Overview shows [vendor data].
     - The trend: the same figures in earlier snapshots of the same keyword-set version and the same `meta.ctr_curve`. A competitor that gained share across three snapshots is the one to study first (steps 4 and 8).
     - A domain high in `top_domains` that isn't a named competitor joins the list, and the keyword set gets a new version.
     - Without snapshots (budget 0), the share of top-10 slots in the WebSearch sample stands in, tagged `[measured: WebSearch sample]`.
   - **In AI answers:** `ai_visibility.py` on `ai_probe.py` observations (seo-ai-search) gives `share_of_voice` per engine, the answers naming each brand out of those naming any tracked brand, and `citation_source_gap`: the domains cited where a competitor is named and we aren't. Hand those domains to seo-links as PR and listing targets.
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
   - Fetch the Wayback Machine CDX API: `https://web.archive.org/cdx/search/cdx?url=rival.com/page&output=json&from=<YYYYMMDD, about 3–6 months before the ranking change>&filter=statuscode:200&collapse=digest&fl=timestamp,statuscode,digest`.
   - `collapse=digest` keeps only captures where the content changed, so each row's timestamp is the date a new version first appeared. Don't add a negative `limit`: rows then show the last capture of each version, so dates come out late.
   - Fetch `https://web.archive.org/web/<timestamp>/rival.com/page` to diff old vs new (titles, headings, sections added).
   - Report: "ranking gain coincides with page update on <date>".
9. **Synthesise.**
   - Per keyword: why they win (format, depth, freshness, authority, UX, SERP features), with evidence tags.
   - A short list of actions routed to seo-content / seo-onpage / seo-schema / seo-links / seo-technical.
10. **Write back to the research store,** once, after the batches:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest serps seo-work/serps-en-1.serps.json --locale en --details seo-work/serps-en-1.json
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest keyword-ideas seo-work/kw-<rival-topic>.json --locale en
    ```

    - One `ingest serps` per `seo-serp-researcher` batch from step 1 (`serps-en-<n>.serps.json` with its details file). It also refreshes `competitors.json`.
    - One `ingest keyword-ideas` per `keyword_ideas.py` file from step 6.
    - A paid gap export (keyword, volume and difficulty columns): `ingest volumes FILE --locale en --source semrush` (or `ahrefs`). Before committing Semrush volumes, see research-store §1.
    - The gap keywords are clustered by seo-keywords, not here.

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
- **DataForSEO SERP API** (`## DataForSEO`). Exact, location-specific SERPs with feature parsing, at scale and pay-per-call: $0.0006 per 10 results in the Standard queue. Justified when WebSearch samples aren't precise enough (local, multi-city, daily). `rank_snapshot.py` buys them for seo-analytics' keyword sets, and the same snapshots give every competitor's position and share of voice, so reuse them before buying SERPs here.

Never present vendor traffic or keyword numbers as measurements. They are `[vendor data]`/`[estimate]` and can be off by multiples, especially for small sites.

## Output

1. **Competitor map:** domain, type (business / publisher / UGC), share of voice and its trend from the rank snapshots (or the share of top-10 slots without them), AI Overview citation share, AI-answer share of voice, top overlapping keywords.
2. **SERP table per keyword:** intent, dominant format, features present, can we win it (yes/no/how).
3. **Page comparison summary per priority keyword:** your metrics vs median rival, gap phrases worth covering, missing schema/trust signals, routed actions.
4. **Gap list:** keywords rivals rank for that you don't (free sample or paid export), clustered and handed to seo-keywords/seo-strategy.
5. **Change log** for rivals that jumped (Wayback evidence).
6. **Assumptions:** the keyword set, market, device and competitor choices you decided, each with its evidence, and which store data was reused and how old it was (e.g. "en SERPs: 31 reused at 4–25 days, 9 refreshed"). Then the questions batched for the user (missing paid access), each with a recommendation.

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
- Store data reused (with its age) and the SERP batches ingested.
- Competitor list, with the snapshot files and keyword-set version its share of voice came from.
- Comparison files.
- Gap decisions.
- Paid-tool units/credits used.
- When to re-run (quarterly, or after the next core update).
