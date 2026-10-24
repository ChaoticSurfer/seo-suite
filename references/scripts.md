# seo-suite scripts

Python 3.9+ standard library only — no installs, no keys required (PSI optionally uses `PSI_API_KEY`).
Run as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<script>.py" …`. Every script prints JSON to stdout;
redirect to a file in a working folder (e.g. `seo-work/`) and pass those files to `triage.py`.
Findings share one shape: `{id, severity: critical|high|medium|low|info, message, evidence}`.
Scripts see raw HTML only (no JavaScript); use `render_diff.py` with a browser-rendered DOM for JS sites.
Tests: `python3 -m unittest discover -s "${CLAUDE_PLUGIN_ROOT}/tests"`.

| Script | Purpose | Key usage |
|---|---|---|
| `page_audit.py` | One page: status/redirects, robots, title (px width), description, canonical, hreflang, viewport, h1/headings, thin/JS-rendered content, images (alt, dimensions, lazy LCP), links (nofollow, anchors), compression, HSTS, mixed content, OG, JSON-LD validation, bot-challenge detection | `page_audit.py URL [--facts] [--fail-on high]` · `page_audit.py --file dom.html --base-url URL` |
| `crawl.py` | BFS crawl of one host obeying Googlebot's robots rules; site findings: broken links, links to redirects, duplicate titles/descriptions/content, near-duplicates (≥90% shingle overlap), click depth, weakly linked, canonical to bad target / in body, hreflang return links, orphans vs sitemap, soft-404 probe; per-page issue counts | `crawl.py URL --max-pages 300 --workers 4 --delay 0.5 --sitemap-urls urls.txt --csv pages.csv --links-csv edges.csv [--path-prefix /blog/] [--user-agent "..."]` |
| `robots_check.py` | Google-style robots.txt evaluation (longest match, groups), 22 search/AI crawler access matrix, sitemaps, Content-Signal lines, 5xx/429/size/asset-blocking findings | `robots_check.py URL [--path /x --path /y]` · `robots_check.py --file draft-robots.txt --path /` |
| `sitemap_check.py` | Sitemap index recursion, .gz, 50k/50MB limits, lastmod validity/uniformity/future, http URLs, cross-host; samples URLs for non-200/noindex/non-canonical | `sitemap_check.py URL [--sample 30] [--urls-out urls.txt]` |
| `psi.py` | PageSpeed Insights: CrUX field p75 (URL + origin) with ratings, CWV pass, Lighthouse scores, LCP element, top opportunities, failed SEO audits | `psi.py URL [--strategy mobile\|desktop]` (set `PSI_API_KEY` for quota) |
| `keyword_ideas.py` | Autocomplete expansion (Google, Bing, YouTube) with a–z, question and commercial modifiers; intent classification; theme clusters. **No volumes.** | `keyword_ideas.py "seed" ["seed 2"] --hl en --gl gb --sources google,bing,youtube [--deep]` |
| `gsc_analyze.py` | GSC/Bing performance CSV: striking distance (est. extra clicks), CTR under-performers vs the site's own CTR curve, question queries, brand split, cannibalisation (query+page), period comparison with likely cause | `gsc_analyze.py Queries.csv [--brand "regex"] [--compare prev.csv] [--min-impressions 50]` |
| `log_analyze.py` | Access logs (combined format, .gz): hits/status/sections/errors/param share per bot (Googlebot variants, Bingbot, AI bots), DNS verification, sitemap URLs never crawled | `log_analyze.py access.log* [--verify-dns] [--sitemap-urls urls.txt]` |
| `redirect_check.py` | Migration map validation: one hop, permanent, lands on expected URL, target 200 + indexable + self-canonical; exit 1 on failures | `redirect_check.py map.csv` (columns old,new) |
| `content_score.py` | Keyword placement (title/h1/first 100 words/URL/meta/h2-h3), Flesch, sentence/paragraph stats, answer-sized paragraphs, question headings, trust signals (author/date schema, byline, about/contact/privacy, citations), top bigrams/trigrams | `content_score.py URL --keyword "kw"` · `--file draft.html` |
| `compare_pages.py` | Your page vs ranking competitors: words, headings, schema, trust, readability, placement; content-gap phrases shared by ≥2 rivals but absent from yours | `compare_pages.py YOUR_URL RIVAL1 RIVAL2 … --keyword "kw"` · `--no-own-page RIVAL1 RIVAL2 …` for a brief before the page exists |
| `render_diff.py` | Raw HTML vs rendered DOM: title/robots/canonical changes after JS, content/links/schema only present after rendering | `render_diff.py URL --rendered dom.html` |
| `serp_cluster.py` | Clusters keywords by shared top-10 URLs: ≥4 shared → one page, 2–3 → interlink (heuristic thresholds, adjustable) | `serp_cluster.py serps.json [--same-page 4] [--interlink 2]` (JSON: keyword → list of top URLs) |
| `triage.py` | Merge findings from any of the above into a P0–P3 fix plan by lookup table (impact, effort, fix); widens priority for issues on ≥25% of pages | `triage.py crawl.json robots.json sitemap.json [page.json…] [--pages N]` |
| `ai_visibility.py` | AI-answer visibility from a logged observations CSV: mention/citation rates with Wilson 95% CIs per engine, never-visible queries, competitor mentions, cited URLs | `ai_visibility.py obs.csv [--brand-domain example.com] [--compare earlier.csv]` |

## Getting a rendered DOM (for JS sites or bot-challenged sites the user can open)

In the built-in browser, open the page, then run `document.documentElement.outerHTML` with the JavaScript tool and
save the result to a file. Stop and ask the user if a CAPTCHA or challenge page appears — never bypass it.

## Known limits

No JavaScript execution · one host per crawl · robots matching treats `Googlebot-Image` etc. via their own group
only if named · schema validation covers Google's main types, not the full schema.org vocabulary ·
autocomplete endpoints are unofficial and rate-limited — keep `--delay` ≥0.25 s · title pixel width is an
Arial-20px estimate.
