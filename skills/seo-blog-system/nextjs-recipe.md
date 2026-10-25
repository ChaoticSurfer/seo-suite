# Next.js App Router recipe for the blog system

`seo-blog-system` reads this file in its step 4 when the repo runs Next.js with the App Router. Each section names
the rules it satisfies (the skill's Rules table) and the files it touches. Adapt names and paths to the repo; keep
what it already does right.

**Verified against nextjs.org/docs on 2026-10-25.** Each API below is on these pages, with each page's own
last-updated date:

| API | Docs page (upd) |
|---|---|
| `generateMetadata`, `metadataBase`, `title.template`, `alternates.canonical/languages/types`, `openGraph` article fields, `robots` | functions/generate-metadata (2026-08-19); `openGraph.modifiedTime` from the `OpenGraphArticle` type in the Next.js source |
| `app/sitemap.ts`, `MetadataRoute.Sitemap`, `alternates.languages` per entry, `generateSitemaps` | file-conventions/metadata/sitemap (2026-08-18) |
| `next/link`: renders an `<a href>`, passing `<a>` attributes such as `rel` through | components/link (2026-08-25) |
| `next/image`: `sizes`, `preload`, `priority`, `fetchPriority`, `loading`, `fill`, `unoptimized`, `loader`, `loaderFile` | components/image (2026-09-28) |
| Route handlers (`app/<path>/route.ts`, `GET`, non-UI responses such as `app/rss.xml/route.ts`), `export const revalidate` | file-conventions/route (2026-04-30) |
| JSON-LD in a page or layout as `<script type="application/ld+json">`, `<` escaped as `<` | guides/json-ld (2026-03-02) |
| `notFound()` from `next/navigation` | functions/not-found (2026-09-23) |
| `generateStaticParams` | functions/generate-static-params (2026-10-01) |
| `after()` from `next/server` | functions/after (2026-09-16) |
| `revalidatePath()` from `next/cache` | functions/revalidatePath (2026-06-25) |
| Route segment config | file-conventions/route-segment-config (2026-10-01) |

**Version differences that change the code.** Read `next` in `package.json` first.
- Next 15+: `params` and `searchParams` are Promises (`await params`). Route handler `context.params` too.
- Next 16: the `id` that `generateSitemaps` passes to `sitemap()` is a `Promise<string>`. `next/image`'s `priority`
  is deprecated in favour of `preload`.
- Next 16 with `cacheComponents` on: `dynamic`, `dynamicParams`, `revalidate` and `fetchCache` segment exports are
  removed. Cache data with `'use cache'` instead (shown in the generateMetadata docs).
- Next 15+: `GET` route handlers are dynamic by default, so a feed or key file declares its own caching.

## 1. One source for URLs, dates and language versions

Every rule about canonicals, hreflang, lastmod and twin links breaks when two files compute the same thing two ways.
Put these in one module (e.g. `lib/blog/urls.ts`) and make the page, the sitemap, the feed and IndexNow read it.
This is project code, not a Next.js API:

```ts
// lib/blog/urls.ts
export const LOCALES = ['en', 'ka', 'ru'] as const
export const DEFAULT_LOCALE = 'en'

/** /blog/<slug> for the default language, /<lang>/blog/<slug> for the others */
export function postPath(lang: string, slug: string): string {
  return lang === DEFAULT_LOCALE ? `/blog/${slug}` : `/${lang}/blog/${slug}`
}

/** The languages this post is really written in: never a route that only serves the English copy */
export function postLanguages(post: Post): string[] {
  return [DEFAULT_LOCALE, ...Object.keys(post.translations)]
}

/** alternates.languages for one post: every real version, itself included, plus x-default */
export function hreflangMap(post: Post): Record<string, string> {
  const map: Record<string, string> = { 'x-default': postPath(DEFAULT_LOCALE, post.slug) }
  for (const lang of postLanguages(post)) map[lang] = postPath(lang, post.slug)
  return map
}

/**
 * The one rule behind datePublished, dateModified, article:*_time and sitemap lastmod.
 * Modified is never before published: a post written ahead was last edited before it went live.
 */
export function postDates(post: Post, lang: string): { published: Date; modified: Date } {
  const published = new Date(post.publishedAt)
  const edits = [post.updatedAt, post.translations[lang]?.updatedAt].filter(Boolean).map((d) => new Date(d!))
  const modified = new Date(Math.max(published.getTime(), ...edits.map((d) => d.getTime())))
  return { published, modified }
}
```

Store dates as instants with a time zone (`2026-10-01T09:00:00+04:00`), and give each translation its own
`updatedAt`. That is what makes per-locale lastmod real (Geotour: `blogPostDates`, `blogPostModifiedIn`).

## 2. Root layout: base URL and title template

```tsx
// app/layout.tsx (or app/[lang]/layout.tsx)
import type { Metadata } from 'next'

export const metadata: Metadata = {
  metadataBase: new URL('https://example.com'),
  title: { template: '%s | Example Tours', default: 'Example Tours' },
}
```

Relative URLs in `alternates` and `openGraph.images` then resolve against `metadataBase`. Without it, a relative
path is a build error.

## 3. Index and pagination (rules: index, pagination)

```tsx
// app/blog/page.tsx
import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'

const PER_PAGE = 12
type Props = { searchParams: Promise<{ page?: string }> }

function pageNumber(raw?: string): number {
  const n = Number(raw ?? '1')
  return Number.isInteger(n) && n >= 1 ? n : NaN
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const page = pageNumber((await searchParams).page)
  const path = page > 1 ? `/blog?page=${page}` : '/blog'
  return {
    title: page > 1 ? `Travel blog, page ${page}` : 'Travel blog',
    alternates: {
      canonical: path,                                    // page 2+ is its own canonical, never page 1
      types: { 'application/rss+xml': '/blog/feed.xml' }, // advertises the feed
    },
  }
}

export default async function BlogIndex({ searchParams }: Props) {
  const page = pageNumber((await searchParams).page)
  const { posts, pages } = await listPosts({ page, perPage: PER_PAGE })
  if (!Number.isFinite(page) || page > pages) notFound() // a real 404, before any <Suspense> streams
  return (
    <main>
      <h1>{page > 1 ? `Travel blog, page ${page}` : 'Travel blog'}</h1>
      {posts.map((post) => (
        <article key={post.slug}><h2><Link href={postPath('en', post.slug)}>{post.title}</Link></h2></article>
      ))}
      <nav aria-label="Pagination">
        {page > 1 && <Link href={page === 2 ? '/blog' : `/blog?page=${page - 1}`} rel="prev">Newer posts</Link>}
        {page < pages && <Link href={`/blog?page=${page + 1}`} rel="next">Older posts</Link>}
      </nav>
    </main>
  )
}
```

- The list is a server component, so its `<a href>` links are in the HTML. No "load more" button without a link.
- `notFound()` must run before streaming starts. Called inside a `<Suspense>` boundary, the response keeps its 200
  and only gets a `noindex` (notFound docs). That is a soft 404 for crawlers.
- Next.js also has `metadata.pagination` (`rel=prev/next` link tags). Google doesn't use them (google-rules §8),
  so they are optional.

## 4. Post template (rules: post indexable, schema, dates, byline, LCP image, links, twin links)

```tsx
// app/[lang]/blog/[slug]/page.tsx
import type { Metadata } from 'next'
import Image from 'next/image'
import { notFound } from 'next/navigation'

type Props = { params: Promise<{ lang: string; slug: string }> }

export async function generateStaticParams() {
  const posts = await allPublishedPosts()
  return posts.flatMap((post) => postLanguages(post).map((lang) => ({ lang, slug: post.slug })))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { lang, slug } = await params
  const post = await getPost(lang, slug)
  if (!post) notFound()
  const { published, modified } = postDates(post, lang)
  return {
    title: post.title,
    description: post.description,
    alternates: { canonical: postPath(lang, slug), languages: hreflangMap(post) },
    openGraph: {
      type: 'article',
      publishedTime: published.toISOString(),
      modifiedTime: modified.toISOString(),
      authors: post.authors.map((a) => a.name),
      images: [{ url: post.image.url, width: post.image.width, height: post.image.height, alt: post.image.alt }],
    },
  }
}

export default async function PostPage({ params }: Props) {
  const { lang, slug } = await params
  const post = await getPost(lang, slug)
  if (!post) notFound()
  const { published, modified } = postDates(post, lang)
  const url = new URL(postPath(lang, slug), 'https://example.com').href
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BlogPosting',
        headline: post.title,
        description: post.description,
        inLanguage: lang,
        mainEntityOfPage: url,
        image: [post.image.url],
        datePublished: published.toISOString(),
        dateModified: modified.toISOString(),
        author: post.authors.map((a) => ({ '@type': 'Person', name: a.name, url: a.url })),
        publisher: { '@type': 'Organization', name: 'Example Tours', url: 'https://example.com' },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Blog', item: 'https://example.com/blog' },
          { '@type': 'ListItem', position: 2, name: post.title },
        ],
      },
    ],
  }
  return (
    <article>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }} />
      <h1>{post.title}</h1>
      <p>
        By {post.authors.map((a) => <a key={a.url} href={a.url} rel="author">{a.name}</a>)} ·{' '}
        <time dateTime={published.toISOString()}>{formatDate(published, lang)}</time>
      </p>
      <Image src={post.image.url} width={post.image.width} height={post.image.height} alt={post.image.alt}
             sizes="(max-width: 768px) 100vw, 768px" fetchPriority="high" />
      <PostBody post={post} />
      <RelatedPosts posts={await relatedByTopic(post, lang)} />
      <nav aria-label="Other languages">
        {postLanguages(post).filter((l) => l !== lang).map((l) => (
          <a key={l} href={postPath(l, slug)} hrefLang={l} lang={l}>{languageName(l)}</a>
        ))}
      </nav>
    </article>
  )
}
```

- **Escape JSON-LD.** `JSON.stringify` alone lets a `</script>` in a title close the tag (JSON-LD guide). Geotour's
  `serializeJsonLd` also escapes `>`, `&`, U+2028 and U+2029.
- **Author:** `Person` for a person, `Organization` for an organisation (Google Article doc). The name in the markup
  is printed as the byline, and `url` is an author page with `ProfilePage` markup. Never "Team" typed as a Person.
- **Hero image:** `fetchPriority="high"`, or `loading="eager"`. Use `preload` (Next 16) or `priority` (15 and
  earlier) only when you need the `<link rel=preload>` in `<head>`; the docs say not to combine `preload` with
  `fetchPriority` or `loading`. Give `width` and `height` (the real file's size, from the CMS or
  `next/image`'s static import), or `fill` with a sized parent. Always pass `sizes`: with it, Next.js writes the
  full `srcset`.
- **Never set `images.unoptimized: true` to get round an optimiser quota.** Images are then "served as-is", so
  `sizes` produces no `srcset` and every phone downloads the desktop file (measured on geotour.ge, 2026-10-25).
  Use a `loader` / `loaderFile` that points at an image CDN, or pre-sized files with a hand-written `srcset`.
- **Twin links** are plain `<a href hrefLang lang>` in the server HTML. A language switcher whose items exist only
  while its menu is open gives crawlers nothing. On Geotour, 0 of 173 crawled posts linked a twin until the footer
  links were added.
- **Related posts by topic:** shared tags or cluster, then fill with next/previous by date. The same newest four
  on every post links only those four. Add contextual body links to money pages and from money pages to the posts
  that support them.
- **Untranslated slugs:** if `/ka/blog/<slug>` renders the English copy, canonicalise it to the English URL, keep it
  out of hreflang and the sitemap, or return 404. Never put it in the cluster (translation_check.py's
  `translation-canonical-cross-language`).

## 5. Archives (rules: archive status, thin noindex)

```tsx
// app/blog/category/[category]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params
  const posts = await postsIn(category)
  if (posts.length === 0) notFound()
  return {
    title: `${categoryName(category)} guides`,
    alternates: { canonical: `/blog/category/${category}` },
    robots: posts.length < 3 ? { index: false, follow: true } : undefined,
  }
}
```

The page component calls `notFound()` on the same condition. A `?tag=` filter on the index can stay a filter that
canonicalises to `/blog`, as long as it is not linked as if it were its own page.

## 6. Sitemap with real per-locale lastmod (rules: sitemap)

Small sites, one file:

```ts
// app/sitemap.ts
import type { MetadataRoute } from 'next'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const posts = await allPublishedPosts()
  return posts.flatMap((post) =>
    postLanguages(post).map((lang) => ({
      url: new URL(postPath(lang, post.slug), 'https://example.com').href,
      lastModified: postDates(post, lang).modified,           // this language's own last change
      alternates: { languages: absolute(hreflangMap(post)) }, // the same cluster as the page head
    }))
  )
}
```

- No `lastModified: new Date()` on static pages: it claims constant change. Leave it out when it isn't known.
- Published posts only. A post scheduled for later joins on its day, and its date is capped at "now", so its
  lastmod is never in the future.
- Per-language files: `generateSitemaps()` returns `[{ id: 'en' }, { id: 'ka' }, …]`, and Next.js serves them at
  `/<segment>/sitemap/<id>.xml`. The sitemap docs describe no index file for them. Geotour puts the function in
  `app/sitemaps/sitemap.ts`, serves its own `<sitemapindex>` from `app/sitemap.xml/route.ts`, and lists it in
  `app/robots.ts`.

## 7. Feed (rule: feed)

```ts
// app/blog/feed.xml/route.ts
export const revalidate = 3600 // without cacheComponents; with it, cache the data with 'use cache'

const xml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export async function GET() {
  const posts = (await allPublishedPosts()).slice(0, 20)
  const items = posts.map((p) => `<item><title>${xml(p.title)}</title>` +
    `<link>https://example.com${postPath('en', p.slug)}</link>` +
    `<guid>https://example.com${postPath('en', p.slug)}</guid>` +
    `<pubDate>${new Date(p.publishedAt).toUTCString()}</pubDate>` +
    `<description>${xml(p.description)}</description></item>`).join('')
  const body = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>` +
    `<title>Example Tours blog</title><link>https://example.com/blog</link>` +
    `<description>Guides from Example Tours</description>${items}</channel></rss>`
  return new Response(body, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } })
}
```

One feed per language for multilingual blogs (`/ka/blog/feed.xml`), each advertised from its own index with
`alternates.types`.

## 8. IndexNow on publish (rule: IndexNow key)

Geotour's pattern, which works:
- `lib/seo/indexnow.ts` builds the payload: absolute URLs on the site's host only, no route patterns
  (`/blog/[slug]` cannot be announced), de-duplicated, at most 10,000. It POSTs to `https://api.indexnow.org/indexnow`
  with `host`, `key`, `keyLocation` and `urlList`, and only from production (`VERCEL_ENV === 'production'`, else
  `NODE_ENV`).
- `app/indexnow-key.txt/route.ts` serves the key as `text/plain`, or 404 when no valid key is set.
- The publish path (an admin route handler or server function) calls `revalidatePath(url)` for every language URL
  of the post, then `after(() => pingIndexNow(urls))`, so the ping never delays the response.
- A one-off script announces the whole blog once, and after deploys that change translations outside the admin.
- Google doesn't take part in IndexNow (google-rules §1). Bing, Yandex, Seznam, Naver and others do.

The key is not a secret (it is served publicly), but keep it in configuration, not hard-coded in several files.

## 9. Language routing

Never redirect a blog URL by `Accept-Language` or a cookie for crawlers: Googlebot sends no `Accept-Language`
(google-rules §6). A proxy or middleware that remembers a visitor's language may redirect people. Each locale URL
must still answer with its own page and 200 when fetched cold.

## 10. Verify locally

```bash
npm run build && npm run start   # a production build on http://localhost:3000
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/blog_system_check.py" http://localhost:3000/blog --production-url https://example.com
```
