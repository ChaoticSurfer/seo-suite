---
name: seo-content
description: Content strategy and quality across many pages. Content audits (keep, update, merge, redirect, delete), decay, cannibalisation, SERP-based briefs, writing or refreshing one article with E-E-A-T, helpful-content checks, safe AI writing. Not for one page's tags (seo-onpage), keyword discovery (seo-keywords) or blog batches (seo-blog-builder).
---

# Content: audit, briefs, writing, refreshes

Decide what each page should become and write content that earns the click.

## When to use / not
- **Use:**
  - a content inventory (10+ URLs);
  - decaying or competing pages;
  - a brief or article for a chosen topic;
  - an E-E-A-T or helpful-content review.
- **Not:**
  - one page's title/meta/links → `seo-onpage`;
  - choosing topics → `seo-keywords`;
  - a keyword-driven batch of blog posts or a content calendar → `seo-blog-builder` ("write an SEO blog post" on one
    topic the user chose stays here);
  - thousands of templated pages → `seo-programmatic`.

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Sections in scope | Sitemap URL count and path prefixes. Up to 2,000 URLs: all of them. Above that: section crawls (`--path-prefix`) in parallel subagents | Every indexable content section |
| Business-critical pages | Navigation; pages with forms, cart, checkout, booking or pricing; Product/Service schema | Treat those as Keep until the data says otherwise |
| GSC exports, last 3 months and the same period a year earlier: Pages, Queries, and a query+page export (API or Looker Studio, needed for cannibalisation) | A connector, or exports in `seo-work/` | **Ask — batched at the end.** Meanwhile build the inventory from the crawl, leave traffic columns `[needs data]`, and mark traffic-based decisions provisional |
| GA4 landing-page sessions and conversions | A connector or an export | **Ask — batched at the end.** Conversions `[needs data]` |
| Brief/article: target query and locale | The request; the research store's clusters (`next-topics`); `seo-work/keywords.csv`; GSC; locale from `<html lang>`, ccTLD, hreflang, currency | The copy's language and its main country |
| Brief/article: audience and brand voice | The site's top pages and About page; the SERP's dominant angle | Match the site's highest-traffic pages |
| Brief/article: author and their real credentials or experience | Bylines, author pages and the About page | **Ask — batched at the end.** Recommend the most relevant existing author; until then the byline is `[needs data]`. Never invent one |
| Brief/article: facts or data the business owns | Case studies, pricing, stats and product pages on the site | `[needs data]`, listed in the end-of-run requests |

## Workflow
**0. Read the research store first** (`seo-research/`, `${CLAUDE_PLUGIN_ROOT}/references/research-store.md`):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export keywords --locale en --format json > seo-work/store-keywords-en.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" next-topics --locale en --limit 10 > seo-work/store-topics-en.json
```
- **No store yet:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" init --site "$SITE" --locales en`, with
  every locale the site publishes, default first. With no topic given and no clusters stored, run `seo-keywords` first.
- **Publishing mode:** `publishing` in `store-status.json` decides whether a written page needs a human sign-off before
  it goes live (C step 6).
- **Audit (A):** still crawl and pull both GSC periods, because the store keeps neither link depth nor an earlier
  period. Keywords whose `demand.gsc_pages` lists 2+ URLs are early cannibalisation candidates, while that list's own
  `provenance` date is within the `gsc` TTL (research-store §6). The store lists a page by its own rule
  (research-store §2: 10+ impressions, 10% of the query's, position 20 or better, never a home page), not by
  `gsc_analyze.py`'s. So step 4 still works from `gsc_qp.json`.
- **Brief (B):** with no topic given, take it from `next-topics`. Reuse the cluster's SERP snapshot
  (`seo-research/serps/<locale>/<sha1 of the head keyword>.json`: page types, features, PAA) unless it is missing or
  older than the `serps` TTL in `manifest.json`; only then WebSearch it. The cluster's keywords are the secondary
  queries, and its `interlinks` are the sibling links.

### A. Content audit and inventory
1. **Collect evidence in parallel:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sitemap_check.py" "$SITE" --sample 0 --urls-out seo-work/urls.txt > seo-work/sitemap.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crawl.py" "$SITE" --max-pages 2000 --sitemap-urls seo-work/urls.txt --csv seo-work/pages.csv > seo-work/crawl.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gsc_analyze.py" seo-work/gsc_pages_now.csv --compare seo-work/gsc_pages_prev.csv > seo-work/gsc_pages.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gsc_analyze.py" seo-work/gsc_query_page.csv > seo-work/gsc_qp.json
   ```
2. **Build the inventory** `seo-work/content-inventory.csv` by joining `pages.csv` with the GSC Pages rows on URL.
   - Columns: `url, title, word_count, inlinks, depth, indexable, issues, clicks, impressions, position, clicks_prev, last_updated, decision, reason`.
   - The join is a few lines of Python. Get `last_updated` from `dateModified` in `page_audit.py URL --facts` (`facts.json_ld`) on a sample, or from the CMS export.
3. **Apply the decision tree** (Checks), then review edge cases by hand: high-converting pages, legal pages, brand pages.
4. **Cannibalisation:** use `gsc_qp.json → cannibalization`. For each query where two or more of your URLs each hold at least 10% of impressions, choose one owner page and one action: merge+301, differentiate intent, or re-link.
5. **Decay:** use `period_comparison.losers` and `likely_cause`. "rankings dropped" means refresh or upgrade the content. "fewer impressions at similar rank" means demand or the SERP changed, so don't rewrite. "CTR fell" means work on the snippet, title or SERP features.
6. **Prioritise:** run `triage.py seo-work/crawl.json`, then rank refreshes by clicks lost and by business value.

### B. Content brief
1. WebSearch the query in its locale and record:
   - the top 10 results' page types, angles and freshness;
   - People Also Ask and related searches;
   - SERP features, including any AI Overview.
2. Run `compare_pages.py <your-url> <top 3–5 URLs> --keyword "$KW"` and use `content_gap_phrases`
   (subtopics competitors share that your page lacks); competitor headings give structure.
   - With no page yet, run `compare_pages.py --no-own-page <top 3–5 URLs> --keyword "$KW"` and use
     `shared_competitor_phrases`.
3. **Write the brief:**
   - search intent and the reader's job-to-be-done;
   - primary and secondary queries;
   - 3 title options;
   - an H2/H3 outline mapped to sub-questions;
   - the answer-first intro;
   - what you'll add that others lack: original data, first-hand testing, expert quotes, tools, examples;
   - sources to cite;
   - internal links in and out;
   - schema type (hand off to `seo-schema`);
   - media needs;
   - author, plus a reviewer for YMYL topics.
   - Length isn't a target; scope is.

### C. Writing or refreshing
1. Write from the brief. Use only facts the user supplied, citable sources, or data you measured. Mark anything else `[needs data]`.
2. Fact-check every claim, number, date and name. Models don't retrieve facts (google-rules §4).
3. Add trust signals:
   - a byline linked to an author page (real person, real credentials);
   - published and updated dates that reflect real changes;
   - citations to primary sources;
   - first-hand evidence (photos, screenshots, data, process).
4. **For a refresh:**
   - keep the URL;
   - keep the sections that earn the queries already in GSC;
   - update facts;
   - add the missing subtopics;
   - change `dateModified` only for substantive edits.
5. Score the page with `content_score.py --file page.html --base-url https://site/<planned-slug> --keyword "$KW"` and fix the placement and structure gaps.
   - A post kept as data (a locale translation file keyed by slug, a table export row with HTML in a column, a TS dictionary rendered to JSON) is scored from its entry: `content_score.py --file lib/i18n/content/blog/ka.json --key "$SLUG" --fields title,excerpt,content --base-url https://site/ka/blog/<slug>/ --keyword "$KW"`. The first title field counts as the `<title>` and H1, the first excerpt or description field as the meta description (`seo-blog-review` step 4).
   - Ship such a post the way `seo-blog-builder` step 4 delivers it: the locale JSON entries in a PR, and the source row through the project's own write path, never through database credentials.
6. **Ship it per autonomy level (references/autonomy.md):** a file in `seo-work/` at level 1, a branch and PR at level 2, merged once CI passes at level 3, published through an authorised CMS connector at level 4. What level 3 merges and level 4 publishes follows the project's publishing mode (`publishing` in the step 0 `status` output, research-store §2), with the gates of `seo-blog-builder`'s Checks:
   - **`automatic`:** an AI-written page goes live as soon as every automated gate there passes (no P0 or P1, every claim sourced, no open marker). Record the review state as `review_state: llm_reviewed`, never in `reviewed_by`.
   - **`review`:** only a page with a named human sign-off (`reviewed_by`, `reviewed_at`). Without it the PR stays open, the page stays `drafted`, and the report asks for the sign-off.
   - **`unset`:** as `review`, plus the one mode question in the end-of-run batch (autonomy.md). Never ask it mid-run.
   - Either way, a page with an open `[needs data]` marker stays unpublished until it is filled. Below the level an action needs, stop there and say which level or credential would finish it.
7. **Once it is live** (level 3 and above): check it with `page_audit.py` (status 200, indexable), submit its URL to IndexNow when the site serves its key file, and set its store status (D). Re-check its GSC position 6–8 weeks later (Log the work).

### D. Write back to the store
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest crawl seo-work/pages.csv
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest gsc seo-work/gsc_query_page.csv --as-of "$PERIOD_END"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" set-status --cluster en-003 --status briefed
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" set-status --cluster en-003 --status published --url https://example.com/blog/post/
```
- **Audit:** ingest the crawl and the current-period GSC CSVs, each with `--as-of` set to the last day its period
  covers (`$PERIOD_END`). Without it the store dates a file by its modification time, so a year-earlier export saved
  later would replace the current values: skip that export, or give it its own `--as-of`.
- **Brief:** save it as `seo-research/briefs/<locale>/<slug>.md` (the `brief` path `next-topics` gives), then set
  the cluster to `briefed`. A SERP you fetched in B step 1 goes back with `ingest serps`, in the two files
  `seo-serp-researcher` writes.
- **Written or refreshed:** `drafted` (written, not yet live), with `--url` set to its planned URL, once the file or
  PR exists; `scheduled` with `--url` once it is queued for a future publish date; `published` with `--url` once it
  is live. A query with no cluster uses `--keyword "$KW" --locale en` instead of `--cluster`.

## Checks
**Decision tree** (thresholds are heuristics; adjust to the site's scale):
- **Keep:** the page earns clicks, conversions or links, or is required (legal, support).
- **Update:**
  - impressions stable or up but position 4–20 (striking distance); or
  - clicks down more than 30% year on year with `likely_cause = rankings dropped`; or
  - facts older than about 12–18 months on a time-sensitive topic.
- **Merge:** two or more pages on the same intent (cannibalisation, or an exact `duplicate-content` hash in the crawl). Merge into the stronger URL and 301 the rest.
- **Redirect (301):** obsolete, but has links or traffic and there is a close replacement.
- **Delete (404/410):** zero clicks for 12 months, no backlinks, and no replacement. Google treats 404 and 410 the same (google-rules §1).
- **Noindex:** only for pages users need but searchers don't (e.g. thin tag pages). Not as a crawl-budget tool (google-rules §1).

**Helpful content** (google-rules §4)
- Original information or analysis.
- Complete coverage.
- Headings that aren't exaggerated.
- A clear who/how/why.
- No easily checked errors.
- Not made mainly to rank.

**E-E-A-T** (google-rules §4)
- Trust matters most.
- YMYL topics need visible expertise and review.
- Fake authors or AI-generated headshots are deceptive.

**AI-assisted content** (google-rules §4)
- Allowed when it meets Search Essentials.
- Mass pages without added value are scaled content abuse.
- Disclose automation where readers would reasonably wonder.
- Review AI-written titles, meta descriptions, schema and alt text.

**Spam boundaries** (google-rules §4)
- Site reputation abuse: hosting third-party content to exploit the host's ranking signals. In the EEA since 2026-08-28, such pages are ranked separately rather than given a manual action.
- Expired domain abuse.
- Faking freshness (changing dates without changes).
- Keyword stuffing.
- Back-button hijacking.

**Readability:** match the audience. `flesch_reading_ease` is English-only, and roughly 60–70 means plain English [heuristic]. Short paragraphs; lists and tables where they help scanning.

**Answer passages:** 40–80-word self-contained answers under question H2s help snippets and AI answers [heuristic, google-rules §10]. "Chunking for AI" is not required.

## Data: free vs paid
**The free path covers:**
- inventory (crawl);
- performance and decay (GSC exports, 16 months);
- cannibalisation (query+page export);
- competitor structure and gaps (`compare_pages`, WebSearch);
- question mining (PAA via WebSearch, `keyword_ideas.py`).

**What paid tools add (never required):**
- **Ahrefs / Semrush:** backlinks per URL, which is the decisive input for redirect-vs-delete decisions. The free alternatives are the GSC Links export and Ahrefs Webmaster Tools for your own verified site. They also give per-page keyword sets beyond GSC's top rows and competitors' top pages for gap finding. Pull only "top pages" and "referring domains per URL" for in-scope sections (tools-paid.md `## Ahrefs`, `## Semrush`).
- **Screaming Frog:** content extraction (custom XPath for dates and authors) across thousands of URLs, and near-duplicate detection (tools-paid.md `## Screaming Frog`).
- **AlsoAsked / AnswerThePublic:** structured question trees for briefs (tools-paid.md `## Other paid tools`).

Volumes and difficulty without data are always `[needs data]`.

## Output
- `content-inventory.csv` with a decision and reason per URL.
- `content-audit.md`:
  - summary counts per decision;
  - top 10 refreshes by clicks at stake;
  - merge groups with the chosen owner URL;
  - the redirect map, to verify with `seo-migration` / `redirect_check.py`;
  - risks.
- Briefs: `seo-research/briefs/<locale>/<slug>.md`.
- Pages: `<slug>.md` or HTML in `seo-work/` at level 1, a PR at level 2, merged at level 3, or published through the CMS connector at level 4, with the live URL and its submission.
- **Assumptions** (in `content-audit.md` or the brief): the scope, critical pages, locale, audience and voice chosen, with the evidence for each; which store data was reused and how old it was. Then the requests batched at the end, each with a recommendation: missing access (GSC, GA4, backlinks) and business decisions (merging or deleting pages that earn traffic or revenue, the byline).

## Pitfalls & myths
- Deleting low-traffic pages en masse "to boost quality": prune only with evidence. Some low-traffic pages convert or attract links.
- Updating dates without real changes is faking freshness (google-rules §4).
- Merging without 301s, or redirecting everything to the homepage, loses the signals. Google treats a mass homepage redirect as a soft 404.
- Length targets ("2,000+ words") don't make content helpful.
- Duplicate content is usually not a penalty; it's a canonicalisation choice. It's only spam when it's scraped or scaled.
- A traffic drop with stable rankings is not a content problem. Check SERP features and demand first.

## Log the work
Append an entry to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`. Include:
- the scope (sections, URL count) and the GSC date ranges;
- the scripts run;
- any paid units spent;
- the counts per decision;
- what was changed or published, and at which autonomy level;
- unverified items (e.g. backlinks unknown);
- a re-check date (6–8 weeks after merges or refreshes).
