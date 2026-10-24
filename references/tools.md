# SEO tools: free first, paid when justified (prices checked 2026-10-24)

**Rule:** every seo-suite workflow must work on the free path. Recommend a paid tool only when it provides data
the free path *cannot* (third-party indexes, panels, scale). Say what it adds, run the cheapest call that answers the
question, and log units or credits spent in `SEO-WORKLOG.md`.

Prices change often. Figures marked [UNVERIFIED] came from third-party pages, not the vendor. Re-check the
vendor's pricing page before quoting a number to a client.

## Free tools

| Tool | Gives you | Limits / notes |
|---|---|---|
| **Google Search Console** | Your clicks, impressions, CTR, position by query/page/country/device · indexing (Pages report, URL Inspection) · sitemaps · Core Web Vitals · links (sample) · manual actions · "Search generative AI" setting and report (impressions only) | 16 months of data · UI export 1,000 rows · API 25k rows/request, 2,000 URL inspections/day/site |
| **Bing Webmaster Tools** | Same for Bing, which also feeds Copilot and much of ChatGPT search · backlinks (own site) · IndexNow · AI Performance report (citations; public preview) [3rd-party] | API key in BWT |
| **Google Analytics 4** | Conversions and engagement from organic traffic · landing pages | Organic queries come from GSC, not GA4 |
| **PageSpeed Insights / CrUX** | Real-user Core Web Vitals (p75, 28 days) and Lighthouse lab audits | Free API key raises the quota (`psi.py`) · CrUX API 150 QPM · History API up to 40 weeks |
| **Rich Results Test · Schema Markup Validator** | Google rich-result eligibility · full schema.org validation | Manual (no public API found) |
| **Google Keyword Planner** | Google Ads volumes | Ranges (e.g. 1K–10K) unless the account has sustained ad spend; threshold undisclosed |
| **Google Trends** | Relative interest over time and by region | API is alpha and application-only |
| **Ahrefs Free** (formerly Ahrefs Webmaster Tools) | For **your verified sites**: top 1,000 backlinks and keywords, site audit (5k crawl credits/project/month), web analytics | Verify the site first. The best free backlink view of your own domain |
| **Screaming Frog (free mode)** | Desktop crawler, 500 URLs | No JS rendering, custom extraction, API joins or saving crawls without a licence |
| **Looker Studio** | Free dashboards on GSC + GA4 | — |
| **Wayback Machine CDX API** | History of competitor and own pages ("what changed before the drop") | `web.archive.org/cdx/search/cdx?url=…&output=json` |
| **AlsoAsked free / Google PAA via search** | Question research | Paid AlsoAsked from $12/mo |
| **This plugin's scripts** | Crawl, page audits, robots/AI-bot matrix, sitemaps, CWV, autocomplete ideas, GSC/log analysis, redirect QA, content scoring, competitor gaps, render diff, SERP clustering, triage, AI-visibility stats | See `scripts.md` |

## Semrush

**Justified when** you need competitors' keywords and estimated traffic, country-level keyword volume and
difficulty at scale, PPC/ad intelligence, or market and traffic estimates. These come from Semrush's ranking database.
The free path cannot replicate them.

**Plans (monthly / annual per month):**
- Free: 10 reports/day.
- SEO: $139 / $117.33. 5 sites, 500 tracked keywords.
- Starter: $199 / $165.17. 50 AI prompts.
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
- **AI Visibility Toolkit:** $99/mo per user. 1 domain, 25 prompts, ChatGPT + Google AI Mode.
- **Traffic & Market:** $289/mo per user annually. The Trends API is a separate quarterly subscription.

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
- Free endpoints: Rank Tracker, Management, Public (`domain-rating-free`) and the GSC endpoints.
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

**Cost tactics:**
1. Select only the fields you need. Avoid `traffic`/`org_traffic` (10×) and `refdomains` (5×) in select, where
   and order_by unless they are the point.
2. Beat the 50-unit minimum by consolidating: Batch Analysis takes up to 100 targets per call.
3. Always `limit`. Estimate first on a free test target and read `x-api-units-cost-total`.
4. Own-site data is free: Ahrefs GSC endpoints (0 units), Ahrefs Free, verified projects (no row caps).
5. Cap OAuth/MCP keys at a monthly unit limit you chose.
6. Plan history is short on Lite (6 months): snapshot what you'll need later rather than re-pulling.
7. Spend the Brand Radar checks your plan includes before buying a pack.

## Screaming Frog

**Justified when** the site is larger than ~2,000 URLs or relies on JavaScript. The plugin's crawler is raw-HTML only
and best up to a few thousand pages. Screaming Frog adds Chromium rendering at scale, custom extraction,
crawl comparison, scheduling, and GSC/GA4/PSI joined per URL.

- **Licence:** £199/year per user (volume discounts down to £169) [USD ≈ $279 UNVERIFIED]. The free mode covers 500 URLs.
- **CLI:** headless with a `licence.txt` key file.
- **MCP:** v24.0 (May 2026) added an SEO Spider MCP server for Claude (crawl, analyse, export). List mode is not
  supported yet. Whether MCP needs a licence is [UNVERIFIED].

**Cost tactics:**
- One licence per person who actually crawls.
- Use the free mode to cross-check `crawl.py` on small sites.
- Link-metric integrations (Ahrefs, Majestic, Moz) spend *those* tools' API units. Enable them only for key URLs.
- Schedule crawls and compare runs automatically instead of recrawling by hand.

**Alternatives:**
- **Sitebulb:** Desktop Lite/Pro; Cloud from £95/mo; JS rendering included; MCP on every plan.
- **Lumar:** quote-only; official MCP at `mcp.lumar.io/mcp`.
- **Botify and Conductor:** enterprise.

## DataForSEO

**Justified when** you need raw data at the lowest unit cost, paying per use instead of subscribing:
- Bulk Google Ads volumes.
- SERP snapshots at scale, including AI Overview and AI Mode, for rank tracking or SERP-overlap clustering.
- Backlink data without a subscription.
- LLM mention/response data for AI visibility.

**Billing:** pay-as-you-go, $50 minimum top-up, and balances never expire. The $100/mo commitment for Backlinks and
LLM Mentions was removed on 2026-07-01.

**Prices:**

| API | Price |
|---|---|
| SERP (Google organic, per 10 results) | Standard queue $0.0006 · Priority $0.0012 · Live $0.002 |
| SERP extras | AI Overview load 2× · `site:`-style operators 5× · each PAA click $0.00015 |
| Keywords Data (Google Ads) | $0.06 per task of up to 1,000 keywords, Standard mode (≈ $60 per 1M keywords); Live $0.09 |
| Labs | $0.012 per task + $0.00012 per item |
| Backlinks | $0.024 per request + $0.000036 per row |
| On-Page | from $0.00015 per page |
| LLM Mentions | $0.10 per task + $0.001 per row |

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

All figures here are [UNVERIFIED]; moz.com blocked our fetch.
- **Moz Pro:** Starter $49, Standard $99, Medium $179, Large $299 per month (about 20% off annually).
- **Moz API:** sold separately. A small free tier of ~50 rows/month; paid from ~$20/mo.
- No official MCP was found.

**Cost tactics:**
- Use DA/PA only as a relative comparison. It is not a Google metric.
- Pull metrics for shortlisted prospects only, never whole link lists.

## Other paid tools

| Tool | Justified for | Price | API / MCP |
|---|---|---|---|
| **Majestic** | Trust Flow / Citation Flow, topical link graphs | Lite $49.99 · Pro $99.99 · API $399.99/mo | Full API on the API plan only; no MCP |
| **SE Ranking** | Cheaper all-in-one rank tracking + audit + AI prompts | Core $129 · Growth $279/mo · standalone API from a $50 wallet | MCP on API tiers |
| **Similarweb** | Competitor traffic, sources, audience overlap (estimates) | Quote-only | MCP needs API, Business or Enterprise |
| **SpyFu** | Historical PPC / competitor ads | ~$39–$249/mo [UNVERIFIED] | — |
| **Keywords Everywhere** | Cheap volume/CPC overlay while browsing; small API jobs | From $84/yr for 100k credits (1 credit = 1 keyword volume) | API and MCP on all plans |
| **AlsoAsked** | People-Also-Ask question trees | From $12/mo | API and MCP on all plans |
| **AnswerThePublic** | Question/preposition idea lists | From $20/mo | No API listed |
| **Local Falcon / DataForSEO local** | Map-pack geo-grid rankings | Per-scan pricing | — |

## AI visibility trackers

**Justified when** you need repeated, automated prompt tracking across engines over time. The free method in
`seo-ai-search` (a frozen query set, 3–5 manual runs per engine, `ai_visibility.py` with confidence intervals) is enough
to *start*, and to decide whether a tracker is worth paying for.

| Tool | Price | Engines | API / MCP |
|---|---|---|---|
| Ahrefs Brand Radar | from $199/mo; prompt packs $50–$250 | AI Overviews, AI Mode, ChatGPT, Gemini, Perplexity, Copilot, Grok, Claude | API + MCP |
| Semrush AI Visibility | $99/mo per user (25 prompts); Semrush One bundles 50–200 | ChatGPT, Google AI Mode | — |
| Otterly.AI | Lite $29 (15 prompts) · Standard $189 (100) · Premium $489 (400) | ChatGPT, AI Overviews, Perplexity, Copilot (+AI Mode, Gemini, Claude as add-ons) | API + MCP from Standard |
| Profound | Enterprise; 7-day trial | up to 9 engines | Enterprise |
| Peec AI | prices not shown on vendor page [UNVERIFIED ~€89+] | ChatGPT, Perplexity, Gemini | API, MCP |
| DataForSEO LLM Mentions / Responses | pay per task | ChatGPT, AI Overviews (Mentions); ChatGPT, Claude, Gemini, Perplexity (Responses) | API + MCP |

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

4. **Limit every call:** row limits, single country/database, only needed fields, no historical data unless asked.
5. **Estimate before running.** Ahrefs free test targets show the unit cost in headers; Semrush has the free
   `countapiunits` balance check; DataForSEO lists prices per task. Tell the user the expected spend for anything
   over ~$5 or 10k units, and get a yes first.
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
| $0/mo | GSC + Bing WMT + GA4 + PSI key + Ahrefs Free + Screaming Frog free + seo-suite |
| ~$150/mo | Add **one** of: Ahrefs Lite (links-heavy work) **or** Semrush SEO/Starter (keyword and competitor-heavy work), plus a $50 DataForSEO wallet for bulk volumes and SERPs |
| ~$500+/mo | Ahrefs Standard **or** Semrush Pro+, plus Screaming Frog licence, a DataForSEO wallet, and an AI tracker (Brand Radar or Otterly Standard) if AI visibility is a KPI |
