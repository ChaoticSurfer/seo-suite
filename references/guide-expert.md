# SEO for Experts — scope, priorities, advanced tactics

## How Claude uses this guide

Load this guide when the user is an SEO practitioner or developer: they use the jargon, ask for raw data, or
say they're experienced.

**Answer style**
- Be terse and skip the basics.
- Lead with evidence: script output, file paths and numbers. Follow with the interpretation and the fix.
- Show the exact commands (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<x>.py" …`) and where the raw JSON/CSV
  was written, so the user can re-run or diff it.
- Tag every claim: `[measured]`, `[Google doc]` (cite google-rules §N), `[vendor data]`, `[estimate]` or
  `[needs data]`.

**Fixes and estimates**
- Prefer root-cause and template-level fixes ("one component emits 1,400 duplicate canonicals") over
  page-by-page lists.
- Give opportunity as **ranges** with the assumptions stated, for example impressions × the CTR delta from
  the site's own CTR curve (`gsc_analyze.py`).
- Never present a single-point traffic forecast.
- Propose changes as **experiments**: pre-registered metric, control group of pages, ≥4 weeks, equal-length
  windows aligned by weekday. Report "coincides with", never "caused".

**Research store** (`references/research-store.md`)
- `seo-research/` keeps keywords, SERP snapshots, clusters, competitors, GSC totals and the page inventory per
  locale, every value with its source and date, versioned with the repo.
- Start each task from `research_store.py status`. Reuse fresh datasets and refresh only the stale or missing ones
  (TTLs in days: keywords 90, volumes 30, SERPs 30, GSC 7, inventory 30, competitors 90). Then `ingest` what you
  fetched.
- State the reuse and its age in *Assumptions*, e.g. "en SERPs reused, 9 days old; GSC refreshed".

**Challenge myths when they come up**
- LSI keywords.
- Word-count targets.
- Text-to-HTML ratio.
- Exact title/description character limits.
- "DA/DR is a Google metric."
- `rel=next/prev` (not used by Google).
- Disavowing on a "toxic score" alone.
- `llms.txt` as a ranking lever.
- FAQ schema for SERP real estate.

**Recent changes to keep front of mind (2025–2026)**
- **HTML indexing cap.** Googlebot for Search indexes only the first **2 MB of HTML, uncompressed** (PDFs
  64 MB). google-rules §1.
- **FAQ rich results stopped showing on 2026-05-07.** HowTo is long gone. The sitelinks search box was removed
  2024-11-21. Course info, Estimated salary, Learning video, Special announcement and Vehicle listing were
  removed 2025-09-09. Practice problems were removed 2026-01-06. Event is physical-only. §5.
- **Site reputation abuse.** First-party oversight doesn't automatically exempt a site. In the EEA, since
  2026-08-28, offending sections are ranked separately rather than given manual actions. §4.
- **New spam policy:** back-button hijacking (2026-04-13). Spam policies explicitly cover manipulating
  generative AI responses (2026-05-15). Spam reports can now lead to manual actions. §4.
- **AI features.** AI Overviews and AI Mode eligibility is the same as snippet eligibility, with no special
  markup or files. The Search Console setting **Settings → Search generative AI** opts a site out of AI
  Overviews, AI Mode and Discover AI without affecting classic ranking. Google-Extended controls only
  Gemini training and grounding. `llms.txt` is not used by Google. §10.
- **Meta robots outside `<head>`** is now honoured (2026-03-24). Canonical is still `<head>`-only. §1.
- **Reserved region codes.** hreflang `UK`, `EU` and `UN` are ignored; use `en-GB`. §6.
- **404 vs 410.** No documented difference. Site-move redirect chains: ≤3 hops ideal, never 5 or more.
  Change of Address forwards signals for 180 days, and redirects should stay for ≥1 year. §1, §9.

---

## Pillar 1 — Technical foundation

**Scope (exhaustive checklist)**
- **Access**
  - robots.txt is RFC 9309-compliant and under 500 KiB. Know Google's longest-match / allow-on-tie rule.
  - A robots.txt answering 5xx or 429 halts crawling for 12 h, then Google uses the cached copy for up to
    30 days.
  - No WAF/CDN challenges for verified bots, including Cloudflare `cf-mitigated: challenge` and managed
    robots.txt injection.
- **Status semantics**
  - Soft-404 detection (probe a non-existent URL).
  - Redirect hops (≤10 followed by Google) and permanent vs temporary redirects.
  - 429/5xx crawl throttling.
- **Indexability**
  - meta robots / `X-Robots-Tag` conflicts.
  - noindex present in the initial HTML (JS-removed noindex may never be seen).
  - noindex combined with a robots.txt disallow, so the noindex is never seen.
- **Canonicalisation**
  - Exactly one canonical, absolute, in `<head>`, self-referencing.
  - Raw and rendered canonicals agree.
  - No canonicals pointing at non-200 / redirecting / noindex URLs.
  - Canonical, sitemap and hreflang tell the same story.
- **Rendering**
  - Raw vs rendered parity for title, robots, canonical, primary content, links and structured data.
  - Only `<a href>` links count as links.
  - History-API routing, no `#/` routes.
  - Shadow DOM uses `<slot>`.
  - Asset files are fingerprinted.
- **Fetch limits**
  - 2 MB HTML cap (watch inline JSON blobs, SVG sprites, hydration payloads).
  - Compression and HTTP/2.
  - ETag/304 support for crawl efficiency.
- **Architecture**
  - Click depth ≤3 for money pages (heuristic).
  - Orphans, dead ends and inlink distribution.
  - Hub pages, breadcrumbs and pagination (unique `?page=n` URLs, no canonical to page 1).
- **Faceted navigation**
  - Block facet crawl in robots.txt, or return 404 for empty or nonsensical combinations.
  - canonical and nofollow are weak, slow controls. §8.
- **Sitemaps**
  - 50k URLs / 50 MB per file; only final 200, canonical, indexable URLs.
  - Truthful `lastmod`. `priority` and `changefreq` are ignored.
  - Image, video and news extensions follow their own rules. §1.
- **Page experience**
  - CWV at p75 field values: LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1. Also HTTPS/HSTS and no intrusive
    interstitials.
  - Mobile parity: the same content, structured data, meta and alt text as desktop. §2.
- **Crawl budget**
  - Only matters at roughly 1M+ pages changing weekly, or 10k+ pages changing daily, or a large "Discovered –
    currently not indexed" backlog.
  - Check with log files.
  - noindex doesn't save budget.
- **Environments**
  - Staging/dev hosts locked behind auth, not just noindex.
  - Launch checklists that strip staging noindex.

**Strategy & prioritisation**
- **Order of impact:** access and indexability, then canonical/duplication, then rendering, then
  architecture/internal links, then CWV, then hygiene. `triage.py` encodes this ordering.
- **SMB / brochure sites:** usually 5–10 template-level issues. Fix them once and move on to content and local.
- **SaaS on a JS framework:** rendering parity and metadata generation per route, docs/blog subfolders rather
  than subdomains (convention), and pricing/integration pages that are reachable and linked.
- **E-commerce:** faceted crawl control, variants (ProductGroup), out-of-stock handling (keep 200 with
  availability, or 301 to a successor, or 404/410 when truly gone), pagination, and parity between feed,
  page and schema.
- **Publishers:** sitemap freshness (news sitemaps: last 2 days, ≤1,000 entries), `max-image-preview:large`,
  stable section URLs, and crawl capacity during spikes.
- **Multilingual:** hreflang reciprocity generated from one source of truth. Avoid locale-adaptive serving,
  because Googlebot crawls mostly from US IPs without `Accept-Language`.

**Advanced tactics**
- **Log analysis.** Googlebot vs AI bots, crawl waste on parameters, sitemap URLs never crawled, and
  reverse+forward DNS verification of claimed Googlebots.
- **Render diffs** at the template level. Capture the DOM per template via the browser, then run
  `render_diff.py`.
- **CI gate.** In pull-request checks, audit the preview's HTML as a file, with the production URL as the base:
  ```bash
  curl -sf "$PREVIEW_URL/<path>" -o page.html && python3 scripts/page_audit.py --file page.html --base-url "https://<production-host>/<path>" --fail-on high
  ```
  If the preview is protected, add `-H "x-vercel-protection-bypass: $BYPASS_SECRET"` to the curl call, with
  the project's Protection Bypass for Automation secret stored as a CI secret.
  A live audit of a preview always fails: Vercel and Netlify send `X-Robots-Tag: noindex` on preview
  deployments, and preview builds usually carry the production canonical (`noindex` / `canonical-elsewhere`).
  A local `next start` server fails on `not-https`.
  File mode skips header checks (X-Robots-Tag, HSTS, compression), so check those with a live `page_audit.py`
  run against production.
- **Use Search Console's URL Inspection API** (2,000/day per site) to see Google's chosen canonical for a
  sample.

**Measurement**
- *Indexing → Pages* reason trends, Crawl Stats (host status, response codes and file types), CrUX via
  `psi.py` (and the CrUX History API with a key), and log-based crawl frequency per section.

**Failure modes**
- Fixing symptoms page by page.
- Canonicalising paginated series to page 1.
- Blocking URLs in robots.txt that need to be deindexed.
- JS-injected canonicals that disagree with the raw HTML.
- CDN bot rules silently challenging Bingbot or OAI-SearchBot.
- Redirect maps with chains, or everything sent to the homepage.

**Tooling**
- **Free path:** `robots_check.py`, `sitemap_check.py --urls-out`, `crawl.py --sitemap-urls --csv`,
  `page_audit.py`, `render_diff.py`, `psi.py` (free `PSI_API_KEY`), `log_analyze.py --verify-dns`,
  `redirect_check.py`, then `triage.py` over all the JSON outputs.
- **Screaming Frog** (see `## Screaming Frog` in `references/tools.md`) is justified for sites over ~2,000 URLs
  or sites that rely on JavaScript. It adds JS-rendered crawling at scale, custom extraction, and scheduled
  crawls with GSC/PSI joins. Its free tier is capped at 500 URLs.
- **Skills:** seo-audit, seo-technical, seo-migration, seo-international, seo-ecommerce.

---

## Pillar 2 — Content & copywriting

**Scope**
- **Demand discovery:** autocomplete, PAA (People Also Ask), GSC queries, forums.
- **Intent and SERP-type mapping:** the dominant page type in the top 10.
- **Clustering by SERP overlap.** Heuristic: ≥4 shared top-10 URLs → same page; 2–3 → separate pages that
  link to each other.
- **Topical map and architecture.**
- **Page-level copy:**
  - Title link and snippet.
  - An answer-first lede.
  - Information gain: first-hand data, original images, tested claims.
  - Conversion copy: value proposition, objections, proof, CTA.
- **E-E-A-T signals:** bylines, author pages, reviewers on YMYL topics, citations, about/contact pages,
  editorial policy. Trust comes first. §4.
- **Freshness:** real updates only. Faking freshness by changing dates is a warning sign. §4.
- **Content lifecycle:** inventory, decay detection, then keep / update / merge / redirect / delete.
  Resolve cannibalisation.
- **AI-assisted production:** allowed when it meets Search Essentials. Fact-check everything, disclose where
  readers would reasonably wonder, and review AI-generated titles, meta, structured data and alt text.
  Scaled content abuse applies however the content is made. §4.
- **Copyright and originality**
  - Scraping, synonymising and auto-translating at scale violate the spam policies. §4.
  - The "Legal removals" policy demotes sites with many valid removal notices.
  - Images need a licence, or must be your own.
  - Merchant Center requires the IPTC `DigitalSourceType = TrainedAlgorithmicMedia` label on AI images and
    labelling of AI product text.
  - Syndication requires a canonical or attribution agreement with the partner.

**Strategy & prioritisation**
- Fix the money pages first: service, product, category, pricing. Then pages already in striking distance
  in GSC (positions 4–20 with impressions). Net-new content comes last.
- **SaaS:** bottom-of-funnel first (comparisons, alternatives, integrations, use-case pages with real product
  screenshots). Then docs, which are a large and underrated link and AI-citation asset.
- **E-commerce:** unique category copy where it helps users choose, product content beyond the manufacturer
  text, and buying guides tied to categories.
- **Publishers:** topical depth, original reporting, author entities.
- **Local:** service × location pages only where the business genuinely operates. Apply the city-swap test:
  if swapping the city name leaves the page valid, the page is thin.

**Advanced tactics**
- **Content-gap phrases** from `compare_pages.py`: subtopics covered by ≥2 competitors and missing from your
  page.
- **Site-specific CTR curve** to find title/snippet under-performers (`gsc_analyze.py`). Rewrite titles against
  Google's rewrite triggers: boilerplate, an obsolete date, no clear main title. §3.
- **Passage design** for featured snippets and AI citation: self-contained 40–80-word answers under a
  question heading, plus tables and stats with sources. This is a heuristic.
- **Decay detection:** period-over-period GSC comparison. Classify each loss as position loss, demand loss,
  or CTR loss from a SERP/AI Overview change.

**Measurement**
- Clicks, impressions and CTR per page and per cluster, with a branded/non-branded split.
- Conversions per landing page (GA4).
- Indexing rate of new content.
- Time to first impression.

**Failure modes**
- Word-count targets.
- Publishing AI content at volume without information gain.
- Merging pages without redirects.
- Updating dates without updating content.
- Ignoring intent mismatches (writing a guide when the SERP wants product grids).

**Tooling**
- **Free path:**
  - `keyword_ideas.py --hl --gl --sources google,bing,youtube`.
  - `gsc_analyze.py` (striking distance, cannibalisation with query+page exports, `--compare`).
  - `content_score.py --keyword`.
  - `compare_pages.py`.
  - WebSearch for SERP inspection (parallelise with the seo-serp-researcher agent).
  - `research_store.py`: ingest keyword ideas, SERPs, clusters and GSC data once, then `next-topics` ranks the
    clusters with no published page [heuristic].
- **Paid adds:**
  - Search volumes and keyword difficulty (Semrush, Ahrefs, DataForSEO Keywords Data, or Keyword Planner
    with spend).
  - Competitor keyword universes (Semrush Organic Research / Ahrefs Organic Keywords).
  - Cost tactic: pull volumes only for shortlisted cluster head terms. See `## Semrush`, `## Ahrefs`,
    `## DataForSEO` and `## Cost-optimisation playbook` in `references/tools.md`.
- **Skills:** seo-keywords, seo-content, seo-blog-builder, seo-blog-review, seo-onpage, seo-programmatic,
  seo-strategy.

---

## Pillar 3 — Backlinks & authority

**Scope**
- Link profile: referring domains, topical relevance, anchor distribution, followed/qualified mix, velocity.
- Brand mentions, linked and unlinked.
- Link reclamation: 404s with links, lost links, redirect gaps after migrations.
- Earning channels: digital PR, data studies, tools and calculators, partnerships, associations, local and
  community links, expert commentary.
- Qualification: `rel=sponsored` / `ugc` / `nofollow`. Google treats these as hints. §3.
- Risk management: link spam policy, manual actions, disavow.

**Strategy & prioritisation**
- **Reclamation first.** It costs nothing and is quick: links to 404s, and broken redirects from old
  domains or migrations.
- **Then assets worth linking to.** Original data, benchmarks, tools, definitive references.
- **Then outreach and PR around those assets.**
- **By site type:**
  - Local/SMB: associations, suppliers, sponsorships, local press.
  - SaaS: integration partners, marketplaces, docs cited by developers, comparison inclusion.
  - E-commerce: brand and manufacturer "where to buy" pages, gift guides, creators (sponsored links tagged).
  - Publishers: original reporting gets cited.
- **Disavow** only for a manual action for unnatural links, or for known past link schemes. A third-party
  "toxic score" alone is not a reason.

**Advanced tactics**
- **Link intersect:** domains linking to ≥2 competitors but not to you. This needs a paid backlink index.
- **Unlinked mention mining:** search for the brand in quotes, excluding your own domain, then request the
  attribution.
- **Internal PageRank sculpting via architecture**, not nofollow. Use the crawl CSV inlinks and depth.
- **Post-migration:** redirect every URL that has external links, prioritised by referring domains.

**Measurement**
- Referring domains over time (GSC *Links* is a free sample; Ahrefs Webmaster Tools is free for verified
  sites).
- Links won per campaign.
- Rankings and clicks of the linked pages compared with control pages.

**Failure modes**
- Buying links or PBNs.
- Guest-post networks.
- Large-scale link exchanges.
- Exact-match anchor patterns.
- Disavowing good links.
- Outreach spam that burns relationships.

**Tooling**
- **Free path:** GSC *Links* export, Bing Webmaster backlinks, Ahrefs Webmaster Tools for owned sites, and
  WebSearch footprints for prospecting.
- **Paid adds:** competitor backlink gap, link intersect, lost and new link alerts, anchor analysis (Ahrefs,
  Semrush Backlink Gap, Majestic, Moz). See `## Ahrefs`, `## Semrush`, `## Moz` and
  `## Cost-optimisation playbook` in `references/tools.md`.
- **Safety:** outreach and disavows are always gated; links that pass ranking value are never bought
  (`references/autonomy.md`). List each outreach
  message (recipient and text) and the disavow file as items in the end-of-run approval batch, and carry out only
  the items the user approves for that run.
- **Skills:** seo-links, seo-competitors.

---

## 4. On-page

**Checks**
- Title link: unique and descriptive, brand at the start or end. There is no character limit; the ~600 px
  truncation is an estimate (`title_px` in `page_audit.py`).
- Meta description: unique and factual; no length limit.
- One dominant `<h1>`.
- Hyphenated, readable URLs.
- Image alt text and filenames. CSS background images are not indexed.
- Internal links with descriptive anchors.
- Structured data for supported features only, with values that match the visible content. §3, §5.

**Scripts:** `page_audit.py`, `content_score.py`.
**Skills:** seo-onpage, seo-schema, seo-media.

## 5. Local

- **Ranking factors:** relevance, distance, prominence. You cannot pay for a better local ranking.
- **Business Profile eligibility:** no virtual offices or PO boxes. The name is the real-world name only.
  Use the fewest, most specific categories. §7.
- **Reviews:** on-site review markup: self-serving reviews are ineligible, and fake or undisclosed
  incentivised reviews are not allowed (§5). Google Business Profile reviews: no incentives of any kind
  (payment, discounts, free goods), disclosed or not, and no gating or selective solicitation (Maps
  user-contributed content policy, support.google.com/contributionpolicy/answer/7400114).
- **NAP consistency** is an industry convention, not a stated Google rule.
- **Geo-grid rank tracking** needs paid data (DataForSEO or Local Falcon).

**Skill:** seo-local.

## 6. AI search

- **Google**
  - Eligibility = indexed + snippet-eligible.
  - Controls: `nosnippet`, `max-snippet`, `data-nosnippet`, and the Search Console *Search generative AI*
    setting. §10.
  - The Search Generative AI performance report shows impressions only.
- **ChatGPT search** tracks Bing closely (vendor study). Ensure Bing indexing (Bing Webmaster Tools;
  IndexNow per autonomy level, `references/autonomy.md`).
- **Bot policy by purpose**
  - Allow the search bots (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Bingbot).
  - Decide separately on the training bots (GPTBot, ClaudeBot, CCBot, Google-Extended, Applebot-Extended).
  - The user-triggered fetchers (ChatGPT-User, Perplexity-User) may ignore robots.txt. Check with
    `robots_check.py`.
- **Content:** citable passages, statistics with sources, first-hand data, entity consistency (Organization
  `sameAs`). The GEO paper reports up to ~40% visibility gains on its benchmark; treat that as directional.
- **Measurement:** a frozen query set, 3–5 runs per engine, logged to CSV, then `ai_visibility.py` (Wilson
  95% CIs). Call a change only when the CI of the difference excludes 0 (`--compare` reports it); overlapping CIs don't rule one out.

**Paid trackers:** see `## AI visibility trackers` in `references/tools.md`.
**Skill:** seo-ai-search.

## 7. Measuring

**GSC**
- 16 months of retention.
- API: 25k rows per request, a ~50k rows/day cap per search type, top rows only.
- URL Inspection API: 2,000/day per site. §11.
- Exports: use query+page for cannibalisation, and equal, weekday-aligned windows. Drop the last ~3 days,
  which are incomplete.

**GA4**
- Conversions by landing page and channel.

**Bing Webmaster Tools**
- Backlinks and keyword data.
- The AI Performance report [3rd-party detail].

**Logs**
- Crawl frequency per section, and AI bot activity.

**Reporting**
- Looker Studio (free) on GSC and GA4.
- Report clicks and conversions per cluster.
- Annotate deployments and Google updates (Search Status Dashboard).

**Scripts:** `gsc_analyze.py`, `log_analyze.py`, `ai_visibility.py`.
**Skills:** seo-analytics, seo-strategy.

## 8. 90-day plan (expert cadence)

- **Weeks 1–2: baseline**
  - Crawl, logs and GSC/GA4 exports. `triage.py` over everything.
  - `research_store.py init`, then ingest the crawl and GSC exports, so every later step reuses them.
  - Fix P0 (access, indexability, canonical conflicts) at template level.
  - Register KPIs and control pages.
- **Weeks 3–6: technical and striking distance**
  - Close the P1 items.
  - Title/snippet experiments on CTR under-performers.
  - Optimise pages at positions 4–20.
  - Set up the CI gate.
- **Weeks 7–10: content**
  - Cluster map, then rewrites and merges of decaying or cannibalised pages.
  - New posts from `next-topics` with seo-blog-builder, in batches the reviewers can sign off.
  - 2–4 high-information-gain assets.
  - Schema only for supported features.
- **Weeks 11–13: authority and AI**
  - Reclamation, then outreach around the assets.
  - Bing indexing and AI bot policy.
  - First AI-visibility baseline (frozen queries, n ≥ 3).
  - Readout with ranges and confidence intervals, and the next-quarter roadmap (seo-strategy).
