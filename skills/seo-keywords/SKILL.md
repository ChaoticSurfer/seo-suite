---
name: seo-keywords
description: Keyword research and topic planning. Expands seeds into real queries (Google, Bing and YouTube autocomplete, People Also Ask, related searches, Search Console, forums), classifies intent, clusters keywords by SERP overlap, builds a topical map (pillar + clusters) and a prioritised target list. Triggers include "keyword research for X", "what should we write about", "find keywords for my site", "cluster these keywords", "topical map", "pillar pages", "which keywords should this page target", "keywords in Georgian/German for market Y" and "what are people searching for". It runs free by default and adds Semrush, Ahrefs, DataForSEO or Keyword Planner volumes only for a shortlist. Results go into the shared research store (seo-research/) that every other skill reuses. It is not for optimising one page (seo-onpage), writing briefs or articles (seo-content), blog batches (seo-blog-builder), competitor domain teardowns (seo-competitors) or Search Console traffic diagnosis (seo-analytics).
---

# Keyword research, clustering and topical maps

Find what the audience actually types, group it the way Google groups it, and decide which page owns each group.

## When to use / not
- **Use:** new site or section, new market or language, content planning, mapping keywords to pages.
- **Not:**
  - existing traffic analysis → `seo-analytics`;
  - one page's tags → `seo-onpage`;
  - turning a cluster into a brief → `seo-content`;
  - turning clusters into a blog batch → `seo-blog-builder`.

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Business, offer, audience, conversion goal (lead, sale, signup) | Home page, navigation, money pages (forms, cart, checkout, booking, pricing), Product/Service/LocalBusiness schema | The goal of the money pages' main call to action |
| **Market:** country (`--gl`) and language (`--hl`) | `<html lang>`, ccTLD, hreflang, currency, addresses. Use native-language seeds. Never transliterate (e.g. Georgian queries in Georgian script unless users really type Latin) | The copy's language and its main country. Entering a new market or language is a business decision: **ask — batched at the end** |
| 3–10 seed topics (products, services, problems solved, competitor names) | Titles, H1s and nav labels of money pages, plus GSC queries | The money pages' H1s |
| Competitor domains | Domains in the top 10 for the head terms (WebSearch, US-located: step 6) | The domains that recur most across those SERPs |
| Existing URL list | `sitemap_check.py --urls-out`, or a crawl CSV | Run the sitemap check |
| GSC Queries export, the best free source of real impressions | A connector, or an export in `seo-work/` | **Ask — batched at the end.** Carry on with autocomplete and SERP evidence |

## Workflow
0. **Read the research store first.** This skill fills the shared store in `seo-research/`
   (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`), and every other skill reuses it, so research each locale
   once and refresh only what has gone stale:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export keywords --locale en --format json > seo-work/store-keywords-en.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export clusters --locale en --format json > seo-work/store-clusters-en.json
   ```
   - No store yet: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" init --site "$SITE" --locales en,ka,ru`, default locale first.
   - Reuse every dataset that `status` doesn't list under `stale` or `missing` for the locale, except the stale records it lists in `gaps.<locale>` (router rule 7). Run step 1 when `keywords` is stale or missing, or for seeds the store doesn't cover yet; step 3 when `gsc` is, or `stale_gsc` lists rows, and for `stale_gsc_pages` with a query+page export (a Queries.csv has no pages, so it leaves them stale); step 6 only for `gaps.<locale>.needs_serp`; step 8's volume lookup for the shortlisted keywords in `stale_volumes`. Before step 7 maps clusters to pages, re-crawl the sections in `stale_inventory` and `ingest crawl`.
1. **Expand the seeds in parallel.** Seeds are independent, so run one process per seed (or batch them), then ingest each file:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_ideas.py" "english tutor" --hl en --gl gb --sources google,bing,youtube > seo-work/kw-english-tutor.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_ideas.py" "ielts preparation" --hl en --gl gb --deep > seo-work/kw-ielts.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_ideas.py" "ინგლისური ენის კურსები" --hl ka --gl ge --sources google > seo-work/kw-ka-courses.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_ideas.py" "репетитор английского" --hl ru --gl ge --sources google,bing > seo-work/kw-ru-tutor.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest keyword-ideas seo-work/kw-english-tutor.json --locale en
   ```
   - Each run returns `keywords` (with `sources`, `modifier`, `intent`), first-token `clusters`, and `multi_source` (typed in more than one engine, a stronger demand signal).
   - `--hl` picks the expansion language. en, ka, ru, he, ar, de and es each have their own letters (Mkhedruli, Cyrillic, Hebrew, Arabic, or Latin with ä ö ü or ñ), question words, modifiers and intent words. Any other language uses the English ones, and `warnings` says so.
   - `completions` is each seed's demand per engine: the suggestions for the bare seed, minus the seed itself. Autocomplete echoes any query it has a signal for, so a seed that only echoes itself scores 0. If a seed scores 0 in every engine, reword it or drop it. `null` means the engine couldn't be read: re-run it, and never read it as 0.
   - Keep `--delay` at 0.25 s or more. Autocomplete is an unofficial endpoint; stay modest.
   - Yandex suggest is left out on purpose. Yandex's search licence (clause 6.6) allows automatic requests only through its paid Search API. For ru, use Google and Bing.
2. **Mine what autocomplete misses:**
   - WebSearch each head term and record People Also Ask, related searches and SERP features. The results are US-located (step 6).
   - Search Reddit, Quora and niche forums (`site:reddit.com <topic>`) for problem language and objections.
   - YouTube suggestions (`--sources youtube`) for how-to demand.
3. **Ground the list in GSC.** If an export exists:
   - run `gsc_analyze.py Queries.csv --brand "<brand regex>"`;
   - `striking_distance` and `question_queries` are proven demand on the site;
   - mark them `[measured]`;
   - ingest the CSV itself, which holds every row: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest gsc Queries.csv --locale en --as-of "$PERIOD_END"`, with the last day the export covers (a query+page export needs no `--locale`).
4. **Clean the list:**
   - de-duplicate (plurals, word order);
   - drop off-topic senses (the classic one is "english teacher" the TV show — check the meaning);
   - drop competitor-navigational terms unless you'll build comparison pages.
5. **Classify intent:**
   - start from the script's `intent` (informational / commercial / transactional / navigational / unclear);
   - correct it by looking at the live SERP (step 6), since page types reveal intent better than words;
   - resolve every `unclear`.
6. **Cluster by SERP overlap.** This is the Google-grounded method; first-token clusters are only a starting point.
   - For each candidate pair inside a theme, WebSearch both in the target locale and compare the top-10 organic URLs.
   - **4 or more shared URLs → same page.** 2–3 shared → separate pages that interlink. 0–1 → separate topics [heuristic, consistent with common SERP-overlap practice].
   - **WebSearch results are US-located:** the tool describes itself as US-only. Tag them `[measured: WebSearch sample, US-located, <date>]`. They fit an en-US market; for any other market they are directional.
   - **Georgia-located results** (ka-GE, ru-GE, en-GE) come from one of two places:
     - DataForSEO's Google Organic SERP with `location_code` 2268. It is paid, so run it only within the configured budget, which the credit guard enforces (tools-paid.md `## DataForSEO`).
     - A watched browser session: a person opens Google with `gl=ge` and the locale's `hl`, and records the top 10. Never automate google.com/search.
   - With neither available, cluster on the WebSearch samples, mark those clusters `[directional: US-located SERPs]`, and add the DataForSEO budget for the head terms to the requests batched at the end.
   - **Parallelise:** split the keywords in `gaps.<locale>.needs_serp` (up to 50 per `status` run, strongest demand first) into batches of about 10 and give each batch to a `seo-serp-researcher` subagent with an output path such as `seo-work/serps-en-1.json`. Each writes that details file and `seo-work/serps-en-1.serps.json` (`{"keyword": [top10 urls]}`). Ingest every batch, then cluster the locale's whole SERP set (the fresh snapshots already in the store plus the new ones) centrally, so every cluster uses the same rule:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest serps seo-work/serps-en-1.serps.json --locale en --details seo-work/serps-en-1.json
     python3 -c "import glob, json, sys; print(json.dumps({s['keyword']: [r['url'] for r in s['results']] for s in (json.load(open(p, encoding='utf-8')) for p in glob.glob(sys.argv[1] + '/*.json'))}, ensure_ascii=False))" seo-research/serps/en > seo-work/serps-en.json
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serp_cluster.py" seo-work/serps-en.json --same-page 4 --interlink 2 > seo-work/clusters-en.json
     ```
   - Pick the head term per cluster as the one with the broadest SERP and highest demand signal.
7. **Build the topical map:**
   - pillar pages (broad intent) → cluster pages (specific intents) → supporting FAQs and how-tos;
   - map each cluster to an existing URL (the store's `export inventory` and `export posts`, crawl CSV / GSC page) or mark it `new`;
   - one cluster = one primary URL, to avoid cannibalisation.
8. **Prioritise** with the heuristic below. Then shortlist about 20–50 clusters for volume lookup if a paid source is configured, and run it within the configured budget (references/autonomy.md). Ingest the export: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest volumes seo-work/semrush-en.csv --locale en --source semrush`.
9. **Write the decisions back to the store**, so the next skill starts from this map:
   - In `seo-work/clusters-en.json`, add to each cluster entry its `role` (`pillar`, `cluster` or `support`), its `head_keyword`, and its `target_url` when step 7 mapped one. Then ingest it:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest clusters seo-work/clusters-en.json --locale en
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" set-status --keyword "english teacher tv show" --locale en --status skip
     ```
   - Mark `skip` every keyword step 4 dropped, so no skill picks it up again. A cluster left with only dropped keywords gets `--cluster` and `--status skip` too, or `next-topics` still offers it.
   - Re-run `status`. Whatever is still `missing` or `stale` (volumes without a paid source, GSC without an export) goes into the requests batched at the end.

## Checks
**Demand evidence ladder** (strongest first):
1. GSC impressions for the site `[measured]`.
2. Keyword Planner or paid-tool volume `[vendor data]`.
3. Multi-engine autocomplete presence `[measured: suggested]`.
4. Single-source autocomplete.
5. PAA / forum mention.

Autocomplete proves a query is typed, **not how often**. Count completions without the echo: the engine returns the query itself whenever it has any signal for it, so a seed whose only suggestion is itself has no measured demand.

**Intent fit:** the page type you can build must match the dominant page type in the top 10. If 7 of 10 results are product category pages, a blog post is the wrong asset [heuristic].

**SERP features:** an AI Overview, local pack, video carousel or shopping results often lower organic CTR. Note them per cluster and check against the site's own GSC CTR by position [heuristic].

**Brand vs non-brand:** report them separately. Branded queries are not an SEO opportunity measure.

**Prioritisation: one formula in two steps (heuristic, not a Google metric):**

1. **Automatic score, every cluster.** `research_store.py next-topics --page-type article|booking` scores what can be
   measured, with a reason for every point (research-store §7):
   `automatic = intent_fit (0–3) + demand (0–4) + serp_gap (−2–3) − cannibalisation (0–3)`.
   - `--page-type` is the page you would build: `article` for a blog post or guide, `booking` for a page that sells
     (tour, service, product, category). Score a cluster both ways when unsure; the SERP shows which page type wins
     (see Intent fit above).
   - Demand follows the evidence ladder. Winnability is in `serp_gap` (weak forum results, AI Overview and, for
     booking pages, a top 10 that is half or more marketplace listings such as OTAs) and in `cannibalisation`. Never an
     invented KD number.
2. **Final score, shortlist only** (the top 50–100 automatic scores per locale). Add what a script can't know:
   `priority = automatic + business_fit (0–3) + season (0–1) − effort (0–2)`.
   - **business_fit:** 3 the searcher can buy what the site sells, on this page · 2 close to buying (comparing,
     planning) · 1 informational that can lead to a sale · **0 not what the business sells: drop it** with
     `set-status --status skip`, whatever its other scores.
   - **season:** 1 when demand peaks 2–4 months from now (Google Trends, that locale), the time a new page needs to be
     indexed and climb; otherwise 0.
   - **effort:** 0 refresh an existing page · 1 new page from material the site already has · 2 new page that needs
     new facts, photos, data or an expert.
   - Ties go to higher-value conversions (a larger order or booking).
   - Write every input and its reason into the CSV, so the order can be audited.

**Tour and travel operators (the formula applied):**

| business_fit | Example searches | Page |
|---|---|---|
| 3 | "private kazbegi tour from tbilisi", "tbilisi airport transfer", «экскурсия в казбеги с русским гидом» | Tour or service page (`booking`) |
| 2 | "tbilisi to kazbegi how to get there", "kakheti day trip itinerary" | Guide that links to the tour (`article`) |
| 1 | "gergeti trinity church history", "kazbegi weather in march" | Article with a tour link |
| 0 | Packages with flights or hotels you don't sell ("tour package from india"), visas, jobs, a same-name place elsewhere | Drop |

- **Marketplace wall:** when OTAs (GetYourGuide, Viator, Tripadvisor, Klook) fill page 1, the booking score drops. Aim
  for the long tail they don't cover: private, from a named city, a guide's language, a vehicle size.
- **Season:** publish 2–4 months before the peak: winter mountain roads and ski in September–October, wine harvest in
  June–July, summer hikes in March–April.
- **Ties:** a multi-day tour beats a half-day one; a tour you can run every day beats one with rare dates.
- Compare demand only within one language. A thin Hebrew or Arabic SERP can beat a bigger English one.

**Locale:** run separate research per country and language. Volumes, intent and SERPs differ (google-rules §6).

## Data: free vs paid
**The free path covers:** real query wording, question mining, intent from live SERPs, clustering by SERP overlap, your own impressions (GSC), and relative demand.

**What paid tools add (never required), and how to spend little:**
- **Google Ads Keyword Planner** (free with an Ads account): volume **ranges** for free; exact volumes only with active spend. It's the cheapest volume source. Query only the shortlisted head terms.
- **Semrush / Ahrefs:** estimated volume, keyword difficulty, clickstream-based clicks per search, a competitor's ranking keywords (the fastest gap finder), and SERP history.
  - Justified when you need competitor keyword sets or difficulty at scale.
  - Cost tactics: query only cluster head terms, limit rows, use one database/country, export once and cache (tools-paid.md `## Semrush`, `## Ahrefs`, `## Cost-optimisation playbook`).
- **DataForSEO Keywords Data API:** Google Ads volumes, pay as you go, batches up to the API limit per task.
  - Cheapest for bulk volumes of a few hundred to thousands of terms.
  - Batch everything into as few tasks as possible (tools-paid.md `## DataForSEO`).
- **Keywords Everywhere:** cheap per-keyword credits for spot checks (tools-paid.md `## Other paid tools`).
- **DataForSEO Google Organic SERP:** Georgia-located top 10s (`location_code` 2268) for clustering ka-GE and ru-GE, which WebSearch can't give. Query only the cluster head terms (tools-paid.md `## DataForSEO`).

Without one of these, the volume column is `[needs data]`. Never estimate it.

## Output
The research store (`seo-research/`): keywords with their demand evidence, SERP snapshots, clusters with role and
target URL, and volumes with their source and date. Other skills start from the store; the files below are this
run's report.

`seo-work/keywords.csv` with columns:
```
cluster, keyword, is_head_term, intent, serp_page_type, serp_features, demand_evidence, gsc_impressions,
volume, volume_source, current_url, current_position, target_url, action(new|refresh|merge|none),
page_type, automatic, business_fit, season, effort, priority, notes
```
Plus `seo-work/topical-map.md`:
- pillar → clusters tree, with the target URL per cluster and internal links planned (cluster ↔ pillar, sibling ↔ sibling where SERPs overlap 2–3);
- the top 10 priorities with reasons and evidence tags;
- the shortlist for volume lookup, if paid data is wanted;
- **Assumptions:** the business goal, market, seeds and competitors chosen, with the evidence for each; which store data was reused and how old it was, and what was refreshed. Then the requests batched at the end, each with a recommendation: missing access (GSC), budget for the volume shortlist, new markets.

## Pitfalls & myths
- Choosing keywords by volume alone ignores intent and winnability. A 50-search, high-intent query can beat a 5,000-search informational one.
- Third-party "keyword difficulty" scores are vendor models, not Google data. Tag them `[vendor data]`.
- One page per keyword variant leads to cannibalisation and thin pages. Cluster by SERP overlap.
- Translating keywords instead of researching per language misses how locals search.
- Autocomplete differs by location, history and time. Record the date and locale.
- AI-search "prompts" aren't keywords, but question-form queries from PAA and GSC `question_queries` are the bridge. Hand off to `seo-ai-search`.

## Log the work
Append an entry to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`. Include:
- seeds, locale and date;
- sources used, with paid units or credits spent and on which terms;
- the store datasets reused (with their age) and the ingests run;
- keyword and cluster counts;
- pages mapped;
- items `[needs data]`;
- a re-check date (re-pull GSC in 8–12 weeks).
