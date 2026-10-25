#!/usr/bin/env python3
"""Check a blog's system, not its posts: index, pagination, a sample of posts, archives, author pages, sitemap and feed.

Usage:
  blog_system_check.py https://example.com/blog [--posts 8] [--max-pages 10] [--sitemap URL]
                       [--money-page URL ...] [--indexnow-key-location URL] [--post-prefix /blog/]
  blog_system_check.py http://localhost:3000/blog --production-url https://example.com   # a local production build
  blog_system_check.py https://preview.example.app/blog --production-url https://example.com --ignore-x-robots-tag
Prints JSON: the pages read, every rule with pass, fail or not_checked, and the findings in the shared
{id, severity, message, evidence} shape, so triage.py ranks them. Rules and their sources: RULES below and
skills/seo-blog-system/SKILL.md. Each post's copy is out of scope (seo-blog-review); hreflang return links per
language version are translation_check.py's.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from robots_check import google_visible_robots, sitemaps_in
from schema_rules import iter_typed_nodes, node_types, validate_json_ld
from seo_lib import (Finding, extract_page, fetch, googlebot_robots_directives, normalize_url, print_json,
                     robots_noindex, sort_findings)
from sitemap_check import UnsupportedSitemapFormat, decompress, parse_sitemap

# Each rule: the finding ids that fail it, and where the rule comes from (references/google-rules.md § or a doc).
RULES: list[dict] = [
    {"id": "blog-index-indexable", "rule": "The blog index returns 200, is indexable and canonicalises to itself",
     "source": "google-rules §1", "findings": ["blog-index-error", "blog-index-noindex", "blog-index-canonical-not-self"]},
    {"id": "blog-index-links-posts", "rule": "The index links its posts with <a href> in the server HTML",
     "source": "google-rules §1 (JavaScript SEO)", "findings": ["blog-index-no-post-links"]},
    {"id": "blog-pagination-crawlable", "rule": "Older posts sit on numbered pages linked with <a href>, each returning 200",
     "source": "google-rules §8", "findings": ["blog-pagination-missing", "blog-pagination-error", "blog-pagination-capped"]},
    {"id": "blog-pagination-self-canonical", "rule": "Page 2+ canonicalises to itself, never to page 1",
     "source": "google-rules §8", "findings": ["blog-pagination-canonical-to-first", "blog-pagination-canonical-not-self"]},
    {"id": "blog-pagination-unique-titles", "rule": "Page 2+ has its own title (the page number in it)",
     "source": "google-rules §3", "findings": ["blog-pagination-title-duplicate"]},
    {"id": "blog-pagination-out-of-range-404", "rule": "A page number past the last page returns 404, not an empty 200",
     "source": "google-rules §1 (soft 404)", "findings": ["blog-pagination-out-of-range-200"]},
    {"id": "blog-post-indexable", "rule": "Each sampled post returns 200 without redirecting, is indexable and self-canonical",
     "source": "google-rules §1", "findings": ["blog-post-error", "blog-post-noindex", "blog-post-canonical-not-self"]},
    {"id": "blog-post-article-schema", "rule": "Each post carries Article/BlogPosting JSON-LD that passes schema_rules.py",
     "source": "google-rules §5", "findings": ["blog-post-schema-missing", "schema-parse-error", "schema-missing-required",
                                               "schema-missing-recommended", "schema-no-context", "schema-limited-type",
                                               "schema-self-serving-review"]},
    {"id": "blog-post-breadcrumb-schema", "rule": "Each post carries a BreadcrumbList with at least 2 items",
     "source": "google-rules §5", "findings": ["blog-post-breadcrumb-missing", "schema-breadcrumb-short"]},
    {"id": "blog-post-dates", "rule": "datePublished is set, not in the future, has a time zone, agrees with "
     "article:published_time, and dateModified is never before it", "source": "google-rules §4-5; Google Article doc (upd 2026-09-08)",
     "findings": ["blog-post-date-missing", "blog-post-modified-before-published", "blog-post-date-future",
                  "blog-post-date-no-timezone", "blog-post-date-mismatch"]},
    {"id": "blog-post-byline", "rule": "The JSON-LD author is a real Person or Organization with a url, and its name is printed on the page",
     "source": "google-rules §4-5; Google structured-data policies (upd 2026-07-10)",
     "findings": ["blog-post-author-missing", "blog-post-byline-missing", "blog-post-author-generic", "blog-post-author-no-url"]},
    {"id": "blog-author-pages", "rule": "Each author url returns 200 and carries Person or ProfilePage markup",
     "source": "google-rules §5", "findings": ["blog-author-page-error", "blog-author-page-no-schema"]},
    {"id": "blog-post-lcp-image", "rule": "The hero image is not lazy, is prioritised, has its size and a srcset",
     "source": "google-rules §2", "findings": ["lcp-lazy", "blog-post-lcp-not-prioritised", "img-no-dimensions",
                                               "blog-post-image-no-srcset"]},
    {"id": "blog-post-url-style", "rule": "Post URLs are lower case, hyphenated and without parameters",
     "source": "google-rules §3", "findings": ["blog-post-url-style"]},
    {"id": "blog-post-links-posts", "rule": "Each post links at least 2 other posts, and not the same ones on every post",
     "source": "google-rules §3", "findings": ["blog-post-few-post-links", "blog-related-posts-identical"]},
    {"id": "blog-language-twin-links", "rule": "Each post links its other language versions with <a href> (hreflang is not a link)",
     "source": "google-rules §1, §6", "findings": ["blog-twin-links-missing"]},
    {"id": "blog-money-pages-link-posts", "rule": "Each money page links at least one post",
     "source": "google-rules §3", "findings": ["blog-money-page-no-post-links"]},
    {"id": "blog-archive-status", "rule": "Category and tag archives return 200 and are never empty",
     "source": "google-rules §1 (soft 404)", "findings": ["blog-archive-error", "blog-archive-empty-200"]},
    {"id": "blog-archive-thin-noindex", "rule": "An indexable archive lists at least 3 posts; thinner ones are noindex or merged",
     "source": "seo-suite convention", "findings": ["blog-archive-thin-indexable"]},
    {"id": "blog-sitemap-lists-posts", "rule": "The sitemap is reachable and lists every sampled post",
     "source": "google-rules §1", "findings": ["sitemap-unreachable", "sitemap-invalid-xml", "not-in-sitemap"]},
    {"id": "blog-sitemap-real-lastmod", "rule": "Each post's lastmod is its own last change (within a day of the later of "
     "dateModified and datePublished)", "source": "google-rules §1", "findings": ["blog-sitemap-post-no-lastmod", "blog-sitemap-lastmod-mismatch"]},
    {"id": "blog-feed", "rule": "An RSS or Atom feed is advertised on the index, parses, uses absolute links and carries the newest post",
     "source": "google-rules §1 (feeds are read as sitemaps)", "findings": ["blog-feed-missing", "blog-feed-invalid",
                                                                           "blog-feed-relative-links", "blog-feed-missing-newest",
                                                                           "blog-feed-not-advertised"]},
    {"id": "blog-indexnow-key", "rule": "The IndexNow key file returns 200 with a valid key",
     "source": "google-rules §1 (IndexNow)", "findings": ["blog-indexnow-key-invalid"]},
]
RULE_OF_FINDING = {fid: rule["id"] for rule in RULES for fid in rule["findings"]}
NOT_CHECKED_WITHOUT = {"blog-money-pages-link-posts": "needs --money-page", "blog-indexnow-key": "needs --indexnow-key-location"}

ARTICLE_TYPES = {"Article", "BlogPosting", "NewsArticle", "TechArticle"}
ARCHIVE_SEGMENTS = {"category", "categories", "tag", "tags", "topic", "topics"}
ARCHIVE_QUERY_KEYS = {"category", "tag", "topic"}
NOT_POST_SEGMENTS = ARCHIVE_SEGMENTS | {"author", "authors", "page", "feed", "rss", "atom", "feed.xml", "rss.xml", "atom.xml"}
FEED_TYPES = {"application/rss+xml", "application/atom+xml"}
FEED_PATHS = ("{index}/feed.xml", "{index}/rss.xml", "{index}/feed", "/feed.xml", "/rss.xml", "/atom.xml", "/feed")
GENERIC_AUTHOR = re.compile(r"\b(team|staff|editors?|editorial|admin|webmaster)\b", re.I)
INDEXNOW_KEY = re.compile(r"^[a-zA-Z0-9-]{8,128}$")  # the IndexNow protocol's key format
OUT_OF_RANGE_PAGE = 9999
THIN_ARCHIVE_POSTS = 3
MIN_POST_LINKS = 2
MIN_POSTS_FOR_IDENTICAL = 3
MAX_ARCHIVES = 6
MAX_AUTHORS = 3
MAX_SITEMAP_FILES = 50
LASTMOD_TOLERANCE = timedelta(days=1)  # a date-only lastmod and a zoned dateModified can name neighbouring days


class _BlogHtml(HTMLParser):
    """What seo_lib's PageFacts leaves out: every <link> and <meta property> tag, and the images in order, marking those
    after the <h1>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self.properties: dict[str, str] = {}
        self.images: list[dict[str, str]] = []
        self._after_h1 = False
        self._picture_depth = 0
        self._picture_has_source = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "link":
            self.links.append(a)
        elif tag == "meta" and a.get("property"):
            self.properties.setdefault(a["property"].lower(), a.get("content", ""))
        elif tag == "picture":
            self._picture_depth += 1
            self._picture_has_source = False
        elif tag == "source" and self._picture_depth and (a.get("srcset") or a.get("type")):
            self._picture_has_source = True
        elif tag == "img":
            self.images.append({**a, "_after_h1": "1" if self._after_h1 else "",
                                "_picture_source": "1" if self._picture_depth and self._picture_has_source else ""})

    def handle_endtag(self, tag):
        if tag == "h1":
            self._after_h1 = True
        elif tag == "picture" and self._picture_depth:
            self._picture_depth -= 1


class Site:
    """Maps between the origin the checker fetches (a local build, a preview) and the production origin pages name."""

    def __init__(self, start_url: str, production_url: str | None):
        parts = urllib.parse.urlsplit(start_url)
        self.fetch_origin = f"{parts.scheme}://{parts.netloc}".lower()
        public = urllib.parse.urlsplit(production_url) if production_url else parts
        self.public_origin = f"{public.scheme}://{public.netloc}".lower()

    def public(self, url: str) -> str:
        url = normalize_url(url)
        return self.public_origin + url[len(self.fetch_origin):] if url.startswith(self.fetch_origin + "/") else url

    def local(self, url: str) -> str:
        url = normalize_url(url)
        return self.fetch_origin + url[len(self.public_origin):] if url.startswith(self.public_origin + "/") else url


class Page:
    """One fetched page: PageFacts plus the <link> tags and ordered images, with URLs in their production form."""

    def __init__(self, url: str, site: Site, fetch_fn, ignore_x_robots_tag: bool):
        self.url = site.public(url)
        result = fetch_fn(site.local(url))
        self.facts = extract_page(result)
        self.status = result.status
        self.redirected = bool(result.redirect_chain)
        self.error = result.error
        x_robots = "" if ignore_x_robots_tag else self.facts.x_robots_tag
        self.indexable = self.status == 200 and not robots_noindex(googlebot_robots_directives(self.facts.meta_robots, x_robots))
        self.canonical = site.public(self.facts.canonical) if self.facts.canonical else ""
        parser = _BlogHtml()
        if result.body:
            parser.feed(result.text)
            parser.close()
        base = result.final_url
        self.link_tags = [{**l, "href": site.public(urllib.parse.urljoin(base, l["href"]))} for l in parser.links if l.get("href")]
        self.images = [{**img, "src": urllib.parse.urljoin(base, img.get("src", ""))} for img in parser.images]
        self.properties = parser.properties
        self.anchors = [{**a, "href": site.public(a["href"])} for a in self.facts.internal_links + self.facts.external_links]
        self.links = [a["href"] for a in self.anchors]
        self.hreflang = [{**h, "href": site.public(h["href"])} for h in self.facts.hreflang]

    def self_canonical(self) -> bool:
        return not self.canonical or self.canonical.rstrip("/") == self.url.rstrip("/")


# ---------------------------------------------------------------- pure helpers

def parse_when(value: str) -> tuple[datetime | None, bool]:
    """(instant, has_zone) for an ISO 8601 date or date-time. A value without a zone is read as UTC."""
    value = (value or "").strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return None, False
    if len(value) == 10:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc), False
    try:  # Python 3.9's fromisoformat takes neither Z nor fractional seconds of other lengths
        moment = datetime.fromisoformat(re.sub(r"\.\d+", "", value).replace("Z", "+00:00"))
    except ValueError:
        return None, False
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc), False
    return moment, True


def dates_disagree(a: str, b: str) -> bool:
    """Two publish dates name different moments: instants when both carry a zone, else the calendar day as written."""
    (when_a, zone_a), (when_b, zone_b) = parse_when(a), parse_when(b)
    if when_a is None or when_b is None:
        return False
    if zone_a and zone_b:
        return abs(when_a - when_b) > timedelta(minutes=1)
    return a.strip()[:10] != b.strip()[:10]


def lastmod_disagrees(lastmod: str, modified: str) -> bool:
    when_lastmod, _ = parse_when(lastmod)
    when_modified, _ = parse_when(modified)
    return bool(when_lastmod and when_modified) and abs(when_lastmod - when_modified) > LASTMOD_TOLERANCE


def path_segments(url: str) -> list[str]:
    return [s for s in urllib.parse.urlsplit(url).path.split("/") if s]


def is_post_url(url: str, post_prefix: str) -> bool:
    """A post is one path segment under the prefix, with no query, that is not an archive, feed or page number."""
    parts = urllib.parse.urlsplit(url)
    if parts.query or not parts.path.startswith(post_prefix):
        return False
    rest = [s for s in parts.path[len(post_prefix):].split("/") if s]
    return len(rest) == 1 and rest[0].lower() not in NOT_POST_SEGMENTS


def is_archive_url(url: str, index_url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    if any(s.lower() in ARCHIVE_SEGMENTS for s in path_segments(url)[:-1]):
        return True
    keys = {k.lower() for k in urllib.parse.parse_qs(parts.query)}
    return parts.path.rstrip("/") == urllib.parse.urlsplit(index_url).path.rstrip("/") and bool(keys & ARCHIVE_QUERY_KEYS)


def page_url(index_url: str, pattern: str, number: int) -> str:
    return f"{index_url}?page={number}" if pattern == "query" else f"{index_url.rstrip('/')}/page/{number}"


def next_page(page: Page, index_url: str, number: int) -> tuple[str, str] | None:
    """(url, pattern) of the page after `number`: a ?page=N or /page/N link, else an <a rel=next>."""
    for pattern in ("query", "path"):
        wanted = normalize_url(page_url(index_url, pattern, number + 1))
        if any(link.rstrip("/") == wanted.rstrip("/") for link in page.links):
            return wanted, pattern
    for anchor in page.anchors:
        if "next" in anchor.get("rel", "").lower().split():
            return anchor["href"], ""
    return None


def article_node(json_ld: list) -> dict | None:
    for _, node in iter_typed_nodes(json_ld):
        if set(node_types(node)) & ARTICLE_TYPES:
            return node
    return None


def has_type(json_ld: list, wanted: set[str]) -> bool:
    return any(set(node_types(node)) & wanted for _, node in iter_typed_nodes(json_ld))


def authors_of(node: dict) -> list[dict]:
    raw = node.get("author")
    items = raw if isinstance(raw, list) else [raw] if raw else []
    return [a if isinstance(a, dict) else {"name": str(a)} for a in items]


def hero_image(images: list[dict]) -> dict | None:
    """The image a post leads with: the first after its <h1>, else the first on the page."""
    return next((img for img in images if img["_after_h1"]), images[0] if images else None)


# ---------------------------------------------------------------- the checker

class Checker:
    def __init__(self, index_url: str, fetch_fn, *, posts: int, max_pages: int, sitemap: str | None, money_pages,
                 indexnow_key_location: str | None, production_url: str | None, post_prefix: str | None,
                 ignore_x_robots_tag: bool, now: datetime):
        self.site = Site(index_url, production_url)
        self.index_url = self.site.public(index_url)
        self.post_prefix = post_prefix or urllib.parse.urlsplit(self.index_url).path.rstrip("/") + "/"
        self.fetch_fn, self.ignore_x_robots_tag, self.now = fetch_fn, ignore_x_robots_tag, now
        self.sample_size, self.max_pages, self.sitemap_url = posts, max_pages, sitemap
        self.money_pages, self.indexnow_key_location = list(money_pages), indexnow_key_location
        self.findings: list[Finding] = []
        self.checked: set[str] = set()
        self.known_posts: dict[str, None] = {}  # an ordered set
        self.sitemap_lastmod: dict[str, str] = {}
        self.pages: dict = {"index": None, "sitemap": None, "pagination": [], "posts": [], "authors": [], "archives": [],
                            "feed": None}

    def get(self, url: str) -> Page:
        return Page(url, self.site, self.fetch_fn, self.ignore_x_robots_tag)

    def mark(self, *rule_ids: str) -> None:
        """Record that these rules were checked: they pass unless a finding fails them."""
        self.checked.update(rule_ids)

    def add(self, finding_id: str, severity: str, message: str, evidence: str = "") -> None:
        self.findings.append(Finding(finding_id, severity, message, evidence))

    def post_links(self, page: Page) -> list[str]:
        return list(dict.fromkeys(l for l in page.links if l in self.known_posts and l != page.url))

    def remember_posts(self, urls) -> None:
        self.known_posts.update(dict.fromkeys(u for u in urls if is_post_url(u, self.post_prefix)))

    def run(self) -> dict:
        index = self.get(self.index_url)
        self.pages["index"] = {"url": index.url, "status": index.status, "indexable": index.indexable, "canonical": index.canonical}
        if not self.check_index(index):
            return self.report()
        self.check_sitemap()
        listing = [index] + self.check_pagination(index)
        sampled = self.check_posts([u for page in listing for u in page.links if is_post_url(u, self.post_prefix)])
        self.check_archives(listing + sampled)
        self.check_feed(index)
        self.check_money_pages()
        self.check_indexnow()
        return self.report()

    def check_index(self, index: Page) -> bool:
        self.mark("blog-index-indexable")
        if index.status != 200:
            self.add("blog-index-error", "critical", f"The blog index returned {index.status or index.error}", index.url)
            return False
        if not index.indexable:
            self.add("blog-index-noindex", "high", "The blog index is noindex", index.url)
        if not index.self_canonical():
            self.add("blog-index-canonical-not-self", "high", f"The blog index canonicalises to {index.canonical}", index.url)
        self.mark("blog-index-links-posts")
        self.remember_posts(index.links)
        if not any(is_post_url(u, self.post_prefix) for u in index.links):
            self.add("blog-index-no-post-links", "high", f"The index HTML has no <a href> to a post under {self.post_prefix} "
                     "(the list may be rendered by JavaScript)", index.url)
        return True

    def check_pagination(self, index: Page) -> list[Page]:
        pages, number, current, pattern = [], 1, index, ""
        while True:
            found = next_page(current, self.index_url, number)
            if not found:
                break
            if number >= self.max_pages:
                self.add("blog-pagination-capped", "info", f"Pagination continues past --max-pages {self.max_pages}; later pages were not checked", found[0])
                break
            url, pattern = found[0], found[1] or pattern
            number += 1
            page = self.get(url)
            pages.append(page)
            if page.status != 200 or page.redirected:
                self.add("blog-pagination-error", "high", f"Page {number} of the index returned {page.status or page.error}"
                         f"{' after a redirect' if page.redirected else ''}", url)
                break
            self.remember_posts(page.links)
            if page.canonical and page.canonical.rstrip("/") == index.url.rstrip("/"):
                self.add("blog-pagination-canonical-to-first", "high", f"Page {number} canonicalises to page 1, so the posts only it "
                         "links look like duplicates' links", url)
            elif not page.self_canonical():
                self.add("blog-pagination-canonical-not-self", "medium", f"Page {number} canonicalises to {page.canonical}", url)
            if page.facts.title and page.facts.title == index.facts.title:
                self.add("blog-pagination-title-duplicate", "low", f"Page {number} repeats page 1's title", f"{url}: {page.facts.title}")
            current = page
        self.pages["pagination"] = [{"url": p.url, "status": p.status, "canonical": p.canonical, "title": p.facts.title} for p in pages]
        if pages:
            self.mark("blog-pagination-crawlable", "blog-pagination-self-canonical", "blog-pagination-unique-titles")
        elif self.sitemap_lastmod:
            self.mark("blog-pagination-crawlable")
            on_index = {u for u in index.links if is_post_url(u, self.post_prefix)}
            unlisted = [u for u in self.known_posts if u not in on_index]
            if unlisted:
                self.add("blog-pagination-missing", "high", f"{len(unlisted)} posts in the sitemap are not on the index, and the index "
                         "links no page 2", ", ".join(unlisted[:5]))
        if pattern:
            self.mark("blog-pagination-out-of-range-404")
            probe = page_url(self.index_url, pattern, OUT_OF_RANGE_PAGE)
            if self.get(probe).status == 200:
                self.add("blog-pagination-out-of-range-200", "medium", f"Page {OUT_OF_RANGE_PAGE}, past the last page, returns 200 "
                         "(a soft 404)", probe)
        return pages

    def check_sitemap(self) -> None:
        self.mark("blog-sitemap-lists-posts")
        if self.sitemap_url:
            queue = [self.sitemap_url]
        else:
            robots = self.fetch_fn(self.site.local(self.site.public_origin + "/robots.txt"))
            queue = sitemaps_in(google_visible_robots(robots.text)) if robots.status == 200 else []
            queue = queue or [self.site.public_origin + "/sitemap.xml"]
        seen, read = set(), []
        while queue and len(seen) < MAX_SITEMAP_FILES:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            result = self.fetch_fn(self.site.local(url))
            if result.status != 200:
                continue
            try:
                kind, entries = parse_sitemap(decompress(result.body))
            except (ET.ParseError, UnsupportedSitemapFormat, OSError, EOFError) as err:
                self.add("sitemap-invalid-xml", "high", f"{url} could not be read as a sitemap: {err}", url)
                continue
            read.append(url)
            if kind == "sitemapindex":
                queue += [e["loc"] for e in entries if e["loc"]]
                continue
            for entry in entries:
                if entry["loc"]:
                    self.sitemap_lastmod[self.site.public(entry["loc"])] = entry["lastmod"]
        self.pages["sitemap"] = {"files": read, "urls": len(self.sitemap_lastmod)}
        if not read:
            self.add("sitemap-unreachable", "high", "No sitemap could be read (robots.txt Sitemap: lines, else /sitemap.xml)",
                     ", ".join(sorted(seen)))
        self.remember_posts(self.sitemap_lastmod)

    def check_posts(self, listed: list[str]) -> list[Page]:
        sampled, link_sets, missing_from_sitemap = [], [], []
        for url in list(dict.fromkeys(listed))[:self.sample_size]:
            post = self.get(url)
            row = {"url": post.url, "status": post.status, "indexable": post.indexable, "canonical": post.canonical}
            self.pages["posts"].append(row)
            self.mark("blog-post-indexable")
            if post.status != 200 or post.redirected:
                self.add("blog-post-error", "high", f"Post returned {post.status or post.error}{' after a redirect' if post.redirected else ''}", url)
                continue
            sampled.append(post)
            if not post.indexable:
                self.add("blog-post-noindex", "high", "A post the index links is noindex", url)
            if not post.self_canonical():
                self.add("blog-post-canonical-not-self", "medium", f"Post canonicalises to {post.canonical}", url)
            self.check_post_schema(post)
            self.check_hero(post)
            self.check_post_links(post, link_sets)
            if self.sitemap_lastmod and post.indexable:
                self.check_post_lastmod(post, missing_from_sitemap)
        if missing_from_sitemap:
            self.add("not-in-sitemap", "low", f"{len(missing_from_sitemap)} sampled posts are missing from the sitemap",
                     ", ".join(missing_from_sitemap[:5]))
        if len(link_sets) >= MIN_POSTS_FOR_IDENTICAL and link_sets[0] and all(s == link_sets[0] for s in link_sets):
            self.add("blog-related-posts-identical", "low", f"All {len(link_sets)} sampled posts link the same posts, so most posts "
                     "get no link from a related one [heuristic]", ", ".join(sorted(link_sets[0])[:5]))
        self.check_authors(sampled)
        return sampled

    def check_post_schema(self, post: Page) -> None:
        url, facts = post.url, post.facts
        self.mark("blog-post-article-schema", "blog-post-breadcrumb-schema")
        for error in facts.json_ld_errors:
            self.add("schema-parse-error", "high", f"JSON-LD does not parse: {error}", url)
        for finding in validate_json_ld(facts.json_ld)[1]:
            self.add(finding.id, finding.severity, finding.message, f"{url} {finding.evidence}".strip())
        if not has_type(facts.json_ld, {"BreadcrumbList"}):
            self.add("blog-post-breadcrumb-missing", "low", "No BreadcrumbList JSON-LD", url)
        node = article_node(facts.json_ld)
        if node is None:
            self.add("blog-post-schema-missing", "medium", "No Article, BlogPosting or NewsArticle JSON-LD", url)
            return
        self.mark("blog-post-dates", "blog-post-byline")
        published, modified = str(node.get("datePublished") or ""), str(node.get("dateModified") or "")
        when_published, published_zone = parse_when(published)
        when_modified, modified_zone = parse_when(modified)
        if when_published is None:
            self.add("blog-post-date-missing", "medium", "The article markup has no readable datePublished", url)
        else:
            if when_published > self.now:
                self.add("blog-post-date-future", "medium", f"datePublished {published} is in the future", url)
            if when_modified and when_modified < when_published:
                self.add("blog-post-modified-before-published", "medium",
                         f"dateModified {modified} is before datePublished {published}", url)
            og_published = post.properties.get("article:published_time", "")
            if og_published and dates_disagree(published, og_published):
                self.add("blog-post-date-mismatch", "low", f"article:published_time {og_published} disagrees with datePublished {published}", url)
        unzoned = [v for v, when, zone in ((published, when_published, published_zone), (modified, when_modified, modified_zone))
                   if when and not zone]
        if unzoned:
            self.add("blog-post-date-no-timezone", "low", f"Dates without a time zone: {', '.join(unzoned)}", url)
        authors = authors_of(node)
        if not authors:
            self.add("blog-post-author-missing", "medium", "The article markup names no author", url)
        text = facts.visible_text.casefold()
        for author in authors:
            name = str(author.get("name") or "").strip()
            if name and name.casefold() not in text:
                self.add("blog-post-byline-missing", "medium", f"The markup's author '{name}' is not printed on the page", url)
            if "Person" in node_types(author) and GENERIC_AUTHOR.search(name):
                self.add("blog-post-author-generic", "low", f"Author '{name}' is typed Person but names a group "
                         "(use Organization, or the real writer) [heuristic]", url)
            if not author.get("url"):
                self.add("blog-post-author-no-url", "low", f"Author '{name}' has no url to a page about them", url)

    def check_hero(self, post: Page) -> None:
        hero = hero_image(post.images)
        if hero is None:
            return
        self.mark("blog-post-lcp-image")
        url, src = post.url, hero["src"]
        if hero.get("loading", "").lower() == "lazy":
            self.add("lcp-lazy", "medium", "The post's hero image is loading=lazy", f"{url}: {src}")
        else:
            preloaded = any("preload" in l.get("rel", "").lower().split() and l.get("as", "").lower() == "image"
                            and (normalize_url(l["href"]) == normalize_url(src) or l.get("imagesrcset") and l.get("imagesrcset") == hero.get("srcset"))
                            for l in post.link_tags)
            if hero.get("fetchpriority", "").lower() != "high" and not preloaded:
                self.add("blog-post-lcp-not-prioritised", "low", "The hero image has no fetchpriority=high and no matching "
                         "<link rel=preload as=image>", f"{url}: {src}")
        if not (hero.get("width") and hero.get("height")) and hero.get("data-nimg") != "fill":
            self.add("img-no-dimensions", "low", "The hero image has no width/height", f"{url}: {src}")
        if not (hero.get("srcset") or hero["_picture_source"] or src.lower().endswith(".svg")):
            self.add("blog-post-image-no-srcset", "low", "The hero image has no srcset, so every screen downloads the same file",
                     f"{url}: {src}")

    def check_post_links(self, post: Page, link_sets: list) -> None:
        url = post.url
        self.mark("blog-post-url-style", "blog-post-links-posts", "blog-language-twin-links")
        path = urllib.parse.urlsplit(url).path
        if path != path.lower() or "_" in path or urllib.parse.urlsplit(url).query:
            self.add("blog-post-url-style", "low", "Post URL has capitals, underscores or parameters", url)
        links = self.post_links(post)
        link_sets.append(set(links))
        if len(links) < MIN_POST_LINKS:
            self.add("blog-post-few-post-links", "low", f"Post links {len(links)} other posts (want {MIN_POST_LINKS}+)", url)
        twins = [h["href"] for h in post.hreflang if h["hreflang"].lower() != "x-default" and h["href"].rstrip("/") != url.rstrip("/")]
        missing = [t for t in dict.fromkeys(twins) if t not in post.links]
        if missing:
            self.add("blog-twin-links-missing", "medium", f"{len(missing)} language versions are in hreflang but not linked from the page",
                     f"{url} -> {', '.join(missing)}")

    def check_post_lastmod(self, post: Page, missing: list) -> None:
        self.mark("blog-sitemap-real-lastmod")
        if post.url not in self.sitemap_lastmod:
            missing.append(post.url)
            return
        lastmod = self.sitemap_lastmod[post.url]
        if not lastmod:
            self.add("blog-sitemap-post-no-lastmod", "low", "The sitemap lists the post without lastmod", post.url)
            return
        node = article_node(post.facts.json_ld) or {}
        dates = [d for d in (str(node.get("datePublished") or ""), str(node.get("dateModified") or "")) if parse_when(d)[0]]
        if dates:
            honest = max(dates, key=lambda d: parse_when(d)[0])
            if lastmod_disagrees(lastmod, honest):
                self.add("blog-sitemap-lastmod-mismatch", "medium", f"Sitemap lastmod {lastmod} is not the post's last change {honest}", post.url)

    def check_authors(self, posts: list[Page]) -> None:
        urls = []
        for post in posts:
            for author in authors_of(article_node(post.facts.json_ld) or {}):
                if author.get("url"):
                    urls.append(self.site.public(urllib.parse.urljoin(post.url, str(author["url"]))))
        rows = []
        for url in list(dict.fromkeys(urls))[:MAX_AUTHORS]:
            self.mark("blog-author-pages")
            page = self.get(url)
            rows.append({"url": url, "status": page.status})
            if page.status != 200:
                self.add("blog-author-page-error", "medium", f"Author page returned {page.status or page.error}", url)
            elif not has_type(page.facts.json_ld, {"Person", "ProfilePage"}):
                self.add("blog-author-page-no-schema", "low", "Author page has no Person or ProfilePage markup", url)
        self.pages["authors"] = rows

    def check_archives(self, pages: list[Page]) -> None:
        candidates = [u for page in pages for u in page.links if is_archive_url(u, self.index_url)]
        rows = []
        for url in list(dict.fromkeys(candidates))[:MAX_ARCHIVES]:
            self.mark("blog-archive-status", "blog-archive-thin-noindex")
            page = self.get(url)
            count = len(self.post_links(page))
            rows.append({"url": url, "status": page.status, "indexable": page.indexable, "posts": count})
            if page.status != 200:
                self.add("blog-archive-error", "medium", f"Archive returned {page.status or page.error}", url)
            elif page.indexable and page.self_canonical() and count == 0:
                self.add("blog-archive-empty-200", "medium", "Indexable archive lists no posts (a soft 404: return 404 or noindex)", url)
            elif page.indexable and page.self_canonical() and count < THIN_ARCHIVE_POSTS:
                self.add("blog-archive-thin-indexable", "low", f"Indexable archive lists {count} posts (fewer than {THIN_ARCHIVE_POSTS})", url)
        self.pages["archives"] = rows

    def check_feed(self, index: Page) -> None:
        self.mark("blog-feed")
        advertised = [l["href"] for l in index.link_tags
                      if "alternate" in l.get("rel", "").lower().split() and l.get("type", "").lower() in FEED_TYPES]
        index_path = urllib.parse.urlsplit(self.index_url).path.rstrip("/")
        probes = [self.site.public_origin + p.format(index=index_path) for p in FEED_PATHS]
        for url in advertised or probes:
            result = self.fetch_fn(self.site.local(url))
            if result.status == 200:
                break
        else:
            self.add("blog-feed-missing", "medium", "No RSS or Atom feed: none is advertised on the index and none answers at the usual paths",
                     ", ".join(advertised or probes))
            self.pages["feed"] = None
            return
        self.pages["feed"] = {"url": url, "advertised": bool(advertised)}
        if not advertised:
            self.add("blog-feed-not-advertised", "low", "The feed exists but the index has no <link rel=alternate type=application/rss+xml>", url)
        try:
            kind, entries = parse_sitemap(decompress(result.body))
        except (ET.ParseError, UnsupportedSitemapFormat, OSError, EOFError) as err:
            self.add("blog-feed-invalid", "medium", f"The feed does not parse: {err}", url)
            return
        if kind not in ("rss", "feed"):
            self.add("blog-feed-invalid", "medium", f"The feed is a <{kind}>, not RSS 2.0 or Atom", url)
            return
        relative = [e["loc"] for e in entries if e["loc"] and not e["loc"].lower().startswith(("http://", "https://"))]
        if relative:
            self.add("blog-feed-relative-links", "medium", f"{len(relative)} feed items have relative links", relative[0])
        newest = next((u for u in index.links if is_post_url(u, self.post_prefix)), None)
        in_feed = {self.site.public(urllib.parse.urljoin(url, e["loc"])) for e in entries if e["loc"]}
        if newest and newest not in in_feed:
            self.add("blog-feed-missing-newest", "low", "The newest post on the index is not in the feed", newest)

    def check_money_pages(self) -> None:
        for url in self.money_pages:
            self.mark("blog-money-pages-link-posts")
            page = self.get(url)
            if page.status != 200 or not self.post_links(page):
                self.add("blog-money-page-no-post-links", "low", f"Money page links no post (HTTP {page.status or page.error})", page.url)

    def check_indexnow(self) -> None:
        if not self.indexnow_key_location:
            return
        self.mark("blog-indexnow-key")
        result = self.fetch_fn(self.site.local(self.indexnow_key_location))
        if result.status != 200 or not INDEXNOW_KEY.match(result.text.strip()):
            self.add("blog-indexnow-key-invalid", "medium", f"The key file returned {result.status or result.error} without a valid key",
                     self.indexnow_key_location)

    def report(self) -> dict:
        failed = {RULE_OF_FINDING.get(f.id) for f in self.findings if f.severity != "info"}  # info: a tool limit, not a defect
        rules = []
        for rule in RULES:
            status = "fail" if rule["id"] in failed else "pass" if rule["id"] in self.checked else "not_checked"
            row = {"id": rule["id"], "status": status, "rule": rule["rule"], "source": rule["source"],
                   "findings": sum(1 for f in self.findings if RULE_OF_FINDING.get(f.id) == rule["id"])}
            if status == "not_checked" and rule["id"] in NOT_CHECKED_WITHOUT:
                row["note"] = NOT_CHECKED_WITHOUT[rule["id"]]
            rules.append(row)
        return {"url": self.index_url, "fetched_from": self.site.fetch_origin, "post_prefix": self.post_prefix,
                "pages": self.pages, "rules": rules,
                "counts": {s: sum(1 for r in rules if r["status"] == s) for s in ("pass", "fail", "not_checked")},
                "findings": [vars(f) for f in sort_findings(self.findings)]}


def check_blog(index_url: str, fetch_fn=fetch, *, posts: int = 8, max_pages: int = 10, sitemap: str | None = None,
               money_pages=(), indexnow_key_location: str | None = None, production_url: str | None = None,
               post_prefix: str | None = None, ignore_x_robots_tag: bool = False, now: datetime | None = None) -> dict:
    return Checker(index_url, fetch_fn, posts=posts, max_pages=max_pages, sitemap=sitemap, money_pages=money_pages,
                   indexnow_key_location=indexnow_key_location, production_url=production_url, post_prefix=post_prefix,
                   ignore_x_robots_tag=ignore_x_robots_tag, now=now or datetime.now(timezone.utc)).run()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("index_url", help="the blog index, e.g. https://example.com/blog")
    ap.add_argument("--posts", type=int, default=8, help="posts to sample from the index and its pages, in listing order")
    ap.add_argument("--max-pages", type=int, default=10, help="index pages to follow")
    ap.add_argument("--sitemap", help="sitemap or sitemap index URL (default: robots.txt Sitemap: lines, else /sitemap.xml)")
    ap.add_argument("--money-page", action="append", default=[], help="a money page that should link posts (repeatable)")
    ap.add_argument("--indexnow-key-location", help="the IndexNow key file URL (the keyLocation the site sends)")
    ap.add_argument("--production-url", help="the production origin pages name in canonicals and sitemaps, when checking a local build or preview")
    ap.add_argument("--post-prefix", help="path posts live under (default: the index path plus /)")
    ap.add_argument("--ignore-x-robots-tag", action="store_true", help="ignore X-Robots-Tag headers (preview deployments send noindex)")
    args = ap.parse_args()
    print_json(check_blog(args.index_url, posts=args.posts, max_pages=args.max_pages, sitemap=args.sitemap,
                          money_pages=args.money_page, indexnow_key_location=args.indexnow_key_location,
                          production_url=args.production_url, post_prefix=args.post_prefix,
                          ignore_x_robots_tag=args.ignore_x_robots_tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
