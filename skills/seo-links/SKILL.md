---
name: seo-links
description: Internal linking and backlinks. Orphan pages, hub and cluster linking, anchor text, backlink audits, link prospecting, broken-link building, unlinked mentions, digital PR, disavow and unnatural-link actions. Free first; outreach is sent only once approved. Not for crawl bugs (seo-technical) or local citations (seo-local).
---

# Links: internal architecture and off-page authority

Make every important page reachable and well linked inside the site, then earn relevant links from
outside it, without breaking Google's link-spam policy (google-rules §4).

## When to use / not

Use it for:
- Internal-link structure: orphans, depth, hubs, anchors, nofollow on internal links.
- Your backlink profile, prospecting, reclaiming links, digital PR plans.
- Disavow decisions.

Not for:
- Redirect chains or broken pages as technical defects → seo-technical. This skill only covers the *links* pointing at them.
- Citations and NAP → seo-local.
- Competitor content gaps → seo-competitors.

## Inputs: decide, don't ask

Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Site root, plus `seo-work/urls.txt` for orphan detection | The request; build the list with `sitemap_check.py --urls-out` | No sitemap: skip orphan detection and say so |
| Money pages: pages that convert or that the business most wants ranking | Navigation; pages with forms, cart, checkout, booking or pricing; Product/Service/LocalBusiness schema; top GSC clicks | Homepage plus the top-level nav product/service pages |
| Search Console → Links export: top linking sites, top linked pages, top linking text | A connector, or an export in `seo-work/`. Only a verified owner can export it | **Ask — batched at the end.** Carry on with part A and the free off-page checks; tag the profile `[needs data]` |
| Optional free sources: Bing Webmaster Tools → Backlinks export; Ahrefs Webmaster Tools (free for verified sites) → Backlinks / Broken backlinks CSV | A connector, or an export in `seo-work/` | **Ask — batched at the end**, saying what each adds |
| Brand names, product names, founders' names, for unlinked-mention searches | `<title>`, Organization schema, about page, footer, product pages | The Organization name or the homepage title's brand |
| Competitors that rank for the target terms (from seo-competitors) | Domains in the top 10 for the head terms (WebSearch) | Skip the gap analysis unless the request or plan includes competitive link building |

## Workflow

**Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`):

```bash
mkdir -p seo-work
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export clusters --format json > seo-work/store-clusters.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export inventory --format csv > seo-work/store-inventory.csv
```

- Reuse the clusters (`role`, `target_url`, `interlinks`) for the hubs in A4, `money_pages` in `seo-research/site.json`, and `seo-research/competitors.json` while `status` doesn't list `competitors` as stale.
- The store keeps no inlinks or click depth, so the A1 crawl always runs. Backlink exports stay in `seo-work/`: the store has no backlink dataset.
- No store yet (`status` exits with "no research store here"): create it with `init --site URL --locales …` (research-store §9).

### A. Internal linking (always first: it is fully in your control and free)

1. Run the free checks. These are independent, so run them in parallel:

   ```bash
   mkdir -p seo-work
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sitemap_check.py" https://example.com --sample 0 --urls-out seo-work/urls.txt > seo-work/sitemap.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crawl.py" https://example.com --max-pages 500 \
     --sitemap-urls seo-work/urls.txt --csv seo-work/pages.csv > seo-work/crawl.json
   ```

   For large sites, delegate to the `seo-site-auditor` agent so the raw JSON stays out of context.

2. Read the crawl findings `[measured]`:
   - `orphan-pages`: in the sitemap but no internal link reached them.
   - `weakly-linked`: exactly one inlink.
   - `deep-pages`: more than 3 clicks deep.
   - `internal-nofollow`
   - `anchor-generic` / `anchor-empty`
   - `noindex-heavily-linked`
   - `links-to-redirects`
   - `broken-internal-links`

   If `hit_page_limit` is true, orphan counts are inflated, so say so.

3. From `pages.csv`, rank pages by `inlinks` and `depth`, then compare against the money-page list. A money page that is deep or has few inlinks is the top fix.

4. Design hubs. For each topic cluster (the store's clusters, from seo-keywords / seo-strategy):
   - A pillar/hub page links to every cluster page.
   - Each cluster page links back to the hub and to 2+ siblings (heuristic), starting with the cluster's `interlinks`.
   - Breadcrumbs reflect the hierarchy.

   Output a link plan: `source URL → target URL → suggested anchor → placement` (in body copy, not the footer).

5. For anchor text, use descriptive anchors that vary naturally. No "click here", no exact-match stuffing on every link (google-rules §3).

6. For template-level fixes, change the nav, breadcrumbs, related-posts and footer components once rather than editing hundreds of pages. In a codebase, find the components and change them per autonomy level (`references/autonomy.md`).

7. Re-crawl after the changes and compare the inlink and depth columns.

### B. Off-page: understand the current profile

1. Load the Search Console Links export, plus Bing/AWT if available. Merge the referring domains and record the source of each one.
   - Search Console shows a *sample* and gives no authority metric. Never call it the full profile.
2. Summarise `[measured]`:
   - Referring domains by count.
   - Most-linked pages.
   - Anchor-text mix (branded / naked URL / generic / descriptive).
   - Links pointing at 404s or redirects.
3. Link reclamation (highest ROI, free):
   - Fetch the target URLs from the "top linked pages" export and find any that return 404 or chain-redirect.
   - Fix with a one-hop 301 to the closest equivalent page, never mass-redirecting to the homepage (google-rules §9), as a redirect-map diff applied per autonomy level (`references/autonomy.md`).
   - Verify with `redirect_check.py map.csv`.
4. Unlinked mentions: WebSearch `"Brand Name" -site:example.com` and variants (product names, founder names, `intitle:"brand"`). List the pages that mention the brand without linking. Write a polite link request to each, as an approval-batch item (C).

### C. Off-page: earn new links

Pick 2–3 tactics that suit the business. Outreach is always gated at every autonomy level (`references/autonomy.md`). Prepare each message exactly (recipient, public contact route, subject, text) and list it in the end-of-run approval batch. Send only the messages the user approves in chat for that run, through the user's connected email account, and log each one. Without a connected account, ask for one. Never send a message without that approval. The tactics:

- **Digital PR / data studies.** Original data, surveys or tools that journalists cite. Plan the asset, the angle and the target publications.
- **Resource and links pages.** Footprints:
  - `"keyword" inurl:resources`
  - `"keyword" intitle:"useful links"`
  - `"keyword" "recommended sites"`
- **Broken link building.** Find dead resources on relevant pages:
  - Search `"keyword" inurl:links` or `"keyword" resources`.
  - Fetch the page and test its outbound links with `page_audit.py`'s facts or by fetching each link.
  - Offer your page as the replacement.
- **Partners, suppliers, customers, associations, local chambers, universities, events you sponsor.** Real relationships.
- **Expert commentary.** Journalist-request platforms. Answers must be genuinely expert.
- **Guest contributions.** Only genuine editorial pieces on relevant sites. Links in them should be `rel=nofollow` or `sponsored` when there is any exchange (google-rules §4).
- Run independent prospect searches in parallel with `seo-serp-researcher` agents, one batch of footprints each.

### D. Toxic links and disavow

- **Default: do nothing.** Google ignores most spammy links automatically.
- Use the disavow tool only when:
  - (a) Search Console shows a **manual action for unnatural links**, or
  - (b) there is a clear paid or link-scheme pattern you or a previous agency created that is likely to trigger one.
- Process:
  1. Try removal outreach first, as approval-batch items (C).
  2. Then disavow at domain level (`domain:spam.example`).
  3. Then file a reconsideration request documenting the cleanup.
- **Disavow files and reconsideration requests are always gated at every autonomy level** (`references/autonomy.md`). Prepare the `disavow.txt` and the request text, and list each as an item in the end-of-run approval batch. Once the user approves them in chat, upload the file and file the request in Search Console in the user's signed-in browser session (neither has an API), then log both. A scheduled run only lists them.
- Do not recommend disavowing on the basis of a third-party "toxicity score" alone. Those scores are vendor heuristics.

### E. Write back to the research store

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" ingest crawl seo-work/pages.csv
```

- Ingest the A1 crawl and the A7 re-crawl, so the next skill gets fresh titles, word counts and HTTP status.
- When the link plan settles which live page is a cluster's hub or primary page, record it: `set-status --cluster ID --status published --url URL`.

## Checks

| Check | Rule | Source |
|---|---|---|
| Every important page has ≥1 internal `<a href>` link | required for discovery | google-rules §3 [Google doc] |
| Links are crawlable `<a href>` (not onclick/`<span>`/`javascript:`) | otherwise not followed | google-rules §1 [Google doc] |
| Internal links are not `nofollow` | wastes discovery | heuristic |
| Click depth of money pages ≤3 | heuristic (crawl `deep-pages`) | heuristic |
| Anchors descriptive, not generic, not stuffed | | google-rules §3 [Google doc] |
| Paid/exchanged links carry `rel=sponsored`/`nofollow`; UGC `rel=ugc` | link-spam policy | google-rules §3–4 [Google doc] |
| No PBNs, link exchanges at scale, paid dofollow links, link-insertion schemes | link spam → manual action | google-rules §4 [Google doc] |
| Removed pages with backlinks 301 to a close equivalent | preserves signals; no mass homepage redirects | google-rules §9 [Google doc] |
| Redirects one hop, 301/308 | | google-rules §1 [Google doc] |

## Data: free vs paid

The free path covers your own site completely:
- Crawl CSV: internal graph, depth, inlinks.
- GSC Links: a sample of external links.
- Bing Webmaster backlinks.
- Ahrefs Webmaster Tools: a fuller external profile for verified sites.
- WebSearch: prospecting and mentions.

Paid tools are justified only for **other people's** link data. See `${CLAUDE_PLUGIN_ROOT}/references/tools-paid.md`:
- **Ahrefs** (`## Ahrefs`). The largest live link index. Use Link Intersect to find sites that link to 2+ competitors but not you, plus competitor best-by-links pages and lost-link alerts.
  - Justified when the plan includes competitive link building or a recovery investigation.
  - Cost tactics: export only the referring-domains view rather than every backlink, filter by DR/traffic and dofollow before exporting, and run Link Intersect once per quarter rather than continuously.
- **Semrush** (`## Semrush`). Backlink Gap and the Backlink Audit workflow, if the team already pays for Semrush for keywords. Don't buy both Semrush and Ahrefs for links alone.
- **Majestic** (`## Other paid tools`). Trust Flow / topical Trust Flow and a historic index. A cheap second opinion on link quality.
- **Moz** (`## Moz`). Domain Authority and a link explorer. DA is a vendor metric, not a Google signal.
- **DataForSEO Backlinks API** (`## DataForSEO`). Pay-as-you-go bulk link data for scripted analysis.

Label every metric from these tools `[vendor data]`. DR/DA/TF are vendor estimates, never Google signals.

## Output

1. **Internal link plan** (`seo-work/internal-links.csv`): `source, target, anchor, placement, reason`, ordered by money-page impact.
2. **Template changes** (nav, breadcrumbs, related posts) as concrete diffs if there is a codebase.
3. **Reclamation list:** `linked 404 URL → redirect target`, plus the redirect map ready for `redirect_check.py`.
4. **Prospect sheet:** `site, page, contact route (public), angle, why relevant, message, status` (awaiting approval, or sent on a date). Each message is an approval-batch item.
5. **Disavow recommendation:** usually "none needed", with the reason. If one is needed, the `disavow.txt` and the reconsideration text as approval-batch items, and whether they were filed.
6. Pipe crawl/sitemap JSON through `triage.py seo-work/crawl.json seo-work/sitemap.json` for P0–P3 ordering of the link-related findings.
7. **Assumptions:** the money pages, brand names, competitors and data sources you decided, each with its evidence, and which store data was reused and how old it was (e.g. "clusters and competitors from seo-research, 20 days old"). Then the questions batched for the user (missing exports or access), each with a recommendation, and the approval batch (outreach messages, disavow items).

## Pitfalls & myths

- **"More links = better."** Relevance and editorial placement matter; 1,000 directory links don't.
- **Buying "guest posts" or "niche edits" with dofollow links** is link spam (google-rules §4), whatever the vendor calls it.
- **Disavowing "toxic" links flagged by a tool** without a manual action usually does nothing, and can remove links that were helping.
- **Footer/sitewide links** are low-value and pattern-detectable. Contextual body links carry more meaning.
- **GSC Links is a sample.** Don't report its counts as totals.
- **Mass-redirecting old URLs to the homepage** is treated as a soft 404, and the link value is lost.
- **Nofollow on internal links** to "sculpt PageRank" doesn't work and hurts discovery.
- Never claim a link "caused" a ranking change. Say it "coincides with".

## Log the work

Append to `SEO-WORKLOG.md` (format: `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`):
- Date and scope.
- Data sources used, with evidence tags.
- Store data reused (with its age) and ingested.
- Paid-tool usage (units/credits spent).
- Files produced.
- Messages sent and disavow items filed on approval, with dates, and the items still awaiting approval.
- Decisions (e.g. "no disavow, no manual action").
- What to re-measure, and when (re-crawl inlinks in 2 weeks; referring domains monthly).
