---
name: seo-migration
description: Plan, validate and monitor site moves without losing search traffic. Covers domain changes, URL restructures, CMS or platform replatforms (e.g. WordPress→Next.js, Shopify→headless), HTTP→HTTPS, www changes, subdomain↔subfolder merges, and site consolidations. Use when the user says "we're migrating", "moving to a new domain", "redesign with new URLs", "replatforming", "build a redirect map", "check my redirects", "traffic dropped after the migration", "launch checklist", or "Change of Address". It builds the URL inventory, the redirect map, staging safeguards, the launch-day checklist and the day 1/7/30/90 monitoring with rollback triggers. Not for a routine audit (use seo-audit), single redirect or canonical bugs (seo-technical), or hreflang setup (seo-international).
---

# SEO Migration

Move URLs so that every old URL with value lands on its single best new equivalent in one hop. Then prove it, and watch it.

## When to use / not

- **Use for:**
  - Any change in URL, domain, protocol, platform or site structure.
  - Merging sites.
  - Post-migration traffic loss.
- **Not for:** a redesign that keeps every URL. Run seo-audit on staging and production instead, but still use the staging-protection and launch checks below.

## Inputs: decide, don't ask

Decide each input from evidence, record it under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Move type: domain, path, platform, protocol, merge, or a combination. Change one thing at a time where possible (§9) | Compare old and new: host, scheme, URL patterns, and the platform behind each | The type the brief describes |
| Old and new hosts, the staging URL | The brief, and the repo's deploy config if there is one | Staging access (credentials, allowlist): ask — batched at the end. Never put credentials into pages; the user logs in themselves |
| Launch date | The brief | Plan relative to launch day (day 0) |
| Whether the old host stays under the team's control. The old domain must stay owned and redirecting for at least a year (§9) | The brief | Assume it stays owned and redirecting. A business decision: ask — batched at the end |
| Exports: Search Console top pages (16 months), analytics landing pages, server logs, the CMS URL list, old sitemaps, pages with backlinks (Ahrefs Webmaster Tools free for the verified site, or Search Console → Links → Top linked pages) | Fetch what's reachable (sitemaps, crawl, Wayback CDX); use APIs and files already configured or in the workspace | Ask for the rest — batched at the end of the first run, not later: Search Console only keeps 16 months |

## Workflow

`S="${CLAUDE_PLUGIN_ROOT}/scripts"`; work in `seo-work/migration/`.

### Phase 1: Inventory (weeks before launch)

0. **Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`), when `seo-research/` exists:
   ```bash
   mkdir -p seo-work/migration
   python3 "$S/research_store.py" status > seo-work/migration/store-status.json
   python3 "$S/research_store.py" export inventory --format csv > seo-work/migration/store-inventory.csv
   python3 "$S/research_store.py" export clusters --format json > seo-work/migration/store-clusters.json
   ```
   - The inventory's URLs are one more source for step 1, and its `gsc_clicks` one more value signal for step 2. They add to the 16-month Search Console export and don't replace it: the store keeps one period's totals.
   - Every cluster `target_url` is a page the content plan relies on: map it by hand.
   - The old-site crawl still runs: the baseline needs `old-crawl.json`, which the store doesn't keep. Note what you reused and its age for *Assumptions* and the work log.
1. **Collect old URLs** from every source (run in parallel):
   ```bash
   python3 "$S/sitemap_check.py" https://old.example.com --sample 0 --urls-out seo-work/migration/old-sitemap-urls.txt > seo-work/migration/old-sitemap.json
   python3 "$S/crawl.py" https://old.example.com --max-pages 5000 --csv seo-work/migration/old-pages.csv > seo-work/migration/old-crawl.json
   python3 "$S/log_analyze.py" access.log* > seo-work/migration/old-logs.json
   zgrep -h Googlebot access.log* | awk '{print $7}' | sort -u > seo-work/migration/old-log-paths.txt
   ```
   `old-logs.json` shows only each bot's top 15 paths, so use it for bot hits and status codes. `old-log-paths.txt` holds every path Googlebot requested (zgrep reads plain and `.gz` logs; `$7` is the request path in combined log format). Then merge in `old-log-paths.txt` (prefixed with the old host), the Search Console pages export, analytics landing pages and top-linked pages. De-duplicate after normalising scheme, host case and trailing slash consistently.
2. **Rank URLs by value:** clicks (GSC), conversions (analytics), referring links, bot hits (logs). The top ~20% of URLs usually carry most of the value. Map those by hand; the long tail can be mapped by pattern.
3. **Baseline:** keep `old-crawl.json`, `old-pages.csv` and a GSC export of the last 28 days plus the previous 28 days. They're needed for `gsc_analyze --compare` after launch.

### Phase 2: Redirect map

4. **Build the map**, a CSV with columns `old,new`:
   - Exact equivalents first (same content).
   - Then the closest relevant parent (category).
   - Never mass-redirect to the homepage; Google treats that as a soft 404 (§9).
   - Content that is intentionally dropped returns 404/410 (§1, §9).
   - Pattern rules (regex on the server) for the long tail. Expand them into explicit rows for testing.
   - Include images, PDFs and other indexed assets that change URL (§9).
5. **Validate on staging or production:**
   ```bash
   python3 "$S/redirect_check.py" seo-work/migration/map.csv --workers 8 > seo-work/migration/redirects.json
   ```
   It exits 1 if any row fails. Each row must be one hop, 301/308, landing exactly on the mapped URL, and the target must be 200, indexable and self-canonical.
   - **Script gap:** a redirect loop or a chain over 10 hops shows up as `status: null`. Treat any `null` status as "loop/unreachable".
6. **New-site readiness** (crawl staging only if it's reachable without bypassing protection):
   - Self-referencing canonicals on new URLs.
   - Internal links point to the new URLs directly, not via redirects.
   - New sitemap(s) list only new final URLs.
   - hreflang updated (seo-international).
   - Structured data URLs updated.
   - robots.txt allows crawling (staging blocks are **removed** at launch).
   - Analytics and Search Console verification are in place on the new host.
   - Server capacity is ready for heavier crawling (§9).

### Phase 3: Staging protection

7. **Staging must not be indexed or leak:**
   - Protect it with HTTP auth or an IP allowlist. That's the most reliable way.
   - noindex on staging is a backup, but **it must not ship to production**. Use an environment-based switch, not a hard-coded tag.
   - Search for leaks: `site:staging.example.com` in WebSearch.
   - Check staging hostnames aren't linked from production and aren't in sitemaps.

### Phase 4: Launch day

8. **Checklist, in order:**
   1. Deploy the new site (per autonomy level, references/autonomy.md; DNS changes and CDN/edge redirect rules are always gated).
   2. Switch on the redirects (per autonomy level, references/autonomy.md; DNS changes and CDN/edge redirect rules are always gated).
   3. Run `redirect_check.py` on the full map against **production**.
   4. Run `robots_check.py` on the new host. Googlebot must be allowed on `/`.
   5. Run `page_audit.py` on the homepage plus one URL per template. There must be no `noindex`, and canonicals must be self-referencing.
   6. Run `sitemap_check.py` on the new host.
   7. Submit the new sitemap in Search Console per autonomy level (references/autonomy.md): at level 4 through an authorised connector, otherwise the user submits it. Keep the old sitemap available for a while so Google re-crawls the redirects.
   8. For a domain change only, the user runs the **Change of Address** tool. It's always gated at every autonomy level (references/autonomy.md): submit it yourself only with the user's approval for this run, and preferably let the user do it. Its rules:
      - Domain-level properties.
      - The same owner on both properties.
      - A 301 on the homepage.
      - Every subdomain variant verified.
      - Signals forward for 180 days (§9).

      Not used for http→https, www, or path-only changes.
   9. Optionally use IndexNow for Bing and Yandex, per autonomy level (references/autonomy.md), since it submits URLs to third parties.
   10. Prepare a change list for the external links the user controls (social profiles, Business Profile, directories) for the owner to apply. These are external accounts, and Business Profile edits are always gated at every autonomy level (references/autonomy.md): edit one yourself only with the user's approval for this run. Draft outreach for the most valuable backlinks; sending it is always gated at every autonomy level (references/autonomy.md), so send nothing unless the user approves each message for this run.

### Phase 5: Monitoring

9. **Cadence:**
   - **Day 1:** full redirect check, 5xx/404 spikes in logs (`log_analyze.py`), Googlebot hitting the new URLs.
   - **Day 7:** `crawl.py` on the new site (broken internal links, links still pointing at old URLs) and Search Console coverage on the new property.
   - **Day 30 and Day 90:**
     ```bash
     python3 "$S/gsc_analyze.py" new-28d.csv --compare old-28d-before-launch.csv
     ```
     Map query-level losses back to their old URL and check its redirect.
   - Expect weeks of fluctuation for a medium site (§9).
10. **Rollback and escalation triggers** (heuristics; list them under *Assumptions* so the team can adjust them before launch):
    - **Fix immediately:** sitewide 5xx, accidental noindex or robots disallow, redirects failing above 2% of the top 20% of URLs.
    - **Escalate:** non-brand clicks down >30% at day 14 with positions dropping (not just impressions).
    - **Investigate per URL** (not a rollback): losses concentrated on specific URLs. They're usually mapping errors.
11. **Keep redirects for at least 1 year, ideally forever.** Keep the old domain registered (§9).
12. **Write back to the research store**, for URLs on the store's host only (`site.json` → `domain`). `ingest crawl` doesn't check the host, and the store can't follow a move to another host: `init` refuses any host but its own, `www.` aside. For a domain or subdomain move, do only the Phase 1 ingest and say under *Assumptions* that the store still describes the old host.
    - **Phase 1:** `ingest crawl seo-work/migration/old-pages.csv`, the pre-move inventory.
    - **Launch:** re-point each cluster in `store-clusters.json` whose `target_url` is an `old` URL in `map.csv` to its `new` URL, passing its current `status` again. Later briefs and posts then link to the new URLs directly, not through redirects (step 6):
      ```bash
      python3 "$S/research_store.py" set-status --cluster en-004 --status published --url https://example.com/new/path/
      ```
    - **Day 7:** ingest the new site's crawl CSV the same way.

## Checks

- **Redirect type and length** (§1, §9):
  - Server-side 301/308. No meta refresh or JS redirects for moves.
  - One hop. Never ≥5 in a move; Google follows ≤10.
- **One-to-one relevance:** no redirecting to the homepage, no chains via the old structure (§9).
- **Status codes:** dropped content returns 404/410, and 404 = 410 for Google (§1).
- **Canonical alignment:**
  - New pages are self-canonical.
  - No canonical points back to the old domain.
  - Sitemaps contain new URLs only (§1).
- **robots.txt:**
  - The old host must stay crawlable (no disallow), or Google can't see the redirects.
  - The new host must not carry the staging disallow.
- **Change of Address:** domain moves only. 180-day window. Redirects stay for at least 180 days and the domain for at least a year (§9).
- **Search Console:**
  - Verify both properties and all variants.
  - Copy the disavow file if one exists.
  - Check the new domain for manual actions before the move (§9).

## Data: free vs paid

- **Free path:**
  - Bundled scripts (sitemap, crawl, redirect_check, log_analyze, gsc_analyze).
  - Search Console: Pages, Links, Change of Address, URL Inspection.
  - Ahrefs Webmaster Tools (free) for backlink targets on the verified domain.
  - Analytics exports.
- **Ahrefs / Semrush** (paid) add the complete list of externally linked old URLs, including links Search Console samples out. Justified for sites with valuable link equity. Pull "Best by links" / "Indexed pages" once, export it, and don't re-query (tools.md `## Ahrefs`, `## Semrush`, `## Cost-optimisation playbook`).
- **Screaming Frog** adds list-mode redirect auditing for 10k+ URL maps, and crawl comparison between old and new. Justified for large migrations (tools.md `## Screaming Frog`). `redirect_check.py` covers maps up to tens of thousands of rows if run with more workers.
- **Wayback Machine CDX** (free) recovers old URLs when the inventory is incomplete: `https://web.archive.org/cdx/search/cdx?url=old.example.com/*&output=json&fl=original&collapse=urlkey`. Fetch it with WebFetch.

## Output

```
# Migration plan / check — <old> → <new> — <date>
Type: … · Launch: … · URLs inventoried: N (sources: …) · Value-ranked top set: N
## Readiness (pass/fail per check, [measured])
## Redirect map validation: checked N · passed N · failed N (table of failures with reason)
## P0–P3 issues (triage.py on crawl/page/robots/sitemap JSONs + redirect failures as P0/P1)
## Launch-day runbook (who does what; items gated per autonomy level are marked)
1. Deploy [per autonomy level; DNS changes always gated] · 2. Redirects on [per autonomy level; CDN/edge redirect rules always gated] · 3.–10. …
## Monitoring schedule + rollback triggers
## Assumptions (move type, launch date, URL value ranking, rollback triggers: each decision and its evidence; research-store data reused, with its age)
## Not verified [needs data]
```

## Pitfalls & myths

- **"301s lose PageRank":** they don't (§9). Losses come from bad mapping, chains, lost content, or changing too much at once.
- **Redirecting everything to the homepage** = soft 404 = lost equity.
- **Blocking the old domain in robots.txt after launch** hides the redirects. Never do it.
- **Shipping the staging noindex or `Disallow: /` to production** is the most common catastrophic migration bug. Check it at launch, in minute one.
- **Removing redirects after "traffic moved"** (e.g. at 3 months) breaks old backlinks and bookmarks.
- **Changing domain, URLs, design and content in one release** makes a loss undiagnosable. Stage the changes where possible.

## Log the work

Append to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`, once per phase:
- Inventory sources and counts.
- The map file path and version.
- `redirect_check` results (passed/failed).
- Launch timestamp.
- Who ran Change of Address and when.
- Paid units spent.
- Monitoring results at day 1/7/30/90.
- Next check date. Set an explicit day-90 and day-365 reminder, the earliest date redirects could ever be reconsidered.
