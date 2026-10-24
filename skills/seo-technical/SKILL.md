---
name: seo-technical
description: Technical SEO deep dive. Covers crawling, indexing, rendering/JavaScript SEO, status codes and redirects, canonicals, robots.txt and meta robots, XML sitemaps, Core Web Vitals, HTTPS/mobile, faceted navigation, pagination, crawl budget and server-log analysis. It also has a codebase mode that finds and fixes SEO defects in Next.js, Nuxt, Astro, SvelteKit, Remix, Gatsby, WordPress, Shopify, Webflow, Frappe/Django/Rails templates, and a CI mode. Use for "pages not indexed", "Discovered/Crawled – currently not indexed", "canonical issues", "robots.txt check", "sitemap errors", "JS SEO", "is Google rendering my site", "Core Web Vitals / INP / LCP", "crawl budget", "analyse my server logs", "fix SEO in my Next.js app", "add an SEO check to CI". Not for a whole-site audit (use seo-audit), site moves (seo-migration), hreflang (seo-international) or copy and on-page rewrites (seo-onpage).
---

# Technical SEO

Make sure every page that should rank can be crawled, rendered, indexed and served fast, and that nothing which shouldn't rank is wasting crawl.

## When to use / not

- **Use for:**
  - Indexing problems.
  - Rendering doubts.
  - Robots, sitemap or canonical conflicts.
  - Core Web Vitals regressions.
  - Large or faceted sites.
  - Bot behaviour (logs).
  - Fixing SEO plumbing in a codebase.
  - Adding an SEO regression gate to CI.
- **Not for:** prioritising across all areas (seo-audit), redirect maps for a move (seo-migration), hreflang clusters (seo-international), or structured data authoring (seo-schema).

## Inputs to gather

1. The affected URLs or URL patterns, plus the Search Console "Pages" report reason if the user has it (e.g. "Crawled – currently not indexed").
2. Is the site built from a repo in this workspace? If so, which framework and version? Check `package.json`, `composer.json`, `requirements.txt` and `Gemfile`.
3. Hosting and CDN: Cloudflare, Vercel, Netlify, nginx. This decides where headers, redirects and bot rules live.
4. Optional:
   - Access logs (the last 7–30 days).
   - A `PSI_API_KEY`.
   - The Search Console Crawl Stats screenshot or export.

## Workflow

`S="${CLAUDE_PLUGIN_ROOT}/scripts"`. Run independent checks in parallel.

1. **Access and directives:**
   ```bash
   python3 "$S/robots_check.py" https://example.com --path /affected/path --path "/search?q=x"
   python3 "$S/page_audit.py" https://example.com/affected/path --facts
   ```
   Read the robots verdict for Googlebot, the meta robots and `X-Robots-Tag`, the canonical, the status code and the redirect chain. To test a draft robots.txt before deploying it, use `robots_check.py --file draft-robots.txt --path …`.
2. **Sitemaps:**
   ```bash
   python3 "$S/sitemap_check.py" https://example.com --sample 50 --urls-out seo-work/sitemap-urls.txt
   ```
3. **Site-wide crawl:**
   ```bash
   python3 "$S/crawl.py" https://example.com --max-pages 500 --sitemap-urls seo-work/sitemap-urls.txt --csv seo-work/pages.csv
   ```
   This finds broken links, redirects, duplicates, depth, orphans, canonical targets, the soft-404 probe and URLs blocked by robots.txt.
4. **Rendering:**
   1. Load the page in the built-in browser.
   2. Save `document.documentElement.outerHTML` to a file.
   3. Run `render_diff.py URL --rendered file.html`.
   4. If the title, canonical or robots tags change after JS, or the content and links only appear after JS, the page needs SSR/SSG or pre-rendering (§1).
5. **Performance:** run `psi.py URL --strategy mobile` (then desktop) per template.
   - Field `p75` is the truth. Lab opportunities explain why.
   - For INP, use the field number and find long tasks with DevTools in the built-in browser.
6. **Logs, if provided.** This shows Googlebot's real crawl:
   ```bash
   python3 "$S/log_analyze.py" access.log* --verify-dns --sitemap-urls seo-work/sitemap-urls.txt
   ```
   Look at:
   - The share of crawl spent on parameter URLs.
   - Errors served to bots.
   - Sections bots ignore.
   - Fake "Googlebot" IPs (`unverified_ips`).
   - Sitemap URLs that were never crawled.
7. **Triage:**
   ```bash
   python3 "$S/triage.py" seo-work/*.json
   ```
   Explain the cause of each P0/P1 and give the exact fix: header, config line, template file.
8. **Codebase mode** (see below): implement fixes as diffs, then re-run step 1 or page_audit to verify.
9. **CI mode.** Add a job that runs:
   ```bash
   python3 scripts/page_audit.py "$PREVIEW_URL/<path>" --fail-on high
   ```
   Run it per key template. It exits 1 on any high or critical finding. Copy the scripts into the repo or pin the plugin path. Pair it with a robots.txt test using `robots_check.py --file public/robots.txt --path /`.

## Checks

- **robots.txt** (§1):
  - ≤500 KiB, UTF-8, at the host root.
  - The most specific user-agent group wins and is never merged with `*`.
  - The longest path wins; an allow wins a tie.
  - `crawl-delay` is ignored by Google (honoured by Bing and Anthropic).
  - Never disallow CSS or JS needed to render the page.
  - **Fetch results:** 4xx (except 429) = no rules apply. 5xx or 429 = Google pauses crawling 12 h, then uses its cached copy for up to 30 days.
- **Meta robots and X-Robots-Tag** (§1):
  - `none` = `noindex, nofollow`.
  - Use `X-Robots-Tag` for PDFs and images.
  - The most restrictive rule wins.
  - The meta tag is read even outside `<head>`.
  - Never put noindex on a URL that robots.txt blocks; it can't be seen.
- **Canonicals** (§1):
  - One per page, absolute, in `<head>`, self-referencing on canonical pages.
  - Points to a 200, indexable, non-redirecting URL.
  - Don't mix the HTML tag and the HTTP header.
  - Sitemaps and internal links agree with it.
  - Redirects are the strongest signal; the sitemap is weak.
- **Status codes** (§1):
  - Error pages must not return 200 (soft 404).
  - 404 and 410 are treated identically.
  - 429/5xx slow crawling and eventually drop URLs.
  - Don't use 401/403 to limit crawl rate.
- **Redirects** (§1): 301/308 for permanent moves, one hop. Google follows ≤10 hops.
- **HTML size** (§1): ≤2 MB uncompressed for Googlebot for Search. Inline JSON blobs (`__NEXT_DATA__`, Nuxt payloads) are the usual reason pages exceed it.
- **JavaScript** (§1):
  - Only `<a href>` links are discovered.
  - Use the History API, not `#/` routes.
  - SPA 404s must return a real 404 or inject noindex.
  - Fingerprint asset URLs.
  - Avoid a noindex in the raw HTML that JS later removes.
- **Sitemaps** (§1):
  - ≤50k URLs and ≤50 MB uncompressed per file; use an index above that.
  - Absolute canonical URLs only.
  - Accurate `lastmod`; `priority` and `changefreq` are ignored.
  - Declare them in robots.txt.
- **Core Web Vitals** (§2): p75, mobile and desktop separately. LCP ≤2.5 s / INP ≤200 ms / CLS ≤0.1. TTFB ≤800 ms is a diagnostic only (web.dev).
  - **LCP fixes:** don't lazy-load the hero image; use `fetchpriority=high` and preload; CDN and caching for TTFB.
  - **CLS fixes:** set width/height on images, reserve ad slots, use `font-display`.
  - **INP fixes:** break up long tasks, yield to the main thread, trim third-party scripts.
- **Mobile-first** (§2):
  - Same content, headings, structured data, meta and alt text on mobile.
  - No primary content hidden behind interaction.
  - m-dot sites need bidirectional annotations.
- **HTTPS:**
  - Final URLs are https, with HSTS (convention).
  - No mixed content.
  - http → https in a single 301.
- **Faceted navigation** (§8):
  - Block facet crawling with a robots.txt disallow on the facet parameters, or move filters into `#` fragments.
  - If facets are indexable: one parameter order, `&` separators, and 404 for empty or nonsensical combinations.
  - canonical and nofollow are weak tools here.
- **Pagination** (§8):
  - A unique `?page=n` URL per page, linked with `<a href>`.
  - Don't canonicalize page 2+ to page 1.
  - `rel=next/prev` is unused by Google.
  - Infinite scroll needs paginated fallback links.
- **Crawl budget** (§1): only matters for sites with ~1M+ pages, or 10k+ pages changing daily, or a large "Discovered – not indexed" count.
  - **Levers:** consolidate duplicates, 404 removed pages, fix soft 404s, avoid chains, support 304/ETag, keep the servers fast.
  - **Not levers:** noindex and temporary robots.txt blocks.

## Codebase mode (framework fixes)

Read the existing files first and match their style. Show a diff before writing anything.

- **Next.js App Router:**
  - Use `export const metadata` / `generateMetadata()` with `title.template`, `alternates.canonical` (absolute; set `metadataBase`), `robots`, `openGraph`.
  - Add `app/sitemap.ts` (use `generateSitemaps` for >50k URLs) and `app/robots.ts`.
  - Use `next/image` with `priority` on the LCP image.
  - Return `notFound()` for missing data so the status is 404, not a soft 404.
  - Avoid `'use client'` on content-bearing pages.
  - Check the `__NEXT_DATA__`/RSC payload size against the 2 MB HTML limit.
- **Pages Router:** use `next/head` per page. `getStaticProps` returns `{ notFound: true }` for missing data.
- **Nuxt:** `useSeoMeta` / `useHead`, `@nuxtjs/sitemap`, `routeRules` for prerender/ISR. Missing data uses `createError({ statusCode: 404 })`.
- **Astro:** canonical via `Astro.url` + `site` in config, `@astrojs/sitemap`, static output by default. Islands keep content in HTML.
- **SvelteKit:** `<svelte:head>`, `+page.server.ts` with `error(404)`, `prerender = true` where possible.
- **Remix / React Router:** the `meta` export plus a `links` export for the canonical. Loaders `throw new Response(null, {status: 404})`.
- **Gatsby:** the Head API, `gatsby-plugin-sitemap`, a canonical plugin.
- **Plain React SPA (CRA/Vite):** the biggest risk. Recommend SSR/SSG (Next/Astro/vite-ssg) or pre-rendering. Until then, at minimum serve real 404s and put the title and meta in the HTML.
- **WordPress (Yoast / Rank Math):**
  - Settings → Reading "Discourage search engines" must be off.
  - Use one SEO plugin only (duplicate canonicals otherwise).
  - noindex the tag, date and attachment archives.
  - Watch for plugin and theme conflicts that output two canonicals.
- **Shopify:**
  - Handle `/collections/x/products/y` duplicates; the canonical points to `/products/y`, and theme links should use the canonical path.
  - Edit `robots.txt.liquid` for facet/filter parameters.
  - Check app-injected JSON-LD for duplicate Product blocks.
- **Webflow:** per-page SEO settings, auto sitemap, 301 rules in hosting settings, canonical tag setting. Custom code embeds for JSON-LD.
- **Frappe / Django / Rails templates:**
  - Put the `<title>`, meta description, canonical and robots in the base template, with per-view blocks that override them.
  - Return 404 from views for missing records, not a 200 "not found" page.
  - Generate sitemaps from the ORM (Django `sitemaps` framework, Rails `sitemap_generator`; for Frappe, a `www/sitemap.xml` page or a hook).
- **CDN / edge** (Cloudflare, Vercel, Netlify): redirects and headers live in config (`vercel.ts`/`vercel.json` redirects, `_redirects`, Cloudflare rules). Check that bot management doesn't challenge verified crawlers. **Changing CDN or bot settings needs the user's explicit approval.**

## Data: free vs paid

- **Free path:**
  - Bundled scripts.
  - Search Console: Pages/indexing report, URL Inspection (2,000/day per site via the API), Crawl Stats.
  - Bing Webmaster Tools.
  - PSI/CrUX (free key).
  - Server logs.
  - The built-in browser for rendering and DevTools performance traces.
- **Screaming Frog** adds JS-rendered crawling at scale, crawl comparison, custom extraction (e.g. find every page missing a component), and its log file analyser. Justified for big or JS-heavy sites and recurring scheduled crawls (tools.md `## Screaming Frog`).
- **Sitebulb / Lumar / Botify** add enterprise crawl scheduling and log pipelines. Only justified for very large sites (tools.md `## Other paid tools`).
- **Semrush / Ahrefs site audits** duplicate the free crawler here. Use them only if the user already pays and wants the dashboards. Their unique value is off-site data, which this skill doesn't need.

## Output

- **Per issue:**
  - What's wrong, with the URL(s) and `[measured]` evidence (status, header, tag, robots line).
  - Why it matters, with the google-rules § reference.
  - The exact fix (file/config + code).
  - The priority from triage.py.
  - How to verify: the re-run command, or URL Inspection.
- **Close with:**
  - A P0–P3 table.
  - "Verified after fix", with before/after script output for anything changed.
  - The open `[needs data]` items.

## Pitfalls & myths

- **"Submit to Google" doesn't make a page indexed.** The fix is quality, internal links and the right status codes. Indexing API use is only for JobPosting and livestream pages (§11).
- **Blocking a URL in robots.txt to remove it from the index backfires**; the URL stays indexed without content.
- **canonical is a hint.** Google may pick another canonical when the signals conflict (duplicates, internal links, sitemap).
- **Dynamic rendering** is a workaround, not a strategy; prefer SSR/SSG.
- **Pagespeed scores ≠ rankings.** CWV is one signal among many, and relevance wins (§2).
- **Don't "fix" crawl budget on a 5,000-page site.** It's almost never the problem.

## Log the work

Append to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`: the URLs/patterns checked, scripts and outputs, the root causes found, files changed (paths, diffs), verification evidence, paid units (normally 0), and the next re-check date (after the next deploy, or 14 days for indexing fixes).
