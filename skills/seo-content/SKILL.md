---
name: seo-content
description: Content strategy and quality across many pages. Covers content audits and inventories (keep/update/merge/redirect/delete), content decay, keyword cannibalisation, SERP-derived content briefs, writing or refreshing articles with E-E-A-T signals, helpful-content self-assessment, and safe use of AI writing. Triggers include "content audit", "which pages should we prune", "traffic decaying on old posts", "two pages competing for the same keyword", "write a content brief for X", "refresh this article", "write an SEO blog post", "is our content helpful", "E-E-A-T review" and "can we use AI for content". It is not for a single page's tags (seo-onpage), keyword discovery and clustering (seo-keywords), template-generated page sets (seo-programmatic), or technical crawl issues (seo-technical).
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
  - thousands of templated pages → `seo-programmatic`.

## Inputs to gather (ask only for what's missing)
1. Site URL, and sections in or out of scope.
2. **GSC exports, last 3 months and the same period a year earlier:**
   - Pages report;
   - Queries report;
   - a query+page export (API or Looker Studio), which is needed for cannibalisation.
3. Optional: GA4 landing-page sessions and conversions; a list of business-critical pages.
4. For briefs or articles: the target query and locale, the audience, the author and their real credentials or experience, the brand voice, and facts or data the business owns.

## Workflow
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
   - The join is a few lines of Python. Get `last_updated` from visible or schema dates via `content_score.py` on a sample.
3. **Apply the decision tree** (Checks), then review edge cases by hand: high-converting pages, legal pages, brand pages.
4. **Cannibalisation:** use `gsc_qp.json → cannibalization`. For each query where two or more of your URLs each hold at least 10% of impressions, choose one owner page and one action: merge+301, differentiate intent, or re-link.
5. **Decay:** use `period_comparison.losers` and `likely_cause`. "rankings dropped" means refresh or upgrade the content. "fewer impressions at similar rank" means demand or the SERP changed, so don't rewrite. "CTR fell" means work on the snippet, title or SERP features.
6. **Prioritise:** run `triage.py seo-work/crawl.json`, then rank refreshes by clicks lost and by business value.

### B. Content brief
1. WebSearch the query in its locale and record:
   - the top 10 results' page types, angles and freshness;
   - People Also Ask and related searches;
   - SERP features, including any AI Overview.
2. Run `compare_pages.py <your-or-placeholder-url> <top 3–5 URLs> --keyword "$KW"`.
   - `content_gap_phrases` gives subtopics competitors share; competitor headings give structure.
   - With no page yet, put the strongest competitor first and read the gap the other way round.
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
1. Draft from the brief. Use only facts the user supplied, citable sources, or data you measured. Mark anything else `[needs data]`.
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
5. Score the draft with `content_score.py --file draft.html --keyword "$KW"` and fix the placement and structure gaps.
6. Deliver as a file or diff. **Never publish to the CMS without explicit approval.**

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
- **Ahrefs / Semrush:** backlinks per URL, which is the decisive input for redirect-vs-delete decisions. The free alternatives are the GSC Links export and Ahrefs Webmaster Tools for your own verified site. They also give per-page keyword sets beyond GSC's top rows and competitors' top pages for gap finding. Pull only "top pages" and "referring domains per URL" for in-scope sections (tools.md `## Ahrefs`, `## Semrush`).
- **Screaming Frog:** content extraction (custom XPath for dates and authors) across thousands of URLs, and near-duplicate detection (tools.md `## Screaming Frog`).
- **AlsoAsked / AnswerThePublic:** structured question trees for briefs (tools.md `## Other paid tools`).

Volumes and difficulty without data are always `[needs data]`.

## Output
- `content-inventory.csv` with a decision and reason per URL.
- `content-audit.md`:
  - summary counts per decision;
  - top 10 refreshes by clicks at stake;
  - merge groups with the chosen owner URL;
  - the redirect map, to verify with `seo-migration` / `redirect_check.py`;
  - risks.
- Briefs: `brief-<slug>.md`.
- Drafts: `draft-<slug>.md` or HTML, as a diff for repo content.

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
- what was changed or published (with approval);
- unverified items (e.g. backlinks unknown);
- a re-check date (6–8 weeks after merges or refreshes).
