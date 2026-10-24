"""Shared fetch + HTML extraction for the seo-suite scripts.

Python 3.9+ standard library only. Every CLI in this folder builds on
`fetch()` and `extract_page()` so a page is parsed the same way everywhere.
"""
from __future__ import annotations

import gzip
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (compatible; seo-suite-audit/0.1)"
MAX_BODY_BYTES = 15 * 1024 * 1024  # Google crawlers fetch at most 15 MB; we read as much to measure overflow.
GOOGLEBOT_HTML_INDEX_BYTES = 2 * 1024 * 1024  # Googlebot for Search indexes only the first 2 MB of HTML (uncompressed).
MAX_REDIRECTS = 10  # Googlebot follows up to 10 hops.
REDIRECT_STATUSES = {301, 302, 303, 307, 308}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@dataclass
class Finding:
    id: str
    severity: str  # critical | high | medium | low | info
    message: str
    evidence: str = ""


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status: int | None
    headers: dict[str, str]
    body: bytes
    redirect_chain: list[tuple[str, int]]
    elapsed_ms: int
    error: str = ""

    @property
    def text(self) -> str:
        charset = "utf-8"
        match = re.search(r"charset=([\w-]+)", self.headers.get("content-type", ""), re.I)
        if match:
            charset = match.group(1)
        return self.body.decode(charset, errors="replace")

    @property
    def is_html(self) -> bool:
        return "html" in self.headers.get("content-type", "").lower()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _decode_body(raw: bytes, encoding: str) -> bytes:
    encoding = encoding.lower()
    if encoding == "gzip":
        return gzip.decompress(raw)
    if encoding == "deflate":
        return zlib.decompress(raw)
    return raw


def fetch(url: str, timeout: float = 20.0, method: str = "GET", user_agent: str = USER_AGENT) -> FetchResult:
    """Fetch `url`, following redirects by hand so every hop is recorded."""
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    chain: list[tuple[str, int]] = []
    current = url
    started = time.monotonic()
    for _ in range(MAX_REDIRECTS + 1):
        if any(current == hop for hop, _ in chain):
            return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=f"redirect loop back to {current}")
        request = urllib.request.Request(
            current,
            method=method,
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Accept": "text/html,*/*;q=0.8"},
        )
        try:
            response = opener.open(request, timeout=timeout)
            status, headers = response.status, response.headers
            raw = response.read(MAX_BODY_BYTES)
        except urllib.error.HTTPError as err:  # 3xx (redirect handler declined), 4xx and 5xx land here
            status, headers = err.code, err.headers
            raw = err.read(MAX_BODY_BYTES) if method == "GET" else b""
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as err:
            return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=str(getattr(err, "reason", err)))
        header_map = {k.lower(): v for k, v in headers.items()}
        if status in REDIRECT_STATUSES and "location" in header_map:
            chain.append((current, status))
            current = urllib.parse.urljoin(current, header_map["location"])
            continue
        body = _decode_body(raw, header_map.get("content-encoding", ""))
        return FetchResult(url, current, status, header_map, body, chain, _ms_since(started))
    return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=f"more than {MAX_REDIRECTS} redirects")


def _ms_since(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def load_local(path: str, base_url: str = "https://localhost/") -> FetchResult:
    """Treat a saved HTML file as a 200 response so the auditors work offline."""
    with open(path, "rb") as fh:
        body = fh.read()
    return FetchResult(base_url, base_url, 200, {"content-type": "text/html; charset=utf-8"}, body, [], 0)


# ---------------------------------------------------------------- HTML parsing

_SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.title_parts: list[str] = []
        self.title_count = 0
        self.metas: list[dict[str, str]] = []
        self.link_tags: list[dict[str, str]] = []
        self.headings: list[tuple[int, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.json_ld: list[str] = []
        self.iframes: list[str] = []
        self.itemtypes: list[str] = []
        self.text_parts: list[str] = []
        self.paragraphs: list[str] = []
        self.list_count = 0
        self.table_count = 0
        self._stack: list[str] = []
        self._in_head = False
        self._in_title = False
        self._in_json_ld = False
        self._json_ld_buffer: list[str] = []
        self._heading: tuple[int, list[str]] | None = None
        self._anchor: dict[str, str] | None = None
        self._anchor_text: list[str] = []
        self._paragraph: list[str] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if a.get("itemtype"):
            self.itemtypes.append(a["itemtype"])
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "head":
            self._in_head = True
        elif tag == "body":
            self._in_head = False
        elif tag == "title" and not self._stack_has("svg"):
            self._in_title = True
            self.title_count += 1
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.link_tags.append({**a, "_in_head": "1" if self._in_head else ""})
        elif tag in _HEADING_TAGS:
            self._heading = (int(tag[1]), [])
        elif tag == "a":
            self._anchor = a
            self._anchor_text = []
        elif tag == "img":
            self.images.append(a)
            if self._anchor is not None and a.get("alt"):
                self._anchor_text.append(a["alt"])
        elif tag == "script":
            self.scripts.append({**a, "_in_head": "1" if self._in_head else ""})
            if a.get("type", "").lower() == "application/ld+json":
                self._in_json_ld = True
                self._json_ld_buffer = []
        elif tag == "iframe":
            self.iframes.append(a.get("src", ""))
        elif tag == "p":
            self._paragraph = []
        elif tag in ("ul", "ol"):
            self.list_count += 1
        elif tag == "table":
            self.table_count += 1
        if tag in _SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if tag not in ("meta", "link", "img", "br", "hr", "input", "source", "wbr"):
            self._stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        elif tag == "title":
            self._in_title = False
        elif tag in _HEADING_TAGS and self._heading:
            level, parts = self._heading
            self.headings.append((level, _squash(" ".join(parts))))
            self._heading = None
        elif tag == "a" and self._anchor is not None:
            self.anchors.append({**self._anchor, "_text": _squash(" ".join(self._anchor_text))})
            self._anchor = None
        elif tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_ld_buffer))
            self._in_json_ld = False
        elif tag == "p" and self._paragraph is not None:
            text = _squash(" ".join(self._paragraph))
            if text:
                self.paragraphs.append(text)
            self._paragraph = None
        if tag in _SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_ld_buffer.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._skip_depth:
            return
        self.text_parts.append(data)
        if self._heading:
            self._heading[1].append(data)
        if self._anchor is not None:
            self._anchor_text.append(data)
        if self._paragraph is not None:
            self._paragraph.append(data)

    def _stack_has(self, tag: str) -> bool:
        return tag in self._stack


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _meta_content(metas: list[dict[str, str]], key: str, attr: str = "name") -> str:
    for meta in metas:
        if meta.get(attr, "").lower() == key:
            return meta.get("content", "")
    return ""


@dataclass
class PageFacts:
    url: str
    final_url: str
    status: int | None
    redirect_chain: list[tuple[str, int]]
    elapsed_ms: int
    content_type: str
    html_bytes: int
    lang: str
    title: str
    title_count: int
    meta_description: str
    meta_robots: str
    x_robots_tag: str
    canonical: str
    canonical_count: int
    canonical_in_body: bool
    hreflang: list[dict[str, str]]
    viewport: str
    charset_declared: bool
    open_graph: dict[str, str]
    twitter: dict[str, str]
    headings: list[tuple[int, str]]
    word_count: int
    paragraphs: list[str]
    list_count: int
    table_count: int
    internal_links: list[dict[str, str]]
    external_links: list[dict[str, str]]
    images: list[dict[str, str]]
    head_blocking_scripts: list[str]
    json_ld: list[object]
    json_ld_errors: list[str]
    microdata_types: list[str]
    iframes: list[str]
    response_headers: dict[str, str]
    visible_text: str = field(repr=False, default="")

    def to_dict(self, include_text: bool = False) -> dict:
        data = asdict(self)
        if not include_text:
            data.pop("visible_text")
            data["paragraphs"] = data["paragraphs"][:5]
        return data


def extract_page(result: FetchResult) -> PageFacts:
    parser = _PageParser()
    if result.is_html or result.body.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
        parser.feed(result.text)
        parser.close()
    base = result.final_url
    header_links = parse_link_header(result.headers.get("link", ""))
    rel_canonical = [l for l in parser.link_tags + header_links if "canonical" in l.get("rel", "").lower().split()]
    canonicals = [l for l in rel_canonical if l.get("_in_head")]  # Google only honours canonicals in <head> or the header
    hreflang = [
        {"hreflang": l.get("hreflang", ""), "href": urllib.parse.urljoin(base, l.get("href", ""))}
        for l in parser.link_tags + header_links
        if "alternate" in l.get("rel", "").lower().split() and l.get("hreflang")
    ]
    internal, external = [], []
    for anchor in parser.anchors:
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        absolute = normalize_url(urllib.parse.urljoin(base, href))
        entry = {"href": absolute, "text": anchor["_text"], "rel": anchor.get("rel", "")}
        (internal if same_site(absolute, base) else external).append(entry)

    json_ld, json_ld_errors = [], []
    for raw in parser.json_ld:
        try:
            json_ld.append(json.loads(raw))
        except json.JSONDecodeError as err:
            json_ld_errors.append(f"{err.msg} at char {err.pos}")

    head_blocking = [
        s.get("src", "")
        for s in parser.scripts
        if s["_in_head"] and s.get("src") and "async" not in s and "defer" not in s and s.get("type", "") != "module"
    ]
    visible_text = _squash(" ".join(parser.text_parts))
    prefixed = lambda prefix, attr: {
        m.get(attr, ""): m.get("content", "") for m in parser.metas if m.get(attr, "").lower().startswith(prefix)
    }
    return PageFacts(
        url=result.requested_url,
        final_url=result.final_url,
        status=result.status,
        redirect_chain=result.redirect_chain,
        elapsed_ms=result.elapsed_ms,
        content_type=result.headers.get("content-type", ""),
        html_bytes=len(result.body),
        lang=parser.lang,
        title=_squash("".join(parser.title_parts)),
        title_count=parser.title_count,
        meta_description=_meta_content(parser.metas, "description"),
        meta_robots=", ".join(
            m.get("content", "") for m in parser.metas if m.get("name", "").lower() in ("robots", "googlebot")
        ),
        x_robots_tag=result.headers.get("x-robots-tag", ""),
        canonical=urllib.parse.urljoin(base, canonicals[0].get("href", "")) if canonicals else "",
        canonical_count=len(canonicals),
        canonical_in_body=len(rel_canonical) > len(canonicals),
        hreflang=hreflang,
        viewport=_meta_content(parser.metas, "viewport"),
        charset_declared=any("charset" in m for m in parser.metas)
        or "charset=" in _meta_content(parser.metas, "content-type", "http-equiv").lower(),
        open_graph=prefixed("og:", "property"),
        twitter=prefixed("twitter:", "name"),
        headings=parser.headings,
        word_count=len(re.findall(r"\w+", visible_text)),
        paragraphs=parser.paragraphs,
        list_count=parser.list_count,
        table_count=parser.table_count,
        internal_links=internal,
        external_links=external,
        images=[{**img, "src": urllib.parse.urljoin(base, img.get("src", ""))} for img in parser.images],
        head_blocking_scripts=head_blocking,
        json_ld=json_ld,
        json_ld_errors=json_ld_errors,
        microdata_types=parser.itemtypes,
        iframes=parser.iframes,
        response_headers=result.headers,
        visible_text=visible_text,
    )


def parse_link_header(value: str) -> list[dict[str, str]]:
    """Parse an HTTP Link header (RFC 8288) into link-tag-like dicts; header links count as <head> links."""
    links = []
    for part in re.split(r",\s*(?=<)", value):
        match = re.match(r"\s*<([^>]*)>(.*)", part)
        if not match:
            continue
        attrs = {k.lower(): v for k, v in re.findall(r';\s*([\w-]+)\s*=\s*"?([^";]*)"?', match.group(2))}
        links.append({**attrs, "href": match.group(1), "_in_head": "1"})
    return links


# ---------------------------------------------------------------- URL helpers

def normalize_url(url: str) -> str:
    """Lower-case scheme/host, drop the fragment, and give an empty path its implicit '/'."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def registrable_host(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, base: str) -> bool:
    return registrable_host(url) == registrable_host(base)


def site_root(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def is_indexable(facts: PageFacts) -> bool:
    directives = f"{facts.meta_robots},{facts.x_robots_tag}".lower()
    return facts.status == 200 and "noindex" not in directives and "none" not in re.split(r"[,\s]+", directives)


# ---------------------------------------------------------------- SERP display

# Arial advance widths (units per 1000 em). Google renders desktop title links in ~20px Arial
# and truncates around 600px; this is an estimate, not Google's exact cut.
_ARIAL_WIDTHS = {
    **dict.fromkeys("ijl'", 222), **dict.fromkeys("ftI.,:;!/ ", 278), "r": 333, "-": 333, "(": 333, ")": 333,
    **dict.fromkeys("ckvxyzsJ", 500), **dict.fromkeys("abdeghnopqu0123456789?L", 556), "m": 833, "w": 722,
    **dict.fromkeys("FTZ", 611), **dict.fromkeys("ABEKPSVXY&", 667), **dict.fromkeys("CDHNRU", 722),
    **dict.fromkeys("GOQ", 778), "M": 833, "W": 944, "|": 260, '"': 355, "—": 1000, "–": 556,
}
TITLE_FONT_PX = 20
TITLE_MAX_PX = 600


def title_pixel_width(title: str) -> int:
    return round(sum(_ARIAL_WIDTHS.get(ch, 556) for ch in title) * TITLE_FONT_PX / 1000)


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: SEVERITY_ORDER[f.severity])


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=lambda o: asdict(o) if hasattr(o, "__dataclass_fields__") else str(o)))
