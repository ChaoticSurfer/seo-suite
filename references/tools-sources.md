# Sources for the tool stacks

Primary sources for the facts in [tools.md](tools.md) and [tools-paid.md](tools-paid.md).

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
  https://developers.openai.com/api/docs/pricing); Anthropic web search fee and Sonnet and Opus 5.5 prices
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
