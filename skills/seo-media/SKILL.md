---
name: seo-media
description: Images, video and news surfaces. Alt text, image sitemaps, WebP/AVIF, hero images and LCP, video watch pages, VideoObject and key moments, YouTube vs self-hosted, Google Discover, Google News and Top stories, podcasts. Not for overall page speed (seo-technical) or schema beyond media types (seo-schema).
---

# Images, video, Discover and News

Make media indexable, eligible for its own surfaces (Images, Video, Discover, Top stories), and light enough not to slow the page.

## When to use / not
- **Use for:**
  - Image audits and fixes.
  - Image and video sitemaps.
  - Video indexing problems.
  - YouTube vs self-hosted decisions.
  - Discover and News eligibility.
  - Publisher sites, podcasts with episode pages.
- **Not for:**
  - Core Web Vitals beyond the LCP image (seo-technical).
  - Generic article schema (seo-schema).

## Inputs: decide, don't ask
Decide each input from evidence, record it under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| **Templates that carry media:** article, product, gallery, video watch page, category with video | URL patterns in the sitemap or a crawl; `summary.images` and `facts.iframes` in the page audits | The URLs given, plus the home page |
| **Where media is hosted.** An image or CDN host's own robots.txt governs those files | The hosts in `facts.images` | The page's own host |
| **Video:** platform (YouTube, Vimeo, Wistia, self-hosted), whether each video has its own watch page, transcripts and chapters | `facts.iframes` and `<video>` tags in the page HTML; the page layout (step 3); the page text | No video found: skip the video steps |
| **Publishers:** whether the site appears in Google News, publishing volume, bylines, dates | `news_entries` in the sitemap check; Article schema; dated, bylined articles | Not a publisher unless that evidence exists |
| **Search Console:** Performance by search type (Image, Video, News, Discover), the Video indexing report and the Discover report. The Discover report only appears once the site reaches a minimum number of impressions | The Search Console API or exports in the workspace, when available | Run without them. Ask — batched at the end, naming what each adds |

## Workflow
0. **Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`), when `seo-research/` exists:
   ```bash
   mkdir -p seo-work
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" status > seo-work/store-status.json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_store.py" export inventory --format csv > seo-work/store-inventory.csv
   ```
   - `seo-research/site.json` → `templates` starts the media-template input. Check it against the pages.
   - Per template, audit the live URLs (`status` 200) with the most `gsc_clicks` in the inventory.
   - The checks below still run on the live pages. Note what you reused and its age for *Assumptions* and the work log.
1. **Inventory, all in parallel:**
   ```bash
   mkdir -p seo-work; i=0
   for u in https://site/article https://site/product https://site/videos/how-to; do
     i=$((i+1)); python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_audit.py" "$u" --facts > "seo-work/media-$i.json" &
   done
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sitemap_check.py" https://site --sample 20 > seo-work/media-sitemap.json &
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/psi.py" https://site/article > seo-work/media-psi.json &
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/robots_check.py" https://cdn.site --path /images/ > seo-work/media-cdn-robots.json &
   wait
   ```
   What to read in each output:
   - **Page audits:** `img-alt-missing`, `img-no-dimensions`, `lcp-lazy`, `img-legacy-formats`, `og-missing`, `snippet-blocked`.
   - **Sitemap check:** `files[].image_entries`, `video_entries`, `news_entries`.
   - **PSI:** `lcp_element` and `top_opportunities`.
   - **CDN robots:** whether Googlebot is allowed on the CDN host. Read `matrix['Googlebot-Image']`: it uses a `User-agent: Googlebot-Image` group if one exists, otherwise the Googlebot group (or `*` if there is no Googlebot group).
2. **Images:** fix in this order. First indexability: `<img src>`, not CSS backgrounds, and not blocked. Then the LCP image. Then alt text and filenames. Then formats and sizes. Then sitemaps.
3. **Video:**
   - List every page with a video and label it a **watch page** (the video is the page's main purpose) or **embedded supporting video**. Only watch pages get video results.
   - Add VideoObject and a video sitemap for watch pages.
   - Read the reasons in the Video indexing report.
4. **Discover:** check eligibility and image requirements across article templates. Review the Discover report for which topics and formats get impressions.
5. **News (publishers):**
   - Check the article template: dates, bylines, author pages, Article schema.
   - Check that section URLs are stable and that the news sitemap exists.
   - Check the transparency pages: about, contact, editorial policy.
6. **Prioritise:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/triage.py" seo-work/media-*.json`.
7. **Write back to the research store**, when it exists: add the media templates you found (article, product, gallery, video watch page) to `seo-research/site.json` → `templates`. Media findings stay in `seo-work/`; the store has no dataset for them.

## Checks
**Images** (google-rules §3) [Google doc]:
- **Indexable formats:** BMP, GIF, JPEG, PNG, WebP, SVG, AVIF, in `<img src>` (also inside `<picture>`). **CSS background images aren't indexed.**
- **Responsive images:** `srcset`/`<picture>`, always with a `src` fallback.
- **Alt text:**
  - Descriptive and specific, with no keyword lists. Roughly ≤125 characters is a convention, not a rule.
  - Decorative images get `alt=""`.
  - Alt also serves as the anchor text when an image is a link.
  - Inline SVG uses `<title>`.
- **Filenames and placement:**
  - Short, descriptive filenames, translated on localised pages.
  - Place images near relevant text.
  - Keep image URLs stable. Changing them can temporarily lose image traffic.
- **Preferred image:**
  - Signal it with `primaryImageOfPage`, `mainEntity` image or `og:image`.
  - Avoid logos and text-heavy images as the main image.
  - `og:image` at 1200×630 for social (convention).
- **Large previews:** `max-image-preview:large` is needed for large previews in Search and Discover.
- **LCP image:**
  - Not `loading=lazy`; use `fetchpriority="high"` and set `width`/`height`.
  - Serve it right-sized (WebP/AVIF). Preload it if it's discovered late (e.g. a CSS or JS hero).
  - LCP ≤2.5 s at p75 (google-rules §2).
- **Image sitemap:**
  - Namespace `http://www.google.com/schemas/sitemap-image/1.1`, `<image:image><image:loc>`.
  - ≤1,000 images per `<url>`. CDN URLs on other domains are fine.
  - Deprecated tags: `caption`, `geo_location`, `title`, `license`.
- **Image metadata (licensable badge):**
  - IPTC metadata embedded in the file (creator, credit line, copyright notice), or ImageObject `license` + `acquireLicensePage`.
  - AI-generated images need IPTC `DigitalSourceType = TrainedAlgorithmicMedia`. Merchant Center requires this for product images (google-rules §4).
- `noimageindex` keeps a page's images out of Image search; use it deliberately.

**Video** (google-rules §8, §1):
- **Watch-page rule:** the page's main purpose must be that one video. A video embedded in an article doesn't get video results.
- **Visibility:** the video must be visible without interaction and not loaded via fragments. Avoid "Video outside viewport" reports.
- **Formats:** MP4, MOV, WebM, MKV, M3U8 and others. No data URLs.
- **Thumbnail:** ≥60×30 px, at least 80% of pixels with alpha above 250, on a stable crawlable URL, in an image format.
- **VideoObject:**
  - Required: `name`, `thumbnailUrl`, `uploadDate`.
  - Recommended: `contentUrl` and/or `embedUrl`, `description`, `duration` (ISO 8601), `expires`, `interactionStatistic`, `regionsAllowed`.
  - Live video: `publication` BroadcastEvent for the LIVE badge.
- **Video sitemap:**
  - Required: `video:thumbnail_loc`, `video:title`, `video:description` (≤2048 chars), and `video:content_loc` or `video:player_loc`.
  - Optional: `duration` 1–28800 s, `publication_date`, `expiration_date`, `family_friendly`, `restriction`, `live`, `uploader` (≤255 chars), `tag` (≤32).
  - Deprecated: `category`, `gallery_loc`, `price`, `tvshow`, and the `player_loc` attributes `autoplay` and `allow_embed`.
- **Key moments:**
  - `hasPart` Clip (`name`, `startOffset`, `url`), in all languages.
  - Or SeekToAction, whose target URL contains `{seek_to_second_number}` (limited languages).
  - YouTube chapters/timestamps work for YouTube-hosted video.
  - `nosnippet` opts out.
- **Indexing API:** officially only for JobPosting and livestream (BroadcastEvent) pages. Don't use it for ordinary videos.

**YouTube vs self-hosted** [heuristic]:

| Goal | Prefer |
|---|---|
| Reach and discovery on YouTube, low hosting cost | YouTube. The watch page on youtube.com usually wins the video result. Embed it on your page for engagement |
| Video results pointing to *your* domain, product or lead capture | A self-hosted or private-platform player (Wistia, Vimeo, Mux) on dedicated watch pages, with VideoObject and a video sitemap |
| Both | YouTube for discovery, plus a dedicated watch page on your site with a transcript, chapters and its own schema |

**Discover** (google-rules §8):
- No markup required. The page must be indexed and follow Discover's content policies.
- **Images:** ≥1200 px wide, more than 300K pixels, 16:9, with `max-image-preview:large`. No logo as the preview image.
- No clickbait or sensationalist titles.
- Gen-AI features in Discover can be excluded with Search Console's Search generative AI setting.
- The Discover report keeps 16 months.

**Google News** (google-rules §8, §1):
- No application process. Content is surfaced automatically if it follows the News content policies, which include transparency: dates, bylines, author and contact information [policy details not re-fetched; check the current policy page].
- **Googlebot-News:** works best with stable section URLs and can't follow JS-embedded links.
- **News sitemap:**
  - Only articles from the **last 2 days**, ≤1,000 `<news:news>` per file.
  - Required: `news:publication` (`news:name` matching the name in Google News, and `news:language` as ISO 639 or `zh-cn`/`zh-tw`), `news:publication_date` (W3C format, first-publish date), `news:title`.
- **Articles:** Article schema with `datePublished`/`dateModified`. A visible date and byline that match the markup. Don't fake updates.

**Podcasts** [verify current state]:
- Google Podcasts shut down in 2024, and podcast listening moved to YouTube Music.
- For search, give each episode its own page with a summary, transcript, chapters and guest bios, linked from a show page.
- Submit the RSS feed to the platforms you target.

## Data: free vs paid
- **Free path:**
  - The scripts above.
  - Search Console Performance with a search-type filter (the API supports the `image`, `video`, `news`, `discover` and `googleNews` types), and the Video indexing report.
  - PageSpeed Insights / CrUX for the LCP image.
  - YouTube Studio for YouTube analytics.
- **Screaming Frog:** site-wide image inventory (file sizes, missing alt, dimensions, images above a size threshold) and checks of the video and image sitemaps. Justified on sites with thousands of images, because `page_audit.py` doesn't measure image byte size and covers one page at a time.
- **YouTube keyword tools** (Ahrefs Keywords Explorer has a YouTube mode, and vidIQ/TubeBuddy):
  - Justified only for a channel strategy at scale.
  - Autocomplete via `keyword_ideas.py --sources youtube` is the free first step.
- **Semrush and Ahrefs** add little for images. Their Discover and News visibility estimates are weak, so use Search Console.
- Prices and cost tactics: `${CLAUDE_PLUGIN_ROOT}/references/tools-paid.md` (## Screaming Frog, ## Ahrefs, ## Cost-optimisation playbook).

## Output
1. **Media inventory by template** [measured].
2. **Image fix list:** indexability first, then the LCP image, alt text, formats and the sitemap.
3. **Video classification:** watch page vs embedded, with schema and sitemap entries proposed per watch page.
4. **Discover and News eligibility checklist** with pass/fail per item.
5. **The `triage.py` plan.**
6. The Search Console reports to watch.
7. **Assumptions:** the templates, hosts, video platforms and publisher status decided from evidence, and the evidence for each, plus the research-store data reused and its age.

## Pitfalls & myths
- **Product or hero images set as CSS backgrounds** never appear in Image search.
- **Lazy-loading the LCP image** is the most common LCP regression.
- **Expecting video rich results for a video embedded mid-article:** only dedicated watch pages qualify.
- **A video sitemap pointing at a `player_loc` that's blocked by robots.txt or needs a login** leaves the video unindexed.
- **Thumbnails on URLs that change with every deploy** cause indexing churn. Keep them stable.
- **Changing news article dates without real updates** looks like faked freshness.
- **Keyword-stuffed alt text** is a spam pattern (keyword stuffing, google-rules §4).

## Log the work
Append to `SEO-WORKLOG.md` (format: `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`). Include:
- Templates and files changed (image components, sitemaps, schema, robots.txt on the CDN).
- Watch pages created or marked up.
- Before and after LCP for the tested URL [measured].
- The Search Console reports to recheck (Video indexing, Image and Discover performance) and the recheck date (about 2–4 weeks).
