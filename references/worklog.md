# SEO work log

Every seo-suite task ends by appending one entry to the project's `SEO-WORKLOG.md`. Default location:
`project-reports/<project>/SEO-WORKLOG.md` inside the seo-suite folder (gitignored), next to that project's research
store (`project-reports/<project>/seo-research/`) and dated reports (`seo-research/research/`). This keeps project
repos untouched and nothing project-specific in the plugin's git history. Use the project root only if the user asks. Newest entry on top. The log is how the
next session — or the next person — knows what was checked, what changed, what it cost, and when to look again.

## Entry format

```markdown
## 2026-10-24 — <task, e.g. "Full technical audit of example.com">

- **Skill / level:** seo-audit · beginner|expert
- **Scope:** <URLs, templates, markets, date ranges>
- **Data sources:** <free: crawl.py (240 pages), PSI mobile (5 URLs), GSC export 28d> · <paid: Semrush 3,100 API units / Ahrefs 0>
- **Outputs:** <paths to JSON/CSV/report files>
- **Key findings:** <3–7 bullets with evidence tags [measured] [Google doc] [vendor data] [estimate]>
- **Changes made:** <files/commits/PRs, CMS edits — or "none (report only)">
- **Not verified / blocked:** <e.g. "Cloudflare challenge blocked crawl; GSC access not provided">
- **Decisions & assumptions:** <what the user chose, what we assumed>
- **Next steps:** <owner + action>
- **Re-check on:** <date, e.g. +14 days for indexing changes, +28 days for CTR tests, +90 days for content>
```

## Rules

- Write facts, not intentions: what ran, what it returned, what changed.
- Record paid usage (units/credits/rows) every time — it makes the next budget decision easy.
- Never paste secrets, API keys, customer personal data or full exports into the log; link file paths instead.
- When a later entry confirms or refutes an earlier one, say so ("Re-check of 2026-10-24: 38/40 redirects fixed").
- Changes are "coinciding with" metric moves, not "causing" them, unless a controlled test showed it.
