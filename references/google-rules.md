# Verified search rules (checked 2026-10-24)

Primary sources: Google Search Central (developers.google.com/search, /crawling), web.dev, Bing Webmaster blog and guidelines,
vendor bot docs. "upd" = the page's own last-updated stamp at check time. Items in §12 are NOT verified —
do not state them as fact. Re-verify anything older than ~6 months before relying on it for a client.

## 1. Crawling & indexing

**Baseline (only 3 requirements):** Googlebot not blocked · page returns HTTP 200 · indexable content.
Eligibility ≠ guaranteed indexing. (essentials/technical, upd 2025-12-18)

**robots.txt** (upd 2026-10-23)
- Max **500 KiB**; content after is ignored. UTF-8; BOM and invalid lines ignored.
- Root of each protocol+host+port; every subdomain needs its own.
- Fields: `user-agent`, `allow`, `disallow`, `sitemap` (absolute URL, ungrouped, repeatable).
  `crawl-delay` unsupported by Google (Bing and Anthropic honour it).
- Most specific user-agent group wins; same-agent groups merge; never combined with `*`; file order irrelevant.
- Longest matching path wins; tie → allow. `*` = any chars, `$` = end. Paths case-sensitive; agent names not.
- Fetch outcomes: 3xx followed ≥5 hops then treated as 404 · 4xx (except 429) = no restrictions ·
  **5xx/429/network error: crawling stops 12 h, then last good copy up to 30 days**, then no-robots if site is up.
- Cached up to 24 h. **Disallow does not deindex** — a blocked URL can be indexed without content.

**Robots meta / X-Robots-Tag** (upd 2026-03-24)
- Supported: `all`, `noindex`, `nofollow`, `none` (=noindex,nofollow), `nosnippet`, `indexifembedded` (with noindex),
  `max-snippet:n` (0 none, -1 unlimited), `max-image-preview:none|standard|large`, `max-video-preview:n`,
  `notranslate`, `noimageindex`, `unavailable_after:<date>`. `data-nosnippet` attribute on span/div/section.
- Ignored by Google: `noarchive`, `nocache`, `nositelinkssearchbox`.
- Bing uses them for Copilot (Bing Webmaster Guidelines §10; undated page, rewritten around 2026-02, read 2026-10-24):
  `NOARCHIVE` keeps content out of Copilot answers and grounding results; `NOCACHE` limits Copilot to the URL, title
  and snippet.
- Most restrictive wins when combined. Meta robots is read even outside `<head>` (2026-03-24).
- Use X-Robots-Tag for PDFs/images/video.
- noindex is only seen if crawlable — **never disallow a URL you want removed by noindex**.
- Google may skip rendering on noindex → removing noindex via JS may never take effect.

**Canonicalization** (upd 2026-07-10)
- Strong: redirects, rel=canonical (HTML or HTTP Link header). Weak: sitemap inclusion. Also HTTPS preference, hreflang clusters.
- rel=canonical only in `<head>`, absolute URL, self-canonical on canonical pages, one value; JS may set it but must match raw HTML.
- Don't canonicalize with robots.txt, noindex or the removal tool; no fragment canonicals; no conflicting signals (sitemap vs tag).

**HTTP status** (upd 2026-02-04)
- 200 with error/empty content → soft 404. Redirects: up to **10 hops**; 301/308 strong canonical signal, 302/303/307 weak.
- All 4xx except 429 handled identically — **404 = 410** in practice. 429/5xx slow crawling; persistent → drop.
- Don't use 401/403 to slow crawling. Site moves: chains ideally ≤3 hops, never ≥5.

**Fetch limits** (upd 2026-06-12): Google crawlers fetch 15 MB by default; **Googlebot for Search indexes only the
first 2 MB of HTML** (and 64 MB of PDF), uncompressed. HTTP/1.1 and HTTP/2; gzip/deflate/br; ETag preferred.

**Crawl budget** (upd 2026-07-22): matters for ~1M+ pages changing weekly, 10k+ daily, or large
"Discovered – currently not indexed". Fix: consolidate duplicates, 404/410 removed pages, fix soft 404s,
accurate lastmod, no chains, support 304. Don't noindex to save budget; don't toggle robots.txt.

**JavaScript SEO** (upd 2026-03-04): crawl → render (deferred) → index. Only `<a href>` links are followed.
History API not `#/` routes. SPA soft 404s: redirect to a 404 URL or inject noindex. Shadow DOM flattened.
Fingerprint asset names. SSR/prerendering recommended.

**Sitemaps** (upd 2026-07-08): ≤**50,000 URLs / 50 MB uncompressed** per file, index for more. Absolute canonical URLs.
`lastmod` used only if consistently accurate (significant change only). `priority`/`changefreq` ignored.
Submit in Search Console or via robots.txt `Sitemap:` — a hint only.
- Image: `image:image/image:loc`, ≤1,000 per `<url>`, CDN hosts fine; caption/title/geo/license deprecated.
- Video: required `thumbnail_loc`, `title`, `description` (≤2048), `content_loc` or `player_loc`.
- News: last **2 days** only, ≤**1,000** `news:news`; `publication(name, language)`, `publication_date`, `title`.

**IndexNow:** GET `/indexnow?url=&key=` or POST ≤10,000 URLs; key file `/{key}.txt`. Bing, Yandex, Seznam, Naver,
Yep, Internet Archive, Amazonbot. **Google does not participate.**

## 2. Page experience

| Metric (p75, field, per device) | Good | Needs improvement | Poor |
|---|---|---|---|
| LCP | ≤2.5 s | ≤4.0 s | >4.0 s |
| INP | ≤200 ms | ≤500 ms | >500 ms |
| CLS | ≤0.1 | ≤0.25 | >0.25 |

- Pass = all three good. INP replaced FID in 2024. LCP candidates: img, svg `<image>`, video poster/first frame,
  CSS url() backgrounds, block text.
- No single "page experience" ranking signal; CWV are used but relevance wins (upd 2026-09-22).
  HTTPS, mobile usability, no intrusive interstitials, non-distracting ads matter for users.
- **Mobile-first:** only the mobile version is indexed — same content, headings, structured data, titles,
  meta, robots, alt text. Don't lazy-load primary content on interaction.
- Interstitials: no full-page overlays hiding content; legal gates as overlays; verified Googlebot past age gates.

## 3. On-page

- **Title links** come from `<title>`, main heading/h1, og:title, prominent text, anchors, WebSite data.
  **No character limit** — truncated to device width. Unique, descriptive, brand at start or end with a delimiter,
  one dominant h1, same language as page. Rewrite triggers: half-empty, stale dates, boilerplate, duplicated site name.
- **Snippets** come mainly from page content; meta description used when better. **No length limit.**
  Unique, factual (price, date, author), no keyword lists. Controls: nosnippet, max-snippet, data-nosnippet.
- **Headings:** no numeric rule; clear hierarchy, one prominent main title.
- **Images:** indexable BMP/GIF/JPEG/PNG/WebP/SVG/AVIF from `<img src>`/`<picture>`; **CSS backgrounds are not indexed**.
  Descriptive alt (not stuffed); descriptive filenames; near relevant text; stable URLs; preferred image via
  primaryImageOfPage/og:image; `max-image-preview:large` for big previews.
- **Links:** each important page needs ≥1 internal link; descriptive anchors (no "click here");
  `rel=sponsored|ugc|nofollow` on outbound as appropriate (hints — Search Central blog 2019-09, "Evolving nofollow").
- **URLs:** hyphens not underscores; readable words; percent-encode; one case; no session IDs or `#` content;
  avoid parameter/filter explosions and infinite calendars.

## 4. Content & spam

- **Helpful content** (upd 2026-10-05): original info/analysis, complete coverage, worth bookmarking/citing,
  visible author expertise, no easily checked errors. Red flags: mass topics, summarising others with no added value,
  trend chasing, fake freshness (date changes), targeting word counts — **no preferred length**.
  The helpful content *system* was folded into core ranking in March 2024 (ranking systems guide, upd 2025-12-10).
- **E-E-A-T** isn't a direct factor; **trust matters most**; YMYL gets more weight. Who/How/Why:
  real bylines (no fake authors or AI headshots; don't make AI the author), disclose automation where readers would
  expect it (**recommended, not required**), made for people.
- **AI content** (upd 2026-10-01): allowed; mass low-value AI pages = scaled content abuse. Fact-check; review AI
  titles/meta/schema/alt. Merchant Center: AI images need IPTC `TrainedAlgorithmicMedia`; label AI product text.
- **Machine/AI translation:** allowed. Scaled content abuse names translating only as an automated transformation of
  scraped content used to make many pages "where little value is provided to users" (spam policies, upd 2026-08-28).
  **2025-06-11:** the advice to block auto-translated pages with robots.txt was removed, "a docs-only change, no change
  in behavior" (Search Central updates log). Staff guidance, not policy (office hours, June 2024): have a native
  speaker review and fix low-quality auto-translations (Illyes); no markup labels a translation, so noindex one you
  are not happy with (Mueller).
- **Spam policies** (upd 2026-08-28): cloaking, doorway abuse, expired domain abuse, hidden text & link abuse,
  keyword stuffing, link spam, machine-generated traffic, malware/malicious practices (incl. **back-button hijacking**,
  2026-04-13), misleading functionality, **scaled content abuse**, scraping, sneaky redirects, thin affiliation,
  UGC spam, **site reputation abuse** (first-party oversight no longer an automatic exemption; in the **EEA since
  2026-08-28 such pages are ranked separately** rather than manual actions), legal/personal-info removals,
  policy circumvention, scam & fraud. Attempts to manipulate generative AI responses are covered (2026-05-15).

## 5. Structured data

**Search Gallery (upd 2026-10-16), 25 features:** Article, Breadcrumb (desktop), Carousel, Course list, Dataset,
Discussion forum, Education Q&A, Employer aggregate rating, Event, Image metadata, Job posting, Local business,
Math solver, Movie, Organization, Product (snippets, merchant listings, variants, shipping/returns, loyalty),
Profile page, Q&A, Recipe, Review snippet, Software app, Speakable, Subscription/paywalled, Vacation rental, Video.

**Gone:** FAQ (stopped showing **2026-05-07**) · HowTo (2023) · Sitelinks search box (2024-11-21) ·
Course info, Estimated salary, Learning video, Special announcement, Vehicle listing (2025-09-09) ·
ClaimReview, Book actions (2025) · Practice problems (2026-01-06). Dataset → Dataset Search only.

**Key requirements** (R = required, rec = recommended):
- Article: R none; rec headline, image (≥50k px, 16:9/4:3/1:1), datePublished, dateModified, author (name+url).
- Product snippet: R name + one of review/aggregateRating/offers. Offer R price; rec availability, priceCurrency.
- Merchant listing: Product R name, image, offers; Offer R price>0 + priceCurrency; rec gtin/mpn/brand/sku,
  shippingDetails (deliveryTime, shippingDestination.addressCountry, shippingRate), hasMerchantReturnPolicy
  (applicableCountry, returnPolicyCategory, merchantReturnDays). Feed > Content API > MC settings > markup.
- ProductGroup: productGroupID, variesBy, hasVariant/isVariantOf.
- Review: author, itemReviewed, reviewRating.ratingValue. AggregateRating: ratingValue + ratingCount|reviewCount.
  **Self-serving reviews** (a business reviewing itself on its own site) are ineligible. **No fake or undisclosed
  incentivised reviews** (money, discounts, vouchers, free products) on the page or in markup
  (structured-data/review-snippet, upd 2026-09-08).
- BreadcrumbList: ≥2 ListItems with position, name, item (item optional on last).
- Organization: R none; rec name, url, logo (≥112×112), sameAs, contactPoint, address, legalName, vatID.
- LocalBusiness: R name, address; rec geo (≥5 decimals), openingHoursSpecification, telephone (+country code), url, priceRange.
- Event: R name, startDate, location with address — **physical events only** (online removed June 2025).
- JobPosting: R datePosted, description, hiringOrganization, jobLocation, title; expire closed jobs.
- VideoObject: R name, thumbnailUrl, uploadDate; rec contentUrl/embedUrl, duration, Clip/SeekToAction.
- Recipe: R name, image. SoftwareApplication: R name, offers.price, aggregateRating|review.
- ProfilePage: R mainEntity with name. DiscussionForumPosting: R author.name, datePublished, text|image|video.

## 6. International

- hreflang via HTML, HTTP header or sitemap (equivalent). **Bidirectional or ignored.** Self-reference included.
- Codes: ISO 639-1 language (+ ISO 15924 script) + optional ISO 3166-1 region. **`UK`, `EU`, `UN` invalid → en-GB.**
  Region alone invalid. `x-default` for unmatched users.
- Google detects language from visible content — ignores `lang` attr and URL.
- Localized versions are duplicates **only if the main content stays untranslated** (localized-versions, upd 2026-09-21).
- With hreflang, the canonical points at a page **in the same language**, or the best substitute language if none
  exists — never at another language version (consolidate-duplicate-urls, upd 2026-07-10).
- **Partial clusters are fine:** some languages can be left out on some pages; Google still processes the pairs that
  point to each other (localized-versions).
- Geo signals: ccTLD, hreflang, local address/phone/currency, links, GBP. Prefer ccTLD/subdomain/subfolder over params.
- Googlebot crawls mostly from US IPs with **no Accept-Language** → use separate locale URLs, not locale-adaptive serving.

## 7. Local

- Local ranking = **relevance, distance, prominence**; you can't pay for local rank.
- GBP: in-person contact required; virtual offices ineligible; real-world name only (no keywords/taglines);
  exact address, no PO boxes; service-area businesses hide address; local controlled phone, no redirects;
  fewest most-specific categories; accurate regular and special hours.
- NAP consistency across the web is an industry convention, not a stated Google rule.

## 8. Video, Discover, News, e-commerce

- **Video:** must be on a watch page whose main purpose is that video; thumbnail ≥60×30; not hidden behind interaction.
- **Discover:** no markup needed; images ≥1200 px wide (>300k px, 16:9) + `max-image-preview:large`; avoid clickbait.
- **News:** no application; automatic; stable section URLs.
- **Faceted navigation:** block crawl of facet params with robots.txt (or fragments) if they shouldn't be crawled;
  if crawled: `&` separator, consistent order, **404 for empty/nonsense combinations**.
- **Pagination:** unique `?page=n` URLs linked with `<a href>`; **don't canonicalize to page 1**; `rel=next/prev` unused.

## 9. Site moves

- Verify all variants of old and new; copy disavow; check manual actions; map every URL (sitemaps, logs, analytics,
  links report, CMS, images/CSS/JS).
- Server-side **301/308**, one hop; never mass-redirect to home; **keep redirects ≥1 year**.
- Permanent redirects don't lose PageRank. Many old URLs redirected to one irrelevant URL (e.g. home) may be treated
  as a soft 404. Google crawls the new site more heavily after a move, so make sure the server has capacity.
  Change one thing at a time (domain, then CMS, then layout), not all at once.
  (crawling-indexing/site-move-with-url-changes, upd 2026-08-20)
- New site: self-canonicals, updated hreflang/internal links, new sitemap. Expect weeks of fluctuation.
- **Change of Address tool**: domain/subdomain changes only (not http→https, paths, www, CDN); same owner;
  homepage 301 in place; forwards signals **180 days**; keep old domain ≥1 year.

## 10. AI search

- **AI Overviews / AI Mode eligibility = indexed + snippet-eligible.** No special schema, no "AI files" needed.
  Controls: nosnippet, data-nosnippet, max-snippet, noindex. Traffic counts inside Search Console "Web".
- Search Console → Settings → **Search generative AI**: site-wide opt-out of AI Overviews/AI Mode/Discover gen-AI
  (not ranking, not training); ~1–2 days; worldwide since 2026-08-31.
- Google AI optimisation guide (upd 2026-07-10): AEO/GEO = SEO. **llms.txt is not used by Google Search.**
  Chunking/rewriting "for AI" not required; structured data not required. Search Generative AI performance report
  (2026-06-03) shows impressions only.
- Crawler tokens: **Google-Extended** (Gemini training/grounding — not Search) · GPTBot (training) ·
  **OAI-SearchBot** (ChatGPT search) · ChatGPT-User (user fetch; robots may not apply) · OAI-AdsBot ·
  ClaudeBot (training) · **Claude-SearchBot** (search) · Claude-User · **PerplexityBot** (search index) ·
  Perplexity-User (generally ignores robots) · CCBot · Applebot / Applebot-Extended (training opt-out, no crawling) ·
  **Bingbot** (Bing + Copilot; no separate AI bot).
- Known about source selection (vendor studies, directional): ChatGPT search overlaps Bing's top results far more than
  Google's; AI Overview citations correlate with organic rank; engines overlap little with each other.
  GEO paper (KDD 2024): citations, quotations and statistics raised visibility up to ~40% on its benchmark.
- Practical: be indexed in Bing; allow search bots separately from training bots.

## 11. Free official data sources

- **Search Console API:** ≤25,000 rows/request, ~50k rows/day/search type (top rows), 2–3 day delay, **16 months**
  retention; 1,200 QPM per site/user. URL Inspection API: **2,000/day, 600/min per site**.
- **PageSpeed Insights v5:** key optional (keyless shares a small quota — create a free key). Returns CrUX + Lighthouse.
- **CrUX API:** key required, 150 QPM; 28-day window; History API up to 40 weekly periods.
- **Bing Webmaster Tools API:** key; URL submission quota per site (check GetUrlSubmissionQuota).
- **Google Trends API:** alpha, application-only (2025-07). **Indexing API:** JobPosting/BroadcastEvent only.
- Rich Results Test: no public API found. Mobile-Friendly Test retired Dec 2023.
- **GSC vs GA4** (upd 2026-01-07): totals won't match (attribution, canonical URLs, consent, missing tags, non-HTML
  files, PT time zone, bots); the general trends should be similar.

## 12. Not verified — do not hard-code

PSI quota numbers · sitemap ping deprecation date · mobile-first "after 2024-07-05" cutoff · FAQ removal from
GSC report/RRT/API · BWT AI Performance details · Bing guideline specifics, except those §1 and §10 state (e.g.
Copilot's NOARCHIVE/NOCACHE handling) · dynamic rendering wording · Indexing API quotas · CrUX eligibility thresholds ·
News transparency policy details · all vendor AI-citation statistics · NAP as a Google rule · INP exact switch date.
