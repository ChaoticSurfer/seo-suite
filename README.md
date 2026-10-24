# seo-suite

A Claude Code plugin that does SEO end to end, from a five-minute page check to a full audit, migration, or
AI-search visibility programme. It is built so the free path always works and paid tools are an upgrade
with a stated reason.

## What's inside

- **18 skills.** The `seo-suite` router plus audit, technical, onpage, content, keywords, schema,
  ai-search, local, international, ecommerce, media, links, migration, analytics, competitors,
  programmatic and strategy.
- **3 agents.** `seo-site-auditor` collects data, `seo-serp-researcher` runs SERP batches in parallel,
  and `seo-content-reviewer` grades pages.
- **15 scripts.** Python standard library only, no installs. They cover page audit, crawler, robots,
  sitemaps, PageSpeed/CrUX, keyword ideas, Search Console analysis, log analysis, redirect-map QA,
  content scoring, competitor comparison, render diff, SERP-overlap clustering, code-based triage (P0–P3) and AI-visibility
  statistics with confidence intervals.
- **References.**
  - `google-rules.md`: dated, verified Google and Bing rules, with an explicit list of unverified items.
  - `tools.md`: free and paid tools, why each paid tool is worth it, and how to spend less on it.
  - `guide-beginner.md` and `guide-expert.md`: the same SEO pillars at two depths. The router picks one
    for the user's level.
  - `worklog.md`: the `SEO-WORKLOG.md` entry format that every task appends to.

## Install

In Claude Code:

```
/plugin install seo-suite --marketplace ChaoticSurfer/seo-suite
```

Or from a terminal:

```bash
claude plugin marketplace add ChaoticSurfer/seo-suite
claude plugin install seo-suite@seo-suite
```

You need Python 3.9 or newer. The scripts use only the standard library, so there is nothing else to install.

## Use

Ask in plain words: "audit example.com", "why did traffic drop in September", "add Product schema",
"get us cited in ChatGPT", "teach me SEO". You can also call a skill directly: `/seo-suite:seo-audit`.

Scripts run on their own too:

```bash
python3 ~/.claude/skills/seo-suite/scripts/page_audit.py https://example.com/
```

## Tests

```bash
python3 -m unittest discover -s ~/.claude/skills/seo-suite/tests
```

`test_docs.py` fails if a skill references a script or flag that doesn't exist. `test_scripts.py` fails if
a script can emit a finding id that has no triage row.

## Read next

- [COMPARISON.md](COMPARISON.md): how this plugin compares with 11 other Claude Code SEO plugins, what it can't
  do, and which data only Semrush, Ahrefs or similar tools can provide.
- [references/tools.md](references/tools.md): free and paid tools, the case for each paid one, and how to
  keep the bill down.
- [references/guide-beginner.md](references/guide-beginner.md) and
  [references/guide-expert.md](references/guide-expert.md): SEO strategy at two depths.

## Manage

- Installed from the marketplace: `claude plugin disable seo-suite@seo-suite`, or
  `claude plugin uninstall seo-suite@seo-suite`.
- A local copy in `~/.claude/skills/seo-suite` loads automatically as `seo-suite@skills-dir`. Delete the folder
  to remove it.

## Licence

MIT
