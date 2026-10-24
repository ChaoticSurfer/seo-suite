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

Facts that are new to this file have their primary sources in [Sources for the Main stack](#sources-for-the-main-stack).

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
  the credit guard can't price it. The row says what the run uses until then. [Build order](#build-order) lists them.
- **(guard: …):** the call shape or cost needs a [credit guard change](#credit-guard-changes-the-stack-needs) first.

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

**When the paid lists take over.** The small and big paid lists in the category sections after this one apply only
when budgets or credentials for paid tools are configured (every credit-guard budget starts at 0), or when the user
asks. They take over per category, using the paid list for the site's size. A paid Main row whose vendor isn't set up
yet falls back to the default row that does the same job, so a partial setup never leaves a gap. Every tool in this
stack also has a label in the paid lists, where several are Cross-checks or Reserve.

**Reserve.** Each category's Reserve table applies to this stack too. A Reserve row marked "(paid lists)", "(small
sites)" or "(big sites)" covers only the paid lists. When its tool also sits in a list here, the row names that
default label, and the default label holds in this stack. Every paid tool is Reserve in this stack: it comes in when
its budget or credentials are configured, or when the user asks, and its "What free can't answer" line says what it
adds. The $0 ones that need a person (the Search Console and Bing exports, Ahrefs Free, Screaming Frog free mode, the
Rich Results Test, and Semrush Free from the [Semrush](#semrush) section) are the first to bring in. No row here calls
a paid tool, so the credit guard has nothing to deny. SerpApi and Moz are outside the guard and stay on their free
plans, which have no overage.

#### Free: keywords and competitors

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Research store (`research_store.py`) | Main | The reuse layer. It keeps every free source's values side by side, each with its source and date, so the cross-checks below compare like with like | Local script, no auth. Skills write only through `ingest`, `set-status` and `glossary add` | $0 | — |
| 2 | Search Console API, Search Analytics **(to build)** | Main | The only measured Google demand: impressions, clicks and position per query, page and country, in any language. With no paid volumes, impressions are the demand number the run prioritises by. Language comes from the URL path or the query's script | Service account that an owner adds as a property user, `webmasters.readonly`. Until the fetcher exists: exports, or the community `mcp-gsc` (audited and pinned) | $0 | 25,000 rows a request, 50,000 rows a day per search type, 2–3 days behind. It shows only queries the site already appears for |
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
| 9 | Chrome headless (`--dump-dom`) | Main | The unattended renderer for `render_diff.py`, in `claude -p` and launchd jobs | Local Chrome with `--timeout` and the default User-Agent. Own site only | $0 | One URL per template, not a rendered crawl of every page |
| 10 | `log_analyze.py` | Main | What Googlebot, Bingbot and AI bots actually fetched: crawl waste, errors served to bots, sitemap URLs never crawled, and crawl budget on big sites | Logs delivered to the run (host export, rsync, an S3 pull). Combined format and `.gz` only. `--verify-dns` | $0 | CDN logs (usually JSON) need a converter, which isn't built |
| 11 | Chrome DevTools MCP (official) | Main | Performance traces behind a poor field INP or LCP | Local stdio with `--headless --isolated --performance-crux=false --usage-statistics=false` | $0 | By default it sends trace URLs to CrUX and usage statistics to Google, hence the flags |
| 12 | IndexNow **(to build: submitter)** | Main | Finishes the job after a fix ships: changed URLs reach Bing, Yandex, Seznam, Naver and Yep | Measurement owns the submitter and schedule. Autonomy level 3 and above | $0 | Google doesn't use it |
| 13 | Search Console URL Inspection API **(to build)** | Cross-check | Google's verdict on the URLs that `crawl.py` and the sitemap describe: indexed or not, Google-chosen against declared canonical, last crawl, robots state and rich results. Crawl and Google agreeing lets the run act. A sitemap URL the crawl calls indexable but Google doesn't index, or gives another canonical, goes to a re-check first | Measurement owns the quota and schedule; Technical reads the results. Up to 2,000 URLs: every URL weekly. Above: changed URLs, money pages and a rotating sample per template | $0 | 2,000 inspections a day per property, 600 a minute. Indexed version only, no live test |
| 14 | `psi.py` (PageSpeed Insights API v5) | Cross-check | Lab against field: compares Lighthouse LCP, CLS and TBT per template with CrUX's p75. Field poor but lab good points to real-user conditions, so the run traces it with row 11 before acting. A lab regression after a release shows before the 28-day field window moves. Its audit also names the LCP element and the biggest opportunities. Where CrUX has no data, it is the only speed signal, reported as lab | Set `psi_api_key`. On 429 the run continues without PSI | $0 | Google recommends a key for automated queries and publishes no quota |
| 15 | Bing Webmaster Tools crawl API (`GetCrawlStats`, `GetCrawlIssues`, `GetUrlInfo`, `FetchUrl`) **(to build: Bing client)** | Cross-check | Compares Bing's crawl counts and errors with `log_analyze.py` and `crawl.py`, and `FetchUrl`'s result with our own fetch, which catches a CDN or WAF serving bots differently. Weekly, and always when there are no logs | The same Bing client as Measurement | $0 | — |

**What free can't answer**

- A rendered crawl of every page, with structured-data validation, near-duplicates past 600 pages and crawl
  comparison: Screaming Frog licence, £199 a year (≈ £17 a month) per user, Main on big sites and Reserve on small.
- A second crawl from other IPs, which catches geo-, IP- or User-Agent-dependent serving and WAF blocks: DataForSEO
  On-Page, ≈ $0.10–3.40 small, ≈ $3–102 big.

#### Free: rank and AI-answer visibility

| # | Tool | Role | Why | How a run drives it unattended | Cost | Notes |
|---|---|---|---|---|---|---|
| 1 | Search Console API, Search Analytics **(to build)** | Main | First-party clicks, impressions and average position by query, page, country, device and date. AI Overview and AI Mode appearances count inside Web. It feeds `gsc_analyze.py` and the per-country CTR curve | The same fetcher as Keywords. Each run re-pulls only the last ~3 days. Big sites: one request a day per country filter | $0 | 1,200 queries a minute per site. Don't compare impressions or position across 2025-05-13 to 2026-04-27 |
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
| 1 | Search Console API: Search Analytics, URL Inspection, Sitemaps **(to build)** | Main | Google's own clicks, impressions and positions for 16 months, its indexing verdict per URL, and `sitemaps.submit` at level 4. Owns the URL Inspection quota for every category | Service account as a property user: `webmasters.readonly`, plus `webmasters` only for `sitemaps.submit` at level 4. Up to 2,000 URLs: every URL weekly and changed URLs daily. Above: changed URLs plus a fixed sample per template | $0 | 2,000 inspections a day per property. Google publishes no Search Console MCP. Never script the Search Console UI |
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

### Keywords and competitors

For each market-language pair: what people search for, how often (volume and seasonality), how hard it is to rank,
the intent and questions behind it, and which competitor domains win those searches with which keywords. The run
clusters and prioritises the keywords each page should own and writes them to the research store (`seo-research/`).

Georgia is a special case. Google Ads has no Georgian language criterion, so GE-ka and GE-ru keywords go into the same
location-only tasks. DataForSEO Labs has no Georgia location, so Georgian competitor databases come from SE Ranking.

**Small sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Research store (`research_store.py`) | Main | The reuse layer. `status` lists stale or missing datasets per locale, so paid calls cover only the gaps. Each value keeps its source and date, so values from two sources sit side by side for the cross-checks | Local script, no auth, runs in every scheduler. Skills write only through `ingest`, `set-status` and `glossary add`. Semrush values stay within 30 days and out of commits | $0 |
| 2 | Search Console API, Search Analytics **(to build)** | Main | The only measured demand: impressions, clicks and position per query, page and country, in any language. The free check on every vendor volume. It has no language dimension, so ka, ru and en come from the URL path or the query's script | Service account that an owner adds as a property user, `webmasters.readonly`. 25,000 rows a request, 50,000 rows a day per search type, 2–3 days behind. Until the read-only fetcher exists: exports, or the community `mcp-gsc` (audited and pinned) | $0 |
| 3 | DataForSEO Keywords Data: Google Ads (`search_volume`, `keywords_for_site`) | Main | Google's own Ads volumes, with 12 monthly values for seasonality. Exact for Georgia (2268) and its cities. `keywords_for_site` gives Google's ideas for a competitor's domain, the cheapest competitor-topic source in Georgia | Connector, Standard queue (`task_post`, free `tasks_ready`, `task_get`), priced by the guard. Keywords up to 80 characters and 10 words | $0.06 a task of up to 1,000 keywords. A quarterly shortlist plus 3 competitors ≈ $0.10 |
| 4 | DataForSEO SERP API (Google organic, People Also Ask) | Main | The observed top 10 per keyword and locale: competitor domains and their share of top-10 slots, SERP features and PAA questions. `serp_cluster.py` groups keywords by overlap. Where vendor databases are thin, as in Georgian, this is the most trustworthy competitor evidence | Same connector, Standard queue. `ingest serps` writes competitors and questions to the store | $0.0006 a SERP. 300 keywords × 2 pairs ≈ $0.36 a snapshot, $0 for keywords rank tracking already holds. ≈ $0–0.80 |
| 5 | DataForSEO Google Autocomplete API | Main | Idea expansion through an official API with exact location. It replaces the unofficial autocomplete endpoints as the main idea source | Same connector, Standard queue, cluster-head seeds only | $0.0006 a task. 30 seeds × ~40 expansions × 2 pairs ≈ $1.44 a quarter, ≈ $0.50 |
| 6 | SE Ranking Data API **(to build: guard prices)** | Main | The cheapest competitor keyword lists and gaps, with a Georgia database (`ge`). `domain/keywords`, `domain/keywords/comparison` and `domain/competitors` cost 100 credits a request for up to 1,000 rows. Records carry volume, difficulty, intent and a 12-month trend | Data API key or MCP (`https://api.seranking.com/mcp`), reads only, server named `seranking`. Until the guard has its prices it allows 5 calls a run, so competitors come from rank 4 meanwhile | ≈ $0.20–0.60 (1,000–3,000 credits). A $50 wallet up front, which never expires |
| 7 | `compare_pages.py` | Main | Compares our page with the pages that win its keyword: size, structure, schema, trust signals, and the phrases competitors share that our page never mentions | Plugin script, no auth. Competitor URLs come from the stored SERPs | $0 |
| 8 | DataForSEO Labs (`ranked_keywords`, `domain_intersection`, `bulk_keyword_difficulty`) **(guard: rows)** | Cross-check | Compares a competitor's keywords and positions with SE Ranking for the same domain and market, and Labs difficulty with SE Ranking's and our SERP-based winnability. Worth it quarterly in markets Labs covers, when the gap list will create pages. **No Georgia** | Same connector, Live only, always with `limit`. As shipped the guard clamps `limit` to `max_rows` (50) | ≈ $0.13 per covered pair. $0 for a GE-only site |
| 9 | `keyword_ideas.py`, Bing suggestions | Cross-check | Compares Bing suggestions with DataForSEO's Google suggestions for the same seeds. Only Bing is a different source: the script's Google and YouTube modes call the same Google service. A phrase both engines suggest ranks higher. Free, so run it on cluster heads each quarter | No auth. Unofficial, undocumented endpoints, a deliberate exception: `--delay` 0.25 s or more, modest volumes | $0 |
| 10 | Competitor sitemap inventory **(to build: polite mode)** | Cross-check | Compares what competitors publish (URL templates, new sections by first-seen date) with the keyword lists from SE Ranking, Labs or `keywords_for_site`. A section with no vendor keywords points to a gap in the vendor's database, common in ka and ru. Confirm it with a SERP check. Free, so run it on every monthly gap pass | Until a polite mode exists (robots.txt, one request at a time per host, stop on 403, 429 or a challenge, snapshot diffs): `sitemap_check.py --sample 0 --urls-out` on competitors, diffed outside the script. Store URLs only, never page text | $0 |
| 11 | WebSearch SERP samples (`seo-serp-researcher` agent) | Cross-check | Compares the top-10 domains and the main page type for 20–50 head terms with DataForSEO's SERP. If both agree, act. If not, re-check with DataForSEO | Claude's own WebSearch and WebFetch, allowed in `--allowedTools`. Tag [measured: WebSearch sample] | $0 (session tokens) |
| 12 | Wayback Machine CDX API | Cross-check | Compares first-seen dates from our sitemap snapshots with the archive's first capture of the same competitor URLs, and backfills history before our first snapshot. Run it when a competitor section appears or a competitor gains | Free public API with no key (`web.archive.org/cdx/search/cdx?url=…&output=json`), at a polite rate | $0 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Research store | Main | As Small. Its TTLs keep paid spend proportional to change, not to site size: volumes and SERPs refresh after 30 days, competitors after 90 | As Small | $0 |
| 2 | Search Console API **(to build)** | Main | As Small, for the freshest days | As Small | $0 |
| 3 | Search Console bulk export to BigQuery | Main | No row cap, and anonymised-query totals: the long tail and per-language splits that the API truncates. It doesn't backfill, so turn it on at onboarding | An owner turns it on once (needs Cloud billing). Runs read it through Google's official BigQuery MCP (`https://bigquery.googleapis.com/mcp`) with only `execute_sql_readonly` exposed. At most 3,000 rows and 3 minutes a call, so aggregate in SQL | $0 within BigQuery's free tier (10 GiB stored, 1 TiB of queries), then $6.25 a TiB. Usually $0–10 |
| 4 | DataForSEO Google Ads | Main | As Small, in bulk | As Small, up to 100 tasks per POST | 20,000 keywords a pair monthly is 120 tasks ≈ $7.20, plus `keywords_for_site` for 10 competitors in 4 locations ≈ $2.40. ≈ $10 |
| 5 | DataForSEO SERP API | Main | As Small, for thousands of keywords per locale. It drives share of voice and SERP-overlap clustering | As Small | 5,000 keywords × 6 pairs ≈ $18, less the keywords rank tracking already holds |
| 6 | SE Ranking Data API **(to build: guard prices)** | Main | The competitor-keyword database for the GE pairs and any market Labs lacks. Cheap per row: 1,000 rows for 100 credits | As Small | 10 competitors × `ge` × 10 pages of 1,000 rows ≈ 10,000 credits ($2) a quarterly pull. ≈ $1 |
| 7 | DataForSEO Labs (`ranked_keywords`, `domain_intersection`, `competitors_domain`, bulk difficulty and traffic) **(guard: rows)** | Main | The cheapest bulk competitor-keyword and traffic-estimate database where it has data: 94 countries, here GB, IL and DE. **No Georgia** | Same connector, Live only, explicit `limit`. The free `dataforseo_labs/status` endpoint shows database freshness | 10 competitors × 3 covered pairs × 5,000 keywords ≈ $19.80 a quarterly pull, plus bulk difficulty ≈ $2.40 a refresh. ≈ $7.40. Under the current 50-row clamp a pull costs ≈ $54 |
| 8 | DataForSEO Google Autocomplete API | Main | As Small, for thousands of seeds | As Small | 200 seeds × ~48 expansions × 6 pairs ≈ $35 a full expansion, run quarterly. ≈ $12 |
| 9 | `compare_pages.py` | Main | As Small | As Small | $0 |
| 10 | SE Ranking Data API in Labs markets **(to build: guard prices)** | Cross-check | Compares a competitor's keyword set and positions with Labs `ranked_keywords` for the same domain and market. A keyword both report enters the gap list. A keyword in only one gets a SERP check first. Worth it on every quarterly pull, because it costs almost nothing | As Small | ≈ $6 a pull for 3 databases. ≈ $2 |
| 11 | Ahrefs API v3 **(to build: REST client)** | Cross-check | A fourth database, with clickstream-based volume, its own difficulty and top pages by traffic. Compares head-term volume and difficulty with DataForSEO's Google Ads volume and SE Ranking's difficulty, and a competitor's top pages with Labs. A gap of more than about 2× on a head term [heuristic] is settled by GSC impressions or a SERP check. Georgia only as ka-GE. Worth it for decisions about new sections or markets | REST v3 with an API key, never the MCP (its terms forbid scripts). The hook doesn't see REST calls, so the client checks the free `subscription-info/limits-and-usage` and the guard's ledger before each run. 10-unit fields only on shortlists | $0 extra on the Ahrefs Standard plan priced under [Backlinks](#backlinks-and-authority). Dropped if that plan is dropped |
| 12 | DataForSEO Clickstream (`bulk_search_volume`) **(guard: price)** | Cross-check | Clickstream volume is measured differently from Google Ads, which merges close variants and rounds. Compares head-term volumes. A large gap flags merged variants or a seasonal spike. Only when a covered market is a target: Georgia coverage is [UNVERIFIED] | Same connector, Live only. The guard has no price for it, so it counts each call at 5% of the DataForSEO budget | 2,000 head terms × 3 covered pairs ≈ $0.75 |
| 13 | CrUX popularity rank (BigQuery) | Cross-check | Google's own popularity band per origin, from Chrome navigations. Compares each competitor's band with vendor traffic estimates. A vendor saying "larger than us" against a lower band makes the estimate suspect. Free, so run it each quarterly competitor review | BigQuery with the service account used for the Search Console export. Bands by country come from `rank` in the materialized `country_summary` table | $0 within the free tier |
| 14 | `keyword_ideas.py`, Bing suggestions | Cross-check | As Small | As Small | $0 |
| 15 | Competitor sitemap inventory **(to build: polite mode)** | Cross-check | As Small, and the publishing rate per section. Confirm templates with no ranked keywords by a SERP check before sending them to seo-programmatic | As Small | $0 |
| 16 | WebSearch SERP samples (`seo-serp-researcher` agent) | Cross-check | As Small, on the head terms of each pair | As Small | $0 (session tokens) |
| 17 | Wayback Machine CDX API | Cross-check | As Small | As Small | $0 |

**Reserve**

| Tool | Use when … |
|---|---|
| Semrush (official MCP; Starter $199 or Pro+ $299, 50,000 units) | The owner already pays Starter or Pro+, **and** a scheduled `claude -p` run has kept a working sign-in for two weeks, or Starter is shown to issue an MCP API key (both unverified). Then read up to 40% of its units, with fixed row limits, as a third Georgian database beside SE Ranking. For a small site, also: SE Ranking returns fewer than 100 keywords for a competitor that holds 5 or more of our tracked top-10 slots. Not Main: a fixed $199 for data that costs a few dollars pay-per-use, and its unattended sign-in is unproven. The $139 SEO plan lists no MCP access |
| Ahrefs API v3 (small sites) | Ahrefs Lite or higher is already paid for links and the REST client exists. Then spend a few units on difficulty and a competitor's top pages. Its MCP is for sessions someone is watching |
| Google Keyword Planner (UI export, or the Ads API) | The client runs Google Ads with sustained spend and wants first-party numbers without a reseller, or DataForSEO is unavailable. Not a cross-check: DataForSEO resells the same Google Ads data |
| Google Trends (API alpha) | Alpha access is granted, for consistently scaled 5-year interest by country and sub-region. Never scrape trends.google.com. DataForSEO's 12 monthly values already cover seasonality |
| Keywords Everywhere (API and MCP) | The markets are among its public checker's countries (US, UK, CA, AU, IN, NZ, ZA) and the team already uses its extension, for spot checks in watched sessions. Its volumes come from Keyword Planner, so it is not an independent cross-check. No Georgia. Credits expire after a year |
| AlsoAsked (Pro: API and MCP) | A question hub of 100 or more pages is planned, and one test query shows it returns Georgian or Russian questions for Georgia (repeats with `fresh=false` are free). Take Pro ($59) for that month. It re-measures Google PAA, which DataForSEO already collects. The guard counts it in the shared "other" bucket |
| AnswerThePublic | A person brainstorms question phrases in a watched session and saves them as seeds. No API or MCP |
| SpyFu (API on Pro + AI or Team) | The work needs a competitor's historical Google Ads keywords and ad copy in one of SpyFu's 16 countries. No Georgia or Israel |
| Moz API | A stakeholder reports Moz keyword metrics or Domain Authority. Free tier 50 rows a month; Starter Medium $20 for 3,000 rows with no overage. Its official MCP is in beta on paid plans. It adds no locale the Main tools lack |
| Ahrefs Free (UI) | A person wants Ahrefs' view of the verified site's top 1,000 keywords. UI only |
| Semrush Traffic & Market (.Trends API) | An enterprise client needs Semrush's panel traffic and audience data instead of Similarweb: $289 a month per user (annual) plus a separate quarterly Trends API subscription |
| Similarweb (MCP; API-only, Business or Enterprise plan) | A board-level market-sizing decision is due in a market Similarweb covers and an API contract is budgeted (quote-only; third parties report $15,000–40,000 a year [UNVERIFIED]). Then compare its visits with Labs and SE Ranking estimates as an order of magnitude only. The guard counts it in the shared "other" bucket |
| Bing Webmaster Tools keyword API (`GetKeywordStats`, `GetRelatedKeywords`) (paid lists) | Bing has 10% or more of the site's search clicks (Bing Webmaster clicks against Bing plus Search Console clicks), for a free second engine's demand numbers. No Bing client is built yet, and Georgian support is unverified. In the default free stack it is a Cross-check |
| Google Ads MCP (official, read-only) | The site runs Google Ads: its search terms report gives real queries with impressions. It has no Keyword Planner |
| Search Console bulk export (small sites) | Search Console API pulls hit 50,000 rows a day per search type. In the default free stack it is Main |
| DataForSEO Clickstream (small sites) | A covered market is a target and one volume decides whether a page gets built |
| YouTube Studio, vidIQ, TubeBuddy | A YouTube channel is in scope. A person reads them; no run connects |
| `keyword_ideas.py`, Google and YouTube suggestions (paid lists) | Google: DataForSEO Autocomplete is unavailable for a run (its budget is used up, or an outage). In the default free stack the Google mode is a Cross-check against Search Console queries. YouTube, in every list: a YouTube channel is in scope and video-search phrases are wanted, which no other tool here gives. Both modes call the same unofficial Google endpoint, so keep `--delay` at 0.25 s or more |
| CrUX popularity rank (small sites) | A Cloud project with billing already exists, for example for the Search Console export, and a competitor's vendor traffic estimate decides its priority. Then compare its band with SE Ranking's estimate, as in the big list. In the default free stack it is Main |

### Backlinks and authority

Who links to us and to our competitors, which links were gained or lost this week, how strong and clean the linking
sites are, and which domains link to competitors but not to us. seo-links acts on it: reclamation redirects through the
autonomy levels, a prospect list, and the disavow decision, which stays gated at every level.

**Small sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | DataForSEO Backlinks API | Main | The only backlink source already wired end to end: connector, guard prices and the weekly B5 delta pipeline. Own and competitor summaries (including broken backlinks and broken pages), referring domains, anchors, and new and lost links. `domain_intersection` takes 20 targets and 10 excluded, so "links to competitors but not to us" is one call. Bulk rank and spam score take 1,000 targets a request. Its depth in .ge and Russian-language sites is unmeasured [UNVERIFIED] | Connector with the login in the keychain. Live only, 30 simultaneous requests. A dashboard daily spend limit makes calls fail (40203) rather than overspend. As shipped the guard clamps `limit` to `max_rows` (50) | Own site + 3 competitors: weekly deltas ≤ $1.39, a quarterly gap ≈ $0.03, a 1,000-target prospect score $0.06. ≈ $1.50 |
| 2 | Bing Webmaster Tools API (`GetLinkCounts`, `GetUrlLinks`) **(to build: Bing client)** | Main | Free first-party links from a search engine's own crawl, independent of every vendor, with the source URL and anchor for each linked page. The free floor when paid budgets are 0. A sample only: verified sites, no nofollow flag, no first-seen date | API key (one per user, for all their verified sites) or OAuth, on the JSON endpoint. A weekly snapshot diff gives new and lost links. Until the client exists: the community `zizzfizzix/mcp-server-bwt`, audited and pinned | $0 |
| 3 | Moz API (Free; Starter Medium during active link building) | Cross-check | A second independent index with DA, PA, Spam Score, Link Intersect (up to 6 targets) and 60-day gained and lost linking domains. Monthly on Free: DA, PA and Spam Score for own site, 3 competitors and shortlisted prospects (≤ 50 rows), against DataForSEO's rank and spam score and Ahrefs DR. When two of three call a prospect weak, drop it. Starter Medium adds monthly gained and lost domains against DataForSEO's lists: a loss both report is real | JSON-RPC API (`x-moz-token` header) or the official MCP (beta, paid plans, account owners) with a Bearer key. Outside the guard, so only Free or Starter Medium, which has no overage. The free tier needs a card at sign-up, which the user enters | $0 on Free. $20 on Starter Medium, only while link building is an active goal |
| 4 | Ahrefs `domain-rating-free` (public API v3 endpoint) **(to build: client)** | Cross-check | Domain Rating for up to 1,000 targets per POST at 0 units: a third authority opinion. A large rank-order gap between DR, DA and DataForSEO rank flags inflated metrics or an index gap, and that domain gets a live check before it reaches the prospect list. Always worth it, because it is free | REST with a v3 key kept in the keychain. The endpoint docs say keys are free on a free account; Ahrefs' help page says new keys need Lite, so confirm once. Every DR shown needs "Domain Rating by Ahrefs" with a link next to it | $0 |
| 5 | `page_audit.py --facts` on the linking page | Cross-check | Ground truth: whether the link exists now, and its rel and anchor. Run it on every link a vendor reports lost before it goes on the reclamation list, and on every new campaign link. Vendor says lost but the page links: index lag. Vendor says new but the page shows nofollow or sponsored: reclassify. Always worth it | Built in. Check the host with `robots_check.py` first, and send one request at a time per host. Raw HTML only. Challenges are reported, never bypassed | $0 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | DataForSEO Backlinks API | Main | As Small, for own site + 10 competitors, with one `domain_intersection` per market (the ka, ru and en competitor sets) and our domain excluded | As Small | Weekly deltas ≈ $3.80, monthly intersections and about 10,000-target scoring ≈ $1–10. ≈ $5–15 |
| 2 | Bing Webmaster Tools API **(to build: Bing client)** | Main | As Small. Also the cheapest independent check on both paid indexes for the own site | As Small. Page through `GetLinkCounts`, then `GetUrlLinks` per target page, spread across the week. Quotas are [UNVERIFIED], so back off on errors and keep the last snapshot | $0 |
| 3 | Ahrefs API v3, Standard **(to build: REST client)** | Cross-check | The deepest second index: `link-intersect-refdomains`, `broken-backlinks`, referring-domain and DR history, and new and lost links with `history=since:<date>`. Compares referring-domain counts and trends per domain with DataForSEO monthly. A gap prospect both find goes first; a loss both report is real. DR is the metric most stakeholders know. The Big stack's only SEO subscription, and it also feeds the keyword, rank and AI-answer cross-checks. Worth it when links are a KPI or those cross-checks are wanted | REST v3 only: ToS §4.4(j) allows automated use only through the API, and the MCP terms forbid scripts. The client prices calls as max(50, rows × field costs) and checks `subscription-info/limits-and-usage` (free) and the guard's ledger before each run. 60 requests a minute, 250 rows a request. Cap the key's units and turn off pay-as-you-go | $249 (Standard, 800,000 units) |
| 4 | `page_audit.py --facts` on the linking page | Cross-check | As Small. It decides which of two disagreeing indexes is right | As Small, batched in a subagent | $0 |
| 5 | Ahrefs `domain-rating-free` (public API v3 endpoint) **(to build: client)** | Cross-check | As Small: a free third authority opinion beside DataForSEO rank and, when Standard is paid, Ahrefs' own metrics. It scores the about 10,000 prospect targets at 0 units, which saves Standard's units for history and link lists. Always worth it, because it is free | As Small, 1,000 targets per POST | $0 |

**Reserve**

| Tool | Use when … |
|---|---|
| Moz API (big sites) | Stakeholders report DA or Spam Score, or a disavow discussion needs a second spam opinion. Starter Large $75 (15,000 rows) or Growth Small $125 (50,000). Both bill overage ($5 per 1,000 rows, $25 per 10,000) and the guard can't see Moz, so add a guard entry first or stay on Starter Medium. In the default free stack the Free tier is a Cross-check |
| Ahrefs API v3, Lite (small sites) | Competitive link building, or a penalty investigation that needs link history, is the plan's main goal and $129 fits. REST v3 only, never the MCP in scheduled runs |
| Semrush backlinks (official MCP) | Semrush is already paid (see the keywords Reserve) and one `backlinks_overview` per domain a month (40 units) is wanted as a further opinion. Never per-line backlink lists in pipelines (40 units a line). Backlink Audit toxicity is UI-only |
| Majestic (API plan) | An unnatural-links manual action is open, or a migration link audit is scheduled. Take the API plan ($399.99, or $333.33 a month billed annually) for that month and call `GetIndexItemInfo` (100 items a call: Trust Flow, Citation Flow, topical Trust Flow). Lite and Pro have no API. No MCP, and the guard doesn't know it |
| SE Ranking Backlinks API | SE Ranking already holds the wallet and the guard has its prices. Its daily new and lost endpoint (10 credits a target plus 1 a date point) is a cheap change detector. Per row it costs about $0.0002 against DataForSEO's $0.000036, and SE Ranking doesn't say it runs its own crawler |
| Search Console Links report | A person is present, quarterly or during an unnatural-links manual action: export "Latest links" and "More sample links" (up to 100,000 rows each) into `seo-work/`. The Search Console API has no links resource |
| Ahrefs Free (UI) | A person is present and there is no paid Ahrefs plan: a quarterly export of the verified site's top 1,000 backlinks and its broken backlinks |
| Common Crawl web graph (paid lists) | A free, citable domain-level view across 50 or more competitor domains is needed, such as a quarterly market study (the Aug–Oct 2026 domain graph has 135.0M nodes and 1.8B edges; the edges file is 7.1 GiB). No anchors, URLs or dates. Common Crawl recommends legal advice before commercial use. In the default free stack it is Main |
| Moz Pro | A stakeholder works in Moz Pro's interface. Moz Pro includes no paid API access, so no run reads it |

### Technical

Can every page that should rank be crawled, rendered and indexed? Is it fast for real users, and is its structured
data eligible? What do search and AI bots actually fetch, and did a shipped fix take effect?

**Small sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | `crawl.py` | Main | The core crawl: broken links, links to redirects, duplicates, click depth, orphans against the sitemap, bad canonical targets, hreflang return links and a soft-404 probe, plus `page_audit` and `schema_rules` on every page. Its CSV feeds `triage.py` and the research store. Raw HTML only, one host per crawl, near-duplicates on the first 600 pages | Standard library, no key, any scheduler. It obeys robots.txt, stops when robots.txt returns 5xx or 429, and reports a Cloudflare challenge without bypassing it | $0 |
| 2 | `sitemap_check.py` | Main | The URL inventory that sets the class (`total_urls`). Checks lastmod, file limits, and a sample of listed URLs for non-200, noindex and non-canonical pages | Run `--urls-out` first, so later steps reuse the list | $0 |
| 3 | `robots_check.py` | Main | Google-style robots.txt evaluation, plus the access matrix for 22 search and AI crawlers and Content-Signal lines. `--file` tests a draft before deploy, so the run blocks a bad change rather than reporting it | It has no `--fail-on`, so CI wraps it in the documented one-liner | $0 |
| 4 | `page_audit.py` | Main | One URL per template: headers, redirect chain, canonical, hreflang (it maps "ge" to "ka"), headings, JSON-LD and challenge detection. In CI, `--file --fail-on high` blocks a regression before it ships | CI downloads the preview HTML (with `x-vercel-protection-bypass` where needed) and runs `page_audit.py --file --base-url <production URL> --fail-on high`. A live run covers headers | $0 |
| 5 | `redirect_check.py` | Main | Checks that every old URL in a redirect map 301s or 308s to its new URL in one hop, and that the new URL is a 200, indexable, self-canonical page. This is how a run knows a shipped redirect fix took effect | A CSV map with old and new columns | $0 |
| 6 | Search Console URL Inspection API **(to build)** | Main | Google's own verdict per URL: indexed or not, Google-chosen against declared canonical, last crawl, robots state, and detected rich results with their issues. 2,000 a day per property covers a small site. Indexed version only, no live test | Measurement owns the quota and schedule; Technical reads the results. Service account, `webmasters.readonly`, 600 a minute | $0 |
| 7 | `schema_rules.py` | Main | Google's rich-result requirements as pure data, run on every crawled page and on the rendered DOM. Knows retired features (FAQ, HowTo, sitelinks search box). Re-check it when Google changes its search gallery | Pure function inside the scripts | $0 |
| 8 | `psi.py` (PageSpeed Insights API v5) | Main | The Lighthouse lab audit per template: LCP element, biggest opportunities, failed SEO audits. Google plans to drop CrUX field data from this API, so field data comes from rank 9. Small sites often have no CrUX data, which makes lab data the main signal | Set `psi_api_key`: Google recommends a key for automated queries and publishes no quota. On 429 the run continues without PSI | $0 |
| 9 | CrUX API and History API **(to build: in `psi.py`)** | Main | Field p75 LCP, INP, CLS, FCP and TTFB per origin or URL and form factor, LCP subparts, and up to 40 weekly points. Often origin-only or empty on small sites: record "no field data" and use lab | Free Cloud key, 150 queries a minute per project, which paying can't raise. History refreshes on Mondays, so the monitor runs on Tuesdays | $0 |
| 10 | `render_diff.py` | Main | Raw HTML against the rendered DOM: a title, robots or canonical that changes after JavaScript, and content or links that exist only after rendering. One URL per template settles whether a rendering crawler is needed at all | Rendered DOM from rank 11 | $0 |
| 11 | Chrome headless (`--dump-dom`) | Main | The simplest unattended renderer for `render_diff.py`: it prints the DOM after scripts run, with no MCP, and works in `claude -p` and launchd jobs | Local Chrome with `--timeout`. Keep the default User-Agent: a Googlebot UA from a non-Google IP looks spoofed. Own site only | $0 |
| 12 | `log_analyze.py` | Main | What Googlebot, Bingbot and AI bots actually fetched: crawl waste, errors served to bots, sitemap URLs never crawled, DNS-verified fake Googlebots. Lower here because shared hosts often give no complete logs | Logs delivered to the run (host export, rsync, an S3 pull). Combined format and `.gz` only. `--verify-dns` | $0 |
| 13 | Chrome DevTools MCP (official) | Main | Diagnoses a poor field INP or LCP with performance traces and insights, throttling and User-Agent emulation. It can save a DOM after interaction. Its Lighthouse audit has no performance category | Local stdio with `--headless --isolated --performance-crux=false --usage-statistics=false`: by default it sends trace URLs to CrUX and usage statistics to Google. Test it once under launchd | $0 |
| 14 | IndexNow **(to build: submitter)** | Main | Finishes the job after a fix ships: changed URLs reach Bing, Yandex, Seznam, Naver and Yep. Google doesn't use it | Measurement owns the submitter and schedule. Autonomy level 3 and above | $0 |
| 15 | Bing Webmaster Tools API (`GetCrawlStats`, `GetCrawlIssues`, `GetUrlInfo`, `FetchUrl`) **(to build: Bing client)** | Cross-check | Compares Bing's crawl counts and errors with `log_analyze.py`'s Bingbot hits and `crawl.py`'s errors, and `FetchUrl`'s result with our own fetch, which catches a CDN or WAF serving bots differently. Free, so weekly in the technical monitor, and always when there are no logs | The same Bing client as Measurement | $0 |
| 16 | DataForSEO On-Page API **(guard: page cap)** | Cross-check | A second crawler from other IPs, with optional JavaScript or browser rendering and microdata validation. Compares status codes, redirects, canonicals, duplicates (including pages past `crawl.py`'s first 600) and structured-data errors with `crawl.py`. Worth it quarterly with the full audit, after a release or migration, or when `render_diff.py` shows a template depends on JavaScript | Connector, Standard queue. As shipped the guard clamps `max_crawl_pages` to `max_rows` (50), so a full check needs its own page cap. Never set `robots_txt_merge_mode=override` | One 2,000-page crawl a quarter: $0.30 raw, $3.00 with JavaScript, $10.20 with browser rendering. ≈ $0.10–3.40 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Screaming Frog SEO Spider (licensed), CLI | Main | Crawls the whole site with Chromium rendering, structured-data validation, near-duplicates, custom extraction, crawl comparison, list mode for migrations, and Search Console, PSI and GA4 joined per URL | `--headless --crawl … --config … --save-crawl --export-tabs … --project-crawl-comparison true` from launchd or cron, on a machine with `licence.txt` and the accepted EULA. A licence per person who runs crawls. Keep the Ahrefs, Majestic and Moz integrations off (they spend those vendors' units), and its URL Inspection join off (it spends Measurement's quota) | £199 a year per user (≈ £17 a month) |
| 2 | `crawl.py`, per section | Main | A raw-HTML crawl per `--path-prefix` section, up to 2,000 pages each, in parallel subagents. Its output is the only crawl `triage.py` and the research store can ingest, so it stays Main until a Screaming Frog CSV adapter exists. A section that differs from Screaming Frog flags JavaScript dependence or drift in Screaming Frog's saved config | One section per subagent | $0 |
| 3 | `sitemap_check.py` | Main | As Small, per section and locale. It stops at 200 sitemap files, so on very large sites run it per child index | As Small | $0 |
| 4 | `robots_check.py` | Main | As Small. Test facet and parameter rules with `--path` | As Small | $0 |
| 5 | `log_analyze.py` | Main | Crawl budget is a real question at this size, and only logs answer it. CDN logs (usually JSON) need converting first, and no converter is built | As Small, logs pulled on a schedule | $0 |
| 6 | Search Console URL Inspection API **(to build)** | Main | 2,000 a day can't cover the site, so inspect changed URLs, money pages and a rotating sample per template. Whether separate URL-prefix properties per locale folder each get 2,000 a day is [UNVERIFIED] | As Small | $0 |
| 7 | CrUX API and History API **(to build: in `psi.py`)** | Main | Big sites more often have URL-level field data: sample the top URLs per template plus the origin | As Small | $0 |
| 8 | `psi.py` | Main | The lab audit per template, which explains poor field numbers | As Small | $0 |
| 9 | `page_audit.py` | Main | Each key template in full, and the CI gate that stops a template regression before it reaches thousands of URLs | As Small | $0 |
| 10 | `redirect_check.py` | Main | Migration maps and shipped redirect fixes at scale | `--workers 8` | $0 |
| 11 | `schema_rules.py` | Main | As Small | As Small | $0 |
| 12 | `render_diff.py` | Main | Decides which sections need Screaming Frog's rendering, which is far slower | As Small | $0 |
| 13 | Chrome headless (`--dump-dom`) | Main | As Small | As Small | $0 |
| 14 | Chrome DevTools MCP | Main | As Small | As Small | $0 |
| 15 | IndexNow **(to build: submitter)** | Main | After each release, changed URLs in batches of up to 10,000 | As Small | $0 |
| 16 | DataForSEO On-Page API **(guard: page cap)** | Cross-check | Compares status codes, redirects, canonicals, duplicates and microdata errors with Screaming Frog on sampled sections (5,000–20,000 pages). It catches geo-, IP- or User-Agent-dependent serving and WAF blocks that a crawl from one machine misses. Worth it after releases and migrations, and when Screaming Frog and `crawl.py` disagree | As Small | Per 1,000 pages: $0.15 raw, $1.50 with JavaScript, $5.10 with browser rendering. A monthly 20,000-page sample ≈ $3, $30 or $102 |
| 17 | Bing Webmaster Tools crawl API **(to build: Bing client)** | Cross-check | As Small, and against Screaming Frog's error lists | As Small | $0 |

**Reserve**

| Tool | Use when … |
|---|---|
| Screaming Frog, licensed (small sites) | Every template depends on JavaScript and crawls recur weekly, or near-duplicates must be checked past 600 pages. £199 a year |
| Screaming Frog free mode | A person wants a GUI cross-check of `crawl.py` on 500 URLs or fewer. No scheduling, saving, rendering or integrations, so it can't be a pipeline step |
| Screaming Frog MCP (licensed) | A person explores a saved crawl in a watched session. It needs the app running or Claude Desktop, and only the licensed user may use it |
| Screaming Frog Log File Analyser | Logs arrive in formats `log_analyze.py` can't read (W3C/IIS, Amazon ELB, HAProxy, JSON, CSV) and a person is present. GUI only, £99 a year |
| Sitebulb (Desktop, Cloud, read-only MCP) | The team already licenses it with scheduled audits, and the run reads finished audits through its MCP (50 sample URLs per issue). The MCP can't start or schedule a crawl |
| Lumar (GraphQL API, MCP add-on) | Hundreds of thousands to millions of URLs, crawls must run in the cloud with no machine awake, or the organisation already pays for it. Its API can start crawls (`runCrawlForProject`) with service-account keys. Quote-only |
| Botify | 1M+ URLs that need crawl, logs and Search Console in one platform, or it is already licensed. Its REST API can create and launch an analysis. Enterprise, quote-only, no official MCP found |
| SE Ranking Website Audit API | The guard has SE Ranking's prices. It then becomes a cloud-crawler cross-check like On-Page: a standard audit costs 2 credits a page (≈ $0.0004 at the wallet rate), and status and report reads are free |
| Built-in browser or Claude in Chrome | A person is present and a page needs their session, a challenge they pass themselves, or a Search Console or Bing export with no API. Neither runs in `claude -p` or launchd jobs |
| Google Rich Results Test | A new template or markup type needs Google's verdict before it is indexed. A person runs it. No API |
| Schema Markup Validator | Markup uses schema.org types beyond Google's rich results. No API. An unattended version would load the downloadable schema.org vocabulary (V30.1, CC BY-SA 3.0) into `schema_rules.py`; not built |
| CrUX on BigQuery | Core Web Vitals must be split by country (for example `country_ge`) or compared across many origins monthly. Needs a Cloud project with a card on file |
| Search Console Crawl Stats and Pages reports (UI) | No logs exist and a person exports Googlebot's own crawl breakdown. No API; Crawl Stats exists for root-level properties only |
| Ahrefs Site Audit | The site already pays Ahrefs Lite or higher and has a scheduled audit project. Read it through REST v3 (issues cost 50 units a request). The API can't start a crawl |
| Semrush Site Audit | The site already pays Semrush and stakeholders want its dashboard. Read the existing project through the MCP (≈ 400 units plus 100 per non-zero issue). Never call "snapshot info" (10,000 units) |
| Cloudflare AI Crawl Control | The site is on Cloudflare: check its AI-bot policies, which can put rules at the top of robots.txt. Dashboard only; CDN changes are gated at every level |
| Google Indexing API | The site has JobPosting or BroadcastEvent pages. It is not a general way to get pages indexed |
| Wayback Machine CDX API | A site move has no list of old URLs |

### Rank and AI-answer visibility

Where does the site rank per market, language and device, in Google and Bing and in AI answers (Google AI Overviews and
AI Mode, ChatGPT, Claude, Perplexity, Copilot)? Which competitors and cited domains sit around it, and did any of that
change enough to act on?

**Small sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Search Console API, Search Analytics **(to build)** | Main | First-party clicks, impressions and average position by query, page, country, device and date. AI Overview and AI Mode appearances count inside Web. It feeds `gsc_analyze.py` and the per-country CTR curve behind visibility and share of voice. Show it beside snapshot rank, never averaged with it. Don't compare impressions or position across 2025-05-13 to 2026-04-27 | The same fetcher as Keywords. Each run re-pulls only the last ~3 days. 1,200 queries a minute per site | $0 |
| 2 | DataForSEO Google Organic SERP API (AI Overview on the money tier) | Main | The only compliant source of fixed-condition rank snapshots and competitor positions: Google has no SERP API, and seo-suite must not query google.com. One task gives rank, URL, SERP features, AI Overview presence and its reference domains. Georgia 2268 (Tbilisi 1007469, Batumi 1007466; the US state 21143 is a trap), with ka, ru and en | Connector, Standard queue, up to 100 tasks a POST, free `tasks_ready`. Validate locale pairs against DataForSEO's lists at the start and fail loudly on an unsupported one. Snapshots go to the research store; the rank-snapshot store is to build | Per pair, at the B6 sizing (50 money keywords daily at depth 10, 450 weekly at depth 20): $3.22, plus $0.90 for AI Overview, plus ≈ $0.65 for daily runs during 2 weeks of rollouts a year. 2 pairs ≈ $9.50 |
| 3 | `ai_probe`: OpenAI, Anthropic and Perplexity APIs **(to build)** | Main | The only route to automated ChatGPT, Claude and Perplexity answers within the vendors' terms. Rows are labelled "API stand-in": OpenAI says its search API uses the same models and tool as ChatGPT Search, and Perplexity says API results differ from its UI. Locale through `user_location` (GE, Tbilisi), untested. Prompts written natively in ka and ru, and a brand alias table covers Latin, Mkhedruli and Cyrillic spellings. Rows go to `ai_visibility.py` for Wilson intervals | Three API keys. Model and tool version pinned per row, 3 runs per prompt. Routine probes on a small pinned model with one search (for example `claude-haiku-5-5` with `max_uses=1`). Outside the guard's hook, so the collector reads `other_monthly_usd`, `per_run_cap_pct` and the guard's ledger, records its own spend there and stops itself ([budget settings](#credit-guard-changes-the-stack-needs)). Perplexity's API Terms §5.1 make its performance confidential information, so named cross-vendor metrics that include Perplexity get legal review before any client report | 20 prompts × 2 languages × 3 engines × 3 runs = 360 probes: $2.70 in search fees plus tokens. ≈ $3–6 [estimate: about 10,000 tokens in and 1,000 out per probe] |
| 4 | DataForSEO Google AI Mode API **(guard: price row)** | Main | The only automatable AI Mode answers and cited references per keyword and locale. Its 43 languages include ru and en but not ka, so reports say GE-ka AI Mode is not measured | Same connector, `ai_mode/task_post` in the Standard queue. The guard has no AI Mode row and prices it at half ($0.0006 against $0.0012) | 50 money keywords × GE-ru weekly ≈ $0.26 |
| 5 | Bing Webmaster Tools API (`GetQueryStats`, `GetPageQueryStats`) **(to build: Bing client)** | Main | Free first-party Bing positions, clicks and impressions per query and page. Bing grounds Copilot. The methods take no country, device or date range, so the data is labelled "Bing, all markets" | Weekly pull into its own table. `gsc_analyze.py` already maps Bing's columns | $0 |
| 6 | Google Search Status Dashboard feed | Main | Google's own start and end dates for updates. The pipeline moves the money tier to daily during a rollout, holds alerts, and compares only a full week after the rollout ends | `GET https://status.search.google.com/incidents.json` once a run. No key; robots.txt allows it | $0 |
| 7 | SerpApi, Free plan **(to build: collector)** | Cross-check | A second SERP collector with its own parser and infrastructure. Compares `rank_absolute` for the same keyword, locale and device on the same day with DataForSEO, only for keywords about to alert (entering or leaving the top 3 or top 10, or a move of 3+ positions held for 2 snapshots). Alert when both agree within 2 positions. Otherwise record "collector disagreement" and re-check on the next run. Worth it whenever an alert reaches a client | REST with `api_key` from the environment, `gl=ge`, `hl=ka` or `ru`. Outside the guard: the free plan has no overage, and the collector counts its own calls. The Legal Shield covers only Production ($150) and higher | $0 within 250 searches a month (50 an hour) |
| 8 | GA4 AI-referral sessions (`analytics-mcp`) | Cross-check | Real sessions from chatgpt.com, perplexity.ai, claude.ai, copilot.microsoft.com and gemini.google.com landing on cited pages. Compares the direction of `ai_probe`'s citation rate per engine with referral sessions to the pages that engine cites. Citations rising while referrals stay flat mean the prompts miss real demand, or citations earn no clicks. Direction only, never levels. Free, so in every monthly report | Read-only, service-account impersonation, `analytics.readonly` | $0 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Search Console API **(to build)** | Main | As Small, with one request a day per country filter. The CTR curve is fitted per country and device and refitted quarterly | As Small. One property's requests at a time; on a quota error, retry once after 15 minutes, then fail loudly | $0 |
| 2 | Search Console bulk export to BigQuery | Main | Removes the 50,000-row cap and flags anonymised queries. Average position = SUM(sum_top_position) / SUM(impressions) + 1 | As in Keywords; shared and counted once | As in Keywords |
| 3 | DataForSEO Google Organic SERP API | Main | Snapshot rank, SERP features, AI Overview and competitor domains for the whole locale matrix, desktop and mobile. Share of voice and AI Overview citation share for us and every competitor come from the same data. Keyword sets are versioned | As Small. Tag each task with project, locale, device and keyword-set version | 200 keywords × 6 pairs × 2 devices weekly at depth 20 with AI Overview ≈ $19, a daily money tier (50 × 6 × 2) ≈ $11, a monthly depth-100 run ≈ $14.40 (the guard caps depth at 50 until limits are per endpoint), and a rollout allowance ≈ $5. ≈ $50 |
| 4 | `ai_probe` **(to build)** | Main | As Small, plus share of voice per engine, language and prompt class, a citation-source gap, and accuracy grading against a facts sheet. "Wrong" claims go to human review before any client report | As Small | 40 prompts × 3 languages × 3 engines × 3 runs = 1,080 probes: $8.10 in search fees plus tokens. ≈ $10–18 [estimate] |
| 5 | DataForSEO Google AI Mode API **(guard: price row)** | Main | As Small, for every non-ka pair (ru, en, he and de are supported) | As Small | 200 keywords × 5 pairs weekly ≈ $5 |
| 6 | Bing Webmaster Tools API **(to build: Bing client)** | Main | As Small | As Small | $0 |
| 7 | Google Search Status Dashboard feed | Main | As Small. It matters more where a rollout moves thousands of tracked pairs at once | As Small | $0 |
| 8 | Ahrefs Rank Tracker via REST v3 **(to build: REST client)** | Cross-check | Positions collected independently for the same keywords and countries (`ge` included). Compares each keyword × country × device weekly with DataForSEO. Pairs that differ by more than 3 positions, or sit on opposite sides of the top-10 line, hold their alerts and are re-checked next week. A persistent gap on one locale points to a location or language mismatch in one tool's setup. Worth it whenever Ahrefs is in the stack, because the reads are free | REST v3 only: `management/projects` and `management/project-keywords` set it up at 0 units, and `rank-tracker/overview` reads it. Standard tracks 2,000 keywords, so keep to the money and mid tiers | $0 extra on the Ahrefs Standard plan priced under Backlinks. Dropped if that plan is dropped |
| 9 | Ahrefs Brand Radar custom prompts via REST v3 **(to build: REST client)** | Cross-check | The same frozen prompts, run by another collector. Ahrefs enters prompts in the web version of each chatbot, except Claude, which it tracks through the API. So under the consumer-app rule only its Claude data and its Google AI Overview and AI Mode data are stored; its ChatGPT, Perplexity, Gemini, Copilot and Grok data is not. Compares Claude mention and citation rates with `ai_probe`, and its AI Overview and AI Mode cited domains with DataForSEO's references, both with Wilson intervals. Worth it when AI visibility is a KPI reported to stakeholders | REST v3: prompts added free with `management/brand-radar-prompts` (`countries` includes `ge`). Reads of custom-prompt data cost no units. Each Claude check uses 8 checks. Checks run monthly | Custom prompts are included on Standard (300 checks). A Basic pack is $50 for 2,500 checks. One monthly cycle of the 120 prompts (40 × 3 languages) at 10 checks each (8 for Claude, 1 each for AI Overview and AI Mode) is about 1,200 checks, which fits the 300 plus a Basic pack. Weekly checks would be about 5,200 a month and need the $100 pack (7,000). Packs bill overage at month end ($0.020 a check on Basic), so the REST client counts each cycle's checks against the included total and stops before it. ≈ $0–50 at monthly checks |
| 10 | DataForSEO Bing Organic SERP API | Cross-check | Per-locale Bing ranks under fixed conditions, which Bing Webmaster Tools can't give. DataForSEO's Bing languages lack Georgian, so Georgia is GE-ru and GE-en only. Compares direction and order of magnitude with Bing Webmaster's all-market averages. Worth it when Bing has 10% or more of the site's search clicks, or AI visibility is a KPI | Same connector and guard, Standard queue | $0.0006 a SERP. 200 keywords × 5 pairs weekly at depth 20 ≈ $5 |
| 11 | GA4 AI-referral sessions | Cross-check | As Small, per market, against `ai_probe` and Brand Radar | As Small | $0 |

**Reserve**

| Tool | Use when … |
|---|---|
| Search Console Search generative AI report (export) | A person exports it monthly into `seo-work/`. It gives Google's own AI Overview and AI Mode impressions per page and country, the first-party check on vendor-sourced Google AI data. No API. Runs read the newest file and flag it stale after 35 days |
| Bing Webmaster Tools AI Performance report (export) | A person exports it monthly: Copilot and Bing AI citations, grounding queries, Citation Share, Intents and Topics. It is the only compliant Copilot signal. No API found. Same staleness rule |
| DataForSEO LLM Mentions | A covered market is a target. Its `chat_gpt` data is US-English only and its collection method isn't documented, so only its `google` platform data qualifies under the consumer-app rule. $0.10 a task plus $0.001 a row |
| DataForSEO LLM Responses | The owner wants one DataForSEO credential instead of three API keys, so it becomes `ai_probe`'s backend. Not a cross-check: it calls the same vendor APIs. Prompts are capped at 500 characters and Standard results can take 72 hours. Never with Gemini web search |
| DataForSEO LLM Scraper | The owner explicitly approves vendor-scraped app answers for a one-off parity check of a few prompts, labelled "vendor-scraped" and kept out of trend lines. It scrapes chatgpt.com and gemini.google.com. The B8 pipeline in seo-automation still samples with it and should move to `ai_probe` |
| Ahrefs Rank Tracker and Brand Radar (small sites) | Ahrefs Lite or higher is already paid and the REST client exists |
| SerpApi, Free plan (big sites) **(to build: collector)** | The site has no Ahrefs plan, so Rank Tracker isn't there as the second collector. Then use it as in the small list: compare positions with DataForSEO only for keywords about to alert, within 250 searches a month (50 an hour). In the default free stack it is Main |
| Search Console bulk export (small sites) | Search Console API pulls hit 50,000 rows a day per search type. In the default free stack it is Main |
| DataForSEO Bing SERP (small sites) | Bing has 10% or more of the site's search clicks |
| Semrush Position Tracking | The owner already runs a campaign that stakeholders read in Semrush. Read its overview (100 units a request) monthly. Positions cost 100 units a keyword, so never as a pipeline |
| Semrush AI Visibility Toolkit | The owner already pays for it ($99 a month per user) and wants a dashboard for people. Its data isn't in the API or MCP |
| SE Ranking Rank Tracker and AI Results Tracker | The site is big, has no Ahrefs plan, and wants a second position source: Core $129 or Growth $279 include API access. Its AI tracker data qualifies only once SE Ranking documents an API-based collection method |
| Otterly.AI (Standard $189: REST and MCP) | The site is big, has no Ahrefs plan, and Otterly documents API-based collection for an engine; only those engines' data is stored. The pages checked don't document its method, so none of its engine data qualifies today. Lite has no API |
| Peec AI | A client already uses it. Prices, which plans include the API and MCP, and its collection method are not published |
| Profound | An enterprise client contracts it. API on Enterprise only; the trial has none |
| Gemini API without grounding ("gemini-parametric") | GA4 shows gemini.google.com at 10% or more of AI-referral sessions for two months [heuristic] and a no-search signal is still wanted. Report it separately as what the model knows without search |
| Gemini API Grounding with Google Search | Google's Gemini API Additional Terms change to allow caching, analysing and collecting Links from Grounded Results |
| Grounding with Bing Search | Microsoft's terms change to allow storing output and using it to evaluate models |
| Ahrefs MCP (interactive) | A person is in the session and wants ad-hoc answers from Ahrefs Rank Tracker, Brand Radar or GSC data (Rank Tracker and GSC tools cost 0 units). Never scheduled |
| Manual checks in the AI apps, by the user | Before the first client report, and when an engine's API citation rate moves outside its previous 95% interval two months running [heuristic]. The user checks 5 prompts by hand and logs them as surface "app". Claude never drives the apps. Perplexity's ToS 5.2(i) also covers systematic manual monitoring, and Copilot is for personal use only |
| Local Falcon | Map-pack rank for local businesses: see [Measurement, local and indexing](#measurement-local-and-indexing) (DataForSEO Google Maps is Main there) |
| SISTRIX Visibility Index | A target market SISTRIX covers (for example DE or GB) and stakeholders report in its index. No Georgia or Israel. API not checked |
| Semrush Sensor | In a watched session, a drop matches no Search Status incident yet. A free page with no API; Semrush's ToS bars scripted extraction |

### Measurement, local and indexing

What did our own site get from Google and Bing (clicks, impressions, positions, indexing state, conversions)? Did the
engines hear about our changes? How visible and accurate are our local listings and map-pack ranks? Local tools apply
only to businesses with physical locations or service areas, and Merchant Center only to stores. Otherwise they are
skipped, not replaced.

**Small sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Search Console API: Search Analytics, URL Inspection, Sitemaps **(to build)** | Main | Google's own clicks, impressions and positions for 16 months, and its indexing verdict per URL. A small site fits the 2,000 inspections a day: every URL weekly, changed URLs daily. `sitemaps.submit` lets a level-4 run submit a sitemap itself. Owns the URL Inspection quota for every category | Service account as a property user: `webmasters.readonly`, plus `webmasters` only for `sitemaps.submit` at level 4. One day per request with `dataState=final`. Google publishes no Search Console MCP. Until the fetcher is built: exports or the community `mcp-gsc`. Never script the Search Console UI | $0 |
| 2 | Google Analytics 4 (official `analytics-mcp`) | Main | What organic visitors do and whether they convert, by landing page, and GBP traffic through `utm_campaign=gbp`. GA4 organic sessions against GSC clicks per landing page flag a removed tag or a consent change before a report blames rankings | Local stdio (Experimental), service-account impersonation, `analytics.readonly`, never `--allow-write`. A standard property allows 200,000 tokens a day; send `returnPropertyQuota` | $0 |
| 3 | Bing Webmaster Tools API **(to build: Bing client)** | Main | Bing's own query and page stats and crawl issues, for all markets at once (URL submission is Reserve: IndexNow submits). `gsc_analyze.py` already reads Bing's columns | API key or OAuth on the JSON endpoint (SOAP and POX were scheduled to retire on 2026-08-31). The key travels in the query string, so never log request URLs | $0 |
| 4 | IndexNow **(to build: submitter)** | Main | The run finishes "tell the engines" itself: changed and removed URLs reach Bing, Yandex (for ru audiences), Seznam, Naver and Yep, which share submissions. Google's side is a clean sitemap plus `sitemaps.submit` | Key file `/{key}.txt` added by a level-2 pull request. POST up to 10,000 URLs at level 3 and above, only changed URLs. 422 means a host mismatch; 429 means back off | $0 |
| 5 | Google Business Profile APIs (local businesses only) **(to build: client)** | Main | Daily Maps and Search impressions, calls, directions, website clicks and bookings, monthly search keywords, and own reviews. The only official way for a run to apply an approved profile change, which stays gated per run | Google must approve access first: a profile verified and active for 60+ days, a website, and the application form. 0 queries a minute until then, 300 after. OAuth `business.manage` as owner or manager, read methods only unless an edit was approved for that run. De-duplicate reviews (a pagination known issue since 2026-06-17) | $0 |
| 6 | Merchant API v1 (stores only) | Main | Product statuses, disapprovals, account issues and performance: the input to seo-ecommerce's feed, page and markup check. Content API for Shopping was sunset on 2026-08-18 | Service account, scope `content`. Read tools only, through the alpha Merchant API MCP (`https://merchantapi.googleapis.com/mcp`) or plain REST as the fallback. Exclude `create_data_source` and `fetch_data_source`. Edits are always gated | $0 |
| 7 | DataForSEO Google Maps and Local Finder, geo-grid (local businesses only) **(guard: price row)** | Main | The cheapest unattended map-pack rank: one Maps SERP per grid point (`location_coordinate` "lat,lng,zoom"), stored raw, so our share of local voice and the competitor list come from one call. Georgian city codes, and ka, ru and en. [vendor data]: we never query google.com/maps | Connector, Standard queue, fixed zoom and depth per keyword set. Avoid `calculate_rectangles` (2×) and operators (5×). The guard bills Maps per 10 results while DataForSEO bills per 100, so it over-reserves | $0.0006 a point. 1 location × 10 keywords × a 5×5 grid ≈ $0.15 monthly or ≈ $0.65 weekly |
| 8 | Google Search Status Dashboard feed | Main | Dates of Google updates and incidents, for drop diagnosis | As in Rank; shared and counted once | $0 |
| 9 | Microsoft Clarity (Data Export API, official MCP) | Cross-check | A second tag that counts sessions its own way, with bot sessions separated, plus quickbacks that show an intent mismatch. Compares organic sessions and engagement per landing page with GA4 and GSC clicks. A gap above about 20% [heuristic] points to consent, tagging or bot-filtering differences. Worth it when Clarity is installed, or when GA4 and GSC disagree | Token created by the project admin. 10 requests a project a day, the last 1–3 days, 3 dimensions and 1,000 rows, so one fixed daily job. Adding the tag is a site change (level 2 and above) | $0 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Search Console API **(to build)** | Main | Fresh days by country, URL Inspection of changed URLs plus a fixed sample per template, and `sitemaps.submit` at level 4. Comparing the API's daily totals with the export's site table shows how much the API truncates | As Small. One property at a time; retry once after 15 minutes, then fail loudly | $0 |
| 2 | Search Console bulk export to BigQuery | Main | Full query × URL tables for cannibalisation and language splits | As in Keywords. Set partition expiration (14 days minimum) or data accumulates forever. Shared and counted once | As in Keywords |
| 3 | Google Analytics 4 | Main | By landing page, section and market | As Small. Pull fixed weekly reports rather than many ad-hoc ones (360 properties get 10× the token quota) | $0 |
| 4 | Bing Webmaster Tools API **(to build: Bing client)** | Main | As Small, weekly | As Small | $0 |
| 5 | IndexNow **(to build: submitter)** | Main | Many URLs per deploy, with no account and no quota beyond 429 throttling | As Small, batches of up to 10,000 per deploy | $0 |
| 6 | Google Business Profile APIs (local businesses only) **(to build: client)** | Main | Per-location data across every location, and approved fixes in bulk, gated per run. Location groups map to the site's location pages | As Small. 300 queries a minute covers hundreds of locations daily | $0 |
| 7 | Merchant API v1 (stores only) | Main | As Small, for big catalogues | As Small. Cap calls per run: agents can drain the quota it shares with the API | $0 |
| 8 | DataForSEO Google Maps and Local Finder (local businesses only) **(guard: price row)** | Main | Every location × money keyword | As Small, with versioned keyword sets | 20 locations × 10 keywords × a 7×7 grid = 9,800 points ≈ $5.90 a scan: ≈ $6 monthly or ≈ $25 weekly |
| 9 | Google Search Status Dashboard feed | Main | As Small. Drops on big sites are often partial | As Small | $0 |
| 10 | Local Falcon (API v2, hosted MCP; local businesses only) | Cross-check | Another geo-grid scanner, with its own share-of-local-voice metric, stored trends, and Apple Maps scans that no other tool here measures. Compares our rank and top-3 presence point by point each month with the DataForSEO grid on money keywords. Agreement at 80% or more of points [heuristic] confirms a change before profile work starts. Disagreement means checking coordinates, zoom and language first. Worth it from more than 10 locations, or when one swing of 3+ positions would trigger work | `POST /v2/run-scan` with `api_key`, `place_id` and a grid of 3–21. Reading reports costs no credits. Google and Apple platforms only: its AI-engine scans fall under the consumer-app rule. Outside the guard, so rely on the plan's credit cap and buy no pay-as-you-go credits | Basic $49.99 (15,150 credits) or Pro $99.99 (31,250), at 1 credit a grid point |
| 11 | Microsoft Clarity | Cross-check | As Small, section by section. 1,000 rows won't cover every URL | As Small, with rotating section filters | $0 |

**Reserve**

| Tool | Use when … |
|---|---|
| Yext (Knowledge Graph API, hosted MCP) | More than 10 locations in markets that Yext confirms on a demo (its Georgian publisher coverage is [UNVERIFIED]), and the owner pre-approves listing pushes per run. It publishes one record to 200+ publishers. Quote-only; third parties report $199–999 per location a year [UNVERIFIED]. Pushing to Google through it is a Business Profile edit, which is always gated. Its MCP reportedly has write access on by default [UNVERIFIED]: turn that off or use a read-only key |
| Local Falcon (small sites) | A map-pack swing is disputed, or Apple Maps rank matters. Starter $24.99 a month |
| Search Console bulk export (small sites) | Search Console API pulls hit 50,000 rows a day per search type. In the default free stack it is Main |
| Looker Studio (Google's pages now title it "Data Studio"), and Pro | A person wants a live dashboard; the run writes the data it reads. Its API manages assets only and can't read report data |
| Apple Business (replaced Business Connect on 2026-04-14) | The owner exports Place Card insights, or an Apple-approved partner the owner delegated to reads the Insights API. Otherwise a dashboard |
| Bing Places for Business | Bing and Copilot listings need correcting, and the owner applies the corrections. No public API is documented |
| BrightLocal | The business is in the USA, UK, Canada or Australia and needs a citation audit or builds, or a third geo-grid opinion. No Georgia. Track from $41 a month for one location |
| Semrush Listing Management and Local | The locations are in a country Semrush supports (Georgia is not one) and the account already pays Semrush. Local Pro is $60 per location a month, with an API |
| Conductor (Data API, MCP) | The organisation already licenses Conductor Intelligence: read its tracked rankings (5,000 calls a day per key) instead of buying the same set |
| Bing URL Submission API (`SubmitUrlBatch`) | A URL must reach Bing before an IndexNow key file can be deployed. 500 URLs a batch; Bing sets each site's daily quota |
| Google Indexing API | JobPosting or BroadcastEvent pages only (200 a day) |
| Community MCPs (`AminForou/mcp-gsc`, `zizzfizzix/mcp-server-bwt`) | A run needs Search Console or Bing API tools before the plugin's own fetchers exist. Audit and pin a version first, and keep `GSC_ALLOW_DESTRUCTIVE=false` |
| Ahrefs GSC endpoints | A watched session with Ahrefs connected and no Google credential yet. 0 units except `gsc-anonymous-queries`. The same data as Search Console, so no cross-check value |
| Ahrefs Web Analytics | The site already uses it instead of GA4. Its API v3 `web-analytics` endpoints cost 0 units, but need a v3 key and the REST client (to build) |
| GA4 BigQuery export | GA4 reports hit thresholds or quotas, or event-level joins with the Search Console export are needed. Daily export up to 1M events on standard properties; streaming export $0.05 a GB |
| Semrush Sensor | As in Rank |
| Google Places API | Only to resolve a location's Place ID. Its terms forbid storing names, addresses or reviews |
| DataForSEO Business Data (Google My Business Info, Reviews) | Comparing map-pack competitors' categories, ratings and review velocity, which the Business Profile API can't give. About $0.0015 a profile [UNVERIFIED]. Store counts, not review text |
| Search Console generative AI report, Bing AI Performance report | See the Rank Reserve |

### Build order

Each "(to build)" item, in the order that unblocks the most categories:

1. **Search Console API fetcher**, read-only: Search Analytics, URL Inspection and Sitemaps. Keywords, Technical, Rank
   and Measurement depend on it.
2. **Bing Webmaster Tools API client:** query, page, link, crawl and keyword methods. Backlinks, Technical, Rank and
   Measurement, and Keywords in the default stack.
3. **Credit guard changes** (next section). SE Ranking, Labs, On-Page, AI Mode, the Maps grid and the depth-100 run
   depend on them.
4. **IndexNow submitter** that checks the key file before sending.
5. **`ai_probe`** and the **rank-snapshot store**.
6. **CrUX API and History API** in `psi.py`.
7. **Polite competitor inventory:** robots.txt, one request at a time per host, a stop on 403, 429 or a challenge,
   snapshots and diffs.
8. **Ahrefs REST v3 client** for the Big cross-checks and `domain-rating-free`, reading the guard's budget and ledger.
9. **Screaming Frog CSV adapter** for `triage.py` and the research store (then `crawl.py` per section can become a
   cross-check), and a **CDN log converter** for `log_analyze.py`.
10. **SerpApi collector** for the Free plan: it counts its own calls, stops at the plan's 250 searches, and writes
    snapshots to the rank-snapshot store. Rank in the default stack, the small Rank cross-check, and the big Rank
    Reserve when there is no Ahrefs plan.
11. **Common Crawl graph reader:** streams each quarterly domain-level release and keeps only the edges into our and
    the competitors' domains, plus their ranks. Backlinks in the default stack.
12. **Google Business Profile client:** read methods with OAuth `business.manage`, and edits only when approved for
    that run. Measurement, local businesses only.

The default free stack needs items 1, 2, 4, 6, 7, 10, 11 and 12, and the `domain-rating-free` part of item 8.

### Credit guard changes the stack needs

Read in `scripts/credit_guard.py` on 2026-10-24, not run:

- **Unpriced vendors share one small allowance.** SE Ranking, AlsoAsked, Similarweb, Otterly and Keywords Everywhere
  calls, and Lumar crawls, share `other_monthly_usd`, and each call is counted at `ask_above_pct` of it. At the
  defaults (25% a run, 5% a call) that is 5 calls a run and 20 a month for the whole bucket, whatever the budget, and
  0-credit calls count too. Raising `other_monthly_usd` doesn't change the count, and lowering `ask_above_pct` is
  global. Needed: an SE Ranking price table from its published credit costs, and a bucket per vendor.
- **One row limit for everything.** `max_rows` (default 50) also clamps DataForSEO `depth`, `limit` and
  `max_crawl_pages`, and adds them when missing. So On-Page stops at 50 pages, a 1,000-row Labs pull becomes 20 tasks,
  and depth 100 is capped at 50. Raising `max_rows` loosens Semrush and Ahrefs too. Needed: limits per vendor and
  endpoint (Labs and Backlinks 1,000, SERP depth 100, On-Page up to the site's URL count).
- **Missing price rows.** AI Mode is priced as a generic SERP, half its $0.0012. Maps is billed per 10 results, while
  DataForSEO bills per 100. Clickstream, LLM Responses, LLM Scraper and Business Data have no price, so each call is
  counted at 5% of the DataForSEO budget.
- **Tools the hook never sees.** Moz, Majestic, Local Falcon, SerpApi, OpenAI, Anthropic, Perplexity, and Ahrefs REST
  calls. Adding a vendor is a code change. Until then they follow the no-overage rule.

Costs in the lists are at the intended call shapes. **Budget settings** for the paid stacks
(`/plugin configure seo-suite@seo-suite`). The default free stack needs none, because it makes no paid calls:

| Option | Small | Big |
|---|---|---|
| `dataforseo_monthly_usd` | 25 | 270 |
| `other_monthly_usd` | 12, after the SE Ranking change, for SE Ranking (≈ $0.60) and `ai_probe` (≈ $6) | 35, after the SE Ranking change, for SE Ranking (≈ $3) and `ai_probe` (≈ $18) |
| `ahrefs_monthly_units` | 0 | Up to 320,000 (40% of Standard), read by the REST client |

- **`ai_probe`'s cap.** The hook never sees OpenAI, Anthropic or Perplexity calls, so `ai_probe` (to build) reads
  `other_monthly_usd`, `per_run_cap_pct` and the guard's ledger before each batch of probes, records its own spend in
  the ledger, and stops at the monthly budget or the per-run cap. It counts against `other_monthly_usd` with
  SE Ranking. The budgets leave room above the two's expected spend (about $6.60 small and $21 big), so a re-run
  still fits. Run the probes weekly, so each run stays under the per-run cap (25%: $3 small, $8.75 big). On big
  sites, run the quarterly SE Ranking pulls (about $8) in a run without probes.
- **Why 270 for big.** The big list's DataForSEO spend reaches about $253 in an average month: Main $105–145, plus
  the cross-checks On-Page up to $102, Bing SERP about $5 and Clickstream about $0.75. Real months are uneven,
  because the Labs pull ($22.20) and the Autocomplete expansion (about $35) are quarterly. Run those two in different
  months of the quarter. The heaviest month is then about $265: recurring Main with the weekly Maps grid (about $123),
  the Autocomplete expansion, and the cross-checks with browser-rendered On-Page. If a month still runs short, drop
  cross-checks in this order: browser-rendered On-Page (fall back to JavaScript mode, then raw), DataForSEO Bing SERP,
  Clickstream. Main calls keep running. With JavaScript-mode On-Page ($30) instead of browser rendering, 200 is
  enough.
- **The per-call threshold.** The guard denies any priced call estimated above `ask_above_pct` (default 5%) of the
  monthly bucket and defers it to the end-of-run questions, which need a person. At these budgets that is $1.25 a
  call for small sites and $13.50 for big ones, under a per-run cap (25%) of $6.25 and $67.50. The guard prices an
  On-Page `task_post` as one call: the per-page price ($0.00015 raw, $0.0015 with JavaScript, $0.0051 with browser
  rendering) × `max_crawl_pages`, summed over the tasks in the POST. So a run splits On-Page into separate
  `task_post` calls of one task each, every one under the threshold: about 800 JavaScript or 245 browser-rendered
  pages a call for small sites, and about 9,000 JavaScript or 2,600 browser-rendered pages for big ones. Raw crawls
  fit easily (about 8,300 and 90,000 pages). Each task covers one section: `respect_sitemap` and `crawl_sitemap_only`
  set to true, and `custom_sitemap` set to that section's child sitemap. Spread the calls over runs that make no other
  large DataForSEO calls, to stay under the per-run cap: a small browser-rendered crawl ($10.20) takes two runs, and
  the big 20,000-page browser-rendered sample ($102) takes two runs of about $51. The other way is raising
  `ask_above_pct`, which applies to every vendor. All of this needs the page-cap change first, because as shipped
  the guard clamps `max_crawl_pages` to 50.

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

### Sources for the Main stack

Checked 2026-10-24, read-only, no sign-ins and no paid calls. Code facts were read in this repo's `scripts/`.

- **DataForSEO:** Labs locations, no Georgia
  (https://cdn.dataforseo.com/v3/locations/locations_and_languages_dataforseo_labs_2026_09_01.csv); Google Ads
  locations, Georgia and cities (https://cdn.dataforseo.com/v3/locations/locations_kwrd_2026_09_01.csv); Google Ads
  prices (https://dataforseo.com/pricing/keywords-data/google-ads); Autocomplete $0.0006 Standard
  (https://dataforseo.com/pricing/serp/google-autocomplete-serp-api); Clickstream
  (https://dataforseo.com/pricing/keywords-data/clickstream-api-pricing); no Russia or Belarus locations
  (https://docs.dataforseo.com/v3/dataforseo_labs/locations_and_languages/); Backlinks prices
  (https://dataforseo.com/pricing/backlinks/backlinks); `domain_intersection` limits
  (https://docs.dataforseo.com/v3/backlinks-domain_intersection-live/); summary broken backlinks and pages
  (https://docs.dataforseo.com/v3/backlinks-summary-live/); On-Page options
  (https://docs.dataforseo.com/v3/on_page/task_post/); AI Mode languages
  (https://docs.dataforseo.com/v3/serp/google/ai_mode/languages/); LLM Mentions coverage
  (https://docs.dataforseo.com/v3/ai_optimization/llm_mentions/locations_and_languages/); LLM Responses
  (https://docs.dataforseo.com/v3/ai_optimization/chat_gpt/llm_responses/live/,
  https://dataforseo.com/pricing/ai-optimization/llm-responses); Maps and Local Finder
  (https://dataforseo.com/pricing/serp/google-maps-serp-api); Bing organic $0.0006 Standard
  (https://dataforseo.com/pricing/serp/bing-organic-serp-api); Google location codes, including the US-state trap
  (https://cdn.dataforseo.com/v3/locations/locations_serp_google_2026_09_01.csv).
- **Google:** Ads languages, no Georgian (https://developers.google.com/google-ads/api/data/codes-formats#languages);
  Trends API alpha (https://developers.google.com/search/apis/trends); Search Console API resources, no links
  (https://developers.google.com/webmaster-tools/v1/api_reference_index); Search Analytics quotas and rows a day
  (https://developers.google.com/webmaster-tools/limits,
  https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data); Links report export
  (https://support.google.com/webmasters/answer/9049606); URL Inspection result
  (https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult); `sitemaps.submit` scope
  (https://developers.google.com/webmaster-tools/v1/sitemaps/submit); bulk export
  (https://support.google.com/webmasters/answer/12917675); Crawl Stats
  (https://support.google.com/webmasters/answer/9679690); PageSpeed Insights v5
  (https://developers.google.com/speed/docs/insights/v5/get-started); CrUX API (https://developer.chrome.com/docs/crux/api);
  CrUX BigQuery (https://developer.chrome.com/docs/crux/bigquery); headless Chrome
  (https://developer.chrome.com/docs/automation-and-testing/headless-cli); Chrome DevTools MCP options
  (https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/configuration.md); BigQuery MCP
  (https://docs.cloud.google.com/bigquery/docs/use-bigquery-mcp); BigQuery prices (https://cloud.google.com/bigquery/pricing);
  no Search Console MCP (https://github.com/google/mcp); `analytics-mcp`
  (https://github.com/googleanalytics/google-analytics-mcp); GA4 Data API token quotas
  (https://developers.google.com/analytics/devguides/reporting/data/v1/quotas); GA4 BigQuery export limits
  (https://support.google.com/analytics/answer/9358801); Business Profile access, metrics and known issues
  (https://developers.google.com/my-business/content/prereqs,
  https://developers.google.com/my-business/reference/performance/rest/v1/DailyMetric,
  https://developers.google.com/my-business/content/known-issues); Merchant API and its MCP
  (https://developers.google.com/merchant/api/overview,
  https://developers.google.com/merchant/api/guides/agentic-tools/merchant-data-mcp); Looker Studio API
  (https://developers.google.com/looker-studio/integrate/api); Status Dashboard feed
  (https://status.search.google.com/incidents.json); Gemini API Additional Terms (https://ai.google.dev/gemini-api/terms);
  Google ToS and robots.txt (https://policies.google.com/terms, https://www.google.com/robots.txt); autocomplete endpoint
  has no robots.txt (https://suggestqueries.google.com/robots.txt returns 404).
- **Microsoft:** Bing Webmaster API methods
  (https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi?view=bing-webmaster-dotnet,
  https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.geturllinks?view=bing-webmaster-dotnet);
  API access (https://learn.microsoft.com/en-us/bingwebmaster/getting-access); SOAP and POX retirement
  (https://learn.microsoft.com/en-us/bingwebmaster/api-protocols); AI Performance additions
  (https://blogs.bing.com/search/2026/6/New-AI-Visibility-Insights-in-Bing-Webmaster-Tools-Intents-Topics-Citation-Share-Compare/);
  Grounding with Bing terms (https://www.microsoft.com/en-us/bing/apis/grounding-legal-enterprise); Bing Places, a
  community answer (https://learn.microsoft.com/en-us/answers/questions/5672165/bing-places-for-business-overview);
  community Bing MCP (https://github.com/zizzfizzix/mcp-server-bwt).
- **Semrush:** plans, SEO without MCP and Starter with it (https://www.semrush.com/prices/); MCP units
  (https://www.semrush.com/kb/1618-mcp); Georgia database (https://www.semrush.com/kb/287-what-countries-does-semrush-cover);
  MCP methods (https://developer.semrush.com/api/basics/semrush-mcp/); Local plans and countries
  (https://www.semrush.com/kb/1611-local-toolkit-pricing-and-plans,
  https://www.semrush.com/kb/874-listing-management-citation-websites).
- **Ahrefs:** API v3 on Lite and higher, rows per request (https://help.ahrefs.com/en/articles/6559232-about-api-v3);
  OpenAPI spec: Rank Tracker, Brand Radar, `web-analytics` at 0 units, `link-intersect-refdomains`, `broken-backlinks`
  (https://docs.ahrefs.com/openapi.json); `domain-rating-free` and its licence
  (https://docs.ahrefs.com/api/reference/public/get-domain-rating-free, https://ahrefs.com/legal/domain-rating-license);
  ToS §4.4 (https://ahrefs.com/legal/terms); Brand Radar collection and prices
  (https://help.ahrefs.com/en/articles/11064852-what-is-brand-radar-and-how-to-use-it); Georgia as ka-GE only
  (https://help.ahrefs.com/en/articles/2127127-what-languages-does-ahrefs-keywords-explorer-support).
- **SE Ranking:** API prices (https://seranking.com/api-pricing.html, https://seranking.com/api/); credit costs
  (https://seranking.com/api/data/getting-started/); regional databases (https://seranking.com/api/data/reference);
  backlinks credits (https://seranking.com/api/data/backlinks/).
- **Moz:** API prices and MCP beta (https://moz.com/products/api/pricing, https://moz.com/api/docs/guides/mcp-servers);
  auth (https://moz.com/api/docs/guides/authentication); gained domains and Link Intersect
  (https://moz.com/api/docs/methods/DataSiteLinkingDomainFilterRecentlyGainedAction,
  https://moz.com/api/docs/methods/DataSiteLinkIntersectFetchAction).
- **Crawlers:** Screaming Frog pricing, MCP, CLI and FAQ (https://www.screamingfrog.co.uk/seo-spider/pricing/,
  https://www.screamingfrog.co.uk/guides/mcp-server/, https://www.screamingfrog.co.uk/seo-spider/user-guide/general/,
  https://www.screamingfrog.co.uk/seo-spider/faq/); Log File Analyser (https://www.screamingfrog.co.uk/log-file-analyser/);
  Sitebulb MCP (https://support.sitebulb.com/en/articles/15957255-what-the-sitebulb-mcp-can-and-can-t-do); Lumar
  (https://www.lumar.io/faq, https://api-docs.lumar.io/docs/graphql/tutorials/run-crawl-and-get-results); Botify
  (https://developers.botify.com/); schema.org downloads (https://schema.org/docs/developers.html); Cloudflare AI Crawl
  Control (https://developers.cloudflare.com/ai-crawl-control/).
- **AI-answer APIs:** OpenAI web search and prices (https://developers.openai.com/api/docs/guides/tools-web-search,
  https://developers.openai.com/api/docs/pricing); Anthropic web search fee and Haiku 5.5 prices
  (https://platform.claude.com/docs/en/about-claude/pricing); Perplexity API Terms §5.1
  (https://www.perplexity.ai/hub/legal/perplexity-api-terms-of-service).
- **Other vendors:** Majestic (https://majestic.com/plans-pricing,
  https://developer-support.majestic.com/api/commands/get-index-item-info.shtml); AlsoAsked
  (https://alsoasked.com/pricing,
  https://help.alsoasked.com/en/articles/16004475-how-do-i-connect-alsoasked-to-my-ai-assistant-with-mcp); Keywords
  Everywhere (https://api.keywordseverywhere.com/docs/README.md, https://keywordseverywhere.com/pricing.html,
  https://keywordseverywhere.com/tools/keyword-volume-checker/); AnswerThePublic (https://answerthepublic.com/pricing);
  SpyFu (https://developer.spyfu.com/docs/api-pricing,
  https://help.spyfu.com/en/articles/2968557-which-countries-does-spyfu-collect-data-in); Similarweb MCP
  (https://developers.similarweb.com/docs/similarweb-mcp); SerpApi (https://serpapi.com/pricing); Otterly
  (https://otterly.ai/pricing, https://docs.otterly.ai/mcp-server); Peec AI (https://docs.peec.ai/mcp/introduction);
  Profound (https://www.tryprofound.com/pricing); Local Falcon (https://www.localfalcon.com/llms.txt,
  https://docs.localfalcon.com/openapi.yaml, https://www.localfalcon.com/features/mcp); Apple Business
  (https://www.apple.com/mx/newsroom/2026/03/introducing-apple-business/,
  https://support.apple.com/guide/business/abcb4226f877/web); BrightLocal (https://www.brightlocal.com/pricing/,
  https://www.brightlocal.com/local-seo-apis/); Yext (https://www.yext.com/knowledge-center/yext-faq,
  https://www.yext.com/blog/unlock-the-agentic-ai-era-with-yext-mcp-server); Conductor
  (https://www.conductor.com/docs/api/rate-limits.md); IndexNow (https://www.indexnow.org/documentation); Common Crawl
  graph (https://data.commoncrawl.org/projects/hyperlinkgraph/cc-main-2026-aug-sep-oct/index.html).
- **Default free stack and this round's fixes** (also checked 2026-10-24, read-only): the bulk export needs a Cloud
  project with billing and accepts partition expiration of 14 days or longer
  (https://support.google.com/webmasters/answer/12917675); BigQuery custom quotas, `QueryUsagePerDay` in TiB,
  approximate and not a strict cap on bytes processed (https://docs.cloud.google.com/bigquery/docs/custom-quotas); CrUX
  on BigQuery needs a credit card on the project, and its materialized `country_summary` table carries the
  `metrics_summary` columns, `rank` ("Coarse popularity ranking") among them
  (https://developer.chrome.com/docs/crux/bigquery); CrUX popularity buckets on a log10 scale
  (https://developer.chrome.com/docs/crux/methodology/metrics); the CrUX API quota is offered without charge
  (https://developer.chrome.com/docs/crux/api); Bing `GetKeywordStats` and `GetRelatedKeywords` (the Bing Webmaster API
  methods page above); On-Page `custom_sitemap`, `crawl_sitemap_only`, browser rendering needing JavaScript and
  `load_resources`, and 100 tasks a POST (https://docs.dataforseo.com/v3/on_page/task_post/); the credit guard's
  per-call threshold and On-Page pricing (`bucket_limits` and `dfs_task_cost` in `scripts/credit_guard.py`); Common
  Crawl's domain vertices, edges and ranks files (the graph page above) and its terms of use
  (https://commoncrawl.org/terms-of-use); Ahrefs' OpenAPI paths: `batch-analysis/batch-analysis`, and no Content
  Explorer or Keyword Clusters path (https://docs.ahrefs.com/openapi.json); SerpApi's Free plan with no Legal Shield,
  its AI Overview `page_token` and its AI Mode engine (https://serpapi.com/pricing,
  https://serpapi.com/google-ai-overview-api, https://serpapi.com/google-ai-mode-api); Google's lawsuit against SerpApi
  (https://blog.google/technology/safety-security/serpapi-lawsuit/); Claude Code's WebSearch tool, which describes
  itself as US-only (its tool description in a Claude Code session).

## Free tools

| Tool | Gives you | Limits / notes | Stack |
|---|---|---|---|
| **Google Search Console** | Your clicks, impressions, CTR, position by query/page/country/device · indexing (Pages report, URL Inspection) · sitemaps · Core Web Vitals · links (sample) · manual actions · "Search generative AI" setting and report (impressions only) | 16 months of data · UI export 1,000 rows · API 25k rows/request, 2,000 URL inspections/day/site | Main (default, small, big): the API, through a read-only fetcher (to build); in the default Technical list, URL Inspection is a Cross-check against `crawl.py`. Bulk export to BigQuery: Main (default, big), Reserve (small). Search generative AI report, Links and Crawl Stats exports: Reserve, use when a person exports them |
| **Bing Webmaster Tools** | Same for Bing, which powers Copilot and is reported to supply ChatGPT search (directional vendor data) · backlinks (own site) · IndexNow · AI Performance report (citations; public preview) [3rd-party] | API key in BWT | Main (default, small, big): the API, through a client (to build). Crawl methods: Cross-check (default, small, big). Positions: Cross-check (default), Main (small, big). Keyword API: Cross-check (default), Reserve (small, big). AI Performance export: Reserve, use when a person exports it |
| **Google Analytics 4** | Conversions and engagement from organic traffic · landing pages | Organic queries come from GSC, not GA4 | Main (default, small, big). AI-referral sessions: Main (default), Cross-check (small, big) |
| **PageSpeed Insights / CrUX** | Real-user Core Web Vitals (p75, 28 days) and Lighthouse lab audits | Free API key raises the quota (`psi.py`) · CrUX API 150 QPM · History API up to 40 weeks | Main (small, big): `psi.py` for lab data, CrUX API and History API for field data (to build). Default: CrUX API and History API Main, `psi.py` a Cross-check (lab against field). CrUX on BigQuery: Reserve, use when field data must be split by country. CrUX popularity rank: Main (default), Cross-check (big), Reserve (small) |
| **Rich Results Test · Schema Markup Validator** | Google rich-result eligibility · full schema.org validation | Manual (no public API found) | Reserve: use when a new template needs Google's verdict before indexing, or markup goes beyond Google's rich-result types |
| **Google Keyword Planner** | Google Ads volumes | Ranges (e.g. 1K–10K) unless the account has sustained ad spend; threshold undisclosed | Reserve: use when the client's Ads account spends and wants first-party numbers without a reseller |
| **Google Trends** | Relative interest over time and by region | API is alpha and application-only | Reserve: use when alpha API access is granted |
| **Ahrefs Free** (formerly Ahrefs Webmaster Tools) | For **your verified sites**: top 1,000 backlinks and keywords, site audit (5k crawl credits/project/month), web analytics | Verify the site first. The best free backlink view of your own domain | Reserve: use when a person exports own-site backlinks or keywords from the UI (no API). The separate `domain-rating-free` API endpoint: Main (default), Cross-check (small, big) |
| **Screaming Frog (free mode)** | Desktop crawler, 500 URLs | No JS rendering, custom extraction, API joins or saving crawls without a licence | Reserve: use when a person wants a GUI cross-check of `crawl.py` on 500 URLs or fewer |
| **Looker Studio** | Free dashboards on GSC + GA4 | — | Reserve: use when a person wants a live dashboard |
| **Wayback Machine CDX API** | History of competitor and own pages ("what changed before the drop") | `web.archive.org/cdx/search/cdx?url=…&output=json` | Cross-check (default, small, big): competitor page history. Reserve: use when a site move has no list of old URLs |
| **AlsoAsked free / Google PAA via search** | Question research | Paid AlsoAsked from $15/mo ($12/mo billed annually); API and MCP on Pro only | People Also Ask through the DataForSEO SERP API: Main (small, big); through WebSearch samples: Main (default), Cross-check (small, big). AlsoAsked: Reserve, use when a question hub of 100+ pages is planned |
| **This plugin's scripts** | Crawl, page audits, robots/AI-bot matrix, sitemaps, CWV, autocomplete ideas, GSC/log analysis, redirect QA, content scoring, competitor gaps, render diff, SERP clustering, triage, AI-visibility stats | See `scripts.md` | Main (default, small, big); each ranked script's rank is in the [Main stack](#main-stack). `psi.py`: Cross-check in the default stack. `keyword_ideas.py`: Cross-check (Bing suggestions in every list, Google suggestions in the default stack), Reserve (Google suggestions in the paid lists, YouTube in every list). `triage.py`, `serp_cluster.py`, `gsc_analyze.py` and `ai_visibility.py` run inside the ranked pipelines (crawl triage, SERP clustering, Search Console analysis, AI-answer statistics) and are not ranked separately. Not ranked: `content_score.py`, `translation_check.py` and `ai_text_check.py`, which are Main in the content skills that call them |

## Semrush

**Justified when** you need competitors' keywords and estimated traffic, country-level keyword volume and
difficulty at scale, PPC/ad intelligence, or market and traffic estimates. These come from Semrush's ranking database.
The free path cannot replicate them.

**Stack:** Reserve (small, big). Use when the owner already pays Starter or Pro+ and a scheduled run has kept its
sign-in working; then it is a third Georgian keyword database and a backlinks opinion. See the
[Main stack](#keywords-and-competitors). Free plan (10 reports a day): Reserve in every list, use when a person wants a
quick look in the interface; it has no API or MCP access, so no run reads it.

**Plans (monthly / annual per month):**
- Free: 10 reports/day.
- SEO: $139 / $117.33. 5 sites, 500 tracked keywords. No MCP or API access is listed, so a run can't use it.
- Starter: $199 / $165.17. 50 AI prompts. MCP access: the cheapest plan that lists it.
- Pro+: $299 / $248.17. 15 sites, 1,500 keywords, history, cannibalisation.
- Advanced and Enterprise: custom.
- Extra seats from $45/mo.
- Rows per report are not stated on the vendor page [UNVERIFIED: Pro 10k, Guru 30k, Business 50k].

**API:**
- Needs the Business-equivalent tier (Advanced or Enterprise) **plus unit packages** (2M–20M units, prices not
  public; unused units expire at renewal).
- Rate limit 10 requests/s. v3 keyword and backlink endpoints are deprecated; use v4.
- Unit costs per returned line (historical = 5×):

| Call | Units |
|---|---|
| `domain_organic` | 10 per line |
| `phrase_this` / `phrase_these` (batch ≤100) / `phrase_organic` | 10 per line |
| `phrase_related` / `phrase_questions` | 40 per line |
| `phrase_kdi` (difficulty) | 50 per line |
| competitors | 40 per line |
| domain vs domain | 80 per line |
| `backlinks_overview` | 40 per request |
| backlinks / referring domains | 40 per line |

- Empty results cost 0 units. Test calls do cost units. The `countapiunits` balance check is free.

**MCP:**
- Endpoint `https://mcp.semrush.com/v2/mcp` (OAuth or `Authorization: Apikey KEY`), read-only.
- Starter, Pro+ and legacy Pro/Guru include **50,000 MCP units** per renewal, shared with API pricing.
- Official connectors exist for Claude, ChatGPT and Perplexity.
- Claude Code: `claude mcp add --transport http semrush https://mcp.semrush.com/v2/mcp`.

**Add-ons:**
- **AI Visibility Toolkit:** $99/mo per user. 1 domain, 25 prompts, ChatGPT + Google AI Mode. Reserve: its data isn't in
  the API or MCP.
- **Traffic & Market:** $289/mo per user annually. The Trends API is a separate quarterly subscription. Reserve: use
  when an enterprise client needs Semrush's panel data instead of Similarweb.

**Cost tactics** (see also the playbook):
1. Always set `display_limit`, and page with `display_offset` only when needed. Billing is per line.
2. Never pull historical data (`display_date`) by default (5× cost). Snapshot monthly yourself.
3. Cheapest call first: overview and organic lines (10) before related/questions (40). Run `phrase_kdi` (50)
   only on a shortlist.
4. Batch with `phrase_these` (≤100 keywords). It saves requests and rate limit, not units.
5. One `database` (country) per call; avoid all-database pulls.
6. Use `backlinks_overview` (flat 40) before any per-line backlink list.
7. 50k MCP units ≈ 5,000 keyword lines: ask narrow questions with fixed limits, database and filters.
8. Read existing Projects (Position Tracking, Site Audit) through the Projects API or MCP instead of
   re-running ad-hoc reports.
9. Cache volumes and difficulty ~30 days; Semrush refreshes volumes monthly.

## Ahrefs

**Justified when** you need the largest fresh **backlink index** (competitor link profiles, link intersect,
lost and new links), organic traffic per URL, Content Explorer, or AI mentions across many engines (Brand Radar).
For your own site, use **Ahrefs Free** first.

**Stack:** REST API v3 on Standard: Cross-check (big, to build) for backlinks, Rank Tracker, Brand Radar and keyword
difficulty, and the Big stack's only SEO subscription. `domain-rating-free`: Main in the default stack, Cross-check
(small, big), to build. Lite for small sites, Site Audit, the GSC endpoints and the MCP: Reserve (the MCP only in
sessions someone is watching). Starter ($29, no API units): Reserve, use when a person wants Ahrefs' interface for
occasional checks; no run reads it. Content Explorer, Keyword Clusters and Batch Analysis are features of Standard and
higher, so they carry Standard's labels: Batch Analysis is the API's `batch-analysis` endpoint, used inside the REST v3
Cross-check (cost tactic 2). Content Explorer and Keyword Clusters have no API v3 path, so they are Reserve, for a
person in the interface when Standard is already paid.

**Plans (monthly):**

| Plan | Price | Tracked keywords | History | API units/mo |
|---|---|---|---|---|
| Starter | $29 | 750 | 1 month | none |
| Lite | $129 | 750 | 6 months | 200k (100 rows/request) |
| Standard | $249 | 2,000 | 2 years | 800k (250 rows/request) |
| Advanced | $449 | 5,000 | 5 years | 2M (500 rows/request) |
| Enterprise | $1,499 (annual only) | 10,000 | unlimited | 4M+ |

- Annual billing saves up to 17%. Seats cost $40, $60 or $80/mo, capped per plan.
- Content Explorer, Keyword Clusters and Batch Analysis start at Standard.

**API v3 metering:**
- Cost per request = max(50, rows × sum of field costs).
- Most fields cost 1; `traffic` and `org_traffic` cost 10; `refdomains` costs 5. Fields are charged even when used
  only in `where` or `order_by`.
- Cached responses cost 0.
- Free endpoints: Rank Tracker, Management, Public (`domain-rating-free`) and the GSC endpoints. Web Analytics
  endpoints are free too, and so are Brand Radar reads that return only custom-prompt data.
- API v3 works directly on Lite and higher (100 rows a request on Lite, 250 on Standard, 500 on Advanced).
- Free test targets: ahrefs.com, yep.com, firehose.com, capped at 100 rows. The response headers show the cost
  (`x-api-units-cost-total`, `x-api-cache`).

**MCP:**
- Endpoint `https://api.ahrefs.com/mcp/mcp` (OAuth or MCP key; Lite and above). Units are shared with the API,
  50 minimum per call.
- OAuth keys default to a 200k units/month cap.
- **Terms forbid scripting the MCP endpoint**; use API v3 for programmatic work.
- Claude Code: `claude mcp add --transport http ahrefs https://api.ahrefs.com/mcp/mcp`.

**Brand Radar (AI visibility):**
- From $199/mo. Prompt packs: $50 for 2.5k checks, $100 for 7k, $250 for 25k.
- Paid plans include 150, 300 or 600 checks.
- Engines: AI Overviews, AI Mode, ChatGPT, Gemini, Perplexity, Copilot, Grok, Claude.
- Collection: Ahrefs enters prompts in the web version of each chatbot with its default model. Claude is tracked
  through the API, and each Claude check uses 8 checks. Under the Main stack's consumer-app rule, only the Claude,
  AI Overview and AI Mode data is stored.

**Cost tactics:**
1. Select only the fields you need. Avoid `traffic`/`org_traffic` (10×) and `refdomains` (5×) in select, where
   and order_by unless they are the point.
2. Beat the 50-unit minimum by consolidating: Batch Analysis takes up to 100 targets per call.
3. Always `limit`. Estimate first on a free test target and read `x-api-units-cost-total`.
4. Own-site data is free: Ahrefs GSC endpoints (0 units), Ahrefs Free, verified projects (no row caps).
5. Cap OAuth/MCP keys at a monthly unit limit you chose.
6. Plan history is short on Lite (6 months): snapshot what you'll need later rather than re-pulling.
7. Spend the Brand Radar checks your plan includes before buying a pack. Packs bill overage at the end of the month
   ($0.020 a check on Basic, $0.015 on Growth, $0.010 on Scale), so count checks and stop before the included total.

## Screaming Frog

**Justified when** the site is larger than ~2,000 URLs or relies on JavaScript. The plugin's crawler is raw-HTML only
and best up to a few thousand pages. Screaming Frog adds Chromium rendering at scale, custom extraction,
crawl comparison, scheduling, and GSC/GA4/PSI joined per URL.

**Stack:** licensed CLI: Main (big). Small sites: Reserve, use when every template depends on JavaScript and crawls
recur weekly. Free mode, MCP and Log File Analyser: Reserve. The default free stack has no licence, so `crawl.py` per
section does the crawling there and Screaming Frog is Reserve.

- **Licence:** £199/year per user (volume discounts down to £169) [USD ≈ $279 UNVERIFIED]. The free mode covers 500 URLs.
- **CLI:** headless with a `licence.txt` key file. Scheduling and saving crawls need a licence. On a machine with no
  UI, also accept the EULA in `spider.config`. A licence covers one person.
- **MCP:** v24.0 (May 2026) added an SEO Spider MCP server for Claude (crawl, analyse, export). List mode is not
  supported yet. The MCP is a paid licence feature only, and it needs the app running or Claude Desktop.

**Cost tactics:**
- One licence per person who actually crawls.
- Use the free mode to cross-check `crawl.py` on small sites.
- Link-metric integrations (Ahrefs, Majestic, Moz) spend *those* tools' API units. Enable them only for key URLs.
- Schedule crawls and compare runs automatically instead of recrawling by hand.

**Alternatives:**
- **Sitebulb:** Desktop Lite/Pro; Cloud from £95/mo; JS rendering included; MCP on every plan. Reserve: its MCP is
  read-only and can't start or schedule a crawl.
- **Lumar:** quote-only; official MCP at `mcp.lumar.io/mcp`. Reserve: use when crawls must run in the cloud at very
  large scale. Its GraphQL API can start crawls.
- **Botify and Conductor:** enterprise. Reserve: use when the organisation already licenses them.

## DataForSEO

**Justified when** you need raw data at the lowest unit cost, paying per use instead of subscribing:
- Bulk Google Ads volumes.
- SERP snapshots at scale, including AI Overview and AI Mode, for rank tracking or SERP-overlap clustering.
- Backlink data without a subscription.
- LLM mention/response data for AI visibility.

**Stack:** Main (small, big): the main paid data source in every category of the Main stack. Labels per API are in
the table. Reserve (default): it is pay per call, so it comes in when its budget is set or the user asks.

**Billing:** pay-as-you-go, $50 minimum top-up, and balances never expire. The $100/mo commitment for Backlinks and
LLM Mentions was removed on 2026-07-01.

**Prices:**

| API | Price | Stack |
|---|---|---|
| SERP (Google organic, per 10 results) | Standard queue $0.0006 · Priority $0.0012 · Live $0.002 | Main (small, big): keywords, competitors, rank |
| SERP extras | AI Overview load 2× · `site:`-style operators 5× · each PAA click $0.00015 | AI Overview: Main on the money tier. PAA: Main. Operators (5×): not used |
| Keywords Data (Google Ads) | $0.06 per task of up to 1,000 keywords, Standard mode (≈ $60 per 1M keywords); Live $0.09 | Main (small, big) |
| Labs | $0.012 per task + $0.00012 per item | Main (big, markets Labs covers) · Cross-check (small, covered markets). No Georgia. Guard: rows |
| Backlinks | $0.024 per request + $0.000036 per row | Main (small, big) |
| On-Page | from $0.00015 per page | Cross-check (small, big). Guard: page cap |
| LLM Mentions | $0.10 per task + $0.001 per row | Reserve: use when a covered market is a target (`google` platform data only) |
| Google Autocomplete (per task) | Standard $0.0006 · Priority $0.0012 · Live $0.002 | Main (small, big) |
| Google AI Mode (per SERP) | Standard $0.0012 | Main (small, big). No Georgian. Guard: price row |
| Google Maps (per SERP of up to 100 results) · Local Finder (per 10 results) | Standard $0.0006 each | Main (small, big) for local businesses. Guard: price row |
| Bing organic (per 10 results) | Standard $0.0006 · Priority $0.0012 · Live $0.002 | Cross-check (big) · Reserve (small) |
| Clickstream bulk search volume | $0.012 per task + $0.00012 per keyword, Live only | Cross-check (big, covered markets) · Reserve (small). Guard: price |
| LLM Responses | Standard $0.0002 per task plus a $0.01 advance, with the unused part refunded | Reserve: use when one DataForSEO credential should replace the three `ai_probe` API keys |
| LLM Scraper | Standard $0.0012 per task | Reserve: it scrapes consumer AI apps, so only with the owner's explicit approval for a one-off parity check |

**MCP:**
- Official server `github.com/dataforseo/mcp-server-typescript` (npm `dataforseo-mcp-server`), remote
  `https://mcp.dataforseo.com/mcp`. The docs list several paths; test which one answers.
- Auth uses your API login and password.
- Trim response fields with `FIELD_CONFIG_JSON` to save tokens.

**Cost tactics:**
1. Standard queue, not Live, for anything that isn't interactive.
2. Fill Keywords Data tasks to 1,000 keywords; you pay per task, not per keyword.
3. Request only the SERP depth you need; every extra 10 results costs another base price.
4. Avoid operator queries (5×).
5. Load AI Overviews only for the keywords where they matter (2×).
6. Cache SERPs for clustering; they don't need to be fresh to the minute.

## Moz

**Justified when** a client or stakeholder reports in **Domain Authority / Page Authority / Spam Score**, or you need
a second link index to cross-check Ahrefs or Majestic.

**Stack:** API Free tier: Cross-check (default and small backlinks), with Starter Medium only while link building is
active on a small site, because it has no overage. Big sites and keyword metrics: Reserve, use when stakeholders
report DA or Spam Score. Moz Pro: Reserve (UI only).

Moz Pro figures are [UNVERIFIED], because moz.com blocked an earlier fetch. The Moz API figures were read from moz.com
on 2026-10-24.
- **Moz Pro:** Starter $49, Standard $99, Medium $179, Large $299 per month (about 20% off annually). Moz Pro includes
  no paid API access.
- **Moz API:** sold separately. Free: 50 rows a month, one request every 10 seconds; a card is needed at sign-up.
  Starter: $20 for 3,000 rows (no overage) or $75 for 15,000 ($5 per extra 1,000). Growth: $125 for 50,000 rows,
  $250 for 120,000 or $500 for 500,000. Every plan includes URL Metrics, Links, Link Intersect, Linking Root Domains,
  Anchor Text and Brand Authority. Auth is an `x-moz-token` header.
- **MCP:** official and in beta, on paid plans, for account owners: `https://api.moz.com/mcp/v1/data`, with OAuth or
  `Authorization: Bearer <Moz API key>`. On the free tier it is [UNVERIFIED]. The credit guard doesn't recognise Moz.

**Cost tactics:**
- Use DA/PA only as a relative comparison. It is not a Google metric.
- Pull metrics for shortlisted prospects only, never whole link lists.

## Other paid tools

| Tool | Justified for | Price | API / MCP | Stack |
|---|---|---|---|---|
| **Majestic** | Trust Flow / Citation Flow, topical link graphs | Lite $49.99 · Pro $99.99 · API $399.99/mo | Full API on the API plan only; no MCP | Reserve: use when an unnatural-links manual action or a migration link audit is open |
| **SE Ranking** | Cheaper all-in-one rank tracking + audit + AI prompts | Core $129 · Growth $279/mo · standalone API from a $50 wallet (250,000 credits that never expire) | MCP in every API tier (`https://api.seranking.com/mcp`) | Data API (to build: guard prices), for competitor keywords and gaps with a Georgia database: Main (small). In the big list it splits by market: Main for the GE pairs and the markets DataForSEO Labs lacks, and Cross-check (big, in markets Labs covers), where Labs is Main. Backlinks, Website Audit, Rank Tracker: Reserve. Reserve (default) |
| **Similarweb** | Competitor traffic, sources, audience overlap (estimates) | Quote-only | MCP needs API, Business or Enterprise | Reserve: use when a board-level market-sizing decision is due and an API contract is budgeted |
| **SpyFu** | Historical PPC / competitor ads | ~$39–$249/mo [UNVERIFIED] | API on Pro + AI ($40 API credit a month) and Team ($100), pay as you go above that | Reserve: use when historical Google Ads keywords and ad copy are needed in its 16 countries (no Georgia or Israel) |
| **Keywords Everywhere** | Cheap volume/CPC overlay while browsing; small API jobs | From $84/yr for 100k credits (1 credit = 1 keyword volume) | API and MCP on all plans | Reserve: use for spot checks in the countries its checker offers (no Georgia) |
| **AlsoAsked** | People-Also-Ask question trees | From $12/mo billed annually: Basic $15 · Lite $29 · Pro $59 ($47 annual) monthly | API and MCP on Pro only; MCP at `https://alsoasked.com/mcp` | Reserve: use when a question hub of 100+ pages is planned |
| **AnswerThePublic** | Question/preposition idea lists | From $20/mo: $20 · $99 · $199 | No API listed | Reserve: use when a person brainstorms seeds by hand |
| **Local Falcon / DataForSEO local** | Map-pack geo-grid rankings | Per-scan pricing: Local Falcon from $24.99/mo at 1 credit per grid point; DataForSEO Maps $0.0006 per point | Local Falcon: API and MCP from Starter. DataForSEO: the connector | DataForSEO Maps grid: Main (small, big) for local businesses. Local Falcon: Cross-check (big, local) · Reserve (small) |

## AI visibility trackers

**Justified when** you need repeated, automated prompt tracking across engines over time. The free method in
`seo-ai-search` (a frozen query set, 3–5 manual runs per engine, `ai_visibility.py` with confidence intervals) is enough
to *start*, and to decide whether a tracker is worth paying for. In the Main stack, `ai_probe` runs the frozen set
through the engines' official APIs instead, and Claude never drives the consumer apps.

| Tool | Price | Engines | API / MCP | Stack |
|---|---|---|---|---|
| Ahrefs Brand Radar | from $199/mo; prompt packs $50–$250 | AI Overviews, AI Mode, ChatGPT, Gemini, Perplexity, Copilot, Grok, Claude | API + MCP | Cross-check (big, to build): custom prompts through REST v3, storing only the Claude (API), AI Overview and AI Mode data |
| Semrush AI Visibility | $99/mo per user (25 prompts); Semrush One bundles 50–200 | ChatGPT, Google AI Mode | — | Reserve: use when the owner already pays and wants a dashboard for people |
| Otterly.AI | Lite $29 (15 prompts) · Standard $189 (100) · Premium $489 (400) | ChatGPT, AI Overviews, Perplexity, Copilot (+AI Mode, Gemini, Claude as add-ons) | API + MCP from Standard | Reserve: use when a big site has no Ahrefs and Otterly documents API-based collection |
| Profound | Enterprise; 7-day trial | up to 9 engines | Enterprise | Reserve: use when an enterprise client contracts it |
| Peec AI | prices not shown on vendor page [UNVERIFIED ~€89+] | ChatGPT, Perplexity, Gemini | API, MCP | Reserve: use when a client already uses it |
| DataForSEO LLM Mentions / Responses | pay per task | ChatGPT, AI Overviews (Mentions); ChatGPT, Claude, Gemini, Perplexity (Responses) | API + MCP | Reserve: Mentions when a covered market is a target; Responses as an alternative `ai_probe` backend |
| `ai_probe` (planned script) | Search fees: OpenAI $10 and Anthropic $10 per 1,000 searches, Perplexity $2.50 per 1,000, plus tokens | ChatGPT, Claude, Perplexity, as API stand-ins | The vendors' official APIs | Main (small, big; to build). Reserve (default), where GA4 AI-referral sessions are the AI-answer signal |

**Cost tactics:**
- Freeze 25–50 prompts that map to real revenue topics before buying.
- Track weekly, not daily; AI answers vary run to run anyway.
- Prefer the tracker bundled with a tool you already pay for.

## Cost-optimisation playbook

1. **Free data first, always:** GSC, Bing WMT, GA4, PSI/CrUX, Ahrefs Free, Screaming Frog free mode, and this
   plugin's scripts. Many questions end here.
2. **Shortlist before you pay.** Generate ideas free (`keyword_ideas.py`, GSC, PAA). Pay for volume/difficulty
   only on the shortlisted cluster head terms (often 20–100 keywords, not 5,000).
3. **Pick the cheapest source per data type:**

| Data | Cheapest source | When to pay more |
|---|---|---|
| Bulk volumes | DataForSEO Keywords Data (~$0.06 per 1,000 keywords) | Semrush or Ahrefs when you also need difficulty and SERP context in one place |
| Competitor keywords/traffic | Semrush (Semrush is strongest here) | — |
| Backlinks | Ahrefs Free for your own site | Ahrefs Lite/Standard for competitors; DataForSEO Backlinks for pay-per-use |
| Rank tracking | GSC (free, your own queries) | DataForSEO SERP Standard queue for competitor/locale tracking; Semrush or Ahrefs if you already pay |
| AI visibility | Manual frozen set + `ai_visibility.py` | Brand Radar or Otterly when you need weekly multi-engine tracking |

   The [Main stack](#main-stack) ranks by unattended automation first and by Georgian coverage, so for competitor
   keywords it puts SE Ranking and DataForSEO ahead of Semrush, and for AI visibility it puts `ai_probe` first.

4. **Limit every call:** row limits, single country/database, only needed fields, no historical data unless asked.
5. **Estimate before running.** Ahrefs free test targets show the unit cost in headers; Semrush has the free
   `countapiunits` balance check; DataForSEO lists prices per task. State the expected spend in the report. The credit guard defers any call
   above `ask_above_pct` to the end-of-run questions, so never stop mid-run to ask (`references/autonomy.md`).
6. **Cache and snapshot.** Store results in the project's `seo-work/` folder with the date; reuse within 30 days
   (volumes) or 7 days (SERPs) instead of re-pulling.
7. **Use what's included:** plan MCP allowances (Semrush 50k units, Ahrefs plan units, included Brand Radar checks),
   Projects data and scheduled crawls before ad-hoc reports.
8. **Seats:** one paid seat per person who actually pulls data. Share exports, not logins (sharing logins usually
   breaks the terms).
9. **Log the spend** in `SEO-WORKLOG.md` (units/credits per task) to see which tool earns its cost.
10. **Budget stacks:**

| Budget | Stack |
|---|---|
| $0/mo | GSC + Bing WMT + GA4 + PSI key + Ahrefs Free + Screaming Frog free + seo-suite. For unattended runs this is the [default free stack](#default-big-website-free-only) |
| ~$130–200/mo | Add **one** of: Ahrefs Lite ($129, links-heavy work) **or** Semrush Starter ($199, keyword and competitor-heavy work; the $139 SEO plan lists no MCP access, so a run can't use it), plus a $50 DataForSEO wallet for bulk volumes and SERPs |
| ~$500+/mo | Ahrefs Standard **or** Semrush Pro+, plus Screaming Frog licence, a DataForSEO wallet, and an AI tracker (Brand Radar or Otterly Standard) if AI visibility is a KPI |

The default free stack costs $0 at every size. With paid tools set up, the
[Main stack](#monthly-cost-of-the-stacks) needs no subscription for a small site (about $15–20 a month, pay per
use). For a big site, Main is about $140–200 a month and Main + Cross-check, with Ahrefs Standard as the one
subscription, about $400–710.
