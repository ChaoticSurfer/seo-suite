#!/usr/bin/env python3
"""Turn findings from any seo-suite script into one ranked fix plan, computed by lookup — not by judgement.

Usage:
  triage.py crawl.json robots.json sitemap.json page.json [--pages 240]
Each finding id maps to (impact 1–5, effort 1–5, fix). Priority:
  impact 5 → P0; 4 → P1; 3 → P2; 2 → P3; 1 → park.
  One level more urgent when it affects ≥25% of crawled pages (impact ≥3); one level less when effort ≥4.
Unknown ids are listed separately so the table can be extended rather than guessed.
"""
from __future__ import annotations

import argparse
import json
import sys

# id: (impact, effort, fix). Impact = organic visibility at stake; effort = typical work to fix.
FINDING_TABLE: dict[str, tuple[int, int, str]] = {
    # access & indexability
    "bot-challenge": (5, 2, "Allow verified bots through the CDN/WAF (Cloudflare: Security → Bots → allow verified bots; skip challenges for answer-engine crawlers you want)."),
    "fetch-failed": (5, 2, "Fix DNS/TLS/server availability."),
    "http-error": (5, 2, "Restore the page (200) or redirect it to its replacement; remove internal links to it."),
    "robots-5xx": (5, 1, "Serve robots.txt with 200 (or 404). A 5xx/429 robots.txt halts crawling."),
    "robots-blocks-google": (5, 1, "Remove the Disallow that blocks Googlebot from the site."),
    "html-truncated": (5, 3, "Cut HTML under 2 MB: move inline data/SVG/JSON out, paginate long lists."),
    "noindex": (4, 1, "Remove noindex if the page should rank (and from the initial HTML, not via JS)."),
    "likely-client-rendered": (4, 4, "Server-render or pre-render primary content and links (SSR/SSG); most AI crawlers do not run JS."),
    "canonical-multiple": (4, 1, "Emit exactly one rel=canonical in <head>."),
    "canonical-to-bad-target": (4, 1, "Point canonicals at the final 200, indexable URL."),
    "canonical-http": (4, 1, "Use the https:// URL in rel=canonical."),
    "robots-blocks-assets": (4, 1, "Allow CSS/JS needed for rendering."),
    "not-https": (4, 3, "Serve over HTTPS and 301 http → https."),
    "viewport-missing": (4, 1, "Add <meta name=viewport content='width=device-width, initial-scale=1'>."),
    "broken-internal-links": (4, 2, "Fix or remove links to error URLs (template links first)."),
    "sitemap-unreachable": (3, 1, "Make the sitemap reachable with 200 and declare it in robots.txt."),
    "sitemap-invalid-xml": (3, 1, "Fix the sitemap XML (escape &, valid namespaces)."),
    "sitemap-noindex": (3, 1, "Drop noindex URLs from the sitemap (or remove the noindex)."),
    "sitemap-non-200": (3, 1, "List only final 200 URLs in sitemaps."),
    "sitemap-http-urls": (3, 1, "Use https URLs in the sitemap."),
    "sitemap-too-big": (3, 2, "Split into files ≤50 MB / 50k URLs under a sitemap index."),
    "sitemap-too-many": (3, 2, "Split into files ≤50k URLs under a sitemap index."),
    "sitemap-compression-error": (3, 1, "Re-generate the .gz sitemap (gzip -t must pass) or serve it uncompressed."),
    "sitemap-unsupported-format": (3, 1, "Use a format Google reads: <urlset>/<sitemapindex> with xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\", RSS 2.0, Atom 1.0, or a UTF-8 text file with one URL per line."),
    "sitemap-nested-index": (3, 1, "List only sitemap files in a sitemap index; point the top-level index straight at every child sitemap."),
    "hreflang-invalid": (3, 1, "Use ISO 639-1 language + optional ISO 3166-1 region (en-GB, not en-UK)."),
    "hreflang-no-return": (3, 2, "Every hreflang target must link back (generate the full set from one source)."),
    "hreflang-no-self": (2, 1, "Include the page itself in its hreflang set."),
    "hreflang-duplicate": (2, 1, "One URL per hreflang value."),
    "hreflang-no-x-default": (1, 1, "Add an x-default alternate (language picker or global page)."),
    "duplicate-content": (3, 3, "Consolidate duplicates: 301 or canonical to one URL; fix parameter/trailing-slash variants."),
    "near-duplicate-content": (2, 3, "Differentiate near-identical pages with unique substance, or consolidate them (301/canonical)."),
    "canonical-in-body": (2, 1, "Move rel=canonical into <head> (or send it as an HTTP Link header)."),
    "redirect-map-failure": (4, 2, "Fix every failing mapping: one-hop 301/308 to the mapped, 200, indexable, self-canonical URL."),
    "js-dependent-seo": (3, 3, "Put titles, robots, canonical, primary content, links and schema in the server HTML (SSR/SSG)."),
    "cwv-fail": (3, 3, "Fix the failing metric at template level (LCP: hero image/TTFB; INP: long JS tasks; CLS: reserved space)."),
    "schema-self-serving-review": (2, 1, "Remove aggregateRating/review from your own Organization/LocalBusiness markup."),
    "no-large-image-preview": (1, 1, "Add <meta name=robots content='max-image-preview:large'> if Discover traffic matters."),
    "orphan-pages": (3, 2, "Link orphaned pages from relevant hubs/navigation, or drop them from the sitemap."),
    "robots-blocks-answer-engine": (3, 1, "Allow OAI-SearchBot / Claude-SearchBot / PerplexityBot / Bingbot if you want AI citations (training bots can stay blocked)."),
    "snippet-blocked": (3, 1, "Remove nosnippet / max-snippet:0 unless you deliberately opt out of snippets and AI Overviews."),
    "soft-404": (3, 2, "Return a real 404/410 status for missing URLs."),
    "missing-url-server-error": (2, 2, "Return 404/410 for missing URLs; a 5xx/429 answer reads as a server problem and slows Google's crawling of the site."),
    "schema-parse-error": (3, 1, "Fix the JSON-LD syntax (validate with Rich Results Test)."),
    "schema-missing-required": (3, 1, "Add the required property — only with values visible on the page."),
    "title-missing": (3, 1, "Write a unique, descriptive <title> (topic + qualifier + brand)."),
    "links-to-redirects": (2, 2, "Update internal links to the final URL."),
    "redirect-chain": (2, 1, "Redirect straight to the final URL (one hop)."),
    "temporary-redirect": (2, 1, "Use 301/308 for permanent moves."),
    "duplicate-titles": (2, 2, "Make titles unique per page (fix the template variable)."),
    "duplicate-descriptions": (2, 2, "Write or template unique meta descriptions."),
    "deep-pages": (2, 3, "Bring important pages within 3 clicks (hub pages, breadcrumbs, related links)."),
    "no-internal-links": (3, 1, "Add crawlable <a href> links from this page."),
    "internal-nofollow": (2, 1, "Remove rel=nofollow from internal links."),
    "noindex-heavily-linked": (2, 2, "Either index the page or stop linking to it sitewide."),
    "h1-missing": (2, 1, "Add one visible <h1> describing the page."),
    "canonical-missing": (2, 1, "Add a self-referencing absolute rel=canonical."),
    "canonical-elsewhere": (2, 1, "Confirm the canonical target is intended."),
    "lcp-lazy": (2, 1, "Remove loading=lazy from the hero image; add fetchpriority=high."),
    "no-compression": (2, 1, "Enable gzip/brotli for HTML."),
    "slow-response": (2, 3, "Cut server response time (caching, CDN, DB queries); verify with CrUX TTFB."),
    "img-alt-missing": (2, 1, "Add descriptive alt (empty alt='' for decorative images)."),
    "mixed-content": (2, 1, "Load all resources over https."),
    "robots-too-big": (2, 2, "Shrink robots.txt under 500 KiB (use wildcards)."),
    "sitemap-non-canonical": (2, 1, "List canonical URLs only."),
    "sitemap-bad-lastmod": (2, 1, "Emit W3C Datetime lastmod."),
    "sitemap-future-lastmod": (2, 1, "Never emit future lastmod."),
    "sitemap-uniform-lastmod": (2, 2, "Emit each page's real last significant modification date."),
    "sitemap-cross-host": (2, 2, "Host sitemaps per host or verify cross-site submission."),
    "description-missing": (1, 1, "Write a unique meta description with concrete facts (price, date, location)."),
    "title-long": (1, 1, "Front-load the important words; trim boilerplate."),
    "title-short": (1, 1, "Add a qualifier (who/what/where) to the title."),
    "title-multiple": (2, 1, "Keep one <title>."),
    "weakly-linked": (1, 2, "Add contextual links from related pages."),
    "not-in-sitemap": (1, 1, "Add indexable pages to the sitemap."),
    "robots-no-sitemap": (1, 1, "Add a Sitemap: line to robots.txt."),
    "img-no-dimensions": (1, 1, "Set width/height (or aspect-ratio) on images."),
    "render-blocking-js": (1, 2, "defer/async scripts in <head>."),
    "thin-content": (1, 3, "Check intent: expand with genuinely useful detail, merge, or noindex."),
    "schema-missing-recommended": (1, 1, "Add recommended properties you can truthfully fill."),
    "schema-breadcrumb-short": (1, 1, "Give BreadcrumbList at least 2 items."),
    "schema-no-context": (2, 1, "Add \"@context\": \"https://schema.org\"."),
    "anchor-empty": (1, 1, "Give links text or an image alt."),
    "anchor-generic": (1, 1, "Use descriptive anchor text."),
    "og-missing": (1, 1, "Add og:title, og:description, og:image (1200×630)."),
    "html-heavy": (1, 2, "Trim HTML weight."),
    "no-hsts": (1, 1, "Send Strict-Transport-Security."),
    "lang-missing": (1, 1, "Set <html lang>."),
    "charset-missing": (1, 1, "Add <meta charset=utf-8>."),
    "img-legacy-formats": (1, 2, "Serve WebP/AVIF with srcset."),
    "robots-unsupported": (1, 1, "Remove noindex:/crawl-delay: lines Google ignores (keep crawl-delay only if you rely on Bing/Anthropic honouring it)."),
    "description-long": (1, 1, "Optional: front-load the key fact."),
    "description-short": (1, 1, "Optional: say more about what the page offers."),
    "robots-missing": (1, 1, "Optional: add robots.txt with a Sitemap: line."),
    "sitemap-empty": (2, 1, "Populate or remove the empty sitemap."),
    "sitemap-no-lastmod": (1, 1, "Add accurate lastmod."),
    "sitemap-duplicates": (1, 1, "De-duplicate sitemap URLs."),
    "sitemap-files-skipped": (1, 1, "Tool limit, not a site defect: run sitemap_check.py on the unchecked child sitemaps to complete total_urls and --urls-out."),
    "h1-multiple": (1, 1, "Optional: one dominant h1."),
    "heading-skip": (1, 1, "Optional: keep heading levels sequential."),
    "schema-limited-type": (1, 1, "No action needed for Google; don't expect a rich result."),
    "schema-none": (1, 2, "Add structured data for the page type (Organization, Article, Product, LocalBusiness, BreadcrumbList…)."),
    "robots-blocked-links": (1, 1, "Confirm those disallowed URLs are meant to be blocked."),
    # technical drift against each URL's baseline (claude_seo.py drift, claude-seo's drift_compare.py rules)
    "technical-drift-critical": (4, 1, "Check the change against the last deploy: restore a removed schema block, canonical, H1 or title, remove an added noindex, or fix the error status, unless the change was intended; then take a new baseline (--rebaseline)."),
    "technical-drift-warning": (2, 1, "Confirm the changed title, description, Open Graph tags or schema were intended; take a new baseline once they are."),
    "technical-drift-info": (1, 1, "No action unless unexpected: new schema, a changed H2 outline or content. Re-baseline after reviewing."),
    # language versions of a post (translation_check.py)
    "translation-body-language-mismatch": (4, 3, "Translate the main content, not just nav/header/footer, into the declared language. If it was left in the source language, Google treats it as a duplicate. Keep it noindex until a fluent reviewer has checked it. If the hreflang code is what's wrong, fix the code instead."),
    "translation-side-by-side": (4, 2, "One language per page: translate the remaining blocks or move them to their own language version."),
    "translation-untranslated-block": (3, 1, "Translate the listed paragraphs. Keep a foreign-language quote only when it's deliberate, and mark it with lang=."),
    "translation-canonical-cross-language": (4, 1, "Point each language version's rel=canonical at itself or a page in the same language, never at another language. Otherwise the version drops out of the index."),
    "translation-canonical-not-self": (2, 1, "Confirm the canonical target is intended. Language versions should normally canonicalise to themselves."),
    "translation-number-missing": (4, 2, "Check each number against the source. Restore any dropped fact, or confirm it was a deliberate unit or currency conversion or written out in words."),
    "translation-number-added": (4, 2, "Check each added number against the source. Remove invented figures, or correct the source if the translation is the accurate one."),
    "translation-metadata-not-translated": (3, 1, "Translate and review the title, meta description, H1 and image alt text in the page's own language and script, not English or Latin transliteration."),
    "translation-length-outlier": (3, 2, "Compare the version with the source paragraph by paragraph. Restore missing or cut-off text, or remove additions."),
    "translation-structure-mismatch": (2, 2, "Bring sections, images, tables and lists in line with the source, or confirm the difference is deliberate localisation."),
    "translation-link-leaves-language": (2, 1, "Link body text to the same-language version of each internal page where one exists."),
    "translation-schema-language-mismatch": (2, 1, "Set structured data inLanguage, and translate headline and description, to match the page's own language."),
    "translation-og-locale-mismatch": (1, 1, "Set og:locale to the page's locale in language_TERRITORY form, e.g. ka_GE or ru_RU."),
    "translation-html-lang-mismatch": (2, 1, "Set <html lang> to the version's language code. Google ignores it, but screen readers and browser translation use it."),
    "translation-hreflang-no-return": (3, 2, "Emit the same full hreflang set, including the page itself, on every version, generated from one source. Google ignores pairs without return links."),
    "translation-hreflang-no-self": (2, 1, "Include the page itself in its hreflang set."),
    "translation-hreflang-set-mismatch": (2, 2, "Generate one identical hreflang set (same codes, URLs and a single x-default) for every language version."),
    "translation-hreflang-no-x-default": (1, 1, "Optional: add the same x-default (a language picker or the main version) to every version's set."),
    "translation-hreflang-wrong-code": (3, 1, "Use ISO 639-1 language codes: ka not ge, uk not ua, el not gr, ja not jp, cs not cz, da not dk."),
    "translation-version-error": (3, 1, "List only final, 200-status URLs in hreflang. Fix or remove alternates that are broken or redirect."),
    "translation-version-noindex": (3, 1, "Index the version once a fluent reviewer has checked it. While it stays noindex, drop it from every version's hreflang set, and never block it with robots.txt instead."),
    "translation-no-alternates": (2, 2, "Add hreflang between the language versions (HTML link, HTTP header or sitemap) so Google can show each searcher their language."),
    "translation-cluster-capped": (1, 1, "Tool limit, not a site defect: run translation_check.py --urls on the versions that weren't checked."),
    "translation-input-redirect": (1, 1, "No action for hreflang: the URL given to the tool redirects, so its final URL was checked. Link to the final URL."),
    # AI-written text (ai_text_check.py); every one is a heuristic, not a verdict
    "ai-text-hidden-instructions": (5, 1, "Remove hidden text and HTML comments that address AI systems or carry prompts. Bing treats prompt injection as abuse, and Google's spam policies cover manipulating AI answers."),
    "ai-text-model-leftover": (4, 1, "Delete the chatbot boilerplate, then re-read and fact-check the whole post: a leftover means nobody edited it."),
    "ai-text-placeholder": (4, 1, "Fill in or delete every placeholder ([insert ...], TODO, XX%, {{...}}) before publishing."),
    "ai-text-quoted-placeholder": (1, 1, "Check each placeholder in a prompt template the post shows: keep it if it is a deliberate prompt template, fill it in or delete it if it is a leftover."),
    "ai-text-unsupported-stat": (3, 2, "Fact-check each statistic or 'studies show' claim. Link the primary source, or cut the claim."),
    "ai-text-repeated-sentence": (2, 1, "Remove repeated sentences."),
    "ai-text-stock-phrases": (2, 2, "Rewrite stock model phrasing (delve, tapestry, testament to...) in plain, specific words."),
    "ai-text-chatbot-phrase": (2, 1, "Check each chat-reply phrase (I hope this helps, feel free to adjust...): keep it if a person wrote it, delete it if it was pasted from a chatbot."),
    "ai-text-generic-intro": (2, 1, "Open with the answer or the specific point instead of a stock opening."),
    "ai-text-generic-outro": (1, 1, "End on a specific takeaway, or cut the summary paragraph."),
    "ai-text-filler-answer": (2, 1, "Answer each question heading in its first sentence; that is what snippets and AI answers quote."),
    "ai-text-hedging": (1, 2, "State what is known and cite it. Cut hedges that add nothing."),
    "ai-text-repeated-phrases": (1, 1, "Vary or cut five-word phrases that repeat."),
    "ai-text-uniform-sentences": (1, 2, "Optional: vary sentence length while editing."),
    "ai-text-em-dash-density": (1, 1, "Optional: replace some em dashes with commas, colons or full stops."),
    "ai-text-label-lists": (1, 1, "Optional: turn some 'Label: explanation' list items into prose or plain bullets."),
    "ai-text-short-text": (1, 1, "Tool limit, no action: the text is under 150 words, so only the leftover, chat-phrase, placeholder and hidden-text checks ran."),
    # the blog system: index, pagination, post template, archives, sitemap, feed (blog_system_check.py)
    "blog-index-error": (5, 2, "Restore the blog index: it must return 200, since it is the main path to every post."),
    "blog-index-noindex": (4, 1, "Remove noindex from the blog index; it is a hub that should rank and pass links to the posts."),
    "blog-index-canonical-not-self": (4, 1, "Point the blog index's canonical at itself."),
    "blog-index-no-post-links": (4, 3, "Render the post list on the server with <a href> links (a server component, SSG or ISR), not after JavaScript runs."),
    "blog-pagination-missing": (4, 2, "Link older posts from numbered pages (?page=2 or /page/2) with plain <a href>, so posts beyond page 1 get a crawlable link."),
    "blog-pagination-error": (4, 1, "Make every linked index page return 200 without redirecting."),
    "blog-pagination-canonical-to-first": (4, 1, "Give page 2 and later their own self-canonical URL. A canonical to page 1 tells Google the older posts' only links are duplicates."),
    "blog-pagination-canonical-not-self": (3, 1, "Point each index page's canonical at its own URL."),
    "blog-pagination-title-duplicate": (1, 1, "Put the page number in page 2+'s title (and H1), e.g. 'Blog, page 2 | Brand'."),
    "blog-pagination-out-of-range-200": (2, 1, "Return 404 for page numbers past the last page (notFound() before any streaming starts), not an empty 200."),
    "blog-pagination-capped": (1, 1, "Tool limit, not a site defect: re-run blog_system_check.py with a higher --max-pages to check the rest."),
    "blog-post-error": (4, 2, "Make every post the index links return 200 directly; update links to redirected posts to the final URL."),
    "blog-post-noindex": (4, 1, "Remove noindex from published posts, or stop listing them on the index and in the sitemap."),
    "blog-post-canonical-not-self": (3, 1, "Point each post's canonical at itself (or at the same-language original it truly duplicates)."),
    "blog-post-schema-missing": (2, 1, "Add BlogPosting (or Article) JSON-LD to the post template: headline, image, datePublished, dateModified, author with url."),
    "blog-post-breadcrumb-missing": (1, 1, "Add BreadcrumbList JSON-LD to the post template, built from the same labels and links as the visible breadcrumb."),
    "blog-post-date-missing": (2, 1, "Emit datePublished in ISO 8601 with a time zone, from the post's real publish moment."),
    "blog-post-modified-before-published": (2, 1, "Compute dateModified as the later of the last edit and the publish moment, in one helper the sitemap, OG tags and JSON-LD all read."),
    "blog-post-date-future": (2, 1, "Publish the post only once its date has passed, or correct datePublished; cap dates at the build or request time."),
    "blog-post-date-no-timezone": (1, 1, "Add the time zone offset to datePublished and dateModified (2026-10-01T09:00:00+04:00); Google assumes one otherwise."),
    "blog-post-date-mismatch": (2, 1, "Derive article:published_time, the visible date and datePublished from the same value."),
    "blog-post-author-missing": (2, 1, "Name the author in the article markup: Person for a person, Organization for an organisation, with a url."),
    "blog-post-byline-missing": (3, 1, "Print the author named in the markup as a visible byline on the post, linked to their author page."),
    "blog-post-author-generic": (2, 2, "Credit the real writer as a Person with an author page, or type the group as Organization. Never invent a person."),
    "blog-post-author-no-url": (1, 1, "Give each author a url to a page about them (an author page with Person or ProfilePage markup)."),
    "blog-author-page-error": (2, 1, "Make every author url return 200, or point it at a page that does."),
    "blog-author-page-no-schema": (1, 1, "Add ProfilePage markup with a Person mainEntity (name, jobTitle, image, sameAs) to the author page."),
    "blog-post-lcp-not-prioritised": (2, 1, "Prioritise the hero image: fetchPriority=\"high\" (next/image: preload on Next 16, priority on 15 and earlier)."),
    "blog-post-image-no-srcset": (2, 2, "Serve a srcset with sizes (next/image does when optimisation is on; images.unoptimized strips it), or a <picture>."),
    "blog-post-url-style": (1, 3, "Use lower-case, hyphenated slugs without parameters for new posts; move old ones only with 301s."),
    "blog-post-few-post-links": (2, 2, "Link each post to at least two related posts on the same topic, with descriptive anchors."),
    "blog-related-posts-identical": (2, 2, "Pick related posts by shared topic or tags per post, not the same newest or popular few everywhere; add next/previous links."),
    "blog-twin-links-missing": (2, 1, "Link each language version of a post to the others with plain <a href lang hreflang> in the server HTML; hreflang alone is not a link."),
    "blog-money-page-no-post-links": (2, 1, "Link each money page to the posts that support it (guides, comparisons), from the body, not only the footer."),
    "blog-archive-error": (2, 1, "Make every linked archive return 200, or remove the link."),
    "blog-archive-empty-200": (3, 1, "Return 404 for an archive with no posts (or noindex it while it is empty), and stop linking to it."),
    "blog-archive-thin-indexable": (1, 1, "Noindex archives with fewer than 3 posts (keep follow), or merge the tag into a broader one."),
    "blog-sitemap-post-no-lastmod": (1, 1, "Emit each post's real last change as lastmod."),
    "blog-sitemap-lastmod-mismatch": (2, 1, "Take each sitemap lastmod from the same helper as dateModified, per language version, never the build time."),
    "blog-feed-missing": (2, 1, "Publish an RSS 2.0 or Atom feed of the newest posts (a route handler) and advertise it with <link rel=alternate type=application/rss+xml>."),
    "blog-feed-invalid": (2, 1, "Fix the feed XML so it parses as RSS 2.0 or Atom 1.0 (escape &, declare the namespace)."),
    "blog-feed-relative-links": (2, 1, "Use absolute URLs in feed item links."),
    "blog-feed-missing-newest": (1, 1, "Rebuild the feed on publish (or revalidate it hourly) so it carries the newest post."),
    "blog-feed-not-advertised": (1, 1, "Advertise the feed in the index <head> with <link rel=alternate type=application/rss+xml> (Next.js: alternates.types)."),
    "blog-indexnow-key-invalid": (2, 1, "Serve the IndexNow key file with 200, text/plain and the key (8-128 of a-z, A-Z, 0-9, -), at the keyLocation the pings send."),
}
PRIORITY_BY_IMPACT = {5: 0, 4: 1, 3: 2, 2: 3, 1: 4}
WIDE_SHARE = 0.25


def priority(impact: int, effort: int, share: float) -> str:
    level = PRIORITY_BY_IMPACT[impact]
    if share >= WIDE_SHARE and impact >= 3:
        level -= 1
    if effort >= 4:
        level += 1
    level = max(0, min(level, 4))
    return "park" if level == 4 else f"P{level}"


def collect(report: dict, source: str) -> list[dict]:
    rows = []
    page = report.get("url") or report.get("start") or report.get("site") or report.get("robots_url") or ""
    for key in ("findings", "site_findings"):
        for f in report.get(key, []):
            rows.append({"id": f["id"], "severity": f.get("severity"), "url": page, "pages": None, "message": f["message"],
                         "evidence": f.get("evidence", ""), "source": source})
    for f in report.get("page_issue_summary", []):
        rows.append({"id": f["id"], "severity": f.get("severity"), "url": page, "pages": f["pages"], "message": f"{f['pages']} pages",
                     "evidence": ", ".join(f["examples"]), "source": source})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reports", nargs="+", help="JSON outputs of the other scripts")
    ap.add_argument("--pages", type=int, help="pages crawled (defaults to pages_crawled in a crawl report)")
    args = ap.parse_args()

    rows, total_pages = [], args.pages
    for path in args.reports:
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
        total_pages = total_pages or report.get("pages_crawled")
        rows += collect(report, path)

    plan, unknown, seen = [], [], set()
    for row in rows:
        if row["id"] not in FINDING_TABLE:
            unknown.append(row)
            continue
        dedupe_key = (row["source"], row["id"], row["severity"], row["message"], row["evidence"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        impact, effort, fix = FINDING_TABLE[row["id"]]
        share = (row["pages"] or 0) / total_pages if total_pages else 0.0
        plan.append({**row, "priority": priority(impact, effort, share), "impact": impact, "effort": effort, "fix": fix,
                     "share_of_pages": round(share, 2) if row["pages"] else None})
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "park": 4}
    plan.sort(key=lambda r: (order[r["priority"]], -r["impact"], r["effort"], -(r["pages"] or 0)))
    print(json.dumps({"total_pages": total_pages, "plan": plan, "unmapped_findings": unknown,
                      "counts": {p: sum(1 for r in plan if r["priority"] == p) for p in order}}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
