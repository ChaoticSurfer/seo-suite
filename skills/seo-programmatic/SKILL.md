---
name: seo-programmatic
description: Plan, build, QA, roll out and prune programmatic SEO page sets generated from data and templates. Examples include location × service pages, integrations, comparisons ("X vs Y"), glossaries, directories, tools by use case, and product or attribute landing pages. Triggers include "programmatic SEO", "pSEO", "generate pages for every city", "template pages at scale", "landing pages from our database", "is this doorway/scaled content", "should we make 5,000 pages" and "our generated pages aren't indexed". It includes a go/no-go test, quality gates, batch rollout and pruning within Google's scaled-content-abuse and doorway policies. It is not for single pages (seo-onpage), hand-written content programmes (seo-content), local Business Profile work (seo-local) or e-commerce category and faceted navigation (seo-ecommerce).
---

# Programmatic SEO

Generate many pages only when each one carries unique, useful data for a real query. Prove that on a sample before scaling.

## When to use / not
- **Use:**
  - a dataset (rows, entities, locations, integrations, attributes);
  - a repeated query pattern (`<service> in <city>`, `<tool> integration with <app>`, `<a> vs <b>`);
  - a template.
- **Not:**
  - a few dozen hand-written pages → `seo-content`;
  - product listing pages and facets → `seo-ecommerce`;
  - GBP or location citations → `seo-local`.

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Query pattern(s) and example queries | The dataset's entity types, existing URL patterns (sitemap, crawl CSV), competitors' template folders in the SERPs | The pattern the existing pages already follow |
| **The dataset:** source, fields per record, record count, update frequency | The file, table or repo in the request; else the fields visible on existing pages | Count only the fields you can see. Repo or database access you lack: **ask — batched at the end** |
| Dataset licence or ownership | Terms, source attribution, the repo | Treat it as not first-party, and weigh the go/no-go that way. **Ask — batched at the end** |
| **The template** and tech stack: how pages are rendered (SSR/SSG is preferred) | The repo's framework files; else the live page and `render_diff.py` | The live page as served |
| **Business value:** what a visitor can do on the page (book, compare, sign up) | Calls to action on existing template pages and money pages | The site's main conversion |
| **Existing sets:** URL patterns, sitemap | Crawl CSV, `sitemap_check.py` | Run both |
| **Existing sets:** GSC Pages export, indexing report counts | A connector, or exports in `seo-work/` | **Ask — batched at the end.** Carry on with the crawl and sitemap |

## Workflow
1. **Go/no-go**, before building anything. Answer each with evidence:
   - **Demand:**
     - does the pattern have real queries?
     - sample 20 instances with `keyword_ideas.py "<pattern instance>" --hl … --gl …` and WebSearch;
     - autocomplete or GSC impressions are evidence, guesses are not.
   - **SERP fit:**
     - for 10 sampled instances, are the top results the same page type (directory, location, comparison)?
     - if they're all national brands or editorial guides, a template page rarely wins [heuristic].
   - **Unique value per page:**
     - at least ~10 meaningful data fields per record that change the page's substance, ideally 20+ [heuristic, borrowed from common pSEO practice];
     - not just a swapped city or name.
   - **Data ownership and freshness:** first-party or licensed data beats scraped data. Scraping and republishing others' content is spam (google-rules §4).

   If two or more answers are weak, **recommend not building**, or start with 20–50 hand-curated pages.
2. **Design the template with data:**
   - Answer the query in the first 200 words using record-specific facts [heuristic].
   - **Data-driven sections:** tables, prices, availability, maps, reviews of *other* entities, stats, FAQs generated from real per-record questions.
   - **Conditional sections:** hide a block when its data is missing. Never print "N/A" walls.
   - **Internal linking:**
     - hub → children;
     - siblings by proximity or similarity;
     - breadcrumbs;
     - each page reachable within 3 clicks [heuristic].
   - Head: a unique title and description from fields, a self-referencing canonical, and schema matching visible data (hand off to `seo-schema`).
   - Render server-side; check with `render_diff.py` if JS fills content.
3. **Build a sample of 50–200 pages** (code changes and deploys per autonomy level, references/autonomy.md) on an indexable build the public can't find (e.g. an IP-allowlisted staging host with no noindex and no auth), or a small production batch. Set this build's canonical base URL to the host you crawl (the staging host), so every page's canonical points to its own URL there. crawl.py skips noindex pages in its duplicate, near-duplicate and depth checks, skips pages whose canonical points to another URL in its duplicate and near-duplicate checks, and it can't log in.
4. **Run the quality gates in parallel:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crawl.py" "$STAGING_HUB" --max-pages 300 --csv seo-work/pseo.csv > seo-work/pseo-crawl.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_audit.py" "$SAMPLE_URL" --fail-on high > seo-work/pseo-page.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/content_score.py" "$SAMPLE_URL" --keyword "$PATTERN_INSTANCE" > seo-work/pseo-content.json
   ```
   - In `seo-work/pseo-crawl.json`, `duplicate-content`, `near-duplicate-content`, `duplicate-titles` and `duplicate-descriptions` must be empty.
   - Before trusting those gates, check that the crawl saw every generated page: `hit_page_limit` in `seo-work/pseo-crawl.json` must be false, and every URL in the sample's sitemap must have a row in `seo-work/pseo.csv`. This writes the URL list and prints the URLs with no row:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sitemap_check.py" "$SAMPLE_SITEMAP" --sample 0 --urls-out seo-work/pseo-urls.txt > seo-work/pseo-sitemap.json
     PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -c "import csv; from seo_lib import normalize_url; rows = {r['url'].rstrip('/') for r in csv.DictReader(open('seo-work/pseo.csv'))}; print([u for u in open('seo-work/pseo-urls.txt').read().split() if normalize_url(u).rstrip('/') not in rows])"
     ```
   - Every row must also have `indexable` True and a `canonical` equal to its own `url`. Pages that fail this are left out of the duplicate gates, so an empty duplicate list doesn't count as a pass. This lists the rows that fail:
     ```bash
     python3 -c "import csv; print([r['url'] for r in csv.DictReader(open('seo-work/pseo.csv')) if r['indexable'] != 'True' or r['canonical'].rstrip('/') != r['url'].rstrip('/')])"
     ```
   - Exact-hash duplicates mean the template varies nothing.
   - Then do a human/LLM review of 20 random pages against the checklist in Checks.
   - **Halt the rollout if more than 5% of sampled pages fail a gate** [heuristic].
5. **Roll out in batches** (each release per autonomy level, references/autonomy.md):
   - release about 5–10% of pages or one high-demand segment first;
   - put them in their own sitemap file (`sitemap-<pattern>-1.xml`) so indexing per batch is measurable in Search Console;
   - validate with `sitemap_check.py <sitemap> --sample 50`;
   - wait for indexing data (2–4 weeks) before the next batch.
6. **Monitor:**
   - GSC Pages → "Crawled/Discovered – currently not indexed" per batch sitemap;
   - impressions per page;
   - `gsc_analyze.py` on query+page for cannibalisation between template instances;
   - log the analysis (`log_analyze.py`) to see whether Googlebot crawls the batch.
7. **Prune:**
   - pages with no impressions after about 3–6 months and no unique data become candidates to merge into their hub, noindex, or remove (404/410);
   - improve the data before adding more pages;
   - keep the sitemap to pages you'd defend.

## Checks
**Policy boundaries** (google-rules §4, must pass):
- **Scaled content abuse:** many pages made mainly to manipulate rankings with little value, however they are made (templates, AI, scraping, synonymising, translation). A template is fine; a template with no per-page substance is not.
- **Doorway abuse:** many near-identical pages funnelling users to one destination, or targeting regions/cities with nothing locally specific.
- **Site reputation abuse:** hosting third-party pSEO on a strong domain to borrow its signals. First-party oversight does not automatically exempt it. In the EEA (since 2026-08-28), such pages are ranked separately.
- **Thin affiliation:** product or comparison pages copying merchant data with no added value.
- **Fake reviews or ratings in schema:** prohibited. Self-serving LocalBusiness/Organization reviews are ineligible (google-rules §5).

**City-swap test (location pages):** replace the city name in a page with another city. If the page still reads as true, it's a doorway. Location pages need local specifics:
- an address or service area;
- local staff, photos, prices, availability;
- local reviews or cases;
- directions;
- local regulations.

**Uniqueness:**
- no exact-duplicate bodies (crawl hash);
- near-duplicate checks by human sample;
- titles, H1s and descriptions differ by meaningful fields, not just the swapped token.

**Indexability:**
- 200 status;
- self-referencing canonical;
- in the sitemap only when indexable;
- no `noindex` in the initial HTML for pages meant to rank (google-rules §1);
- empty-data combinations return 404, not thin pages (google-rules §8, faceted navigation guidance).

**Crawl budget:**
- it only matters at roughly 1M+ pages changing weekly, or 10k+ pages changing daily, or a large "Discovered – currently not indexed" backlog (google-rules §1);
- consolidate duplicates;
- don't rely on noindex to save budget.

**Freshness:** the data refresh date is visible and accurate. `lastmod` changes only when the data changes (google-rules §1).

## Data: free vs paid
**The free path covers:**
- pattern demand sampling (autocomplete, WebSearch);
- SERP fit;
- template QA (crawl, page_audit, content_score);
- rollout monitoring (GSC sitemaps and page indexing, logs).

**What paid tools add (never required):**
- **DataForSEO Keywords Data / SERP API:** volumes and SERPs for thousands of pattern instances in a few batched tasks, the cheapest way to size the whole pattern before building (tools.md `## DataForSEO`).
- **Semrush / Ahrefs:** competitors' programmatic folders and their traffic estimates. Pull "top pages" filtered to the competitor's template path to see which instances actually earn traffic before choosing yours (tools.md `## Semrush`, `## Ahrefs`).
- **Screaming Frog:** near-duplicate detection (minhash similarity) and custom extraction across the full set (tools.md `## Screaming Frog`).

Size and traffic estimates without data stay `[needs data]`.

## Output
- `pseo-plan.md`:
  - a go/no-go verdict with evidence per criterion;
  - the template spec (sections ↔ data fields, conditional rules, internal-link rules, head template);
  - QA gate results on the sample (pass/fail counts, failing URLs);
  - the batch rollout plan (segments, sitemap files, dates, success criteria: indexed %, impressions per page);
  - pruning rules;
  - **Assumptions:** the pattern, dataset fields, licence, rendering and business value assumed, with the evidence for each. Then the requests batched at the end, each with a recommendation: missing access (repo, database, GSC) and business decisions (whether to build at all, how many pages).
- For code: the template/component and sitemap generator changes, as diffs.

## Pitfalls & myths
- "Google penalises programmatic pages": it targets low-value scaled pages, not templates. Zillow-style data pages are fine.
- Launching 50k pages at once means you can't tell which segment fails, and indexing stalls. Use batches with their own sitemaps.
- Spinning text with AI to "make pages unique" without new data is still scaled content abuse.
- Auto-generated FAQs with invented Q&A add nothing, and FAQ rich results no longer show (google-rules §5).
- `noindex` on most of the set while still linking to it sitewide wastes crawl and confuses signals. Generate fewer pages instead.
- Location pages for places you don't serve are doorways and also misleading to users.

## Log the work
Append an entry to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`. Include:
- the pattern and the dataset (records, fields);
- the go/no-go result;
- sample QA numbers;
- batches released (dates, URL counts, sitemap files);
- paid units spent;
- unverified items;
- the next re-check date (the per-batch indexing check, 2–4 weeks).
