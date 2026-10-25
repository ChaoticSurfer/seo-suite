# Integrations

Every tool seo-suite connects to, how each connection works, what you need to do, what it costs, and what is still
planned. Checked 2026-10-24. Prices change often; [references/tools.md](references/tools.md) has the full price notes.

**The short version:**

- **It works with no accounts and no keys.** The plugin's own scripts fetch web pages directly and use free Google
  and Bing endpoints. That is enough for a full technical audit.
- **claude-seo is installed on first need** for JavaScript rendering, the Search Console API and technical drift.
  `scripts/claude_seo.py` clones [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) into seo-suite's
  data folder, pulls its latest main before every use (never pinned) and sets up its venv and Chromium (about 150 MB).
  It needs git and Python 3.11–3.14, and it is not added as a second plugin.
- **Paid SEO data** (Semrush, Ahrefs, DataForSEO) comes through optional connector plugins in this repo. Paid calls
  stay off until you set a budget.
- **Your own Google and Bing data** comes from the Search Console API through claude-seo once you sign in, exports,
  Google's official GA4 server, or Claude working in the browser while you are signed in.
- **Some tools are advice only.** The docs say when they are worth paying for, but the plugin does not connect to
  them.

## Contents

- [Where to start](#where-to-start)
- [Terms used here](#terms-used-here)
- [At a glance](#at-a-glance)
- [Main stack](#main-stack)
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
   ([how](#verifying-you-own-the-site)), and submit the sitemap under *Indexing → Sitemaps*. Then sign in once for the
   API ([how](#your-own-data-google-bing-and-your-business-accounts)), or export the *Performance* report each month,
   or let Claude open Search Console in the browser while you are signed in.
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
| **Through claude-seo** | `claude_seo.py` installs claude-seo on first use and runs its tool. Needs git and Python 3.11–3.14 |
| **Connector** | Install a small add-on plugin from this repo and sign in to the vendor once. The credit guard limits its spending |
| **Add it yourself** | No connector. You add the vendor's own MCP server. The credit guard recognises it and limits its spending |
| **Your licence** | A licensed tool you add yourself. The credit guard recognises it but lets calls through, because there is no per-call charge |
| **Your account** | Your own Google, Bing or business data, through exports, an official server or the browser |
| **Web** | Public sources Claude reads with its own web tools, or that you check by hand |
| **Advice only** | Covered in the docs, with no connection |
| **Planned** | Not built yet |

The Stack column gives each tool's label in the [Main stack](#main-stack): "default" is the free stack every run
starts with, and "paid" is the small and big lists that apply once paid tools are set up.

| Tool | Level | Used for | What you do | Cost | Stack |
|---|---|---|---|---|---|
| Any website (yours or a competitor's) | Built in | Crawls, page audits, robots.txt, sitemaps, redirects, rendering checks, page comparisons | Nothing | Free | Main in every list |
| claude-seo (AgriciDaniel) | Through claude-seo | The rendered DOM for `render_diff.py` (Playwright), Search Console Search Analytics, URL Inspection and sitemaps, and technical drift between crawls | Nothing: installed on first use. For Search Console, sign in once | Free | Main in every list |
| Google PageSpeed Insights API | Built in | Lab speed audits and real-user Core Web Vitals | Nothing. Add a free key only if the shared quota runs out | Free | Main (paid lists); Cross-check in the default stack, lab against CrUX field |
| Google, Bing and YouTube autocomplete | Built in | Keyword ideas | Nothing | Free. Unofficial public endpoints, rate-limited | Default: Cross-check (Google, Bing). Paid: Cross-check (Bing), Reserve (Google). YouTube: Reserve |
| Your server's access logs | Built in | Which bots crawl what, fake Googlebots, sitemap URLs never crawled | Supply the log files | Free | Main in every list |
| Semrush | Connector | Competitors' keywords and traffic, keyword volume and difficulty | Install the connector, sign in, set `semrush_monthly_units` | A Semrush plan that includes API units | Reserve |
| Ahrefs | Connector | Backlinks, competitor link profiles, organic keywords | Install the connector, sign in, lower the key's cap in Ahrefs, set `ahrefs_monthly_units` | Lite plan ($129/mo) or higher | `domain-rating-free` (to build): Main (default), Cross-check (small, big). REST v3 on Standard (to build): Cross-check (big). Lite, Site Audit, the GSC endpoints and the MCP: Reserve, the MCP only in sessions you watch |
| DataForSEO | Connector | Bulk keyword volumes, search result snapshots, backlinks, AI-answer data | Install the connector, enter the API login, set a daily limit at DataForSEO, set `dataforseo_monthly_usd` | Pay as you go, $50 minimum top-up | Main (small, big); labels per API in [references/tools.md](references/tools-paid.md#dataforseo). Reserve (default) |
| Similarweb, SE Ranking, Keywords Everywhere, AlsoAsked, Otterly, Lumar | Add it yourself | Traffic estimates, rank tracking, volumes, question research, AI-answer tracking, crawling | Add the vendor's MCP server (named after the vendor), set `other_monthly_usd` | The vendor's own plan | SE Ranking Data API (to build): Main (small). In the big list it splits by market: Main for the GE pairs and the markets DataForSEO Labs lacks, and Cross-check in the markets Labs covers. Reserve (default). SE Ranking's other APIs and the other vendors: Reserve |
| Screaming Frog | Your licence | Large crawls with JavaScript rendering | CLI for scheduled crawls, MCP in sessions you watch | £199/year. Free mode crawls 500 URLs and has no MCP | Big: Main (licensed CLI). Small and the default stack: Reserve |
| Sitebulb | Your licence | Reading finished crawls (its MCP is read-only and can't start crawls) | Add its MCP server (OAuth) | A Sitebulb plan | Reserve |
| Google Search Console | Your account | Clicks, queries, positions, indexing | Sign in once for the API (`claude_seo.py google-signin`), or export Performance reports, or let Claude use Search Console in the browser | Free | The API (through claude-seo): Main (default, small, big); in the default Technical list, URL Inspection is a Cross-check against `crawl.py`. Bulk export to BigQuery: Main (default, big), Reserve (small). Search generative AI report, Links and Crawl Stats exports: Reserve, use when a person exports them |
| Google Analytics 4 | Your account | What organic visitors do and whether they convert | Sign in with `gcloud` and add Google's `analytics-mcp` server | Free | Main in every list. AI referrals: Main (default), Cross-check (small, big) |
| Bing Webmaster Tools | Your account | Bing search data and your backlinks | Export reports | Free | The API (client to build): Main (default, small, big). Crawl methods: Cross-check (default, small, big). Positions: Cross-check (default), Main (small, big). Keyword API: Cross-check (default), Reserve (small, big). AI Performance export: Reserve, use when a person exports it |
| Google Keyword Planner | Your account | Search volume ranges | Export the shortlist's volumes | Free with a Google Ads account | Reserve |
| Google Business Profile, Merchant Center | Your account | Local and shopping visibility | Share exports or read-only access | Free | Main in every list where they apply (Business Profile client to build) |
| IndexNow | Your account | Telling Bing, Yandex and others that a page changed | Host a key file at your site's root | Free | Main in every list (submitter to build) |
| Live search results | Web | Who ranks, what the results page shows, People Also Ask | Nothing | Free on a Claude subscription; an API-key run pays Anthropic's web search fee (up to 8 searches a call) | WebSearch samples: Main (default), Cross-check (small, big) |
| ChatGPT, Perplexity, Google AI Overviews and AI Mode, Copilot, Claude, Gemini | Web | Whether AI answers mention or cite you | Nothing, or collect answers yourself | Free stack: GA4 AI referrals and SerpApi Free. Paid: official APIs through `ai_probe.py`; DataForSEO SERP and AI Mode for Google AI answers ([Main stack](#main-stack)) | `ai_probe.py`: Main (small, big), Reserve (default). Checks by hand: Reserve. Never automated in the apps |
| Wayback Machine | Web | Old versions of pages | Nothing | Free | Cross-check in every list; Reserve for a site move |
| Rich Results Test, Schema Markup Validator | Web (by hand) | A final check of structured data | Run them yourself | Free | Reserve |

## Main stack

The ranked core of tools that lets a run do SEO end to end with no person in the loop once credentials are given. The
full tables are in [references/tools.md](references/tools.md#main-stack): why each tool is there, how a run drives it,
what it costs a month, what each cross-check compares, and the condition for every Reserve tool.

- **Main:** in the ranked core stack for that list (the default free stack, or the paid list for that site size).
- **Cross-check:** runs alongside a Main tool because it measures the same thing differently. Agreement raises
  confidence. Disagreement sends the item to a re-check before the run acts on it.
- **Reserve:** a good tool that is not in the stack, brought in under a stated condition ("use when …").
- **(to build):** the vendor's route is official and allowed for unattended runs, but seo-suite has no client for it
  yet, or the credit guard can't price it yet.
- **(through claude-seo):** run by `scripts/claude_seo.py` with claude-seo's own tools, installed on first use.

**Default: big website, free only.** Every run starts here, at every site size: the most thorough stack that costs
$0. The page count sets only its depth: up to 2,000 URLs the run covers every URL, and above that it works in
sections and samples. Free means $0 to run. API keys for free quotas (PageSpeed Insights, CrUX, Search Console, Bing
Webmaster Tools) count as free; pay-per-call APIs (OpenAI, Anthropic, Perplexity, DataForSEO) don't. The small and big
paid lists below take over only when budgets or credentials for paid tools are set, or when you ask. The full tables,
quotas, billing-account notes and what free can't answer are in
[references/tools.md](references/tools.md#default-big-website-free-only).

- **Keywords and competitors**
  1. Research store (`research_store.py`).
  2. Search Console API (through claude-seo): measured demand per query, page and country.
  3. Search Console bulk export to BigQuery: needs a Cloud project with billing, $0 within BigQuery's free tier.
  4. WebSearch samples (`seo-serp-researcher`): who wins each head term, and People Also Ask. At most 200 searches per
     session (per turn in `claude -p`); $0 on a Claude subscription.
  5. Competitor sitemap inventory (to build: polite mode): what competitors publish.
  6. `compare_pages.py`: our page against the pages that win.
  7. CrUX popularity rank (BigQuery, with a card on the project): each competitor's size band.
- **Backlinks**
  1. Bing Webmaster Tools API (to build): Bing's own sample of our links.
  2. Ahrefs `domain-rating-free` (to build): Domain Rating for up to 1,000 targets a call, at 0 units.
  3. Common Crawl web graph (to build: graph reader): who links to competitors, at domain level.
- **Technical**
  1. `crawl.py`: the whole site, or per section above 2,000 URLs.
  2. `sitemap_check.py`: the URL inventory that sets the depth.
  3. `robots_check.py`: robots.txt and the AI-bot matrix, also before deploy.
  4. `page_audit.py`: one URL per template, and the CI gate.
  5. `redirect_check.py`: redirect maps and shipped redirect fixes.
  6. `schema_rules.py`: Google's rich-result rules.
  7. CrUX API and History API (to build): real-user Core Web Vitals.
  8. `render_diff.py`: what changes after JavaScript.
  9. claude-seo's renderer (`claude_seo.py render`): the rendered DOM in scheduled runs; headless Chrome only when
     claude-seo can't be set up.
  10. `log_analyze.py`: what bots actually fetch.
  11. Chrome DevTools MCP: traces behind a poor INP or LCP.
  12. IndexNow (to build): changed URLs to Bing, Yandex and others.
- **Rank and AI answers**
  1. Search Console API (through claude-seo): our own positions and clicks.
  2. Search Console bulk export to BigQuery.
  3. SerpApi Free (to build: collector): 250 Google rank snapshots a month for the money tier, with AI Overview and
     AI Mode.
  4. GA4 AI-referral sessions: the free AI-answer signal.
  5. Google Search Status Dashboard feed: dates of Google updates.
- **Measurement, local and indexing**
  1. Search Console API (through claude-seo): Search Analytics, URL Inspection, sitemap submission.
  2. Search Console bulk export to BigQuery.
  3. Google Analytics 4 (`analytics-mcp`).
  4. Bing Webmaster Tools API (to build).
  5. IndexNow (to build).
  6. Google Business Profile APIs (to build: client): local businesses only, after Google approves access.
  7. Merchant API: stores only.
  8. Google Search Status Dashboard feed (shared with Rank).
- **Cross-checks:** Google suggestions against Search Console queries, Bing suggestions, the Bing keyword API (to
  build) and the Wayback Machine for keywords. Moz API Free and a live `page_audit.py` check for links. URL Inspection
  (through claude-seo) against `crawl.py` and the sitemap, technical drift (through claude-seo) against each URL's
  baseline, `psi.py` lab against CrUX field, and Bing crawl data (to build) for technical. Bing Webmaster positions (to
  build) against Search Console for rank. Microsoft Clarity for measurement.

**Size.** Small is up to 2,000 indexable URLs: the sitemap total across every locale folder, subdomain and ccTLD. Big
is more. Markets, competitors, keywords and locations multiply the costs but don't change the class.

**Small sites, paid.** Main costs about $15–20 a month, pay per use, with no subscription.

- **Keywords and competitors**
  1. Research store (`research_store.py`): reuse, gaps, a source and date for every value.
  2. Search Console API (through claude-seo): measured demand per query, page and country.
  3. DataForSEO Google Ads volumes: Google's numbers, exact for Georgia and its cities.
  4. DataForSEO SERP API: who wins each keyword, SERP features, People Also Ask.
  5. DataForSEO Google Autocomplete: keyword ideas through an official API.
  6. SE Ranking Data API (to build: guard prices): competitor keywords and gaps, with a Georgia database.
  7. `compare_pages.py`: our page against the pages that win.
- **Backlinks**
  1. DataForSEO Backlinks API: new and lost links, the link gap, prospect scoring.
  2. Bing Webmaster Tools API (to build): Bing's own sample of our links, free.
- **Technical**
  1. `crawl.py`: the whole site, raw HTML.
  2. `sitemap_check.py`: the URL inventory that sets the size class.
  3. `robots_check.py`: robots.txt and the AI-bot matrix, also before deploy.
  4. `page_audit.py`: one URL per template, and the CI gate.
  5. `redirect_check.py`: redirect maps and shipped redirect fixes.
  6. Search Console URL Inspection API (through claude-seo): Google's index verdict per URL.
  7. `schema_rules.py`: Google's rich-result rules.
  8. `psi.py`: Lighthouse lab audits.
  9. CrUX API and History API (to build): real-user Core Web Vitals.
  10. `render_diff.py`: what changes after JavaScript.
  11. claude-seo's renderer (`claude_seo.py render`): the rendered DOM in scheduled runs; headless Chrome only when
      claude-seo can't be set up.
  12. `log_analyze.py`: what bots actually fetch.
  13. Chrome DevTools MCP: traces behind a poor INP or LCP.
  14. IndexNow (to build): changed URLs to Bing, Yandex and others.
- **Rank and AI answers**
  1. Search Console API (through claude-seo): our own positions and clicks.
  2. DataForSEO Google organic SERP API: rank snapshots, competitors, AI Overview citations.
  3. `ai_probe.py`: ChatGPT, Claude and Perplexity answers through their official APIs.
  4. DataForSEO Google AI Mode API: AI Mode answers and citations (no Georgian).
  5. Bing Webmaster Tools API (to build): Bing positions, all markets.
  6. Google Search Status Dashboard feed: dates of Google updates.
- **Measurement, local and indexing**
  1. Search Console API (through claude-seo): Search Analytics, URL Inspection, sitemap submission.
  2. Google Analytics 4 (`analytics-mcp`): what organic visitors do and whether they convert.
  3. Bing Webmaster Tools API (to build): Bing's own data.
  4. IndexNow (to build): the run tells the engines itself.
  5. Google Business Profile APIs (to build: client): local businesses only, after Google approves access.
  6. Merchant API: stores only.
  7. DataForSEO Google Maps geo-grid: map-pack rank, local businesses only.
  8. Google Search Status Dashboard feed (shared with Rank).
- **Cross-checks:** DataForSEO Labs (markets it covers, not Georgia), Bing suggestions from `keyword_ideas.py`,
  competitor sitemaps (to build), WebSearch samples and the Wayback Machine for keywords. Moz API Free, Ahrefs
  `domain-rating-free` (to build) and a live `page_audit.py` check for links. Bing crawl data (to build), DataForSEO
  On-Page and technical drift (through claude-seo) for technical. SerpApi Free (to build: collector) and GA4 AI
  referrals for rank. Microsoft Clarity for measurement.

**Big sites, paid.** Main costs about $140–200 a month, with Screaming Frog as the only licence. Main + Cross-check
is about $400–710, with Ahrefs Standard as the one SEO subscription.

- **Keywords and competitors**
  1. Research store.
  2. Search Console API (through claude-seo).
  3. Search Console bulk export to BigQuery, read through Google's BigQuery MCP.
  4. DataForSEO Google Ads volumes.
  5. DataForSEO SERP API.
  6. SE Ranking Data API (to build: guard prices): the Georgian and non-Labs markets.
  7. DataForSEO Labs: the markets it covers.
  8. DataForSEO Google Autocomplete.
  9. `compare_pages.py`.
- **Backlinks**
  1. DataForSEO Backlinks API.
  2. Bing Webmaster Tools API (to build).
- **Technical**
  1. Screaming Frog SEO Spider (licensed), through its command line.
  2. `crawl.py` per section, until a Screaming Frog adapter feeds `triage.py`.
  3. `sitemap_check.py`.
  4. `robots_check.py`.
  5. `log_analyze.py`.
  6. Search Console URL Inspection API (through claude-seo): changed URLs and samples.
  7. CrUX API and History API (to build).
  8. `psi.py`.
  9. `page_audit.py`.
  10. `redirect_check.py`.
  11. `schema_rules.py`.
  12. `render_diff.py`.
  13. claude-seo's renderer (`claude_seo.py render`).
  14. Chrome DevTools MCP.
  15. IndexNow (to build).
- **Rank and AI answers**
  1. Search Console API (through claude-seo).
  2. Search Console bulk export to BigQuery.
  3. DataForSEO Google organic SERP API.
  4. `ai_probe.py`.
  5. DataForSEO Google AI Mode API.
  6. Bing Webmaster Tools API (to build).
  7. Google Search Status Dashboard feed.
- **Measurement, local and indexing**
  1. Search Console API (through claude-seo).
  2. Search Console bulk export to BigQuery.
  3. Google Analytics 4.
  4. Bing Webmaster Tools API (to build).
  5. IndexNow (to build).
  6. Google Business Profile APIs (to build: client; local businesses only).
  7. Merchant API (stores only).
  8. DataForSEO Google Maps geo-grid (local businesses only).
  9. Google Search Status Dashboard feed.
- **Cross-checks:** Ahrefs API v3 through REST, to build (backlinks, Rank Tracker, Brand Radar with Claude, AI Overview
  and AI Mode data only, and keyword difficulty), SE Ranking in Labs markets, DataForSEO Clickstream, the CrUX
  popularity rank, Bing suggestions, competitor sitemaps, WebSearch samples and the Wayback Machine. Ahrefs
  `domain-rating-free` (to build) and a live `page_audit.py` check for links. DataForSEO On-Page, Bing crawl data and
  technical drift (through claude-seo) for technical. DataForSEO Bing SERPs and GA4 AI referrals for rank. Local
  Falcon (local) and Microsoft Clarity for measurement.

Semrush, Moz for big sites, SerpApi Free for big sites (use when there is no Ahrefs plan), Similarweb, AlsoAsked,
Yext and the person-assisted exports (the Search generative AI report, the Links report and Bing's AI Performance
report) are Reserve. In the default free stack, every paid tool is Reserve, brought in when its budget or credentials
are set or you ask.

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
- **Some actions always need your OK,** whatever the autonomy level: messages to real people, disavow files,
  deleting pages that earn traffic, Change of Address, DNS and CDN changes, Google Business Profile and Merchant
  Center edits, and spending above budget. The run prepares each one exactly and lists it at the end; Claude carries
  out the items you approve. Buying reviews or ranking links, and anything a vendor's terms forbid, are never done.
  The full list is in [references/autonomy.md](references/autonomy.md).

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
  - Ahrefs' terms forbid scripted use of its MCP server, so Ahrefs' MCP is used only in sessions you are watching.
    Scheduled runs reach Ahrefs only through the REST v3 client (to build:
    [build order](#planned-not-built-yet) item 8), for `domain-rating-free` and the big-site cross-checks,
    never through the MCP. Until that client exists, scheduled runs use DataForSEO for links and rankings.
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

- **The default free stack needs no budget.** It makes no paid calls, so every budget can stay at 0.
- **The paid stacks:** use the Small or Big values in
  [references/tools.md](references/tools-paid.md#credit-guard-limits). `dataforseo_monthly_usd` is 25
  small and 270 big. `other_monthly_usd` is 12 small and 35 big, for SE Ranking and `ai_probe`, after the credit guard
  changes listed there. `ahrefs_monthly_units` is 0 small, and up to 320,000 of Ahrefs Standard's 800,000 big, read
  by the REST client.
- **Semrush is Reserve.** Leave `semrush_monthly_units` at 0 unless you already pay for a plan. Then use up to 20,000
  of the 50,000 units it includes.
- **Today:** the scheduled pipelines in the seo-automation skill cost about $5–6 a month in DataForSEO for one site.

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
- AlsoAsked has an official MCP server at `https://alsoasked.com/mcp`, with a browser sign-in, on the Pro plan only
  (its REST API is Pro only too). Add it as `claude mcp add --transport http --scope user alsoasked
  https://alsoasked.com/mcp`, then `claude mcp login alsoasked`, so the guard recognises the name.

More detail: [references/paid-tools-automation.md](references/paid-tools-automation.md).

## Autonomy levels: what Claude may change

By default Claude only reads and reports. To allow more, set the `autonomy_level` option with
`/plugin configure seo-suite@seo-suite`:

| Level | What Claude does without asking |
|---|---|
| **1. Analyse** (default) | Reads only: fetches, crawls, free tools, paid calls within budget, reports |
| **2. Fix in code** | Level 1, plus edits to your site's code on a separate branch, sent as a pull request |
| **3. Ship** | Level 2, plus merging pull requests that pass CI, and submitting sitemaps and IndexNow for changed URLs |
| **4. Operate** | Level 3, plus publishing to a CMS and Search Console sitemap submission through an authorised connector |

Anything above your level waits for your OK. No level covers requesting indexing in Search Console, so that always
needs your OK. Some actions always need you, whatever the level (see [Rules](#rules-every-integration-follows)).
Details: [references/autonomy.md](references/autonomy.md).

## Your own data: Google, Bing and your business accounts

| Source | How seo-suite gets the data | Notes |
|---|---|---|
| **Google Search Console** | The Search Console API through claude-seo once you sign in: `claude_seo.py gsc-export` writes the same CSV an export gives, `claude_seo.py run gsc_inspect.py` checks URLs, and at autonomy level 4 `claude_seo.py submit-sitemap` submits a sitemap. Sign in once in a terminal: `python3 <plugin-dir>/scripts/claude_seo.py google-signin --client-secret client_secret.json`, with an OAuth client (type Desktop app) from a Google Cloud project with the Search Console API enabled. It asks only for `webmasters.readonly`; add `--sitemap-write` for `webmasters`, which level 4 needs. A service account an owner adds as a property user works too (`GOOGLE_APPLICATION_CREDENTIALS`). Without a sign-in: your exports (Performance → Export), read by `gsc_analyze.py`. Or Claude works in Search Console itself in the built-in browser or Claude in Chrome, signed in as you. With the Ahrefs connector, its `gsc` tools also read Search Console data at 0 units (except `gsc-anonymous-queries`), in sessions you watch | Google publishes no Search Console MCP server. With access set up (OAuth, or a service account added as a property user), the Search Console API gives up to 25,000 rows per request and the URL Inspection API 2,000 checks a day per site. An OAuth app left in *Testing* status gets refresh tokens that expire after 7 days, which breaks scheduled runs: publish the app, or use a service account. For big sites, have an owner turn on the bulk export to BigQuery early: it needs Google Cloud billing and has no row cap, but does not backfill. The Search generative AI report has no API, so it is exported in the browser. **Data warning:** a Google logging error made impressions, CTR and average position unreliable from 2025-05-13 to 2026-04-27 (clicks were not affected), so don't compare those metrics across that window ([Google's notice](https://support.google.com/webmasters/answer/6211453)) |
| **Google Analytics 4** | Google's official `analytics-mcp` server, which you add yourself after signing in with `gcloud` | Read-only unless started with `--allow-write`. The plugin never adds that flag |
| **Bing Webmaster Tools** | Performance exports, which `gsc_analyze.py` reads by matching Bing's column names to Search Console's. Or Bing's API, with a key from Settings → API Access, through a community MCP server you choose to trust | The plugin has no built-in Bing API client. Bing powers Copilot, so its data matters for AI search too |
| **Google Keyword Planner** | Your export (a UTF-16 CSV), read by `research_store.py ingest volumes`, which keeps ranges such as "1K – 10K" as written | Ranges unless the Ads account spends. The same command reads Semrush, Ahrefs and DataForSEO volume exports. Google's official Google Ads MCP has no Keyword Planner |
| **Google Business Profile** | An authorised connector, or exports and screenshots from the owner. The public listing is read with web search | Performance (searches, calls, directions, website clicks) needs owner access. The Business Profile API needs Google's approval. Profile edits always need your OK, and business.google.com is never automated |
| **Bing Places, Apple Business** | The owner's dashboards | Listing corrections are exact items in the end-of-run approval batch. The owner applies them, because Bing Places and Apple Business have no public API for it |
| **Google Merchant Center** | Read-only, through a connector or an export: diagnostics, the feed source and a sample of about 20 top products | Feed data overrides page markup, so seo-ecommerce checks that feed, page and markup match. Edits always need your OK |
| **IndexNow** | Changed URLs are submitted at autonomy level 3 or higher. First the site must serve a key (8–128 letters, digits or dashes) as a UTF-8 text file `{key}.txt` at its root. seo-suite has no IndexNow setting, so the key file is part of the site | Up to 10,000 URLs per request. Reaches Bing, Yandex, Seznam, Naver, Yep and others. Google does not use IndexNow |
| **Cloudflare AI Crawl Control** | Read in your Cloudflare dashboard: Security Settings → Bot traffic → AI bot policies | With Bot Preference Sync on and an AI policy set to block, Cloudflare puts its own rules at the top of your robots.txt. They disallow Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot, Google-Extended, GPTBot and meta-externalagent, and add `Content-signal: search=yes, ai-train=no, use=reference`. `robots_check.py` evaluates the live file, so it sees these rules, but it doesn't yet say Cloudflare added them. Available on all plans |
| **Google Indexing API** | Not used | Only for JobPosting and livestream (BroadcastEvent) pages. It is not a way to get ordinary pages indexed |

Each source's label is in the [At a glance](#at-a-glance) table. The three it doesn't list are Reserve: Bing Places
and Apple Business, use when the owner corrects listings or exports insights; Cloudflare AI Crawl Control, use when
the site is on Cloudflare; and the Google Indexing API, use for JobPosting or BroadcastEvent pages only.

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

| Server | What it adds | Notes | Stack |
|---|---|---|---|
| Chrome DevTools MCP (official) | Performance traces (for example, the long tasks behind a poor INP) and a Lighthouse audit of your own pages. The audit has no performance category | `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`. Use it only on your own site | Main in every list |
| Microsoft Clarity MCP (official) | Your Clarity project's data | The project admin creates the token. 10 requests per project per day, covering the last 1–3 days, so run it as one fixed daily job | Cross-check in every list |
| Google Ads MCP (official) | Read-only Google Ads data | It has no Keyword Planner | Reserve: use when the site runs Google Ads |
| Bing Webmaster Tools, community (`zizzfizzix/mcp-server-bwt`) | Bing query and page stats | Uses your Bing API key. Third-party code | Reserve: use until the plugin's Bing client exists |
| Search Console, community (`AminForou/mcp-gsc`) | The Search Console API | OAuth or a service account. Third-party code holding your Search Console access: audit it and pin a version. Destructive tools are off by default | Reserve: use when claude-seo can't be set up on the machine (no git, or no Python 3.11–3.14) |

## Public web sources

- **Live search results.** The `seo-serp-researcher` agent uses Claude's own web search and page fetch tools. It
  collects the top 10 results, page types, results-page features and People Also Ask questions. These are not
  Google's own results. For exact Google positions, use Search Console or DataForSEO.
- **AI answers.** A frozen set of questions is asked 3–5 times per engine (ChatGPT, Perplexity, Google AI Overviews
  and AI Mode, Copilot, Claude, Gemini), and the answers are logged for `ai_visibility.py`, which reports mention and
  citation rates with confidence intervals.
  - Only you check the apps, by hand. Claude never drives chatgpt.com, perplexity.ai, gemini.google.com, claude.ai or
    Copilot. The [Main stack](references/tools-paid.md#rank-and-ai-answer-visibility) keeps these manual checks as
    Reserve: 5 prompts before the first client report, logged as surface "app".
  - Today, the AI-visibility pipeline (B8) in the seo-automation skill still samples weekly through the DataForSEO
    connector with DataForSEO's LLM Scraper (about $0.18 a week for 25 questions × 2 engines × 3 runs), and adds LLM
    Mentions monthly. This conflicts with the Main stack's rule: the LLM Scraper collects its answers from
    chatgpt.com and gemini.google.com, so they aren't stored for analysis, and of LLM Mentions only the `google`
    platform data qualifies. The pipeline is to move to `ai_probe` ([build order](#planned-not-built-yet)
    item 5).
  - The [Main stack](#main-stack) keeps the LLM Scraper as Reserve, only for a one-off parity check of a few prompts
    that the owner explicitly approves, labelled "vendor-scraped" and kept out of trend lines. `ai_probe.py`,
    which uses the engines' official APIs, is the Main route.
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

  Scheduled runs never use Ahrefs' MCP: they reach Ahrefs only through the REST v3 client (to build: build order
  item 8). A `claude -p` run can't do an OAuth sign-in, so finish every sign-in first.
- **Permission rules.** seo-automation proposes allow, ask and deny rules for the connected vendors' free and read-only
  tools. Paid tools stay unlisted, so the credit guard decides. After your one-time OK, it merges the rules into
  `~/.claude/settings.json`, because a plugin can't ship them itself. Scheduled runs set
  `--permission-mode dontAsk` and list exactly the tools they need in `--allowedTools`.
- **Git, GitHub and CI.** From autonomy level 2, fixes go to the site's repo as a branch and pull request, opened with
  `git` and `gh`. From level 3, pull requests that pass CI can be merged. seo-technical can also add a CI job that
  downloads each key template's preview HTML and runs the page audit on it, failing on high-severity findings. A
  protected Vercel preview needs the `x-vercel-protection-bypass` header, with the secret stored in CI.
- **Your CMS and Search Console (level 4).** At autonomy level 4, Claude publishes to your CMS and submits sitemaps in
  Search Console through a connector you have authorised. Below level 4, the run finishes everything up to its level
  and says which level or credential would finish the job (for example, at level 2 the pull request is open, and
  level 3 merges it).

## Which source answers which question

The free column gives the default free stack's Main tools, and the paid column the paid lists' Main tools. Both note
their cross-checks. Ranks are in the [Main stack](#main-stack); every Reserve condition is in
[references/tools.md](references/tools.md#main-stack).

| Question | Free source | Paid, when free isn't enough |
|---|---|---|
| Broken pages, redirects, titles, canonicals, duplicates | `crawl.py` (per section above 2,000 URLs), `sitemap_check.py`, `page_audit.py`, `redirect_check.py` | Big sites: Screaming Frog (licensed CLI). Cross-check: DataForSEO On-Page, a second crawl from other IPs |
| Is content there only after JavaScript runs? | `render_diff.py`, with the DOM from claude-seo's renderer (`claude_seo.py render`) | Big sites: Screaming Frog renders whole sections. Cross-check: DataForSEO On-Page with JavaScript or browser rendering |
| Speed and Core Web Vitals, yours or a competitor's | CrUX API and History API (to build) for field data, and Chrome DevTools MCP traces. Cross-check: `psi.py` lab audits | — (the paid lists use the same free tools, with `psi.py` as Main) |
| Structured data | `page_audit.py` and `schema_rules.py`. The Rich Results Test by hand is Reserve | Big sites: Screaming Frog's structured-data validation. Cross-check: DataForSEO On-Page microdata errors |
| Your own queries, clicks and positions | Search Console API through claude-seo (`claude_seo.py gsc-export`, 16 months of data) and the bulk export to BigQuery (needs Cloud billing). Without a sign-in: exports → `gsc_analyze.py` | — |
| How bots crawl your site | `log_analyze.py` on your access logs. Cross-check: Bing Webmaster crawl data (to build) | — |
| Keyword ideas | Search Console queries and WebSearch samples (People Also Ask). Cross-check: `keyword_ideas.py` Google and Bing suggestions (no volumes) | DataForSEO Google Autocomplete. Cross-check: Bing suggestions |
| Search volume and difficulty | Search Console impressions (measured demand, not volumes). Cross-check: Bing keyword API counts (to build) | DataForSEO Google Ads volumes; difficulty from SE Ranking (to build) and, outside Georgia, DataForSEO Labs (Main on big sites, a cross-check on small). Big cross-checks: Ahrefs Standard and DataForSEO Clickstream |
| Competitors' keywords and traffic | Competitor sitemap inventory (to build), WebSearch samples, `compare_pages.py`, and the CrUX popularity rank for each competitor's size band | SE Ranking Data API (to build), and DataForSEO Labs outside Georgia (Main on big sites, a cross-check on small). Big cross-checks: Ahrefs Standard, and SE Ranking in Labs markets |
| Your own backlinks | Bing Webmaster Tools API (to build). Cross-checks: Moz API Free and a live `page_audit.py` check. Ahrefs Free and the Search Console Links report are Reserve, exported by a person | DataForSEO Backlinks API. Big cross-check: Ahrefs Standard |
| Competitors' backlinks | Common Crawl web graph (to build), domain level, and Ahrefs `domain-rating-free` (to build) for authority | DataForSEO Backlinks API. Big cross-check: Ahrefs Standard |
| Rank tracking | Search Console positions, and SerpApi Free (to build) snapshots for the money tier. Cross-check: Bing Webmaster positions | DataForSEO Google organic SERP snapshots for competitors and other locales. Cross-checks: SerpApi Free (small), Ahrefs Rank Tracker (big) |
| Visibility in AI answers | GA4 AI-referral sessions, and SerpApi Free for AI Overview and AI Mode. Checks by hand are Reserve | `ai_probe.py` and DataForSEO Google AI Mode and AI Overview. Big cross-check: Ahrefs Brand Radar's Claude, AI Overview and AI Mode data |
| What a page looked like before | Wayback Machine CDX API (a Cross-check for competitor history) | — |

## What to connect, by budget

| Budget | Stack |
|---|---|
| $0/mo | Search Console, Bing Webmaster Tools, GA4, a PageSpeed key, Ahrefs Free, Screaming Frog free mode, and seo-suite's scripts. For unattended runs this is the [default free stack](#main-stack) |
| ~$130–200/mo | Add **one** of Ahrefs Lite ($129, for link-heavy work) **or** Semrush Starter ($199) (for keyword- and competitor-heavy work; the $139 SEO plan lists no MCP access, so a run can't use it), plus a $50 DataForSEO top-up for bulk volumes and search results, which lasts months at the scheduled pipelines' few dollars a month |
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
| Search Console | An OAuth client (Desktop app) from your Google Cloud project, for `claude_seo.py google-signin`; or a service account that an owner adds as a property user | claude-seo keeps the token in `~/.config/claude-seo/oauth-token.json` (owner-only permissions) and the client's path in `~/.config/claude-seo/google-api.json`. A service account goes in `GOOGLE_APPLICATION_CREDENTIALS` |
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
| GitHub, PyPI and Playwright's download host | The git clone and pull of claude-seo, its Python packages and Chromium. Nothing about your sites | The first time `claude_seo.py` runs, a pull before every use, and a new setup when claude-seo's requirements change |
| Anthropic | Everything Claude reads or writes in the session, as for any Claude Code use | Always |

The credit guard's ledger and cache, the research store and the work log are local files. The research store goes
further only if you commit it to a repo.

## Check your setup

- **Servers:** `claude mcp list` shows each server. One that needs signing in again shows as failed.
- **Balances, free:** Ahrefs `subscription-info` (0 units), DataForSEO `appendix/user_data`, and Semrush
  `countapiunits` (API-key route only).
- **Credit guard:** `/hooks` shows it on PreToolUse, PostToolUse, PostToolUseFailure and PostToolBatch, plus the
  SessionStart hook for the PageSpeed key, and the schema check on PostToolUse Edit|Write.
- **claude-seo:** `python3 <plugin-dir>/scripts/claude_seo.py ensure --browser` installs or updates it and prints the
  commit and whether Chromium is ready. It fails with the reason when git, Python 3.11–3.14 or the network is missing.
- **Cache:** repeat one paid call. The second answer comes from the cache and costs nothing.
- **Before scheduling:** finish every sign-in with `/mcp` or `claude mcp login <name>`, and the Search Console sign-in
  with `claude_seo.py google-signin`, because a `claude -p` run cannot do OAuth. Run `claude_seo.py ensure --browser`
  once too, so the first scheduled run doesn't spend minutes on claude-seo's setup.

## Advice only: not connected

The docs explain what these are for and when they are worth paying for, but the plugin has no connection to them.
The Stack column gives each one's label in the [Main stack](#main-stack); every Reserve condition is in
[references/tools.md](references/tools.md#main-stack).

| Tool | What the docs say it is good for | Stack |
|---|---|---|
| Moz | Domain Authority, Page Authority and Spam Score, when someone reports in them. Moz has an official MCP server, in beta on paid API plans for account owners (`https://api.moz.com/mcp/v1/data`, OAuth or a Bearer API key). The plugin hasn't wired it, and the credit guard doesn't recognise Moz. In the [Main stack](#main-stack) the free API tier is a backlink cross-check for small sites | API Free tier: Cross-check (default and small backlinks). Big sites and Moz Pro: Reserve |
| Majestic | Trust Flow and Citation Flow. API on its API plan only, no MCP | Reserve |
| SpyFu | Historical paid-search and competitor ads | Reserve |
| AnswerThePublic | Question and phrase lists. No API listed | Reserve |
| Google Trends | Relative interest over time. Its API is in alpha | Reserve |
| Ahrefs Brand Radar, Semrush AI Visibility, Peec AI, Profound | Paid trackers of brand mentions in AI answers | Brand Radar: Cross-check (big, paid, to build). The others: Reserve |
| Semrush Sensor | Algorithm volatility, to see whether a drop is industry-wide (free page) | Reserve |
| Looker Studio | Free dashboards on Search Console and GA4 | Reserve |
| Ahrefs Free (formerly Ahrefs Webmaster Tools) | Your own site's backlinks and audit, in its own interface | Reserve |
| Screaming Frog free mode | Crawling up to 500 URLs, to cross-check the plugin's crawler | Reserve |
| Screaming Frog Log File Analyser | A desktop app for very large logs. `log_analyze.py` covers the core questions | Reserve |
| YouTube Studio, vidIQ, TubeBuddy | YouTube analytics and keyword tools for a channel strategy | Reserve |
| BrightLocal, Yext, Semrush Listing Management | Citation audits and listing distribution for multi-location businesses | Reserve |
| Local Falcon | Map-pack rankings on a grid of locations | Cross-check (big, paid, local businesses). Reserve (small) |
| Botify, Conductor | Enterprise crawling and SEO platforms | Reserve |

## Planned, not built yet

In build order, the items that unblock the most categories first:

1. Done: the **Search Console API** runs through claude-seo (`claude_seo.py gsc-export`, `run gsc_inspect.py`,
   `submit-sitemap`), with `webmasters.readonly` by default. It writes the same CSVs `gsc_analyze.py` reads, so
   mid-size sites aren't limited by the 1,000-row export.
2. A **Bing Webmaster Tools API client** for the query, page, link, crawl and keyword methods.
3. **Credit guard changes:** an SE Ranking price table and a budget per vendor, row limits per endpoint, and the
   missing price rows (AI Mode, Maps, Clickstream and others).
4. An **IndexNow submitter** that checks the key file before sending, since level 3 promises IndexNow.
5. Done: **`ai_probe.py`**, direct AI-answer checks through the official APIs of OpenAI, Anthropic and Perplexity: a fixed
   question set, several runs each, fed to `ai_visibility.py`. They use the APIs because OpenAI's terms forbid automated
   extraction from the ChatGPT app. API answers can differ from what the app shows. Gemini is Reserve: answers grounded
   with Google Search are never stored for analysis, because its terms forbid it, and the API without grounding is
   brought in only when GA4 shows gemini.google.com at 10% or more of AI-referral sessions for two months [heuristic].
   With it, `rank_snapshot.py` and `rank_compare.py` store fixed-condition positions and compare runs.
6. **CrUX LCP subparts and the full 40-week history** in `psi.py`, through the CrUX API and History API, using the
   same Google key.
7. A **polite competitor inventory:** competitor sitemap diffs that honour robots.txt, send one request at a time per
   host, and stop on 403, 429 or a challenge.
8. An **Ahrefs REST v3 client** for the big-site cross-checks and the free `domain-rating-free` endpoint.
9. A **Screaming Frog CSV adapter** for `triage.py` and the research store, and a **CDN log converter** for
   `log_analyze.py`.
10. A **SerpApi collector** for the Free plan's 250 searches a month.
11. A **Common Crawl graph reader** for the free domain-level link graph.
12. A **Google Business Profile client** for local businesses.

Also planned, outside that order:

- **Competitor modules:** share of voice and Wayback change history as scripts (competitor sitemap diffs are item 7).
  Today these are manual steps in the seo-competitors skill.

**Under consideration, not yet decided.** These came out of a review of other Claude Code SEO plugins (claude-seo,
geo-seo-claude, seomachine and the older seo-skills), keeping only ideas with evidence behind them. The review's
Search Console fetcher, IndexNow submitter and CrUX history are now items 1, 4 and 6 above.

- Done: a **crawl diff** between runs, which the weekly technical monitor needs, is `claude_seo.py drift` (claude-seo's
  drift rules, one snapshot per crawl run).

## How it works inside Claude Code

- **Hooks.** The plugin uses five hook events:
  - SessionStart exports `psi_api_key` as `PSI_API_KEY`, and the plugin's data folder as `SEO_SUITE_DATA`, where
    `claude_seo.py` keeps claude-seo.
  - PreToolUse, PostToolUse and PostToolUseFailure run the credit guard on the recognised vendors' MCP calls.
  - PostToolUse on Edit and Write also runs `schema_hook.py`: JSON-LD that doesn't parse, a leftover placeholder or an
    object without `@type` comes back to Claude as an error to fix; missing rich-result fields come back as advice.
    Other files are skipped at once.
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
