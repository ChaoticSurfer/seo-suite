# SEO work log

Every seo-suite task ends by appending one entry to `SEO-WORKLOG.md` in the project root (create it if missing;
for a site with no repo, keep it in the working folder the user chose). Newest entry on top. The log is how the
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
