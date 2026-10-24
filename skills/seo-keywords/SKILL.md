---
name: seo-keywords
description: Keyword research and topic planning. Expands seeds into real queries (Google, Bing and YouTube autocomplete, People Also Ask, related searches, Search Console, forums), classifies intent, clusters keywords by SERP overlap, builds a topical map (pillar + clusters) and a prioritised target list. Triggers include "keyword research for X", "what should we write about", "find keywords for my site", "cluster these keywords", "topical map", "pillar pages", "which keywords should this page target", "keywords in Georgian/German for market Y" and "what are people searching for". It runs free by default and adds Semrush, Ahrefs, DataForSEO or Keyword Planner volumes only for a shortlist. It is not for optimising one page (seo-onpage), writing briefs or articles (seo-content), competitor domain teardowns (seo-competitors) or Search Console traffic diagnosis (seo-analytics).
---

# Keyword research, clustering and topical maps

Find what the audience actually types, group it the way Google groups it, and decide which page owns each group.

## When to use / not
- **Use:** new site or section, new market or language, content planning, mapping keywords to pages.
- **Not:**
  - existing traffic analysis → `seo-analytics`;
  - one page's tags → `seo-onpage`;
  - turning a cluster into a brief → `seo-content`.

## Inputs to gather (ask only for what's missing)
1. The business, offer, audience, and conversion goal (lead, sale, signup).
2. **Market:** country (`--gl`) and language (`--hl`). Use native-language seeds. Never transliterate (e.g. Georgian queries in Georgian script unless users really type Latin).
3. 3–10 seed topics: products, services, problems solved, competitor names.
4. **Optional:**
   - GSC Queries export, the best free source of real impressions;
   - existing URL list (crawl CSV or sitemap);
   - competitor domains.

## Workflow
1. **Expand the seeds in parallel.** Seeds are independent, so run one process per seed (or batch them):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_ideas.py" "english tutor" --hl en --gl gb --sources google,bing,youtube > seo-work/kw-english-tutor.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/keyword_ideas.py" "ielts preparation" --hl en --gl gb --deep > seo-work/kw-ielts.json
   ```
   - Each run returns `keywords` (with `sources`, `modifier`, `intent`), first-token `clusters`, and `multi_source` (typed in more than one engine, a stronger demand signal).
   - Keep `--delay` at 0.25 s or more. Autocomplete is an unofficial endpoint; stay modest.
2. **Mine what autocomplete misses:**
   - WebSearch each head term and record People Also Ask, related searches and SERP features.
   - Search Reddit, Quora and niche forums (`site:reddit.com <topic>`) for problem language and objections.
   - YouTube suggestions (`--sources youtube`) for how-to demand.
3. **Ground the list in GSC.** If an export exists:
   - run `gsc_analyze.py Queries.csv --brand "<brand regex>"`;
   - `striking_distance` and `question_queries` are proven demand on the site;
   - mark them `[measured]`.
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
   - **Parallelise:** split themes into batches of about 20 keywords and give each batch to a `seo-serp-researcher` subagent. Each returns `{"keyword": [top10 urls]}` JSON. Merge the batches into one `serps.json` and compute overlaps centrally with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serp_cluster.py" serps.json --same-page 4 --interlink 2`, so every cluster uses the same rule.
   - Pick the head term per cluster as the one with the broadest SERP and highest demand signal.
7. **Build the topical map:**
   - pillar pages (broad intent) → cluster pages (specific intents) → supporting FAQs and how-tos;
   - map each cluster to an existing URL (crawl CSV / GSC page) or mark it `new`;
   - one cluster = one primary URL, to avoid cannibalisation.
8. **Prioritise** with the heuristic below. Then shortlist about 20–50 clusters for volume lookup if the user has a paid source.

## Checks
**Demand evidence ladder** (strongest first):
1. GSC impressions for the site `[measured]`.
2. Keyword Planner or paid-tool volume `[vendor data]`.
3. Multi-engine autocomplete presence `[measured: suggested]`.
4. Single-source autocomplete.
5. PAA / forum mention.

Autocomplete proves a query is typed, **not how often**.

**Intent fit:** the page type you can build must match the dominant page type in the top 10. If 7 of 10 results are product category pages, a blog post is the wrong asset [heuristic].

**SERP features:** an AI Overview, local pack, video carousel or shopping results reduce organic clicks. Note them per cluster and expect lower CTR [Google doc: AI features, google-rules §10].

**Brand vs non-brand:** report them separately. Branded queries are not an SEO opportunity measure.

**Prioritisation (heuristic, not a Google metric):**
- `priority = demand (1–5) + business_fit (1–5) + winnability (1–5) − effort (1–5)`.
- **Demand:** from the evidence ladder.
- **Business fit:** how close it is to the conversion.
- **Winnability:** your existing position, whether the top 10 has weak or forum results, your topical authority. Never an invented KD number.
- **Effort:** a new page vs a refresh.
- State the scores' inputs in the CSV so they can be audited.

**Locale:** run separate research per country and language. Volumes, intent and SERPs differ (google-rules §6).

## Data: free vs paid
**The free path covers:** real query wording, question mining, intent from live SERPs, clustering by SERP overlap, your own impressions (GSC), and relative demand.

**What paid tools add (never required), and how to spend little:**
- **Google Ads Keyword Planner** (free with an Ads account): volume **ranges** for free; exact volumes only with active spend. It's the cheapest volume source. Paste only the shortlisted head terms.
- **Semrush / Ahrefs:** estimated volume, keyword difficulty, clickstream-based clicks per search, a competitor's ranking keywords (the fastest gap finder), and SERP history.
  - Justified when you need competitor keyword sets or difficulty at scale.
  - Cost tactics: query only cluster head terms, limit rows, use one database/country, export once and cache (tools.md `## Semrush`, `## Ahrefs`, `## Cost-optimisation playbook`).
- **DataForSEO Keywords Data API:** Google Ads volumes, pay as you go, batches up to the API limit per task.
  - Cheapest for bulk volumes of a few hundred to thousands of terms.
  - Batch everything into as few tasks as possible (tools.md `## DataForSEO`).
- **Keywords Everywhere:** cheap per-keyword credits for spot checks (tools.md `## Other paid tools`).

Without one of these, the volume column is `[needs data]`. Never estimate it.

## Output
`seo-work/keywords.csv` with columns:
```
cluster, keyword, is_head_term, intent, serp_page_type, serp_features, demand_evidence, gsc_impressions,
volume, volume_source, current_url, current_position, target_url, action(new|refresh|merge|none),
demand, business_fit, winnability, effort, priority, notes
```
Plus `seo-work/topical-map.md`:
- pillar → clusters tree, with the target URL per cluster and internal links planned (cluster ↔ pillar, sibling ↔ sibling where SERPs overlap 2–3);
- the top 10 priorities with reasons and evidence tags;
- the shortlist for volume lookup, if paid data is wanted.

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
- keyword and cluster counts;
- pages mapped;
- items `[needs data]`;
- a re-check date (re-pull GSC in 8–12 weeks).
