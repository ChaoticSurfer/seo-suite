#!/usr/bin/env python3
"""Check a blog post's language versions against each other: is each one really translated, complete and wired up?

Built for posts an LLM (such as Claude) wrote and translated. It looks for what unreviewed machine translation gets
wrong: paragraphs left in the source language, numbers dropped or invented, titles and alt text copied untranslated,
sections missing, canonicals pointing at another language, and hreflang sets that disagree.

Usage:
  translation_check.py https://blog.example.com/en/post/      # follows hreflang alternates (breadth-first, max 20 pages)
  translation_check.py --urls en:https://example.com/post ka:https://example.com/ka/post   # hreflang missing or broken
  translation_check.py --files en:post.en.md ka:post.ka.md ru:post.ru.html --base-url "https://blog.example.com/{lang}/post/"
  translation_check.py --files en:blog_posts.csv ka:lib/i18n/content/blog/ka.json --key SLUG --fields title,excerpt,content
                                                   # posts kept as data: a table export row, a translation file entry
  translation_check.py URL --source en     # version the others are compared with (default: x-default target, else longest)
Outputs JSON {"url", "source", "hreflang_checked", "cluster": [one summary per version], "findings": [...]};
finding ids start with "translation-".

How to read it:
- Language is detected offline from the visible main text: Unicode script first (Georgian Mkhedruli, Cyrillic,
  Greek, ...), then stopword profiles for en, de, fr, es, it, pt, nl, pl, tr, ru, uk, bg. Google also goes by visible
  content and ignores lang attributes and URLs, so those are only compared with what was detected. Blocks under 8
  words are too short to judge and are skipped. On a page in a non-Latin script, a mostly Latin block with 30% of its
  letters in the page's script (a Russian sentence quoting English UI labels) is judged in the page's script; a block
  whose profile scores within 0.05 of the page language is read as the page language. A language without a profile
  (sv, cs, ro, sr, mk...) is only called foreign when a profiled language clearly matches; close neighbours can still
  be mistaken for each other (Galician reads as Portuguese, Catalan as Spanish), so check such a body-language
  finding by eye.
- Findings marked [heuristic] (length band, numbers, structure, link language) rest on no published Google threshold.
  They are leads for a reviewer, not verdicts.
- None of this replaces a fluent human reviewer per language, which Google staff recommend for machine translations
  (Illyes, Search Central office hours, June 2024). Keep a version nobody has reviewed noindex; don't block it in
  robots.txt (Google removed that advice on 2025-06-11), and never combine noindex with a robots.txt disallow.
- Main content is the largest <article> (if it holds at least 30% of the page's words), else <main>, else <body>
  without nav, aside, form and the page's own header/footer. Code (<pre>, <code>) is ignored.
- Markdown support is a minimal subset: front matter (title, description, lang, canonical), headings, paragraphs,
  lists, tables, block quotes, links, images and code fences. Raw HTML inside Markdown is read as text, and template
  syntax ({{ site.baseurl }}, {% include %}) is not expanded, so check drafts that use it as built HTML.
- A .json, .csv or .tsv draft is a post kept as data: --key picks the entry (a translation file's slug, a dotted key
  in a TS dictionary the project rendered to JSON, or the slug column of a table export such as Supabase's), and
  --fields names what to read. The first title field becomes the <title> and H1, the first excerpt or description the
  meta description, and the rest the body, as a blog template renders them (seo_lib.content_entry_page).
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser

from schema_rules import iter_typed_nodes
from seo_lib import (
    COMMON_CODE_MISTAKES, ISO_639_1, FetchResult, Finding, PageFacts, content_fields, extract_page, fetch, html_draft,
    is_indexable, load_draft_file, normalize_url, print_json, same_site, sort_findings,
)

MAX_VERSIONS = 20  # a post rarely has more language versions; the rest are reported as translation-cluster-capped
FETCH_DELAY_S = 0.3  # pause between fetches of one site
MIN_BLOCK_WORDS = 8  # shorter blocks (captions, names, buttons) are too short to tell the language from
MIN_DETECT_LETTERS = 20
DETECT_CONFIDENCE = 0.2  # stopword share needed to call text another language (script-only languages: script share)
UNPROFILED_CONFIDENCE = 0.35  # stricter when the page language has no profile but shares the script (sv vs en, sr vs bg)
EXPECTED_LANGUAGE_MARGIN = 0.05  # another profile must beat the page's language by this much (es and fr share de, en, la)
OWN_SCRIPT_MIN_SHARE = 0.3  # mostly Latin text with this share in the page's non-Latin script = it quoting Latin terms
SIDE_BY_SIDE_SHARE = 0.25  # this share of main-content words in a second language = side-by-side or partial translation
ARTICLE_MIN_SHARE = 0.3  # an <article> smaller than this share of the page is a teaser card, not the post
SMALL_NUMBER_MAX = 9  # integers up to 9 are often written as words ("three"), so they are not compared
DATE_PART_MAX = 12  # date parts up to 12 may be a month, which other languages write as a word
LENGTH_BAND = (0.7, 1.4)  # [heuristic] observed / expected word-count ratio outside this band suggests omission or addition
MIN_LENGTH_CHECK_WORDS = 150  # below this the ratio is too noisy to mean anything
SAME_FIELD_MIN_CHARS = 12  # a shorter title or alt (a brand name, "Logo") may rightly be the same in every language
FINDING_EXAMPLES = 5
NUMBER_EXAMPLES = 15

# [heuristic] Rough words per English word in running prose, for the length band only. No published source; the band
# around it is wide on purpose. Languages without spaces between words (zh, ja, th) are not compared.
WORDS_PER_ENGLISH_WORD = {"en": 1.0, "de": 0.95, "nl": 1.0, "fr": 1.15, "es": 1.15, "it": 1.1, "pt": 1.12, "pl": 0.95,
                          "tr": 0.8, "ru": 0.9, "uk": 0.9, "bg": 0.95, "ka": 0.8, "el": 1.05, "hy": 0.9}

SCRIPT_RANGES = (  # (first, last code point, script); only letters (str.isalpha) are counted
    (0x0041, 0x024F, "Latin"), (0x1E00, 0x1EFF, "Latin"),
    (0x0370, 0x03FF, "Greek"), (0x1F00, 0x1FFF, "Greek"),
    (0x0400, 0x052F, "Cyrillic"),
    (0x0530, 0x058F, "Armenian"),
    (0x0590, 0x05FF, "Hebrew"),
    (0x0600, 0x06FF, "Arabic"), (0x0750, 0x077F, "Arabic"),
    (0x0900, 0x097F, "Devanagari"), (0x0980, 0x09FF, "Bengali"), (0x0A80, 0x0AFF, "Gujarati"),
    (0x0B80, 0x0BFF, "Tamil"), (0x0C00, 0x0C7F, "Telugu"), (0x0C80, 0x0CFF, "Kannada"), (0x0D00, 0x0D7F, "Malayalam"),
    (0x0E00, 0x0E7F, "Thai"),
    (0x10A0, 0x10FF, "Georgian"),  # Asomtavruli and Mkhedruli (everyday Georgian is Mkhedruli, U+10D0-U+10FA)
    (0x1C90, 0x1CBF, "Georgian"),  # Mtavruli capitals (Unicode 11): ALL-CAPS only, e.g. what str.upper() makes of Mkhedruli
    (0x2D00, 0x2D2F, "Georgian"),  # Nuskhuri
    (0x3040, 0x30FF, "Kana"), (0x3400, 0x4DBF, "Han"), (0x4E00, 0x9FFF, "Han"),
    (0x1100, 0x11FF, "Hangul"), (0xAC00, 0xD7AF, "Hangul"),
)
PROFILED_SCRIPTS = {"Latin": ("en", "de", "fr", "es", "it", "pt", "nl", "pl", "tr"), "Cyrillic": ("ru", "uk", "bg")}
PROFILED_LANGUAGES = {lang for langs in PROFILED_SCRIPTS.values() for lang in langs}
SCRIPT_LANGUAGES = {"Georgian": ("ka",), "Armenian": ("hy",), "Greek": ("el",), "Hebrew": ("he", "yi"),
                    "Arabic": ("ar", "fa", "ur"), "Devanagari": ("hi", "mr", "ne"), "Bengali": ("bn", "as"),
                    "Gujarati": ("gu",), "Tamil": ("ta",), "Telugu": ("te",), "Kannada": ("kn",), "Malayalam": ("ml",),
                    "Thai": ("th",), "Kana": ("ja",), "Han": ("zh", "ja"), "Hangul": ("ko",)}
# Languages written in one non-Latin script, so a title or description without a single letter of it is untranslated
# or transliterated. Japanese is left out: a title can be all Han characters.
LANGUAGE_SCRIPT = {"ka": "Georgian", "hy": "Armenian", "el": "Greek", "he": "Hebrew", "ar": "Arabic", "fa": "Arabic",
                   "ur": "Arabic", "hi": "Devanagari", "mr": "Devanagari", "ne": "Devanagari", "bn": "Bengali",
                   "gu": "Gujarati", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "th": "Thai",
                   "ko": "Hangul", "ru": "Cyrillic", "uk": "Cyrillic", "bg": "Cyrillic", "mk": "Cyrillic",
                   "be": "Cyrillic", "kk": "Cyrillic", "ky": "Cyrillic", "mn": "Cyrillic", "tg": "Cyrillic", "tt": "Cyrillic"}
TWO_SCRIPT_LANGUAGES = {"sr": ("Cyrillic", "Latin")}  # Serbian is written in both, so neither script is wrong for it

# High-frequency function words. A text's language is the profile with the largest share of its words.
STOPWORDS = {lang: set(words.split()) for lang, words in {
    "en": "the a i and of to in is that for it with as was on are be this by at or from but not have an they which you were "
          "has their we can will more if also been there its would about into than these when what how our your should do",
    "de": "der die und in den von zu das mit sich des auf für ist im dem nicht ein eine als auch es an werden aus er hat "
          "dass sie nach wird bei einer um am sind noch wie einem über einen so zum war haben nur oder aber vor zur bis "
          "mehr durch man kann ich wir ihr wenn",
    "fr": "le la les de des et un une du en est que qui dans pour pas sur au par plus ne se ce il elle avec sont ou mais "
          "son sa ses aux nous vous leur été cette comme être fait tout aussi peut très sans entre donc l d qu",
    "es": "el la los las de del y a en que un una es por con para se no al lo su sus como más pero o este esta son ha "
          "también entre cuando muy sin sobre ya hay puede todo porque desde está fue ser han",
    "it": "il lo la i gli le di a del della dei e è che un una per in con non si da al alla sono come più ma anche nel "
          "nella questo questa ha essere tra fra se suo sua loro molto quando tutto così delle degli l",
    "pt": "o a os as de do da dos das e em no na nos nas um uma que é para com não por se mais como mas ao à seu sua "
          "ou são também foi pelo pela ser está muito quando isso este esta já entre sobre você",
    "nl": "de het een en van in is dat op te voor met zijn niet aan er ook als bij door maar om of wordt dan uit naar "
          "nog wel kan hij ze we je deze die dit worden hebben heeft meer geen over tot zo",
    "pl": "i w na z się nie do to że jest o jak a od po co za ale przez dla tak jego czy są już oraz może tym być "
          "który która które ich jej tylko bardzo przy także więc gdy gdzie było będzie ten ta",
    "tr": "ve bir bu da de için ile olarak çok daha en gibi ama ne o olan kadar sonra her ya veya değil var yok mi mı "
          "şu ki ise göre diye ancak hem nasıl neden tüm bazı olduğu oldu ilk",
    "ru": "и в не на что с по как это а к для из но о от то он же за у так все его она они мы вы бы если или только "
          "уже при был была были быть есть этот эта этого также может чтобы более очень когда где нет ещё еще их её",
    "uk": "і в у не на що з із по як це а до для від але про та й він вона вони ми ви б якщо або тільки вже при був "
          "була були бути є цей ця також може щоб більш дуже коли де немає ще їх її його який яка які",
    "bg": "и в на да се не за с от е са по че като но това той тя те ние вие към при или ако само вече беше бъде има "
          "няма този тази също може много когато където още тях който която които след през до във",
}.items()}
LETTER_CUES = {  # letters frequent in one language of a script and rare in the others
    "ru": "ыэё", "uk": "іїєґ", "bg": "ъ", "de": "äöüß", "fr": "èêëîïœûù", "es": "ñ¿¡", "pt": "ãõ", "it": "ìò",
    "pl": "ąćęłńśźż", "tr": "ğşı",
}
LETTER_ABSENT = {"ru": "іїєґ", "uk": "ыэёъ", "bg": "ыэёіїєґ"}  # letters a language does not have at all
CUE_WEIGHT, CUE_BONUS_MAX, ABSENT_SHARE, ABSENT_PENALTY = 3.0, 0.15, 0.002, 0.3

WORD_RE = re.compile(r"[^\W\d_]+")
# Single letters joined by . - or / (E-E-A-T, A/B, e.g., U.S.): not words, but they would score as the one-letter
# stopwords of other languages (Portuguese a, e, o; Italian e, i).
LETTER_SEQUENCE_RE = re.compile(r"(?<!\w)(?:[^\W\d_][./-])+[^\W\d_](?!\w)")
INVISIBLE_CHARS_RE = re.compile("[\u00ad\u200b\u200c\u2060\ufeff]")  # soft hyphen and zero-width characters
DATE_RE = re.compile(r"(?<![\d.,/-])(\d{1,4})([./-])(\d{1,2})\2(\d{1,4})(?!\d)")
NUMBER_RE = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:[ \u00a0\u202f\u2009'’.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?!\d)")
ROMAN_RE = re.compile(r"(?<!\w)[IVX]{2,6}(?!\w)")  # centuries: Georgian and Russian write "XIV" where English writes "14th"
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}
ASSET_PATH = re.compile(r"\.(?:pdf|jpe?g|png|gif|webp|avif|svg|mp4|zip|css|js|xml)$", re.I)


# ---------------------------------------------------------------- language detection

@dataclass
class Detection:
    lang: str | None  # ISO 639-1 code, or None when the text is too short or matches no profile
    confidence: float  # stopword share (+ letter cues) for profiled scripts, script share for the others
    script: str | None


def script_of(ch: str) -> str | None:
    code = ord(ch)
    for first, last, script in SCRIPT_RANGES:
        if first <= code <= last:
            return script
    return None


def letter_scripts(text: str) -> Counter:
    return Counter(script for script in (script_of(ch) for ch in text if ch.isalpha()) if script)


def language_scripts(lang: str) -> tuple[str, ...]:
    """Scripts `lang` is written in; a language in neither map is taken to be written in Latin."""
    return TWO_SCRIPT_LANGUAGES.get(lang) or (LANGUAGE_SCRIPT.get(lang, "Latin"),)


def _profile_scores(text: str, candidates: tuple[str, ...]) -> dict[str, float]:
    tokens = [t.lower() for t in WORD_RE.findall(LETTER_SEQUENCE_RE.sub(" ", text))]
    letters = [ch for ch in text.lower() if ch.isalpha()]
    scores = {}
    for lang in candidates:
        score = sum(1 for t in tokens if t in STOPWORDS[lang]) / (len(tokens) or 1)  # no tokens: text was all E-E-A-T
        cue_share = sum(1 for ch in letters if ch in LETTER_CUES.get(lang, "")) / len(letters)
        score += min(CUE_BONUS_MAX, CUE_WEIGHT * cue_share)
        if sum(1 for ch in letters if ch in LETTER_ABSENT.get(lang, "")) / len(letters) > ABSENT_SHARE:
            score -= ABSENT_PENALTY
        scores[lang] = score
    return scores


def detect_language(text: str, expected: str | None = None) -> Detection:
    """Language of `text` from its letters. `expected`, the page's own language, wins ties and near-ties with other
    profiles, and breaks ties among languages that share an unprofiled script (Devanagari for hi/mr/ne, Arabic for
    ar/fa/ur, Han for zh/ja). When `expected` is written in a non-Latin script, mostly Latin text with at least
    OWN_SCRIPT_MIN_SHARE of its letters in that script is judged in that script (a Russian sentence quoting English UI
    labels); text mostly in any other script is judged in its own."""
    scripts = letter_scripts(text)
    total = sum(scripts.values())
    if total < MIN_DETECT_LETTERS:
        return Detection(None, 0.0, None)
    script, count = scripts.most_common(1)[0]
    if expected and script == "Latin":
        own_script = max(language_scripts(expected), key=lambda s: scripts[s])
        if own_script != "Latin" and scripts[own_script] >= OWN_SCRIPT_MIN_SHARE * total:
            script, count = own_script, scripts[own_script]
    if script in PROFILED_SCRIPTS:
        script_text = "".join(ch if script_of(ch) in (script, None) else " " for ch in text)
        scores = _profile_scores(script_text, PROFILED_SCRIPTS[script])
        lang = max(scores, key=scores.get)
        if expected in scores and scores[lang] - scores[expected] < EXPECTED_LANGUAGE_MARGIN:
            lang = expected
        return Detection(lang if scores[lang] > 0 else None, round(max(scores[lang], 0.0), 3), script)
    languages = SCRIPT_LANGUAGES.get(script, ())
    if not languages:
        return Detection(None, 0.0, script)
    return Detection(expected if expected in languages else languages[0], round(count / total, 3), script)


def is_other_language(detection: Detection, expected: str) -> bool:
    """True when `detection` confidently names a language other than `expected`."""
    if not (detection.lang and expected and detection.lang != expected):
        return False
    same_script_unprofiled = expected not in PROFILED_LANGUAGES and detection.script in language_scripts(expected)
    return detection.confidence >= (UNPROFILED_CONFIDENCE if same_script_unprofiled else DETECT_CONFIDENCE)


def primary_subtag(code: str) -> str:
    return re.split(r"[-_]", code.strip().lower(), maxsplit=1)[0] if code else ""


def code_problem(code: str, detected: str | None) -> str | None:
    """Why an hreflang code is wrong for a page detected as `detected`, or None when it is fine."""
    language = primary_subtag(code)
    if not language or code.lower() == "x-default":
        return None
    fix = COMMON_CODE_MISTAKES.get(language)
    if language not in ISO_639_1:
        return f"'{code}' is not an ISO 639-1 language code" + (f"; use '{fix}'" if fix else "")
    if fix and detected == fix:
        return f"'{code}' is a country code here: the page reads as '{fix}', so use '{fix}'"
    return None


# ---------------------------------------------------------------- main content

_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "pre", "code", "button", "select", "textarea", "iframe", "object",
              "audio", "video", "canvas"}  # their text is fallback for old browsers, not content
_BLOCK_KINDS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "td", "th", "figcaption", "dt", "dd",
                "caption", "summary"}
_BOUNDARY_TAGS = _BLOCK_KINDS | {"div", "section", "article", "main", "header", "footer", "aside", "nav", "body", "ul",
                                 "ol", "table", "tr", "figure", "form", "details", "hr"}


@dataclass
class Block:
    kind: str  # p, li, h1..h6, td, blockquote, ...; "div" for text outside those
    text: str
    links: list[str] = field(default_factory=list)  # absolute hrefs of the links inside the block

    @property
    def words(self) -> int:
        return len(WORD_RE.findall(self.text))


@dataclass
class MainContent:
    blocks: list[Block]
    images: list[dict[str, str]]  # {"src", "alt"}
    links: list[dict[str, str]]  # {"href", "text"}
    lists: int
    tables: int

    @property
    def text(self) -> str:
        return " ".join(b.text for b in self.blocks)

    @property
    def words(self) -> int:
        return sum(b.words for b in self.blocks)

    @property
    def headings(self) -> list[Block]:
        return [b for b in self.blocks if re.fullmatch(r"h[1-6]", b.kind)]

    @property
    def prose(self) -> str:
        """Text of the blocks long enough to judge, so menus, reference lists and captions don't dilute detection."""
        return " ".join(b.text for b in self.blocks if b.words >= MIN_BLOCK_WORDS) or self.text


@dataclass
class _Region:
    article: int | None  # which top-level <article> the item is in
    in_main: bool
    in_chrome: bool  # nav, aside, form, or a header/footer that is not inside an article or main


class _ContentParser(HTMLParser):
    """Records every text block, image, link, list and table with the region it sits in, so main_content() can keep
    the post body and drop navigation."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.items: list[tuple[str, _Region, object]] = []  # (kind, region, payload)
        self._has_base = False
        self._stack: list[str] = []
        self._article: int | None = None
        self._articles = 0
        self._skip = 0
        self._buffer: list[str] = []
        self._buffer_links: list[str] = []
        self._anchor: dict[str, str] | None = None
        self._anchor_text: list[str] = []

    def _region(self) -> _Region:
        chrome = in_content = False
        for tag in self._stack:
            if tag in ("article", "main"):
                in_content = True
            elif tag in ("nav", "aside", "form") or (tag in ("header", "footer") and not in_content):
                chrome = True
        return _Region(self._article, "main" in self._stack, chrome)

    def _flush(self) -> None:
        # Hyphenation plugins put soft hyphens inside words (qual\u00adité), which would split them into stopword fragments.
        text = re.sub(r"\s+", " ", INVISIBLE_CHARS_RE.sub("", "".join(self._buffer))).strip()
        if text:
            kind = next((t for t in reversed(self._stack) if t in _BLOCK_KINDS), "div")
            self.items.append(("block", self._region(), Block(kind, text, self._buffer_links)))
        self._buffer, self._buffer_links = [], []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if self._skip:
            if tag in _SKIP_TAGS:
                self._skip += 1
            return
        if tag == "base" and a.get("href") and not self._has_base:  # only the first <base href> counts
            self.base_url, self._has_base = urllib.parse.urljoin(self.base_url, a["href"]), True
        if tag in _BOUNDARY_TAGS:
            self._flush()
        if tag in _SKIP_TAGS:
            self._skip = 1
            return
        href = a.get("href", "").strip()
        if tag == "img":
            self.items.append(("image", self._region(), {"src": a.get("src", ""), "alt": a.get("alt", "").strip()}))
        elif tag == "a" and href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
            self._anchor, self._anchor_text = {"href": normalize_url(urllib.parse.urljoin(self.base_url, href))}, []
            self._buffer_links.append(self._anchor["href"])
        elif tag in ("ul", "ol"):
            self.items.append(("list", self._region(), None))
        elif tag == "table":
            self.items.append(("table", self._region(), None))
        if tag in _VOID_TAGS:
            return
        if tag == "article" and self._article is None:
            self._articles += 1
            self._article = self._articles
        self._stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self._skip:
            if tag in _SKIP_TAGS:
                self._skip -= 1
            return
        if tag == "a" and self._anchor is not None:
            text = re.sub(r"\s+", " ", "".join(self._anchor_text)).strip()
            self.items.append(("link", self._region(), {**self._anchor, "text": text}))
            self._anchor = None
        if tag in _BOUNDARY_TAGS:
            self._flush()
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass
            if "article" not in self._stack:
                self._article = None

    def handle_data(self, data):
        if self._skip:
            return
        self._buffer.append(data)
        if self._anchor is not None:
            self._anchor_text.append(data)

    def close(self):
        super().close()
        self._flush()


def main_content(page_html: str, base_url: str) -> MainContent:
    """The post body: the largest <article>, else <main>, else everything outside the page chrome."""
    parser = _ContentParser(base_url)
    parser.feed(page_html)
    parser.close()
    items = parser.items
    article_words: Counter = Counter()
    for kind, region, payload in items:
        if kind == "block" and region.article is not None:
            article_words[region.article] += payload.words
    page_words = sum(p.words for kind, region, p in items if kind == "block" and not region.in_chrome)
    if article_words and article_words.most_common(1)[0][1] >= ARTICLE_MIN_SHARE * page_words:
        best = article_words.most_common(1)[0][0]
        keep = [item for item in items if item[1].article == best]
    elif any(region.in_main for _, region, _ in items):
        keep = [item for item in items if item[1].in_main]
    else:
        keep = [item for item in items if not item[1].in_chrome]
    return MainContent(
        blocks=[p for kind, _, p in keep if kind == "block"],
        images=[p for kind, _, p in keep if kind == "image"],
        links=[p for kind, _, p in keep if kind == "link"],
        lists=sum(1 for kind, _, _ in keep if kind == "list"),
        tables=sum(1 for kind, _, _ in keep if kind == "table"),
    )


# ---------------------------------------------------------------- Markdown drafts

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
_FRONT_MATTER_KEYS = {"title": "title", "description": "description", "lang": "lang", "language": "lang",
                      "locale": "lang", "canonical": "canonical", "canonical_url": "canonical", "canonicalurl": "canonical"}
_MD_LINK_OR_IMAGE = re.compile(r"(!?)\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^)]*[\"'])?\s*\)")
_MD_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)")
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_MD_GROUPED = ("p", "ul", "ol", "blockquote", "table")  # consecutive lines of these kinds form one block


def _md_emphasis(text: str) -> str:
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])|(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)",
                  lambda m: m.group(1) or m.group(2), text)


def _md_inline(text: str) -> str:
    out = []
    for i, part in enumerate(re.split(r"(`[^`]+`)", text)):
        if i % 2:  # inline code
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        pos = 0
        for m in _MD_LINK_OR_IMAGE.finditer(part):
            out.append(_md_emphasis(html.escape(part[pos:m.start()])))
            bang, label, target = m.groups()
            if bang:
                out.append(f'<img alt="{html.escape(label)}" src="{html.escape(target)}">')
            else:
                out.append(f'<a href="{html.escape(target)}">{_md_emphasis(html.escape(label))}</a>')
            pos = m.end()
        out.append(_md_emphasis(html.escape(part[pos:])))
    return "".join(out)


def _md_render(kind: str, lines: list[str]) -> str:
    if kind in ("ul", "ol"):
        return f"<{kind}>" + "".join(f"<li>{_md_inline(line)}</li>" for line in lines) + f"</{kind}>"
    if kind == "table":
        return "<table>" + "".join("<tr>" + "".join(f"<td>{_md_inline(cell.strip())}</td>" for cell in row.strip("|").split("|"))
                                   + "</tr>" for row in lines) + "</table>"
    if kind == "blockquote":
        return f"<blockquote><p>{_md_inline(' '.join(lines))}</p></blockquote>"
    if kind == "pre":
        return "<pre></pre>"  # code is not prose: nothing to translate or compare
    if kind == "hr":
        return "<hr>"
    return f"<{kind}>{_md_inline(' '.join(lines))}</{kind}>"  # p, h1..h6


def markdown_to_html(text: str) -> str:
    """A Markdown draft as an HTML page; front matter becomes <title>, meta description, html lang and canonical."""
    meta: dict[str, str] = {}
    front = _FRONT_MATTER.match(text)
    if front:
        for line in front.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip().lower() in _FRONT_MATTER_KEYS:
                meta[_FRONT_MATTER_KEYS[key.strip().lower()]] = value.strip().strip("\"'")
        text = text[front.end():]
    blocks: list[tuple[str, list[str]]] = []
    fence, after_blank = None, False
    for line in text.splitlines():
        stripped = line.strip()
        if fence:
            fence = None if stripped.startswith(fence) else fence
            continue
        if stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
            blocks.append(("pre", []))
            continue
        if not stripped:
            after_blank = True
            continue
        heading, item = _MD_HEADING.match(stripped), _MD_LIST_ITEM.match(line)
        if heading:
            kind, content = f"h{len(heading.group(1))}", heading.group(2)
        elif re.fullmatch(r"(?:[-*_]\s*){3,}", stripped):
            kind, content = "hr", ""
        elif item:
            kind, content = ("ol" if item.group(1)[0].isdigit() else "ul"), item.group(2)
        elif blocks and blocks[-1][0] in ("ul", "ol") and line[:1].isspace():
            blocks[-1][1][-1] += " " + stripped  # an indented continuation of the last list item
            continue
        elif stripped.startswith(">"):
            kind, content = "blockquote", stripped.lstrip(">").strip()
        elif stripped.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):  # the |---|---| separator row
                continue
            kind, content = "table", stripped
        else:
            kind, content = "p", stripped
        joins = (blocks and blocks[-1][0] == kind and kind in _MD_GROUPED
                 and (not after_blank or kind in ("ul", "ol")))  # a blank line between list items keeps the list open
        if joins:
            blocks[-1][1].append(content)
        else:
            blocks.append((kind, [content]))
        after_blank = False
    head = [f"<title>{html.escape(meta.get('title', ''))}</title>"]
    if meta.get("description"):
        head.append(f'<meta name="description" content="{html.escape(meta["description"])}">')
    if meta.get("canonical"):
        head.append(f'<link rel="canonical" href="{html.escape(meta["canonical"])}">')
    return (f'<!doctype html><html lang="{html.escape(meta.get("lang", ""))}"><head><meta charset="utf-8">'
            + "".join(head) + "</head><body><article>" + "".join(_md_render(k, lines) for k, lines in blocks)
            + "</article></body></html>")


def is_markdown_path(path: str) -> bool:
    return path.lower().endswith((".md", ".markdown", ".mdx"))


def load_draft(path: str, url: str, key: str | None = None, fields: list[str] | None = None) -> FetchResult:
    """A local HTML, Markdown or content-file draft as a 200 response for `url` (`key` and `fields` pick a JSON, CSV or
    TSV entry; seo_lib.load_draft_file)."""
    if not is_markdown_path(path):
        return load_draft_file(path, url, key, fields)
    with open(path, encoding="utf-8") as fh:
        return html_draft(url, markdown_to_html(fh.read()))


# ---------------------------------------------------------------- numbers

def number_key(raw: str) -> str:
    """One spelling for a number however a language writes it: 1,250 = 1 250 = 1.250 = 1250; 3.5 = 3,5;
    1.250,75 = 1,250.75. A single separator before exactly three digits is read as grouping in every language, so an
    ambiguous value is at least read the same way in every version."""
    raw = re.sub(r"[\s\u00a0\u202f\u2009'’]", "", raw)
    marks = re.findall(r"[.,]", raw)
    if not marks:
        return str(int(raw))
    last = max(raw.rfind("."), raw.rfind(","))
    whole, fraction = raw[:last], raw[last + 1:]
    if len(set(marks)) > 1 or (len(marks) == 1 and len(fraction) != 3):
        fraction = fraction.rstrip("0")
        return str(int(re.sub(r"[.,]", "", whole) or "0")) + (f".{fraction}" if fraction else "")
    return str(int(re.sub(r"[.,]", "", raw)))


def roman_value(numeral: str) -> int | None:
    """Value of an upper-case Roman numeral made of I, V and X, or None when it is not a well-formed one."""
    total = 0
    for ch, nxt in zip(numeral, numeral[1:] + " "):
        value = ROMAN_VALUES[ch]
        total += -value if ROMAN_VALUES.get(nxt, 0) > value else value
    return total if _to_roman(total) == numeral else None


def _to_roman(value: int) -> str:
    out = ""
    for number, letters in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while value >= number:
            out, value = out + letters, value - number
    return out


def numbers_in(text: str) -> set[str]:
    """Numbers worth comparing across translations. Dates are split into parts and Roman numerals (XIV) read as
    numbers; integers up to 9 and date parts up to 12 (often written as words or month names) are left out."""
    found = {str(v) for v in (roman_value(m.group(0)) for m in ROMAN_RE.finditer(text)) if v and v > SMALL_NUMBER_MAX}
    for m in DATE_RE.finditer(text):
        found |= {str(int(part)) for part in (m.group(1), m.group(3), m.group(4)) if int(part) > DATE_PART_MAX}
    for m in NUMBER_RE.finditer(DATE_RE.sub(" ", text)):
        key = number_key(m.group(0))
        if "." in key or int(key) > SMALL_NUMBER_MAX:
            found.add(key)
    return found


# ---------------------------------------------------------------- cluster

@dataclass
class Version:
    code: str  # hreflang code this version is listed under ("" when only listed as x-default, or not listed)
    url: str  # URL as requested or listed
    result: FetchResult
    facts: PageFacts
    content: MainContent
    detection: Detection
    codes: list[str] = field(default_factory=list)  # every code any version lists this URL under

    @property
    def ok(self) -> bool:
        return self.facts.status == 200

    @property
    def fallback_only(self) -> bool:
        """Listed only as x-default (typically a language picker): not a translation to compare."""
        return not self.code and any(c.lower() == "x-default" for c in self.codes)

    @property
    def expected_language(self) -> str:
        return primary_subtag(self.code) or primary_subtag(self.facts.lang)

    @property
    def urls(self) -> set[str]:
        return {url_key(self.url), url_key(self.facts.final_url)}


def url_key(url: str) -> str:
    return normalize_url(url).rstrip("/") if url else ""


def detect_body_language(v: Version) -> Detection:
    return detect_language(v.content.prose, v.expected_language)


def load_version(code: str, url: str, result: FetchResult) -> Version:
    facts = extract_page(result)
    content = main_content(result.text, result.final_url) if facts.status == 200 else MainContent([], [], [], 0, 0)
    version = Version(code, url, result, facts, content, Detection(None, 0.0, None), [code] if code else [])
    version.detection = detect_body_language(version)
    return version


def discover_cluster(start_url: str, limit: int = MAX_VERSIONS) -> tuple[list[Version], bool]:
    """Fetch the start page and, breadth-first, every hreflang alternate any fetched version lists, up to `limit`.
    Returns the versions and whether alternates were left unfetched. Each version gets the code it is listed under
    most often."""
    queue, seen, versions = [start_url], {url_key(start_url)}, []
    listed: dict[str, Counter] = {}
    while queue and len(versions) < limit:
        url = queue.pop(0)
        if versions:
            time.sleep(FETCH_DELAY_S)
        version = load_version("", url, fetch(url))
        versions.append(version)
        seen.add(url_key(version.facts.final_url))  # a redirect target that hreflang lists is this version, not a new one
        for alt in version.facts.hreflang:
            key = url_key(alt["href"])
            listed.setdefault(key, Counter())[alt["hreflang"]] += 1
            if key not in seen:
                seen.add(key)
                queue.append(alt["href"])
    for version in versions:
        codes = sum((listed.get(key, Counter()) for key in version.urls), Counter())
        version.codes = [c for c, _ in codes.most_common()]
        version.code = next((c for c in version.codes if c.lower() != "x-default"), "")
        version.detection = detect_body_language(version)  # the expected language is known only now
    return versions, bool(queue)


def _label(v: Version) -> str:
    return f"{v.code or v.expected_language or '?'} {v.facts.final_url}"


def _clip(text: str, limit: int = 120) -> str:
    return text if len(text) <= limit else text[:limit - 1] + "…"


def schema_languages(facts: PageFacts) -> list[str]:
    values = []
    for _, node in iter_typed_nodes(facts.json_ld):
        raw = node.get("inLanguage")
        for value in raw if isinstance(raw, list) else [raw]:
            if isinstance(value, dict):
                value = value.get("alternateName") or value.get("name")
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
    return values


@dataclass
class LanguageMix:
    """How the version's judgeable blocks (MIN_BLOCK_WORDS or more) split between its own and other languages."""
    foreign: list[tuple[Block, Detection]]  # blocks that confidently read as another language
    own_share: float  # share of judged words in the version's own language
    foreign_share: float  # share of judged words in other languages


def language_mix(v: Version) -> LanguageMix:
    judged = [(b, detect_language(b.text, v.expected_language)) for b in v.content.blocks if b.words >= MIN_BLOCK_WORDS]
    total = sum(b.words for b, _ in judged) or 1
    foreign = [(b, d) for b, d in judged if is_other_language(d, v.expected_language)]
    own = sum(b.words for b, d in judged if d.lang == v.expected_language)
    return LanguageMix(foreign, round(own / total, 3), round(sum(b.words for b, _ in foreign) / total, 3))


def pick_source(versions: list[Version], source_code: str | None) -> Version:
    candidates = [v for v in versions if v.ok and not v.fallback_only] or [v for v in versions if v.ok]
    if source_code:
        for v in candidates:
            if v.code.lower() == source_code.lower() or v.expected_language == primary_subtag(source_code):
                return v
        raise ValueError(f"no reachable version has the code {source_code!r}")
    for v in candidates:
        for alt in v.facts.hreflang:
            if alt["hreflang"].lower() == "x-default":
                target = next((w for w in candidates if url_key(alt["href"]) in w.urls), None)
                if target:
                    return target
    return max(candidates, key=lambda v: v.content.words)


def _reachability_checks(versions: list[Version]) -> list[Finding]:
    """A language version must be the final, 200, indexable URL. A redirect is an hreflang error only when some
    version's hreflang lists the redirecting URL; a URL given on the command line may redirect."""
    out = []
    add = lambda *args: out.append(Finding(*args))
    listed = {url_key(a["href"]) for v in versions for a in v.facts.hreflang}
    for v in versions:
        chain = " -> ".join(f"{u} [{s}]" for u, s in v.result.redirect_chain)
        redirect_listed = bool(v.result.redirect_chain) and url_key(v.url) in listed
        if v.facts.status is None:
            add("translation-version-error", "high", f"Language version {_label(v)} could not be fetched", v.result.error)
        elif v.facts.status != 200:
            add("translation-version-error", "high", f"Language version {_label(v)} answers HTTP {v.facts.status}", v.url)
        elif redirect_listed:
            add("translation-version-error", "medium", f"{v.url} redirects to {v.facts.final_url}; list the final URL in hreflang",
                chain)
        elif not is_indexable(v.facts):
            add("translation-version-noindex", "medium",
                f"{_label(v)} is noindex but is a language version: finish its review and index it, or drop it from every "
                "version's hreflang set", f"meta='{v.facts.meta_robots}' header='{v.facts.x_robots_tag}'")
        if v.ok and v.result.redirect_chain and not redirect_listed:
            add("translation-input-redirect", "info", f"{v.url} redirects to {v.facts.final_url}; checked the final URL", chain)
    return out


def _language_checks(v: Version, versions: list[Version], source: Version) -> list[Finding]:
    """The body really is in the declared language (Google reads the visible text, not lang or hreflang), and the
    lang attribute, og:locale, schema inLanguage and canonical agree with it."""
    out = []
    add = lambda *args: out.append(Finding(*args))
    expected, detected = v.expected_language, v.detection.lang
    problem = code_problem(v.code, detected)
    mix = language_mix(v)
    wrong_script = bool(detected and expected and detected != expected and v.detection.script not in language_scripts(expected))
    mismatch = is_other_language(v.detection, expected) or wrong_script
    examples = " | ".join(_clip(b.text, 80) for b, _ in mix.foreign[:FINDING_EXAMPLES])
    langs = sorted({d.lang for _, d in mix.foreign})
    if problem:
        add("translation-hreflang-wrong-code", "high", f"hreflang code for {v.facts.final_url}: {problem}")
    elif mismatch and mix.own_share < SIDE_BY_SIDE_SHARE:
        untranslated = detected == source.detection.lang and v is not source
        # Below DETECT_CONFIDENCE the profile is a guess: only the script is evidence (a Georgian page in Latin letters).
        reads = f"reads as '{detected}'" if v.detection.confidence >= DETECT_CONFIDENCE else f"is in {v.detection.script} script"
        add("translation-body-language-mismatch", "critical" if untranslated else "high",
            f"{_label(v)} is declared '{expected}' but its main text {reads}"
            + ("; the body was left untranslated, so Google treats the page as a duplicate of the source" if untranslated else ""),
            _clip(v.content.text))
    elif mix.foreign and (mismatch or mix.foreign_share >= SIDE_BY_SIDE_SHARE):
        add("translation-side-by-side", "high",
            f"{mix.foreign_share:.0%} of the main text on {_label(v)} is in {langs}, {mix.own_share:.0%} in '{expected}': a "
            "side-by-side or half-finished translation (Google advises one language per page)", examples)
    elif mix.foreign:
        add("translation-untranslated-block", "medium",
            f"{len(mix.foreign)} block(s) on {_label(v)} are in {langs}, not '{expected}' (translate them unless quoted on "
            "purpose)", examples)
    if v.facts.lang and v.code and primary_subtag(v.facts.lang) != primary_subtag(v.code):
        add("translation-html-lang-mismatch", "low",
            f"<html lang='{v.facts.lang}'> on the version listed as '{v.code}' (Google ignores lang; screen readers and "
            "browser translation use it)", v.facts.final_url)
    og_locale = v.facts.open_graph.get("og:locale", "")
    if og_locale and expected and primary_subtag(og_locale) != expected:
        add("translation-og-locale-mismatch", "low", f"og:locale '{og_locale}' on the '{expected}' version {v.facts.final_url}")
    wrong_schema = [code for code in schema_languages(v.facts) if expected and primary_subtag(code) != expected]
    if wrong_schema:
        add("translation-schema-language-mismatch", "medium",
            f"Structured data inLanguage {wrong_schema} on the '{expected}' version (copied from another language?)",
            v.facts.final_url)
    canonical = url_key(v.facts.canonical)
    if canonical and canonical not in v.urls:
        target = next((w for w in versions if w is not v and canonical in w.urls), None)
        if target:
            add("translation-canonical-cross-language", "high",
                f"{_label(v)} canonicalises to the '{target.code or target.expected_language}' version, which drops it "
                "from the index; point each language's canonical at itself", v.facts.canonical)
        else:
            add("translation-canonical-not-self", "medium", f"{_label(v)} canonicalises to a URL outside the language cluster",
                v.facts.canonical)
    return out


def _same_text(a: str, b: str) -> bool:
    a, b = re.sub(r"\s+", " ", a).strip().casefold(), re.sub(r"\s+", " ", b).strip().casefold()
    return len(a) >= SAME_FIELD_MIN_CHARS and a == b


def _first_h1(v: Version) -> str:
    return next((t for level, t in v.facts.headings if level == 1), "")


METADATA_FIELDS = {"title": lambda v: v.facts.title, "meta description": lambda v: v.facts.meta_description, "h1": _first_h1}


def _metadata_checks(versions: list[Version], source: Version) -> list[Finding]:
    """Title, meta description, H1 and image alt text are translated (Google names these in its review advice for
    AI-generated content)."""
    out = []
    for v in versions:
        if v is source or not v.expected_language:
            continue
        problems = []
        others = [w for w in versions if w is not v and w.expected_language != v.expected_language]
        for name, get in METADATA_FIELDS.items():
            value = get(v)
            same_as = [w.code or w.expected_language for w in others if _same_text(value, get(w))]
            scripts = letter_scripts(value)
            script = LANGUAGE_SCRIPT.get(v.expected_language)
            found = detect_language(value, v.expected_language)
            if same_as:
                problems.append(f"{name} identical to {same_as}: '{_clip(value, 80)}'")
            elif script and len(value) >= SAME_FIELD_MIN_CHARS and scripts and not scripts[script]:
                problems.append(f"{name} has no {script} letters: '{_clip(value, 80)}' (Google wants the page's language "
                                "and script in titles, not English or Latin transliteration)")
            elif len(WORD_RE.findall(value)) >= MIN_BLOCK_WORDS and is_other_language(found, v.expected_language):
                problems.append(f"{name} reads as '{found.lang}': '{_clip(value, 80)}'")
        other_alts = {a["alt"].casefold() for w in others for a in w.content.images}
        same_alts = [a["alt"] for a in v.content.images if len(a["alt"]) >= SAME_FIELD_MIN_CHARS and a["alt"].casefold() in other_alts]
        if same_alts:
            problems.append(f"{len(same_alts)} image alt text(s) identical to another language: '{_clip(same_alts[0], 60)}'")
        if problems:
            out.append(Finding("translation-metadata-not-translated", "medium",
                               f"Untranslated metadata on {_label(v)}: {len(problems)} field(s)", " | ".join(problems)))
    return out


def _counts(v: Version) -> dict[str, int]:
    return {"headings": sum(1 for b in v.content.headings if b.kind != "h1"), "images": len(v.content.images),
            "tables": v.content.tables, "lists": v.content.lists, "links": len(v.content.links)}


def _parity_checks(versions: list[Version], source: Version) -> list[Finding]:
    """[heuristic] A translation keeps the source's length, sections, media and facts."""
    out = []
    add = lambda *args: out.append(Finding(*args))
    source_numbers, source_counts = numbers_in(source.content.text), _counts(source)
    src = source.code or source.expected_language
    src_lang = source.detection.lang or source.expected_language
    for v in versions:
        if v is source:
            continue
        lang = v.detection.lang or v.expected_language
        if lang in WORDS_PER_ENGLISH_WORD and src_lang in WORDS_PER_ENGLISH_WORD and source.content.words >= MIN_LENGTH_CHECK_WORDS:
            expected = source.content.words * WORDS_PER_ENGLISH_WORD[lang] / WORDS_PER_ENGLISH_WORD[src_lang]
            ratio = v.content.words / expected
            if not LENGTH_BAND[0] <= ratio <= LENGTH_BAND[1]:
                add("translation-length-outlier", "medium",
                    f"[heuristic] {_label(v)} has {v.content.words} words where about {round(expected)} are expected from "
                    f"the {src} source ({ratio:.2f}x): "
                    + ("text may be missing, or the model's output was cut off" if ratio < 1 else "text may have been added"),
                    f"band {LENGTH_BAND[0]}-{LENGTH_BAND[1]}x of a rough words-per-English-word factor")
        counts = _counts(v)
        diffs = {k: (source_counts[k], counts[k]) for k in counts if counts[k] != source_counts[k]}
        if diffs:
            severe = any(k in diffs for k in ("headings", "images", "tables"))
            add("translation-structure-mismatch", "medium" if severe else "low",
                f"[heuristic] {_label(v)} differs in structure from the {src} source",
                "; ".join(f"{k}: source {a}, this {b}" for k, (a, b) in diffs.items()))
        numbers = numbers_in(v.content.text)
        missing, added = sorted(source_numbers - numbers, key=float), sorted(numbers - source_numbers, key=float)
        if missing:
            add("translation-number-missing", "high",
                f"[heuristic] {len(missing)} number(s) in the {src} source are not in {_label(v)}: a dropped fact, or a "
                "number written out in words or converted (units, currency); check each one", ", ".join(missing[:NUMBER_EXAMPLES]))
        if added:
            add("translation-number-added", "high",
                f"[heuristic] {len(added)} number(s) in {_label(v)} are not in the {src} source: an invented fact, or a "
                "localised conversion; check each one", ", ".join(added[:NUMBER_EXAMPLES]))
    return out


def _language_marker(v: Version, codes: set[str]) -> tuple[str, str] | None:
    """('path', 'ka') when the version lives under /ka/, ('host', 'ka') on ka.example.com, else None."""
    parts = urllib.parse.urlsplit(v.facts.final_url)
    first = parts.path.strip("/").split("/")[0].lower()
    label = (parts.hostname or "").split(".")[0].lower()
    if first in codes:
        return "path", first
    if label in codes:
        return "host", label
    return None


def _link_language_checks(versions: list[Version]) -> list[Finding]:
    """[heuristic] Internal links in the post body stay in the post's language section."""
    out = []
    codes = {c.lower() for v in versions for c in (v.code, v.expected_language) if c}
    root_language = any(_language_marker(v, codes) is None for v in versions)  # e.g. English at /, others under /ka/
    for v in versions:
        marker = _language_marker(v, codes)
        if not marker:
            continue
        kind, own = marker
        leaving = []
        for link in v.content.links:
            parts = urllib.parse.urlsplit(link["href"])
            if not same_site(link["href"], v.facts.final_url) or ASSET_PATH.search(parts.path):
                continue
            target = (parts.path.strip("/").split("/")[0] if kind == "path" else (parts.hostname or "").split(".")[0]).lower()
            if target in codes and target != own:
                leaving.append(link["href"])
            elif target not in codes and kind == "path" and root_language and parts.path not in ("", "/"):
                leaving.append(link["href"])  # an unprefixed path is the root language's page
        if leaving:
            out.append(Finding("translation-link-leaves-language", "low",
                               f"[heuristic] {len(leaving)} body link(s) on {_label(v)} point outside the '{own}' section "
                               "(link to the same-language page where one exists)", ", ".join(leaving[:FINDING_EXAMPLES])))
    return out


def _hreflang_checks(versions: list[Version]) -> list[Finding]:
    """Every version lists itself and the same set as the others, every pair links both ways, codes are valid."""
    out = []
    add = lambda *args: out.append(Finding(*args))
    entries = {id(v): {(a["hreflang"].lower(), url_key(a["href"])) for a in v.facts.hreflang} for v in versions}
    union = set().union(*entries.values())
    fallbacks = sorted(u for c, u in union if c == "x-default")
    if len(fallbacks) > 1:  # reported once here, not again as an entry each version lacks
        add("translation-hreflang-set-mismatch", "low",
            f"The versions name {len(fallbacks)} different x-default URLs; every version should name the same fallback",
            ", ".join(fallbacks[:FINDING_EXAMPLES]))
    lists = lambda a, b: any(u in b.urls for _, u in entries[id(a)])  # a's hreflang set includes b
    own_codes = {v.code.lower() for v in versions}
    for code in sorted({c for c, _ in union} - own_codes):  # a version's own code was checked with its content
        problem = code_problem(code, None)
        if problem:
            add("translation-hreflang-wrong-code", "high", f"hreflang {problem}",
                ", ".join(sorted(u for c, u in union if c == code)[:FINDING_EXAMPLES]))
    for v in versions:
        if not entries[id(v)]:
            add("translation-hreflang-no-return", "high",
                f"{_label(v)} has no hreflang links at all, so none of its pairs is confirmed and Google ignores them")
            continue
        if not lists(v, v):
            add("translation-hreflang-no-self", "medium", f"{_label(v)} does not list itself in its hreflang set")
        for w in versions:
            if w is not v and entries[id(w)] and lists(v, w) and not lists(w, v):
                add("translation-hreflang-no-return", "high",
                    f"{_label(v)} lists {w.facts.final_url} as an alternate, but that page does not link back (Google "
                    "ignores the pair without return links)", f"add {v.code or '?'} -> {v.facts.final_url} on {w.facts.final_url}")
        # Entries v lacks because it doesn't return w's link were just reported, from w's side, as no-return.
        reported = {e for w in versions if w is not v and lists(w, v) and not lists(v, w) for e in union if e[1] in w.urls}
        missing = union - entries[id(v)] - reported - {e for e in union if e[1] in v.urls}
        if len(fallbacks) > 1:
            missing = {e for e in missing if e[0] != "x-default"}
        if missing:
            add("translation-hreflang-set-mismatch", "low",
                f"{_label(v)}'s hreflang set differs from the other versions' (every version should carry the same set)",
                "missing: " + ", ".join(f"{c} -> {u}" for c, u in sorted(missing)[:FINDING_EXAMPLES]))
    if union and not any(c == "x-default" for c, _ in union):
        add("translation-hreflang-no-x-default", "low",
            "No version declares an x-default alternate (optional: the fallback for searchers whose language has no version)")
    return out


def summarise(v: Version, source: Version | None) -> dict:
    mix = language_mix(v) if v.ok else None
    return {
        "code": v.code, "codes": v.codes, "url": v.url, "final_url": v.facts.final_url, "status": v.facts.status,
        "indexable": v.ok and is_indexable(v.facts), "is_source": v is source, "fallback_only": v.fallback_only,
        "canonical": v.facts.canonical, "self_canonical": url_key(v.facts.canonical) in v.urls if v.facts.canonical else None,
        "html_lang": v.facts.lang, "og_locale": v.facts.open_graph.get("og:locale", ""),
        "schema_in_language": schema_languages(v.facts), "detected_language": v.detection.lang,
        "detection_confidence": v.detection.confidence, "detected_script": v.detection.script,
        "title": v.facts.title, "main_words": v.content.words, "counts": _counts(v), "numbers": len(numbers_in(v.content.text)),
        "other_language_share": mix.foreign_share if mix and v.content.words else None,
        "hreflang": v.facts.hreflang,
    }


def cluster_report(versions: list[Version], source_code: str | None = None, check_hreflang: bool = True,
                   capped: bool = False) -> dict:
    """All cluster checks. `source_code` names the original; `check_hreflang` is off for drafts without hreflang."""
    findings = _reachability_checks(versions)
    if capped:
        findings.append(Finding("translation-cluster-capped", "info",
                                f"Stopped after {MAX_VERSIONS} versions; alternates beyond that were not checked"))
    healthy = [v for v in versions if v.ok]
    if not healthy:
        return {"source": None, "hreflang_checked": False, "cluster": [summarise(v, None) for v in versions],
                "findings": sort_findings(findings)}
    if check_hreflang and not any(v.facts.hreflang for v in healthy):
        findings.append(Finding("translation-no-alternates", "medium",
                                ("This page lists no hreflang alternates, so there is no cluster to follow; pass the "
                                 "versions with --urls" if len(versions) == 1 else "No language version declares hreflang")
                                + ". Add hreflang so Google can show each searcher the version in their language",
                                ", ".join(v.facts.final_url for v in healthy)))
        check_hreflang = False
    source = pick_source(versions, source_code)
    translations = [v for v in healthy if not v.fallback_only]
    for v in translations:
        findings += _language_checks(v, versions, source)
    findings += _metadata_checks(translations, source)
    findings += _parity_checks(translations, source)
    findings += _link_language_checks(translations)
    if check_hreflang:
        findings += _hreflang_checks(healthy)
    return {"source": source.code or source.expected_language, "hreflang_checked": check_hreflang,
            "cluster": [summarise(v, source) for v in versions], "findings": sort_findings(findings)}


def _pairs(values: list[str], option: str, ap: argparse.ArgumentParser) -> list[tuple[str, str]]:
    pairs = []
    for value in values:
        code, sep, target = value.partition(":")
        if not (sep and code and target):
            ap.error(f"{option} expects LANG:VALUE pairs, got {value!r}")
        pairs.append((code, target))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="a post URL; its hreflang alternates are followed")
    ap.add_argument("--urls", nargs="+", metavar="LANG:URL", help="language versions to compare (hreflang missing or broken)")
    ap.add_argument("--files", nargs="+", metavar="LANG:PATH", help="local drafts: HTML, Markdown, or JSON, CSV or TSV "
                                                                   "content files (with --key and --fields)")
    ap.add_argument("--key", help="with --files: the post's entry in each JSON, CSV or TSV file (its slug, or a dotted key)")
    ap.add_argument("--fields", type=content_fields, help="with --key: the fields to read, e.g. title,excerpt,content")
    ap.add_argument("--base-url", default="https://localhost/{lang}/", help="URL of each --files draft; {lang} becomes its code")
    ap.add_argument("--source", help="code of the original version (default: the x-default target, else the longest)")
    args = ap.parse_args()
    if sum(bool(x) for x in (args.url, args.urls, args.files)) != 1:
        ap.error("give exactly one of: URL, --urls, --files")
    if (args.key or args.fields) and not args.files:
        ap.error("--key and --fields pick an entry of a --files content file")
    if args.files and "{lang}" not in args.base_url:
        ap.error("--base-url needs a {lang} placeholder so each draft gets its own URL")

    capped = False
    if args.url:
        versions, capped = discover_cluster(args.url)
        start = versions[0]
        if start.facts.status is None or start.facts.status >= 400:
            print_json({"url": args.url, "status": start.facts.status,
                        "error": start.result.error or f"HTTP {start.facts.status}: not checking an error page"})
            return 2
    elif args.urls:
        versions = []
        for code, url in _pairs(args.urls, "--urls", ap):
            if versions:
                time.sleep(FETCH_DELAY_S)
            versions.append(load_version(code, url, fetch(url)))
    else:
        versions = []
        for code, path in _pairs(args.files, "--files", ap):
            url = args.base_url.replace("{lang}", code)
            try:
                versions.append(load_version(code, url, load_draft(path, url, args.key, args.fields)))
            except ValueError as err:
                ap.error(str(err))
    check_hreflang = not args.files or any(v.facts.hreflang for v in versions)  # drafts often get hreflang at build time
    try:
        report = cluster_report(versions, args.source, check_hreflang, capped)
    except ValueError as err:
        ap.error(str(err))
    print_json({"url": args.url or versions[0].facts.final_url, **report})
    return 0


if __name__ == "__main__":
    sys.exit(main())
