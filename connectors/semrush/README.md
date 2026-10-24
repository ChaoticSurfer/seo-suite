# seo-suite-semrush

An optional connector for seo-suite. It adds Semrush's official MCP server, `https://mcp.semrush.com/v2/mcp`, which
is read-only and signs in with OAuth. Its tools appear as `mcp__plugin_seo-suite-semrush_semrush__<tool>`.

Your Semrush plan must include API units:
- Semrush One Starter, Pro+ and the legacy Pro and Guru plans include 50,000 units per renewal.
- Advanced and Business plans need a units package.

MCP calls spend the same units as the API.

## Set up (once)

1. Install the core plugin and this connector:
   `claude plugin install seo-suite@seo-suite` and `claude plugin install seo-suite-semrush@seo-suite`.
2. Sign in. In a Claude Code session, run `/mcp`, choose `plugin:seo-suite-semrush:semrush`, and choose
   **Authenticate**. You complete the Semrush login in your browser. Claude never types your password.
3. Set a budget. Run `/plugin configure seo-suite@seo-suite` and set `semrush_monthly_units`. A budget of 0 (the
   default) blocks every paid Semrush call.

Never paste keys or passwords into the chat.

### API-key route (instead of OAuth)

Run this yourself in a terminal, with `SEMRUSH_API_KEY` already set in your shell:

```bash
claude mcp add --transport http semrush-key https://mcp.semrush.com/v2/mcp --header "Authorization: Apikey $SEMRUSH_API_KEY"
```

- The shell expands the variable, so the key is saved in your Claude Code MCP config (`~/.claude.json`). It is never
  stored in a project file.
- Its tools appear as `mcp__semrush-key__<tool>`, and the credit guard covers them.
- Use one route, not both. Two Semrush servers show every tool twice.

## What the credit guard does with Semrush

The guard is `scripts/credit_guard.py` in the core plugin.

- **Free calls.** The 12 discovery tools and `get_report_schema` run without budget checks. Semrush's own skills
  warn only before `execute_report`, but no Semrush document gives a price for these tools.
- **Row limits.** Every `execute_report` needs a row limit (`display_limit` or `limit`). Without one, a v3 report
  returns up to 10,000 lines at 10 to 80 units each. The guard caps the limit at `max_rows` (default 50). If the call
  has no limit at all, the guard denies it and tells Claude to read `get_report_schema` first.
- **Estimates.** Each call is estimated from Semrush's per-line and per-request prices. Historical data
  (`display_date`) costs five times as much. A report whose price the guard doesn't know is deferred, not run. It
  goes into the end-of-run questions, because some Site Audit methods cost 10,000 units per request.
- **Caching.** Results are cached for at most 30 days, as Semrush's terms require. An identical call inside that
  window is answered from the cache file at no cost.

## Limits

- The MCP is read-only. It can't create projects, start Site Audit crawls, or change Position Tracking campaigns. The
  UI or the direct Projects API (Business plan) does that, done by you.
- Some features exist only in the web UI: Keyword Strategy Builder, SEO Writing Assistant, Topic Research, Keyword
  Magic Tool groups, personal keyword difficulty, and Backlink Audit toxicity.
- Don't drive the Semrush web UI with a browser for data. Semrush's Terms (§3.3) forbid scraping, and forbid feeding
  Semrush output to AI except through official integrations. This MCP is the compliant route.
- Semrush allows 10 requests per second and 10 at once per account.

See [the autonomy policy](../../references/autonomy.md) for what runs without asking.
