# SEO tools: the paid lists, Reserve and vendor notes (prices checked 2026-10-24)

Read this only when a paid budget or credential is set, the user asks for a paid tool, or a free row's Reserve rule
may apply. The default free stack, the labels and the rules behind every list are in
[tools.md](tools.md). Facts new to these lists have their sources in [tools-sources.md](tools-sources.md).

## Paid lists by category

Each category has a small and a big paid list and a Reserve table. They take over from the default free stack per
category as [tools.md](tools.md#default-big-website-free-only) describes.

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
| 2 | Search Console API, Search Analytics **(through claude-seo)** | Main | The only measured demand: impressions, clicks and position per query, page and country, in any language. The free check on every vendor volume. It has no language dimension, so ka, ru and en come from the URL path or the query's script | `claude_seo.py gsc-export` with the property named, on the user's one-time OAuth sign-in (`webmasters.readonly`) or a service account an owner adds as a property user. 25,000 rows a request, 50,000 rows a day per search type, 2–3 days behind. Without either: exports, or Search Console in the browser while the user is signed in | $0 |
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
| 2 | Search Console API **(through claude-seo)** | Main | As Small, for the freshest days | As Small | $0 |
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
| 6 | Search Console URL Inspection API **(through claude-seo)** | Main | Google's own verdict per URL: indexed or not, Google-chosen against declared canonical, last crawl, robots state, and detected rich results with their issues. 2,000 a day per property covers a small site. Indexed version only, no live test | Measurement owns the quota and schedule; Technical reads the results. `claude_seo.py run gsc_inspect.py --site-url <property> --batch urls.txt --json` on the sign-in or service account, `webmasters.readonly`, 600 a minute | $0 |
| 7 | `schema_rules.py` | Main | Google's rich-result requirements as pure data, run on every crawled page and on the rendered DOM. Knows retired features (FAQ, HowTo, sitelinks search box). Re-check it when Google changes its search gallery | Pure function inside the scripts | $0 |
| 8 | `psi.py` (PageSpeed Insights API v5) | Main | The Lighthouse lab audit per template: LCP element, biggest opportunities, failed SEO audits. Google plans to drop CrUX field data from this API, so field data comes from rank 9. Small sites often have no CrUX data, which makes lab data the main signal | Set `psi_api_key`: Google recommends a key for automated queries and publishes no quota. On 429 the run continues without PSI | $0 |
| 9 | CrUX API and History API **(to build: in `psi.py`)** | Main | Field p75 LCP, INP, CLS, FCP and TTFB per origin or URL and form factor, LCP subparts, and up to 40 weekly points. Often origin-only or empty on small sites: record "no field data" and use lab | Free Cloud key, 150 queries a minute per project, which paying can't raise. History refreshes on Mondays, so the monitor runs on Tuesdays | $0 |
| 10 | `render_diff.py` | Main | Raw HTML against the rendered DOM: a title, robots or canonical that changes after JavaScript, and content or links that exist only after rendering. One URL per template settles whether a rendering crawler is needed at all | Rendered DOM from rank 11 | $0 |
| 11 | claude-seo `render_page.py` (`claude_seo.py render`) | Main | The unattended renderer for `render_diff.py`: Playwright Chromium with claude-seo's SSRF guards, one `python3` command, so it works in `claude -p` and launchd jobs that allow only `Bash(python3 *)` | Installed on first use (git clone of main, a venv and Chromium, about 150 MB) and pulled before every use. Headless Chrome (`--dump-dom`, default User-Agent: a Googlebot UA from a non-Google IP looks spoofed) renders only when claude-seo can't be set up. Own site only | $0 |
| 12 | `log_analyze.py` | Main | What Googlebot, Bingbot and AI bots actually fetched: crawl waste, errors served to bots, sitemap URLs never crawled, DNS-verified fake Googlebots. Lower here because shared hosts often give no complete logs | Logs delivered to the run (host export, rsync, an S3 pull). Combined format and `.gz` only. `--verify-dns` | $0 |
| 13 | Chrome DevTools MCP (official) | Main | Diagnoses a poor field INP or LCP with performance traces and insights, throttling and User-Agent emulation. It can save a DOM after interaction. Its Lighthouse audit has no performance category | Local stdio with `--headless --isolated --performance-crux=false --usage-statistics=false`: by default it sends trace URLs to CrUX and usage statistics to Google. Test it once under launchd | $0 |
| 14 | IndexNow **(to build: submitter)** | Main | Finishes the job after a fix ships: changed URLs reach Bing, Yandex, Seznam, Naver and Yep. Google doesn't use it | Measurement owns the submitter and schedule. Autonomy level 3 and above | $0 |
| 15 | Bing Webmaster Tools API (`GetCrawlStats`, `GetCrawlIssues`, `GetUrlInfo`, `FetchUrl`) **(to build: Bing client)** | Cross-check | Compares Bing's crawl counts and errors with `log_analyze.py`'s Bingbot hits and `crawl.py`'s errors, and `FetchUrl`'s result with our own fetch, which catches a CDN or WAF serving bots differently. Free, so weekly in the technical monitor, and always when there are no logs | The same Bing client as Measurement | $0 |
| 16 | DataForSEO On-Page API **(guard: page cap)** | Cross-check | A second crawler from other IPs, with optional JavaScript or browser rendering and microdata validation. Compares status codes, redirects, canonicals, duplicates (including pages past `crawl.py`'s first 600) and structured-data errors with `crawl.py`. Worth it quarterly with the full audit, after a release or migration, or when `render_diff.py` shows a template depends on JavaScript | Connector, Standard queue. As shipped the guard clamps `max_crawl_pages` to `max_rows` (50), so a full check needs its own page cap. Never set `robots_txt_merge_mode=override` | One 2,000-page crawl a quarter: $0.30 raw, $3.00 with JavaScript, $10.20 with browser rendering. ≈ $0.10–3.40 |
| 17 | Technical drift (`claude_seo.py drift`) **(through claude-seo)** | Cross-check | As in the default stack: each crawl against each URL's known-good baseline, so a release that drops a canonical, schema block or H1, or adds a noindex, shows up in the next run's triage | One snapshot per crawl run from `crawl.py --csv`, the first run only baselines, `--rebaseline` after verified fixes | $0 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Screaming Frog SEO Spider (licensed), CLI | Main | Crawls the whole site with Chromium rendering, structured-data validation, near-duplicates, custom extraction, crawl comparison, list mode for migrations, and Search Console, PSI and GA4 joined per URL | `--headless --crawl … --config … --save-crawl --export-tabs … --project-crawl-comparison true` from launchd or cron, on a machine with `licence.txt` and the accepted EULA. A licence per person who runs crawls. Keep the Ahrefs, Majestic and Moz integrations off (they spend those vendors' units), and its URL Inspection join off (it spends Measurement's quota) | £199 a year per user (≈ £17 a month) |
| 2 | `crawl.py`, per section | Main | A raw-HTML crawl per `--path-prefix` section, up to 2,000 pages each, in parallel subagents. Its output is the only crawl `triage.py` and the research store can ingest, so it stays Main until a Screaming Frog CSV adapter exists. A section that differs from Screaming Frog flags JavaScript dependence or drift in Screaming Frog's saved config | One section per subagent | $0 |
| 3 | `sitemap_check.py` | Main | As Small, per section and locale. It stops at 200 sitemap files, so on very large sites run it per child index | As Small | $0 |
| 4 | `robots_check.py` | Main | As Small. Test facet and parameter rules with `--path` | As Small | $0 |
| 5 | `log_analyze.py` | Main | Crawl budget is a real question at this size, and only logs answer it. CDN logs (usually JSON) need converting first, and no converter is built | As Small, logs pulled on a schedule | $0 |
| 6 | Search Console URL Inspection API **(through claude-seo)** | Main | 2,000 a day can't cover the site, so inspect changed URLs, money pages and a rotating sample per template. Whether separate URL-prefix properties per locale folder each get 2,000 a day is [UNVERIFIED] | As Small | $0 |
| 7 | CrUX API and History API **(to build: in `psi.py`)** | Main | Big sites more often have URL-level field data: sample the top URLs per template plus the origin | As Small | $0 |
| 8 | `psi.py` | Main | The lab audit per template, which explains poor field numbers | As Small | $0 |
| 9 | `page_audit.py` | Main | Each key template in full, and the CI gate that stops a template regression before it reaches thousands of URLs | As Small | $0 |
| 10 | `redirect_check.py` | Main | Migration maps and shipped redirect fixes at scale | `--workers 8` | $0 |
| 11 | `schema_rules.py` | Main | As Small | As Small | $0 |
| 12 | `render_diff.py` | Main | Decides which sections need Screaming Frog's rendering, which is far slower | As Small | $0 |
| 13 | claude-seo `render_page.py` (`claude_seo.py render`) | Main | As Small | As Small | $0 |
| 14 | Chrome DevTools MCP | Main | As Small | As Small | $0 |
| 15 | IndexNow **(to build: submitter)** | Main | After each release, changed URLs in batches of up to 10,000 | As Small | $0 |
| 16 | DataForSEO On-Page API **(guard: page cap)** | Cross-check | Compares status codes, redirects, canonicals, duplicates and microdata errors with Screaming Frog on sampled sections (5,000–20,000 pages). It catches geo-, IP- or User-Agent-dependent serving and WAF blocks that a crawl from one machine misses. Worth it after releases and migrations, and when Screaming Frog and `crawl.py` disagree | As Small | Per 1,000 pages: $0.15 raw, $1.50 with JavaScript, $5.10 with browser rendering. A monthly 20,000-page sample ≈ $3, $30 or $102 |
| 17 | Bing Webmaster Tools crawl API **(to build: Bing client)** | Cross-check | As Small, and against Screaming Frog's error lists | As Small | $0 |
| 18 | Technical drift (`claude_seo.py drift`) **(through claude-seo)** | Cross-check | As Small, on each section crawl's CSV | As Small, `--workers 8` | $0 |

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
| 1 | Search Console API, Search Analytics **(through claude-seo)** | Main | First-party clicks, impressions and average position by query, page, country, device and date. AI Overview and AI Mode appearances count inside Web. It feeds `gsc_analyze.py` and the per-country CTR curve behind visibility and share of voice. Show it beside snapshot rank, never averaged with it. Don't compare impressions or position across 2025-05-13 to 2026-04-27 | The same `claude_seo.py gsc-export` as Keywords. Each run re-pulls only the last ~3 days. 1,200 queries a minute per site | $0 |
| 2 | DataForSEO Google Organic SERP API (AI Overview on the money tier) | Main | The only compliant source of fixed-condition rank snapshots and competitor positions: Google has no SERP API, and seo-suite must not query google.com. One task gives rank, URL, SERP features, AI Overview presence and its reference domains. Georgia 2268 (Tbilisi 1007469, Batumi 1007466; the US state 21143 is a trap), with ka, ru and en | Connector, Standard queue, up to 100 tasks a POST, free `tasks_ready`. Validate locale pairs against DataForSEO's lists at the start and fail loudly on an unsupported one. Snapshots go to the research store; the rank-snapshot store is to build | Per pair, at the B6 sizing (50 money keywords daily at depth 10, 450 weekly at depth 20): $3.22, plus $0.90 for AI Overview, plus ≈ $0.65 for daily runs during 2 weeks of rollouts a year. 2 pairs ≈ $9.50 |
| 3 | `ai_probe.py`: OpenAI, Anthropic and Perplexity APIs | Main | The only route to automated ChatGPT, Claude and Perplexity answers within the vendors' terms. Rows are labelled "API stand-in": OpenAI says its search API uses the same models and tool as ChatGPT Search, and Perplexity says API results differ from its UI. Locale through `user_location` (GE, Tbilisi), untested. Prompts written natively in ka and ru, and a brand alias table covers Latin, Mkhedruli and Cyrillic spellings. Rows go to `ai_visibility.py` for Wilson intervals | Three API keys. Model and tool version pinned per row, 3 runs per prompt. Routine probes on a pinned model with one search (for Claude `claude-sonnet-5-5` with `max_uses=1`; Haiku is not allowed). Outside the guard's hook, so the collector reads `other_monthly_usd`, `per_run_cap_pct` and the guard's ledger, records its own spend there and stops itself ([budget settings](#credit-guard-limits)). Perplexity's API Terms §5.1 make its performance confidential information, so named cross-vendor metrics that include Perplexity get legal review before any client report | 20 prompts × 2 languages × 3 engines × 3 runs = 360 probes: $2.70 in search fees plus tokens. ≈ $3–6 [estimate: about 10,000 tokens in and 1,000 out per probe] |
| 4 | DataForSEO Google AI Mode API **(guard: price row)** | Main | The only automatable AI Mode answers and cited references per keyword and locale. Its 43 languages include ru and en but not ka, so reports say GE-ka AI Mode is not measured | Same connector, `ai_mode/task_post` in the Standard queue. The guard has no AI Mode row and prices it at half ($0.0006 against $0.0012) | 50 money keywords × GE-ru weekly ≈ $0.26 |
| 5 | Bing Webmaster Tools API (`GetQueryStats`, `GetPageQueryStats`) **(to build: Bing client)** | Main | Free first-party Bing positions, clicks and impressions per query and page. Bing grounds Copilot. The methods take no country, device or date range, so the data is labelled "Bing, all markets" | Weekly pull into its own table. `gsc_analyze.py` already maps Bing's columns | $0 |
| 6 | Google Search Status Dashboard feed | Main | Google's own start and end dates for updates. The pipeline moves the money tier to daily during a rollout, holds alerts, and compares only a full week after the rollout ends | `GET https://status.search.google.com/incidents.json` once a run. No key; robots.txt allows it | $0 |
| 7 | SerpApi, Free plan **(to build: collector)** | Cross-check | A second SERP collector with its own parser and infrastructure. Compares `rank_absolute` for the same keyword, locale and device on the same day with DataForSEO, only for keywords about to alert (entering or leaving the top 3 or top 10, or a move of 3+ positions held for 2 snapshots). Alert when both agree within 2 positions. Otherwise record "collector disagreement" and re-check on the next run. Worth it whenever an alert reaches a client | REST with `api_key` from the environment, `gl=ge`, `hl=ka` or `ru`. Outside the guard: the free plan has no overage, and the collector counts its own calls. The Legal Shield covers only Production ($150) and higher | $0 within 250 searches a month (50 an hour) |
| 8 | GA4 AI-referral sessions (`analytics-mcp`) | Cross-check | Real sessions from chatgpt.com, perplexity.ai, claude.ai, copilot.microsoft.com and gemini.google.com landing on cited pages. Compares the direction of `ai_probe`'s citation rate per engine with referral sessions to the pages that engine cites. Citations rising while referrals stay flat mean the prompts miss real demand, or citations earn no clicks. Direction only, never levels. Free, so in every monthly report | Read-only, service-account impersonation, `analytics.readonly` | $0 |

**Big sites**

| # | Tool | Role | Why | How a run drives it | Monthly cost |
|---|---|---|---|---|---|
| 1 | Search Console API **(through claude-seo)** | Main | As Small, with one request a day per country filter. The CTR curve is fitted per country and device and refitted quarterly | As Small. One property's requests at a time; on a quota error, retry once after 15 minutes, then fail loudly | $0 |
| 2 | Search Console bulk export to BigQuery | Main | Removes the 50,000-row cap and flags anonymised queries. Average position = SUM(sum_top_position) / SUM(impressions) + 1 | As in Keywords; shared and counted once | As in Keywords |
| 3 | DataForSEO Google Organic SERP API | Main | Snapshot rank, SERP features, AI Overview and competitor domains for the whole locale matrix, desktop and mobile. Share of voice and AI Overview citation share for us and every competitor come from the same data. Keyword sets are versioned | As Small. Tag each task with project, locale, device and keyword-set version | 200 keywords × 6 pairs × 2 devices weekly at depth 20 with AI Overview ≈ $19, a daily money tier (50 × 6 × 2) ≈ $11, a monthly depth-100 run ≈ $14.40 (the guard caps depth at 50 until limits are per endpoint), and a rollout allowance ≈ $5. ≈ $50 |
| 4 | `ai_probe.py` | Main | As Small, plus share of voice per engine, language and prompt class, a citation-source gap, and accuracy grading against a facts sheet. "Wrong" claims go to human review before any client report | As Small | 40 prompts × 3 languages × 3 engines × 3 runs = 1,080 probes: $8.10 in search fees plus tokens. ≈ $10–18 [estimate] |
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
| 1 | Search Console API: Search Analytics, URL Inspection, Sitemaps **(through claude-seo)** | Main | Google's own clicks, impressions and positions for 16 months, and its indexing verdict per URL. A small site fits the 2,000 inspections a day: every URL weekly, changed URLs daily. `sitemaps.submit` lets a level-4 run submit a sitemap itself. Owns the URL Inspection quota for every category | Service account as a property user: `webmasters.readonly`, plus `webmasters` only for `sitemaps.submit` at level 4 (`claude_seo.py submit-sitemap`). Never the Indexing API scope. One day per request with `dataState=final`. Google publishes no Search Console MCP. Without a sign-in or service account: exports. Never script the Search Console UI | $0 |
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
| 1 | Search Console API **(through claude-seo)** | Main | Fresh days by country, URL Inspection of changed URLs plus a fixed sample per template, and `sitemaps.submit` at level 4. Comparing the API's daily totals with the export's site table shows how much the API truncates | As Small. One property at a time; retry once after 15 minutes, then fail loudly | $0 |
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
| Community MCP (`zizzfizzix/mcp-server-bwt`) | A run needs Bing Webmaster API tools before the plugin's own Bing client exists. Audit and pin a version first. Search Console runs through claude-seo |
| Ahrefs GSC endpoints | A watched session with Ahrefs connected and no Google credential yet. 0 units except `gsc-anonymous-queries`. The same data as Search Console, so no cross-check value |
| Ahrefs Web Analytics | The site already uses it instead of GA4. Its API v3 `web-analytics` endpoints cost 0 units, but need a v3 key and the REST client (to build) |
| GA4 BigQuery export | GA4 reports hit thresholds or quotas, or event-level joins with the Search Console export are needed. Daily export up to 1M events on standard properties; streaming export $0.05 a GB |
| Semrush Sensor | As in Rank |
| Google Places API | Only to resolve a location's Place ID. Its terms forbid storing names, addresses or reviews |
| DataForSEO Business Data (Google My Business Info, Reviews) | Comparing map-pack competitors' categories, ratings and review velocity, which the Business Profile API can't give. About $0.0015 a profile [UNVERIFIED]. Store counts, not review text |
| Search Console generative AI report, Bing AI Performance report | See the Rank Reserve |

### Credit-guard limits

What `scripts/credit_guard.py` does today, and what that means for the paid lists:

- **Unpriced vendors share one small allowance.** SE Ranking, AlsoAsked, Similarweb, Otterly and Keywords Everywhere
  calls, and Lumar crawls, share `other_monthly_usd`, and each call is counted at `ask_above_pct` of it. At the
  defaults (25% a run, 5% a call) that is 5 calls a run and 20 a month for the whole bucket, whatever the budget, and
  0-credit calls count too. Raising `other_monthly_usd` doesn't change the count, and lowering `ask_above_pct` is
  global. A per-vendor bucket and an SE Ranking price table would fix this; until then, plan around it.
- **One row limit for everything.** `max_rows` (default 50) also clamps DataForSEO `depth`, `limit` and
  `max_crawl_pages`, and adds them when missing. So On-Page stops at 50 pages, a 1,000-row Labs pull becomes 20 tasks,
  and depth 100 is capped at 50. Raising `max_rows` loosens Semrush and Ahrefs too. Per-vendor and per-endpoint limits
  (Labs and Backlinks 1,000, SERP depth 100, On-Page up to the site's URL count) would fix this.
- **Missing price rows.** AI Mode is priced as a generic SERP, half its $0.0012. Maps is billed per 10 results, while
  DataForSEO bills per 100. Clickstream, LLM Responses, LLM Scraper and Business Data have no price, so each call is
  counted at 5% of the DataForSEO budget.
- **Tools the hook never sees.** Moz, Majestic, Local Falcon, SerpApi, OpenAI, Anthropic, Perplexity, and Ahrefs REST
  calls. Adding a vendor is a code change; until then they follow the no-overage rule. `ai_probe.py` and
  `rank_snapshot.py` read and record the guard's ledger themselves.

Costs in the lists are at the intended call shapes. **Budget settings** for the paid stacks
(`/plugin configure seo-suite@seo-suite`). The default free stack needs none, because it makes no paid calls:

| Option | Small | Big |
|---|---|---|
| `dataforseo_monthly_usd` | 25 | 270 |
| `other_monthly_usd` | 12, after the SE Ranking change, for SE Ranking (≈ $0.60) and `ai_probe` (≈ $6) | 35, after the SE Ranking change, for SE Ranking (≈ $3) and `ai_probe` (≈ $18) |
| `ahrefs_monthly_units` | 0 | Up to 320,000 (40% of Standard), read by the REST client |

- **`ai_probe`'s cap.** The hook never sees OpenAI, Anthropic or Perplexity calls, so `ai_probe.py` reads
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

## Semrush

**Justified when** you need competitors' keywords and estimated traffic, country-level keyword volume and
difficulty at scale, PPC/ad intelligence, or market and traffic estimates. These come from Semrush's ranking database.
The free path cannot replicate them.

**Shared-access ("group buy") proxies.** A Semrush session on a domain other than `semrush.com` (for example
`1.semrush.com.in`) is a third-party reseller. Semrush's terms may forbid shared accounts, the operator sees every
query, data can be cached or partial, and sessions expire without warning. Use it read-only, in the user's own
browser, never type credentials into it, tag its numbers `[vendor data: proxy]` with the database and date, and log
what was queried, since the credit guard never sees browser use.

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
| `ai_probe.py` | Search fees: OpenAI $10 and Anthropic $10 per 1,000 searches, Perplexity $2.50 per 1,000, plus tokens | ChatGPT, Claude, Perplexity, as API stand-ins | The vendors' official APIs | Main (small, big). Reserve (default), where GA4 AI-referral sessions are the AI-answer signal |

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

   The [Main stack](tools.md#main-stack) ranks by unattended automation first and by Georgian coverage, so for competitor
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
| $0/mo | GSC + Bing WMT + GA4 + PSI key + Ahrefs Free + Screaming Frog free + seo-suite. For unattended runs this is the [default free stack](tools.md#default-big-website-free-only) |
| ~$130–200/mo | Add **one** of: Ahrefs Lite ($129, links-heavy work) **or** Semrush Starter ($199, keyword and competitor-heavy work; the $139 SEO plan lists no MCP access, so a run can't use it), plus a $50 DataForSEO wallet for bulk volumes and SERPs |
| ~$500+/mo | Ahrefs Standard **or** Semrush Pro+, plus Screaming Frog licence, a DataForSEO wallet, and an AI tracker (Brand Radar or Otterly Standard) if AI visibility is a KPI |

The default free stack costs $0 at every size. With paid tools set up, the
[Main stack](tools.md#monthly-cost-of-the-stacks) needs no subscription for a small site (about $15–20 a month, pay per
use). For a big site, Main is about $140–200 a month and Main + Cross-check, with Ahrefs Standard as the one
subscription, about $400–710.
