#!/usr/bin/env python3
"""Shared SEO research store: research a site once, then let every skill reuse it.

The store is a folder in the project (default seo-research/), versioned with the repo. It keeps keywords with their
demand evidence, SERP snapshots, clusters, competitors, a page inventory and glossaries, per locale, with the source
and date of every value. Secrets, raw paid-API responses (they stay in the credit guard cache) and personal data
never go in. Schema, merge rules and TTLs: references/research-store.md.

Usage:
  research_store.py init --site https://example.com --locales en,ka,ru      # the first locale is the default
  research_store.py ingest keyword-ideas kw.json --locale en                  # keyword_ideas.py output
  research_store.py ingest serps serps.json --locale en [--details details.json]
  research_store.py ingest clusters clusters.json --locale en                 # serp_cluster.py output
  research_store.py ingest gsc gsc.json [--locale en]                         # gsc_analyze.py output or a GSC CSV
  research_store.py ingest crawl pages.csv                                    # crawl.py --csv output
  research_store.py ingest volumes volumes.csv --locale en --source semrush   # keyword,volume[,difficulty]
  research_store.py ingest posts posts.csv [--locale en]                      # CMS export: url or slug, title…
  research_store.py status
  research_store.py next-topics [--locale en] [--limit 10]
  research_store.py set-status --cluster en-001 --status briefed
  research_store.py set-status --keyword "english tutor" --locale en --status published --url https://example.com/x/
  research_store.py glossary add --locale ka --term Claude --translation Claude --do-not-translate
  research_store.py glossary show --locale ka
  research_store.py export keywords|clusters|inventory|posts [--locale en] --format csv|json
Every ingest takes --as-of DATE, the last day its data covers (default: the file's modification time); give it for a
GSC comparison-period export. Every command takes --dir DIR (default seo-research). Output is JSON on stdout; export
--format csv prints CSV.
"""
from __future__ import annotations

import argparse
import codecs
import csv
import datetime as dt
import glob
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import urllib.parse
from collections import Counter, defaultdict

from credit_guard import locked
from gsc_analyze import key_of, load_rows
from keyword_ideas import classify_intent
from seo_lib import normalize_url, print_json, registrable_host
from serp_cluster import _key as same_page_key

DEFAULT_DIR = "seo-research"
STORE_VERSION = 1
STATUSES = ("planned", "briefed", "drafted", "scheduled", "published", "skip")
ROLES = ("pillar", "cluster", "support")
# Days before a dataset is stale. Clusters and glossaries are decisions, not observations, so they never go stale.
TTL_DAYS = {"keywords": 90, "volumes": 30, "serps": 30, "gsc": 7, "inventory": 30, "competitors": 90,
            "clusters": None, "glossary": None, "posts": 7}
INVENTORY_COLUMNS = ["url", "locale", "title", "cluster_id", "words", "last_modified", "status", "gsc_clicks",
                     "gsc_impressions", "crawled_at", "gsc_at"]
INVENTORY_NUMBERS = ("words", "status", "gsc_clicks", "gsc_impressions")
KEYWORD_COLUMNS = ["keyword", "locale", "intent", "cluster_id", "status", "target_url", "autocomplete_sources",
                   "gsc_impressions", "gsc_position", "gsc_pages", "volume", "volume_source", "volume_date",
                   "difficulty", "difficulty_source", "serp_features", "notes", "first_seen", "updated_at"]
CLUSTER_COLUMNS = ["cluster_id", "locale", "head_keyword", "head_source", "keywords", "role", "target_url",
                   "target_source", "interlinks", "priority", "status", "brief_slug"]
POST_COLUMNS = ["locale", "url", "slug", "title", "status", "publish_date", "cluster_id", "as_of"]
VOLUME_HEADERS = {  # Semrush, Ahrefs, DataForSEO and Keyword Planner export names
    "keyword": {"keyword", "keywords", "query", "phrase", "search term"},
    "volume": {"volume", "search volume", "search_volume", "avg. monthly searches", "avg monthly searches"},
    "difficulty": {"difficulty", "keyword difficulty", "keyword_difficulty", "kd"},
}
POST_HEADERS = {  # plain CSV names and seo-blog-review's post inventory
    "url": {"url", "address"},
    "slug": {"slug"},
    "locale": {"locale", "lang", "language"},
    "title": {"title"},
    "status": {"status"},
    "publish_date": {"publish_date", "publish date", "date", "date_published"},
}
GSC_MIN_IMPRESSIONS = 10  # below this a GSC query, or a page's part of it, is too thin to count: the query is skipped
COMPETING_PAGE_SHARE = 0.1  # as in gsc_analyze.cannibalization: a page with >=10% of a query's impressions competes
GSC_TARGET_MAX_POSITION = 20  # a page GSC ranks lower than this for a query doesn't compete for it yet
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w")
PHONE_RUN = re.compile(r"\+?(?:\(\d+\)|\d+)(?:[ .\-]?(?:\(\d+\)|\d+))*")  # digits joined by spaces, dots, - or ()
PHONE_DIGITS = range(9, 16)  # E.164 numbers have at most 15 digits; national ones at least 9 (+995 5XX XX XX XX)
GEORGIAN_MOBILE = re.compile(r"5\d\d \d\d \d\d \d\d")  # 5XX XX XX XX, as Georgian mobile numbers are written
YEAR = re.compile(r"(19|20)\d\d")
TEXT_LIMIT = 200  # PAA questions and result titles are trimmed to this; the store keeps no vendor answer text
# Who set a keyword's intent, weakest first. A stronger source replaces a weaker one whatever the dates; the store's
# own wording guess (for a keyword first seen outside keyword_ideas) is replaced by any real observation.
STORE_INTENT_GUESS = "wording-guess"
KEYWORD_IDEAS_INTENT = "keyword_ideas"  # keyword_ideas.py's own classify_intent label, carried in its output
INTENT_SOURCE_RANK = {STORE_INTENT_GUESS: 0, KEYWORD_IDEAS_INTENT: 1, "serp": 2}
# Where a cluster's target_url came from. The first two are declared and never recomputed; the others are derived
# from its keywords on every write: "keywords" when a keyword's target was set with set-status, "gsc" when GSC
# impressions inferred it.
DECLARED_CLUSTER_TARGETS = ("input", "set-status")
GSC_INFERRED_TARGET = "gsc"
# next-topics heuristic: page types a blog post or guide competes with, forum hosts that signal a beatable SERP
ARTICLE_TYPES = {"guide/article", "listicle", "news", "forum/ugc"}
MIN_TYPED_RESULTS = 5
INTENT_FIT = {"informational": 3, "commercial": 2, "unclear": 1, "transactional": 0, "navigational": 0}
UGC_HOSTS = ("reddit.com", "quora.com", "stackexchange.com", "stackoverflow.com")
HEURISTIC = ("priority = intent_fit (0..3) + demand (0..4) + serp_gap (-1..3) - cannibalisation (0..3). "
             "[heuristic, not a Google metric: scored for an article page; read the reasons, not only the order]")
MISSING = object()


# ---------------------------------------------------------------- small helpers

def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def observed_at(path: str) -> str:
    """When an input's data was fetched or exported: the file's modification time (a copied file looks newer)."""
    return dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc).replace(microsecond=0).isoformat()


def as_of_date(value: str) -> str:
    """--as-of: the last day (or moment) an input's data covers, as UTC ISO time. A date alone is 00:00 UTC."""
    text = value.strip()
    try:
        moment = dt.datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a date: {value!r} (use YYYY-MM-DD, the last day the data covers)") \
            from None
    moment = moment if moment.tzinfo else moment.replace(tzinfo=dt.timezone.utc)
    if moment > dt.datetime.now(dt.timezone.utc):
        raise argparse.ArgumentTypeError(f"{value} is in the future; give the last day the data covers")
    return moment.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def data_date(args) -> str:
    """The date of an ingest's data: --as-of when given, else the file's modification time."""
    return args.as_of or observed_at(args.file)


def age_days(at: str, now: str) -> float:
    return round((dt.datetime.fromisoformat(now) - dt.datetime.fromisoformat(at)).total_seconds() / 86400, 1)


def locale_code(value: str) -> str:
    code = value.strip().lower().replace("_", "-")
    if not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]{2,8})*", code):
        raise argparse.ArgumentTypeError(f"not a locale code: {value!r} (use en, ka, ru-ge …)")
    return code


def locale_list(value: str) -> list[str]:
    """init --locales: a comma list of locale codes, duplicates removed, order kept (the first is the default)."""
    return list(dict.fromkeys(locale_code(code) for code in value.split(",") if code.strip()))


def positive_int(value: str) -> int:
    if not re.fullmatch(r"\d+", value.strip()) or int(value) < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or more, got {value!r}")
    return int(value)


def clean_keyword(text: str) -> str:
    return " ".join(str(text).lower().split())


def url_key(url: str | None) -> str | None:
    """For comparing URLs only, as serp_cluster compares results: www., the scheme and a trailing slash are ignored."""
    return same_page_key(url) if url else None


def slugify(text: str) -> str:
    return re.sub(r"[^\w]+", "-", text.lower()).strip("-")  # \w keeps Georgian and Cyrillic letters


def to_int(value) -> int | None:
    text = str(value if value is not None else "").strip().replace(",", "")
    return round(float(text)) if re.fullmatch(r"-?\d+(\.\d+)?", text) else None


def parse_volume(cell: str):
    """A number; or the text as written when it is a range (Keyword Planner without ad spend: "1K – 10K") or an
    abbreviated number ("2.4K"); else None, so a vendor placeholder ("-", "n/a") never replaces a stored volume."""
    cell = cell.strip()
    plain = re.sub(r"[,\s  ]", "", cell)
    if re.fullmatch(r"\d+(\.\d+)?", plain):
        return round(float(plain))
    if re.fullmatch(r"\d[\d.,]*\s*[KkMm]?(\s*[–—-]\s*\d[\d.,]*\s*[KkMm]?)?", cell):
        return cell
    return None


def volume_number(volume) -> float:
    """A volume as a number for ranking; a range counts as its lower bound."""
    if isinstance(volume, (int, float)):
        return volume
    match = re.search(r"(\d+(?:\.\d+)?)\s*([km]?)", str(volume or "").lower())
    if not match:
        return 0
    return float(match.group(1)) * {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2)]


def is_ugc_host(url: str) -> bool:
    host = registrable_host(url)
    return any(host == name or host.endswith("." + name) for name in UGC_HOSTS)


def has_personal_data(keyword: str) -> bool:
    """An e-mail address, or a phone number: a run of 9–15 digits joined by spaces, dots, hyphens or brackets. A run
    joined by spaces alone is a list of quantities instead when its groups are all round numbers without a leading
    zero ("100 200 300 word essay"), all single digits ("9 8 7 6 5 4 3 2 1") or all years ("2023 2024 2025"), unless
    it is grouped as a Georgian mobile number (5XX XX XX XX). A phone number has a +, other separators, one long
    group, or a leading-zero or uneven group ("500 00 00 00", "123 45 67 89")."""
    if EMAIL.search(keyword):
        return True
    for run in PHONE_RUN.findall(keyword):
        if len(re.sub(r"\D", "", run)) not in PHONE_DIGITS:
            continue
        groups = run.split()
        if not re.fullmatch(r"[\d ]+", run) or len(groups) == 1 or GEORGIAN_MOBILE.fullmatch(run):
            return True
        quantities = (all(group[0] != "0" and group.endswith("0") for group in groups)
                      or all(len(group) == 1 for group in groups) or all(YEAR.fullmatch(group) for group in groups))
        if not quantities:
            return True
    return False


def require(condition: bool, path: str, where: str, expected: str) -> None:
    """Refuse a malformed input with its file and the place in it, rather than a traceback or a half-applied file."""
    if not condition:
        raise SystemExit(f"{path}: {where} must be {expected}")


def is_text_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def is_group_id(value) -> bool:
    """A serp_cluster.py group id, which interlinks name: a number or a string. JSON true is neither, though Python
    counts it as the number 1 (and would link group 1)."""
    return isinstance(value, (int, str)) and not isinstance(value, bool)


def clip(text: str) -> str:
    return " ".join(text.split())[:TEXT_LIMIT]


# ---------------------------------------------------------------- files

def read_json(path: str, default=MISSING):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        if default is MISSING:
            raise SystemExit(f"{path}: file not found") from None
        return default
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: not valid JSON ({exc})") from None


def read_jsonl(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    raise SystemExit(f"{path}: line {number} is not valid JSON; fix that line") from None
    return records


def read_store_csv(path: str, columns: list[str], numbers: tuple[str, ...] = ()) -> list[dict]:
    """Rows of a store CSV with exactly `columns` (a column the file lacks reads as empty)."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return [{c: to_int(row.get(c)) if c in numbers else row.get(c) or "" for c in columns}
                for row in csv.DictReader(fh)]


def read_text(path: str) -> str:
    """An export as text: UTF-16 with a BOM (Keyword Planner), else UTF-8 with or without a BOM."""
    with open(path, "rb") as fh:
        raw = fh.read()
    utf16 = raw[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
    try:
        return raw.decode("utf-16") if utf16 else raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SystemExit(f"{path}: not UTF-8 or UTF-16 text; re-export it as a UTF-8 CSV") from None


def read_table(path: str, headers: dict[str, set[str]],
               key_columns: tuple[str, ...] = ("keyword",)) -> tuple[list[dict], set[str]]:
    """Rows of a CSV or TSV export renamed to canonical columns. The header is the first line naming one of
    `key_columns`, so title rows above it are skipped (Keyword Planner writes them, and UTF-16)."""
    lines = read_text(path).splitlines()
    for index, line in enumerate(lines):
        delimiter = "\t" if "\t" in line else ","
        names = [cell.strip().lower() for cell in next(csv.reader([line], delimiter=delimiter), [])]
        mapping = {i: canonical for i, name in enumerate(names)
                   for canonical, aliases in headers.items() if name in aliases}
        if set(key_columns) & set(mapping.values()):
            rows = [{mapping[i]: cell for i, cell in enumerate(cells) if i in mapping}
                    for cells in csv.reader(lines[index + 1:], delimiter=delimiter) if any(c.strip() for c in cells)]
            return rows, set(mapping.values())
    expected = sorted(set().union(*(headers[c] for c in key_columns)))
    raise SystemExit(f"{path}: no {' or '.join(key_columns)} column found (expected one of {expected})")


def dump_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def csv_text(columns: list[str], rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def flat_row(record: dict, columns: list[str]) -> dict:
    row = {}
    for column in columns:
        value = record[column] if column in record else record["demand"][column]
        row[column] = ";".join(value) if isinstance(value, list) else value
    return row


def write_atomic(path: str, text: str) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o644)  # mkstemp makes it private; store files are shared through the repo
    os.replace(temporary, path)


# ---------------------------------------------------------------- merge rules

def new_keyword(keyword: str, locale: str, at: str, now: str) -> dict:
    return {"keyword": keyword, "locale": locale, "intent": None, "cluster_id": None,
            "demand": {"autocomplete_sources": [], "gsc_impressions": None, "gsc_position": None, "gsc_pages": [],
                       "volume": None, "volume_source": None, "volume_date": None, "difficulty": None,
                       "difficulty_source": None},
            "serp_features": [], "target_url": None, "status": "planned", "notes": "", "first_seen": at,
            "updated_at": now, "provenance": {}}


def set_field(record: dict, field: str, value, source: str, at: str) -> bool:
    """Newest value wins: write `value` unless the stored one was observed later. None never overwrites (never drop
    data). The winner's source and date go to record["provenance"][field]. True when anything changed."""
    if value is None:
        return False
    known = record["provenance"].get(field)
    if known and known["at"] > at:
        return False
    holder, name = (record["demand"], field.split(".", 1)[1]) if field.startswith("demand.") else (record, field)
    stamp = {"source": source, "at": at}
    if holder.get(name) == value and known == stamp:
        return False
    holder[name] = value
    record["provenance"][field] = stamp
    return True


def set_intent(record: dict, intent: str | None, source: str, at: str) -> bool:
    """A stronger source (INTENT_SOURCE_RANK) replaces a weaker one whatever the dates, a weaker one never replaces a
    stronger one, and between equals the newest wins. So the SERP's intent beats keyword_ideas' guess, and both beat
    the store's own guess, in any ingest order."""
    if intent is None:
        return False
    known = record["provenance"].get("intent")
    rank, known_rank = INTENT_SOURCE_RANK[source], INTENT_SOURCE_RANK[known["source"]] if known else -1
    if rank < known_rank:
        return False
    if rank > known_rank:
        record["intent"], record["provenance"]["intent"] = intent, {"source": source, "at": at}
        return True
    return set_field(record, "intent", intent, source, at)


def add_autocomplete_sources(record: dict, sources: list[str], at: str) -> bool:
    """Demand evidence accumulates: engines that suggested the keyword are added, never removed. It is dated by the
    newest input that suggested the keyword, in any ingest order."""
    if not sources:
        return False
    merged = sorted(set(record["demand"]["autocomplete_sources"]) | set(sources))
    known = record["provenance"].get("demand.autocomplete_sources")
    stamp = {"source": "keyword_ideas", "at": max(at, known["at"]) if known else at}
    if merged == record["demand"]["autocomplete_sources"] and stamp == known:
        return False
    record["demand"]["autocomplete_sources"] = merged
    record["provenance"]["demand.autocomplete_sources"] = stamp
    return True


def apply(record: dict, values: dict, source: str, at: str, now: str) -> bool:
    changed = False
    for field, value in values.items():
        changed |= set_field(record, field, value, source, at)
    if changed:
        record["updated_at"] = now
    return changed


def demand_rank(record: dict) -> tuple:
    demand = record["demand"]
    return demand["gsc_impressions"] or 0, volume_number(demand["volume"]), len(demand["autocomplete_sources"])


def usable_keyword(raw: str, counts: Counter) -> str | None:
    keyword = clean_keyword(raw)
    if has_personal_data(keyword):
        counts["skipped_personal_data"] += 1
        return None
    return keyword or None


def tally(counts: Counter, created: bool, changed: bool) -> None:
    counts["added" if created else "updated" if changed else "unchanged"] += 1


# ---------------------------------------------------------------- the store

class Store:
    """The store folder in memory. Commands change it, then save() rewrites every file atomically in sorted order."""

    def __init__(self, directory: str):
        self.dir = directory
        self.site = read_json(self.file("site.json"))
        self.manifest = read_json(self.file("manifest.json"))
        self.keywords = {(r["locale"], r["keyword"]): r for r in read_jsonl(self.file("keywords.jsonl"))}
        self.clusters = {c["cluster_id"]: c for c in read_json(self.file("clusters.json"), [])}
        self.competitors = {c["domain"]: c for c in read_json(self.file("competitors.json"), [])}
        self.inventory = {row["url"]: row for row in read_store_csv(self.file("inventory.csv"), INVENTORY_COLUMNS,
                                                                    INVENTORY_NUMBERS)}
        self.posts = {post_key(row): row for row in read_store_csv(self.file("posts.csv"), POST_COLUMNS)}
        self.pending_serps: dict[str, dict] = {}  # SERP files an ingest made, written by save() with the rest
        self.upgrade_first_version_clusters()
        self.derive_gsc_targets()  # read-only commands see the derived fields as the next write stores them
        self.derive_clusters()

    def file(self, *parts: str) -> str:
        return os.path.join(self.dir, *parts)

    @property
    def locales(self) -> list[str]:
        return self.site["locales"]

    @property
    def own_hosts(self) -> set[str]:
        """The site's hosts: its domain plus the host of every markets[locale].url_prefix (ka.example.com, …)."""
        return {self.site["domain"]} | {registrable_host(m["url_prefix"]) for m in self.site["markets"].values()
                                        if m.get("url_prefix")}

    def is_own_url(self, url: str) -> bool:
        return registrable_host(url) in self.own_hosts

    def is_home_page(self, url: str) -> bool:
        """The site's or a locale's home page (/, /ka/, https://ka.example.com/): it ranks for everything, so GSC
        impressions never make it a keyword's target."""
        path = urllib.parse.urlsplit(url).path.strip("/").lower()
        return path == "" or path in self.locales

    def dataset_ttl(self, dataset: str) -> int | None:
        """The TTL in days, as tuned in manifest.json, else the default."""
        ttl = (self.manifest["datasets"].get(dataset) or {}).get("ttl_days", TTL_DAYS[dataset])
        require(ttl is None or isinstance(ttl, (int, float)) and not isinstance(ttl, bool), self.file("manifest.json"),
                f"datasets.{dataset}.ttl_days", "a number of days, or null for never stale")
        return ttl

    def check_locale(self, locale: str) -> str:
        if locale not in self.locales:
            raise SystemExit(f"locale {locale!r} is not in this store ({', '.join(self.locales)}). Add it: "
                             f"research_store.py init --site {self.site['site']} --locales {locale} --dir {self.dir}")
        return locale

    def locale_of_url(self, url: str) -> str:
        """markets[locale].url_prefix when set, else a first path segment that is a locale (/ka/…), else the
        default locale."""
        prefixes = sorted(((m["url_prefix"], loc) for loc, m in self.site["markets"].items() if m.get("url_prefix")),
                          key=lambda p: -len(p[0]))
        for prefix, locale in prefixes:
            if url.startswith(prefix):
                return locale
        first = urllib.parse.urlsplit(url).path.strip("/").split("/")[0].lower()
        return first if first in self.locales else self.locales[0]

    def keyword(self, keyword: str, locale: str, at: str, now: str) -> tuple[dict, bool]:
        """The record for keyword+locale, created with the store's own wording-based intent guess when new."""
        record = self.keywords.get((locale, keyword))
        if record:
            record["first_seen"] = min(record["first_seen"], at)
            if record["provenance"]["intent"]["source"] == STORE_INTENT_GUESS:  # dated by its oldest input, any order
                record["provenance"]["intent"]["at"] = record["first_seen"]
            return record, False
        record = self.keywords[(locale, keyword)] = new_keyword(keyword, locale, at, now)
        set_intent(record, classify_intent(keyword), STORE_INTENT_GUESS, at)
        return record, True

    def inventory_row(self, url: str) -> dict:
        if url not in self.inventory:
            self.inventory[url] = {"url": url, "locale": self.locale_of_url(url), "title": "", "cluster_id": "",
                                   "words": None, "last_modified": "", "status": None, "gsc_clicks": None,
                                   "gsc_impressions": None, "crawled_at": "", "gsc_at": ""}
        return self.inventory[url]

    def serp_file(self, locale: str, keyword: str) -> str:
        return self.file("serps", locale, hashlib.sha1(keyword.encode("utf-8")).hexdigest() + ".json")

    def serp(self, locale: str, keyword: str | None) -> dict | None:
        if not keyword:
            return None
        path = self.serp_file(locale, keyword)
        return self.pending_serps.get(path) or read_json(path, None)

    def serp_paths(self) -> list[str]:
        return sorted(set(glob.glob(self.file("serps", "*", "*.json"))) | set(self.pending_serps))

    def serp_snapshots(self) -> list[dict]:
        return [self.pending_serps.get(path) or read_json(path) for path in self.serp_paths()]

    def dataset_date(self, dataset: str, locale: str) -> str | None:
        return (self.manifest["datasets"].get(dataset) or {"locales": {}})["locales"].get(locale)

    def touch(self, dataset: str, locale: str, source: str, at: str) -> None:
        """Record that `dataset` got data for `locale` observed at `at`; its dates only move forward."""
        entry = self.manifest["datasets"].setdefault(dataset, {"updated_at": at, "sources": [], "records": 0,
                                                               "ttl_days": TTL_DAYS[dataset], "locales": {}})
        entry["sources"] = sorted(set(entry["sources"]) | {source})
        entry["locales"][locale] = max(entry["locales"].get(locale, at), at)
        entry["updated_at"] = max(entry["locales"].values())

    def new_cluster_id(self, locale: str) -> str:
        numbers = [int(c.rsplit("-", 1)[1]) for c in self.clusters if self.clusters[c]["locale"] == locale]
        return f"{locale}-{max(numbers, default=0) + 1:03d}"

    def competitor_domains(self, snapshot: dict) -> set[str]:
        """The registrable domains of a top 10, minus the site's own hosts."""
        return {registrable_host(r["url"]) for r in snapshot["results"]} - self.own_hosts - {""}

    def refresh_competitors(self, older_fetches: list[dict]) -> None:
        """Domains in the stored top-10s, minus the site's own hosts. A domain no longer seen keeps its entry with 0.
        `older_fetches` are SERPs older than their keyword's stored snapshot: their domains count as they would have
        had that file come first (seen then, no longer seen now)."""
        seen: dict[str, dict] = {}
        for snapshot in self.serp_snapshots():
            for domain in self.competitor_domains(snapshot):
                entry = seen.setdefault(domain, {"locales": set(), "keywords_shared": 0, "last_seen": ""})
                entry["locales"].add(snapshot["locale"])
                entry["keywords_shared"] += 1
                entry["last_seen"] = max(entry["last_seen"], snapshot["fetched_at"])
        for domain, old in self.competitors.items():
            if domain not in seen:
                old["keywords_shared"] = 0
        for fetch in older_fetches:
            for domain in self.competitor_domains(fetch):
                if domain in seen:
                    seen[domain]["locales"].add(fetch["locale"])
                    continue
                old = self.competitors.get(domain, {"locales": [], "last_seen": ""})
                self.competitors[domain] = {
                    "domain": domain, "locales": sorted(set(old["locales"]) | {fetch["locale"]}), "keywords_shared": 0,
                    "last_seen": max(old["last_seen"], fetch["fetched_at"])}
        for domain, entry in seen.items():
            old_locales = set(self.competitors.get(domain, {}).get("locales", []))
            self.competitors[domain] = {"domain": domain, "locales": sorted(entry["locales"] | old_locales),
                                        "keywords_shared": entry["keywords_shared"], "last_seen": entry["last_seen"]}

    def record_counts(self) -> dict[str, int]:
        records = list(self.keywords.values())
        return {
            "keywords": len(records),
            "volumes": sum(r["demand"]["volume"] is not None for r in records),
            "serps": len(self.serp_paths()),
            "clusters": len(self.clusters),
            "gsc": sum(r["demand"]["gsc_impressions"] is not None for r in records)
                   + sum(row["gsc_impressions"] is not None for row in self.inventory.values()),
            "inventory": len(self.inventory),
            "competitors": len(self.competitors),
            "glossary": sum(len(read_json(path)) for path in glob.glob(self.file("glossary", "*.json"))),
            "posts": len(self.posts),
        }

    def upgrade_first_version_clusters(self) -> None:
        """A clusters.json written by the store's first version, before head_source, target_source and brief_slug. That
        version kept a head until the next clusters file, so it stays as if the file had named it. A target that none
        of the cluster's keywords has came from the clusters file or set-status, so it stays declared; one that a
        keyword has is derived again. Runs before derive_gsc_targets changes the keywords' targets."""
        for cluster in self.clusters.values():
            if "head_source" not in cluster:
                cluster["head_source"] = "input"
            if "target_source" not in cluster:
                targets = {self.keywords[(cluster["locale"], k)]["target_url"] for k in cluster["keywords"]
                           if (cluster["locale"], k) in self.keywords}
                declared = cluster["target_url"] and cluster["target_url"] not in targets
                cluster["target_source"] = "input" if declared else None
            cluster.setdefault("brief_slug", None)

    def derive_gsc_targets(self) -> None:
        """A keyword's target that set-status didn't declare is the first of its demand.gsc_pages (competing_pages),
        or none, recomputed on every load and write so the newest GSC export with pages decides it in any ingest order.
        A store written before that rule may list home pages, or pages of a query under GSC_MIN_IMPRESSIONS, which
        could never compete: those are dropped first."""
        for record in self.keywords.values():
            demand, provenance = record["demand"], record["provenance"]
            if (demand["gsc_impressions"] or 0) < GSC_MIN_IMPRESSIONS:
                demand["gsc_pages"] = []
            else:
                demand["gsc_pages"] = [page for page in demand["gsc_pages"] if not self.is_home_page(page)]
            if (provenance.get("target_url") or {}).get("source", GSC_INFERRED_TARGET) != GSC_INFERRED_TARGET:
                continue  # set with set-status
            if demand["gsc_pages"]:
                record["target_url"] = demand["gsc_pages"][0]
                provenance["target_url"] = {"source": GSC_INFERRED_TARGET, "at": provenance["demand.gsc_pages"]["at"]}
            else:
                record["target_url"] = None
                provenance.pop("target_url", None)

    def derive_clusters(self) -> None:
        """The cluster fields that follow from its keywords, recomputed on every write so the ingest order never
        matters: a target the clusters file or set-status didn't declare (the most common target_url of its keywords),
        and the head keyword while the cluster is planned, unless the clusters file named it. Once a cluster has left
        planned, its brief's file name is frozen in brief_slug."""
        for cluster in self.clusters.values():
            missing = [k for k in cluster["keywords"] if (cluster["locale"], k) not in self.keywords]
            if missing:  # a hand edit or a git merge resolution
                raise SystemExit(f"{self.file('clusters.json')}: cluster {cluster['cluster_id']} keyword {missing[0]!r} "
                                 f"is not in {self.file('keywords.jsonl')}; restore its line there (git history has "
                                 "it) or remove the keyword from that cluster")
            require(is_text_list(cluster.get("interlinks")), self.file("clusters.json"),
                    f"cluster {cluster['cluster_id']} interlinks", "a list of cluster ids")
            gone = [c for c in cluster["interlinks"] if c not in self.clusters]
            if gone:
                raise SystemExit(f"{self.file('clusters.json')}: cluster {cluster['cluster_id']} interlinks "
                                 f"{gone[0]!r}, which is not in that file; restore that cluster (git history has it) "
                                 "or remove the interlink")
            records = [self.keywords[(cluster["locale"], k)] for k in cluster["keywords"]]
            if cluster.get("target_source") not in DECLARED_CLUSTER_TARGETS:
                targets = Counter(r["target_url"] for r in records if r["target_url"])
                cluster["target_url"] = targets.most_common(1)[0][0] if targets else None
                inferred = all(r["provenance"]["target_url"]["source"] == "gsc" for r in records
                               if r["target_url"] and r["target_url"] == cluster["target_url"])
                cluster["target_source"] = (None if not cluster["target_url"] else
                                            GSC_INFERRED_TARGET if inferred else "keywords")
            stale_head = cluster["status"] == "planned" and cluster["head_source"] != "input"
            if cluster["keywords"] and (stale_head or cluster["head_keyword"] not in cluster["keywords"]):
                cluster["head_keyword"] = best_keyword(self, cluster["locale"], cluster["keywords"])
                cluster["head_source"] = "picked"
        slugs = brief_slugs(self)
        for cluster in self.clusters.values():
            if cluster["status"] != "planned" and not cluster["brief_slug"]:
                cluster["brief_slug"] = slugs[cluster["cluster_id"]]

    def save(self, now: str) -> None:
        self.derive_gsc_targets()
        self.derive_clusters()
        context = scoring_context(self)
        for cluster in self.clusters.values():
            cluster["priority"] = score_cluster(self, cluster, context)["priority"]
        for row in self.inventory.values():
            row["cluster_id"] = ";".join(context["targets"].get(url_key(row["url"]), []))
        for key, cluster_ids in post_clusters(self).items():
            self.posts[key]["cluster_id"] = ";".join(cluster_ids)
        keyword_lines = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                         for _, record in sorted(self.keywords.items()))
        inventory = sorted(self.inventory.values(), key=lambda row: (row["locale"], row["url"]))
        for path, snapshot in sorted(self.pending_serps.items()):
            write_atomic(path, dump_json(snapshot))
        write_atomic(self.file("site.json"), dump_json(self.site))
        write_atomic(self.file("keywords.jsonl"), "".join(keyword_lines))
        write_atomic(self.file("clusters.json"), dump_json([self.clusters[c] for c in sorted(self.clusters)]))
        write_atomic(self.file("competitors.json"), dump_json([self.competitors[d] for d in sorted(self.competitors)]))
        write_atomic(self.file("inventory.csv"), csv_text(INVENTORY_COLUMNS, inventory))
        write_atomic(self.file("posts.csv"), csv_text(POST_COLUMNS, sorted_posts(self.posts.values())))
        counts = self.record_counts()
        for name, entry in self.manifest["datasets"].items():
            entry["records"] = counts[name]
        write_atomic(self.file("manifest.json"), dump_json(self.manifest))


def init_store(directory: str, site_url: str, locales: list[str] | None, now: str) -> dict:
    parts = urllib.parse.urlsplit(site_url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise SystemExit(f"--site must be an http(s) URL, got {site_url!r}")
    given = locales or []
    with locked(directory):
        site_path = os.path.join(directory, "site.json")
        site = read_json(site_path, None)
        if site is None:
            site = {"site": normalize_url(site_url), "domain": registrable_host(site_url), "locales": given or ["en"],
                    "markets": {}, "money_pages": [], "templates": [], "stack": "",
                    "assumptions": [] if given else ["locales not given at init: assumed en"]}
        elif site["domain"] != registrable_host(site_url):
            raise SystemExit(f"{directory} is the store for {site['domain']}, not {registrable_host(site_url)}")
        else:
            site["locales"] += [code for code in given if code not in site["locales"]]
        write_atomic(site_path, dump_json(site))
        if not os.path.exists(os.path.join(directory, "manifest.json")):
            write_atomic(os.path.join(directory, "manifest.json"), dump_json({"store_version": STORE_VERSION,
                                                                              "datasets": {}}))
        if not os.path.exists(os.path.join(directory, ".gitignore")):
            write_atomic(os.path.join(directory, ".gitignore"), ".lock\n*.tmp\n")
        Store(directory).save(now)
    return {"store": directory, "site": site["site"], "domain": site["domain"], "locales": site["locales"]}


# ---------------------------------------------------------------- ingest

def summary(kind: str, path: str, locale: str | None, at: str, counts: Counter) -> dict:
    return {"ingested": kind, "file": path, "locale": locale, "observed_at": at, **dict(sorted(counts.items()))}


def ingest_keyword_ideas(store: Store, args, now: str) -> dict:
    data = read_json(args.file)
    if not isinstance(data, dict) or not isinstance(data.get("keywords"), list) or not isinstance(data.get("locale"),
                                                                                                  str):
        raise SystemExit(f"{args.file}: not keyword_ideas.py output (needs 'keywords' and 'locale')")
    for number, item in enumerate(data["keywords"]):
        where = f"keywords[{number}]"
        require(isinstance(item, dict) and isinstance(item.get("keyword"), str), args.file, where,
                "an object with a 'keyword' string")
        require(is_text_list(item.get("sources", [])), args.file, f"{where}.sources", "a list of strings")
        require(isinstance(item.get("intent"), (str, type(None))), args.file, f"{where}.intent", "a string")
    locale = store.check_locale(args.locale)
    hl, _, gl = data["locale"].lower().partition("-")
    if hl != locale.split("-")[0]:
        raise SystemExit(f"{args.file} was fetched with --hl {hl}, which is not the language of locale {locale}")
    market = store.site["markets"].setdefault(locale, {})
    region = locale.split("-")[1] if re.fullmatch(r"[a-z]+-[a-z]{2}", locale) else ""  # en-gb is the gb market
    market_gl = market.get("gl") or region
    if gl and market_gl and market_gl != gl:  # a locale is one market; another region needs its own locale
        raise SystemExit(f"{args.file} was fetched with --gl {gl}, but locale {locale} is the --gl {market_gl} "
                         f"market ({store.file('site.json')} markets.{locale}.gl, else the locale's region); give that "
                         f"market a locale of its own (init --locales {hl}-{gl})")
    market.setdefault("hl", hl)
    market["gl"] = market_gl or gl  # a file without a region fills nothing, in any order
    at, counts = data_date(args), Counter()
    for item in data["keywords"]:
        keyword = usable_keyword(item["keyword"], counts)
        if not keyword:
            continue
        record, created = store.keyword(keyword, locale, at, now)
        changed = set_intent(record, item.get("intent"), KEYWORD_IDEAS_INTENT, at)
        changed |= add_autocomplete_sources(record, item.get("sources", []), at)
        if changed:
            record["updated_at"] = now
        tally(counts, created, changed)
    store.touch("keywords", locale, "keyword_ideas", at)
    return summary("keyword-ideas", args.file, locale, at, counts)


def paa_questions(items, path: str, where: str) -> list[str]:
    """Only the questions of a People Also Ask block: strings, or a vendor object's question (its 'question', else its
    'title', as DataForSEO's people_also_ask_element has it). Answer text and URLs are dropped."""
    require(isinstance(items, list), path, where, "a list")
    questions = []
    for number, item in enumerate(items):
        text = (item.get("question") or item.get("title")) if isinstance(item, dict) else item
        require(isinstance(text, str), path, f"{where}[{number}]", "a question string, or an object with a 'title'")
        if clip(text):
            questions.append(clip(text))
    return questions


def serp_details(path: str | None) -> dict[str, dict]:
    """The --details file, checked whole before anything is applied: per keyword, the results' titles and page types
    by URL, and features, PAA and intent, each None when the file doesn't give it (not observed)."""
    data = read_json(path) if path else {}
    require(isinstance(data, dict), path, "the file",
            '{"keyword": {"results": [{"url", "title", "type"}], "features": […], "paa": […], "intent": "…"}}')
    details = {}
    for raw_keyword, detail in data.items():
        where = repr(raw_keyword)
        require(isinstance(detail, dict), path, where, "an object")
        described = {}
        require(isinstance(detail.get("results", []), list), path, f"{where} results", "a list")
        for number, result in enumerate(detail.get("results", [])):
            spot = f"{where} results[{number}]"
            require(isinstance(result, dict) and isinstance(result.get("url"), str), path, spot,
                    "an object with a 'url' string")
            kind = result.get("type") or result.get("page_type") or ""
            require(isinstance(result.get("title") or "", str) and isinstance(kind, str), path, spot,
                    "an object whose title and type are strings")
            title = clip(result.get("title") or "")
            if title or kind:  # one with neither describes nothing, so a stored description stays in any order
                described[normalize_url(result["url"])] = {"title": title, "type": kind.lower()}
        features = detail.get("features")
        require(features is None or is_text_list(features), path, f"{where} features", "a list of strings")
        require(isinstance(detail.get("intent"), (str, type(None))), path, f"{where} intent", "a string")
        details[clean_keyword(raw_keyword)] = {
            "results": described,
            "features": None if features is None else sorted({re.sub(r"[^a-z0-9]+", "_", f.lower()).strip("_")
                                                              for f in features}),
            "paa": paa_questions(detail["paa"], path, f"{where} paa") if detail.get("paa") is not None else None,
            "intent": (detail.get("intent") or "").lower() or None}
    return details


def ingest_serps(store: Store, args, now: str) -> dict:
    serps = read_json(args.file)
    if not isinstance(serps, dict) or not all(is_text_list(v) for v in serps.values()):
        raise SystemExit(f"{args.file}: expected serps.json shaped {{\"keyword\": [\"top1 url\", …]}}")
    details = serp_details(args.details)
    locale = store.check_locale(args.locale)
    at, counts, older_fetches = data_date(args), Counter(), []
    for raw_keyword, urls in serps.items():
        keyword = usable_keyword(raw_keyword, counts)
        if not keyword:
            continue
        old = store.serp(locale, keyword) or {}
        detail = details.get(keyword, {"results": {}, "features": None, "paa": None, "intent": None})
        fetched = [normalize_url(u) for u in urls[:10]]
        kept_newer = old.get("fetched_at", "") > at
        if kept_newer:  # the newer snapshot stays; this fetch still counts as it would have in the other order
            counts["kept_newer"] += 1
            older_fetches.append({"locale": locale, "fetched_at": at, "results": [{"url": url} for url in fetched]})
            results = []
            for result in old["results"]:  # a page keeps its title and type between fetches, in either order
                described = None if result["title"] or result["type"] else detail["results"].get(result["url"])
                results.append({**result, **described} if described else result)
            store.pending_serps[store.serp_file(locale, keyword)] = {**old, "results": results}
        else:
            before = {r["url"]: r for r in old.get("results", [])}  # a page keeps its title and type between fetches
            results = []
            for url in fetched:
                known = detail["results"].get(url) or before.get(url) or {}
                results.append({"url": url, "title": known.get("title", ""), "type": known.get("type", "")})
            # features and PAA are this fetch's observations: never carried over from an older snapshot
            store.pending_serps[store.serp_file(locale, keyword)] = {
                "keyword": keyword, "locale": locale, "fetched_at": at, "results": results,
                "features": detail["features"], "paa": detail["paa"]}
        # the keyword record's own date rules keep its newer values, so an older fetch updates it in either order
        record, created = store.keyword(keyword, locale, at, now)
        changed = set_field(record, "serp_features", detail["features"], "serps", at)
        changed |= set_intent(record, detail["intent"], "serp", at)
        if changed:
            record["updated_at"] = now
        if not kept_newer:
            tally(counts, created, changed)
    store.touch("serps", locale, "serps", at)
    store.refresh_competitors(older_fetches)
    store.touch("competitors", locale, "serps", at)
    return summary("serps", args.file, locale, at, counts)


def best_keyword(store: Store, locale: str, keywords: list[str]) -> str:
    """Head term: the strongest demand evidence, then the broadest (shortest) phrase, then alphabetical."""
    return max(sorted(keywords), key=lambda k: (demand_rank(store.keywords[(locale, k)]), -len(k)))


def ingest_clusters(store: Store, args, now: str) -> dict:
    data = read_json(args.file)
    if not isinstance(data, dict) or "clusters" not in data:
        raise SystemExit(f"{args.file}: not serp_cluster.py output (needs 'clusters')")
    require(isinstance(data["clusters"], list), args.file, "clusters", "a list")
    for number, group in enumerate(data["clusters"]):
        where = f"clusters[{number}]"
        require(isinstance(group, dict) and is_group_id(group.get("id")), args.file, where, "an object with an 'id'")
        require(is_text_list(group.get("keywords")), args.file, f"{where}.keywords", "a list of strings")
        for key in ("head_keyword", "role", "target_url"):
            require(isinstance(group.get(key), (str, type(None))), args.file, f"{where}.{key}", "a string")
    links = data.get("interlink_clusters", [])
    require(isinstance(links, list), args.file, "interlink_clusters", "a list")
    for number, link in enumerate(links):
        require(isinstance(link, dict) and all(is_group_id(link.get(end)) for end in ("from", "to")),
                args.file, f"interlink_clusters[{number}]", "an object whose 'from' and 'to' are cluster ids")
    locale = store.check_locale(args.locale)
    at, counts = data_date(args), Counter()
    stored = store.dataset_date("clusters", locale)
    if stored and stored > at:
        raise SystemExit(f"{args.file} ({at}) is older than the stored {locale} clusters ({stored}); not applied")
    member_of = {k: c["cluster_id"] for c in store.clusters.values() if c["locale"] == locale for k in c["keywords"]}
    stable, claimed, groups = {}, set(), []
    for group in data["clusters"]:
        keywords = sorted({k for k in (usable_keyword(raw, counts) for raw in group["keywords"]) if k})
        if not keywords:
            continue
        votes = Counter(member_of[k] for k in keywords if k in member_of)
        reuse = [cid for cid, _ in sorted(votes.items(), key=lambda kv: (-kv[1], kv[0])) if cid not in claimed]
        cluster_id = reuse[0] if reuse else store.new_cluster_id(locale)
        counts["clusters_reused" if reuse else "clusters_added"] += 1
        claimed.add(cluster_id)
        stable[group["id"]] = cluster_id
        groups.append((cluster_id, keywords, group))
        moving = set(keywords)
        for other in store.clusters.values():  # membership moves to the newest grouping
            if other["locale"] == locale and other["cluster_id"] != cluster_id:
                other["keywords"] = [k for k in other["keywords"] if k not in moving]
        cluster = store.clusters.setdefault(cluster_id, {
            "cluster_id": cluster_id, "locale": locale, "head_keyword": None, "head_source": "picked", "keywords": [],
            "role": "cluster", "target_url": None, "target_source": None, "interlinks": [], "priority": 0,
            "status": "planned", "brief_slug": None})
        cluster["keywords"] = sorted(set(cluster["keywords"]) | set(keywords))
        for keyword in keywords:
            record, created = store.keyword(keyword, locale, at, now)
            tally(counts, created, apply(record, {"cluster_id": cluster_id}, "clusters", at, now))
    for cluster_id, keywords, group in groups:
        cluster = store.clusters[cluster_id]
        if group.get("role"):
            if group["role"] not in ROLES:
                raise SystemExit(f"{args.file}: role {group['role']!r} is not one of {', '.join(ROLES)}")
            cluster["role"] = group["role"]
        if group.get("target_url"):  # else a declared target is kept and a derived one recomputed (save)
            cluster["target_url"], cluster["target_source"] = normalize_url(group["target_url"]), "input"
        head = clean_keyword(group.get("head_keyword") or "")
        if head:
            if head not in cluster["keywords"]:
                raise SystemExit(f"{args.file}: head_keyword {head!r} is not in its cluster's keywords")
            cluster["head_keyword"], cluster["head_source"] = head, "input"
        else:  # picked by demand evidence on every write while planned (Store.derive_clusters)
            cluster["head_source"] = "picked"
    for link in links:
        if link["from"] not in stable or link["to"] not in stable:
            continue  # one end had only keywords that were skipped
        a, b = stable[link["from"]], stable[link["to"]]
        for source, target in ((a, b), (b, a)):
            store.clusters[source]["interlinks"] = sorted(set(store.clusters[source]["interlinks"]) | {target})
    store.touch("clusters", locale, "serp_cluster", at)
    return summary("clusters", args.file, locale, at, counts)


def gsc_rows_from_report(path: str) -> list[dict]:
    """The query/page rows inside a gsc_analyze.py report (its top lists only; a CSV gives every row)."""
    data = read_json(path)
    if not isinstance(data, dict) or "rows" not in data or "striking_distance" not in data:
        raise SystemExit(f"{path}: not gsc_analyze.py output (needs 'rows' and 'striking_distance')")
    def numbers(item: dict, keys: tuple[str, ...]) -> bool:
        return all(isinstance(item.get(k), (int, float)) for k in keys)

    rows: dict[str, dict] = {}
    for name in ("striking_distance", "ctr_underperformers", "question_queries"):
        for number, row in enumerate(data.get(name, [])):
            require(isinstance(row, dict) and numbers(row, ("clicks", "impressions", "position"))
                    and any(k in row for k in ("query", "page"))
                    and all(isinstance(row[k], str) for k in ("query", "page") if k in row),
                    path, f"{name}[{number}]", "a row with a query or page, clicks, impressions and position")
            rows.setdefault(key_of(row), row)
    for number, item in enumerate(data.get("cannibalization", [])):
        require(isinstance(item, dict) and isinstance(item.get("query"), str) and numbers(item, ("impressions",))
                and isinstance(item.get("pages"), list)
                and all(isinstance(p, dict) and isinstance(p.get("page"), str)
                        and numbers(p, ("clicks", "share", "position")) for p in item["pages"]),
                path, f"cannibalization[{number}]",
                "a query with impressions and pages (page, clicks, share, position)")
        for page in item["pages"]:
            row = {"query": item["query"], "page": page["page"], "clicks": page["clicks"],
                   "impressions": round(page["share"] * item["impressions"]), "position": page["position"]}
            rows.setdefault(key_of(row), row)
    return list(rows.values())


def gsc_rows_from_csv(path: str) -> list[dict]:
    try:
        return load_rows(path)
    except UnicodeDecodeError:
        raise SystemExit(f"{path}: not UTF-8 text; re-export it as a UTF-8 CSV") from None
    except ValueError as exc:  # gsc_analyze._number on a cell like "lots"
        raise SystemExit(f"{path}: a clicks, impressions, CTR or position cell is not a number ({exc})") from None


def competing_pages(store: Store, items: list[dict], impressions: float) -> list[str]:
    """The site's pages that compete for a query by GSC, most impressions first: each with at least
    GSC_MIN_IMPRESSIONS and COMPETING_PAGE_SHARE of the query's impressions at an average position of
    GSC_TARGET_MAX_POSITION or better, and never a home page, which gets impressions for everything. The first is the
    query's GSC target (Store.derive_gsc_targets); two or more is cannibalisation."""
    pages = []
    for row in sorted((r for r in items if "page" in r), key=lambda r: -r["impressions"]):
        url = normalize_url(row["page"])
        if (row["impressions"] >= max(GSC_MIN_IMPRESSIONS, COMPETING_PAGE_SHARE * impressions)
                and row["position"] <= GSC_TARGET_MAX_POSITION and not store.is_home_page(url)):
            pages.append(url)
    return pages


def ingest_gsc(store: Store, args, now: str) -> dict:
    rows = gsc_rows_from_report(args.file) if args.file.endswith(".json") else gsc_rows_from_csv(args.file)
    counts = Counter()
    own = [row for row in rows if "page" not in row or store.is_own_url(row["page"])]
    if len(own) < len(rows):
        counts["skipped_other_site"] = len(rows) - len(own)
    if rows and not own:
        raise SystemExit(f"{args.file}: every row is from another site; this store is for {store.site['domain']}")
    rows = own
    locale = store.check_locale(args.locale) if args.locale else None
    if not locale and any("query" in r and "page" not in r for r in rows):
        if len(store.locales) > 1:
            raise SystemExit(f"{args.file} has queries without pages, so their locale is unknown: pass --locale")
        locale = store.locales[0]
    at, touched = data_date(args), set()
    by_query, by_page = defaultdict(list), defaultdict(lambda: [0.0, 0.0])
    for row in rows:
        if "page" in row:
            by_page[normalize_url(row["page"])][0] += row["clicks"]
            by_page[normalize_url(row["page"])][1] += row["impressions"]
        if "query" in row:
            by_query[(locale or store.locale_of_url(row["page"]), clean_keyword(row["query"]))].append(row)
    for (query_locale, raw_query), items in sorted(by_query.items()):
        query = usable_keyword(raw_query, counts)
        if not query:
            continue
        store.check_locale(query_locale)
        impressions = sum(r["impressions"] for r in items)
        if impressions < GSC_MIN_IMPRESSIONS:  # stored keyword or not, so the store is the same in any ingest order
            counts["skipped_below_min_impressions"] += 1
            continue
        position = sum(r["position"] * r["impressions"] for r in items) / impressions
        pages = competing_pages(store, items, impressions) if any("page" in r for r in items) else None
        record, created = store.keyword(query, query_locale, at, now)
        changed = apply(record, {"demand.gsc_impressions": round(impressions),
                                 "demand.gsc_position": round(position, 1),
                                 "demand.gsc_pages": pages}, "gsc", at, now)
        tally(counts, created, changed)
        touched.add(query_locale)
    for url, (clicks, impressions) in sorted(by_page.items()):
        row = store.inventory_row(url)
        if row["gsc_at"] > at:  # each row keeps the date of its own GSC data
            counts["pages_kept_newer"] += 1
            continue
        row["gsc_clicks"], row["gsc_impressions"], row["gsc_at"] = round(clicks), round(impressions), at
        counts["pages"] += 1
        touched.add(row["locale"])
    for code in sorted(touched):
        store.touch("gsc", code, "gsc", at)
    return summary("gsc", args.file, locale, at, counts)


def ingest_crawl(store: Store, args, now: str) -> dict:
    at, counts, touched = data_date(args), Counter(), set()
    reader = csv.DictReader(io.StringIO(read_text(args.file)))
    missing = {"url", "status", "title", "word_count"} - set(reader.fieldnames or [])
    if missing:
        raise SystemExit(f"{args.file}: not a crawl.py --csv file (missing {sorted(missing)})")
    for raw in reader:
        url = normalize_url(raw["url"])
        if not store.is_own_url(url):
            counts["skipped_other_site"] += 1
            continue
        row = store.inventory_row(url)
        if row["crawled_at"] > at:  # each row keeps the date of its own crawl
            counts["kept_newer"] += 1
            continue
        row.update(title=raw["title"], words=to_int(raw["word_count"]), status=to_int(raw["status"]), crawled_at=at)
        modified = raw.get("last_modified") or raw.get("lastmod")  # CMS or Screaming Frog exports carry one
        if modified:
            row["last_modified"] = modified
        counts["pages"] += 1
        touched.add(row["locale"])
    if counts["skipped_other_site"] and not counts["pages"] + counts["kept_newer"]:
        raise SystemExit(f"{args.file}: every row is from another site; this store is for {store.site['domain']}")
    for code in sorted(touched):
        store.touch("inventory", code, "crawl", at)
    return summary("crawl", args.file, None, at, counts)


def ingest_volumes(store: Store, args, now: str) -> dict:
    locale = store.check_locale(args.locale)
    source = args.source.strip().lower()
    if not source:
        raise SystemExit("--source names the vendor, e.g. semrush, ahrefs, dataforseo, keyword-planner")
    rows, columns = read_table(args.file, VOLUME_HEADERS)
    if "volume" not in columns:
        raise SystemExit(f"{args.file}: no volume column found (expected one of {sorted(VOLUME_HEADERS['volume'])})")
    at, counts = data_date(args), Counter()
    for row in rows:
        keyword = usable_keyword(row.get("keyword", ""), counts)
        if not keyword:
            continue
        record, created = store.keyword(keyword, locale, at, now)
        demand = record["demand"]
        changed = False
        if set_field(record, "demand.volume", parse_volume(row.get("volume", "")), source, at):
            demand["volume_source"], demand["volume_date"], changed = source, at[:10], True
        difficulty = row.get("difficulty", "").strip()
        if set_field(record, "demand.difficulty", to_int(difficulty), source, at):
            demand["difficulty_source"], changed = source, True
        if changed:
            record["updated_at"] = now
        tally(counts, created, changed)
    store.touch("volumes", locale, source, at)
    return summary("volumes", args.file, locale, at, counts)


# ---------------------------------------------------------------- posts

def post_key(post: dict) -> str:
    """A post is known by its URL, or by <locale>/<slug> when the export gives no URL (a queued post)."""
    return post["url"] or f"{post['locale']}/{post['slug']}"


def sorted_posts(posts) -> list[dict]:
    return sorted(posts, key=lambda post: (post["locale"], post["url"], post["slug"]))


def url_slug(url: str) -> str:
    return urllib.parse.unquote(urllib.parse.urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]) if url else ""


def words_of(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", text.lower()))  # letters and digits of any script; - _ and punctuation split


def read_posts_export(path: str) -> list[dict]:
    """Rows of a posts export, renamed to the POST_HEADERS names: a CSV or TSV, or JSON (a list of posts, or
    {"posts": […]})."""
    if not path.endswith(".json"):
        return read_table(path, POST_HEADERS, key_columns=("url", "slug"))[0]
    data = read_json(path)
    items = data.get("posts") if isinstance(data, dict) else data
    require(isinstance(items, list), path, "the file", 'a list of posts, or {"posts": […]}')
    rows = []
    for number, item in enumerate(items, 1):
        require(isinstance(item, dict), path, f"row {number}", "an object")
        row = {}
        for key, value in item.items():
            canonical = next((c for c, aliases in POST_HEADERS.items() if key.strip().lower() in aliases), None)
            if canonical is None:
                continue
            require(isinstance(value, (str, type(None))), path, f"row {number} {key}", "text")
            row[canonical] = value or ""
        rows.append(row)
    return rows


def post_date(value: str, path: str, where: str) -> str:
    text = value.strip()
    if not text:
        return ""
    try:
        return dt.date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        raise SystemExit(f"{path}: {where} publish date {value!r} must start with YYYY-MM-DD") from None


def post_status(value: str, publish_date: str, as_of_day: str, path: str, where: str) -> str:
    """A store status, or empty: scheduled when the publish date is after the export's date, else published (an export
    lists existing posts)."""
    status = value.strip().lower()
    if not status:
        return "scheduled" if publish_date > as_of_day else "published"
    accepted = [s for s in STATUSES if s != "skip"]
    require(status in accepted, path, f"{where} status {value!r}", f"one of {', '.join(accepted)}, or empty")
    return status


def post_clusters(store: Store) -> dict[str, list[str]]:
    """The clusters each post covers, in its locale: those whose target, or a keyword's target, is the post's URL;
    else, by the words of its title and slug, the clusters holding the longest keyword those words contain, so a post
    "English tutor jobs in London" covers "english tutor jobs", not "english tutor" [heuristic]."""
    by_url, by_words = defaultdict(set), defaultdict(set)
    for cluster in store.clusters.values():
        locale = cluster["locale"]
        if cluster["target_url"]:
            by_url[(locale, url_key(cluster["target_url"]))].add(cluster["cluster_id"])
        for keyword in cluster["keywords"]:
            by_words[(locale, words_of(keyword))].add(cluster["cluster_id"])
            record = store.keywords.get((locale, keyword))
            if record and record["target_url"]:
                by_url[(locale, url_key(record["target_url"]))].add(cluster["cluster_id"])
    covered = {}
    for key, post in store.posts.items():
        found = by_url.get((post["locale"], url_key(post["url"]))) if post["url"] else None
        if not found:
            best, found = 0, set()
            for words in (words_of(post["title"]), words_of(post["slug"])):
                for start in range(len(words)):
                    for end in range(start + 1, len(words) + 1):
                        ids = by_words.get((post["locale"], words[start:end]))
                        if ids and end - start >= best:
                            found = (found if end - start == best else set()) | ids
                            best = end - start
        covered[key] = sorted(found)
    return covered


def ingest_posts(store: Store, args, now: str) -> dict:
    """Existing and queued posts from a CMS export, so next-topics never proposes their topics again."""
    rows = read_posts_export(args.file)
    default_locale = (store.check_locale(args.locale) if args.locale
                      else store.locales[0] if len(store.locales) == 1 else None)
    at, counts, touched, keys = data_date(args), Counter(), set(), []
    for number, raw in enumerate(rows, 1):
        where = f"row {number}"
        url = normalize_url(raw["url"].strip()) if raw.get("url", "").strip() else ""
        if url and not store.is_own_url(url):
            counts["skipped_other_site"] += 1
            continue
        slug = urllib.parse.unquote(raw.get("slug", "").strip()) or url_slug(url)
        require(bool(url or slug), args.file, where, "a post with a URL or a slug")
        if raw.get("locale", "").strip():
            try:
                code = locale_code(raw["locale"])
            except argparse.ArgumentTypeError as exc:
                raise SystemExit(f"{args.file}: {where}: {exc}") from None
            # an hreflang code with a region (en-GB, as seo-blog-review's inventory has it) is its language, unless the
            # store has that region as a locale of its own
            locale = store.check_locale(code if code in store.locales else code.split("-")[0])
        elif url:
            locale = store.locale_of_url(url)
        elif default_locale:
            locale = default_locale
        else:
            raise SystemExit(f"{args.file}: {where} has no URL and no locale, and the store has several: pass --locale")
        publish_date = post_date(raw.get("publish_date", ""), args.file, where)
        status = post_status(raw.get("status", ""), publish_date, at[:10], args.file, where)
        new = {"locale": locale, "url": url, "slug": slug, "title": "", "status": status, "publish_date": "",
               "cluster_id": "", "as_of": ""}
        key = post_key(new)
        old = store.posts.get(key)
        if old and old["as_of"] > at:  # each post keeps the date of the export it came from
            counts["kept_newer"] += 1
            continue
        post = dict(old or new)  # an empty cell never blanks a stored value
        post.update(locale=locale, slug=slug or post["slug"], title=clip(raw.get("title", "")) or post["title"],
                    status=status, publish_date=publish_date or post["publish_date"], as_of=at)
        tally(counts, old is None, post != old)
        store.posts[key] = post
        keys.append(key)
        touched.add(locale)
    if counts["skipped_other_site"] and not keys and not counts["kept_newer"]:
        raise SystemExit(f"{args.file}: every row is from another site; this store is for {store.site['domain']}")
    for code in sorted(touched):
        store.touch("posts", code, "posts", at)
    covered = post_clusters(store)
    counts["without_cluster"] = sum(not covered[key] for key in set(keys))
    return summary("posts", args.file, args.locale, at, counts)


# ---------------------------------------------------------------- next-topics heuristic

def scoring_context(store: Store) -> dict:
    targets = defaultdict(list)
    for cluster_id in sorted(store.clusters):
        if store.clusters[cluster_id]["target_url"]:
            targets[url_key(store.clusters[cluster_id]["target_url"])].append(cluster_id)
    live = defaultdict(list)
    for url in sorted(store.inventory):
        if store.inventory[url]["status"] == 200:
            live[store.inventory[url]["locale"]].append(store.inventory[url])
    return {"targets": targets, "live_pages": live, "live": {url_key(r["url"]) for rows in live.values() for r in rows}}


def score_intent_fit(head: dict | None, serp: dict | None, reasons: list[str]) -> int:
    types = [r["type"] for r in serp["results"] if r["type"]] if serp else []
    if len(types) >= MIN_TYPED_RESULTS:
        articles = sum(t in ARTICLE_TYPES for t in types)
        score = int(3 * articles / len(types) + 0.5)
        reasons.append(f"intent fit {score}/3: {articles} of {len(types)} typed top results are articles, listicles, "
                       f"news or forum threads [measured: SERP {serp['fetched_at'][:10]}]")
        return score
    intent = (head or {}).get("intent") or "unclear"
    source = ((head or {}).get("provenance", {}).get("intent") or {}).get("source", "none")
    score = INTENT_FIT.get(intent, 1)
    reasons.append(f"intent fit {score}/3: head keyword intent '{intent}' (from {source}); no typed SERP to confirm "
                   "the page type [heuristic]")
    return score


def score_demand(records: list[dict], reasons: list[str]) -> int:
    proven = [r for r in records if (r["demand"]["gsc_impressions"] or 0) >= GSC_MIN_IMPRESSIONS]
    if proven:
        impressions = sum(r["demand"]["gsc_impressions"] for r in proven)
        best = min(r["demand"]["gsc_position"] for r in proven)
        reasons.append(f"demand 4/4: {impressions} GSC impressions on {len(proven)} keywords, best average position "
                       f"{best} [measured]")
        return 4
    with_volume = [r for r in records if volume_number(r["demand"]["volume"]) > 0]
    if with_volume:
        top = max(with_volume, key=lambda r: volume_number(r["demand"]["volume"]))["demand"]
        reasons.append(f"demand 3/4: volume {top['volume']} ({top['volume_source']}, {top['volume_date']}) "
                       "[vendor data]")
        return 3
    engines = max((len(r["demand"]["autocomplete_sources"]) for r in records), default=0)
    if engines >= 2:
        reasons.append(f"demand 2/4: suggested by {engines} engines; no volume [measured: suggested]")
        return 2
    if engines == 1:
        reasons.append("demand 1/4: suggested by one engine; how often it is searched is unknown [measured: suggested]")
        return 1
    reasons.append("demand 0/4: no demand evidence yet [needs data]")
    return 0


def score_serp_gap(serp: dict | None, reasons: list[str]) -> int:
    if not serp:
        reasons.append("SERP gap 0: no SERP stored for the head keyword [needs data]")
        return 0
    weak = [r["url"] for r in serp["results"] if r["type"] == "forum/ugc" or is_ugc_host(r["url"])]
    score = min(len(weak), 3)
    reasons.append(f"SERP gap {score}: {len(weak)} forum or UGC results in the top {len(serp['results'])} "
                   "[heuristic: weak results are beatable]")
    if "ai_overview" in (serp["features"] or []):  # None: the fetch didn't record features
        score -= 1
        reasons.append("SERP gap -1: an AI Overview is shown, so organic clicks are likely lower [heuristic]")
    if serp["paa"]:
        reasons.append(f"{len(serp['paa'])} People Also Ask questions to answer (not scored)")
    return score


def score_cannibalisation(store: Store, cluster: dict, records: list[dict], serp: dict | None, context: dict,
                          reasons: list[str]) -> int:
    risk, target = 0, url_key(cluster["target_url"])
    ranking = sorted({page for r in records for page in r["demand"]["gsc_pages"]})
    others = [page for page in ranking if url_key(page) != target]
    if len(ranking) >= 2:
        risk += 2
        reasons.append(f"cannibalisation -2: {len(ranking)} of your URLs get impressions for this cluster "
                       f"({', '.join(ranking[:3])}); choose one owner [measured: GSC]")
    elif others:
        risk += 1
        reasons.append(f"cannibalisation -1: {others[0]} already gets impressions for this cluster; refresh or "
                       "retarget it rather than add a page [measured: GSC]")
    shared = [c for c in context["targets"].get(target, []) if c != cluster["cluster_id"]] if target else []
    if shared:
        risk += 1
        reasons.append(f"cannibalisation -1: clusters {', '.join(shared)} target the same URL")
    own = [r["url"] for r in (serp or {}).get("results", [])
           if store.is_own_url(r["url"]) and url_key(r["url"]) != target]
    if own:
        risk += 1
        reasons.append(f"cannibalisation -1: the site already ranks in the top 10 with {own[0]} [measured: SERP]")
    if cluster.get("target_source") == GSC_INFERRED_TARGET and target in context["live"]:
        risk += 1
        reasons.append(f"cannibalisation -1: refresh {cluster['target_url']} rather than add a page: it is live and "
                       "GSC gives it this cluster's impressions [measured: GSC + crawl]")
    head = cluster["head_keyword"]
    titled = [row["url"] for row in context["live_pages"].get(cluster["locale"], [])
              if head and head in row["title"].lower() and url_key(row["url"]) != target]
    if titled:
        risk += 1
        reasons.append(f"cannibalisation -1: live page {titled[0]} has the head keyword in its title [measured: crawl]")
    return min(risk, 3)


def score_cluster(store: Store, cluster: dict, context: dict) -> dict:
    """The next-topics priority [heuristic, not a Google metric], with the reason for every point."""
    locale, head = cluster["locale"], cluster["head_keyword"]
    records = [store.keywords[(locale, k)] for k in cluster["keywords"] if (locale, k) in store.keywords]
    serp = store.serp(locale, head)
    reasons: list[str] = []
    scores = {"intent_fit": score_intent_fit(store.keywords.get((locale, head)), serp, reasons),
              "demand": score_demand(records, reasons),
              "serp_gap": score_serp_gap(serp, reasons),
              "cannibalisation": score_cannibalisation(store, cluster, records, serp, context, reasons)}
    return {"priority": scores["intent_fit"] + scores["demand"] + scores["serp_gap"] - scores["cannibalisation"],
            "scores": scores, "reasons": reasons, "paa": (serp or {}).get("paa") or [],
            "evidence": {"gsc_impressions": sum(r["demand"]["gsc_impressions"] or 0 for r in records),
                         "volume": sum(volume_number(r["demand"]["volume"]) for r in records)}}


# ---------------------------------------------------------------- commands

def keyword_gap(records: list[dict]) -> dict:
    """A count, and up to 50 of the keywords, strongest demand first."""
    return {"count": len(records), "keywords": [r["keyword"] for r in sorted(records, key=demand_rank,
                                                                             reverse=True)[:50]]}


def url_gap(rows: list[dict]) -> dict:
    return {"count": len(rows), "urls": sorted(row["url"] for row in rows)[:50]}


def older_than(at: str | None, ttl: int | None, now: str) -> bool:
    return bool(at) and ttl is not None and age_days(at, now) > ttl


def status(store: Store, args, now: str) -> dict:
    datasets, stale, missing = {}, [], []
    for name in TTL_DAYS:
        entry = store.manifest["datasets"].get(name)
        ttl = store.dataset_ttl(name)
        per_locale = {}
        for locale in store.locales:
            at = store.dataset_date(name, locale)
            if at is None:
                missing.append({"dataset": name, "locale": locale})
                continue
            age = age_days(at, now)
            per_locale[locale] = {"updated_at": at, "age_days": age, "stale": ttl is not None and age > ttl}
            if per_locale[locale]["stale"]:
                stale.append({"dataset": name, "locale": locale, "updated_at": at, "age_days": age, "ttl_days": ttl})
        datasets[name] = {**entry, "locales": per_locale} if entry else None
    ttl = {name: store.dataset_ttl(name) for name in ("serps", "volumes", "gsc", "inventory")}
    covered = post_clusters(store)
    gaps = {}
    for locale in store.locales:
        records = [r for (code, _), r in sorted(store.keywords.items()) if code == locale]
        active = [r for r in records if r["status"] != "skip"]
        needs_serp = []
        for record in active:
            snapshot = store.serp(locale, record["keyword"])
            if not snapshot or age_days(snapshot["fetched_at"], now) > ttl["serps"]:
                needs_serp.append(record)
        clusters = [c for c in store.clusters.values() if c["locale"] == locale]
        pages = [row for row in store.inventory.values() if row["locale"] == locale]
        posts = [key for key, post in store.posts.items() if post["locale"] == locale]
        # Per record: a refresh of a few rows makes the dataset's newest date fresh, not the rest of its rows
        gaps[locale] = {
            "keywords": len(records),
            "unclustered": sum(r["cluster_id"] is None for r in active),
            "without_volume": sum(r["demand"]["volume"] is None for r in active),
            "without_gsc": sum(r["demand"]["gsc_impressions"] is None for r in active),
            "needs_serp": keyword_gap(needs_serp),
            "stale_volumes": keyword_gap([r for r in active if r["demand"]["volume"] is not None and older_than(
                (r["provenance"].get("demand.volume") or {}).get("at"), ttl["volumes"], now)]),
            "stale_gsc": keyword_gap([r for r in active if r["demand"]["gsc_impressions"] is not None and older_than(
                (r["provenance"].get("demand.gsc_impressions") or {}).get("at"), ttl["gsc"], now)]),
            "stale_gsc_pages": url_gap([row for row in pages if older_than(row["gsc_at"], ttl["gsc"], now)]),
            "stale_inventory": url_gap([row for row in pages if older_than(row["crawled_at"], ttl["inventory"], now)]),
            "posts": {"count": len(posts), "without_cluster": sum(not covered[key] for key in posts)},
            "clusters": len(clusters),
            "empty_clusters": sum(not c["keywords"] for c in clusters),
            "clusters_without_target": sum(not c["target_url"] for c in clusters
                                           if c["keywords"] and c["status"] != "skip"),
            "published_clusters": sum(c["status"] == "published" for c in clusters),
            "briefs": len(glob.glob(store.file("briefs", locale, "*.md"))),
            "glossary_terms": len(read_json(store.file("glossary", f"{locale}.json"), {})),
        }
    return {"store": store.dir, "site": store.site["site"], "locales": store.locales, "checked_at": now,
            "datasets": datasets, "stale": stale, "missing": missing, "gaps": gaps,
            "note": "Reuse fresh data, refresh only what is stale or missing, and say in Assumptions what was reused "
                    "and how old it was."}


def next_topics(store: Store, args, now: str) -> dict:
    locale = store.check_locale(args.locale) if args.locale else None
    context, topics, excluded, covered = scoring_context(store), [], Counter(), []
    posts_of = defaultdict(list)
    for key, cluster_ids in sorted(post_clusters(store).items()):
        for cluster_id in cluster_ids:
            posts_of[cluster_id].append(store.posts[key]["url"] or store.posts[key]["slug"])
    slugs = brief_slugs(store)
    for cluster in (store.clusters[c] for c in sorted(store.clusters)):
        if locale and cluster["locale"] != locale:
            continue
        if not cluster["keywords"]:
            excluded["empty"] += 1
        elif cluster["status"] in ("scheduled", "published", "skip"):
            excluded[cluster["status"]] += 1
        elif posts_of[cluster["cluster_id"]]:
            excluded["post"] += 1
            covered.append({"cluster_id": cluster["cluster_id"], "head_keyword": cluster["head_keyword"],
                            "posts": posts_of[cluster["cluster_id"]]})
        elif (cluster.get("target_source") != GSC_INFERRED_TARGET
              and url_key(cluster["target_url"]) in context["live"]):
            excluded["live_target"] += 1  # a declared target that is live: a refresh, not a new topic
        else:
            score = score_cluster(store, cluster, context)
            slug = slugs[cluster["cluster_id"]]
            topics.append({
                **{k: cluster[k] for k in ("cluster_id", "locale", "head_keyword", "keywords", "role", "status",
                                           "target_url")},
                **{k: score[k] for k in ("priority", "scores", "evidence", "reasons", "paa")},
                "interlinks": [{k: store.clusters[c][k] for k in ("cluster_id", "head_keyword", "target_url", "status")}
                               for c in cluster["interlinks"]],
                "brief": f"briefs/{cluster['locale']}/{slug}.md",
                "brief_exists": os.path.exists(store.file("briefs", cluster["locale"], f"{slug}.md")),
            })
    topics.sort(key=lambda t: (-t["priority"], -t["evidence"]["gsc_impressions"], -t["evidence"]["volume"],
                               -len(t["keywords"]), t["cluster_id"]))
    return {"heuristic": HEURISTIC, "locale": locale, "candidates": len(topics), "topics": topics[:args.limit],
            "excluded": dict(sorted(excluded.items())), "covered_by_posts": covered}


def brief_slugs(store: Store) -> dict[str, str]:
    """Each cluster's brief file name: its brief_slug once it has left planned, so a brief written where next-topics
    said stays found whatever other heads do. Otherwise the slug of its head keyword, with the cluster id appended
    when a frozen name or an earlier cluster of the locale has that slug ("c tutor" and "c++ tutor" are both
    c-tutor)."""
    used = {(c["locale"], c["brief_slug"]) for c in store.clusters.values() if c["brief_slug"]}
    slugs = {}
    for cluster_id in sorted(store.clusters):
        cluster = store.clusters[cluster_id]
        if cluster["brief_slug"]:
            slugs[cluster_id] = cluster["brief_slug"]
            continue
        slug = slugify(cluster["head_keyword"] or "")
        if (cluster["locale"], slug) in used:
            slug = f"{slug}-{cluster_id}"
        used.add((cluster["locale"], slug))
        slugs[cluster_id] = slug
    return slugs


def set_status(store: Store, args, now: str) -> dict:
    url = normalize_url(args.url) if args.url else None
    if args.cluster:
        cluster = store.clusters.get(args.cluster)
        if not cluster:
            raise SystemExit(f"no cluster {args.cluster!r} in {store.dir}")
        previous, cluster["status"] = cluster["status"], args.status
        if url:
            cluster["target_url"], cluster["target_source"] = url, "set-status"
        updated = 0
        for keyword in cluster["keywords"]:  # keywords that shared the cluster's old status follow it
            record = store.keywords.get((cluster["locale"], keyword))
            if record and record["status"] == previous:
                updated += apply(record, {"status": args.status, "target_url": url}, "set-status", now, now)
        return {"updated": "cluster", "cluster": cluster, "keywords_updated": updated}
    if not args.locale:
        raise SystemExit("--keyword needs --locale")
    keyword = clean_keyword(args.keyword)
    record = store.keywords.get((store.check_locale(args.locale), keyword))
    if not record:
        raise SystemExit(f"no keyword {keyword!r} in locale {args.locale} in {store.dir}")
    apply(record, {"status": args.status, "target_url": url}, "set-status", now, now)
    return {"updated": "keyword", "keyword": record}


def glossary_add(store: Store, args, now: str) -> dict:
    locale = store.check_locale(args.locale)
    path = store.file("glossary", f"{locale}.json")
    terms = read_json(path, {})
    term = args.term.strip()
    entry = terms.get(term, {"translation": "", "note": "", "do_not_translate": False})
    entry["translation"] = args.translation
    if args.note is not None:
        entry["note"] = args.note
    if args.do_not_translate:
        entry["do_not_translate"] = True
    terms[term] = entry
    write_atomic(path, dump_json(terms))
    store.touch("glossary", locale, "glossary add", now)
    return {"locale": locale, "term": term, **entry}


def glossary_show(store: Store, args, now: str) -> dict:
    locale = store.check_locale(args.locale)
    return {"locale": locale, "terms": read_json(store.file("glossary", f"{locale}.json"), {})}


def export(store: Store, args, now: str) -> list | None:
    locale = store.check_locale(args.locale) if args.locale else None
    if args.dataset == "keywords":
        rows, columns = [r for _, r in sorted(store.keywords.items())], KEYWORD_COLUMNS
    elif args.dataset == "clusters":
        rows, columns = [store.clusters[c] for c in sorted(store.clusters)], CLUSTER_COLUMNS
    elif args.dataset == "posts":
        rows, columns = sorted_posts(store.posts.values()), POST_COLUMNS
    else:
        rows, columns = sorted(store.inventory.values(), key=lambda r: (r["locale"], r["url"])), INVENTORY_COLUMNS
    rows = [r for r in rows if locale in (None, r["locale"])]
    if args.format == "json":
        return rows
    sys.stdout.write(csv_text(columns, [flat_row(r, columns) for r in rows]))
    return None


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dir", default=DEFAULT_DIR, help="store folder (default seo-research)")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = ap.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", parents=[common], help="create the store, or add locales to it")
    init.add_argument("--site", required=True, help="the site's home URL")
    init.add_argument("--locales", type=locale_list, help="comma list, default locale first, e.g. en,ka,ru")

    ingest = commands.add_parser("ingest", help="merge a script's output or an export into the store")
    kinds = ingest.add_subparsers(dest="kind", required=True)
    for name, run, help_text in (
            ("keyword-ideas", ingest_keyword_ideas, "keyword_ideas.py JSON"),
            ("serps", ingest_serps, "serps.json {keyword: [top urls]}"),
            ("clusters", ingest_clusters, "serp_cluster.py JSON"),
            ("gsc", ingest_gsc, "gsc_analyze.py JSON, or a GSC Queries/Pages/query+page CSV"),
            ("crawl", ingest_crawl, "crawl.py --csv pages.csv"),
            ("volumes", ingest_volumes, "CSV keyword,volume[,difficulty] from a vendor export"),
            ("posts", ingest_posts, "CMS posts export, CSV or JSON: url or slug, locale, title, status, publish_date")):
        kind = kinds.add_parser(name, parents=[common], help=help_text)
        kind.add_argument("file")
        kind.add_argument("--as-of", type=as_of_date, help="the last day the data covers, YYYY-MM-DD (default: the "
                                                           "file's modification time)")
        kind.set_defaults(run=run, writes=True)
        if name in ("keyword-ideas", "serps", "clusters", "volumes"):
            kind.add_argument("--locale", type=locale_code, required=True)
        elif name == "gsc":
            kind.add_argument("--locale", type=locale_code, help="locale of all the queries, overriding their page "
                                                                 "URLs; for a Queries.csv without pages")
        elif name == "posts":
            kind.add_argument("--locale", type=locale_code, help="locale of rows with neither a locale nor a URL")
        if name == "serps":
            kind.add_argument("--details", help="JSON {keyword: {results: [{url, title, type}], features, paa, "
                                                "intent}}")
        if name == "volumes":
            kind.add_argument("--source", required=True, help="vendor name, e.g. semrush, ahrefs, keyword-planner")

    commands.add_parser("status", parents=[common], help="datasets, ages, stale and missing data, gaps per locale"
                        ).set_defaults(run=status, writes=False)
    topics = commands.add_parser("next-topics", parents=[common], help="clusters to write next, with reasons")
    topics.add_argument("--locale", type=locale_code)
    topics.add_argument("--limit", type=positive_int, default=10)
    topics.set_defaults(run=next_topics, writes=False)

    mark = commands.add_parser("set-status", parents=[common], help="move a cluster or keyword along the pipeline")
    which = mark.add_mutually_exclusive_group(required=True)
    which.add_argument("--cluster")
    which.add_argument("--keyword")
    mark.add_argument("--locale", type=locale_code, help="with --keyword")
    mark.add_argument("--status", required=True, choices=STATUSES)
    mark.add_argument("--url", help="the page that targets it")
    mark.set_defaults(run=set_status, writes=True)

    glossary = commands.add_parser("glossary", help="approved translations per locale")
    actions = glossary.add_subparsers(dest="action", required=True)
    add = actions.add_parser("add", parents=[common])
    add.add_argument("--locale", type=locale_code, required=True)
    add.add_argument("--term", required=True)
    add.add_argument("--translation", required=True)
    add.add_argument("--do-not-translate", action="store_true")
    add.add_argument("--note")
    add.set_defaults(run=glossary_add, writes=True)
    show = actions.add_parser("show", parents=[common])
    show.add_argument("--locale", type=locale_code, required=True)
    show.set_defaults(run=glossary_show, writes=False)

    out = commands.add_parser("export", parents=[common], help="keywords, clusters, inventory or posts as CSV or JSON")
    out.add_argument("dataset", choices=("keywords", "clusters", "inventory", "posts"))
    out.add_argument("--locale", type=locale_code)
    out.add_argument("--format", required=True, choices=("csv", "json"))
    out.set_defaults(run=export, writes=False)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    now = now_utc()
    if args.command == "init":
        print_json(init_store(args.dir, args.site, args.locales, now))
        return 0
    if not os.path.exists(os.path.join(args.dir, "site.json")):
        raise SystemExit(f"{args.dir}: no research store here. Create it: research_store.py init --site URL "
                         f"--dir {args.dir}")
    with locked(args.dir):
        store = Store(args.dir)
        result = args.run(store, args, now)
        if args.writes:
            store.save(now)
    if result is not None:
        print_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
