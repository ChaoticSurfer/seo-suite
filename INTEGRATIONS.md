# Integrations

Every tool seo-suite connects to, how each connection works, what you need to do, what it costs, and what is still
planned. Checked 2026-10-24. Prices change often; [references/tools.md](references/tools.md) has the full price notes.

**The short version:**

- **It works with no accounts and no keys.** The plugin's own scripts fetch web pages directly and use free Google
  and Bing endpoints. That is enough for a full technical audit.
- **Paid SEO data** (Semrush, Ahrefs, DataForSEO) comes through optional connector plugins in this repo. Paid calls
  stay off until you set a budget.
- **Your own Google and Bing data** comes from exports, Google's official GA4 server, or Claude working in the browser
  while you are signed in.
- **Some tools are advice only.** The docs say when they are worth paying for, but the plugin does not connect to
  them.

## Contents

- [Where to start](#where-to-start)
- [Terms used here](#terms-used-here)
- [At a glance](#at-a-glance)
- [Rules every integration follows](#rules-every-integration-follows)
- [Built in: no accounts, no keys](#built-in-no-accounts-no-keys)
- [Paid SEO data: connector plugins](#paid-seo-data-connector-plugins)
- [The credit guard: a budget for every paid call](#the-credit-guard-a-budget-for-every-paid-call)
- [Autonomy levels: what Claude may change](#autonomy-levels-what-claude-may-change)
- [Your own data: Google, Bing and your business accounts](#your-own-data-google-bing-and-your-business-accounts)
- [Free servers you can add yourself](#free-servers-you-can-add-yourself)
- [Public web sources](#public-web-sources)
- [Scheduled runs and code changes](#scheduled-runs-and-code-changes)
- [Which source answers which question](#which-source-answers-which-question)
- [What to connect, by budget](#what-to-connect-by-budget)
- [Every credential and where it goes](#every-credential-and-where-it-goes)
- [What leaves your machine](#what-leaves-your-machine)
- [Check your setup](#check-your-setup)
- [Advice only: not connected](#advice-only-not-connected)
- [Planned, not built yet](#planned-not-built-yet)
- [How it works inside Claude Code](#how-it-works-inside-claude-code)
- [More detail](#more-detail)

## Where to start

Every step after the first is optional. Stop once the free data answers your questions.

1. **Nothing yet.** Install seo-suite ([README](README.md#install)) and ask in plain words, for example "audit
   example.com". The scripts need no accounts or keys.
2. **Google Search Console.** Add the site, preferably as a Domain property, verify it
   ([how](#verifying-you-own-the-site)), and submit the sitemap under *Indexing → Sitemaps*. Then either export the
   *Performance* report each month, or let Claude open Search Console in the browser while you are signed in.
3. **Bing Webmaster Tools.** Import the site from Search Console, which also verifies it.
4. **Ahrefs Free.** Verify the site. It gives the best free view of your own backlinks: the top 1,000 backlinks and
   keywords, plus a site audit.
5. **A PageSpeed Insights key,** only if `psi.py` runs out of the shared quota. Set `psi_api_key` with
   `/plugin configure seo-suite@seo-suite`.
6. **GA4,** if you want to see conversions from organic traffic. Add Google's `analytics-mcp` server (see
   [GA4](#your-own-data-google-bing-and-your-business-accounts)).
7. **Google Business Profile,** if you are a local business. Set it up or claim it.
8. **Paid data,** only for questions free data can't answer. Install one connector, sign in, then set its budget
   above 0 (see [the credit guard](#the-credit-guard-a-budget-for-every-paid-call)).
9. **Let Claude change things,** if you want. At the default autonomy level 1 it only reads and reports. Level 2 lets
   it propose code changes as pull requests ([levels](#autonomy-levels-what-claude-may-change)).
10. **Schedules, last.** The seo-automation skill proposes permission rules and a schedule, and applies them only
    after your OK.

Commands that start with `/`, such as `/plugin configure`, are typed into a Claude Code session. Commands that start
with `claude`, `gcloud` or `npx` are run in your computer's terminal.

## Terms used here

- **Connector plugin:** a small add-on plugin in this repo that connects one paid vendor. seo-suite itself is the main
  plugin.
- **MCP server:** a connection that lets Claude call a vendor's data directly as tools, instead of you exporting
  reports.
- **OAuth sign-in:** you log in on the vendor's own website in your browser and approve access. Claude never sees or
  types your password.
- **API units:** the credits Semrush and Ahrefs charge per data request. DataForSEO charges in US dollars.
- **Credit guard:** the plugin's spending limit. It checks every paid request against the budgets you set.
- **Run:** one Claude Code session, whether you are watching it or it was scheduled.
- **Autonomy level:** how much Claude may change without asking, from 1 (read only, the default) to 4.
- **Pull request and CI:** a pull request is a proposed change to your site's code that stays separate until it is
  merged. CI is the automated checks your code host runs on it.
- SEO terms such as SERP (the search results page) and Core Web Vitals: see the
  [beginner glossary](references/guide-beginner.md#glossary).

## At a glance

| Level | Meaning |
|---|---|
| **Built in** | The plugin's own scripts call it. Nothing to set up |
| **Connector** | Install a small add-on plugin from this repo and sign in to the vendor once. The credit guard limits its spending |
| **Add it yourself** | No connector. You add the vendor's own MCP server. The credit guard recognises it and limits its spending |
| **Your licence** | A licensed tool you add yourself. The credit guard recognises it but lets calls through, because there is no per-call charge |
| **Your account** | Your own Google, Bing or business data, through exports, an official server or the browser |
| **Web** | Public sources Claude reads with its own web tools, or that you check by hand |
| **Advice only** | Covered in the docs, with no connection |
| **Planned** | Not built yet |

| Tool | Level | Used for | What you do | Cost |
|---|---|---|---|---|
| Any website (yours or a competitor's) | Built in | Crawls, page audits, robots.txt, sitemaps, redirects, rendering checks, page comparisons | Nothing | Free |
| Google PageSpeed Insights API | Built in | Lab speed audits and real-user Core Web Vitals | Nothing. Add a free key only if the shared quota runs out | Free |
| Google, Bing and YouTube autocomplete | Built in | Keyword ideas | Nothing | Free. Unofficial public endpoints, rate-limited |
| Your server's access logs | Built in | Which bots crawl what, fake Googlebots, sitemap URLs never crawled | Supply the log files | Free |
| Semrush | Connector | Competitors' keywords and traffic, keyword volume and difficulty | Install the connector, sign in, set `semrush_monthly_units` | A Semrush plan that includes API units |
| Ahrefs | Connector | Backlinks, competitor link profiles, organic keywords | Install the connector, sign in, lower the key's cap in Ahrefs, set `ahrefs_monthly_units` | Lite plan ($129/mo) or higher |
| DataForSEO | Connector | Bulk keyword volumes, search result snapshots, backlinks, AI-answer data | Install the connector, enter the API login, set a daily limit at DataForSEO, set `dataforseo_monthly_usd` | Pay as you go, $50 minimum top-up |
| Similarweb, SE Ranking, Keywords Everywhere, AlsoAsked, Otterly, Lumar | Add it yourself | Traffic estimates, rank tracking, volumes, question research, AI-answer tracking, crawling | Add the vendor's MCP server (named after the vendor), set `other_monthly_usd` | The vendor's own plan |
| Screaming Frog | Your licence | Large crawls with JavaScript rendering | CLI for scheduled crawls, MCP in sessions you watch | £199/year. Free mode crawls 500 URLs and has no MCP |
| Sitebulb | Your licence | Reading finished crawls (its MCP is read-only and can't start crawls) | Add its MCP server (OAuth) | A Sitebulb plan |
| Google Search Console | Your account | Clicks, queries, positions, indexing | Export Performance reports, or let Claude use Search Console in the browser | Free |
| Google Analytics 4 | Your account | What organic visitors do and whether they convert | Sign in with `gcloud` and add Google's `analytics-mcp` server | Free |
| Bing Webmaster Tools | Your account | Bing search data and your backlinks | Export reports | Free |
| Google Keyword Planner | Your account | Search volume ranges | Export the shortlist's volumes | Free with a Google Ads account |
| Google Business Profile, Merchant Center | Your account | Local and shopping visibility | Share exports or read-only access | Free |
| IndexNow | Your account | Telling Bing, Yandex and others that a page changed | Host a key file at your site's root | Free |
| Live search results | Web | Who ranks, what the results page shows, People Also Ask | Nothing | Free |
| ChatGPT, Perplexity, Google AI Overviews and AI Mode, Copilot, Claude, Gemini | Web | Whether AI answers mention or cite you | Nothing, or collect answers yourself | Free (DataForSEO for automatic sampling) |
| Wayback Machine | Web | Old versions of pages | Nothing | Free |
| Rich Results Test, Schema Markup Validator | Web (by hand) | A final check of structured data | Run them yourself | Free |

## Rules every integration follows

- **Credentials go only into Claude Code's own settings:** `/mcp` sign-ins, `/plugin configure`, or environment
  variables. Never into chat, files, logs or websites. If a key or password ever appears in chat, it isn't used:
  revoke it and enter a new one through `/plugin configure` or `/mcp`.
- **Paid tools only through their official APIs and MCP servers.** The plugin never drives the Semrush, Ahrefs or
  Similarweb websites, Google search results for rank checks, or business.google.com. Their terms or robots.txt forbid
  it. Two exceptions are deliberate:
  - `keyword_ideas.py` reads Google's and Bing's public autocomplete endpoints, which are unofficial and
    rate-limited.
  - Claude may use your own Search Console, Bing Webmaster Tools and site in the browser, lightly and with you
    present.
- **Some actions always need you,** whatever the autonomy level: messages to real people, buying links or reviews,
  disavow files, deleting pages that earn traffic, Change of Address, DNS and CDN changes, Google Business Profile and
  Merchant Center edits, and spending above budget. The full list is in [references/autonomy.md](references/autonomy.md).

## Built in: no accounts, no keys

The scripts use only Python's standard library, so there is nothing to install.

- **Websites.** `crawl.py`, `page_audit.py`, `robots_check.py`, `sitemap_check.py`, `redirect_check.py`,
  `content_score.py` and `compare_pages.py` fetch pages over plain HTTP, including competitors' pages for comparison.
  `render_diff.py` compares the raw HTML with a rendered copy saved from a browser.
  - A Cloudflare bot challenge is reported as a critical finding by the page audit and crawl, and is never bypassed.
    Other CDNs' challenges are not recognised: they show up as HTTP errors, or as thin pages when served with a 200.
- **PageSpeed Insights.** `psi.py` calls Google's PageSpeed Insights API. It returns a Lighthouse lab audit, plus
  real-user Core Web Vitals from the Chrome UX Report when Google has enough data for the page.
  - It works without a key, but the shared quota is small. For more, create a free key in Google Cloud and set the
    `psi_api_key` option ([where it goes](#every-credential-and-where-it-goes)).
  - The **CrUX API and History API** are separate, and `psi.py` doesn't call them. They need a free Google Cloud key
    and allow 150 queries a minute per project, a limit paying can't raise. The History API returns up to 40 weekly
    points and refreshes on Mondays, which is why the weekly technical monitor runs on Tuesdays.
- **Autocomplete.** `keyword_ideas.py` collects Google and Bing autocomplete suggestions, and YouTube's on request. It
  gives ideas, not volumes.
  - You can set the language and country (`--hl ka --gl ge` for Georgia). The expansion words (English question and
    buying words, plus a–z) and the intent labels are English, so in other languages and scripts most expansions add
    little and most intents come out "unclear".
- **Server logs.** `log_analyze.py` reads your Apache or Nginx access logs (combined format, `.gz` accepted). It shows
  what Googlebot, Bingbot and AI crawlers actually request: crawl waste, errors served to bots, and sitemap URLs never
  crawled. With `--verify-dns`, it runs reverse and forward DNS lookups to confirm that "Googlebot" and "Bingbot" hits
  really come from Google and Microsoft.

## Paid SEO data: connector plugins

Each connector is optional. Install only the ones for vendors you pay for, so nobody sees a failing server for a tool
they don't have.

| Vendor | Install (type in Claude Code) | How it connects | Sign-in |
|---|---|---|---|
| **Semrush** | `/plugin install seo-suite-semrush@seo-suite` | Semrush's official MCP server, read-only | Run `/mcp`, choose `plugin:seo-suite-semrush:semrush`, then **Authenticate**. Log in to Semrush in your browser |
| **Ahrefs** | `/plugin install seo-suite-ahrefs@seo-suite` | Ahrefs' official MCP server, limited to its SEO tool groups | Run `/mcp`, choose `plugin:seo-suite-ahrefs:ahrefs`, then **Authenticate**. Log in, pick the workspace and click **Allow**. Needs the Lite plan or higher |
| **DataForSEO** | `/plugin install seo-suite-dataforseo@seo-suite` | DataForSEO's official MCP server, which runs on your computer through `npx`. Needs Node.js 22 or newer. The first start downloads it | Run `/plugin configure seo-suite-dataforseo@seo-suite` and enter the API login and password from DataForSEO's dashboard. The API password is not your dashboard password. Both are masked and kept in the system keychain (the Keychain on macOS) |

Vendor details:

- **Semrush.**
  - Semrush charges in API units, and MCP calls spend the same units. Semrush One Starter and Pro+, and the older Pro
    and Guru plans, include 50,000 units. Semrush's pages differ on whether they refresh monthly or at renewal.
    Advanced and Business plans need a separate units package.
  - **API key instead of OAuth:** skip the connector. Save the key in your shell as `SEMRUSH_API_KEY`, then run this
    in your own terminal, so the key never goes into chat:

    ```bash
    claude mcp add --transport http semrush-key https://mcp.semrush.com/v2/mcp --header "Authorization: Apikey $SEMRUSH_API_KEY"
    ```

  - Use one route, not both: two Semrush servers show every tool twice. Having an API key also lets you use Semrush's
    free `countapiunits` balance check, though whether it shows the MCP allowance is unverified.
- **Ahrefs.**
  - Signing in creates an Ahrefs API key with a monthly cap of 200,000 units. Lower it to your budget in Ahrefs under
    Account settings → API keys, and turn off pay-as-you-go units under Limits & usage so overage is never charged.
  - Ahrefs' terms forbid scripted use of its MCP server, so Ahrefs is used only in sessions you are watching.
    Scheduled runs use DataForSEO for links and rankings instead.
- **DataForSEO.**
  - Also set a daily spending limit in DataForSEO's dashboard (API Settings). Calls over it fail instead of costing
    more.
  - **Other routes:** to sign in with OAuth instead of a password, skip the connector and run
    `claude mcp add --transport http dataforseo https://mcp.dataforseo.com/v3/mcp`, then `/mcp` → Authenticate. The
    credit guard also covers a local server you add by hand (`npx -y dataforseo-mcp-server@3.1.3`, named `dfs-mcp` in
    DataForSEO's guide).

Setup notes for each: [Semrush](connectors/semrush/README.md), [Ahrefs](connectors/ahrefs/README.md),
[DataForSEO](connectors/dataforseo/README.md). The whole setup, with permission rules and schedules, is in the
[seo-automation skill](skills/seo-automation/SKILL.md).

## The credit guard: a budget for every paid call

The credit guard is part of the main plugin. It checks every paid MCP call before it runs and records it after,
however the vendor was added (a connector above, `claude mcp add`, or a claude.ai connector), **as long as the
server's name contains the vendor's name**, for example `semrush`, `ahrefs`, `dataforseo` or `dfs-mcp`. Name any
server you add by hand after its vendor. claude.ai connectors should match too, but that is unverified.

There is no guard in cloud routines, which load no plugins, or in `claude -p --bare`, which skips hooks. Never add
`--bare` to a scheduled run.

**Every budget starts at 0, which blocks all paid calls.** Free tools and cached results still work. You set the
budgets once with `/plugin configure seo-suite@seo-suite`:

| Option | Default | Meaning |
|---|---|---|
| `semrush_monthly_units`, `ahrefs_monthly_units` | 0 | Monthly budget in API units. A month is a UTC calendar month |
| `dataforseo_monthly_usd`, `other_monthly_usd` | 0 | Monthly budget in US dollars |
| `per_run_cap_pct` | 25 | The most one session may spend, as a percentage of each monthly budget |
| `ask_above_pct` | 5 | A single call estimated above this percentage of its monthly budget is not run. It is listed in the end-of-run questions, and you approve it by raising this value or the budget for the next run |
| `max_rows` | 50 | Row limit on paid Semrush, Ahrefs and DataForSEO calls. Other vendors' calls are not clamped |
| `cache_ttl_days` | 0 | Days a paid result is reused. 0 means 30 days for keyword volumes, 7 for search results, rankings, domain data and backlinks, and 1 for site audits |

**Example.** With `semrush_monthly_units` at 20,000, one session may spend up to 5,000 units (25%). Any single call
estimated above 1,000 units (5%) is held for your decision.

**Suggested starting budgets for one site:**

- Semrush: up to 20,000 of the 50,000 units your plan includes.
- Ahrefs: up to 20,000 (Lite includes 200,000).
- DataForSEO: $10. The scheduled pipelines cost about $5–6 a month for one site.
- Other vendors: 0 until you connect one.

What it does on each call:

- **Reuses results.** An identical call is answered from the cache, which costs nothing. Semrush results are never
  reused after 30 days, because Semrush's terms forbid caching them longer. Older cache files stay on disk until you
  delete them.
- **Limits rows.** Row limits on Semrush, Ahrefs and DataForSEO calls are capped at `max_rows`, and a missing limit is
  added on Ahrefs and DataForSEO list and crawl endpoints. A Semrush per-line report with no row limit and no fixed
  line count, or one with no known price, is refused.
- **Stops overspending.** A call that would go over the monthly budget or the per-run cap is refused. If actual
  charges still push a vendor past either limit, the guard stops the run after that batch of calls. A failed call is
  counted at its estimate, in case the vendor charged it.
- **Holds expensive calls for your decision.** A call above `ask_above_pct`, or a Semrush report whose price is
  unknown, is not run. It is recorded and listed in the questions at the end of the run, so the run never stops to
  ask.
- **Logs spend** in a ledger, so you can see what each tool cost. The ledger, cache and held requests are in the
  plugin's data folder, under `credit-guard/`.

Vendors it recognises:

| Vendor | Budget it uses | How it prices a call |
|---|---|---|
| Semrush | `semrush_monthly_units` | From Semrush's published prices. A report with no known price is held for your decision |
| Ahrefs | `ahrefs_monthly_units` | From Ahrefs' published prices. Free tools, such as Rank Tracker and account info, run without a budget check |
| DataForSEO | `dataforseo_monthly_usd` | From DataForSEO's published prices. Free tools, such as documentation and the balance check, run without a budget check |
| Similarweb, SE Ranking, Keywords Everywhere, AlsoAsked, Otterly | `other_monthly_usd` | Prices unknown. Every call is counted as `ask_above_pct` of `other_monthly_usd` (5% by default) |
| Lumar | `other_monthly_usd` | Calls that start or resume a crawl (`analyze_run_crawl`, `analyze_resume_crawl`, `analyze_create_single_page_request`, `lumar_act`) are counted the same way. All other calls run without a budget check |
| Screaming Frog, Sitebulb | None | You pay for a licence, not per call, so calls run without a budget check |

Only Semrush, Ahrefs and DataForSEO have a connector. For the others, add the vendor's MCP server yourself and name it
after the vendor so the guard recognises it:

- Lumar's MCP needs its paid MCP Server add-on.
- Screaming Frog's MCP (v24 or newer) needs a paid licence, and the app running or the Claude Desktop extension.
  Scheduled crawls use the Screaming Frog command line (`--headless`) instead.
- Screaming Frog and Sitebulb document no Claude Code command.
- AlsoAsked has no MCP server we could confirm, only a REST API with an API key, so the guard covers it only if you
  add a server whose name contains `alsoasked`.

More detail: [references/paid-tools-automation.md](references/paid-tools-automation.md).

## Autonomy levels: what Claude may change

By default Claude only reads and reports. To allow more, set the `autonomy_level` option with
`/plugin configure seo-suite@seo-suite`:

| Level | What Claude does without asking |
|---|---|
| **1. Analyse** (default) | Reads only: fetches, crawls, free tools, paid calls within budget, reports |
| **2. Fix in code** | Level 1, plus edits to your site's code on a separate branch, sent as a pull request |
| **3. Ship** | Level 2, plus merging pull requests that pass CI, and submitting sitemaps and IndexNow for changed URLs |
| **4. Operate** | Level 3, plus CMS drafts and publishing, and Search Console sitemap submission, through a connected account |

Anything above your level waits for your OK. No level covers requesting indexing in Search Console, so that always
needs your OK. Some actions always need you, whatever the level (see [Rules](#rules-every-integration-follows)).
Details: [references/autonomy.md](references/autonomy.md).

## Your own data: Google, Bing and your business accounts

| Source | How seo-suite gets the data | Notes |
|---|---|---|
| **Google Search Console** | Your exports (Performance → Export), read by `gsc_analyze.py`. Or Claude works in Search Console itself in the built-in browser or Claude in Chrome, signed in as you. With the Ahrefs connector, its `gsc` tools also read Search Console data at 0 units (except `gsc-anonymous-queries`), in sessions you watch | Google publishes no Search Console MCP server. With access set up (OAuth, or a service account added as a property user), the Search Console API gives up to 25,000 rows per request and the URL Inspection API 2,000 checks a day per site. A community server can wrap them (see [free servers](#free-servers-you-can-add-yourself)). For big sites, have an owner turn on the bulk export to BigQuery early: it needs Google Cloud billing and has no row cap, but does not backfill. The Search generative AI report has no API, so it is exported in the browser. **Data warning:** a Google logging error made impressions, CTR and average position unreliable from 2025-05-13 to 2026-04-27 (clicks were not affected), so don't compare those metrics across that window ([Google's notice](https://support.google.com/webmasters/answer/6211453)) |
| **Google Analytics 4** | Google's official `analytics-mcp` server, which you add yourself after signing in with `gcloud` | Read-only unless started with `--allow-write`. The plugin never adds that flag |
| **Bing Webmaster Tools** | Performance exports, which `gsc_analyze.py` reads by matching Bing's column names to Search Console's. Or Bing's API, with a key from Settings → API Access, through a community MCP server you choose to trust | The plugin has no built-in Bing API client. Bing powers Copilot, so its data matters for AI search too |
| **Google Keyword Planner** | Your export (a UTF-16 CSV), read by `research_store.py ingest volumes`, which keeps ranges such as "1K – 10K" as written | Ranges unless the Ads account spends. The same command reads Semrush, Ahrefs and DataForSEO volume exports. Google's official Google Ads MCP has no Keyword Planner |
| **Google Business Profile** | An authorised connector, or exports and screenshots from the owner. The public listing is read with web search | Performance (searches, calls, directions, website clicks) needs owner access. The Business Profile API needs Google's approval. Profile edits always need your OK, and business.google.com is never automated |
| **Bing Places, Apple Business Connect** | The owner's dashboards | Listing corrections are drafted for the owner to apply |
| **Google Merchant Center** | Read-only, through a connector or an export: diagnostics, the feed source and a sample of about 20 top products | Feed data overrides page markup, so seo-ecommerce checks that feed, page and markup match. Edits always need your OK |
| **IndexNow** | Changed URLs are submitted at autonomy level 3 or higher. First the site must serve a key (8–128 letters, digits or dashes) as a UTF-8 text file `{key}.txt` at its root. seo-suite has no IndexNow setting, so the key file is part of the site | Up to 10,000 URLs per request. Reaches Bing, Yandex, Seznam, Naver, Yep and others. Google does not use IndexNow |
| **Cloudflare AI Crawl Control** | Read in your Cloudflare dashboard: Security Settings → Bot traffic → AI bot policies | With Bot Preference Sync on and an AI policy set to block, Cloudflare puts its own rules at the top of your robots.txt. They disallow Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot, Google-Extended, GPTBot and meta-externalagent, and add `Content-signal: search=yes, ai-train=no, use=reference`. `robots_check.py` evaluates the live file, so it sees these rules, but it doesn't yet say Cloudflare added them. Available on all plans |
| **Google Indexing API** | Not used | Only for JobPosting and livestream (BroadcastEvent) pages. It is not a way to get ordinary pages indexed |

### Verifying you own the site

Search Console, Bing Webmaster Tools and Ahrefs Free all need proof that you own the site.

| Service | Ways to verify | Watch out for |
|---|---|---|
| Google Search Console | **Domain property:** a DNS record at your domain name provider (the only method). **URL-prefix property:** HTML file upload, HTML tag, Google Analytics tracking code, Google Tag Manager, or the DNS record | Prefer a Domain property. It covers every subdomain and both http and https |
| Bing Webmaster Tools | Import from Search Console, which verifies automatically. Or an XML file (`BingSiteAuth.xml` at the site root), a meta tag, or a CNAME record. Domain Connect can add the record for supported DNS providers | Bing re-checks imported sites. If you revoke its Search Console access, reconnect it or verify another way |
| Ahrefs Free | Search Console (recommended), a DNS TXT record, an HTML file in the root folder, or an HTML tag in the homepage `<head>` | With Search Console, add the project in the same form as the Search Console property (`www` or not). Keep the record in place: Ahrefs checks it regularly |

From autonomy level 2, Claude can add the HTML file or tag in a pull request. It counts only once that change is live.
A DNS record needs your approval at every level, because DNS changes are always gated.

## Free servers you can add yourself

None of these is bundled. The credit guard has no opinion on them because they cost nothing, so your permission rules
decide.

| Server | What it adds | Notes |
|---|---|---|
| Chrome DevTools MCP (official) | Performance traces (for example, the long tasks behind a poor INP) and a Lighthouse audit of your own pages. The audit has no performance category | `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`. Use it only on your own site |
| Microsoft Clarity MCP (official) | Your Clarity project's data | The project admin creates the token. 10 requests per project per day, covering the last 1–3 days, so run it as one fixed daily job |
| Google Ads MCP (official) | Read-only Google Ads data | It has no Keyword Planner |
| Bing Webmaster Tools, community (`zizzfizzix/mcp-server-bwt`) | Bing query and page stats | Uses your Bing API key. Third-party code |
| Search Console, community (`AminForou/mcp-gsc`) | The Search Console API | OAuth or a service account. Third-party code holding your Search Console access: audit it and pin a version. Destructive tools are off by default |

## Public web sources

- **Live search results.** The `seo-serp-researcher` agent uses Claude's own web search and page fetch tools. It
  collects the top 10 results, page types, results-page features and People Also Ask questions. These are not
  Google's own results. For exact Google positions, use Search Console or DataForSEO.
- **AI answers.** A frozen set of questions is asked 3–5 times per engine (ChatGPT, Perplexity, Google AI Overviews
  and AI Mode, Copilot, Claude, Gemini), and the answers are logged for `ai_visibility.py`, which reports mention and
  citation rates with confidence intervals.
  - You can collect them yourself, or Claude can in the built-in browser, using only sessions you already have. It
    never creates accounts and stops at any CAPTCHA.
  - Automatic sampling runs through the DataForSEO connector: the AI-visibility pipeline in the seo-automation skill
    samples weekly with DataForSEO's LLM Scraper (about $0.18 a week for 25 questions × 2 engines × 3 runs) and adds
    LLM Mentions monthly.
- **Wayback Machine.** Its free CDX API shows how competitors' pages, and your own, looked before. It also recovers old
  URLs during a site move.
- **Google Search Status Dashboard.** seo-analytics checks `status.search.google.com` to see whether a traffic drop
  matches a ranking update.
- **Rich Results Test and Schema Markup Validator.** `page_audit.py` checks structured data against Google's current
  rules. These two Google tools have no public API, so use them by hand for a final check.

## Scheduled runs and code changes

- **Scheduling.** Recurring runs, such as a weekly technical check, use one of these:

  | Where it runs | Credit guard and paid tools | Use it for |
  |---|---|---|
  | Your Mac, on a timer. A macOS launchd job starts Claude Code without the app (`claude -p`). The Mac must be awake | Yes | Anything, including paid pipelines |
  | A scheduled task in the Claude Desktop app. It runs while the app is open and the Mac is awake | Yes, from your local setup | Anything, while the app is open |
  | A cloud routine (`/schedule`) on Anthropic's servers. Your Mac can be off | **No.** Cloud sessions load no plugins, so there is no credit guard | Free pipelines only |

  Scheduled runs never use Ahrefs. A `claude -p` run can't do an OAuth sign-in, so finish every sign-in first.
- **Permission rules.** seo-automation proposes allow, ask and deny rules for the connected vendors' free and read-only
  tools. Paid tools stay unlisted, so the credit guard decides. After your one-time OK, it merges the rules into
  `~/.claude/settings.json`, because a plugin can't ship them itself. Scheduled runs set
  `--permission-mode dontAsk` and list exactly the tools they need in `--allowedTools`.
- **Git, GitHub and CI.** From autonomy level 2, fixes go to the site's repo as a branch and pull request, opened with
  `git` and `gh`. From level 3, pull requests that pass CI can be merged. seo-technical can also add a CI job that
  downloads each key template's preview HTML and runs the page audit on it, failing on high-severity findings. A
  protected Vercel preview needs the `x-vercel-protection-bypass` header, with the secret stored in CI.
- **Your CMS and Search Console (level 4).** At autonomy level 4, Claude can save CMS drafts or publish, and submit
  sitemaps in Search Console, through a connector you have authorised. Below level 4, CMS changes are drafted for you
  to apply.

## Which source answers which question

| Question | Free source | Paid, when free isn't enough |
|---|---|---|
| Broken pages, redirects, titles, canonicals, duplicates | `crawl.py`, `page_audit.py`, `redirect_check.py` | Screaming Frog for sites over ~2,000 URLs or that rely on JavaScript |
| Is content there only after JavaScript runs? | `render_diff.py` with a page rendered in the browser | — |
| Speed and Core Web Vitals, yours or a competitor's | `psi.py` (Lighthouse lab audit plus field data) | — |
| Structured data | `page_audit.py`, then the Rich Results Test by hand | — |
| Your own queries, clicks and positions | Search Console export → `gsc_analyze.py` (16 months of data) | — |
| How bots crawl your site | `log_analyze.py` on your access logs | — |
| Keyword ideas | `keyword_ideas.py` (no volumes) | — |
| Search volume and difficulty | Keyword Planner ranges | DataForSEO Keywords Data for cheap bulk volumes. Semrush or Ahrefs for difficulty and results-page context together |
| Competitors' keywords and traffic | — | Semrush (strongest), Ahrefs |
| Your own backlinks | Ahrefs Free, Search Console *Links*, Bing Webmaster Tools | — |
| Competitors' backlinks | — | Ahrefs Lite or higher, or DataForSEO Backlinks pay per use |
| Rank tracking | Search Console positions | DataForSEO search snapshots for competitors and other locales |
| Visibility in AI answers | A frozen question set + `ai_visibility.py` | DataForSEO LLM endpoints, Ahrefs Brand Radar or Otterly |
| What a page looked like before | Wayback Machine CDX API | — |

## What to connect, by budget

| Budget | Stack |
|---|---|
| $0/mo | Search Console, Bing Webmaster Tools, GA4, a PageSpeed key, Ahrefs Free, Screaming Frog free mode, and seo-suite's scripts |
| ~$130–200/mo | Add **one** of Ahrefs Lite ($129, for link-heavy work) **or** Semrush SEO ($139) or Starter ($199) (for keyword- and competitor-heavy work), plus a $50 DataForSEO top-up for bulk volumes and search results, which lasts months at the scheduled pipelines' few dollars a month |
| ~$500+/mo | Ahrefs Standard **or** Semrush Pro+, plus a Screaming Frog licence, a DataForSEO wallet, and an AI tracker (Brand Radar or Otterly Standard) if AI visibility is a goal you report on |

Why each paid tool is worth it, and how to spend less: [references/tools.md](references/tools.md).

## Every credential and where it goes

| Credential | Where you get it | Where it goes |
|---|---|---|
| PageSpeed Insights API key | Google Cloud console → enable *PageSpeed Insights API* → Credentials → API key | `psi_api_key` in `/plugin configure seo-suite@seo-suite`. It is kept in the system keychain and exported as `PSI_API_KEY` each session |
| Semrush | OAuth, or an API key | OAuth: `/mcp` → `plugin:seo-suite-semrush:semrush` → Authenticate. Key: set `SEMRUSH_API_KEY` in your shell, then run the `claude mcp add … --header "Authorization: Apikey $SEMRUSH_API_KEY"` command above. The key ends up in `~/.claude.json` |
| Ahrefs (Lite or higher) | OAuth | `/mcp` → `plugin:seo-suite-ahrefs:ahrefs` → Authenticate. Then lower the key's 200,000-unit cap in Account settings → API keys |
| DataForSEO | API login and API password from the dashboard. The API password is not your dashboard password | `/plugin configure seo-suite-dataforseo@seo-suite` (system keychain). Never pass them on the command line |
| GA4 | Application Default Credentials from `gcloud auth application-default login` with the `analytics.readonly` and `cloud-platform` scopes, or by impersonating a service account | `GOOGLE_APPLICATION_CREDENTIALS` and `GOOGLE_PROJECT_ID` in the `claude mcp add analytics-mcp` command |
| Bing Webmaster Tools | Settings → API Access in Bing Webmaster Tools | No seo-suite option uses it. A community Bing MCP server can |
| Search Console | None by default: exports or the browser | A community MCP needs OAuth, or a service account that an owner adds as a property user |
| IndexNow | A key you make up: 8–128 letters, digits or dashes | A text file `{key}.txt` at the site root |
| Ahrefs Free | None | It has no API or MCP. Use it in its own interface |

## What leaves your machine

| Destination | What is sent | When |
|---|---|---|
| The sites you audit, yours or competitors' | Ordinary page requests (URLs) | Every crawl, page audit, robots, sitemap, redirect or comparison check |
| Google PageSpeed Insights | The page URL, and your key if set | `psi.py` |
| Google and Bing autocomplete | Your seed phrases, with the language and country | `keyword_ideas.py` |
| Your DNS resolver | IP addresses of hits claiming to be Googlebot or Bingbot | `log_analyze.py --verify-dns` only |
| Semrush, Ahrefs, DataForSEO and other vendors you connect | The query Claude sends: domains, URLs or keywords | Paid calls, only within your budgets |
| Google (GA4, Search Console) and other accounts you connect | Requests made with your sign-in | Only when you have connected them |
| Anthropic | Everything Claude reads or writes in the session, as for any Claude Code use | Always |

The credit guard's ledger and cache, the research store and the work log are local files. The research store goes
further only if you commit it to a repo.

## Check your setup

- **Servers:** `claude mcp list` shows each server. One that needs signing in again shows as failed.
- **Balances, free:** Ahrefs `subscription-info` (0 units), DataForSEO `appendix/user_data`, and Semrush
  `countapiunits` (API-key route only).
- **Credit guard:** `/hooks` shows it on PreToolUse, PostToolUse, PostToolUseFailure and PostToolBatch, plus the
  SessionStart hook for the PageSpeed key.
- **Cache:** repeat one paid call. The second answer comes from the cache and costs nothing.
- **Before scheduling:** finish every sign-in with `/mcp` or `claude mcp login <name>`, because a `claude -p` run
  cannot do OAuth.

## Advice only: not connected

The docs explain what these are for and when they are worth paying for, but the plugin has no connection to them.

| Tool | What the docs say it is good for |
|---|---|
| Moz | Domain Authority, Page Authority and Spam Score, when someone reports in them. Moz documents an MCP server, but the plugin has not checked or wired it |
| Majestic | Trust Flow and Citation Flow. API on its API plan only, no MCP |
| SpyFu | Historical paid-search and competitor ads |
| AnswerThePublic | Question and phrase lists. No API listed |
| Google Trends | Relative interest over time. Its API is in alpha |
| Ahrefs Brand Radar, Semrush AI Visibility, Peec AI, Profound | Paid trackers of brand mentions in AI answers |
| Semrush Sensor | Algorithm volatility, to see whether a drop is industry-wide (free page) |
| Looker Studio | Free dashboards on Search Console and GA4 |
| Ahrefs Free (formerly Ahrefs Webmaster Tools) | Your own site's backlinks and audit, in its own interface |
| Screaming Frog free mode | Crawling up to 500 URLs, to cross-check the plugin's crawler |
| Screaming Frog Log File Analyser | A desktop app for very large logs. `log_analyze.py` covers the core questions |
| YouTube Studio, vidIQ, TubeBuddy | YouTube analytics and keyword tools for a channel strategy |
| BrightLocal, Yext, Semrush Listing Management | Citation audits and listing distribution for multi-location businesses |
| Local Falcon | Map-pack rankings on a grid of locations |
| Botify, Conductor | Enterprise crawling and SEO platforms |

## Planned, not built yet

- **Direct AI-answer checks through the engines' own APIs,** OpenAI first, then Gemini: a fixed question set, several
  runs each, fed to `ai_visibility.py`. They use the APIs because OpenAI's terms forbid automated extraction from the
  ChatGPT app. API answers can differ from what the app shows.
- **A rank-tracking script** that stores positions and compares runs. Today the rank-tracking pipeline in the
  [seo-automation skill](skills/seo-automation/SKILL.md) uses Search Console positions from exports and DataForSEO
  search snapshots on a schedule, plus Ahrefs Rank Tracker in sessions you watch.
- **Competitor modules:** share of voice, competitor sitemap diffs, and Wayback change history as scripts. Today these
  are manual steps in the seo-competitors skill.

**Under consideration, not yet decided.** These came out of a review of other Claude Code SEO plugins (claude-seo,
geo-seo-claude, seomachine and the older seo-skills), keeping only ideas with evidence behind them:

- A read-only **Search Console API fetcher** (`webmasters.readonly` scope) that writes the same CSVs `gsc_analyze.py`
  reads, so mid-size sites aren't limited by the 1,000-row export.
- **WordPress drafts** for autonomy level 4, through an Application Password on a Contributor account, which can save
  drafts but not publish.
- An **IndexNow submitter** that checks the key file before sending, since level 3 promises IndexNow.
- **CrUX LCP subparts and the full 40-week history** in `psi.py`, using the same Google key.
- A **crawl diff** between runs, which the weekly technical monitor needs.

## How it works inside Claude Code

- **Hooks.** The plugin uses five hook events:
  - SessionStart exports `psi_api_key` as `PSI_API_KEY`.
  - PreToolUse, PostToolUse and PostToolUseFailure run the credit guard on the recognised vendors' MCP calls.
  - PostToolBatch runs after every batch of tool calls and stops the run when a batch pushed a vendor past its monthly
    budget or per-run cap.
- **Plugin options.** These hold the autonomy level, budgets and keys. Sensitive values are kept in the system
  keychain.
- **The built-in browser, or Claude in Chrome.** Used for Search Console and other dashboards without an API, and for
  rendered pages. Claude never types passwords. It stops at sign-in pages, CAPTCHAs and bot challenges, and lists them
  as access requests. Claude in Chrome needs a claude.ai sign-in, so it never runs in scheduled or API-key jobs.
- **Subagents.** The site auditor, search-results researcher and content reviewer run in parallel to keep big outputs
  out of the main conversation.

## More detail

- [references/tools.md](references/tools.md): every free and paid tool, the case for each paid one, prices, and how
  to spend less.
- [references/paid-tools-automation.md](references/paid-tools-automation.md): how the paid tools are automated, and
  the credit guard in detail.
- [references/autonomy.md](references/autonomy.md): what Claude decides alone, what it asks, and the autonomy levels.
- [skills/seo-automation/SKILL.md](skills/seo-automation/SKILL.md): connecting the vendors, budgets, permissions and
  schedules.
