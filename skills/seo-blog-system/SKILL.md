---
name: seo-blog-system
description: Sets up or upgrades a blog's SEO plumbing (URLs, paginated index, category, tag and author pages, post template and schema, sitemap with real lastmod, RSS, IndexNow, hreflang, related links, noindex for thin archives). Next.js first. Use for "set up our blog". Not for writing (seo-blog-builder) or reviewing posts (seo-blog-review).
---

# Blog system: the plumbing around the posts

Make the blog itself rank-ready, so every post `seo-blog-builder` ships is found, crawled, understood and linked.
This skill owns the templates, routes and feeds. It never writes or rewrites a post's copy.

Two modes, decided from the repo, never asked:
- **Upgrade:** the site has a blog. Measure it against the Rules, then change only what is missing or wrong.
- **Setup:** the site has no blog. Scaffold one in the project's own stack, once the content model is settled.

## When to use / not
- **Use:**
  - "set up a blog", "add a blog to our Next.js site";
  - "fix our blog's SEO", "our older posts aren't indexed", "page 2 canonicalises to page 1";
  - adding an RSS feed, per-locale sitemaps, IndexNow, author pages or language-version links to a blog;
  - before `seo-blog-builder`'s first batch on a site whose blog fails the Rules.
- **Not:**
  - writing posts, briefs or a content calendar → `seo-blog-builder`;
  - reviewing posts or translations → `seo-blog-review`;
  - one page's title and meta → `seo-onpage`;
  - hreflang and URL structure for a whole site beyond the blog → `seo-international`;
  - a whole-site audit → `seo-audit`; schema for other page types → `seo-schema`.

## Inputs: decide, don't ask
Decide each input from evidence, record the choice under *Assumptions*, and carry on
(`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Stack and version | `package.json` (`next`, `astro`), the `app/` or `pages/` folder, `astro.config.*`, `seo-research/site.json` → `stack` | Plain static HTML. No repo: report only (level 1), with the diffs written against the live HTML |
| Mode | A blog route (`app/**/blog/`, `src/pages/blog/`), post files (`content/`, `src/content/blog/`, `_posts/`), a posts table in migrations, or blog URLs in the sitemap | Any one of these: upgrade. None: setup |
| Blog index, post prefix and locales | The blog route and its links; `<html lang>`, hreflang and locale folders | `/blog`, posts at `/blog/<slug>`, the locales the site already has |
| Production URL | `metadataBase`, `site` in `astro.config.*`, the canonical on the live home page | The live site's origin |
| Money pages | `seo-research/site.json` → `money_pages`; else pages with forms, pricing, booking or Product/Service schema | The 3 most linked pages in the main navigation |
| Content model (setup mode) | See below | **Ask once, batched at the end, with a recommendation** |
| IndexNow key | The repo's config (a key file route, an env var name, a `/<key>.txt` in `public/`) | No key: generate one in setup, read it from configuration, and say where it lives. Never paste it into chat or the work log |
| Preview URL for the PR | The CI's deploy comment (Vercel, Netlify), `gh pr view --json comments` | A local production build (step 5) |
| Autonomy level | `autonomy_level` (`seo-automation`) | Level 1 |

### The content model (setup mode)
Where posts live and how they are edited is the business's choice. Decide it from evidence only when the repo makes
it obvious; otherwise build nothing that depends on it and ask once, at the end of the run.
- **Obvious from the repo:** other content already lives as MDX or Markdown in the repo → MDX in
  `content/blog/<locale>/<slug>.mdx`. Other content already lives in database rows with JSON translation files →
  posts the same way. A headless CMS connector the site already uses → posts there.
- **Not obvious** (none of these, or two that conflict): read `seo-blog-builder`'s `content-model.md` if a run
  wrote one. Then scaffold only the parts that don't depend on storage (step 4: the URL helpers, metadata, schema,
  sitemap and feed builders, all reading one `Post` type), and add one question to the end-of-run batch.
  For example: "Where should posts live? Recommendation: MDX files in the repo, because the site is built from the
  repo with no database and posts then ship as PRs. Alternatives: rows in the Supabase database the tours use, with
  JSON translations, if non-developers will edit posts. Answer `mdx` or `database`."
- Every model carries the same fields: title, meta description, slug per locale, `publishedAt` and `updatedAt` as
  instants with a zone, a per-translation `updatedAt`, authors (each with an author page), image (URL, width,
  height, alt), tags or category, body, a per-version robots field, and the review fields `seo-blog-builder` needs.

## Workflow
`S="${CLAUDE_PLUGIN_ROOT}/scripts"`, `W="seo-work/blog-system/$(date +%F)"`, `$BLOG` the live blog index (e.g.
`https://example.com/blog`), `$PROD` its production origin. Run independent checks in parallel.

0. **Read the research store** when `seo-research/` exists (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`):
   `python3 "$S/research_store.py" status > "$W/store-status.json"`. Take `stack`, `templates` and `money_pages` from
   `seo-research/site.json`, and check them against the repo.
1. **Detect the stack and the mode** (Inputs). Read the blog's route files, its data layer, the sitemap, robots and
   metadata code, and at least one other page template, before planning any change.
2. **Measure the live blog** (upgrade mode; skip in setup):
   ```bash
   mkdir -p "$W"
   python3 "$S/blog_system_check.py" "$BLOG" --money-page "$PROD/pricing" --indexnow-key-location "$PROD/indexnow-key.txt" > "$W/blog-system.json"
   python3 "$S/sitemap_check.py" "$PROD" --sample 30 --urls-out "$W/sitemap-urls.txt" > "$W/sitemap.json"
   python3 "$S/robots_check.py" "$PROD" --path / --path /blog > "$W/robots.json"
   python3 "$S/crawl.py" "$BLOG" --max-pages 500 --path-prefix /blog/ --sitemap-urls "$W/sitemap-urls.txt" --csv "$W/pages.csv" > "$W/crawl.json"
   python3 "$S/page_audit.py" "$BLOG" > "$W/page-index.json"
   python3 "$S/page_audit.py" "$PROD/blog/<newest-post>" > "$W/page-post.json"
   python3 "$S/translation_check.py" "$PROD/blog/<newest-post>" > "$W/translation.json"
   python3 "$S/triage.py" "$W"/*.json > "$W/triage.json"
   ```
   - `blog_system_check.py`'s `rules` array is the gap list: every `fail` is a change, every `pass` is left alone.
     Read each finding's evidence in the page source before trusting it, as the scripts see raw HTML only.
   - On a multilingual blog, run `crawl.py` once over all language sections (`--path-prefix /` with a higher
     `--max-pages`), so `hreflang-no-return` sees both ends, and run `translation_check.py` on one post per
     template.
   - Run the router's audit profile when the blog is part of a wider audit request:
     `python3 "$S/audit_profile.py" --request-file seo-work/request.txt --sitemap "$W/sitemap.json" > "$W/profile.json"`.
3. **Plan the change list.** One row per failing rule: the rule, the evidence, the file, the exact diff, and the
   check that will prove it. In setup mode, every rule is a row. Order by `triage.py` priority. Keep each change
   in its own commit, and keep the PR under about 300 changed lines; split it by rule group (index and pagination,
   post template, sitemap and feed, IndexNow) when it grows past that.
4. **Implement**, matching the repo's style and helpers:
   - **Next.js App Router:** follow `${CLAUDE_PLUGIN_ROOT}/skills/seo-blog-system/nextjs-recipe.md`. Every API in it
     was checked against nextjs.org/docs; re-check any API the recipe doesn't list before using it.
   - **Other stacks:** see Other stacks below.
   - Build URLs, the hreflang set, the dates and the post list in one module, which the page, the sitemap, the feed
     and IndexNow all read.
   - Untranslated language routes: canonical to the original, out of hreflang and the sitemap, or 404.
5. **Verify against the PR's preview, or a local production build** (never `next dev`):
   ```bash
   npm run build && npm run start    # serves http://localhost:3000
   python3 "$S/blog_system_check.py" http://localhost:3000/blog --production-url "$PROD" > "$W/after-blog-system.json"
   curl -s http://localhost:3000/blog -o "$W/index.html" && python3 "$S/page_audit.py" --file "$W/index.html" --base-url "$PROD/blog" --fail-on high > "$W/after-page-index.json"
   curl -s "http://localhost:3000/blog/<slug>" -o "$W/post.html" && python3 "$S/page_audit.py" --file "$W/post.html" --base-url "$PROD/blog/<slug>" --fail-on high > "$W/after-page-post.json"
   curl -s http://localhost:3000/robots.txt -o "$W/robots.txt" && python3 "$S/robots_check.py" --file "$W/robots.txt" --path / --path /blog > "$W/after-robots.json"
   ```
   - **A preview deployment:** run `blog_system_check.py "$PREVIEW/blog" --production-url "$PROD" --ignore-x-robots-tag`.
     Previews send `X-Robots-Tag: noindex`, which isn't a defect of the blog. Use the `seo-technical` CI mode for
     a protected preview's bypass header.
   - `sitemap_check.py`, `crawl.py` and `translation_check.py` follow absolute production URLs, so run them against
     the live site after the merge, not against the build. Then re-run step 2 and compare.
   - Run `seo-blog-review`'s scripted checks (its step 4) on one post per language, so the template change didn't
     break titles, `inLanguage` or `og:locale`.
   - Done means `blog_system_check.py` shows no `fail` for the rules you changed, and no new findings anywhere.
6. **Deliver per autonomy level** (`references/autonomy.md`):
   - **Level 1:** the report, with each planned change as an exact diff and the command that will verify it.
   - **Level 2:** a branch `seo/blog-system-<date>`, one commit per rule group, pushed, and a PR whose description
     holds the rules table (before → after) and the step 5 output. Stop at the open PR.
   - **Level 3:** once CI and the step 5 checks pass on the preview, merge. After the deploy, re-run step 2 on
     production, then submit the changed and new URLs (index pages, feed, sitemap files and every post whose
     template output changed) through IndexNow, and record the response codes.
   - Above the level: say which level would finish the job, e.g. "level 3 merges the open PR".
7. **Record the stack** in `seo-research/site.json` → `stack` (e.g. "Next.js 16 App Router, Vercel") when it is new
   or wrong, and log the work.

## Rules
`blog_system_check.py` checks the rows marked ✓ itself. The rest come from the script named.

| Rule | Checked by | Source |
|---|---|---|
| The index returns 200, is indexable and canonicalises to itself | ✓ `blog-index-indexable` | google-rules §1 |
| The index links its posts with `<a href>` in the server HTML | ✓ `blog-index-links-posts`; `render_diff.py` | google-rules §1 |
| Older posts sit on numbered pages (`?page=2`, `/page/2`) linked with `<a href>`, each 200 | ✓ `blog-pagination-crawlable` | google-rules §8 |
| Page 2+ canonicalises to itself, never to page 1 | ✓ `blog-pagination-self-canonical` | google-rules §8 |
| Page 2+ has its own title | ✓ `blog-pagination-unique-titles` | google-rules §3 |
| A page number past the end returns 404 | ✓ `blog-pagination-out-of-range-404` | google-rules §1 |
| Each post: 200 without a redirect, indexable, self-canonical | ✓ `blog-post-indexable` | google-rules §1 |
| BlogPosting/Article JSON-LD that passes `schema_rules.py` (headline, image, dates, author with url) | ✓ `blog-post-article-schema` | google-rules §5 |
| BreadcrumbList with 2+ items | ✓ `blog-post-breadcrumb-schema` | google-rules §5 |
| `datePublished` set, with a zone, not in the future, equal to `article:published_time`; `dateModified` never earlier | ✓ `blog-post-dates` | google-rules §4–5; Google Article doc |
| A real author: Person or Organization as appropriate, with a url, printed as a byline | ✓ `blog-post-byline` | google-rules §4; Google Article doc and structured-data policies |
| Author pages return 200 with Person or ProfilePage markup | ✓ `blog-author-pages` | google-rules §5 |
| The hero image is not lazy, is prioritised, has its size and a `srcset` | ✓ `blog-post-lcp-image`; `psi.py` for the field LCP | google-rules §2 |
| Post URLs: lower case, hyphens, no parameters | ✓ `blog-post-url-style` | google-rules §3 |
| Each post links 2+ related posts, chosen per post, not the same few everywhere | ✓ `blog-post-links-posts` | google-rules §3 |
| Money pages link the posts that support them | ✓ `blog-money-pages-link-posts` (with `--money-page`) | google-rules §3 |
| Language versions link each other with `<a href hreflang lang>` in the server HTML | ✓ `blog-language-twin-links` | google-rules §1, §6 |
| hreflang: the full set, itself and x-default included, on every version, with return links; each version canonicalises to itself | `translation_check.py`, `crawl.py` (`hreflang-*`, `translation-hreflang-*`, `translation-canonical-*`) | google-rules §6 |
| Category and tag archives return 200 and are never empty | ✓ `blog-archive-status` | google-rules §1 |
| An indexable archive lists 3+ posts; thinner ones are `noindex, follow` or merged | ✓ `blog-archive-thin-noindex` | seo-suite convention |
| The sitemap lists every indexable post, and no noindex, redirected or non-canonical URL | ✓ `blog-sitemap-lists-posts`; `sitemap_check.py` | google-rules §1 |
| Each post's lastmod is its own last change, per language; never uniform or in the future | ✓ `blog-sitemap-real-lastmod`; `sitemap_check.py` | google-rules §1 |
| An RSS or Atom feed, advertised on the index, absolute links, carrying the newest post | ✓ `blog-feed` | google-rules §1 |
| IndexNow: a valid key file, and the URLs of every published or changed post sent on publish | ✓ `blog-indexnow-key` (with `--indexnow-key-location`); the publish code by reading it | google-rules §1 |
| Titles and meta descriptions: unique, descriptive, in the page's language | `page_audit.py`, `crawl.py` (`duplicate-titles`) | google-rules §3 |
| robots.txt allows the blog, its CSS and JS, and lists the sitemap | `robots_check.py` | google-rules §1 |

## Other stacks
- **Astro:** set `site` in `astro.config.*`, and build the canonical from `Astro.url` and `site`. The official
  sitemap integration writes the sitemap, and Astro's "Add an RSS feed" recipe the feed; check that each entry's
  lastmod comes from the post's own date, not the build. Return `paginate()` from `getStaticPaths` in a
  `[page].astro` route for numbered pages (Astro routing guide), and give each page its own canonical. Read the
  installed integration's docs before using an option this file doesn't name.
- **Plain static HTML:** one template per page type. Generate the sitemap and feed in the build script from the
  same post list, with each file's own dates. Ping IndexNow from the deploy step, after the files are live.

## Data: free vs paid
- **Free path, which covers this whole skill:** the bundled scripts, the repo, a local production build or the
  PR's preview, Search Console (Pages report, URL Inspection for a post on each template), Bing Webmaster Tools
  (IndexNow submissions and the URL inspection), PSI/CrUX for the post template's field LCP.
- **Screaming Frog** adds a JavaScript-rendered crawl of a large blog (thousands of posts) and custom extraction
  of a template element across every post, e.g. every post missing the twin-links block (tools-paid.md
  `## Screaming Frog`). Only worth it when the blog is larger than `crawl.py`'s practical size.
- **Semrush and Ahrefs** add nothing to the plumbing. Their keyword and backlink data belongs to
  `seo-blog-builder` and `seo-links`.

## Output
- **Mode and stack**, with the evidence for each.
- **Rules table, before and after:** each rule with `pass`, `fail` or `not_checked` from `blog_system_check.py`, the
  other scripts' rows, and the change that fixed each failure.
- **Per change:** the file, the diff (level 1) or the commit and PR link (levels 2–3), and the verification output.
- **The P0–P3 table** from `triage.py`.
- **Not verified:** rules left `not_checked` and why (no money pages known, no IndexNow key location, a preview
  behind protection, production checks pending the deploy).
- **Assumptions:** the mode, index, post prefix, locales, production URL, money pages and content model decided from
  evidence, and the research-store data reused with its age.
- **Questions for the end of the run:** the content model while it is undecided (setup mode), credentials or repo
  access the run lacked, and the level that would finish the job.

## Pitfalls & myths
Lessons from Geotour (a Next.js App Router site in seven languages), which this skill uses as its reference:
- **Done right, keep:** one helper for publish and modified dates, which the sitemap, OG tags and JSON-LD all read,
  with modified never before published; a `lastmod` per language that moves when only that translation changes;
  "Read this article in" links between language versions in the server HTML; IndexNow sending every language URL
  of a changed post, from production only, with a key file route.
- **Pagination canonicalised to page 1.** `/blog?page=N` pointed at `/blog`, so the only pages that linked to older
  posts told Google they were duplicates. Fixed by making page 2+ self-canonical with a numbered title.
- **`images.unoptimized: true` strips `srcset`.** It was set to get round an optimiser quota, and the hero image,
  `sizes` and all, now ships one full-size file to every screen (measured on geotour.ge, 2026-10-25). Use a
  `loader` with an image CDN instead.
- **A team typed as a Person.** "Geotour Team" is printed as the byline and marked up as `Person`. Google's Article
  doc wants `Organization` for organisations, and a real person needs an author page.
- **A soft 404 for empty topics.** A `?tag=` with no posts rendered an empty list with a 200. Fixed with `notFound()`.
  Call it before any `<Suspense>` boundary streams, or the 200 stays.
- **The same related posts on every article.** Topic first, then next/previous by date, so every post gets a link.
- **No feed.** The blog shipped without RSS. A feed is cheap, and Google reads RSS and Atom as sitemaps.
- **Myths:** `rel=prev/next` is not used by Google; `priority` and `changefreq` in the sitemap are ignored;
  IndexNow does not reach Google; hreflang is not a link, so language versions still need `<a href>` between them.

## Log the work
Append to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`: the mode and stack, the blog and
production URLs checked, `blog_system_check.py` counts before and after, the files changed with commits and the PR,
what was verified on the preview or local build and what waits for production, the content-model decision or the
open question, IndexNow submissions and their response codes, paid units (normally 0), and the re-check date: the
day after the deploy for the production run of step 2, then 14 days for indexing in Search Console.
