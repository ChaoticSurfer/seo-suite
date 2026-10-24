# seo-suite-ahrefs

An optional connector for seo-suite. It adds Ahrefs' official hosted MCP server, `https://api.ahrefs.com/mcp/mcp`,
which signs in with OAuth and needs the Lite plan or higher. Its tools appear as
`mcp__plugin_seo-suite-ahrefs_ahrefs__<tool>`.

The server URL turns on only the SEO tool groups:
- site-explorer-overview and site-explorer-reports
- keywords-explorer and serp-overview
- rank-tracker, site-audit and gsc
- batch-analysis, public and subscription-info

These groups are left out:
- Content Helper and Brand Radar, which are expensive.
- management, which holds the write endpoints.
- web-analytics and social-media.

MCP calls spend the same monthly API units as API v3. Lite includes 200,000 units a month and at most 100 rows per
request.

## Set up (once)

1. Install the core plugin and this connector:
   `claude plugin install seo-suite@seo-suite` and `claude plugin install seo-suite-ahrefs@seo-suite`.
2. Sign in. In a Claude Code session, run `/mcp`, choose `plugin:seo-suite-ahrefs:ahrefs`, and choose
   **Authenticate**. You log in, pick the workspace and click Allow in your browser.
3. Cap the key at Ahrefs, which only you can do:
   - The key that OAuth creates gets a default cap of 200,000 units a month, which is the whole Lite allowance.
     Lower it in Account settings → API keys.
   - Turn off pay-as-you-go units in Limits & usage, unless you want overage charged.
4. Set a budget. Run `/plugin configure seo-suite@seo-suite` and set `ahrefs_monthly_units`. A budget of 0 (the
   default) blocks every paid Ahrefs call.

Never paste keys or passwords into the chat.

## What the credit guard does with Ahrefs

The guard is `scripts/credit_guard.py` in the core plugin.

- **Free calls.** These cost 0 units and run without budget checks: rank-tracker, gsc (except
  `gsc-anonymous-queries`), subscription-info, public, management, web-analytics, social-media,
  `site-audit-projects` and `doc`.
- **Estimates.** A call costs max(50, rows × the sum of its unique field costs), counting fields in `select`,
  `where` and `order_by`.
  - Traffic, volume, difficulty, value and cost fields cost 10 units.
  - Referring-domain fields cost 5 units.
  - Most other fields cost 1 unit.
- **Row limits.** List endpoints return 1,000 rows by default. The guard adds a missing `limit`, or lowers a larger
  one, to `max_rows` (default 50).
- **Caching.** Results are cached for 30 days (keywords), 7 days (SERPs, domains and backlinks) or 1 day (site
  audits).

## Limits

- Ahrefs' MCP terms don't allow driving the MCP endpoint from custom scripts or bridges. Use it from Claude Code
  interactively. Scheduled or unattended jobs belong on REST API v3 with an API key, which this connector doesn't
  ship. Whether a headless `claude -p` run counts as a supported client is unverified.
- Ahrefs' Terms (4.4) forbid automated use of app.ahrefs.com except through the API. The site also sits behind a
  Cloudflare challenge. Don't drive the web UI.
- Ahrefs Free (formerly Webmaster Tools) data isn't reachable through the API or MCP. Free accounts can only use the
  public endpoints.
- The API can't start Site Audit crawls.

See [the autonomy policy](../../references/autonomy.md) for what runs without asking.
