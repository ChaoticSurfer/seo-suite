# Audit profiles: which stack an audit runs, and how deep

An audit runs one profile: a suite of tools from [tools.md](tools.md#main-stack) plus a depth. `seo-audit` picks it
with `scripts/audit_profile.py`, never with a question, records why under *Assumptions*, and carries on. The default is
the most thorough stack that costs $0, at every site size. Nobody has to name a profile, but anyone can: say "quick
check" or "use paid tools", or set the `audit_profile` plugin option. The script is the source of truth for every
table here. If the two disagree, fix one of them.

## 1. Profiles

| id | Label | When it applies | Suite (tools.md) | Cross-checks |
|---|---|---|---|---|
| `full-free` | Full · free | **The default at every size**: no quick request, free chosen (free words or option `full-free`), nothing chose paid, or paid was chosen but no budget its paid list uses is above 0 (fallback plus one question). Depth follows the measured size | `### Default: big website, free only`, all five categories. Main and Cross-check rows that are built and have access run. Reserve rows come in under their own "use when" rule. `(to build)` rows and rows without access go to *What could not be verified*, with that category's "What free can't answer" line | on |
| `paid-small` | Full · paid, small | Full depth, paid chosen, size small, and `dataforseo_monthly_usd` or `other_monthly_usd` above 0 | Each category's **Small sites** list, taking over per category. A paid row whose vendor isn't set up (not signed in, or budget 0) falls back to the default row that does the same job ("When the paid lists take over"). The credit guard enforces every limit | on |
| `paid-big` | Full · paid, big | As `paid-small`, with size big. `ahrefs_monthly_units` also counts here | Each category's **Big sites** list, with the same take-over and fallback | on |
| `quick` | Quick | **Only on request:** quick words with no full words, or option `quick` with no full words. Measurement never picks it | seo-audit's quick profile: `robots_check.py`, `page_audit.py` (with `schema_rules.py` inside) and `psi.py --strategy mobile` on the given URL, or the home page when only a host is given; `render_diff.py` when the page shows `likely-client-rendered`; then `triage.py`. No paid calls | off |

Overlapping tools that measure differently run together as Cross-checks in every full profile. Agreement raises
confidence; disagreement sends the item to a re-check before the run acts on it. Paid Cross-checks run only inside the
guard's budgets.

## 2. Depth

| Size class | `crawl` | `competitors` | `report` |
|---|---|---|---|
| quick | `none`: no crawl | 0 | `top-10`: the ten most urgent issues |
| small (up to 2,000 indexable URLs) | `site`: one whole-site `crawl.py` run at `--max-pages 2001`, so `hit_page_limit` means "more than 2,000 pages" | 3 | `full`: the whole seo-audit Output |
| big (more than 2,000) | `sections`: one `--path-prefix` crawl per first path segment (locale plus segment on multilingual sites), up to 2,000 pages each, in parallel subagents | 10 | `full` |

`competitors` is how many competitor domains seo-audit step 8 names from its SERP sample (3 and 10 are the tools.md
cost-example sizes). `stack` in the JSON points to the lists: `default-free`, `small` or `big`. The tool rows are never
copied into code; tools.md stays their only source.

**Not set by a profile**, because it never varies or someone else owns it:

- **Templates and PSI:** one URL per template plus the money pages, with `page_audit.py` and `psi.py`, in every full
  profile (seo-audit steps 3–4).
- **SERP keywords per pair:** the tools.md rows own them (20–50 head terms a pair, at most 200 WebSearch calls a
  session). The audit samples only the money pages' head terms.
- **Paid-budget share per run:** the guard's `per_run_cap_pct` (25%) and `ask_above_pct` (5%).
- **Schedule cadence:** seo-automation, and seo-audit's re-check rule (30 days after fixes ship, 90 for a routine check).
- **The section list on big sites:** a judgement in seo-audit step 2.
- **Add-on rows** (§6).

## 3. Signals

| Signal | Measured by | Used for |
|---|---|---|
| Indexable URLs | `sitemap_check.py` `total_urls`, summed over one report per host: the start host, plus each subdomain or ccTLD host in the home page's hreflang hrefs (`page_audit.py --facts`) | The size class at 2,000. Exactly 2,000 is small |
| Crawl limit | `crawl.py` `hit_page_limit` of the whole-site crawl at `--max-pages 2001` | Big when the crawl passes 2,000 pages, with or without a sitemap: the sitemap under-lists the site, or more than 2,000 pages are crawlable though fewer are indexable |
| Crawl count | `crawl.py` `indexable_pages` | The size count when there is no sitemap (tools.md "Size boundary") |
| Paid budgets | `credit_guard.read_options` over `CLAUDE_PLUGIN_OPTION_*`, which the SessionStart hook exports to Bash | Whether a paid list is usable for this size |
| Connected paid servers | `--connected NAME`: each MCP server name in Claude's tool list (between `mcp__` and the next `__`), mapped with `credit_guard.vendor_for` | End-of-run questions only. A budget of 0 can't spend: the guard denies it |
| `audit_profile` option | `CLAUDE_PLUGIN_OPTION_AUDIT_PROFILE` (empty or unset means `auto`) | A standing preference. It beats budgets and loses to the user's words |
| Request words | `--request-file`, which holds only the user's own words | A per-run override of depth (quick or full) and money (free or paid) |

**Options never configured** (a fresh install): a `CLAUDE_PLUGIN_OPTION_*` variable that is absent or empty reads as
its `plugin.json` default, so the picker reads `auto` and 0 for every budget and picks exactly as those defaults do.
When no option variable is set at all, its "options read" line adds "(none exported to Bash: defaults)". That is the
normal case, not an error: Claude Code passes a hook no option variable at all until the option is configured
[measured: `claude -p --plugin-dir` run, Claude Code 2.1.302, 2026-10-25], so the SessionStart hook exports none. The
picker and the guard carry the defaults themselves, and `tests/test_audit_profile.py` checks that they match
`plugin.json`.

**Not signals:** locales and market-language pairs (tools.md: they multiply costs and never change the class); Search
Console traffic (no fetcher yet, so the profile would flip on whether an export exists); company size (nothing
measures it); site type (a row condition inside the lists, §6); a Screaming Frog licence (every paid tool is Reserve in
the free stack and comes in under its own rule); month-to-date spend (the guard enforces it per call).

## 4. Rules (pure, in order, never a question mid-run)

- **R0. Inputs.** The option comes from `CLAUDE_PLUGIN_OPTION_AUDIT_PROFILE`, the budgets from `read_options`. An
  absent or empty variable is its default (§3, options never configured). A value outside the option values, or a
  budget the guard rejects, prints a message on stderr and exits 2. `--ignore-options` reads neither (option `auto`,
  every budget 0) and says so in `reasons`. A missing or malformed input file fails loudly; there is never a silent
  default.
- **R1. Words.** Only the request file is read: lowercased, whitespace collapsed, ’ read as '. Each phrase (§5) must
  follow a non-word character or the start of the text, and end at a word end, with an optional plural s. So "unpaid
  tools" is not paid, "quick checkout" is not quick, and "quick checks" is. "quick wins" matches nothing, and the bare
  words "quick" and "free" are never phrases. A paid phrase with a negation just before it is ignored (§5), so "don't
  use Semrush" asks for nothing.
- **R2. Depth.** Full words give full. Otherwise quick words, or else option `quick`, give quick. Otherwise full.
  Full words beat quick words.
- **R3. Quick.** Depth quick gives `quick`, chosen by `request` or `option`. Size, budgets and connected servers are
  ignored.
- **R4. Size.** Summed `total_urls` above 2,000 → big (`sitemap`). Otherwise a whole-site crawl with `hit_page_limit`
  → big (`crawl-limit`). Otherwise a summed count above 0 → small (`sitemap`). Otherwise crawl `indexable_pages` →
  small (`crawl`). Otherwise small (`unknown`) until measured. A crawl report with `pages_crawled` 0 (stopped by
  robots.txt) is ignored.
- **R5. Usable budgets** are the budgets above 0 of the guarded vendors with Main or Cross-check rows in that size's
  paid lists: DataForSEO and SE Ranking (`other_monthly_usd`) at both sizes, Ahrefs only on big sites. Semrush is
  Reserve in every list, and Ahrefs' paid API in the small lists (its free `domain-rating-free` endpoint needs no
  budget), so their budgets never pick a paid list there; `reasons` names each one.
- **R6. Money** (full only), first match wins: free words → free (`request`); paid words → paid (`request`); option
  `full-free` → free (`option`); option `paid` → paid (`option`); a usable budget → paid (`budgets`); otherwise free
  (`default`). Free beats paid, so "free tools first, then paid tools", which matches both, is free.
- **R7. Fallback.** Paid with no usable budget runs `full-free` (`fallback`) and asks one question: set this size's
  budgets from tools.md "Budget settings" (`/plugin configure seo-suite@seo-suite`). The skill fills in the numbers
  from tools.md; the script doesn't copy them.
- **R8. Connected but unbudgeted.** Only when chosen by `default` or `fallback`: each connected DataForSEO or SE
  Ranking server (Ahrefs rows use REST v3, never its MCP) whose budget is 0 adds one question naming its budget
  option. Never when the user or the option chose free.
- **R9. Profile.** Free gives `full-free`; paid gives `paid-small` or `paid-big`. Depth comes from the size class, or
  the quick row for `quick`.
- **R10. Re-pick.** seo-audit runs the picker at most three times: at step 0 with no size, at the end of step 1 with
  the sitemap reports, and, only if step 2's whole-site crawl hit its limit or the size is still `unknown` (no sitemap
  URLs), with `--crawl`. The last output is the run's profile. Paid calls come after the crawl, so a switch from small
  to big spends nothing on the wrong list.

**Tie-breaks:** exactly 2,000 URLs is small; full beats quick and free beats paid; words beat the option and the option
beats budgets. No rule raises a budget or makes a call.

## 5. Request words and option values

| Intent | Phrases |
|---|---|
| quick | `quick check`, `quick audit`, `quick look`, `quick scan`, `quick seo check`, `quick seo audit`, `quick review`, `spot check`, `spot-check`, `just this page`, `only this page` |
| full | `full audit`, `deep audit`, `deep dive`, `in-depth`, `thorough`, `thoroughly`, `comprehensive` |
| free | `free only`, `only free`, `free tools only`, `free tools`, `free audit`, `free stack`, `no paid`, `not paid`, `without paid`, `avoid paid`, `skip paid`, `never use paid`, `don't use paid`, `do not use paid`, `don't want paid`, `do not want paid`, `no need for paid`, `don't spend`, `do not spend` |
| paid | `paid tools`, `paid audit`, `paid stack`, `use paid`, `use semrush`, `use ahrefs`, `use dataforseo`, `use se ranking` |
| negation | `no`, `not`, `never`, `without`, `avoid`, `skip`, `cannot`, `dont`, `cant`, `wont`, `shouldnt`, `*n't` |

The table is literal. Naming a vendor ("use Semrush") is paid, and R5 and R7 say what its budget can and can't do.

**Negation.** A paid phrase is ignored when a negation is among the 3 words before it in the same clause, with no `,`
`.` `;` `:` `!` `?` or bracket in between. `*n't` is any word ending in n't (`don't`, `can't`, `won't`). Overlapping
paid phrases ("use paid" + "paid tools") are measured from the first one, so "I don't want to use paid tools" asks for
nothing. So:

- "don't use Semrush", "do not use DataForSEO" and "we can't use paid tools" ask for nothing: the option and the
  budgets decide.
- "no paid tools" and "never use paid data" are free, through their free phrases.
- "No problem, use paid tools" and "don't use Semrush, use DataForSEO" are paid: the comma ends the negation.
- A vendor the user refuses is not a picker signal. seo-audit leaves that vendor's rows out of the run, so they fall
  back to the default row, as for a vendor that isn't set up.

**Limits.** Only paid phrases are checked: a negated quick, full or free phrase still counts ("not a deep dive" is
full). A negation further back, or across a comma ("we don't think, at this stage, we should use paid tools"), is
missed, and the phrase counts. Without an apostrophe only the forms in the table count ("we didnt use paid tools" is
paid). A wrongly found negation can only keep a run free. Requests in Georgian or Russian
match nothing, so the option applies. Extend the tables in the script and here; never read page text for words.

| `audit_profile` | Effect |
|---|---|
| `auto` (default) | The free big-website stack, or the paid list for the site's size when a usable budget is above 0 |
| `quick` | The quick profile, unless the request has full words |
| `full-free` | Never paid tools, even with budgets set |
| `paid` | The paid list for the site's size; with no usable budget the run stays free and asks for one |

## 6. Add-ons

Add-ons are rows that evidence turns on inside the chosen stack. They are not profiles and not in the picker: seo-audit
applies each at the step where its evidence appears and records it under *Assumptions*.

| id | Signal (script → field) | Adds | Profiles |
|---|---|---|---|
| `js-render` | `page_audit.py` finding `likely-client-rendered`, or very few links, on a template URL | Step 5: `render_diff.py` on a rendered DOM, plus `page_audit.py --file` on it (Free technical #8). Chrome headless renders the DOM (#9), so scheduled runs get this add-on too, once their `--allowedTools` allow seo-audit step 5's commands. Without Chrome or Chromium, the built-in browser renders it in an attended session; a scheduled run lists the templates under *What could not be verified* | all |
| `search-exports` | `Queries.csv` and `Pages.csv`, or a Bing export, in the workspace | Step 6: `gsc_analyze.py` (`--compare` with two periods), and `research_store.py ingest gsc --as-of` | full |
| `logs` | An access log (combined format or `.gz`) delivered to the run | `log_analyze.py access.log --verify-dns --sitemap-urls seo-work/sitemap-urls.txt` (Free technical #10) | full |
| `local` | `summary.schema_types` of the home page or a money page has `LocalBusiness` or a type in `schema_rules.LOCAL_BUSINESS_SUBTYPES` | Rows marked "(local businesses only)": the Business Profile APIs (to build, so an access request for now), and the paid lists' DataForSEO Maps geo-grid | full |
| `store` | A money page's `schema_types` has `Product` | Rows marked "(stores only)": Merchant API v1, read-only, when a Merchant MCP or credential is connected; otherwise an access request | full |

## 7. CLI, JSON and exit codes

```bash
python3 "$S/audit_profile.py" --request-file seo-work/request.txt [--sitemap seo-work/sitemap.json ...] \
  [--crawl seo-work/crawl.json] [--connected SERVER ...] [--ignore-options] > seo-work/profile.json
```

- `--sitemap` and `--connected` repeat, once per host or server. `--crawl` takes only the whole-site crawl.
- **Exit 0** with JSON on stdout. **Exit 2** on a bad option or budget, with the message on stderr: re-run with
  `--ignore-options` and put that line first in the end-of-run questions. A missing input file exits non-zero with a
  traceback.
- `reasons` always holds the size line, an "options read" line (the option and all four budgets, plus "(none exported
  to Bash: defaults)" when no profile or budget option reached Bash, or "plugin options ignored (--ignore-options)"),
  a line per budget left unused, the override lines and the pick line. `budgets` are floats.

```json
{"profile": "full-free", "label": "Full · free", "stack": "default-free", "cross_checks": true, "report": "full",
 "crawl": {"mode": "sections", "max_pages": 2000}, "competitors": 10,
 "chosen_by": "default", "size_class": "big", "indexable_urls": 5400, "size_source": "sitemap",
 "audit_profile_option": "auto", "options_exported": true,
 "budgets": {"dataforseo_monthly_usd": 0.0, "other_monthly_usd": 0.0, "ahrefs_monthly_units": 0.0, "semrush_monthly_units": 0.0},
 "reasons": ["5,400 sitemap URLs > 2,000: big",
             "options read: audit_profile=auto, dataforseo_monthly_usd 0, other_monthly_usd 0, ahrefs_monthly_units 0, semrush_monthly_units 0",
             "full-free (chosen by default)"],
 "questions": []}
```

## 8. Worked example

"Audit example.com" with every budget at 0 and a DataForSEO MCP server connected:

1. **Step 0**, no size yet: `full-free` (chosen by `default`) at small depth, size `unknown`, and one question:
   `dataforseo_monthly_usd` is 0, so the connected server can't spend.
2. **Step 1**, with `--sitemap seo-work/sitemap.json` (4,900 URLs) and one ccTLD host from hreflang (500): 5,400 URLs,
   big. Still `full-free`, now with section crawls of up to 2,000 pages and 10 competitors.
3. **No step 2 re-pick:** the site is big, so there is no whole-site crawl.

With `dataforseo_monthly_usd` set to 270 instead, step 1 gives `paid-big` (chosen by `budgets`). Each category then
uses its **Big sites** list, and the rows whose vendor isn't set up (Ahrefs, SE Ranking) fall back to the default row
that does the same job. Saying "free only" in the request turns that run back into `full-free` (chosen by `request`).
