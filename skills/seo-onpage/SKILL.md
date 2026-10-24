---
name: seo-onpage
description: Optimise one page (or one page template) for a target query, covering the title link, meta description, H1/H2 outline, an answer-first intro, internal links in and out, image alt text and filenames, and a check that the page type matches search intent. Triggers include "optimise this page for X", "improve the title and meta", "on-page SEO for /pricing", "why doesn't this page rank for X", "rewrite my H1", "page-level SEO review" and "fix the SEO on this template/component". It works on a live URL, a saved or rendered HTML file, or the page's source in the codebase (shown as diffs). It is not for whole-site audits (seo-audit / seo-technical), content inventories or briefs (seo-content), keyword discovery (seo-keywords), JSON-LD writing (seo-schema) or AI-answer citations (seo-ai-search).
---

# On-page optimisation

Get one page into the best shape for one primary query and its close variants. Start from measured facts, then use judgement.

## When to use / not
- **Use:** a single URL or template, with one primary query (plus 2–5 secondaries) in mind.
- **Not:** sitewide issues → `seo-technical`. Several pages competing for one query → `seo-content` (cannibalisation). No keyword chosen yet → `seo-keywords` first.

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Page | The URL or file/component path in the request. Given only a site: the URL that ranks for the query (GSC, or WebSearch `site:domain.com "<query>"`) | The money page whose title/H1 best matches the query |
| Primary query + 2–5 secondaries | The page's GSC queries by clicks, then impressions; else the title/H1 topic, checked against autocomplete and People Also Ask | The H1's head term |
| Country and language (localises the SERP check) | `<html lang>`, ccTLD, hreflang, currency, addresses | The copy's language and its main country |
| Brand suffix for titles | The suffix repeated after the delimiter in the site's titles (crawl CSV), `og:site_name`, WebSite schema | `og:site_name`, else the domain name |
| GSC export for this page (queries, clicks, impressions, position) | A connector, or an export in `seo-work/`. It shows what the page already ranks for: never rewrite away from queries that already bring clicks | **Ask — batched at the end.** Carry on without it |

## Workflow
1. **Collect evidence in parallel** (independent runs; write JSON to `seo-work/`):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_audit.py" "$URL" --facts > seo-work/page.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/content_score.py" "$URL" --keyword "$KW" > seo-work/content.json
   ```
   For a local or rendered file, use `--file page.html --base-url "$URL"` on either script.
   - If `page.json` shows `bot-challenge`, stop that step. Never try to get around the challenge. Record an access request for the end of the run (a copy of the rendered page saved from a browser, to re-run with `--file`), and carry on with the steps that don't need the page.
   - If it shows `likely-client-rendered`, capture the rendered DOM (in the built-in browser, run `document.documentElement.outerHTML` and save it). Then run `render_diff.py "$URL" --rendered dom.html` and report what exists only after JavaScript.
2. **Check the SERP intent.** WebSearch the primary query in the target locale and record the top 10 results:
   - page type (guide, listicle, product, category, tool, local pack, video, forum);
   - angle (beginner, comparison, price, "near me");
   - freshness;
   - SERP features (AI Overview, People Also Ask, video, local pack, shopping).

   If most of the top results are a different page type from yours, say so first. Polishing the wrong type of page rarely works [measured: SERP sample].
3. **Benchmark against competitors** (optional but recommended). Run `compare_pages.py "$URL" <top 3–5 organic URLs> --keyword "$KW" > seo-work/compare.json`. Use `content_gap_phrases` to find subtopics you are missing. Ignore `median_competitor_words` as a target, because length is not a ranking factor (google-rules §4).
4. **Find internal link sources:**
   - If a crawl CSV exists (`crawl.py … --csv`), pick 3–8 relevant indexable pages with high `inlinks`, low `depth`, and topical overlap in title or URL.
   - Otherwise run a WebSearch for `site:domain.com "<topic>"` and use the results.
   - For each source, suggest the exact sentence and anchor where the link goes.
5. **Write the recommendations** (the Checks below).
6. **Present everything as one before/after table.** Apply changes only per autonomy level (references/autonomy.md):
   - In code mode, show a unified diff of the template or component. Commit it on a branch and open a PR only at level 2 or above.
   - Change CMS content only at level 4, through an authorised connector.
7. **Re-run** `page_audit.py` on the changed page (or the local build) and show the finding delta.

## Checks
**Title link** (google-rules §3)
- Google sets no length limit; titles are truncated by width.
- Write **3 options**, each with an estimated pixel width. Get the widths from `title_pixel_width` in `seo_lib.py` (the `title_px` value in page.json). Target roughly 600 px or less as an estimate, not a rule [estimate].
- Put the primary topic first, then a qualifier (year only if the content truly changes, audience, format, location), then the brand after a delimiter.
- Avoid what triggers rewrites:
  - near-empty titles;
  - boilerplate shared across similar pages;
  - a mismatch with the H1;
  - stale dates;
  - the site name duplicated.

**Meta description** (google-rules §3)
- Google sets no length limit.
- Unique per page, with concrete facts (price, date, location, format) and no keyword lists.
- Around 150–160 characters shows fully on desktop [estimate].
- Google may still use page text instead.

**H1 and outline**
- One dominant visible H1 that matches the title topic.
- H2s map to the sub-questions found in the SERP (People Also Ask, competitor headings).
- Keep heading levels sequential. That's a convention for readability; Google has no numeric rule (google-rules §3).

**Intro, answer first**
- The first paragraph directly answers the main query in 40–80 words (`content_score` reports `first_paragraph_words`).
- Self-contained passages are what snippets and AI answers lift [heuristic, google-rules §10].
- Keep key content visible, not hidden in tabs or behind clicks.

**Keyword placement** (`content_score.placement`)
- The topic should appear in the title, the H1 and the first 100 words.
- Use natural variants, not exact-match repetition.
- `per_1000_words` is informational only. There is no target density, and keyword stuffing is spam (google-rules §4).

**Internal links**
- Every important page needs at least 1 contextual inlink (google-rules §3). Aim for at least 3 from relevant pages [heuristic].
- Use descriptive anchors (`anchor-generic` and `anchor-empty` findings).
- No `rel=nofollow` on internal links.
- Outbound: link to 1–3 genuinely useful sources for claims [heuristic].

**Images** (google-rules §3)
- Descriptive `alt`; empty `alt=""` for decorative images.
- Descriptive filenames that use hyphens.
- `width` and `height` set.
- The hero/LCP image is not `loading=lazy` and has `fetchpriority=high` (`lcp-lazy` finding).
- Use WebP/AVIF with `srcset`. CSS background images are not indexed.

**URL**
- Short, readable, hyphenated, lowercase.
- Change a URL only with a 301 and a strong reason. Hand off to `seo-migration` for redirect checks.

**Indexability blockers come first:** `noindex`, `canonical-elsewhere`, `canonical-multiple`, `http-error`. These outrank every copy fix.

**Structured data:** list the types the page type warrants (Article, Product, LocalBusiness, BreadcrumbList…) and hand off to `seo-schema`.

**Social:** `og:title`, `og:description`, and `og:image` at 1200×630 [convention].

## Data: free vs paid
**The free path covers:**
- on-page facts and placement (the scripts);
- SERP page types and features (WebSearch);
- what the page already ranks for (GSC export);
- internal link candidates (crawl CSV).

**What paid tools add (never required):**
- **Semrush / Ahrefs:** every keyword this URL ranks for, with estimated volume and position history, beyond GSC's top rows and 16-month window. They also give competitor URLs' keyword sets. Pull one URL's organic keywords report and cap the rows (see tools.md `## Semrush` / `## Ahrefs`).
- **DataForSEO SERP API:** localised SERP snapshots at scale, when WebSearch can't pin the country or device. It's pay-per-call; see tools.md `## DataForSEO`.
- **Screaming Frog:** rendered-DOM audits of many templates at once (tools.md `## Screaming Frog`).

Volume and difficulty without data are always `[needs data]`.

## Output
Write `seo-work/onpage-<slug>.md` containing:
1. A verdict line: is the intent match correct, and is anything blocking indexing?
2. A **before/after table** with columns Element | Current | Recommended | Why | Evidence tag.
   - Rows: title (3 options with px), meta description, H1, H2 outline, intro, internal links in (source page → anchor → sentence), links out, images, schema hand-off, URL.
3. Remaining `page_audit` findings, ranked by running `triage.py seo-work/page.json`.
4. What was not verified (e.g. rendered DOM not captured, no GSC data).
5. **Assumptions:** the page, queries, locale and brand suffix chosen, with the evidence for each. Then the requests batched at the end (missing access, and what each would add), each with a recommendation.

## Pitfalls & myths
- "Titles must be 50–60 characters" and "meta must be 155": these are tool conventions. Google truncates by width and has no limit.
- Word-count targets are not a ranking factor. Match intent and depth.
- "LSI keywords" are not a Google concept. Cover subtopics because searchers need them.
- Changing a title that already earns clicks can lose them. Check GSC first, change one element at a time, then wait at least 4 weeks after re-crawl before judging, comparing against unchanged control pages (seo-analytics §D) [heuristic].
- `meta keywords` is ignored by Google.
- A JavaScript-injected title or canonical that differs from the raw HTML sends conflicting signals; fix it at the template.
- Don't invent facts in copy or schema (prices, ratings, credentials). Use only what's on the page or what the user provides.

## Log the work
Append an entry to `SEO-WORKLOG.md` in the project root using `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`. Include:
- the page and the query;
- the scripts run and the SERP sample date;
- any paid units spent;
- what changed (or what was proposed);
- unverified items;
- a re-check date (GSC check 4 weeks after deployment).
