---
name: seo-audit
description: Full SEO audit orchestrator for a whole site or a single page, run on measured evidence. Use when the user says "audit my site", "SEO audit", "site health check", "why isn't my site ranking", "check my website for SEO issues", "technical + content audit", "give me an SEO fix list", or "quick SEO check of this URL". It runs the robots, sitemap, crawl, PageSpeed, page and render checks, turns every finding into a P0–P3 plan with triage.py, groups issues by template, and offers to fix code in repo-backed sites. Not for a deep dive on one area: use seo-technical (crawling, rendering, CWV, framework code), seo-onpage (one page's copy and tags), seo-content, seo-keywords, seo-links, seo-migration (site moves), seo-international (hreflang), seo-local, seo-ecommerce, seo-ai-search, or seo-analytics (traffic drops, GSC data).
---

# SEO Audit

A site-wide audit built on measured evidence that ends in a P0–P3 fix plan. Each issue is fixed once, in the template that produces it.

## When to use / not

- **Use for:**
  - The first look at any site.
  - A periodic health check (quarterly).
  - Before or after a redesign.
  - "Rank higher" requests where the cause is unknown.
  - A one-URL quick audit.
- **Not for:**
  - A traffic drop with a date attached: use **seo-analytics** first, then come back here.
  - A planned domain or URL change: use **seo-migration**.
  - Writing or rewriting copy: use **seo-onpage** or **seo-content**.

## Inputs: decide, don't ask

Decide each input from evidence, record it under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Start URL and canonical host (www vs non-www, https) | The URL given; the final URL after redirects in `home.json` | The URL as given |
| Business goal and the 3–5 money pages or templates (home, category, product/service, article, location) | Navigation; pages with forms, cart, checkout, booking or pricing; Product/Service/LocalBusiness schema; GSC top pages | Home plus one page per template |
| Site size (sets `--max-pages`) | `total_urls` in `sitemap.json` | 300; above 2,000, crawl in sections |
| Repo | The site's code in this workspace: fixes become diffs | No repo: list each fix, and ask for repo or CMS connector access, batched at the end, naming the fixes it would let the run ship |
| Free exports: Search Console Performance (Queries.csv and Pages.csv, last 3 months plus the previous period), Bing Webmaster, server logs, a `PSI_API_KEY` | What's configured or already in the workspace | Run without them. Ask — batched at the end, naming what each adds |
| Paid tools (Semrush, Ahrefs, Screaming Frog licence) | Only what's already configured, within the paid-data budget | None; never required |

## Workflow

Use a working folder `seo-work/<host>-<YYYYMMDD>/`, in the project or the scratchpad. `S="${CLAUDE_PLUGIN_ROOT}/scripts"`.

0. **Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`), when `seo-research/` exists:
   ```bash
   mkdir -p seo-work
   python3 "$S/research_store.py" status > seo-work/store-status.json
   python3 "$S/research_store.py" export inventory --format csv > seo-work/store-inventory.csv
   ```
   - Start the Inputs from `seo-research/site.json` (`money_pages`, `templates`, `stack`, `locales`, `markets`) and check each against the site. The site wins.
   - The inventory's `gsc_clicks` stand in for the GSC top pages when picking money pages, on rows whose `gsc_at` is within the 7-day `gsc` TTL (research-store §6).
   - The crawl and page checks still run: an audit measures the site as it is today, and the store keeps the page list, not the findings.
   - Note what you reused and its age for *Assumptions* and the work log.
1. **Access gate (run these three in parallel; they are independent):**
   ```bash
   python3 "$S/robots_check.py" https://example.com --path / --path /blog/ > seo-work/robots.json
   python3 "$S/sitemap_check.py" https://example.com --sample 50 --urls-out seo-work/sitemap-urls.txt > seo-work/sitemap.json
   python3 "$S/page_audit.py" https://example.com/ > seo-work/home.json
   ```
   **Stop if the homepage can't be fetched.** If `page_audit.py` exits 2 (`home.json` has an `error` key, or a `fetch-failed` finding), stop. Report it as P0: the site is unreachable (DNS/TLS/timeout/redirect loop), quoting the `error` text.

   **Stop fetching on a bot challenge.** If `home.json` contains `bot-challenge`, skip the crawl and page checks on that host and finish the report from what came back. Report it as P0: the CDN/WAF is challenging automated clients. Add an access request, batched at the end, to either:
   - allow verified bots and the answer-engine crawlers they want, or
   - save the rendered page from the built-in browser so the audit can continue with `--file`.

   Never try to bypass a challenge or CAPTCHA.
2. **Crawl.** Note `hit_page_limit` in the results. If it's true, the orphan and depth findings are partial; say so.
   ```bash
   python3 "$S/crawl.py" https://example.com --max-pages 300 --sitemap-urls seo-work/sitemap-urls.txt --csv seo-work/pages.csv > seo-work/crawl.json
   ```
   For sites over 2,000 URLs, crawl in sections with parallel subagents. Give each one a section start URL with the matching `--path-prefix`, e.g. `crawl.py https://example.com/blog/ --path-prefix /blog/ --max-pages N`, then merge their findings.
3. **Find the templates.** Group `pages.csv` rows by URL pattern (first path segment plus depth). Pick one representative per template, plus the money pages.
4. **Per-template evidence** (run in parallel, one process per URL):
   ```bash
   python3 "$S/page_audit.py" URL > seo-work/page-<template>.json
   python3 "$S/psi.py" URL --strategy mobile > seo-work/psi-<template>.json
   ```
   **PSI quota:** if PSI returns 429, continue without it and add a free key (how to get one is in the `hint` field) to the access requests batched at the end. Field data is `field_url` / `field_origin`; `null` means CrUX has too little traffic, so fall back to lab data.
5. **JavaScript sites.** This step applies if a page has `likely-client-rendered`, an SPA framework, or very few links.
   1. Open the URL in the built-in browser.
   2. Run `document.documentElement.outerHTML` and save the result as `seo-work/rendered-<template>.html`.
   3. Run the diff:
      ```bash
      python3 "$S/render_diff.py" URL --rendered seo-work/rendered-<template>.html > seo-work/render-<template>.json
      ```
   4. Also run `page_audit.py --file seo-work/rendered-<template>.html --base-url URL` to audit what users actually see.
6. **Search data, if exports were provided.**
   ```bash
   python3 "$S/gsc_analyze.py" Queries.csv --brand "brandname" > seo-work/gsc.json
   ```
   Add `--compare previous.csv` when they gave two periods.
7. **Triage.** `triage.py` ranks findings from every script that emits them: crawl, robots, sitemap, page audit, PSI (`cwv-fail`), render_diff (`js-dependent-seo`) and redirect_check (`redirect-map-failure`).
   ```bash
   python3 "$S/triage.py" seo-work/crawl.json seo-work/robots.json seo-work/sitemap.json seo-work/page-*.json seo-work/psi-*.json > seo-work/triage.json
   ```
   If step 5 ran, append `seo-work/render-*.json`.
   - Check `unmapped_findings`; rank any by hand with the same impact rules and say so.
   - Raise `cwv-fail` on a money template one level (P2 → P1): the table can't know which templates earn revenue.
8. **Judgement pass.** Scripts can't measure these, so judge them yourself and tag each one `[estimate]`:
   - Search intent match on the money pages.
   - Thin or duplicate templates.
   - E-E-A-T and trust (google-rules §4).
   - Internal linking toward the money pages.
   - Structured data matches the visible content.
9. **Fix in the template, not the page.** Use `page_issue_summary` (finding → page count) to say "1 template fix = N pages". In a repo:
   - Locate the template or layout file.
   - Show a diff, and apply it per autonomy level (references/autonomy.md).
   - Re-run `page_audit.py` afterwards to prove the fix.
10. **Write the results back to the research store:**
    ```bash
    python3 "$S/research_store.py" init --site https://example.com --locales en,ka
    python3 "$S/research_store.py" ingest crawl seo-work/pages.csv
    python3 "$S/research_store.py" ingest gsc Pages.csv --as-of "$PERIOD_END"
    ```
    - `init` creates the store (the locales found, default first), adds new locales, and refuses another domain. If it refuses, this site isn't the store's: skip the ingests.
    - Ingest every section's `pages.csv` for a sectioned crawl, and only the current GSC period, not the comparison one. Give it `--as-of` set to the last day its period covers (`$PERIOD_END`). Without it the store dates the file by when it was saved, so a newer period ingested later with `--as-of` counts as older and is refused. Keep the GSC `Pages.csv` out of `seo-work/`: on a case-insensitive disk (the macOS default) it overwrites the crawl's `pages.csv`. `Queries.csv` has no page column, so on a store with more than one locale ingest it only with the `--locale` its queries are in.
    - Record the money pages, templates and stack you decided in `seo-research/site.json` (`money_pages`, `templates`, `stack`), with their evidence in `assumptions`.
11. **Write the report and the work log** (see below).

**Quick audit mode (one URL, about 5 minutes).** Run `page_audit.py`, `psi.py` and `robots_check.py` on that URL in parallel. Add `render_diff` if it's a JS site. Apply the step 1 stop checks to the `page_audit.py` output. Then run `triage.py` on the JSONs and report the top 10 issues with fixes. State clearly that site-wide issues (duplicates, orphans, depth, sitemap) were not checked.

## Checks

Thresholds follow google-rules. Anything not from Google is labelled.

- **Indexability:**
  - Googlebot is allowed by robots.txt.
  - robots.txt returns 200/404, never 5xx or 429. Google pauses crawling 12 h after one, then uses its cached copy for up to 30 days (§1).
  - Pages return 200.
  - No accidental `noindex`.
  - Exactly one canonical tag, absolute and in `<head>`.
  - The canonical target is 200 and indexable (§1).
- **Size:** HTML under 2 MB uncompressed. Googlebot for Search indexes only the first 2 MB (§1).
- **Redirects:** one hop, 301/308. Google follows at most 10 hops; aim for ≤3 in a move (§1, §9).
- **Error pages:**
  - Missing URLs return 404 or 410. Google treats them the same (§1).
  - The soft-404 probe in `crawl.py` must get a 4xx (404/410 preferred; not 429).
- **Sitemaps:**
  - Only final, 200, canonical, indexable URLs.
  - ≤50k URLs and ≤50 MB per file.
  - `lastmod` real and not uniform. `priority`/`changefreq` are ignored (§1).
- **Rendering:** primary content and `<a href>` links are in the raw HTML. Most AI crawlers don't run JS (§1, §10).
- **Core Web Vitals:** p75 field data, LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1. A page passes only if all three are good (§2).
- **Mobile:** viewport set; mobile content and structured data match desktop (§2).
- **Titles and headings:**
  - A unique, descriptive title on every page. Google has no character limit and truncates by width (§3).
  - One dominant h1 (§3).
  - Using ~600 px as a target is a convention.
- **Internal linking:**
  - Every important page linked at least once (§3).
  - ≤3 clicks deep: heuristic.
- **Structured data:**
  - Valid JSON-LD that matches visible content (§5).
  - FAQ rich results are retired (2026-05-07), as are HowTo and the sitelinks search box. Don't recommend adding them for Google (§5).
- **Duplicates:** no duplicate titles, descriptions or body content across indexable URLs. The thresholds are crawl-based heuristics.
- **AI search:**
  - Answer-engine crawlers (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Bingbot) are allowed if the user wants AI citations.
  - `nosnippet` and `max-snippet:0` also opt the page out of AI Overviews (§10).

## Data: free vs paid

- **Free path** (default, enough for a full audit): the bundled scripts, Search Console exports, Bing Webmaster Tools, PSI/CrUX, server logs, the built-in browser for rendered DOM.
- **Screaming Frog** (licence) adds:
  - JS-rendered crawling at scale (10k+ URLs).
  - Custom extraction.
  - Scheduled crawls.
  - GSC/GA/PSI joined per URL.

  Justified for sites above about 2,000 URLs or for JS-heavy sites (see tools.md `## Screaming Frog`). Its free mode (500 URLs) can cross-check our crawl.
- **Semrush / Ahrefs** add what no audit script can see: backlink profile, estimated competitor traffic, and keyword volumes for the "opportunity" column. Use them only for prioritising, never for finding technical defects. Pull just the domain overview and top pages, not full exports (tools.md `## Semrush`, `## Ahrefs`, `## Cost-optimisation playbook`).
- **Ahrefs Webmaster Tools** (free, for verified sites) gives own-site backlinks and a site audit. Prefer it over paid Ahrefs for the user's own domain.

## Output

```
# SEO audit — <host> — <date>
Scope: N pages crawled (limit hit? y/n) · templates: … · data: [measured] scripts, GSC export? PSI field data?
## Executive summary (5 bullets: biggest risk, biggest opportunity, quick wins count, what's healthy, what's unverified)
## Fix plan
| Priority | Issue | Scope (pages/template) | Evidence | Fix | Effort |
P0 = blocks indexing/revenue now · P1 = large visibility loss · P2 = meaningful · P3 = polish · park = no action
## Quick wins (≤1 day each, P1–P2, effort 1)
## Template fixes (one fix → N pages)
## Performance (CWV per template: field vs lab)
## Assumptions (scope, templates, money pages, market: each decision and the evidence behind it; research-store data reused, with its age)
## What could not be verified [needs data] — and the cheapest source for each
## Next re-check date
```

Tag every row with `[measured]`, `[Google doc]`, `[vendor data]`, `[estimate]` or `[needs data]`. Never print search volume, traffic, DA/DR or an invented "SEO score". The triage priority is the only ranking, and it comes from a lookup table, not a feeling.

## Pitfalls & myths

- **Disallow ≠ noindex.** A blocked URL can still be indexed without its content. To deindex a URL, allow crawling and serve `noindex` (§1).
- **noindex added by JS may never be seen**, and removing noindex with JS may never take effect (§1).
- **Word count, keyword density and Flesch scores are not ranking factors.** Report them only as diagnostics (§4).
- **Lighthouse "SEO 100" ≠ good SEO.** Lab performance ≠ CWV. Use field data when it exists.
- **llms.txt** is not used by Google (§10). FAQ/HowTo markup earns no Google rich result (§5).
- **Fixing 400 pages one by one** when 1 template causes them is wasted work. Always map issues to templates.
- **A crawl from your machine ≠ Googlebot's view.** Bot challenges, geo-redirects and A/B tests differ. Confirm critical findings with Search Console URL Inspection: through the API when Search Console access is configured, otherwise as an access request batched at the end.

## Log the work

Append an entry to `SEO-WORKLOG.md` in the project root, following `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`. Include:
- Scope and pages crawled.
- Scripts run and the paths of their outputs.
- Paid units spent (0 if none).
- P0/P1 counts and the changes made, with diffs or file paths.
- Unverified items.
- The next re-check date: 30 days after fixes ship, or 90 days for a routine check.
