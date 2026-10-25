---
name: seo-schema
description: Use when the user asks about structured data, schema markup, JSON-LD or rich results — "add schema to this page", "why don't we get rich results", "validate my JSON-LD", "product schema / merchant listing errors in Search Console", "review stars", "breadcrumb markup", "Organization schema", "is FAQ schema still worth it", "generate structured data for our templates". It finds the markup on a page, checks it against Google's current requirements, writes JSON-LD for each page type and says where to put it for each framework. Not for: general page audits (seo-onpage, seo-technical), visibility in AI answers (seo-ai-search), product feeds and Merchant Center strategy (seo-ecommerce), image and video indexing beyond VideoObject (seo-media), Business Profile work (seo-local).
---

# Structured data (schema.org JSON-LD)

Make every template carry valid, truthful JSON-LD for the Google features it is eligible for, and nothing that earns nothing or misleads.

## When to use / not
- **Use for:**
  - Detecting and validating markup.
  - Generating JSON-LD for a page type.
  - Fixing errors in Search Console enhancement or merchant-listing reports.
  - Deciding which types are worth adding.
  - Placing markup in Next.js, Nuxt, Astro, WordPress or Shopify.
- **Not for:**
  - Picking keywords or rewriting copy (seo-content).
  - Product feed policy (seo-ecommerce).
  - Video watch-page eligibility (seo-media).
  - Getting cited by AI. Structured data is **not required** for Google's AI features (google-rules §10).

## Inputs: decide, don't ask
Decide each input from evidence, record it under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| One URL per template: home, about, article, category, product, location, event, job, video page, profile, forum thread | The URLs given; URL patterns in the sitemap or a crawl | Home plus the URLs given |
| The visible facts each template shows, such as name, price, currency, availability, author, dates, address, hours and ratings. **Markup may only repeat what the page shows.** | The page itself: `page_audit.py --facts`, or the rendered DOM | Not visible: leave the property out |
| Stack and how markup is emitted: server-rendered, client-injected, Google Tag Manager, or an SEO plugin. Note any duplicate emitters | The repo; raw vs rendered HTML (step 2); several blocks with the same `@type` | No markup yet: plan server-rendered JSON-LD (step 2) |
| Search Console exports: Enhancements (per type), Merchant listings, Product snippets, and URL Inspection results | Exports already in the workspace; the URL Inspection API when Search Console access is configured | Run without them. Ask — batched at the end, naming what each adds |

## Workflow
0. **Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`), when `seo-research/` exists:
   ```bash
   mkdir -p seo-work
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export inventory --format csv > seo-work/store-inventory.csv
   ```
   - `seo-research/site.json` → `templates` and `stack` start the template and emitter inputs. Check them against the pages.
   - The inventory gives a live URL (`status` 200) per template; pick the one with the most `gsc_clicks`.
   - The markup checks still run on the live pages. Note what you reused and its age for *Assumptions* and the work log.
1. **Inventory every template, in parallel.**
   ```bash
   mkdir -p seo-work && i=0
   for u in "https://site/" "https://site/blog/post" "https://site/p/sku"; do
     i=$((i+1)); python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_audit.py" "$u" --facts > "seo-work/schema-$i.json" &
   done; wait
   ```
   From each file, read `summary.schema_types`, the `schema-*` findings and `facts.json_ld` (the parsed blocks).
2. **If markup is injected by JavaScript** (GTM, client components, headless storefronts):
   - Capture the rendered DOM in the built-in browser (`document.documentElement.outerHTML`) and save it.
   - Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_diff.py" URL --rendered seo-work/rendered.html`.
   - Google renders JS markup later. Most other parsers never do. Prefer server-rendered JSON-LD.
   - Don't trust a WebFetch summary for schema, because those tools often strip `<script type="application/ld+json">`. Use the scripts or a browser.
3. **Classify every `@type`:**
   - **Eligible:** a current Search Gallery feature (see Checks).
   - **Retired:** a `schema-limited-type` finding.
   - **Unknown to `schema_rules.py`:** check it by hand against the type's Google doc.
4. **Fix in this order:** parse errors, then missing required properties, then wrong nested values, then recommended properties you can truthfully fill. For each fix, point to the visible element the value comes from (parity).
5. **Generate missing markup from the templates below.**
   - Use one `@graph` per page.
   - Give every entity a stable `@id` (`https://site/#organization`, `{{url}}#article`) and reference it rather than repeating it.
6. **Place the markup for the stack** (see Placement), per autonomy level (references/autonomy.md). Remove duplicate emitters, e.g. a theme and a plugin both emitting Product.
7. **Validate:**
   - Re-run `page_audit.py` on staging or production, or with `--file` on the rendered HTML.
   - After the change is live and recrawled, the URL Inspection API (free, 2,000 calls/day/site) reports the rich results Google detected on each indexed URL and their issues (`richResultsResult`). Record them as `[measured]`; that closes the check without a person.
   - The [Rich Results Test](https://search.google.com/test/rich-results) and the [Schema Markup Validator](https://validator.schema.org/) have no public API (google-rules §11), so unattended runs never drive them. They are Reserve: use them in a session the user watches, for a type `page_audit.py` doesn't cover or a page not indexed yet.
8. **Prioritise:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" seo-work/schema-*.json`.
9. **Monitor:** Search Console → Enhancements (one report per type), Merchant listings and Product snippets. Counts update over days to weeks after recrawl.
10. **Write back to the research store**, when it exists: record the templates and how each one emits markup (server-rendered, plugin, GTM) in `seo-research/site.json` → `templates` and `stack`, so the next skill doesn't rediscover them. Markup findings stay in `seo-work/`; the store has no dataset for them.

## Checks
**What `schema_rules.py` checks, and what it doesn't.**
- **Checked:** top-level presence of required and recommended properties per `@type` (including `@graph`, nested typed nodes such as ProductGroup, OfferShippingDetails and MerchantReturnPolicy, LocalBusiness subtypes, and the presence of Event `location.address`), retired types, and missing `@context`.
- **Not checked, so read the JSON yourself:**
  - Nested values: `offers.price` > 0, `reviewRating.ratingValue`, the contents of `location.address` (only its presence is checked), and any nested object without an `@type` (e.g. an untyped `shippingDetails` or `hasMerchantReturnPolicy` isn't checked against the OfferShippingDetails/MerchantReturnPolicy rules).
  - Image size and aspect ratio.
  - Date formats.
  - Parity with visible content.
  - Microdata and RDFa (only their item types are listed).
- Note that it flags `Course` as retired. That refers to Course *info*. The Course **list** carousel (an ItemList of Course) still exists.

**Current Google Search Gallery** (25 features, google-rules §5) [Google doc]:
- Article, Breadcrumb (desktop only), Carousel, Course list, Dataset, Discussion forum.
- Education Q&A, Employer aggregate rating, Event, Image metadata, Job posting, Local business.
- Math solver, Movie, Organization, Product (snippets, merchant listings, variants, shipping/returns, loyalty).
- Profile page, Q&A, Recipe, Review snippet, Software app, Speakable, Subscription/paywalled content, Vacation rental, Video.

**Retired:**
- FAQ: stopped showing 2026-05-07.
- HowTo: removed in 2023.
- Sitelinks search box (`WebSite` → `SearchAction`): removed 2024-11-21.
- Removed 2025-09-09: Course info, Estimated salary, Learning video, Special announcement, Vehicle listing.
- ClaimReview and Book actions: phased out.
- Practice problems: removed 2026-01-06.
- Leaving retired markup in place is harmless, but don't add it expecting a rich result.

**Required and key properties** (google-rules §5) [Google doc]:

| Type | Required | Must-know rules |
|---|---|---|
| Article / BlogPosting / NewsArticle | none | Rec `headline`, `image` (several, each ≥50K pixels, 16:9 + 4:3 + 1:1), `datePublished`, `dateModified` (ISO 8601), `author` (Person/Organization with `name`, plus `url` or `sameAs`; one `author` per person; name only in `name`) |
| BreadcrumbList | `itemListElement` with **≥2** ListItems | Each has `position`, `name`, `item`. `item` may be omitted only on the last crumb |
| Product (snippet) | `name` + one of `review` / `aggregateRating` / `offers` | Offer: `price`. AggregateOffer: `lowPrice` + `priceCurrency`. A past `priceValidUntil` can suppress the result. Pros and cons (`positiveNotes`/`negativeNotes`, ≥2) on **editorial** review pages only |
| Product (merchant listing) | `name`, `image`, `offers` as **Offer** (not AggregateOffer) with `price` > 0 + `priceCurrency` | `shippingDetails` → OfferShippingDetails: `deliveryTime` (`handlingTime`/`transitTime` with min/max and unitCode `DAY`), `shippingDestination.addressCountry`, `shippingRate` (value + currency; 0 = free). `hasMerchantReturnPolicy`: `applicableCountry`, `returnPolicyCategory`, `merchantReturnDays` if the window is finite. GTINs are numeric, never URLs. A Merchant Center feed overrides the markup |
| ProductGroup (variants) | `name` | `productGroupID` on the group, or `inProductGroupWithID` on every variant. `variesBy` (schema.org color/size/material/pattern/suggestedAge/suggestedGender). `hasVariant` ⇄ `isVariantOf`. Single-page: one canonical plus a preselect URL per variant. Multi-page: no group `url`, full group repeated on each page |
| Review / AggregateRating | Review: `author` (name <100 chars), `itemReviewed` (unless nested), `reviewRating.ratingValue`. Aggregate: `ratingValue` + `ratingCount` or `reviewCount` | **Self-serving** reviews of your own LocalBusiness/Organization on your own site are ineligible. No fake or undisclosed incentivised reviews |
| Organization | none | `logo` ≥112×112 px, crawlable, readable on white. Put it on the home or about page. Use the most specific subtype (`OnlineStore`, `EducationalOrganization`…). `sameAs` lists official profiles |
| LocalBusiness | `name`, `address` | `telephone` with country code, `geo` ≥5 decimals, `openingHoursSpecification` (hh:mm:ss), `priceRange` <100 chars |
| Event | `name`, `startDate`, `location` (Place with `address`) | **Physical events only.** Use `eventStatus` for changes. When rescheduling, keep `startDate` updated and add `previousStartDate` |
| JobPosting | `title`, `description`, `datePosted`, `hiringOrganization`, `jobLocation` | Fully remote: `jobLocationType: TELECOMMUTE` + `applicantLocationRequirements`. Expire closed jobs (`validThrough`, 404/410 or remove the markup) |
| VideoObject | `name`, `thumbnailUrl`, `uploadDate` | Rec `contentUrl`/`embedUrl`, `duration`, `description`, `hasPart` (Clip). The watch-page rule lives in seo-media |
| Recipe | `name`, `image` | Rec ingredients, instructions, times, yield, nutrition.calories |
| SoftwareApplication | `name`, `offers.price` (0 if free), `aggregateRating` or `review` | Rec `applicationCategory`, `operatingSystem` |
| ProfilePage | `mainEntity` (Person/Organization) with `name` | Rec `dateCreated`, `dateModified`, `sameAs`, `image` |
| DiscussionForumPosting | `author.name`, `datePublished`, one of `text`/`image`/`video` | Q&A forums use QAPage instead |
| Dataset | `name`, `description` (50–5000 chars) | Feeds Dataset Search only |

**General rules:**
- Prefer JSON-LD.
- Use absolute URLs and ISO 8601 dates.
- No empty strings or placeholders.
- Mark up the main visible content only, never hidden content.
- Keep one entity per real-world thing, linked by `@id`.
- Use the same language as the page (`inLanguage` should match `<html lang>`).

## Templates
Replace every `{{…}}` with a value visible on the page. If there's no value, delete the property. Never ship braces.
```json
{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","@id":"{{origin}}/#organization","name":"{{brand}}","url":"{{origin}}/",
  "logo":{"@type":"ImageObject","url":"{{logo_url}}"},"sameAs":["{{official_profile_urls}}"]},
 {"@type":"WebSite","@id":"{{origin}}/#website","url":"{{origin}}/","name":"{{brand}}","publisher":{"@id":"{{origin}}/#organization"}},
 {"@type":"BreadcrumbList","itemListElement":[
  {"@type":"ListItem","position":1,"name":"{{crumb1}}","item":"{{crumb1_url}}"},
  {"@type":"ListItem","position":2,"name":"{{page_title}}"}]}]}
```
```json
{"@context":"https://schema.org","@type":"BlogPosting","@id":"{{url}}#article","headline":"{{h1}}","image":["{{img_16x9}}","{{img_4x3}}","{{img_1x1}}"],
 "datePublished":"{{iso_published}}","dateModified":"{{iso_modified}}","author":[{"@type":"Person","name":"{{author}}","url":"{{author_page}}"}],
 "publisher":{"@id":"{{origin}}/#organization"},"mainEntityOfPage":"{{url}}"}
```
```json
{"@context":"https://schema.org","@type":"Product","@id":"{{url}}#product","name":"{{name}}","image":["{{img}}"],"description":"{{desc}}",
 "sku":"{{sku}}","gtin":"{{gtin}}","brand":{"@type":"Brand","name":"{{brand}}"},
 "offers":{"@type":"Offer","url":"{{url}}","price":"{{price}}","priceCurrency":"{{ISO4217}}","availability":"https://schema.org/InStock",
  "itemCondition":"https://schema.org/NewCondition",
  "shippingDetails":{"@type":"OfferShippingDetails","shippingRate":{"@type":"MonetaryAmount","value":"{{ship_cost}}","currency":"{{ISO4217}}"},
   "shippingDestination":{"@type":"DefinedRegion","addressCountry":"{{CC}}"},
   "deliveryTime":{"@type":"ShippingDeliveryTime","handlingTime":{"@type":"QuantitativeValue","minValue":0,"maxValue":1,"unitCode":"DAY"},
    "transitTime":{"@type":"QuantitativeValue","minValue":1,"maxValue":5,"unitCode":"DAY"}}},
  "hasMerchantReturnPolicy":{"@type":"MerchantReturnPolicy","applicableCountry":"{{CC}}",
   "returnPolicyCategory":"https://schema.org/MerchantReturnFiniteReturnWindow","merchantReturnDays":"{{days}}"}}}
```
- **ProductGroup:** `{"@type":"ProductGroup","name":…,"productGroupID":"{{parent_sku}}","variesBy":["https://schema.org/color"],"hasVariant":[{Product…}]}`.
- **LocalBusiness:** the most specific subtype, with `name`, `address` (PostalAddress: streetAddress, addressLocality, postalCode, addressCountry), `telephone` (+country code), `geo`, `openingHoursSpecification` and `url`. Reference the Organization with `parentOrganization` → `@id`.
- **Event:** `name`, `startDate`, `endDate`, `eventStatus`, `location` (Place + PostalAddress), `offers` (url, price, priceCurrency, availability), `organizer`, `image`.
- **JobPosting:** the required five, plus `validThrough`, `employmentType`, `baseSalary` (MonetaryAmount + QuantitativeValue with unitText `HOUR`/`MONTH`/`YEAR`) and `identifier`.
- **VideoObject, Recipe, SoftwareApplication, ProfilePage, DiscussionForumPosting, Dataset:** fill the required columns in the table, then the recommended properties you can show.

## Placement
- **Next.js App Router:**
  - Render the script in the server component (`page.tsx` or `layout.tsx`) so it lands in the raw HTML:
    `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }} />`
  - Don't use `next/script` for JSON-LD, and don't build it in a client component.
  - Pages Router: inside `next/head`.
- **Nuxt:** `useHead({ script: [{ type: "application/ld+json", innerHTML: JSON.stringify(data) }] })`, in SSR mode.
- **Astro:** `<script type="application/ld+json" set:html={JSON.stringify(data)} />`.
- **WordPress:**
  - Yoast and Rank Math each emit an `@graph`. Extend through their filters (`wpseo_schema_graph`, `rank_math/json_ld`) rather than adding another plugin.
  - WooCommerce emits Product too, so de-duplicate.
- **Shopify:**
  - Themes emit Product/Organization in Liquid, often via `{{ product | structured_data }}`.
  - Check whether apps (reviews, SEO apps) emit a second Product, and keep one.
- **GTM-injected markup:** Google can read it after rendering, but it's fragile and invisible to non-rendering parsers. Move it server-side.

## Data: free vs paid
- **Free (enough for most sites):**
  - `page_audit.py`, `render_diff.py`, `triage.py`.
  - Rich Results Test, Schema Markup Validator (no API: watched sessions only).
  - Search Console enhancement and merchant-listing reports.
  - URL Inspection API (2,000/day/site).
- **Screaming Frog** (paid licence; free tier is 500 URLs): validates structured data across a whole crawl, including JS rendering.
  - Justified when the site has thousands of templated URLs, or when markup varies per page (e.g. per-SKU offers).
  - Our crawler runs the same top-level checks, but without JS and without nested-value validation.
- **Sitebulb:** a similar capability.
- **Semrush / Ahrefs site audits:** report only whether markup is present. Not worth buying for schema alone.
- Licences and cost tactics: `${CLAUDE_PLUGIN_ROOT}/references/tools-paid.md` (## Screaming Frog, ## Cost-optimisation playbook).

## Output
For each template:
- Types found [measured].
- Eligible features [Google doc].
- Errors and warnings with the JSON path.
- Parity issues, each naming the visible element vs the markup value.
- The proposed JSON-LD as a diff in the right file.
- The validation step and the Search Console report to watch.
- Assumptions: the templates, stack and emitters decided from evidence, and the evidence for each, plus the research-store data reused and its age.
- End with the `triage.py` plan.

## Pitfalls & myths
- **Structured data doesn't rank you.** It makes you eligible for features, and Google may still not show them.
- **Adding FAQ, HowTo or SearchAction for "stars or more SERP space"** earns nothing in 2026.
- **Fake ratings and markup values that differ from the page** (price, availability) risk manual actions and merchant-listing disapprovals.
- **Self-serving review stars on your own business** are ineligible, so don't promise them.
- **Several plugins each emitting Product or Organization** produce conflicting entities. Keep one emitter.
- **`@type` arrays are valid.** `["Product","Car"]` is fine.
- **Markup on noindexed or canonicalised-away URLs is never used.**

## Log the work
Append an entry to `SEO-WORKLOG.md` in the project root, using the format in `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`. Include:
- The templates and URLs touched.
- Types added, changed or removed.
- Evidence files (`seo-work/schema-*.json`).
- Validation results (`page_audit.py` schema findings, the rich results URL Inspection detected, and Rich Results Test or Schema Markup Validator pass/fail when a watched session ran them).
- The Search Console report to recheck, and the recheck date (about 2–4 weeks).
