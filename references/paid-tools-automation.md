# Paid SEO tools from Claude Code: the automation playbook (verified 2026-10-24)

How to connect each vendor, what every call costs, and what the vendor's terms allow, for unattended, credit-safe runs.
The `seo-automation` skill uses this file. Plans and prices for buying decisions are in `tools.md`.

**Rules:**
- **Official MCP or API, never the vendor's web UI.** Semrush, Ahrefs and Similarweb restrict automated UI use (§7).
- **Every fact has a source** in brackets, resolved in [Sources](#sources).
- **Marked [UNVERIFIED]** means no primary source confirmed it. Don't state it as fact.
- **Corrected claims only.** Where a research claim was refuted, only the corrected version appears here.
- **Re-check prices** older than ~3 months against the vendor page before quoting them.

## 1. Semrush

### Connect
- **Endpoint:** `https://mcp.semrush.com/v2/mcp`, streamable HTTP only. v1 is undocumented; don't use it [semrush-mcp].
- **Claude Code:** `claude mcp add semrush https://mcp.semrush.com/v2/mcp -t http`, then `/mcp` → Semrush MCP →
  **Authenticate** [semrush-mcp].
- **Auth:** OAuth 2.1 is the default. Clients without OAuth send `Authorization: Apikey <key>` [semrush-mcp].
  - The `seo-suite-semrush@seo-suite` plugin bundles the server as `semrush`, OAuth only.
  - **API-key route, run by the user** with the key in their own environment, never in chat:
    `claude mcp add --transport http semrush-key https://mcp.semrush.com/v2/mcp --header "Authorization: Apikey $SEMRUSH_API_KEY"`.
    The guard matches `mcp__semrush-key__*`.
- **Plans with MCP SEO data** [semrush-kb-mcp]:
  - Semrush One Starter and Pro+, and SEO Classic Pro and Guru: 50,000 API units each.
  - Semrush One Advanced and SEO Classic Business: an add-on package of 2M, 5M, 10M or 20M units.
- **Refresh timing:** the MCP FAQ says the allowance resets every monthly billing cycle [semrush-mcp-faq]. The KB says
  it refreshes on the renewal date [semrush-kb-mcp]. Annual-plan behaviour is [UNVERIFIED]. Unused standard API units
  expire rather than roll over [semrush-kb-api].
- **Units:** MCP calls use the same units as the API, with no extra MCP fees [semrush-mcp].
- **Read-only scope:**
  - all SEO API reports, all Trends API reports (by subscription), and the read-only Projects API v3 methods;
  - no creating projects, no Site Audit or Position Tracking settings, no starting crawls [semrush-mcp].
  - Setup writes exist only in the direct Projects API (Business plus units), at 100 units per request and 100 per
    keyword added [semrush-projects-overview].
- **Trends data** (`traffic_overview`, `audience_research`) needs Trends API Basic or Premium. It has its own quota,
  10,000 requests a month by default [semrush-trends-access].

### Tools and the call flow
- **12 discovery tools:** `domain_overview`, `organic_research`, `keyword_research`, `competitors_research`,
  `backlinks_research`, `audience_research`, `traffic_overview`, `paid_search_research`, `shopping_research`,
  `position_tracking`, `site_audit`, `projects`.
- **Two meta-tools:** `get_report_schema` (a report's parameters) and `execute_report` (runs it and spends units)
  [semrush-mcp].
- **Flow:** discovery tool → report id → `get_report_schema(report)` → `execute_report(params)`. UI names such as
  "Keyword Magic Tool" are not tools or report ids [semrush-kw-skill].
- **Report ids Semrush's own skills use as verified routes** [semrush-skills]:

  | Discovery tool | Report ids |
  |---|---|
  | `keyword_research` | `phrase_this`, `phrase_related`, `phrase_questions`, `phrase_organic` |
  | `organic_research` | `resource_organic`, `resource_organic_unique` |
  | `competitors_research` | `domain_organic_organic`, `domain_domains` (≤ 5 domains), `backlinks_matrix`, `backlinks_comparison` |
  | `backlinks_research` | `backlinks_overview`, `backlinks_refdomains`, `backlinks_anchors`, `backlinks`, `backlinks_historical`, `backlinks_pages` |
  | `traffic_overview` (Trends) | `summary`, `sources` |
  | `paid_search_research` | `resource_adwords` |
  | `domain_overview` | `domain_rank` |
  | `projects` | `list_projects` |
  | `site_audit` | `snapshots`, `info`, `meta_issues`, `issue_details`, `page_list`, `page_info` |

  Rediscover them each session; don't hard-code them.
- **`execute_report` input field names** (report id, limit, database, columns) are not publicly documented
  [UNVERIFIED]. Read them from `get_report_schema` at runtime and cache the schema for the session. Re-read it only
  when a parameter is rejected.
- **Documented fragments** [semrush-skills]:
  - `snapshots` takes the project id as `id`;
  - `issue_details` needs project, snapshot and issue ids plus a limit;
  - an optional `sort` may be rejected.
- **Discovery and schema calls:** whether they cost units is [UNVERIFIED]. KB 1618 says every MCP query consumes units
  [semrush-kb-mcp]. The units page says requests that return no data cost nothing [semrush-units]. Calibrate once, as
  in `seo-automation` A.6.

### Unit costs (per line returned unless marked; historical data ×5)

| Report | Units | Source |
|---|---|---|
| `phrase_this`, `phrase_these` (≤ 100 keywords), `phrase_organic`, `phrase_all` | 10 | [semrush-keyword] |
| `phrase_fullsearch` (broad match), `phrase_adwords` | 20 | [semrush-keyword] |
| `phrase_related`, `phrase_questions` | 40 | [semrush-keyword] |
| `phrase_kdi` (difficulty) | 50 | [semrush-keyword] |
| `domain_organic`, `domain_organic_unique`, `domain_rank`, `url_organic` | 10 | [semrush-domain] [semrush-overview] |
| `domain_organic_organic` (competitors) | 40 | [semrush-domain] |
| `domain_domains` (keyword gap) | 80 | [semrush-domain] |
| `backlinks_overview` | 40 **per request** | [semrush-backlinks] |
| `backlinks`, `backlinks_refdomains`, anchors, pages, matrix, comparison | 40 | [semrush-backlinks] |
| Site Audit: snapshots, info, meta issues, issue details, page id by URL | 100 per request | [semrush-sa] |
| Site Audit: page info | 1,000 per request | [semrush-sa] |
| Site Audit: **snapshot info, snapshots history** | **10,000 per request** (history: per snapshot). Never call | [semrush-sa] |
| Position Tracking: campaigns list, campaign dates, overview, visibility index | 100 per request | [semrush-pt] |
| Position Tracking: positions | 100 **per keyword** (500 keywords ≈ 50,000) | [semrush-pt] |
| Position Tracking: competitors discovery / landing pages | 1,000 per competitor / per page | [semrush-pt] |
| Projects v3: list or get project | 100 per request (v4 price [UNVERIFIED]) | [semrush-projects] |

- **Empty or failed calls:** an empty response costs 0. When units run short, per-line reports return only the lines
  you can afford. Otherwise you get ERROR 132, or HTTP 403 on the Projects API [semrush-units].
- **Cheaper keyword difficulty:** request the `Kd` export column of `phrase_these` (10 a line, up to 100 keywords)
  instead of `phrase_kdi` (50 a line) [semrush-keyword]. No Kd surcharge is documented, but this has not been checked
  with a metered call.
- **v3 keyword and backlink reports are deprecated** in favour of v4 but still work. v4 is billed at v3 rates during
  Early Access [semrush-v4-backlinks] [semrush-v4-keywords].

### The 10,000-row trap and the row-limit rule
- **The trap:** in the v3 SEO API, an omitted or zero `display_limit` returns **10,000 lines**, at most 100,000 per
  request [semrush-keyword] [semrush-domain]. One unlimited `domain_organic` call can cost 100,000 units, twice the
  50k allowance. An unlimited `phrase_related` can cost 400,000. Whether the MCP applies its own default is
  [UNVERIFIED].
- **The rule, enforced by the credit guard:**
  - Every `execute_report` carries an explicit row limit of `max_rows` (default 50) or less. Semrush's own skills start
    at 30–50 rows and widen only after reviewing the first batch [semrush-kw-skill] [semrush-skills].
  - One `database` per call; never the all-database variants (`phrase_all`, `domain_ranks`, `url_ranks`).
  - No `display_date` unless the step is a trend analysis.
  - Server-side `display_filter` and `display_sort`, so the top N are the right N.
  - Minimal export columns.
  - At most 5 competitors, reused across steps [semrush-prompts].
- **Rate limit:** 10 requests per second and 10 simultaneous per account. Run at most 2–3 in parallel
  [semrush-limits].
- **Balance:**
  - `GET http://www.semrush.com/users/countapiunits.html?key=KEY` is free but needs an API key. Whether it shows the
    MCP allowance is [UNVERIFIED].
  - The Query log shows per-request spend for the SEO API. Whether MCP calls appear there is [UNVERIFIED]
    [semrush-units].
  - Otherwise use My Profile → Subscription info [semrush-kb-mcp].
- **Failures:** on ERROR 132, 403 or an access error, stop that branch and never retry in a loop. On a schema error,
  re-read the schema once, then fetch a small unfiltered set and filter it locally [semrush-kw-skill].
- **Prefer the MCP over the raw API** when the MCP covers the data. Semrush's llms.txt tells agents to [semrush-llms].

### UI-only: no API, so never drive the UI
Use an API equivalent where one exists, otherwise leave the feature out and say so in the report.
- Keyword Strategy Builder [semrush-ksb]; SEO Writing Assistant [semrush-swa]; Topic Research [semrush-tr].
- Keyword Magic Tool groups and subgroups, personal keyword difficulty (PKD), Backlink Audit Toxicity Score, and the
  Site Audit "Markup" and "Internal Linking" thematic reports [semrush-backlink-skill].
- Creating or configuring Position Tracking and Site Audit campaigns, unless the user has Business plus units for
  Projects API writes [semrush-projects-overview].
- AI Visibility Toolkit and Content Toolkit: no API in the docs. That none exists privately is [UNVERIFIED].

### Terms (ToS last updated 2026-08-25) [semrush-tos]
- **§3.3 bans:**
  - (k) automated systems that send more requests than a human could with a browser;
  - (p) harvesting or scraping, at any speed;
  - (e) working around technical limits;
  - (r) using Semrush outputs as inputs or prompts to any AI or LLM, except "Semrush's official integrations embedded
    into an AI system".

  The official MCP is the defensible route. Browser extraction into Claude conflicts with (p) and (r) even at human
  speed.
- **§3.3 API rules:** at most 10 inquiries per second per IP and 10 simultaneous per Authorized User. No caching for
  more than one month without written consent, so Semrush cache TTL ≤ 30 days.
- **§4.1 / §4.2:** one individual per account, credentials are never shared, and an API key belongs to one account.
- **User-supplied exports:** Semrush's own skills accept them as a fallback, but §3.3(r) literally covers them. Warn the
  user and let them decide. Whether this is allowed is [UNVERIFIED].

## 2. Ahrefs

### Connect
- **Endpoint:** `https://api.ahrefs.com/mcp/mcp` (Streamable HTTP), on Lite and higher plans [ahrefs-mcp-intro].
  Local setup is no longer supported: `@ahrefs/mcp` was archived on 2026-02-24 [ahrefs-mcp-help] [ahrefs-repo].
- **Claude Code:** `claude mcp add ahrefs https://api.ahrefs.com/mcp/mcp -t http`, then `/mcp` → log in → pick a
  workspace → **Allow** [ahrefs-mcp-cc].
- **Plugin:** `seo-suite-ahrefs@seo-suite` bundles the same endpoint as `ahrefs`, OAuth only. It is optional; skip it
  when the user already added Ahrefs.
- **Alternative auth:** an "MCP key" from Account settings → API keys, sent as `Authorization: Bearer <MCP key>`
  [ahrefs-mcp-openclaw]. MCP keys and API v3 keys are not interchangeable, except that Enterprise can use v3 keys
  [ahrefs-mcp-help].
- **Key caps:**
  - OAuth-created MCP keys default to a **200,000-unit monthly cap per key**, which admins can change.
  - Manually created keys have no per-key cap by default [ahrefs-mcp-intro].
  - Pay-as-you-go units can auto-charge. Disable or cap them in Limits & usage [ahrefs-keys].
- **Narrow the tool set with `?tools=`:**
  - 20 groups: site-explorer-overview, site-explorer-reports, keywords-explorer, serp-overview, rank-tracker,
    site-audit, brand-radar-simple, brand-radar-entities, web-analytics-overview, web-analytics-sources,
    web-analytics-geo, web-analytics-user-agents, web-analytics-pages, gsc, social-media, content-helper,
    batch-analysis, management, public, subscription-info.
  - Or `essentials`, which must be used alone.
  - An unknown group fails the connection with `invalid tool category` [ahrefs-tool-cats].
- **Tool names:** the docs list groups, not tools. The only confirmed names are `site-explorer-refdomains` and
  `keywords-explorer-volume-history`, which follow the REST path [ahrefs-mcp-openclaw]. Read the live list from
  `/mcp`. The `doc` helper name, the tool count, and an `apiUsageCosts` object in responses are reported only for the
  archived server or by third parties [UNVERIFIED].

### Metering and limits

| Plan | Units / month (MCP + Connect + API shared) | Max rows per request | Price / month |
|---|---|---|---|
| Lite | 200,000 | 100 | $129 |
| Standard | 800,000 | 250 | $249 |
| Advanced | 2,000,000 | 500 | $449 |
| Enterprise | custom | unlimited | $1,499 (annual) |

Units and rows: [ahrefs-api-help]. Prices: [ahrefs-pricing]. API, MCP and Connect need Lite or higher; Ahrefs Free and
Starter have no API [ahrefs-api-help].

- **Cost per request** = max(50, rows × the sum of unique field costs across `select`, `where` and `order_by`)
  [ahrefs-limits].
  - Most fields cost 1. `volume`, `keyword_difficulty`, `sum_traffic`, `traffic`, `org_traffic`, `org_cost`,
    `traffic_potential` and `intents` cost 10. `refdomains`-type fields cost 5 [ahrefs-openapi].
  - `volume_monthly_history` costs 2 per month (minimum 50) [ahrefs-ke-ref].
  - Cached responses cost 0. The cache TTL is undocumented [ahrefs-limits].
- **Default `limit` is 1,000** on most list endpoints [ahrefs-openapi]. What happens above the plan's row cap is
  [UNVERIFIED], so always send `limit` ≤ the plan maximum.
- **Free (0-unit) endpoints** [ahrefs-openapi]:
  - all rank-tracker GETs; all management endpoints; `subscription-info/limits-and-usage`;
  - `site-audit/projects`; all web-analytics; `gsc/*` except `gsc/anonymous-queries`; social-media;
  - public: `domain-rating-free` takes up to 1,000 targets per POST, needs a v3 key and requires the attribution
    "Domain Rating by Ahrefs". Crawler IPs need no key.
- **Fixed-price endpoints** [ahrefs-openapi]:
  - Site Audit `issues`, `page-explorer` and `page-content`: 50 units per request. The API cannot start a crawl.
  - Content Helper topics: 1,000, plus 500 with `target_url`. The scoring is never cached.
- **Budget guard:** `GET /v3/subscription-info/limits-and-usage` (free) returns `units_usage_workspace`,
  `units_limit_workspace`, `units_limit_api_key` and `usage_reset_date` [ahrefs-openapi].
- **Free test targets:** ahrefs.com, yep.com and firehose.com; the keywords ahrefs, yep and firehose; `limit` ≤ 100.
  They need a paid plan and an API key, and the `x-api-units-cost-*` headers are REST only [ahrefs-free-test]
  [ahrefs-limits].
- **Rate limit:** 60 requests per minute, HTTP 429 on excess [ahrefs-api-intro]. Monetary fields are USD cents
  [ahrefs-llms].
- **Batch Analysis:** `POST /v3/batch-analysis/batch-analysis`, 1–100 targets [ahrefs-openapi]. The web tool needs
  Standard [ahrefs-batch-help]. The API endpoint is documented as part of v3, which Lite can use [ahrefs-api-help];
  this has not been checked with a live call on Lite.
- **Rank Tracker:** updates weekly by default on all plans [ahrefs-rt-freq]. `date_compared` works only on `overview`,
  `competitors-overview` and `competitors-pages`. Call `serp-overview` and `competitors-stats` twice and diff them
  [ahrefs-rt-serp].
- **`traffic_mode`:** the default changed to adaptive on 2026-09-04. Pass `traffic_mode=static` for comparable
  history [ahrefs-changelog].
- **Brand Radar** [ahrefs-brand-radar]:
  - Refresh: AI Overviews every few days, chatbots monthly.
  - Custom-prompt packs: $50 for 2,500 checks, $100 for 7,000, $250 for 25,000. A Claude check uses 8 checks.
  - Index add-on: $199 a month per platform, or $699 for all platforms.

### Terms
- **MCP endpoint:** "custom scripts, bridges, or standalone HTTP/JSON-RPC clients" are not permitted. Programmatic use
  belongs on the public API [ahrefs-mcp-intro].
  - Use the MCP only through Claude Code's MCP client, in interactive sessions.
  - Whether a scheduled `claude -p` run counts as a script is [UNVERIFIED], so scheduled seo-suite runs leave Ahrefs
    out.
  - An Ahrefs REST v3 path with an API key is not built in seo-suite.
- **ToS §4.4** (2026-09-14) [ahrefs-tos]:
  - (i) no scraping except with Ahrefs' own software;
  - (j) no automated use except through the Ahrefs API;
  - (k) automated API use must respect Ahrefs' robots.txt;
  - (n) no circumventing limits.

  §8.4 allows suspension or IP blocks. The FAQ forbids shared logins [ahrefs-faq]. app.ahrefs.com serves a Cloudflare
  managed challenge to non-browser clients [ahrefs-cf].
- **Ahrefs Free** (formerly Webmaster Tools) data for verified sites is UI-only:
  - Site Explorer shows 1,000 backlinks and keywords;
  - Site Audit has 5,000 crawl credits per project per month [ahrefs-free].

## 3. DataForSEO

### Connect
- **Active server:** v3 at `github.com/dataforseo/mcp-server-typescript`, npm `dataforseo-mcp-server` 3.1.3
  (2026-10-02). It needs Node ≥ 22. The v2 server is deprecated [dfs-repo] [dfs-npm].
- **Four tools:**
  - `docs_index({section?})`, `docs_list_sections`, `docs_search({url, needCodeExample=false})`;
  - `api_request({method: GET|POST|PUT|DELETE, path | url, data, noAiMode=false})` [dfs-repo].
  - `api_request` refuses hosts other than api.dataforseo.com, so the free sandbox works only through curl
    [dfs-api-tool].
- **Plugin:** `seo-suite-dataforseo@seo-suite` bundles the server as `dataforseo`. It reads `dataforseo_login` and
  `dataforseo_password` from the plugin's sensitive config, which is stored in the Keychain [cc-plugin-ref].
- **Manual local stdio**, typed by the user in their own terminal only:
  `claude mcp add dataforseo --env DATAFORSEO_LOGIN=<login> --env DATAFORSEO_PASSWORD=<password> -- npx -y dataforseo-mcp-server@3.1.3`.
  `DATAFORSEO_USERNAME` is an alias [dfs-repo] [dfs-help-cc]. The help centre names this server `dfs-mcp`, so its
  tools appear as `mcp__dfs-mcp__*`.
- **Remote v3:** `https://mcp.dataforseo.com/v3/mcp`, OAuth 2.0 by default, or `Authorization: Basic <base64
  login:password>` [dfs-repo].
  - The help centre's `https://mcp.dataforseo.com/http` endpoint shows the deprecated v2 fingerprint [dfs-help-cc].
  - Local HTTP mode is `--mode http`, not a bare `http` argument [dfs-npm].
- **Live endpoints:** the MCP sends only the first task of a Live request and warns that the rest were dropped
  [dfs-live-mw].

### Standard vs Live

| API | Standard (queued) | Live | Notes |
|---|---|---|---|
| Google organic SERP, per 10 results | $0.0006 (~5 min) | $0.002 (~6 s); priority $0.0012 | +1 base per extra 10 results. Search operators ×5. `load_async_ai_overview` and `calculate_rectangles` +1 base each. PAA click +$0.00015 [dfs-serp-price] |
| Google Ads keyword data (search_volume, etc.) | $0.06 per task of ≤ 1,000 keywords (1–3 h) | $0.09 per task. 12 calls/min, one task per call | Same price for 1 or 1,000 keywords. `keywords_for_keywords` takes ≤ 20 seeds [dfs-ads-price] |
| Labs (keyword_ideas, domain_intersection, bulk KD, …) | — | $0.012 per task + $0.00012 per item, ≤ 1,000 items | `include_clickstream_data` ×2. `keyword_ideas` default limit 700, so always set it [dfs-labs-price] [dfs-keyword-ideas] |
| Backlinks | — | $0.024 per request + $0.000036 per row, ≤ 1,000 rows | `timeseries_new_lost_summary` charged per request [dfs-bl-price] [dfs-timeseries] |
| On-Page crawl, per page | $0.00015 | — | JS $0.0015; browser rendering $0.0051; Lighthouse $0.005. `max_crawl_pages` is the spending cap [dfs-onpage-price] |
| LLM Mentions | — | $0.10 per task + $0.001 per row | ChatGPT (US English) and AI Overviews; 60-day cycle [dfs-llm-mentions] |
| LLM Scraper (ChatGPT, Gemini) / AI Mode SERP | $0.0012 per result | $0.004 | LLM Responses Standard $0.0002 + $0.01 advance, up to 72 h [dfs-llm-responses] |
| Google Autocomplete | $0.0006 per task | $0.002 | [dfs-autocomplete] |

- **Account:** $50 minimum top-up, a $1 trial, funds don't expire [dfs-pricing].
- **Free sandbox:** dummy data in the real response shape [dfs-sandbox].
- **Labs vs Keywords for Keywords:** for small jobs, Labs Keyword Ideas is cheaper than Google Ads Keywords For
  Keywords [dfs-labs-vs-ads].

### Batching (scheduled jobs use Standard only)
- **`task_post`** [dfs-ads-post] [dfs-serp-post]:
  - up to 100 tasks per POST (more gives error 40006);
  - a `tag` of up to 255 characters for the run id;
  - optional `postback_url` / `pingback_url`;
  - every response carries a `cost` field.
- **Fill each Google Ads task** to 1,000 deduplicated keywords [dfs-ads-post].
- **Waiting:** wait the typical turnaround rather than polling hot. Then call `tasks_ready` (free, 20 per minute, up to
  1,000 tasks from the last 3 days) and `task_get/<id>` for each ready task [dfs-tasks-ready].
- **Results are kept** 30 days in Standard mode (SERP HTML 7 days), so store task ids and re-fetch rather than
  re-post. Live results are not stored: cache them locally [dfs-retention].

### `.ai` responses and FIELD_CONFIG
- **`.ai` paths:** `api_request` adds `.ai` to every path by default [dfs-api-tool].
  - `.ai` drops empty, null and false fields, rounds floats to 3 decimals, and defaults `limit`/`depth` to 10, at no
    extra charge.
  - It is documented for Live and Task GET endpoints only [dfs-ai].
  - What `task_post` does on a `.ai` path is [UNVERIFIED]. Send `noAiMode: true` on `task_post`.
- **Field config:** set with `--configuration <file>`, `FIELD_CONFIG_PATH` or `FIELD_CONFIG_JSON` (the JSON wins). It
  is keyed by exact endpoint path under `supported_fields` [dfs-field-config].
  - No wildcards.
  - `[]` or an unlisted path returns the full response.
  - An invalid config loads nothing, built-in defaults included.
  - It never matches `task_get/<id>` paths.
- **It trims after the response arrives,** so it saves Claude context, not DataForSEO money [dfs-field-config]
  [dfs-api-tool]. The hosted remote server can't load a custom config.

### Account controls (set by the human in the dashboard; automation only reads them)
- **`GET /v3/appendix/user_data`:** free, 6 calls per minute. Returns `money.balance`, `money.limits`, statistics and
  the base price table [dfs-user-data] [dfs-rates].
- **Daily spending limit** in API Settings, for all APIs or per API or endpoint. It runs per UTC calendar day, resets
  at 00:00 UTC (not a rolling window), and calls over it fail with **40203** [dfs-limit].
- **IP whitelist:** static IPs only; other IPs get **40207**. How it interacts with the hosted MCP is [UNVERIFIED]
  [dfs-ip].
- **Rate limits:** 10,000 calls per minute overall. 30 simultaneous for Labs, Backlinks, OnPage, Content Analysis,
  Trends and AI Optimization. Live Google Ads 12 per minute [dfs-rates].
- **Freshness** [dfs-freshness]:
  - the keywords database follows Google's monthly cycle; Google usually updates mid-month, which
    `GET /v3/keywords_data/google_ads/status/` shows;
  - Labs updates after its source, so check the free `GET /v3/dataforseo_labs/status`;
  - SERP database 30–90 days; backlinks full cycle ≤ 90 days; LLM Mentions 60 days.

## 4. Crawlers: Screaming Frog, Sitebulb, Lumar

### Screaming Frog SEO Spider
- **MCP:**
  - built into v24 and **works only with a paid licence**;
  - needs database storage mode, the default [sf-mcp];
  - the release history and v24 post date the MCP to 24.0 (19 May 2026); the FAQ says 24.1 [sf-mcp] [sf-v24].
- **MCP transports:** STDIO, as the Claude Desktop extension `spider-stdio-mcp.mcpb`, or Streamable HTTP with the UI
  running ("Start MCP Server", or the 24.1 auto-start setting) [sf-mcp].
  - The only documented URL is `http://localhost:11435/mcp`, from an LM Studio example. Confirm the port in File →
    Settings → MCP Server.
  - Screaming Frog documents no Claude Code command. `claude mcp add --transport http screaming-frog http://localhost:11435/mcp`
    is our form [UNVERIFIED].
- **29 tools,** e.g. `sf_list_crawls`, `sf_crawl(crawl_url, config_path, project_name, crawl_name)`,
  `sf_crawl_progress`, `sf_generate_report(category, file_path, data_fields, export_type CSV|NDJSON)`,
  `sf_export_seo_element_urls(…, start_index, max_rows)`, `sf_url_info` and `sf_url_links` [sf-mcp].
  - Node tools (`sf_run_node_js_script`, `sf_npm_install`) are off by default. File access is limited to an allowed
    base directory.
  - Only the licensed user may access the software through the MCP.
  - Save reports to files and parse them with scripts. List mode isn't supported through the MCP [sf-mcp] [sf-v24].
- **Unattended crawls use the CLI, not the MCP.** They cost no credits [sf-guide].
  - Example: `ScreamingFrogSEOSpiderLauncher --crawl https://example.com --headless --save-crawl --output-folder ./seo-work/sf --timestamped-output --project-name example --task-name weekly --project-crawl-comparison "true" --export-format csv --export-tabs "Internal:All,Response Codes:Client Error (4xx)"`.
  - On macOS the launcher is in the app's `Contents/MacOS`.
  - Values: `--export-tabs "Tab:Filter"`, `--bulk-export "Submenu:Export"`, `--save-report "Submenu:Report"`.
- **Only one process** can use the crawl database at a time, so close the GUI for CLI runs [sf-guide].
- **Licence:** £199 / $279 / €245 per user per year; 5+ licences £189 down to £169. Free mode crawls 500 URLs and can't
  save crawls [sf-pricing] [sf-faq]. Whether the CLI or `--headless` needs a licence is [UNVERIFIED]. On a machine
  with no UI, set up `licence.txt` and the EULA in config [sf-faq].
- **v24 adds Auto Compare Crawls** for scheduled and CLI crawls, and emailed exports [sf-v24].

### Sitebulb
- **Endpoints:** `https://mcp.sitebulb.com/cloud` and `https://mcp.sitebulb.com/desktop`. Remote HTTP, **OAuth only,
  no API key** [sb-connect].
- **Tools:** 15, all read-only (scope `mcp:read`). They cannot start, pause or change crawls [sb-security].
  - They read finished crawls only, and return up to 50 sample URLs per hint. Full lists come from an app export
    [sb-cando].
  - The Desktop endpoint needs the app installed, signed in, running and licensed [sb-faq].
- **Plans:** all Cloud plans and Desktop Pro and Lite, including the trial [sb-faq]. No Claude Code command is
  documented.
- **Tool names** (`project_list`, `project_audit_list`, `audit_hint_category_list`, `audit_hint_list`,
  `audit_url_list`, `audit_report_summary`, `audit_report_seo`, `search`, …) are "examples to recognise, not
  identifiers". Match them at runtime [sb-plugin].
- **No CLI or public API was found** [sb-cli]. That is an [UNVERIFIED] negative.

### Lumar
- **Endpoint:** `https://mcp.lumar.io/mcp`. Needs the paid **MCP Server add-on**, whose price is not public
  [lumar-overview].
- **Auth** [lumar-auth]:
  - OAuth;
  - a user key `Authorization: Bearer <userKeyId>:<secret>`, always read-only;
  - a service-account key `Bearer lmr_sa_<id>_<secret>`.
- **Toolsets:** chosen with `/mcp/x/<list>` or `X-MCP-Toolsets`. Starting crawls needs `analyze:write` [lumar-auth].
  For automation keys, grant `analyze:read` only.
- **Compact surface:** `X-MCP-Surface: compact` exposes `lumar_find`, `lumar_read` and `lumar_act` and saves tokens
  [lumar-surfaces].
- **Crawl credits:** each crawled URL uses credits. Real cost per URL comes from
  `analyze_list_project_custom_metrics` (`costPerUrl`); balances from `lumar_get_account_credits`
  [lumar-crawl-skill].
- **Long jobs:** keep the id, check once later rather than polling, and use report exports for full datasets
  [lumar-usage].

## 5. Free Google and Microsoft sources

| Source | Access and auth | Quotas and limits | Notes |
|---|---|---|---|
| **Search Console API** | No official MCP; Google's lists have none [google-mcp-list] [gcloud-mcp-products]. OAuth (installed/web app) or a **service account added as a property user** by an owner. Scope `webmasters.readonly` [gsc-auth] [gsc-prereqs] | Search Analytics: 1,200 QPM per site and per user, plus load quotas (wait 15 min). URL Inspection: 2,000/day and 600/min per site [gsc-limits] | `rowLimit` ≤ 25,000; ≤ 50K rows per day per search type. Query one day at a time and page `startRow` [gsc-query] [gsc-all-data]. UI export stops at 1,000 rows [gsc-perf-blog] |
| GSC bulk export to BigQuery | An owner sets it up; needs billing | No row cap; no backfill; anonymized queries have no text | Turn it on early for big sites [gsc-bulk] [gsc-bulk-help] |
| GSC community MCP | AminForou/mcp-gsc, `uvx mcp-search-console`, OAuth or service account. `GSC_ALLOW_DESTRUCTIVE` defaults to false | Same as the API | Third-party code holding GSC credentials: audit and pin it [gsc-mcp-amin] |
| GSC Generative AI performance report | UI only; no API `type` value | Impressions only; 1,000-row table | Export with the user present (§7). CSV format [UNVERIFIED] [gsc-genai] |
| **GA4** | Official `googleanalytics/google-analytics-mcp`: `pipx run analytics-mcp`, ADC with `analytics.readonly` [ga4-mcp]. Not bundled in any seo-suite plugin. The user adds it: `claude mcp add analytics-mcp --scope user -e "GOOGLE_APPLICATION_CREDENTIALS=PATH" -e "GOOGLE_PROJECT_ID=ID" -- pipx run analytics-mcp` | Standard property: 200,000 tokens per day, 40,000 per hour, 14,000 per project per hour, 10 concurrent. 360 gets 10× tokens. 120 thresholded requests per hour [ga4-quotas] | 10 tools. 9 read-only: `get_account_summaries`, `get_property_details`, `list_google_ads_links`, `list_property_annotations`, `get_custom_dimensions_and_metrics`, `run_report`, `run_realtime_report`, `run_funnel_report`, `run_conversions_report`. `create_property_annotation` appears only with `--allow-write` + `analytics.edit` [ga4-coordinator]. Send `returnPropertyQuota: true` |
| Google Ads | Official `googleads/google-ads-mcp`: read-only, 3 tools (GAQL `search`, `get_resource_metadata`, `list_accessible_customers`) [ads-mcp] [ads-mcp-doc] | — | **No Keyword Planner** in the MCP [ads-mcp-pr48] |
| Keyword Planner (Ads API) | `KeywordPlanIdeaService` needs **Basic** access (brand verification) or Standard. Explorer blocks Planning services. Developer tokens were sunset 2026-09-09; access is per Cloud project [ads-access] | 1 request/s per customer ID [ads-quotas] | `GenerateKeywordIdeas` ≤ 20 seeds [ads-ideas]. Historical metrics ≤ 10,000 keywords; cache monthly [ads-kp-overview]. Not built in seo-suite |
| PageSpeed Insights v5 | Key optional, recommended for automation: `psi_api_key` in `/plugin configure seo-suite@seo-suite`, which the core SessionStart hook exports as `PSI_API_KEY` for `psi.py` | Quota not stated by Google [UNVERIFIED: 25,000/day] | Google plans to drop CrUX field data from PSI; no date [psi-api] [psi-start] |
| CrUX API / History API | Cloud API key | 150 queries/min per project, free; paying can't raise it | 28-day window, updated daily ~04:00 UTC. History: ≤ 40 weekly points, Mondays [crux-api] [crux-history] |
| Chrome DevTools MCP | `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest` [devtools-clients] | — | Traces plus `lighthouse_audit` (no performance category). `--no-performance-crux`, `--no-usage-statistics`, `--slim` [devtools-mcp] [devtools-mcp-readme] |
| **Bing Webmaster Tools** | No official MCP. Community `zizzfizzix/mcp-server-bwt` (uvx) [bwt-mcp]. API key from Settings → API Access, one per user, or OAuth [bwt-access] | — | JSON endpoint `ssl.bing.com/webmaster/api.svc/json/METHOD?apikey=…`. SOAP/POX were scheduled to retire 2026-08-31 [bwt-protocols]. Methods include GetQueryStats, GetPageStats, GetUrlSubmissionQuota, SubmitUrlBatch [bwt-methods] |
| IndexNow | Key file at the site root | ≤ 10,000 URLs per POST | Level 3 and up only [indexnow] |
| Microsoft Clarity | Official MCP; the project admin creates the token [clarity-mcp] | **10 requests per project per day**, last 1–3 days, 1,000 rows | One fixed daily job; never ad hoc [clarity-api] |
| Google Trends API | Gated alpha | Not published | Don't scrape trends.google.com [trends-api] |
| Indexing API | — | 200 publishes per day | **JobPosting / BroadcastEvent pages only.** Never a general "force indexing" tool [indexing-api] |

- **Google OAuth in "Testing":** apps with External consent screens in Testing get refresh tokens that expire after
  **7 days**. There is a limit of 100 refresh tokens per account per client. Service accounts avoid both
  [google-oauth].
- **Business Profile API:** needs approval (a profile verified 60+ days, 300 QPM after approval) [gbp-prereqs].
  Agencies are managers, never password holders [gbp-policy].

## 6. Other vendors with MCPs (primary sources)

| Vendor | MCP and auth | Cost control |
|---|---|---|
| SE Ranking | `https://api.seranking.com/mcp`, OAuth 2.1 or an `X-Api-Key` header. Keys have full account access [seranking-mcp] | Only 2xx responses cost credits. `DATA_getSubscription` costs 0. Data API 10 RPS. Always ask before `PROJECT_*` writes [seranking-credits] [seranking-skills] |
| Similarweb | `https://mcp.similarweb.com`, `api-key` header. Needs an API-only, Business or Enterprise plan [similarweb-mcp] [similarweb-cursor] | Credits = domains × endpoint price × granularity × countries × history × results [similarweb-credits]. Claude Code header form [UNVERIFIED] |
| Keywords Everywhere | `https://mcp.keywordseverywhere.com/mcp`, Bearer key [ke-mcp] | Volume costs 1 credit per keyword, ≤ 100 per call. `GET /account/credits` returns the balance; 402 means none left [ke-credits] |
| AlsoAsked | No MCP found [UNVERIFIED negative]. REST with `X-Api-Key`, Pro plan [alsoasked-auth] | `fresh=false` repeats are free. Depth 3 costs 4 credits [alsoasked-search] |
| Otterly.AI | `https://data.otterly.ai/mcp`, OAuth only [otterly-mcp] | A per-period tool-call cap. `get_account_info` is free. Write tools are gated |
| Moz | A docs page exists [moz-mcp] | Endpoint, auth and quota [UNVERIFIED] |

## 7. Browser automation rules

| Target | Automate? | Why |
|---|---|---|
| Semrush web app | **No** | ToS §3.3(k), (p), (r) [semrush-tos] |
| Ahrefs web app | **No** | ToS §4.4(i)/(j), and a Cloudflare challenge [ahrefs-tos] [ahrefs-cf] |
| Similarweb platform | **No** | Restrictions (v): no automated means "for any purpose" [similarweb-tos] |
| Google Search results (rank checks) | **No** | Automated queries break the spam policies and ToS [google-spam] [google-tos] |
| business.google.com manager pages | **No** | robots.txt disallows them; Google's ToS bans automated access against robots.txt [gbp-robots] [google-tos] |
| Your own Search Console / Bing Webmaster UI | Yes, light use with the user present | No robots disallow found. Prefer the free APIs, which return more rows [browser-research-gsc] |
| QA of your own site | Yes | Rendered DOM, traces, screenshots |

- **Claude in Chrome needs a `/login` claude.ai session.** API-key and setup-token sessions keep it off, so it never
  runs in scheduled or API-key jobs [cc-chrome].
- **What Claude in Chrome does:**
  - it shares the browser's existing logins;
  - it pauses for the user at login pages and CAPTCHAs [cc-chrome];
  - account creation and CAPTCHA bypass are prohibited in every mode;
  - downloads need approval even on always-allowed sites [chrome-perms].
- **A project or plugin cannot turn Chrome on** [cc-chrome].
- **Prompt injection** is the main browser risk. Use a separate profile and an allowlist, and stop if the agent wanders
  [chrome-safety].
- **Playwright MCP origin lists are not a security boundary** [playwright-mcp].

## 8. The credit guard

`${CLAUDE_PLUGIN_ROOT}/scripts/credit_guard.py` in the core `seo-suite` plugin is the source of truth. This section
describes what it does. If the two disagree, fix one of them.

**Where it runs:**
- **Wiring:** the core plugin's `hooks/hooks.json` runs `credit_guard.py <pre|post|post-failure|batch>` on PreToolUse,
  PostToolUse, PostToolUseFailure and PostToolBatch, in exec form with the hook's JSON on stdin.
- **Every call is seen:** PreToolUse hooks run before every tool call, whether or not it needs permission, in every
  permission mode [cc-hooks] [cc-permissions]. Plugin hooks also fire inside subagents, with `agent_id`; plugin-agent
  frontmatter hooks are ignored [cc-hooks] [cc-plugin-components].
- **Failing closed:**
  - `pre` fails closed on its own. Any internal error, such as an invalid option or unreadable state, exits 2, and exit 2
    always blocks [cc-hooks].
  - A timeout or a script that can't start still lets the call through, unless `hooks/hooks.json` sets
    `onFailure: "block"` (Claude Code v2.1.295+) [cc-hooks].
- **No guard at all** in these cases:
  - `claude -p --bare` skips hooks, installed plugins and MCP servers [cc-headless];
  - cloud sessions install no plugins, not even ones a repo's settings enable [cc-cloud-env].
- **Unattended defaults:** since v2.1.302, a `-p` run with no permission mode set starts in Manual, which denies any
  call that needs approval [cc-headless].

**State:**
- **Ledger:** `${CLAUDE_PLUGIN_DATA}/credit-guard/ledger.jsonl`, written under a lock, because hooks for parallel calls
  run concurrently [cc-hooks].
- **Cache:** `${CLAUDE_PLUGIN_DATA}/credit-guard/cache/<vendor>/<sha256>.json` (vendor, tool, call, data type,
  fetched_at, input, response).
- **Deferred calls:** `${CLAUDE_PLUGIN_DATA}/credit-guard/requests.jsonl`, one line per call: ts, session_id, agent_id,
  vendor, bucket, tool, call, input_summary, estimate, currency, price_known, threshold, reason, request_key.
- **Without `CLAUDE_PLUGIN_DATA`** (a skills-dir copy): `~/.claude/plugins/data/seo-suite/credit-guard/`.
- **Never write state** to `${CLAUDE_PLUGIN_ROOT}`, which changes on every update [cc-plugin-ref].

**Options** are core-plugin userConfig, read as `CLAUDE_PLUGIN_OPTION_<KEY>` [cc-plugin-ref]:

| Option | Default | Meaning |
|---|---|---|
| `autonomy_level` | 1 | `autonomy.md` levels 1–4 |
| `audit_profile` | auto | The audit profile when the request names none: `auto`, `quick`, `full-free` or `paid` (`references/profiles.md`). Read by `scripts/audit_profile.py`, not by the guard |
| `semrush_monthly_units`, `ahrefs_monthly_units` | 0 | Monthly budget in vendor units. 0 = that vendor's paid calls are denied |
| `dataforseo_monthly_usd` | 0 | Monthly DataForSEO budget in USD |
| `other_monthly_usd` | 0 | One USD budget shared by Similarweb, SE Ranking, Keywords Everywhere, AlsoAsked, Otterly and Lumar crawls, and `ai_probe.py`'s OpenAI, Perplexity and Anthropic calls |
| `per_run_cap_pct` | 25 | Share of the vendor's monthly budget one run (session) may spend |
| `ask_above_pct` | 5 | A call estimated above this share of the monthly budget is deferred: denied and recorded in `credit-guard/requests.jsonl` for the end-of-run questions. 0 = defer every paid call |
| `max_rows` | 50 | Row limit the guard clamps or adds |
| `cache_ttl_days` | per data type | One TTL for every data type when set |
| `psi_api_key` (sensitive) | unset | Exported as `PSI_API_KEY` by the core SessionStart hook; not used by the guard |
| `openai_api_key`, `perplexity_api_key`, `anthropic_api_key` (sensitive) | unset | Exported as `SEO_SUITE_OPENAI_API_KEY`, `SEO_SUITE_PERPLEXITY_API_KEY` and `SEO_SUITE_ANTHROPIC_API_KEY` for `ai_probe.py`. The prefix keeps other tools in Bash on their own keys, and the Claude Code CLI never takes the Anthropic key as `ANTHROPIC_API_KEY` |

Hooks get these variables, but commands Claude runs through Bash don't [cc-plugin-ref]. So the core SessionStart hook
also exports `audit_profile`, the four monthly budgets, `per_run_cap_pct` and `max_rows` to Bash under their
`CLAUDE_PLUGIN_OPTION_` names, the hooks' `CLAUDE_PLUGIN_DATA` as `SEO_SUITE_DATA`, and the session id from its input
as `SEO_SUITE_SESSION_ID`. `audit_profile.py`, `rank_snapshot.py` and `ai_probe.py` then read the same options, ledger
and run as the hooks. An option changed mid-session reaches Bash at the next session.

### Scripts that pay a vendor directly

The hook never sees `rank_snapshot.py run` (DataForSEO REST) or `ai_probe.py run` (OpenAI, Perplexity and Anthropic
APIs). They use the guard's own helper, `script_check`, `script_reserve` and `script_settle` in `credit_guard.py`:
- **Before the first call,** the whole run's estimate is checked against the bucket's monthly budget and per-run cap.
  A budget of 0 stops the script before anything is sent.
- **Before each batch** (all of a snapshot's `task_post` calls; one prompt's runs per engine), the batch's estimate is
  reserved in `ledger.jsonl` under the session id, so hook calls and script calls share one per-run cap.
- **After each batch** it is settled: DataForSEO's `cost` field, Perplexity's `usage.cost.total_cost`, or the reported
  tokens and search calls at the script's price table (marked estimated). A failed call keeps its estimate, in case
  it was charged.
- **At either limit** the script stops and says which one; the run lists it in the end-of-run questions.
- **Prices:** `rank_snapshot.py` prices tasks with the guard's own DataForSEO table. `ai_probe.py` has a table checked
  2026-10-24: OpenAI web search $10 per 1,000 calls plus tokens (`gpt-5-mini` $0.25 / $2 per 1M), Perplexity
  `web_search` $2.50 per 1,000 plus tokens (a preset priced as `perplexity/sonar`, $0.25 / $2.50), Anthropic web search
  $10 per 1,000 plus tokens (`claude-haiku-5-5` $0.10 / $0.50). A model with no price stops the script
  [openai-pricing] [pplx-pricing] [anthropic-pricing].
- **Not covered:** the per-call threshold (`ask_above_pct`), which defers single MCP calls. A script's batches are
  bounded by the per-run cap instead.

### Which tools it guards

The guard reads the server name: `mcp_server.name` from the hook input (v2.1.274+) when present, else the tool-name
prefix [cc-hooks]. The vendor whose pattern matches is the one guarded, so every name form below is covered:

| How the server was added | Tool name | Source |
|---|---|---|
| Vendor plugin | `mcp__plugin_seo-suite-<vendor>_<server>__<tool>`, e.g. `mcp__plugin_seo-suite-semrush_semrush__execute_report` | [cc-mcp] |
| User ran `claude mcp add` (vendor docs) | `mcp__<name>__<tool>`, e.g. `mcp__semrush__…`, `mcp__semrush-key__…`, `mcp__ahrefs__…`, `mcp__dfs-mcp__…` (the name DataForSEO's guide uses [dfs-help-cc]). The plugin copy of the same URL is then dropped as a duplicate | [cc-mcp] |
| claude.ai connector | `mcp__claude_ai_<Server>__<tool>`. The exact normalisation is [UNVERIFIED]; copy the name from `/mcp` | [cc-permissions] |
| Desktop-app local session connectors | In-process `sdk` servers, possibly named by id. The guard can only match them if the name carries the vendor | [cc-permissions] |

- **Recognised vendors:** Semrush, Ahrefs, DataForSEO (`dataforseo` or `dfs`), Similarweb, SE Ranking, Keywords
  Everywhere, AlsoAsked, Otterly and Lumar.
- **No per-call charge** (always no opinion): Screaming Frog and Sitebulb, which are licensed local or read-only
  tools.
- **Not vendors:** GA4 (`mcp__analytics-mcp__*`), GSC community servers and Bing are free, so the guard ignores them.
- **Name the server after the vendor** when adding it by hand. A name the guard can't map to a vendor is not guarded.

### PreToolUse decisions (in this order)
1. **Not a recognised vendor, or a free tool or path → no opinion.** The user's permission rules decide. Free means:
   - Semrush: the 12 discovery tools and `get_report_schema` (expected free; [UNVERIFIED], see §1);
   - Ahrefs: `rank-tracker-*`, `management-*`, `subscription-info*`, `web-analytics-*`, `social-media-*`, `public-*`,
     `gsc-*` except `gsc-anonymous-queries`, plus `doc`, `site-audit-projects` and `keywords-explorer-service-notices`;
   - DataForSEO: `docs_index`, `docs_list_sections`, `docs_search`, and `api_request` to `appendix/user_data`,
     `tasks_ready` or `task_get`;
   - Lumar: everything except `analyze_run_crawl`, `analyze_resume_crawl`, `analyze_create_single_page_request` and
     `lumar_act`.
2. **Semrush `execute_report` with no row limit → deny.** This applies to per-line reports and reports with no price
   entry. The reason tells Claude to read `get_report_schema` and pass `display_limit` or `limit` ≤ `max_rows`. This
   is the 10,000-row trap (§1).
3. **Clamp row limits to `max_rows`** (the result is sent as `updatedInput`, every other field unchanged [cc-hooks]):
   - Semrush `display_limit` / `limit`;
   - Ahrefs `limit`, added when missing on list endpoints (default 1,000 rows);
   - DataForSEO `limit`, `depth` and `max_crawl_pages`, added when missing on list and crawl endpoints.
4. **Cache hit** (same vendor, tool and input inside the TTL) → **deny**. The reason names the cached file, which Claude
   reads at zero cost. Deleting the file forces a fresh call.
5. **Monthly budget is 0 → deny.**
6. **Estimate the cost** from the static price tables in §1–3:
   - Semrush: lines × price, or the per-request price; history ×5;
   - Ahrefs: max(50, rows × field costs), with fixed prices for Site Audit and Content Helper;
   - DataForSEO: per task, plus per item, row, page or 10 SERP results. Only the first task of a Live call is billed.

   A call with no price entry is budgeted at the `ask_above_pct` threshold.
7. **Month-to-date + estimate > monthly budget → deny**, with the remaining amount. Month-to-date includes in-flight
   reservations: every allowed call reserves its estimate, held for 30 minutes until PostToolUse settles it.
8. **This run's spend + estimate > `per_run_cap_pct` of the monthly budget → deny.**
9. **Defer** (deny and record, never ask mid-run) when any of these hold:
   - the estimate is above `ask_above_pct` of the monthly budget;
   - `ask_above_pct` is 0;
   - it is a Semrush call with no price entry, for example Site Audit snapshot info (10,000 units).

   The guard appends one line per deferred call to `credit-guard/requests.jsonl` (deduplicated per session) and tells
   Claude to continue with free sources. Claude lists the deferred calls, with estimates, in the end-of-run questions
   (`references/autonomy.md`). The user approves by raising `ask_above_pct` or the budget for the next run.
10. **Otherwise allow,** with the budget status as the reason.

**Precedence and limits:**
- Among hooks, precedence is deny > defer > ask > allow.
- A hook's allow never overrides deny or ask *rules*, and exit 2 always blocks [cc-hooks] [cc-permissions].
- Settings-file rules can't see MCP parameters (rules with parentheses are skipped), which is why the per-call logic
  lives in the hook [cc-permissions].

### PostToolUse, PostToolUseFailure and PostToolBatch
- **PostToolUse** settles the reservation with the actual cost where the response shows it:
  - DataForSEO's `cost` field;
  - 0 for a Semrush `ERROR … ::` response, since requests that return no data cost nothing [semrush-units];
  - otherwise the estimate.

  It caches the raw response, except error responses (Semrush `ERROR`, DataForSEO status ≥ 40000). It returns a
  one-line budget status and the cache path as `additionalContext`.
- **PostToolUseFailure** keeps the estimate in the ledger, in case the vendor charged it. It tells Claude to read the
  error and not repeat the same call unchanged.
- **PostToolBatch is the circuit breaker.** When this batch's paid calls pushed a vendor past its monthly budget or
  per-run cap, it returns `decision: "block"`, which stops the loop before the next model call [cc-hooks].
- **Other hook options the guard doesn't use:** `updatedToolOutput` could replace a bulky MCP result with a summary
  (MCP output isn't schema-validated) [cc-hooks]. That would save context, not credits, because the call has already
  run.

### Cache TTLs

**The guard's defaults by data type** (`cache_ttl_days` replaces all of them):

| Data type | Default | Basis |
|---|---|---|
| Keywords (volume, CPC, difficulty) | 30 days | Google Ads and DataForSEO monthly, mid-month [dfs-freshness]; Ahrefs at least monthly [ahrefs-ke-freq]; Semrush KMT monthly [semrush-kmt-date] |
| SERP, positions, domain snapshots | 7 days | SERPs refresh from days to weeks by popularity [ahrefs-ke-freq] [dfs-freshness]; Ahrefs Rank Tracker weekly [ahrefs-rt-freq] |
| Backlinks | 7 days (deltas run weekly) | Indexes update continuously; full cycles ≤ 90 days [ahrefs-links-freq] [dfs-freshness] |
| Audit data (Site Audit, Lumar) | 1 day | Per crawl |
| AI visibility (Brand Radar, LLM Mentions) | 30 days | Chatbot indexes monthly, LLM Mentions 60-day cycle [ahrefs-brand-radar] [dfs-freshness] |
| Anything else | 7 days | — |
| **Anything from Semrush** | **Never more than 30 days**, whatever the setting | ToS: no caching beyond one month [semrush-tos] |

**Finer TTLs the pipelines apply** when they store their own snapshots in `seo-work/` (from vendor cadences):
- long-tail keyword difficulty: 30 days;
- daily rank tier: 1 day (Semrush Position Tracking updates daily [semrush-pt-kb]);
- AI Overviews: 3–7 days [ahrefs-brand-radar];
- CrUX: 7 days (28-day rolling window [crux-api]);
- GSC: kept for good, re-pulling only the last ~3 days (2–3 day lag; don't re-query final data [gsc-all-data]
  [gsc-limits]).

### What the guard cannot do
- **Refund.** PostToolUse runs after the paid call. Prevention happens only in PreToolUse [cc-hooks].
- **Survive being switched off.** `disableAllHooks`, a `--settings` override or managed `allowManagedHooksOnly` disables
  it, so it is a safety net, not a tamper-proof control. Vendor-side caps are the backstop: the Ahrefs key cap, the
  DataForSEO daily limit, and the Semrush included-units ceiling.
- **Know the true balance** without a vendor balance call. It estimates from static tables, so prices drift.
- **See every large payload for certain.** MCP output warns above 10,000 tokens and is capped at 25,000 by default. Text
  over 50,000 characters is saved to a file, so read that file instead of re-calling [cc-mcp]. Whether PostToolUse
  sees the full payload past those limits is [UNVERIFIED].
- **Guard a server whose name doesn't name the vendor,** or any run under `--bare` or in the cloud.

## 9. Credit plan per pipeline (one site, 3 competitors, October 2026 prices)

| Pipeline | Cadence | Paid step and call shape | Per run | Per month | Sources |
|---|---|---|---|---|---|
| B1 Full audit | Quarterly | None on `full-free`, the default audit profile at every size (references/profiles.md). Paid crawlers follow the profile's lists: Screaming Frog CLI is Main on `paid-big` ($0 per crawl with a licence) and Reserve elsewhere; DataForSEO On-Page with `max_crawl_pages` is a Cross-check on `paid-small` and `paid-big`, within budgets | $0. On-Page 5,000 pages: $0.75 / JS $7.50 / browser $25.50. Semrush SA read path ≈ 400 + 100 per non-zero issue | ≈ $0 | [dfs-onpage-price] [semrush-sa] [sf-pricing] |
| B2 Weekly technical monitor | Weekly | Ahrefs `site-audit/projects` (free), then `issues` with `date_compared` only if "new" > 0 (interactive only) | $0; Ahrefs ≤ 50 units | $0 | [ahrefs-sa-issues] |
| B3 Keyword research | Quarterly or on demand | Shortlist of 300: DataForSEO `search_volume` Standard (1 task) + Labs `bulk_keyword_difficulty`. SERPs for the top 20. No Keyword Planner: Labs `keyword_ideas` with `limit` 1,000 | $0.06 + $0.048 + $0.012 ≈ $0.12 (+$0.132 for ideas). Semrush 3,000 units. Ahrefs 6,300 units | ≈ $0.04 averaged | [dfs-ads-price] [dfs-labs-price] [dfs-keyword-ideas] [semrush-keyword] [ahrefs-ke-ref] |
| B4 Competitor gap | Monthly | DataForSEO `domain_intersection` (`intersections=false`, `limit` 100, volume filter) per competitor | 3 × $0.024 = $0.072. Ahrefs 3 × 2,200 units. Semrush 3 × 1,000 units | $0.07 | [dfs-intersection] [ahrefs-ok-ref] [semrush-domain] |
| B5 Backlink deltas | Weekly | `timeseries_new_lost_summary` (`group_range=week`). Only when non-zero: `backlinks/backlinks/live` (`one_per_domain`, `first_seen > last run`, `limit` 100) for new and for lost | ≤ $0.08 per domain; 4 domains ≤ $0.32 | ≤ $1.39 | [dfs-timeseries] [dfs-backlinks-live] [dfs-bl-price] |
| B6 Rank tracking | Daily / weekly | `rank_snapshot.py`, SERP Standard: 50 money keywords daily at depth 10, 450 weekly at depth 20, up to 100 tasks a POST, free `tasks_ready` and `task_get/advanced`. GSC (`rank_snapshot.py gsc`) and Ahrefs Rank Tracker reads are free | $0.03 per day; $0.54 per week, per market and language | ≈ $3.22 (+$0.90 with AI Overview on the money tier) | [dfs-serp-price] [ahrefs-openapi] |
| B7 GSC content refresh | Monthly | SERP Standard for the flagged pages' top queries (~20) | $0.012 (AIO $0.024) | ≈ $0.02 | [dfs-serp-price] [gsc-all-data] |
| B8 AI visibility | Monthly | `ai_probe.py` through the official APIs: 40 prompts × 2 engines (OpenAI main, Perplexity cross-check) × 3 runs = 240 probes, at about 10,000 tokens in and 1,000 out each [estimate]. From `other_monthly_usd`, not DataForSEO. LLM Scraper is out: it drives chatgpt.com and gemini.google.com | ≈ $2.60 (OpenAI `gpt-5-mini` ≈ $0.0145 a probe, Perplexity `fast` preset ≈ $0.0075); Claude `claude-haiku-5-5` adds ≈ $1.40 | ≈ $2.60 | [openai-pricing] [pplx-pricing] |
| B9 Multilingual blog QA | Weekly or per PR | Optional SERP check per target keyword per locale | $0.0006 per keyword-locale (10 posts × 3 locales ≈ $0.018) | ≈ $0.08 | [dfs-serp-price] |
| B10 Blog batch | Weekly | SERP Standard only for the topics whose snapshot is stale (`next-topics --limit 12` per locale). Volumes for the shortlisted head terms only when they are missing or stale: `search_volume` Standard as in B3, one task per locale | $0.0006 per keyword-locale (12 topics × 3 locales ≈ $0.022). Volumes $0.06 per task | ≈ $0.09 (+$0.06 per locale whose volumes are refreshed, at most monthly) | [dfs-serp-price] [dfs-ads-price] |
| **Total scheduled (DataForSEO)** | | | | **≈ $4.9 a month** (≈ $5.8 with AI Overview on the money tier); budget $10 | |
| **Total scheduled (`other_monthly_usd`)** | | | | **≈ $2.60 a month** for B8; budget $12, so one run stays under the $3 per-run cap | |

**Semrush and Ahrefs** fit interactive, targeted work: competitor keyword sets, link-index lookups and Semrush-only
metrics. Keep them ≤ 40% of the included allowance, so other skills still have room.

**Do not run on these vendors as pipelines:**
- Semrush Position Tracking positions: 100 units per keyword.
- Semrush backlink delta pulls: 4,000 units per 100 lines.
- Any Site Audit snapshot info.

## [UNVERIFIED] — do not state as fact; settle at runtime or with the vendor

- **Semrush:**
  - whether discovery tools and `get_report_schema` cost units;
  - `execute_report` field names;
  - whether the MCP applies its own default row limit;
  - whether `countapiunits` shows the MCP allowance, and whether the Query log includes MCP calls;
  - monthly vs renewal refresh for annual plans;
  - the v4 Projects API price;
  - no Kd surcharge on `phrase_these` (documented, not metered);
  - whether user-supplied exports are allowed under §3.3(r);
  - whether private AI Visibility or Content Toolkit APIs exist.
- **Ahrefs:**
  - the hosted MCP's tool names, the `doc` helper, the tool count and the `apiUsageCosts` object;
  - behaviour when `limit` exceeds the plan's row cap;
  - the cache TTL;
  - whether scheduled `claude -p` counts as a "custom script";
  - whether a Free-account key can call 0-unit endpoints;
  - Batch Analysis API on Lite (not live-tested);
  - how to get daily Rank Tracker updates;
  - the Content Helper 400 wording;
  - the `refdomains_source` cost (1 vs 5; read the header).
- **DataForSEO:**
  - `task_post` on `.ai` paths;
  - the hosted MCP with an IP whitelist;
  - whether several search operators stack;
  - any monthly minimum for Backlinks (none on the pricing pages).
- **Screaming Frog:** whether the CLI or `--headless` needs a licence; the default MCP port; whether scheduling needs a
  licence.
- **Sitebulb:** absence of a CLI or API; rate-limit numbers; a Claude Code command.
- **Lumar:** the add-on price; a stdio package.
- **Google and Microsoft:**
  - the PSI daily quota;
  - getting more than 50K GSC rows per day by splitting filters;
  - errors when adding GSC service accounts;
  - CSV as the Generative AI report's export format;
  - no API for the Bing AI Performance report;
  - the Bing URL-submission quota, and whether existing keys still work after the SOAP retirement.
- **Claude Code:**
  - claude.ai connector name normalisation;
  - whether PostToolUse's `tool_response` holds the full payload above 25k tokens or 50k characters;
  - whether a hook "allow" is honoured in `dontAsk` (scheduled runs list tools in `--allowedTools` instead);
  - Keychain access from cron on macOS;
  - whether `MAX_MCP_OUTPUT_TOKENS` works in project settings.
- **Other vendors:** Similarweb's Claude Code header form; Keywords Everywhere's MCP tool names; Moz's MCP details; that
  AlsoAsked has no MCP.

## Sources

Each bracketed label in the text links to the URL defined below. The definitions are visible in the raw file.

[semrush-mcp]: https://developer.semrush.com/api/basics/semrush-mcp/
[semrush-kb-mcp]: https://www.semrush.com/kb/1618-mcp
[semrush-mcp-faq]: https://www.semrush.com/mcp/
[semrush-kb-api]: https://www.semrush.com/kb/5-api
[semrush-skills]: https://github.com/semrush/skills
[semrush-kw-skill]: https://github.com/semrush/skills/blob/main/keyword-research/SKILL.md
[semrush-backlink-skill]: https://github.com/semrush/skills/blob/main/backlink-audit/SKILL.md
[semrush-prompts]: https://www.semrush.com/mcp/prompt-library?view=prompts
[semrush-llms]: https://developer.semrush.com/api/llms.txt
[semrush-units]: https://developer.semrush.com/api/v3/get-started/api-units-balance/
[semrush-keyword]: https://developer.semrush.com/api/v3/seo/keyword-reports/
[semrush-domain]: https://developer.semrush.com/api/v3/seo/domain-reports/
[semrush-overview]: https://developer.semrush.com/api/v3/seo/overview-reports/
[semrush-backlinks]: https://developer.semrush.com/api/v3/seo/backlinks/
[semrush-v4-backlinks]: https://developer.semrush.com/api/v4/seo/backlinks/
[semrush-v4-keywords]: https://developer.semrush.com/api/v4/seo/keyword-reports/
[semrush-projects]: https://developer.semrush.com/api/v3/projects/projects/
[semrush-projects-overview]: https://developer.semrush.com/api/v3/projects/overview/
[semrush-pt]: https://developer.semrush.com/api/v3/projects/position-tracking/
[semrush-sa]: https://developer.semrush.com/api/v3/projects/site-audit/
[semrush-limits]: https://developer.semrush.com/api/v3/introduction/api-usage-restrictions/
[semrush-trends-access]: https://developer.semrush.com/api/v3/get-started/api-access/
[semrush-tos]: https://www.semrush.com/company/legal/terms-of-service/
[semrush-ksb]: https://www.semrush.com/kb/1058-keyword-strategy-builder
[semrush-swa]: https://www.semrush.com/kb/814-seo-writing-assistant
[semrush-tr]: https://www.semrush.com/kb/776-topic-research
[semrush-kmt-date]: https://www.semrush.com/kb/1138-date-range-in-kmt
[semrush-pt-kb]: https://www.semrush.com/kb/326-how-often-does-the-position-tracking-update-its-data
[ahrefs-mcp-intro]: https://docs.ahrefs.com/mcp/docs/introduction.md
[ahrefs-mcp-cc]: https://docs.ahrefs.com/mcp/docs/claude-code.md
[ahrefs-mcp-openclaw]: https://docs.ahrefs.com/mcp/docs/openclaw.md
[ahrefs-mcp-help]: https://help.ahrefs.com/en/articles/13913559-getting-started-with-ahrefs-mcp
[ahrefs-tool-cats]: https://docs.ahrefs.com/mcp/docs/tool-categories.md
[ahrefs-repo]: https://github.com/ahrefs/ahrefs-mcp-server/blob/main/src/server.ts
[ahrefs-api-help]: https://help.ahrefs.com/en/articles/6559232-about-api-v3
[ahrefs-api-intro]: https://docs.ahrefs.com/api/docs/introduction.md
[ahrefs-limits]: https://docs.ahrefs.com/api/docs/limits-consumption.md
[ahrefs-free-test]: https://docs.ahrefs.com/api/docs/free-test-queries.md
[ahrefs-keys]: https://docs.ahrefs.com/api/docs/api-keys-creation-and-management.md
[ahrefs-openapi]: https://docs.ahrefs.com/openapi.json
[ahrefs-llms]: https://docs.ahrefs.com/llms.txt
[ahrefs-changelog]: https://docs.ahrefs.com/api/docs/changelog.md
[ahrefs-pricing]: https://ahrefs.com/pricing
[ahrefs-batch-help]: https://help.ahrefs.com/en/articles/10835759-efficient-ways-to-handle-repetitive-tasks-in-ahrefs
[ahrefs-rt-freq]: https://help.ahrefs.com/en/articles/604245-how-frequently-do-my-tracked-keywords-get-updated
[ahrefs-rt-serp]: https://docs.ahrefs.com/api/reference/rank-tracker/get-serp-overview
[ahrefs-sa-issues]: https://docs.ahrefs.com/en/api/reference/site-audit/get-issues
[ahrefs-ok-ref]: https://docs.ahrefs.com/api/reference/site-explorer/get-organic-keywords
[ahrefs-ke-ref]: https://docs.ahrefs.com/api/reference/keywords-explorer/get-overview
[ahrefs-ke-freq]: https://help.ahrefs.com/en/articles/1077603-how-often-is-the-data-in-keywords-explorer-and-site-explorer-updated
[ahrefs-links-freq]: https://help.ahrefs.com/en/articles/78052-how-often-is-ahrefs-links-database-updated
[ahrefs-brand-radar]: https://help.ahrefs.com/en/articles/11064852-what-is-brand-radar-and-how-to-use-it
[ahrefs-tos]: https://ahrefs.com/legal/terms
[ahrefs-faq]: https://ahrefs.com/faq
[ahrefs-free]: https://ahrefs.com/free
[ahrefs-cf]: https://app.ahrefs.com/robots.txt
[dfs-repo]: https://github.com/dataforseo/mcp-server-typescript
[dfs-npm]: https://registry.npmjs.org/dataforseo-mcp-server
[dfs-api-tool]: https://github.com/dataforseo/mcp-server-typescript/blob/master/src/core/tools/api-request-tool.ts
[dfs-field-config]: https://github.com/dataforseo/mcp-server-typescript/blob/master/src/core/config/field-configuration.ts
[dfs-live-mw]: https://github.com/dataforseo/mcp-server-typescript/blob/master/src/core/middleware/api-request/live-endpoint-api-request-middleware.ts
[dfs-ai]: https://docs.dataforseo.com/v3/appendix/ai_optimized_response/
[dfs-help-cc]: https://dataforseo.com/help-center/3-ways-to-install-dataforseo-mcp-with-claude-code
[dfs-serp-price]: https://dataforseo.com/pricing/google-serp/google-organic-serp-api
[dfs-ads-price]: https://dataforseo.com/pricing/keywords-data/google-ads
[dfs-ads-post]: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/task_post.md
[dfs-tasks-ready]: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/tasks_ready.md
[dfs-serp-post]: https://docs.dataforseo.com/v3/serp/google/organic/task_post.md
[dfs-retention]: https://dataforseo.com/help-center/how-long-do-you-keep-results
[dfs-labs-price]: https://dataforseo.com/pricing/dataforseo-labs/dataforseo-google-api
[dfs-labs-vs-ads]: https://dataforseo.com/help-center/dataforseo-labs-api-vs-google-ads-api
[dfs-keyword-ideas]: https://docs.dataforseo.com/v3/dataforseo_labs-google-keyword_ideas-live/
[dfs-intersection]: https://docs.dataforseo.com/v3/dataforseo_labs-google-domain_intersection-live/
[dfs-bl-price]: https://dataforseo.com/pricing/backlinks/backlinks
[dfs-timeseries]: https://docs.dataforseo.com/v3/backlinks-timeseries_new_lost_summary-live/
[dfs-backlinks-live]: https://docs.dataforseo.com/v3/backlinks-backlinks-live/
[dfs-onpage-price]: https://dataforseo.com/pricing/on-page/onpage-api
[dfs-llm-mentions]: https://dataforseo.com/pricing/ai-optimization/llm-mentions
[dfs-llm-responses]: https://dataforseo.com/pricing/ai-optimization/llm-responses
[openai-pricing]: https://developers.openai.com/api/docs/pricing
[pplx-pricing]: https://docs.perplexity.ai/docs/getting-started/pricing.md
[anthropic-pricing]: https://platform.claude.com/docs/en/about-claude/pricing
[dfs-autocomplete]: https://dataforseo.com/pricing/google-serp/google-autocomplete-serp-api
[dfs-pricing]: https://dataforseo.com/pricing
[dfs-sandbox]: https://docs.dataforseo.com/v3/appendix/sandbox.md
[dfs-user-data]: https://docs.dataforseo.com/v3/appendix/user_data/
[dfs-rates]: https://dataforseo.com/help-center/rate-limits-and-request-limits
[dfs-limit]: https://dataforseo.com/help-center/limit-my-payments
[dfs-ip]: https://dataforseo.com/help-center/whitelist-ips
[dfs-freshness]: https://dataforseo.com/help-center/how-often-is-dataforseo-api-data-updated
[sf-mcp]: https://www.screamingfrog.co.uk/guides/mcp-server/
[sf-guide]: https://www.screamingfrog.co.uk/seo-spider/user-guide/general/
[sf-faq]: https://www.screamingfrog.co.uk/seo-spider/faq/
[sf-pricing]: https://www.screamingfrog.co.uk/seo-spider/pricing/
[sf-v24]: https://www.screamingfrog.co.uk/blog/seo-spider-24/
[sb-connect]: https://support.sitebulb.com/en/articles/15984107-connect-any-mcp-client-to-sitebulb
[sb-security]: https://support.sitebulb.com/en/articles/15984092-sitebulb-mcp-security-and-privacy-overview
[sb-cando]: https://support.sitebulb.com/en/articles/15957255-what-the-sitebulb-mcp-can-and-can-t-do
[sb-faq]: https://support.sitebulb.com/en/articles/15984102-sitebulb-mcp-troubleshooting-and-faq
[sb-plugin]: https://github.com/sitebulb/sitebulb-plugin
[sb-cli]: https://features.sitebulb.com/suggestions/52576/cli-access
[lumar-overview]: https://api-docs.lumar.io/docs/lumar-mcp/overview/
[lumar-auth]: https://api-docs.lumar.io/docs/lumar-mcp/authentication-and-toolsets/
[lumar-surfaces]: https://api-docs.lumar.io/docs/lumar-mcp/tool-surfaces/
[lumar-usage]: https://api-docs.lumar.io/docs/lumar-mcp/usage/
[lumar-crawl-skill]: https://github.com/deepcrawl/lumar-plugins/blob/main/plugins/lumar-analytics/skills/analyze-run-crawl/SKILL.md
[google-mcp-list]: https://github.com/google/mcp
[gcloud-mcp-products]: https://docs.cloud.google.com/mcp/supported-products
[gsc-limits]: https://developers.google.com/webmaster-tools/limits
[gsc-query]: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
[gsc-all-data]: https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data
[gsc-auth]: https://developers.google.com/webmaster-tools/v1/how-tos/authorizing
[gsc-prereqs]: https://developers.google.com/webmaster-tools/v1/prereqs
[gsc-bulk]: https://developers.google.com/search/blog/2023/02/bulk-data-export
[gsc-bulk-help]: https://support.google.com/webmasters/answer/12917675
[gsc-mcp-amin]: https://github.com/AminForou/mcp-gsc
[gsc-perf-blog]: https://developers.google.com/search/blog/2022/10/performance-data-deep-dive
[gsc-genai]: https://support.google.com/webmasters/answer/16984139?hl=en
[ga4-mcp]: https://github.com/googleanalytics/google-analytics-mcp
[ga4-coordinator]: https://github.com/googleanalytics/google-analytics-mcp/blob/main/analytics_mcp/coordinator.py
[ga4-quotas]: https://developers.google.com/analytics/devguides/reporting/data/v1/quotas
[ads-mcp]: https://github.com/googleads/google-ads-mcp
[ads-mcp-doc]: https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server
[ads-mcp-pr48]: https://github.com/googleads/google-ads-mcp/pull/48
[ads-access]: https://developers.google.com/google-ads/api/docs/api-policy/access-levels
[ads-quotas]: https://developers.google.com/google-ads/api/docs/best-practices/quotas
[ads-ideas]: https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas
[ads-kp-overview]: https://developers.google.com/google-ads/api/docs/keyword-planning/overview
[psi-api]: https://developers.google.com/speed/docs/insights/rest/v5/pagespeedapi/runpagespeed
[psi-start]: https://developers.google.com/speed/docs/insights/v5/get-started
[crux-api]: https://developer.chrome.com/docs/crux/api
[crux-history]: https://developer.chrome.com/docs/crux/history-api
[devtools-mcp]: https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md
[devtools-mcp-readme]: https://github.com/ChromeDevTools/chrome-devtools-mcp
[devtools-clients]: https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/client-configurations.md
[bwt-mcp]: https://github.com/zizzfizzix/mcp-server-bwt
[bwt-access]: https://learn.microsoft.com/en-us/bingwebmaster/getting-access
[bwt-protocols]: https://learn.microsoft.com/en-us/bingwebmaster/api-protocols
[bwt-methods]: https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi?view=bing-webmaster-dotnet
[indexnow]: https://www.indexnow.org/documentation
[clarity-mcp]: https://github.com/microsoft/clarity-mcp-server
[clarity-api]: https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-data-export-api
[trends-api]: https://developers.google.com/search/blog/2025/07/trends-api
[indexing-api]: https://developers.google.com/search/apis/indexing-api/v3/quickstart
[google-oauth]: https://developers.google.com/identity/protocols/oauth2
[gbp-prereqs]: https://developers.google.com/my-business/content/prereqs
[gbp-policy]: https://support.google.com/business/answer/7353941?hl=en
[gbp-robots]: https://business.google.com/robots.txt
[google-tos]: https://policies.google.com/terms?hl=en-US
[google-spam]: https://developers.google.com/search/docs/essentials/spam-policies
[browser-research-gsc]: https://search.google.com/robots.txt
[similarweb-tos]: https://www.similarweb.com/corp/legal/terms/
[similarweb-mcp]: https://developers.similarweb.com/docs/similarweb-mcp
[similarweb-cursor]: https://developers.similarweb.com/docs/cursor-mcp-integration
[similarweb-credits]: https://developers.similarweb.com/docs/data-credits-unpublished-whats-new-in-v40
[seranking-mcp]: https://seranking.com/api/integrations/mcp/
[seranking-credits]: https://seranking.com/api/data/getting-started/
[seranking-skills]: https://github.com/seranking/seo-skills/tree/main/skills/seo-api
[ke-mcp]: https://api.keywordseverywhere.com/docs/#/mcp_integration
[ke-credits]: https://api.keywordseverywhere.com/docs/#/keyword_data/get_keyword_data
[alsoasked-auth]: https://developers.alsoasked.com/docs/also-asked/j389o9lgezike-authentication
[alsoasked-search]: https://developers.alsoasked.com/docs/also-asked/fdmxb8iq84kmn-searching
[otterly-mcp]: https://docs.otterly.ai/mcp-server
[moz-mcp]: https://moz.com/api/docs/mcp
[cc-mcp]: https://code.claude.com/docs/en/mcp
[cc-hooks]: https://code.claude.com/docs/en/hooks
[cc-permissions]: https://code.claude.com/docs/en/permissions
[cc-plugin-components]: https://code.claude.com/docs/en/plugins/components
[cc-plugin-ref]: https://code.claude.com/docs/en/plugins/manifest-reference
[cc-cloud-env]: https://code.claude.com/docs/en/cloud-environments
[cc-headless]: https://code.claude.com/docs/en/headless
[cc-chrome]: https://code.claude.com/docs/en/chrome
[chrome-perms]: https://support.claude.com/en/articles/12902446-claude-in-chrome-permissions-guide
[chrome-safety]: https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely
[playwright-mcp]: https://github.com/microsoft/playwright-mcp
