---
name: seo-local
description: Use for local and maps visibility — "local SEO", "Google Business Profile", "rank in Google Maps / the map pack", "near me searches", "NAP consistency", "local citations", "how to get more Google reviews", "location pages", "service area business", "multi-location SEO", "our listing got suspended", "Apple Maps / Bing Places". Covers Business Profile optimisation within Google's guidelines, ethical review strategy, NAP and citations, LocalBusiness schema, location and service-area pages, local rank checks and local links. Profile edits, listing corrections and review requests go to the end-of-run approval batch, and Claude carries out only the approved ones. Not for: general on-page work (seo-onpage), schema syntax (seo-schema), language or country targeting (seo-international), link building beyond local (seo-links).
---

# Local SEO

Win local-pack and maps visibility through accurate, verified business data, a real reputation, and location pages that are genuinely useful.

## When to use / not
- **Use for:**
  - Single- or multi-location businesses with in-person contact: a storefront, or a service at the customer's location.
  - Business Profile audits.
  - Planning reviews and citations.
  - Location and service-area pages.
  - Local schema.
  - Suspension risk.
- **Not for:**
  - Online-only businesses with no physical contact. They're ineligible for a Business Profile, so send them to seo-content and seo-links.
  - International targeting (seo-international).

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| **Ground-truth details:** legal or real-world name exactly as on signage; each location's address, or service areas; a local phone number the business controls; hours, including special hours; primary services; website URL per location | Location and contact pages, the footer, LocalBusiness schema, the public Business Profile and maps listings (WebSearch) | The location page's own details, marked provisional. Where sources disagree, which string is real is the owner's call: **ask — batched at the end** |
| **Business Profile access** | An authorised connector, or screenshots or exports from the owner. Never request passwords | **Ask — batched at the end.** Meanwhile read the public listing |
| **Facts read from the profile, not invented:** current categories, review count and rating | The public listing (WebSearch, maps) | `[needs data]` |
| Profile performance (searches, calls, directions, website clicks) | Owner access only | **Ask — batched at the end.** `[needs data]` until then |
| Target services × areas | Service and location pages, `areaServed` in schema, navigation | The services and areas the site already names |
| Competitors who appear in the map pack | WebSearch `"<primary service> <city>"` per area (indicative only, see step 7) | The businesses that recur across those results |
| Country or market (citation sources differ by country) | ccTLD, addresses, phone country code, `<html lang>` | The country of the business address |

## Workflow
0. **Read the research store first** (`seo-research/`, `${CLAUDE_PLUGIN_ROOT}/references/research-store.md`) when the project has one:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export keywords --locale en --format json > seo-work/store-keywords-en.json
   ```
   - "<service> <city>" keywords with demand evidence show which service × area pages are worth having (Inputs).
   - Their SERP snapshots younger than the `serps` TTL give step 7's organic results and whether a local pack shows (`local_pack` in `features`). WebSearch only the rest. The store holds no map-pack businesses, so the competitor check in Inputs still runs.
1. **Eligibility and risk** (google-rules §7) [Google doc]:
   - The business needs in-person contact during its stated hours.
   - Virtual offices are ineligible. PO boxes aren't allowed. A co-working space needs signage and staff on site.
   - A service-area business hides its address and uses one central profile.
   - **Each location gets one profile.** Look for duplicates and for keyword-stuffed names; both are suspension risks.
2. **Website audit, every location page in parallel:**
   ```bash
   mkdir -p seo-work; i=0
   for u in https://site/locations/tbilisi https://site/locations/batumi; do
     i=$((i+1))
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_audit.py" "$u" > "seo-work/local-audit-$i.json" &
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/content_score.py" "$u" --keyword "<service> <city>" > "seo-work/local-content-$i.json" &
   done; wait
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compare_pages.py" https://site/locations/tbilisi https://site/locations/batumi --no-own-page > seo-work/local-cityswap.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compare_pages.py" https://site/locations/tbilisi https://site/about --no-own-page > seo-work/local-template.json
   python3 -c "import json; t = set(json.load(open('seo-work/local-template.json'))['shared_competitor_phrases']); print([p for p in json.load(open('seo-work/local-cityswap.json'))['shared_competitor_phrases'] if p not in t])"
   ```
   - The last three commands are a **city-swap test** (heuristic). With `--no-own-page`, `shared_competitor_phrases` is the complete list, in a stable order, of phrases found on both pages (among each page's most frequent two- and three-word phrases). It includes header, nav and footer text, so two location pages on one template always share many phrases. So run it twice: location vs location (`local-cityswap.json`), and location vs a non-location page such as `/about` (`local-template.json`), whose shared phrases are template text. The one-liner subtracts the second list from the first; judge only the remainder. If most of the remaining phrases would still be true with the city names swapped, the pages are doorway-like (doorway abuse, google-rules §4).
   - Check that the page shows the address, phone and hours exactly as on the profile, plus a map embed, directions, parking or transport, photos of the actual location, the staff or practitioners there, services offered there, and reviews or testimonials from that location.
3. **LocalBusiness schema** (see seo-schema):
   - The most specific subtype, `name`, `address` and `telephone` with country code.
   - `geo` to at least 5 decimals, `openingHoursSpecification`, `url` of the location page.
   - `parentOrganization` → `@id` of the Organization.
   - **No `aggregateRating` for your own business on your own site.** Self-serving reviews are ineligible.
4. **Business Profile checklist.** Profile edits are always gated at every autonomy level (references/autonomy.md). List each change (field, current value, new value) as an item in the end-of-run approval batch. Make only the changes the user approves in chat for that run, through the Business Profile API, then re-read the profile to confirm them and log them. Without API access, ask for it (Google must approve it first). Never automate business.google.com.
   - **Name:** the real-world name only. No taglines, cities, keywords or phone numbers.
   - **Categories:** as few and as specific as possible, describing what the business *is*. Check which primary category the competitors in the map pack use.
   - **Hours:** regular and special hours. Omit them for appointment-only businesses.
   - **Contact:** a local phone number, and a website link to the matching location page, not the homepage, for multi-location businesses. Add UTMs (`?utm_source=google&utm_medium=organic&utm_campaign=gbp`) so profile clicks show separately in analytics.
   - **Content:** attributes, services and products, and a description of what you do, who for and where, without keyword lists.
   - **Media and updates:** real photos and video of the premises, team and work, refreshed regularly. Updates/posts for offers and events.
   - **Practitioners:** public-facing practitioners may have their own profile (a solo practitioner at a brand uses "Brand: Name"). Support staff may not.
5. **Reviews strategy:**
   - Ask every customer the same way, at the right moment, with a direct review link.
   - **No gating** (asking only happy customers), no incentives, no employee or fake reviews.
   - Reply to every review, negative ones especially: factual, polite, no customer personal data.
   - Report clearly fake reviews through the profile tools.
   - Review requests are messages to real people, always gated at every autonomy level (references/autonomy.md). Prepare the request text, the review link and the channel, and list each send (its recipient list and message) as an item in the end-of-run approval batch. **Never send a review request, or any message to a customer, without the user's explicit approval of that item in chat for that run.** Send only the approved items, through the business's connected account, and log the count, channel and date, never the contact details. Any test sends use only the user's approved test numbers and invalid fake emails.
6. **Citations and NAP:**
   - List where the business already appears and prepare each correction against the ground truth (name, address format, phone, URL): the listing, the field, the current and the new value. These listings are external accounts, so each correction is an item in the end-of-run approval batch (references/autonomy.md). Make only the approved ones, through the listing's connected account (the Business Profile API for Google), and log them. A listing with no connected account goes in the requests, with the access it needs.
   - Core everywhere: Google Business Profile, Apple Business Connect, Bing Places, Facebook, and the main maps app in that country.
   - Country-specific directories: find them by running WebSearch for "<category> <city>". List those that actually rank or that the competitors in the map pack use, rather than assuming. For Georgia (.ge), verify which local directories and maps apps rank for the category before recommending any.
   - NAP consistency is an industry convention, not a stated Google rule (google-rules §7).
7. **Local rank and visibility checks:**
   - WebSearch can't emulate a searcher's location, so treat its results as indicative only.
   - For real local positions, use a paid geo-grid tracker within the configured budget (see Data). Without one, report the WebSearch results as indicative and add searches made at each location (incognito, location on) to the requests batched at the end.
8. **Local links and mentions:**
   - Local press, associations and chambers of commerce, sponsorships, partner businesses, event listings, local "best of" lists.
   - Hand outreach off to seo-links.
9. **Prioritise:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" seo-work/local-audit-*.json`. Profile items go first because they're the largest local lever.
10. **Write back to the store** (skip when the project has none):
    - Step 7's WebSearch results go in with `ingest serps`, as the two files `seo-serp-researcher` writes, with `local pack` among the features when the map pack shows. That also adds queries the store didn't hold.
    - Record each location page as the owner of its "<service> <city>" query:
      ```bash
      python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" set-status --keyword "<service> <city>" --locale en --status published --url https://site/locations/tbilisi
      ```

## Checks
**Local ranking factors** [Google doc]:
- **Relevance:** categories, services and content.
- **Distance:** from the searcher.
- **Prominence:** reviews (count and rating), links, mentions, general fame.
- You can't pay for local rank (google-rules §7).

**Profile guideline violations to flag, with suspension risk:**
- Keywords in the name.
- A virtual office or PO box.
- Several profiles for one location.
- A premium-rate or redirecting phone number.
- A website link to a social page.
- A service-area business showing its address.

**Location pages:**
- One indexable URL per real location, linked from a crawlable store locator: `<a href>` links, not only a JavaScript map.
- Self-canonical, in the sitemap.
- Unique substance on each page.

**Service-area pages:**
- Only for areas you genuinely serve, each with area-specific substance such as jobs done, local regulations, travel time and testimonials.
- Mass city-swap pages are doorway abuse. More than about 30 thin area pages is a red flag (heuristic).

**Schema:**
- LocalBusiness `name` and `address` required.
- Phone with country code, `geo` ≥5 decimals.
- Reviews only for *other* businesses.

**On-page:**
- City and service in the title and H1 where natural.
- The NAP block in HTML text, not an image.
- Click-to-call (`tel:`) links.

**Measurement:**
- Business Profile Performance: searches, calls, direction requests, website clicks.
- Search Console filtered to location-page URLs.
- GA4 traffic from the profile link, via the UTMs.

## Data: free vs paid
- **Free path:**
  - Business Profile Performance and Search Console.
  - Manual map-pack checks by the user at each location.
  - WebSearch for competitors and citation discovery.
  - Bing Places and Apple Business Connect dashboards.
  - The scripts above.
- **Geo-grid rank trackers** (Local Falcon, BrightLocal, or DataForSEO Google Maps/Local Finder SERP endpoints):
  - Justified for multi-location businesses or competitive map packs where rank changes street by street.
  - Run a small grid (e.g. 5×5) monthly per key term rather than daily, to control cost.
- **Citation management:**
  - BrightLocal: audits and builds.
  - Yext: pushes listings to many sites. Justified only for large multi-location brands. Listings may revert if you cancel [vendor terms; verify].
  - Semrush Listing Management is an alternative if you already have Semrush.
- **Ahrefs and Semrush keyword tools** add search volume for "service + city" terms, which helps when choosing which location or service pages to build.
- Prices and cost tactics: `${CLAUDE_PLUGIN_ROOT}/references/tools.md` (## Other paid tools, ## DataForSEO, ## Cost-optimisation playbook).

## Output
1. **Eligibility and risk summary.**
2. **Profile change list**, as current → new, each an approval-batch item, and which ones were applied through the API.
3. **NAP mismatch table**, by source with the exact strings.
4. **Location-page fixes**, with the content to add per page, plus city-swap results.
5. **LocalBusiness JSON-LD** per location.
6. **Review plan**: the request text, link and channel, and each send as an approval-batch item.
7. **Citation targets** with evidence that they rank.
8. **Measurement baseline** (profile and Search Console numbers as given by the user, tagged [measured]).
9. **Assumptions:** the ground-truth details, services × areas, competitors and market assumed, with the evidence for each; which store data was reused and how old it was. Then the requests batched at the end, each with a recommendation: missing access (Business Profile, Search Console, on-location searches) and the owner's calls (which NAP string is real). Then the approval batch: profile edits, listing corrections and review-request sends, one item each.

## Pitfalls & myths
- **Keyword-stuffing the profile name** may help briefly, but it is a guideline violation and a common cause of suspension.
- **Frequent changes to name, address or categories** can trigger re-verification.
- **"Near me" pages don't need to say "near me".** Proximity comes from the searcher's location.
- **Buying reviews, or offering discounts for them,** risks review removal and profile penalties, and violates consumer-protection law in many countries.
- **Hundreds of city pages with swapped names** are doorway abuse.
- **Never invent addresses, phone numbers, ratings or review counts** in pages, schema or reports.

## Log the work
Append to `SEO-WORKLOG.md` (format: `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`). Include:
- Locations covered.
- Profile changes and listing corrections applied on approval, with dates, and those still awaiting approval.
- Review requests sent on approval: count, channel and date, never contact details.
- NAP fixes per source.
- Pages and schema changed.
- The baseline metrics and where they came from.
- The next check date (about 4–6 weeks for profile and review effects).
