"""Shared fetch + HTML extraction for the seo-suite scripts.

Python 3.9+ standard library only. Every CLI in this folder builds on
`fetch()` and `extract_page()` so a page is parsed the same way everywhere.
"""
from __future__ import annotations

import codecs
import gzip
import http.client
import json
import re
import ssl
import time
import unicodedata
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
FETCHABLE_SCHEMES = {"http", "https"}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
BYTE_ORDER_MARKS = ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"))


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
        return self.body.decode(_sniff_charset(self.headers.get("content-type", ""), self.body), errors="replace")

    @property
    def is_html(self) -> bool:
        return "html" in self.headers.get("content-type", "").lower()

    @property
    def redirect_failed(self) -> bool:
        """fetch() gave up on the redirects themselves (a loop, more than MAX_REDIRECTS hops, a non-http(s) target),
        not on the network or the server."""
        hops = [hop for hop, _ in self.redirect_chain]
        return self.status is None and bool(hops) and (
            self.final_url in hops or len(hops) > MAX_REDIRECTS
            or urllib.parse.urlsplit(self.final_url).scheme.lower() not in FETCHABLE_SCHEMES)


def _sniff_charset(content_type: str, body: bytes) -> str:
    """Pick the decoder the way browsers do: byte-order mark, then the Content-Type charset, then a <meta> charset
    in the first 1024 bytes, then UTF-8. Labels that are not text encodings Python knows are skipped, as browsers
    skip labels they do not know."""
    for bom, codec in BYTE_ORDER_MARKS:
        if body.startswith(bom):
            return codec
    header = re.search(r"charset=[\"']?([\w.:-]+)", content_type, re.I)
    meta = re.search(rb"<meta[^>]+charset=[\"']?([\w.:-]+)", body[:1024], re.I)
    for label, from_meta in ((header and header.group(1), False), (meta and meta.group(1).decode("ascii"), True)):
        if not label:
            continue
        try:
            name = codecs.lookup(label).name
            # LookupError for codecs that are not text encodings (hex, base64, rot13, zip); UnicodeError for the ones
            # that cannot decode a page at all (undefined, idna). errors="replace" keeps a lone byte valid UTF-16.
            b"<\xff".decode(name, "replace")  # a non-ASCII byte too, so codecs that can't decode real pages fail here
        except (LookupError, UnicodeError):
            continue
        # A <meta> that the ASCII prescan could read cannot be in UTF-16, so browsers read the page as UTF-8 (WHATWG).
        return "utf-8" if from_meta and name.startswith("utf-16") else name
    return "utf-8"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _decode_body(raw: bytes, encoding: str) -> bytes:
    encoding = encoding.lower()
    if encoding == "gzip":
        return gzip.decompress(raw)
    if encoding == "deflate":
        try:
            return zlib.decompress(raw)
        except zlib.error:  # raw deflate without the zlib wrapper, which browsers also accept
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def to_uri(url: str) -> str:
    """Percent-encode the path and query the way browsers do: non-ASCII as UTF-8, spaces, control characters and DEL.
    Other printable ASCII ([ ] | ^ { } ...) stays as written, and existing %xx escapes are upper-cased
    (RFC 3986 §6.2.2.1), so /café, /caf%c3%a9 and /caf%C3%A9 are one URL. A non-ASCII host is IDNA-encoded (Python's
    IDNA 2003 codec; browsers differ only for ß/ς/ZWJ/ZWNJ), so a page that writes its own URLs in punycode matches
    itself in same_site().
    A host IDNA cannot encode ("a..b.com") is kept as written; fetch() reports it as an error."""
    parts = urllib.parse.urlsplit(_ascii_host(url))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, _percent_encode(parts.path), _percent_encode(parts.query),
                                    parts.fragment))


def _percent_encode(part: str) -> str:
    part = re.sub(r"%[0-9a-fA-F]{2}", lambda m: m.group(0).upper(), part)
    return re.sub(r"[^\x21-\x7e]", lambda m: urllib.parse.quote(m.group(0)), part)


def _ascii_host(url: str) -> str:
    """`url` with its host IDNA-encoded (münchen.de -> xn--mnchen-3ya.de), userinfo and port kept. urllib connects to a
    Unicode host but writes it unencoded into the Host header, which fails or sends latin-1 bytes. A host IDNA cannot
    encode (an empty label, a character IDNA 2003 does not know) is kept as written, and fetch() reports it as an error."""
    parts = urllib.parse.urlsplit(url)
    if parts.netloc.isascii():
        return url
    userinfo, at, host_port = parts.netloc.rpartition("@")
    host, colon, port = host_port.partition(":")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return url
    return urllib.parse.urlunsplit(parts._replace(netloc=f"{userinfo}{at}{host}{colon}{port}"))


def fetch(url: str, timeout: float = 20.0, method: str = "GET", user_agent: str = USER_AGENT,
          max_bytes: int = MAX_BODY_BYTES) -> FetchResult:
    """Fetch `url`, following redirects by hand so every hop is recorded. At most `max_bytes` of the body are read."""
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    chain: list[tuple[str, int]] = []
    current = url
    started = time.monotonic()
    for _ in range(MAX_REDIRECTS + 1):
        current = to_uri(current)
        if urllib.parse.urlsplit(current).scheme.lower() not in FETCHABLE_SCHEMES:  # no file://, ftp://, data: via redirects
            return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=f"refusing non-http(s) URL {current}")
        if any(current == hop for hop, _ in chain):
            return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=f"redirect loop back to {current}")
        try:
            request = urllib.request.Request(
                current,  # to_uri() IDNA-encoded the host: urllib writes a Unicode one unencoded into the Host header
                method=method,
                headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Accept": "text/html,*/*;q=0.8"},
            )
            try:
                response = opener.open(request, timeout=timeout)
                status, headers = response.status, response.headers
                raw = response.read(max_bytes)
            except urllib.error.HTTPError as err:  # 3xx (redirect handler declined), 4xx and 5xx land here
                status, headers = err.code, err.headers
                raw = err.read(max_bytes) if method == "GET" else b""
        # OSError covers URLError, TLS, refused/reset and read timeouts (socket.timeout on 3.9); HTTPException covers a
        # cut-off body (IncompleteRead) and a bad port; ValueError covers a host IDNA cannot encode (e.g. "a..b.com").
        except (OSError, http.client.HTTPException, ValueError) as err:
            return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=str(getattr(err, "reason", err)))
        header_map: dict[str, str] = {}
        for k, v in headers.items():
            k = k.lower()
            # A repeated header (Link) is one comma-joined value (RFC 9110 §5.3). Repeated X-Robots-Tag headers are kept
            # one per line instead, because a `bingbot:` scope ends with its own header.
            separator = "\n" if k == "x-robots-tag" else ", "
            header_map[k] = f"{header_map[k]}{separator}{v}" if k in header_map else v
        if status in REDIRECT_STATUSES and "location" in header_map:
            chain.append((current, status))
            location = header_map["location"]
            if not location.isascii():  # http.client reads header bytes as latin-1; browsers read a raw Location as UTF-8
                location = location.encode("latin-1").decode("utf-8", errors="replace")
            current = urllib.parse.urljoin(current, location)
            continue
        encoding = header_map.get("content-encoding", "")
        try:
            body = _decode_body(raw, encoding)
        except (zlib.error, OSError, EOFError) as err:  # gzip.BadGzipFile is an OSError; a truncated gzip raises EOFError
            return FetchResult(url, current, None, {}, b"", chain, _ms_since(started),
                               error=f"HTTP {status} body could not be decoded as {encoding}: {err}")
        return FetchResult(url, current, status, header_map, body, chain, _ms_since(started))
    return FetchResult(url, current, None, {}, b"", chain, _ms_since(started), error=f"more than {MAX_REDIRECTS} redirects")


def _ms_since(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def load_local(path: str, base_url: str = "https://localhost/") -> FetchResult:
    """Treat a saved HTML file as a 200 response so the auditors work offline.

    A file that is valid UTF-8 is read as UTF-8, because a rendered DOM saved from the browser keeps the page's original
    <meta charset>; any other file is decoded like a fetched page (BOM, then <meta charset>)."""
    with open(path, "rb") as fh:
        body = fh.read()
    try:
        body.decode("utf-8")
        content_type = "text/html; charset=utf-8"
    except UnicodeDecodeError:
        content_type = "text/html"
    return FetchResult(base_url, to_uri(base_url), 200, {"content-type": content_type}, body, [], 0)  # same form as extracted URLs


# ---------------------------------------------------------------- HTML parsing

_SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_HEAD_CONTENT_TAGS = {"html", "head", "meta", "link", "title", "style", "script", "noscript", "base", "template"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.base_href = ""
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
        self._in_head = True  # <head> and its tags are optional: browsers keep the head open until body content starts
        self._picture_has_source = False
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
        if self._in_head and tag not in _HEAD_CONTENT_TAGS and not (self._skip_depth or self._in_title):
            self._in_head = False  # <body>, or any body-only element such as <img> or <div>, ends the head for good
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "base" and a.get("href") and not self.base_href:  # only the first <base href> counts
            self.base_href = a["href"]
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
            self._flush_anchor()  # an <a> start tag closes any <a> still open, as browsers do
            self._anchor = a
            self._anchor_text = []
        elif tag == "source" and self._stack_has("picture") and (a.get("srcset") or a.get("type")):
            self._picture_has_source = True
        elif tag == "img":
            if self._stack_has("picture") and self._picture_has_source:
                a["_picture_source"] = "1"  # the browser picks from the <picture>'s <source>s, not just this src
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
        if tag not in ("meta", "link", "base", "img", "br", "hr", "input", "source", "wbr"):
            self._stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "svg":  # foreign element: the self-closing slash really closes it (browsers ignore it on <script> etc.)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        elif tag == "title":
            self._in_title = False
        elif tag in _HEADING_TAGS and self._heading:
            level, parts = self._heading
            self.headings.append((level, _squash(" ".join(parts))))
            self._heading = None
        elif tag == "a":
            self._flush_anchor()
        elif tag == "picture":
            self._picture_has_source = False
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
        if self._in_head and data.strip():
            self._in_head = False  # so does the first non-whitespace text
        self.text_parts.append(data)
        if self._heading:
            self._heading[1].append(data)
        if self._anchor is not None:
            self._anchor_text.append(data)
        if self._paragraph is not None:
            self._paragraph.append(data)

    def close(self):
        super().close()  # parse any buffered trailing data first
        self._flush_anchor()  # an <a> never closed is still a link

    def _flush_anchor(self):
        if self._anchor is not None:
            self.anchors.append({**self._anchor, "_text": _squash(" ".join(self._anchor_text))})
            self._anchor = None

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
    base = urllib.parse.urljoin(result.final_url, parser.base_href)  # a <base href> moves what relative URLs resolve against
    resolve = lambda href: to_uri(urllib.parse.urljoin(base, href))
    # Link-header URLs resolve against the response URL, never the document's <base>.
    header_links = [{**l, "href": urllib.parse.urljoin(result.final_url, l["href"])}
                    for l in parse_link_header(result.headers.get("link", ""))]
    rel_canonical = [l for l in parser.link_tags + header_links if "canonical" in l.get("rel", "").lower().split()]
    canonicals = [l for l in rel_canonical if l.get("_in_head")]  # Google only honours canonicals in <head> or the header
    hreflang = [
        {"hreflang": l.get("hreflang", ""), "href": resolve(l.get("href", ""))}
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
        (internal if same_site(absolute, result.final_url) else external).append(entry)

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
        canonical=resolve(canonicals[0].get("href", "")) if canonicals else "",
        canonical_count=len({resolve(l.get("href", "")) for l in canonicals}),  # distinct URLs: repeating the same one is fine
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
        images=[{**img, "src": resolve(img.get("src", ""))} for img in parser.images],
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
    """Lower-case scheme/host, drop the fragment, give an empty path its implicit '/', and put the host, path and query
    in to_uri() form (so /café, /caf%c3%a9 and /caf%C3%A9 are one URL, and urllib can request it)."""
    parts = urllib.parse.urlsplit(to_uri(url))
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def registrable_host(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, base: str) -> bool:
    return registrable_host(url) == registrable_host(base)


def site_root(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


# X-Robots-Tag rules whose own value follows a colon, so `max-snippet:0` is not read as a user-agent scope.
_ROBOTS_RULES_WITH_VALUES = {"max-snippet", "max-image-preview", "max-video-preview", "unavailable_after"}


def googlebot_robots_directives(meta_robots: str, x_robots_tag: str) -> str:
    """Lower-cased robots rules Googlebot obeys: the robots/googlebot meta tags plus the X-Robots-Tag rules that are
    not scoped to another crawler. `bingbot: noindex, nofollow` applies to Bing only; a scope lasts until the next `agent:`
    or the end of its header (fetch() joins repeated X-Robots-Tag headers with newlines)."""
    rules = []
    for header in x_robots_tag.lower().split("\n"):
        agent = ""
        for token in header.split(","):
            scoped = re.match(r"\s*([\w-]+)\s*:(.*)", token)
            if scoped and scoped.group(1) not in _ROBOTS_RULES_WITH_VALUES:
                agent, token = scoped.group(1), scoped.group(2)
            if agent in ("", "googlebot"):
                rules.append(token.strip())
    return ", ".join([meta_robots.lower(), *rules])


def robots_noindex(directives: str) -> bool:
    """True for `noindex`, or `none` (= noindex, nofollow) as a whole rule; `max-image-preview:none` is not one."""
    return "noindex" in directives or "none" in re.split(r"[,\s]+", directives)


def is_indexable(facts: PageFacts) -> bool:
    return facts.status == 200 and not robots_noindex(googlebot_robots_directives(facts.meta_robots, facts.x_robots_tag))


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
    # Full-width East Asian characters (CJK ideographs, kana, hangul) render about 1 em wide.
    return round(sum(1000 if unicodedata.east_asian_width(ch) in ("W", "F") else _ARIAL_WIDTHS.get(ch, 556) for ch in title)
                 * TITLE_FONT_PX / 1000)


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: SEVERITY_ORDER[f.severity])


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=lambda o: asdict(o) if hasattr(o, "__dataclass_fields__") else str(o)))
