---
name: seo-ecommerce
description: Use for online stores and catalogues — "ecommerce SEO", "product page SEO", "category page optimisation", "faceted navigation / filters creating thousands of URLs", "sort and filter parameters indexed", "out of stock or discontinued products", "product variants / colour URLs", "pagination", "Merchant Center free listings", "Shopping tab", "Shopify SEO", "WooCommerce SEO", "duplicate manufacturer descriptions". Covers URL inventory and crawl waste, index rules for facets, pagination, variants, product lifecycle, parity between page, markup and feed, internal linking and platform specifics. Not for: schema syntax and templates (seo-schema), product images and video (seo-media), replatforming or domain moves (seo-migration), keyword demand research (seo-keywords).
---

# E-commerce SEO

Get the right category and product URLs crawled, indexed and shown in rich, Shopping and AI results, and stop facets, sorts and dead SKUs from wasting crawl.

## When to use / not
- **Use for:**
  - Catalogue sites of any size.
  - Category and product template work.
  - Filter and parameter control.
  - Stock lifecycle.
  - Merchant listings.
  - Shopify, WooCommerce, Magento or headless storefront specifics.
- **Not for:**
  - A one-off schema fix (seo-schema).
  - A move to a new platform (seo-migration, which then hands back here for the new templates).

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Platform and theme or headless stack | Page source and headers (e.g. `cdn.shopify.com`, `/collections/`, `wp-content`, `?add-to-cart=`), the generator meta tag, the repo | Unknown: skip the platform specifics and check rendering with `render_diff.py` |
| Catalogue size (SKUs, categories); languages and currencies | Product and category sitemap counts; `<html lang>`, hreflang, `priceCurrency` and visible prices | The sitemap counts |
| URL patterns: product, category, filter (parameters or paths), sort, internal search, pagination, cart/account, tracking parameters | Crawl CSV and sitemap; links on category templates | The patterns the crawl finds |
| How stock status, discontinued products and variants are handled today | Sampled out-of-stock and variant pages (`availability` in JSON-LD, `?variant=` URLs); sitemap URLs that 404 or redirect | The behaviour the samples show |
| Top-revenue categories and SKUs (optimise those first) | GA4 e-commerce data if connected; else main-nav and mega-menu categories, "top sellers" blocks, GSC clicks, crawl inlinks | Main-nav categories and their top-seller SKUs |
| **Merchant Center (read-only):** diagnostics, the feed source, a feed sample of about 20 top SKUs | A connector or an export | **Ask — batched at the end.** Run the parity check on page vs markup and leave the feed column `[needs data]` |
| **Search Console:** Pages and Merchant listings / Product snippets reports, plus a query+page performance export | A connector or exports in `seo-work/` | **Ask — batched at the end.** Carry on with the crawl |

## Workflow
1. **Inventory, all three in parallel:**
   ```bash
   mkdir -p seo-work
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sitemap_check.py" https://shop --sample 50 --urls-out seo-work/shop-sitemap-urls.txt > seo-work/shop-sitemap.json &
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/robots_check.py" https://shop --path / --path "/collections/shoes?sort_by=price" --path "/search?q=x" --path "/shoes?color=red&size=9" > seo-work/shop-robots.json &
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crawl.py" https://shop --max-pages 1500 --csv seo-work/shop-pages.csv > seo-work/shop-crawl.json &
   wait
   ```
   Then re-run the crawl with `--sitemap-urls seo-work/shop-sitemap-urls.txt` to find orphan and not-in-sitemap pages.
2. **Measure crawl waste** from `shop-pages.csv`:
   - Group URLs by path pattern and query parameter. For each group, count URLs, the share that are indexable, the share that are duplicate content, and the canonical target.
   - With server logs, `log_analyze.py` shows Googlebot's share of hits on parameter URLs (`parameter_url_share`).
3. **Template audit,** one URL each for product, category, filtered category, search, page 2 and out-of-stock product, in parallel:
   - Run `page_audit.py URL --facts`.
   - Run `content_score.py URL --keyword "<category term>"`.
   - On headless or JS themes, run `render_diff.py` to confirm that price, links, product grid and JSON-LD are in the raw HTML.
4. **Parity check for about 20 top SKUs.** For each, compare the visible price, currency, availability, GTIN and image against the JSON-LD `offers` and the feed row. Any mismatch causes listing disapprovals. Write the result as a table.
5. **Set index rules.** Make a pattern table (see Checks) and implement it in robots.txt, meta robots, canonicals and internal links, per autonomy level (references/autonomy.md).
6. **Fix the lifecycle** for out-of-stock, discontinued and seasonal products (see Checks), implemented the same way.
7. **Internal linking:**
   - Category hierarchy with breadcrumbs (BreadcrumbList).
   - Links from the home page and mega-menu to money categories.
   - Related and complementary products. Links from "top sellers" blocks.
   - Product pages within 3 clicks (the crawl's `deep-pages` finding; heuristic).
8. **Content:**
   - **Categories:** a short, helpful intro (who it's for, how to choose, key filters) above or near the grid, plus buying guides linked from the category. Not a wall of keyword text below the footer.
   - **Products:** rewrite manufacturer copy for the top SKUs first; add specs tables, sizing, real photos, real reviews and Q&A.
9. **Prioritise:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" seo-work/shop-crawl.json seo-work/shop-robots.json seo-work/shop-sitemap.json`.

## Checks
**Faceted navigation** (google-rules §8) [Google doc]:
- **Facets with no search demand:** block crawling with a robots.txt disallow on their parameters, or keep them in URL fragments (`#`).
- **`rel=canonical` and `nofollow`** are weak, slow alternatives. nofollow only works if *every* link to the URL carries it.
- **Facets with demand** (e.g. "red running shoes", proven with search data):
  - Give them clean, stable URLs with a consistent filter order and `&` separators.
  - Self-canonical, unique title and H1, linked internally, in the sitemap.
  - Return **404** for empty results, duplicate or nonsensical filters, and out-of-range pages.
- **Sort, view, session and tracking parameters** never get indexed. Disallow them, or canonicalise them to the clean URL.

**Choose one mechanism per URL:** disallow *or* noindex, never both. A disallowed URL's noindex is never seen. For URLs already indexed: noindex first, wait until they drop out, then disallow.

**Internal search results:** keep them out of the index. Disallow `/search` (prefer this for crawl budget) or noindex it, and don't link to search URLs from templates (convention, supported by Google's crawl-budget guidance).

**Pagination** (google-rules §8):
- Each page gets its own `?page=n` URL, linked with `<a href>`, and is self-canonical. **Never canonicalise to page 1.**
- `rel=next/prev` isn't used by Google.
- Infinite scroll or "load more" also needs crawlable paginated links.
- Titles may repeat across the series.

**Variants** (google-rules §5):
- Model them as `ProductGroup` + `hasVariant`.
- Give a variant its own indexable URL only when it has its own search demand (e.g. a colour people search for). Otherwise use one canonical page with preselect URLs (e.g. `?variant=`) that canonicalise to it.

**Lifecycle:**
- **Temporarily out of stock:** keep the 200 page, set `availability` OutOfStock or BackOrder, show a restock date and alternatives, keep it in the sitemap.
- **Permanently discontinued, with a successor:** 301 to the successor or the closest category.
- **Gone with no equivalent:** 404 or 410. Google treats them the same.
- **Never mass-redirect to the homepage.** Google reads that as a soft 404.
- **Seasonal pages:** keep one stable URL year-round and update its content.

**Merchant listings:**
- Product markup with `name`, `image`, and Offer `price` > 0 plus `priceCurrency`, with shipping and return policy (details in seo-schema).
- No past `priceValidUntil`. Numeric GTINs.
- Merchant Center **feed data overrides markup**, so keep feed, page and markup identical.
- Free listings need a Merchant Center account; the owner sets that up.
- **AI content rules:** AI-generated images need IPTC `DigitalSourceType = TrainedAlgorithmicMedia`, and AI-generated titles and descriptions must be labelled (google-rules §4).

**Reviews:**
- Product ratings come only from real customer reviews of that product.
- No incentivised reviews without disclosure.
- Pros/cons markup only on editorial review pages.

**Thin pages** (heuristic): categories or tags with 0–1 products, and auto-generated tag pages. Consolidate them, noindex them, or remove them from navigation.

**Platform specifics:**
- **Shopify:**
  - Products are reachable at `/products/x` and `/collections/c/products/x`. The canonical is `/products/x`, so make theme links use it too.
  - `?variant=` URLs canonicalise to the product.
  - Tag-filtered collection URLs (`/collections/c/tag`) are usually thin. robots.txt is editable via `robots.txt.liquid`.
  - Search & Discovery filter parameters: check how the theme links them and whether they're crawlable.
  - Apps often inject a second Product JSON-LD, so de-duplicate.
- **WooCommerce:**
  - Disallow `?add-to-cart=` and `?orderby=` crawling.
  - Noindex cart, checkout and my-account pages.
  - Review `product_tag` archives.
  - Watch for duplicate Product schema from WooCommerce plus Yoast or Rank Math.
- **Headless / Next.js commerce:**
  - SSR or ISR the category grids and product pages, with server-side JSON-LD.
  - Filter links must be real `<a href>` links only where indexing is intended.
  - Return real 404 status codes.

## Data: free vs paid
- **Free path:**
  - The scripts above (`crawl.py` suits up to a few thousand URLs from one machine, without JS rendering).
  - Search Console: Merchant listings, Product snippets, Pages (indexed vs not), Shopping tab performance.
  - Merchant Center diagnostics.
  - Server logs (`log_analyze.py`).
  - `keyword_ideas.py` for facet ideas, without volumes.
- **Screaming Frog:** crawls 10k–1M URLs with JS rendering, custom extraction (price and availability selectors) and structured-data validation. Justified for large catalogues, or when `crawl.py` reaches its limit (`hit_page_limit: true`).
- **Semrush or Ahrefs:**
  - Search volumes and keyword difficulty to decide which facets deserve their own indexable URLs.
  - Competitors' category keyword gaps.
  - Justified when indexing decisions affect hundreds of facet combinations. One month's subscription during planning is often enough.
- **DataForSEO Google Shopping / Merchant APIs:** competitor price and listing data, priced per use. Justified for price-sensitive verticals.
- **Botify or Lumar:** enterprise crawl and log analytics, justified for catalogues of 1M+ URLs.
- Prices and cost tactics: `${CLAUDE_PLUGIN_ROOT}/references/tools.md` (## Screaming Frog, ## Semrush, ## Ahrefs, ## DataForSEO, ## Cost-optimisation playbook).

## Output
1. **URL inventory by pattern,** with counts, indexable share and crawl-waste share [measured].
2. **Index-rule table,** one row per pattern: index / noindex / disallow / canonicalise, with the reason and how it's implemented.
3. **Lifecycle policy.**
4. **Parity table** (page vs markup vs feed).
5. **Template fixes** per page type.
6. **Internal-link plan.**
7. **Content priorities** by revenue.
8. **The `triage.py` plan.**
9. **Assumptions:** the platform, catalogue size, patterns and top-revenue pages assumed, with the evidence for each. Then the requests batched at the end, each with a recommendation: missing access (Merchant Center, Search Console, GA4, logs).

## Pitfalls & myths
- **Canonicalising every filter to the category while linking to filters sitewide:** Google may ignore those canonicals, and you still pay the crawl cost.
- **Disallow plus noindex on the same URL:** the noindex is never seen, so the URL can stay indexed with no snippet.
- **Turning out-of-stock products into 404s** loses rankings that come back when stock returns.
- **JS-only filters and "load more"** leave products undiscoverable.
- **Long SEO text blocks at the bottom of categories:** Google has no preferred word count (google-rules §4). Write for choosing.
- **Duplicate manufacturer descriptions** aren't penalised, but they give Google no reason to prefer your page.

## Log the work
Append to `SEO-WORKLOG.md` (format: `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`). Include:
- Patterns changed and the mechanism used.
- Files and settings changed (robots.txt, theme templates, app settings).
- Parity results.
- Evidence files (`seo-work/shop-*`).
- The Search Console reports to recheck (Pages, Merchant listings) and the recheck date (about 2–6 weeks; large catalogues take longer).
