# seo-suite-dataforseo

An optional connector for seo-suite. It adds DataForSEO's official v3 MCP server: the npm package
`dataforseo-mcp-server`, pinned to 3.1.3 and run locally over stdio. Its tools appear as
`mcp__plugin_seo-suite-dataforseo_dataforseo__<tool>`.

The server has four tools:
- `docs_index`, `docs_list_sections` and `docs_search` are free.
- `api_request` calls any `api.dataforseo.com` endpoint.

DataForSEO is pay-as-you-go. The minimum top-up is $50, and the funds don't expire.

You need Node.js 22 or newer and `npx`. The first start downloads the package, which can take a moment.

## Set up (once)

1. Install the core plugin and this connector:
   `claude plugin install seo-suite@seo-suite` and `claude plugin install seo-suite-dataforseo@seo-suite`.
2. Enter the API credentials. In a Claude Code session, run `/plugin configure seo-suite-dataforseo@seo-suite` and
   fill in:
   - `dataforseo_login`
   - `dataforseo_password`

   Both come from the DataForSEO dashboard under API access. The API password is not your dashboard password.
   - Both values are masked and stored in the system keychain.
   - Don't pass them with `--config` on the command line, because they would land in your shell history.
   - Never paste them into the chat.
3. Set a daily spending limit at DataForSEO, which only you can do. Go to app.dataforseo.com/api-settings. Calls
   over the limit fail with error 40203, and the limit resets at 00:00 UTC.
4. Set a budget. Run `/plugin configure seo-suite@seo-suite` and set `dataforseo_monthly_usd`. A budget of 0 (the
   default) blocks every paid DataForSEO call.

If you would rather use OAuth than a password, add the hosted server yourself:
`claude mcp add --transport http dataforseo https://mcp.dataforseo.com/v3/mcp`, then `/mcp` → Authenticate. The credit
guard covers `mcp__dataforseo__*` and `mcp__dfs-mcp__*` too.

## What the credit guard does with DataForSEO

The guard is `scripts/credit_guard.py` in the core plugin.

- **Free calls.** These run without budget checks: the docs tools, `appendix/user_data` (your balance),
  `tasks_ready` and `task_get`.
- **Estimates.** Each `api_request` is estimated from its endpoint path (October 2026 prices):

  | Endpoint | Price |
  |---|---|
  | SERP, Standard queue | $0.0006 per 10 results |
  | SERP, Live | $0.002 per 10 results |
  | Google Ads volumes | $0.06 (Standard) or $0.09 (Live) per task of up to 1,000 keywords |
  | Labs | $0.012 + $0.00012 per item |
  | Backlinks | $0.024 + $0.000036 per row |
  | LLM Mentions | $0.1 + $0.001 per row |
  | On-Page | $0.00015 per page, plus JavaScript or browser-rendering add-ons |

  SERP surcharges: search operators cost five times as much each, priority 2 doubles the Standard price, and AI
  Overview loading or `calculate_rectangles` each add one base price.
- **Row limits.** The guard caps `limit`, `depth` and `max_crawl_pages` at `max_rows` (default 50). It also adds the
  limit when a list endpoint or On-Page crawl leaves it out.
- **Actual cost.** When a response shows its `cost`, the ledger records that figure instead of the estimate.
- **Batching.** Prefer the Standard queue (`task_post`, then free `tasks_ready` and `task_get`) for bulk work. It is
  3.3 times cheaper for SERPs, and posted tasks stay retrievable for 30 days. A cached `task_post` response gives the
  task ids to fetch again for free.

## Limits

- A Live endpoint takes one task per call; the MCP sends only the first task. Google Ads Live is limited to 12
  calls a minute.
- `api_request` only reaches `api.dataforseo.com`, so the free sandbox can't be used through the MCP.

See [the autonomy policy](../../references/autonomy.md) for what runs without asking.
