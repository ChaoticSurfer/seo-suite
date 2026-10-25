# SEO tools: free first, paid when justified (prices checked 2026-10-24)

**Rule:** every seo-suite workflow must work on the free path. Recommend a paid tool only when it provides data
the free path *cannot* (third-party indexes, panels, scale). Say what it adds, run the cheapest call that answers the
question, and log units or credits spent in `SEO-WORKLOG.md`.

Prices change often. Figures marked [UNVERIFIED] came from third-party pages, not the vendor. Re-check the
vendor's pricing page before quoting a number to a client.

## Main stack

The ranked core stack for running SEO end to end with no person in the loop once credentials are given. Each category
has three lists: the [default free stack](#default-big-website-free-only), used at every site size, and the small and
big paid lists, which apply only when paid tools are set up or the user asks. Ranked 2026-10-24 by four criteria, in
this order:

1. **Unattended within the terms.** A run can drive it through an official API or MCP server, with quotas and a
   sign-in that a scheduled run can hold.
2. **Data quality and coverage** for the job, including small markets and non-English locales such as Georgia (ka, ru)
   and multi-language sites.
3. **Cost per useful result** at that site size, from the prices in this file. No paid calls were made to rank them.
4. **Overlap** with what the plugin's free scripts already do.

Facts that are new to this file have their primary sources in [tools-sources.md](tools-sources.md). The paid lists,
each category's Reserve table, the credit-guard limits and the vendor notes are in [tools-paid.md](tools-paid.md).

### Size boundary

- **Small:** up to 2,000 indexable URLs. Count them with `sitemap_check.py` (`total_urls`), summed across every locale
  folder, subdomain and ccTLD of the site. Use the crawl count when there is no sitemap.
- **Big:** more than 2,000 indexable URLs.

Nothing else moves a site between classes. Three things already share the 2,000 line: `autonomy.md` crawls everything
up to 2,000 URLs and splits into sections above it, Screaming Frog becomes worth paying for above about 2,000 URLs, and
the URL Inspection API allows 2,000 checks a day per property. So a small site can be inspected in full every day and a
big one only sampled.

Market-language pairs, competitors, tracked keywords and physical locations don't change the class. They multiply the
per-unit costs in each list. The cost examples assume:

| | Small | Big |
|---|---|---|
| Market-language pairs | 2 (GE-ka, GE-ru) | 6 (GE-ka, GE-ru, GE-en, GB-en, IL-he, DE-de) |
| Competitors | 3 | 10 |
| Physical locations (local businesses only) | 1 | 20 |

The monthly cost is what a class produces, not what decides it. Scale switches inside a class are "use when" conditions
instead: more than 10 locations for listing distribution, Search Console API pulls that hit 50,000 rows a day for the
BigQuery export, and templates that need JavaScript for a rendering crawler.

### Labels

- **Main:** in the ranked core stack for that list (the default free stack, or the paid list for that site size).
- **Cross-check:** runs alongside a Main tool because it measures the same thing differently. Agreement raises
  confidence. Disagreement sends the item to a re-check before the run acts on it. Each row says what is compared and
  when it is worth the cost.
- **Reserve:** a good tool that is not in the stack. Each one has the condition under which it is brought in.
- **(to build):** the vendor's route is official and allowed for unattended runs, but seo-suite has no client yet, or
  the credit guard can't price it. The row says what the run uses until then. INTEGRATIONS.md "Planned, not built yet" lists them in order.
- **(through claude-seo):** run by `scripts/claude_seo.py`, which clones AgriciDaniel/claude-seo into seo-suite's data
  folder on first use, pulls its latest main before every use and sets up its venv. Never the Indexing API.
- **(guard: …):** the call shape or cost needs a [credit guard change](tools-paid.md#credit-guard-limits) first.

A tool has one label per list. It can hold different labels in different lists: `psi.py` is a Cross-check in the
default stack and Main in the paid lists. The one split inside a list is by market, and its row says so (SE Ranking
in the big keywords list).

### Rules behind every list

- **No vendor UIs and no consumer AI apps.** A run never scrapes a vendor's web app. It never automates chatgpt.com,
  perplexity.ai, gemini.google.com, claude.ai or Copilot, and it doesn't store vendor data collected from those apps
  either, whoever collects it. Gemini answers grounded with Google Search and Grounding with Bing output are never
  stored for analysis, because their terms forbid it.
- **Vendor-collected Google results pages are allowed** (DataForSEO, SerpApi, Ahrefs' AI Overview and AI Mode data).
  They are tagged [vendor data]. seo-suite never fetches google.com itself.
- **Finish the action.** Prefer tools that let the run complete the step (submit URLs, open a pull request, apply an
  approved edit) over tools that only produce something for a person to paste.
- **No overage outside the credit guard.** The guard sees only MCP calls to the vendors it knows. A tool it can't see
  (a script's own calls, Ahrefs REST calls including Brand Radar checks, or Moz, Majestic, Local Falcon, SerpApi, OpenAI,
  Anthropic and Perplexity) runs only on a plan
  with no overage and pay-as-you-go off, or after its script reads the guard's budget options and ledger and stops
  itself.
- **Exports that need a person are Reserve.** Search Console's Search generative AI report, Crawl Stats and Links
  report, and Bing's AI Performance report have no API, so they sit outside the unattended stack. When a person
  exports one monthly, runs read the newest file and flag it stale after 35 days.
- **One owner per shared quota and purchase.** Measurement owns the URL Inspection quota and the Search Console and
  IndexNow schedules, and Technical reads their results. Every organic SERP pull goes through the research store, so a
  keyword that rank tracking already snapshotted within the cache TTL (7 days in the credit guard, 30 in the research
  store) isn't bought again. Shared tools are counted once in the totals.
- **Not ranked here:** `content_score.py`, `translation_check.py` and `ai_text_check.py` serve the content skills, and
  no content category was ranked. They are Main in the content skills that call them, at every size and in every list,
  because they cost $0. No WordPress-specific tools or connectors are included.

### Default: big website, free only

**The rule.** This is the stack every run uses by default, at every site size: the most thorough stack that costs $0.
The [size boundary](#size-boundary) sets only its depth. Up to 2,000 URLs a run crawls and inspects every URL; above
that it works in sections and samples, and each row says how. Free means $0 to run. API keys for free quotas
(PageSpeed Insights, CrUX, Search Console, Bing Webmaster Tools) count as free; pay-per-call APIs (OpenAI, Anthropic,
Perplexity, DataForSEO) don't. A row that needs a Cloud billing account or has a free-tier ceiling says so.

**When the paid lists take over.** The small and big paid lists, per category in [tools-paid.md](tools-paid.md), apply only
when budgets or credentials for paid tools are configured (every credit-guard budget starts at 0), or when the user
asks. They take over per category, using the paid list for the site's size. A paid Main row whose vendor isn't set up
yet falls back to the default row that does the same job, so a partial setup never leaves a gap. Every tool in this
stack also has a label in the paid lists, where several are Cross-checks or Reserve. seo-audit applies this through
scripts/audit_profile.py; see references/profiles.md.

**Reserve.** Each category's Reserve table ([tools-paid.md](tools-paid.md)) applies to this stack too. A Reserve row marked "(paid lists)", "(small
sites)" or "(big sites)" covers only the paid lists. When its tool also sits in a list here, the row names that
default label, and the default label holds in this stack. Every paid tool is Reserve in this stack: it comes in when
its budget or credentials are configured, or when the user asks, and its "What free can't answer" line says what it
adds. The $0 ones that need a person (the Search Console and Bing exports, Ahrefs Free, Screaming Frog free mode, the
Rich Results Test, and Semrush Free from the [Semrush](tools-paid.md#semrush) section) are the first to bring in. No row here calls
a paid tool, so the credit guard has nothing to deny. SerpApi and Moz are outside the guard and stay on their free
plans, which have no overage.

#### Free: keywords and competitors

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Research store (`research_store.py`) | Main | The reuse layer. It keeps every free source's values side by side, each with its source and date, so the cross-checks below compare like with like | Local script, no auth. Skills write only through `ingest`, `set-status` and `glossary add` | $0 | — |
| 2 | Search Console API, Search Analytics **(through claude-seo)** | Main | The only measured Google demand: impressions, clicks and position per query, page and country, in any language. With no paid volumes, impressions are the demand number the run prioritises by. Language comes from the URL path or the query's script | `claude_seo.py gsc-export` with the property named, on the user's one-time OAuth sign-in (`claude_seo.py google-signin`, `webmasters.readonly`) or a service account an owner adds as a property user (`GOOGLE_APPLICATION_CREDENTIALS`). Without either: exports, or Search Console in the browser while the user is signed in | $0 | 25,000 rows a request, 50,000 rows a day per search type, 2–3 days behind. It shows only queries the site already appears for |
| 3 | Search Console bulk export to BigQuery | Main | No row cap, and anonymised-query totals: the long tail and the per-language splits that the API truncates. It doesn't backfill, so turn it on at onboarding at every size | An owner turns it on once. Runs read it through Google's BigQuery MCP with only `execute_sql_readonly` exposed. At most 3,000 rows and 3 minutes a call, so aggregate in SQL | $0 within BigQuery's free tier | **Needs a Cloud project with billing**, which Google's setup page requires. Free tier: 10 GiB stored and 1 TiB of queries a month, then $6.25 a TiB. Limit queries with a `QueryUsagePerDay` custom quota set with headroom, for example 0.025 TiB a day (about 0.78 TiB in a 31-day month): Google says custom quotas are approximate and don't strictly cap bytes processed, so check BigQuery's billing report monthly. Limit storage with partition expiration (14 days or longer). With no billing account, skip it and say so in the report |
| 4 | WebSearch SERP samples (`seo-serp-researcher` agent) | Main | The free view of who wins a keyword: top-10 domains, page types and People Also Ask questions for 20–50 head terms per pair. The competitor list starts here | Claude's own WebSearch and WebFetch, allowed in `--allowedTools`. Tag [measured: WebSearch sample] | $0 on a Claude subscription. On API-key billing it uses Anthropic's web search ($10 per 1,000 searches), and one call may run up to 8 searches, so up to about $0.08 a call: an API-key run counts it or skips this row | Not Google's results, and the tool describes itself as US-only, so per-locale results are directional and never positions. At most 200 WebSearch calls per session (per turn in `claude -p`), raised with `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`; above that, split the pairs across runs (code.claude.com/docs/en/tools-reference) |
| 5 | Competitor sitemap inventory **(to build: polite mode)** | Main | What competitors publish: URL templates and new sections by first-seen date. With no vendor keyword database, it is this stack's map of competitor topics | Until a polite mode exists (robots.txt, one request at a time per host, stop on 403, 429 or a challenge, snapshot diffs): `sitemap_check.py --sample 0 --urls-out` on competitors, diffed outside the script | $0 | Store URLs only, never page text |
| 6 | `compare_pages.py` | Main | Our page against the pages that win its keyword: size, structure, schema, trust signals, and the phrases competitors share that our page never mentions | Plugin script, no auth. Competitor URLs come from rows 4 and 5 | $0 | — |
| 7 | CrUX popularity rank (BigQuery) | Main | The only free size signal per competitor origin: Google's popularity band from Chrome navigations (top 1k, 5k, 10k and so on, on a log10 scale with half steps). It stands in for vendor traffic estimates in the quarterly competitor review | BigQuery MCP, read-only, with the Cloud project from row 3. One query a quarter | $0 within the 1 TiB monthly query tier | CrUX's BigQuery page says the project needs a credit card. Bands by country come from the materialized `country_summary` table, which carries the `metrics_summary` columns, `rank` among them; the page doesn't say whether that rank is measured within the country. Small competitors may be missing from CrUX |
| 8 | `keyword_ideas.py`, Google suggestions | Cross-check | Compares Google's suggestions for cluster-head seeds with our Search Console queries. A phrase in both is confirmed demand. A suggestion with no impressions is a gap candidate, checked with a WebSearch sample before a page is planned. It is also this stack's source of phrases the site doesn't appear for yet | No auth. Unofficial, undocumented endpoint, a deliberate exception: `--delay` 0.25 s or more, modest volumes, `--hl` and `--gl` per pair (`--hl ka --gl ge`) | $0 | Ideas, not volumes. The expansion words and intent labels are English, so ka and ru expansions add little |
| 9 | `keyword_ideas.py`, Bing suggestions | Cross-check | Compares Bing's suggestions with Google's for the same seeds. Only Bing is a different source: the YouTube mode calls the same Google service. A phrase both engines suggest ranks higher | As row 8 | $0 | As row 8 |
| 10 | Bing Webmaster Tools keyword API (`GetKeywordStats`, `GetRelatedKeywords`) **(to build: Bing client)** | Cross-check | Bing's own keyword impressions for shortlisted phrases, by country and language: this stack's only market-wide demand counts. Compares the order of demand inside a cluster with Search Console impressions. A phrase high in both gets its page first. They are Bing counts, never Google volumes | The Bing client, with an API key or OAuth on the JSON endpoint | $0 | Georgian support is unverified. Weight it by Bing's share of the market's searches |
| 11 | Wayback Machine CDX API | Cross-check | Compares first-seen dates from our competitor sitemap snapshots with the archive's first capture of the same URLs, and backfills history before our first snapshot. Run it when a competitor section appears or a competitor gains | Free public API with no key (`web.archive.org/cdx/search/cdx?url=…&output=json`), fetched with WebFetch at a polite rate | $0 | — |

**What free can't answer**

- Google search volumes and 12-month seasonality per keyword and locale: DataForSEO Google Ads, ≈ $0.10 a month
  small, ≈ $10 big.
- Google's own top 10, SERP features and People Also Ask per keyword at an exact location: DataForSEO SERP API,
  ≈ $0–0.80 small, ≈ $18 big.
- Competitors' full keyword lists, positions and gaps, Georgia included: SE Ranking Data API, ≈ $0.20–0.60 small,
  ≈ $1 big (plus ≈ $2 as the big cross-check in Labs markets).
- Keyword difficulty and competitor traffic estimates outside Georgia: DataForSEO Labs, ≈ $0.13 per covered pair small
  (a cross-check), ≈ $7.40 big.
- Idea expansion at an exact location through an official API: DataForSEO Google Autocomplete, ≈ $0.50 small, ≈ $12
  big.
- A clickstream volume opinion: DataForSEO Clickstream, ≈ $0.75 big; Reserve on small sites.

#### Free: backlinks and authority

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Bing Webmaster Tools API (`GetLinkCounts`, `GetUrlLinks`) **(to build: Bing client)** | Main | Free first-party links from a search engine's own crawl, with the source URL and anchor for each linked page of ours. A weekly snapshot diff gives new and lost links | API key (one per user, for all their verified sites) or OAuth, on the JSON endpoint. Page through `GetLinkCounts`, then `GetUrlLinks` per target page, spread across the week. Until the client exists: the community `zizzfizzix/mcp-server-bwt`, audited and pinned | $0 | Own verified sites only, and a sample: no nofollow flag and no first-seen date. Quotas are [UNVERIFIED], so back off on errors and keep the last snapshot. The key travels in the query string, so never log request URLs |
| 2 | Ahrefs `domain-rating-free` (public API v3 endpoint) **(to build: client)** | Main | Domain Rating for up to 1,000 targets per POST at 0 units: this stack's authority number for competitors, linking domains and prospects | REST with a v3 key kept in the keychain | $0 | The endpoint docs say keys are free on a free account; Ahrefs' help page says new keys need Lite, so confirm once. If a key needs Lite, this row leaves the free stack. Every DR shown needs "Domain Rating by Ahrefs" with a link next to it |
| 3 | Common Crawl web graph, domain level **(to build: graph reader)** | Main | The only free view of who links to competitors: referring domains per competitor, and the domains that link to competitors but not to us. The Aug–Oct 2026 graph has 135.0M nodes and 1.8B edges, and its ranks file adds harmonic centrality and PageRank per domain. For our own site, its referring domains are compared with Bing's: a domain that only one source shows gets a row 5 check | Each quarterly release: download the domain vertices (942.6 MiB), edges (7.1 GiB) and ranks (2.4 GiB) files, and stream them through a reader that keeps only the edges into our and the competitors' domains | $0 | Domain level only: no anchors, URLs or dates. About 10 GiB of downloads a quarter. Common Crawl's terms strongly recommend legal counsel before any use, commercial use included, so the owner takes that advice before client reports use it |
| 4 | Moz API, Free | Cross-check | A second authority opinion: DA, PA and Spam Score for our site, competitors and shortlisted prospects, against DR and Common Crawl's ranks. When two of three call a prospect weak, drop it | JSON-RPC API with the `x-moz-token` header, monthly, at most 50 rows | $0 | 50 rows a month, one request every 10 seconds. The free tier needs a card at sign-up, which the user enters. Outside the guard, so Free only |
| 5 | `page_audit.py --facts` on the linking page | Cross-check | Ground truth for every link Bing reports new or lost, and for every prospect page: whether the link exists now, with its rel and anchor. Bing says lost but the page links: index lag | Built in. Check the host with `robots_check.py` first, and send one request at a time per host. Raw HTML only. Challenges are reported, never bypassed | $0 | — |

**What free can't answer**

- Full own and competitor backlink lists with anchors and first-seen and lost dates, every week: DataForSEO Backlinks
  API, ≈ $1.50 small, ≈ $5–15 big.
- URL-level "links to competitors but not to us", with anchors, and bulk spam scores for prospect lists: the same
  DataForSEO Backlinks budget (`domain_intersection`, bulk rank and spam score).
- A second deep index with referring-domain and DR history, broken backlinks and link intersect: Ahrefs API v3,
  Standard $249 as the big cross-check; Reserve on small sites (Lite $129).
- Monthly gained and lost linking domains from a second index: Moz Starter Medium, $20 on small sites during active
  link building; Reserve on big sites (Starter Large $75).

#### Free: technical

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | `crawl.py` | Main | The core crawl: broken links, links to redirects, duplicates, click depth, orphans against the sitemap, bad canonical targets, hreflang return links and a soft-404 probe, plus `page_audit` and `schema_rules` on every page. Its CSV feeds `triage.py` and the research store | Up to 2,000 URLs: the whole site. Above: one `--path-prefix` section per subagent, up to 2,000 pages each. Standard library, no key | $0 | Raw HTML only, one host per crawl, near-duplicates on the first 600 pages. It obeys robots.txt and reports a challenge without bypassing it |
| 2 | `sitemap_check.py` | Main | The URL inventory that sets the depth (`total_urls`), plus lastmod, file limits and a sample of listed URLs for non-200, noindex and non-canonical pages | Run `--urls-out` first, so later steps reuse the list. Above 200 sitemap files, run it per child index | $0 | — |
| 3 | `robots_check.py` | Main | Google-style robots.txt evaluation and the access matrix for 22 search and AI crawlers. `--file` tests a draft before deploy, so the run blocks a bad change | CI wraps it in the documented one-liner. `--path` tests facet and parameter rules | $0 | — |
| 4 | `page_audit.py` | Main | One URL per template, and the CI gate that stops a template regression before it ships | CI runs `page_audit.py --file --base-url <production URL> --fail-on high` on the preview HTML. A live run covers headers | $0 | — |
| 5 | `redirect_check.py` | Main | Redirect maps and shipped redirect fixes: one hop, permanent, landing on a 200, indexable, self-canonical page | A CSV map with old and new columns. `--workers 8` on big maps | $0 | — |
| 6 | `schema_rules.py` | Main | Google's rich-result requirements as pure data, on every crawled page and on the rendered DOM | Pure function inside the scripts | $0 | — |
| 7 | CrUX API and History API **(to build: in `psi.py`)** | Main | Field p75 LCP, INP, CLS, FCP and TTFB per origin or URL and form factor, and up to 40 weekly points: what real users get. Big sites: the origin plus the top URLs per template | Free Cloud API key. History refreshes on Mondays, so the monitor runs on Tuesdays. Until it is built, `psi.py` reads the field p75 that PageSpeed Insights still returns | $0 | 150 queries a minute per project, offered without charge, which paying can't raise. Often origin-only or empty on small sites: record "no field data" |
| 8 | `render_diff.py` | Main | Raw HTML against the rendered DOM, one URL per template. It decides which templates depend on JavaScript | Rendered DOM from row 9 | $0 | — |
| 9 | claude-seo `render_page.py` (`claude_seo.py render`) | Main | The unattended renderer for `render_diff.py`, in `claude -p` and launchd jobs: Playwright Chromium after the page settles, with claude-seo's SSRF guards and service workers blocked | Installed on first use into seo-suite's data folder (a git clone of claude-seo's main branch, a venv and Chromium, about 150 MB) and pulled before every use. Headless Chrome (`--dump-dom`, default User-Agent) renders only when claude-seo can't be set up. Own site only | $0 | One URL per template, not a rendered crawl of every page. Needs git and Python 3.11–3.14 |
| 10 | `log_analyze.py` | Main | What Googlebot, Bingbot and AI bots actually fetched: crawl waste, errors served to bots, sitemap URLs never crawled, and crawl budget on big sites | Logs delivered to the run (host export, rsync, an S3 pull). Combined format and `.gz` only. `--verify-dns` | $0 | CDN logs (usually JSON) need a converter, which isn't built |
| 11 | Chrome DevTools MCP (official) | Main | Performance traces behind a poor field INP or LCP | Local stdio with `--headless --isolated --performance-crux=false --usage-statistics=false` | $0 | By default it sends trace URLs to CrUX and usage statistics to Google, hence the flags |
| 12 | IndexNow **(to build: submitter)** | Main | Finishes the job after a fix ships: changed URLs reach Bing, Yandex, Seznam, Naver and Yep | Measurement owns the submitter and schedule. Autonomy level 3 and above | $0 | Google doesn't use it |
| 13 | Search Console URL Inspection API **(through claude-seo)** | Cross-check | Google's verdict on the URLs that `crawl.py` and the sitemap describe: indexed or not, Google-chosen against declared canonical, last crawl, robots state and rich results. Crawl and Google agreeing lets the run act. A sitemap URL the crawl calls indexable but Google doesn't index, or gives another canonical, goes to a re-check first | Measurement owns the quota and schedule; Technical reads the results. Up to 2,000 URLs: every URL weekly. Above: changed URLs, money pages and a rotating sample per template | $0 | 2,000 inspections a day per property, 600 a minute. Indexed version only, no live test |
| 14 | `psi.py` (PageSpeed Insights API v5) | Cross-check | Lab against field: compares Lighthouse LCP, CLS and TBT per template with CrUX's p75. Field poor but lab good points to real-user conditions, so the run traces it with row 11 before acting. A lab regression after a release shows before the 28-day field window moves. Its audit also names the LCP element and the biggest opportunities. Where CrUX has no data, it is the only speed signal, reported as lab | Set `psi_api_key`. On 429 the run continues without PSI | $0 | Google recommends a key for automated queries and publishes no quota |
| 15 | Bing Webmaster Tools crawl API (`GetCrawlStats`, `GetCrawlIssues`, `GetUrlInfo`, `FetchUrl`) **(to build: Bing client)** | Cross-check | Compares Bing's crawl counts and errors with `log_analyze.py` and `crawl.py`, and `FetchUrl`'s result with our own fetch, which catches a CDN or WAF serving bots differently. Weekly, and always when there are no logs | The same Bing client as Measurement | $0 | — |
| 16 | Technical drift: claude-seo's drift rules (`claude_seo.py drift`) **(through claude-seo)** | Cross-check | Compares this crawl with each URL's known-good baseline: 17 rules for a removed schema block, canonical, H1 or title, an added noindex, an error status, and changed titles, descriptions, Open Graph tags or H2 outline. Findings go to `triage.py` (`technical-drift-*`). Run it on every crawl of a monitored site | One snapshot per crawl run from `crawl.py --csv`; the first run only baselines. `--rebaseline` after verified fixes. Baselines live in claude-seo's own database (`~/.cache/claude-seo/drift/`), not in git | $0 | Raw HTML only, one fetch per URL; Core Web Vitals are skipped (`psi.py` covers them) |

**What free can't answer**

- A rendered crawl of every page, with structured-data validation, near-duplicates past 600 pages and crawl
  comparison: Screaming Frog licence, £199 a year (≈ £17 a month) per user, Main on big sites and Reserve on small.
- A second crawl from other IPs, which catches geo-, IP- or User-Agent-dependent serving and WAF blocks: DataForSEO
  On-Page, ≈ $0.10–3.40 small, ≈ $3–102 big.

#### Free: rank and AI-answer visibility

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Search Console API, Search Analytics **(through claude-seo)** | Main | First-party clicks, impressions and average position by query, page, country, device and date. AI Overview and AI Mode appearances count inside Web. It feeds `gsc_analyze.py` and the per-country CTR curve | The same `claude_seo.py gsc-export` as Keywords. Each run re-pulls only the last ~3 days. Big sites: one request a day per country filter | $0 | 1,200 queries a minute per site. Don't compare impressions or position across 2025-05-13 to 2026-04-27 |
| 2 | Search Console bulk export to BigQuery | Main | Removes the 50,000-row cap and flags anonymised queries. Average position = SUM(sum_top_position) / SUM(impressions) + 1 | As in Keywords; shared and counted once | $0 within the free tier | As in Keywords: needs a Cloud project with billing |
| 3 | SerpApi, Free plan **(to build: collector)** | Main | This stack's only fixed-condition Google rank snapshots: position, URL, SERP features and AI Overview presence for a money tier of keywords, and Google AI Mode answers with their references (`engine=google_ai_mode`). Shown beside Search Console's average position for the same query and country, never averaged with it. A snapshot move that Search Console doesn't show within a week is re-checked. [vendor data]: seo-suite never fetches google.com | REST with `api_key` from the environment, `gl=ge`, `hl=ka` or `ru`, and `location` for a city. Outside the guard: the free plan has no overage, and the collector counts its own calls. Spend the 250 searches on the money tier, for example 25 keywords × 2 pairs weekly (about 217 a month) | $0 | 250 searches a month, 50 an hour. An AI Overview needs a follow-up request with a `page_token` that expires within a minute; whether it counts as a search is [UNVERIFIED]. No Legal Shield on Free. Google sued SerpApi on 2025-12-19 over its Search results, so treat the feed as at risk |
| 4 | GA4 AI-referral sessions (`analytics-mcp`) | Main | This stack's AI-answer signal: real sessions from chatgpt.com, perplexity.ai, claude.ai, copilot.microsoft.com and gemini.google.com landing on our pages, per engine and page. Direction only, never levels | Read-only, service-account impersonation, `analytics.readonly` | $0 | Counts clicks, not mentions or citations without a click. Reading GA4 never touches the AI apps |
| 5 | Google Search Status Dashboard feed | Main | Google's own start and end dates for updates. The run holds alerts during a rollout and compares only a full week after it ends | `GET https://status.search.google.com/incidents.json` once a run | $0 | No key; robots.txt allows it |
| 6 | Bing Webmaster Tools API (`GetQueryStats`, `GetPageQueryStats`) **(to build: Bing client)** | Cross-check | Compares Bing's positions and clicks per query and page with Search Console's. A move in both engines is a change in our page; a move in one is that engine's update, checked against row 5 for Google. Bing grounds Copilot, so it is also this stack's Copilot-side signal | Weekly pull into its own table. `gsc_analyze.py` already maps Bing's columns | $0 | The methods take no country, device or date range, so the data is labelled "Bing, all markets" |

**What free can't answer**

- Snapshot rank for every tracked keyword, locale and device beyond 250 searches a month, with AI Overview references
  and competitor positions: DataForSEO Google Organic SERP API, ≈ $9.50 small (2 pairs), ≈ $50 big.
- ChatGPT, Claude and Perplexity answers to the frozen prompts, with mention and citation rates: `ai_probe` through
  the official APIs, ≈ $3–6 small, ≈ $10–18 big.
- AI Mode answers at volume (no Georgian): DataForSEO Google AI Mode API, ≈ $0.26 small, ≈ $5 big.
- Bing ranks per locale: DataForSEO Bing Organic SERP API, ≈ $5 big; Reserve on small sites.
- A second collector for positions and AI citations: Ahrefs Rank Tracker and Brand Radar through REST v3, $0 extra on
  the big stack's Standard plan ($249) plus Brand Radar packs $0–50; Reserve on small sites (Lite $129).

#### Free: measurement, local and indexing

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Search Console API: Search Analytics, URL Inspection, Sitemaps **(through claude-seo)** | Main | Google's own clicks, impressions and positions for 16 months, its indexing verdict per URL, and `sitemaps.submit` at level 4. Owns the URL Inspection quota for every category | Service account as a property user: `webmasters.readonly`, plus `webmasters` only for `sitemaps.submit` at level 4 (`claude_seo.py submit-sitemap`). Never the Indexing API scope. Up to 2,000 URLs: every URL weekly and changed URLs daily. Above: changed URLs plus a fixed sample per template | $0 | 2,000 inspections a day per property. Google publishes no Search Console MCP. Never script the Search Console UI |
| 2 | Search Console bulk export to BigQuery | Main | Full query × URL tables for cannibalisation and language splits | As in Keywords; shared and counted once | $0 within the free tier | As in Keywords: needs a Cloud project with billing |
| 3 | Google Analytics 4 (official `analytics-mcp`) | Main | What organic visitors do and whether they convert, by landing page. GA4 organic sessions against Search Console clicks flag a removed tag or a consent change | Local stdio, service-account impersonation, `analytics.readonly`, never `--allow-write`. Fixed weekly reports on big sites | $0 | A standard property allows 200,000 tokens a day; send `returnPropertyQuota` |
| 4 | Bing Webmaster Tools API **(to build: Bing client)** | Main | Bing's own query and page stats and crawl issues, for all markets at once (URL submission is Reserve: IndexNow submits) | API key or OAuth on the JSON endpoint | $0 | The key travels in the query string, so never log request URLs |
| 5 | IndexNow **(to build: submitter)** | Main | The run tells the engines itself: changed and removed URLs reach Bing, Yandex, Seznam, Naver and Yep | Key file `/{key}.txt` added by a level-2 pull request. POST up to 10,000 URLs at level 3 and above, only changed URLs | $0 | 422 means a host mismatch; 429 means back off |
| 6 | Google Business Profile APIs (local businesses only) **(to build: client)** | Main | Daily Maps and Search impressions, calls, directions, website clicks and bookings, monthly search keywords and own reviews, and the only official way to apply an approved profile change, gated per run | OAuth `business.manage` as owner or manager, read methods only unless an edit was approved for that run | $0 | Google must approve access first (profile verified and active for 60+ days, a website, the application form): 0 queries a minute until then, 300 after |
| 7 | Merchant API v1 (stores only) | Main | Product statuses, disapprovals, account issues and performance | Service account, scope `content`. Read tools only, through the alpha Merchant API MCP or plain REST | $0 | Edits are always gated |
| 8 | Google Search Status Dashboard feed | Main | Dates of Google updates and incidents, for drop diagnosis | As in Rank; shared and counted once | $0 | — |
| 9 | Microsoft Clarity (Data Export API, official MCP) | Cross-check | A second tag that counts sessions its own way, with bot sessions separated. Compares organic sessions and engagement per landing page with GA4 and Search Console clicks. A gap above about 20% [heuristic] points to consent, tagging or bot-filtering differences | Token created by the project admin. One fixed daily job; rotating section filters on big sites | $0 | 10 requests a project a day, the last 1–3 days, 3 dimensions and 1,000 rows. Adding the tag is a site change (level 2 and above) |

**What free can't answer**

- Map-pack rank per grid point: DataForSEO Google Maps geo-grid, ≈ $0.15 monthly or ≈ $0.65 weekly small, ≈ $6 or
  ≈ $25 big.
- A second geo-grid scanner, and Apple Maps rank: Local Falcon, Basic $49.99 or Pro $99.99 as the big cross-check;
  Reserve on small sites (Starter $24.99).
- Competitors' map-pack categories, ratings and review velocity: DataForSEO Business Data, Reserve at both sizes, about
  $0.0015 a profile [UNVERIFIED].

### Monthly cost of the stacks

| | Small | Big |
|---|---|---|
| **Default: free only** | $0 | $0 |
| **Main** | ≈ $15–20 | ≈ $140–200 |
| **Main + Cross-check** | ≈ $15–24, or ≈ $35–44 with Moz Starter Medium during active link building | ≈ $400–710 |

- **Default:** $0 at every size. The BigQuery rows (the Search Console export and the CrUX popularity rank) need a
  Cloud project with billing and stay $0 within BigQuery's free tier. A `QueryUsagePerDay` custom quota set with
  headroom (0.025 TiB a day) limits queries, but Google calls custom quotas approximate, so check BigQuery's billing
  report monthly.
- **Small Main:** DataForSEO ≈ $12–13 (rank SERPs ≈ $9.50 for 2 pairs, backlinks ≈ $1.50, Autocomplete ≈ $0.50,
  keyword SERPs $0–0.80, volumes ≈ $0.10, AI Mode ≈ $0.26, Maps grid ≈ $0.15–0.65 if local), `ai_probe` ≈ $3–6,
  SE Ranking ≈ $0.20–0.60. Everything else is $0. Cash up front: the $50 DataForSEO top-up and the $50 SE Ranking
  wallet (neither expires), plus prepaid AI API credit.
- **Small cross-checks** add Labs (≈ $0.13 per covered pair, $0 for a GE-only site) and On-Page ($0.10–3.40). Moz
  Free, Ahrefs `domain-rating-free`, SerpApi Free, Clarity, GA4 and the scripts cost $0.
- **Big Main:** Screaming Frog ≈ $23 (£199 a year; the USD figure is [UNVERIFIED]), DataForSEO ≈ $105–145 (volumes
  ≈ $10, keyword SERPs ≈ $18, Labs ≈ $7.40, Autocomplete ≈ $12, backlinks $5–15, rank SERPs ≈ $50, AI Mode ≈ $5,
  Maps grid $6–25 if local), `ai_probe` ≈ $10–18, SE Ranking ≈ $1, BigQuery $0–10. No SEO subscription.
- **Big cross-checks** add Ahrefs Standard $249 (the one subscription, shared by the backlink, keyword, rank and
  AI-answer cross-checks), Brand Radar prompt packs $0–50, On-Page $3–102, SE Ranking in Labs markets ≈ $2,
  DataForSEO Bing SERP ≈ $5, Clickstream ≈ $0.75, and Local Falcon $50–100 if local.
- **Not included:** every Reserve tool (Semrush, Moz in Big, Similarweb, AlsoAsked, Yext and the rest).

Big Main sits below this file's ~$500+ budget stack; Main + Cross-check reaches it.

## Free tools

| Tool | Gives you | Limits / notes | Stack |
|---|---|---|---|
| **Google Search Console** | Your clicks, impressions, CTR, position by query/page/country/device · indexing (Pages report, URL Inspection) · sitemaps · Core Web Vitals · links (sample) · manual actions · "Search generative AI" setting and report (impressions only) | 16 months of data · UI export 1,000 rows · API 25k rows/request, 2,000 URL inspections/day/site | Main (default, small, big): the API through claude-seo (`claude_seo.py gsc-export`, `claude_seo.py run gsc_inspect.py`); in the default Technical list, URL Inspection is a Cross-check against `crawl.py`. Bulk export to BigQuery: Main (default, big), Reserve (small). Search generative AI report, Links and Crawl Stats exports: Reserve, use when a person exports them |
| **Bing Webmaster Tools** | Same for Bing, which powers Copilot and is reported to supply ChatGPT search (directional vendor data) · backlinks (own site) · IndexNow · AI Performance report (citations; public preview) [3rd-party] | API key in BWT | Main (default, small, big): the API, through a client (to build). Crawl methods: Cross-check (default, small, big). Positions: Cross-check (default), Main (small, big). Keyword API: Cross-check (default), Reserve (small, big). AI Performance export: Reserve, use when a person exports it |
| **Google Analytics 4** | Conversions and engagement from organic traffic · landing pages | Organic queries come from GSC, not GA4 | Main (default, small, big). AI-referral sessions: Main (default), Cross-check (small, big) |
| **PageSpeed Insights / CrUX** | Real-user Core Web Vitals (p75, 28 days) and Lighthouse lab audits | Free API key raises the quota (`psi.py`) · CrUX API 150 QPM · History API up to 40 weeks | Main (small, big): CrUX API and History API for field data (to build), with `psi.py` for lab data. Default: CrUX API and History API Main, `psi.py` a Cross-check (lab against field). CrUX on BigQuery: Reserve, use when field data must be split by country. CrUX popularity rank: Main (default), Cross-check (big), Reserve (small) |
| **Rich Results Test · Schema Markup Validator** | Google rich-result eligibility · full schema.org validation | Manual (no public API found) | Reserve: use when a new template needs Google's verdict before indexing, or markup goes beyond Google's rich-result types |
| **Google Keyword Planner** | Google Ads volumes | Ranges (e.g. 1K–10K) unless the account has sustained ad spend; threshold undisclosed | Reserve: use when the client's Ads account spends and wants first-party numbers without a reseller |
| **Google Trends** | Relative interest over time and by region | API is alpha and application-only | Reserve: use when alpha API access is granted |
| **Ahrefs Free** (formerly Ahrefs Webmaster Tools) | For **your verified sites**: top 1,000 backlinks and keywords, site audit (5k crawl credits/project/month), web analytics | Verify the site first. The best free backlink view of your own domain | Reserve: use when a person exports own-site backlinks or keywords from the UI (no API). The separate `domain-rating-free` API endpoint: Main (default), Cross-check (small, big) |
| **Screaming Frog (free mode)** | Desktop crawler, 500 URLs | No JS rendering, custom extraction, API joins or saving crawls without a licence | Reserve: use when a person wants a GUI cross-check of `crawl.py` on 500 URLs or fewer |
| **Looker Studio** | Free dashboards on GSC + GA4 | — | Reserve: use when a person wants a live dashboard |
| **Wayback Machine CDX API** | History of competitor and own pages ("what changed before the drop") | `web.archive.org/cdx/search/cdx?url=…&output=json` | Cross-check (default, small, big): competitor page history. Reserve: use when a site move has no list of old URLs |
| **AlsoAsked free / Google PAA via search** | Question research | Paid AlsoAsked from $15/mo ($12/mo billed annually); API and MCP on Pro only | People Also Ask through the DataForSEO SERP API: Main (small, big); through WebSearch samples: Main (default), Cross-check (small, big). AlsoAsked: Reserve, use when a question hub of 100+ pages is planned |
| **This plugin's scripts** | Crawl, page audits, robots/AI-bot matrix, sitemaps, CWV, autocomplete ideas, GSC/log analysis, redirect QA, content scoring, competitor gaps, render diff, SERP clustering, triage, AI-visibility stats | See `scripts.md` | Main (default, small, big); each ranked script's rank is in the [Main stack](#main-stack). `psi.py`: Cross-check in the default stack. `keyword_ideas.py`: Cross-check (Bing suggestions in every list, Google suggestions in the default stack), Reserve (Google suggestions in the paid lists, YouTube in every list). `triage.py`, `serp_cluster.py`, `gsc_analyze.py` and `ai_visibility.py` run inside the ranked pipelines (crawl triage, SERP clustering, Search Console analysis, AI-answer statistics) and are not ranked separately. Not ranked: `content_score.py`, `translation_check.py` and `ai_text_check.py`, which are Main in the content skills that call them |
