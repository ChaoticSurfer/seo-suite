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
  research_store.py status
  research_store.py next-topics [--locale en] [--limit 10]
  research_store.py set-status --cluster en-001 --status briefed
  research_store.py set-status --keyword "english tutor" --locale en --status published --url https://example.com/x/
  research_store.py glossary add --locale ka --term Claude --translation Claude --do-not-translate
  research_store.py glossary show --locale ka
  research_store.py export keywords|clusters|inventory [--locale en] --format csv|json
Every command takes --dir DIR (default seo-research). Output is JSON on stdout; export --format csv prints CSV.
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
STATUSES = ("planned", "briefed", "drafted", "published", "skip")
ROLES = ("pillar", "cluster", "support")
# Days before a dataset is stale. Clusters and glossaries are decisions, not observations, so they never go stale.
TTL_DAYS = {"keywords": 90, "volumes": 30, "serps": 30, "gsc": 7, "inventory": 30, "competitors": 90,
            "clusters": None, "glossary": None}
INVENTORY_COLUMNS = ["url", "locale", "title", "cluster_id", "words", "last_modified", "status", "gsc_clicks",
                     "gsc_impressions"]
INVENTORY_NUMBERS = ("words", "status", "gsc_clicks", "gsc_impressions")
KEYWORD_COLUMNS = ["keyword", "locale", "intent", "cluster_id", "status", "target_url", "autocomplete_sources",
                   "gsc_impressions", "gsc_position", "gsc_pages", "volume", "volume_source", "volume_date",
                   "difficulty", "difficulty_source", "serp_features", "notes", "first_seen", "updated_at"]
CLUSTER_COLUMNS = ["cluster_id", "locale", "head_keyword", "keywords", "role", "target_url", "interlinks", "priority",
                   "status"]
VOLUME_HEADERS = {  # Semrush, Ahrefs, DataForSEO and Keyword Planner export names
    "keyword": {"keyword", "keywords", "query", "phrase", "search term"},
    "volume": {"volume", "search volume", "search_volume", "avg. monthly searches", "avg monthly searches"},
    "difficulty": {"difficulty", "keyword difficulty", "keyword_difficulty", "kd"},
}
GSC_MIN_IMPRESSIONS = 10  # below this a GSC query is too thin to count as demand or to be added as a new keyword
COMPETING_PAGE_SHARE = 0.1  # as in gsc_analyze.cannibalization: a page with >=10% of a query's impressions competes
PERSONAL_DATA = re.compile(r"[\w.+-]+@[\w-]+\.\w|\+?\d{3}[\s.-]?\d{3}[\s.-]?\d{3,4}")  # e-mail address, phone number
INTENT_GUESS = "keyword_ideas"  # source label of keyword_ideas.classify_intent, the wording-based intent guess
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


def age_days(at: str, now: str) -> float:
    return round((dt.datetime.fromisoformat(now) - dt.datetime.fromisoformat(at)).total_seconds() / 86400, 1)


def locale_code(value: str) -> str:
    code = value.strip().lower().replace("_", "-")
    if not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]{2,8})*", code):
        raise argparse.ArgumentTypeError(f"not a locale code: {value!r} (use en, ka, ru-ge …)")
    return code


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
    """A number, or the text as written when it is a range (Keyword Planner without ad spend: "1K – 10K")."""
    cell = cell.strip()
    plain = re.sub(r"[,\s  ]", "", cell)
    if re.fullmatch(r"\d+(\.\d+)?", plain):
        return round(float(plain))
    return cell or None


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


def read_inventory(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return [{k: to_int(v) if k in INVENTORY_NUMBERS else v for k, v in row.items()} for row in csv.DictReader(fh)]


def read_table(path: str, headers: dict[str, set[str]]) -> tuple[list[dict], set[str]]:
    """Rows of a CSV or TSV export renamed to canonical columns. Reads UTF-16 files and skips title rows above the
    header (Keyword Planner writes both)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-16") if raw[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE) else raw.decode("utf-8-sig")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        delimiter = "\t" if "\t" in line else ","
        names = [cell.strip().lower() for cell in next(csv.reader([line], delimiter=delimiter), [])]
        mapping = {i: canonical for i, name in enumerate(names)
                   for canonical, aliases in headers.items() if name in aliases}
        if "keyword" in mapping.values():
            rows = [{mapping[i]: cell for i, cell in enumerate(cells) if i in mapping}
                    for cells in csv.reader(lines[index + 1:], delimiter=delimiter) if any(c.strip() for c in cells)]
            return rows, set(mapping.values())
    raise SystemExit(f"{path}: no keyword column found (expected one of {sorted(headers['keyword'])})")


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
    known = record["provenance"].get("intent")
    if source == INTENT_GUESS and known and known["source"] != INTENT_GUESS:
        return False  # an intent read from the live SERP is never replaced by the wording-based guess
    return set_field(record, "intent", intent, source, at)


def add_autocomplete_sources(record: dict, sources: list[str], at: str) -> bool:
    """Demand evidence accumulates: engines that suggested the keyword are added, never removed."""
    merged = sorted(set(record["demand"]["autocomplete_sources"]) | set(sources))
    if merged == record["demand"]["autocomplete_sources"]:
        return False
    known = record["provenance"].get("demand.autocomplete_sources")
    record["demand"]["autocomplete_sources"] = merged
    record["provenance"]["demand.autocomplete_sources"] = {"source": "keyword_ideas",
                                                           "at": max(at, known["at"]) if known else at}
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
    if PERSONAL_DATA.search(keyword):
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
        self.inventory = {row["url"]: row for row in read_inventory(self.file("inventory.csv"))}

    def file(self, *parts: str) -> str:
        return os.path.join(self.dir, *parts)

    @property
    def locales(self) -> list[str]:
        return self.site["locales"]

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
        """The record for keyword+locale, created with the wording-based intent guess when new."""
        record = self.keywords.get((locale, keyword))
        if record:
            record["first_seen"] = min(record["first_seen"], at)
            return record, False
        record = self.keywords[(locale, keyword)] = new_keyword(keyword, locale, at, now)
        set_intent(record, classify_intent(keyword), INTENT_GUESS, at)
        return record, True

    def inventory_row(self, url: str) -> dict:
        if url not in self.inventory:
            self.inventory[url] = {"url": url, "locale": self.locale_of_url(url), "title": "", "cluster_id": "",
                                   "words": None, "last_modified": "", "status": None, "gsc_clicks": None,
                                   "gsc_impressions": None}
        return self.inventory[url]

    def serp_file(self, locale: str, keyword: str) -> str:
        return self.file("serps", locale, hashlib.sha1(keyword.encode("utf-8")).hexdigest() + ".json")

    def serp(self, locale: str, keyword: str | None) -> dict | None:
        return read_json(self.serp_file(locale, keyword), None) if keyword else None

    def serp_files(self) -> list[str]:
        return sorted(glob.glob(self.file("serps", "*", "*.json")))

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

    def refresh_competitors(self) -> None:
        """Domains in the stored top-10s, minus the site itself. A domain no longer seen keeps its entry with 0."""
        seen: dict[str, dict] = {}
        for path in self.serp_files():
            snapshot = read_json(path)
            for domain in {registrable_host(r["url"]) for r in snapshot["results"]} - {self.site["domain"], ""}:
                entry = seen.setdefault(domain, {"locales": set(), "keywords_shared": 0, "last_seen": ""})
                entry["locales"].add(snapshot["locale"])
                entry["keywords_shared"] += 1
                entry["last_seen"] = max(entry["last_seen"], snapshot["fetched_at"])
        for domain, old in self.competitors.items():
            if domain not in seen:
                old["keywords_shared"] = 0
        for domain, entry in seen.items():
            old_locales = set(self.competitors.get(domain, {}).get("locales", []))
            self.competitors[domain] = {"domain": domain, "locales": sorted(entry["locales"] | old_locales),
                                        "keywords_shared": entry["keywords_shared"], "last_seen": entry["last_seen"]}

    def record_counts(self) -> dict[str, int]:
        records = list(self.keywords.values())
        return {
            "keywords": len(records),
            "volumes": sum(r["demand"]["volume"] is not None for r in records),
            "serps": len(self.serp_files()),
            "clusters": len(self.clusters),
            "gsc": sum(r["demand"]["gsc_impressions"] is not None for r in records)
                   + sum(row["gsc_impressions"] is not None for row in self.inventory.values()),
            "inventory": len(self.inventory),
            "competitors": len(self.competitors),
            "glossary": sum(len(read_json(path)) for path in glob.glob(self.file("glossary", "*.json"))),
        }

    def save(self, now: str) -> None:
        context = scoring_context(self)
        for cluster in self.clusters.values():
            cluster["priority"] = score_cluster(self, cluster, context)["priority"]
        for row in self.inventory.values():
            row["cluster_id"] = ";".join(context["targets"].get(url_key(row["url"]), []))
        keyword_lines = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                         for _, record in sorted(self.keywords.items()))
        inventory = sorted(self.inventory.values(), key=lambda row: (row["locale"], row["url"]))
        write_atomic(self.file("site.json"), dump_json(self.site))
        write_atomic(self.file("keywords.jsonl"), "".join(keyword_lines))
        write_atomic(self.file("clusters.json"), dump_json([self.clusters[c] for c in sorted(self.clusters)]))
        write_atomic(self.file("competitors.json"), dump_json([self.competitors[d] for d in sorted(self.competitors)]))
        write_atomic(self.file("inventory.csv"), csv_text(INVENTORY_COLUMNS, inventory))
        counts = self.record_counts()
        for name, entry in self.manifest["datasets"].items():
            entry["records"] = counts[name]
        write_atomic(self.file("manifest.json"), dump_json(self.manifest))


def init_store(directory: str, site_url: str, locales: str | None, now: str) -> dict:
    parts = urllib.parse.urlsplit(site_url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise SystemExit(f"--site must be an http(s) URL, got {site_url!r}")
    given = [locale_code(code) for code in (locales or "").split(",") if code.strip()]
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
    if not isinstance(data, dict) or "keywords" not in data or "locale" not in data:
        raise SystemExit(f"{args.file}: not keyword_ideas.py output (needs 'keywords' and 'locale')")
    locale = store.check_locale(args.locale)
    hl, _, gl = data["locale"].lower().partition("-")
    if hl != locale.split("-")[0]:
        raise SystemExit(f"{args.file} was fetched with --hl {hl}, which is not the language of locale {locale}")
    market = store.site["markets"].setdefault(locale, {})
    market.setdefault("hl", hl)
    market.setdefault("gl", gl)
    at, counts = observed_at(args.file), Counter()
    for item in data["keywords"]:
        keyword = usable_keyword(item["keyword"], counts)
        if not keyword:
            continue
        record, created = store.keyword(keyword, locale, at, now)
        changed = set_intent(record, item.get("intent"), INTENT_GUESS, at)
        changed |= add_autocomplete_sources(record, item.get("sources", []), at)
        if changed:
            record["updated_at"] = now
        tally(counts, created, changed)
    store.touch("keywords", locale, "keyword_ideas", at)
    return summary("keyword-ideas", args.file, locale, at, counts)


def ingest_serps(store: Store, args, now: str) -> dict:
    serps = read_json(args.file)
    if not isinstance(serps, dict) or not all(isinstance(v, list) for v in serps.values()):
        raise SystemExit(f"{args.file}: expected serps.json shaped {{\"keyword\": [\"top1 url\", …]}}")
    details = read_json(args.details) if args.details else {}
    if not isinstance(details, dict):
        raise SystemExit(f"{args.details}: expected {{\"keyword\": {{\"results\": […], \"features\": […], "
                         f"\"paa\": […]}}}}")
    details = {clean_keyword(k): v for k, v in details.items()}
    locale = store.check_locale(args.locale)
    at, counts = observed_at(args.file), Counter()
    for raw_keyword, urls in serps.items():
        keyword = usable_keyword(raw_keyword, counts)
        if not keyword:
            continue
        old = store.serp(locale, keyword) or {}
        if old.get("fetched_at", "") > at:
            counts["kept_newer"] += 1
            continue
        detail = details.get(keyword, {})
        described = {normalize_url(r["url"]): r for r in detail.get("results", [])}
        before = {r["url"]: r for r in old.get("results", [])}
        results = []
        for url in (normalize_url(u) for u in urls[:10]):
            known = described.get(url) or before.get(url) or {}
            results.append({"url": url, "title": known.get("title", ""),
                            "type": (known.get("type") or known.get("page_type") or "").lower()})
        features = (sorted({re.sub(r"[^a-z0-9]+", "_", f.lower()).strip("_") for f in detail["features"]})
                    if "features" in detail else old.get("features", []))
        snapshot = {"keyword": keyword, "locale": locale, "fetched_at": at, "results": results, "features": features,
                    "paa": detail.get("paa", old.get("paa", []))}
        write_atomic(store.serp_file(locale, keyword), dump_json(snapshot))
        record, created = store.keyword(keyword, locale, at, now)
        changed = set_field(record, "serp_features", features, "serps", at)
        changed |= set_intent(record, (detail.get("intent") or "").lower() or None, "serp", at)
        if changed:
            record["updated_at"] = now
        tally(counts, created, changed)
    store.touch("serps", locale, "serps", at)
    store.refresh_competitors()
    store.touch("competitors", locale, "serps", at)
    return summary("serps", args.file, locale, at, counts)


def best_keyword(store: Store, locale: str, keywords: list[str]) -> str:
    """Head term: the strongest demand evidence, then the broadest (shortest) phrase, then alphabetical."""
    return max(sorted(keywords), key=lambda k: (demand_rank(store.keywords[(locale, k)]), -len(k)))


def ingest_clusters(store: Store, args, now: str) -> dict:
    data = read_json(args.file)
    if not isinstance(data, dict) or "clusters" not in data:
        raise SystemExit(f"{args.file}: not serp_cluster.py output (needs 'clusters')")
    locale = store.check_locale(args.locale)
    at, counts = observed_at(args.file), Counter()
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
            "cluster_id": cluster_id, "locale": locale, "head_keyword": None, "keywords": [], "role": "cluster",
            "target_url": None, "interlinks": [], "priority": 0, "status": "planned"})
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
        if group.get("target_url"):
            cluster["target_url"] = normalize_url(group["target_url"])
        elif not cluster["target_url"]:
            targets = Counter(store.keywords[(locale, k)]["target_url"] for k in cluster["keywords"]
                              if store.keywords[(locale, k)]["target_url"])
            cluster["target_url"] = targets.most_common(1)[0][0] if targets else None
        head = clean_keyword(group.get("head_keyword") or "")
        if head:
            if head not in cluster["keywords"]:
                raise SystemExit(f"{args.file}: head_keyword {head!r} is not in its cluster's keywords")
            cluster["head_keyword"] = head
        elif cluster["status"] == "planned" or cluster["head_keyword"] not in cluster["keywords"]:
            cluster["head_keyword"] = best_keyword(store, locale, cluster["keywords"])
    for link in data.get("interlink_clusters", []):
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
    rows: dict[str, dict] = {}
    for name in ("striking_distance", "ctr_underperformers", "question_queries"):
        for row in data.get(name, []):
            rows.setdefault(key_of(row), row)
    for item in data.get("cannibalization", []):
        for page in item["pages"]:
            row = {"query": item["query"], "page": page["page"], "clicks": page["clicks"],
                   "impressions": round(page["share"] * item["impressions"]), "position": page["position"]}
            rows.setdefault(key_of(row), row)
    return list(rows.values())


def ingest_gsc(store: Store, args, now: str) -> dict:
    rows = gsc_rows_from_report(args.file) if args.file.endswith(".json") else load_rows(args.file)
    locale = store.check_locale(args.locale) if args.locale else None
    if not locale and any("query" in r and "page" not in r for r in rows):
        if len(store.locales) > 1:
            raise SystemExit(f"{args.file} has queries without pages, so their locale is unknown: pass --locale")
        locale = store.locales[0]
    at, counts, touched = observed_at(args.file), Counter(), set()
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
        if (query_locale, query) not in store.keywords and impressions < GSC_MIN_IMPRESSIONS:
            counts["skipped_below_min_impressions"] += 1
            continue
        position = (sum(r["position"] * r["impressions"] for r in items) / impressions if impressions
                    else sum(r["position"] for r in items) / len(items))
        pages = [normalize_url(r["page"]) for r in sorted(items, key=lambda r: -r["impressions"])
                 if "page" in r and impressions and r["impressions"] / impressions >= COMPETING_PAGE_SHARE]
        record, created = store.keyword(query, query_locale, at, now)
        has_pages = any("page" in r for r in items)
        changed = apply(record, {"demand.gsc_impressions": round(impressions),
                                 "demand.gsc_position": round(position, 1),
                                 "demand.gsc_pages": pages if has_pages else None}, "gsc", at, now)
        if pages and not record["target_url"]:
            changed |= apply(record, {"target_url": pages[0]}, "gsc", at, now)
        tally(counts, created, changed)
        touched.add(query_locale)
    for url, (clicks, impressions) in sorted(by_page.items()):
        known = url in store.inventory and store.inventory[url]["gsc_impressions"] is not None
        row = store.inventory_row(url)
        if known and (store.dataset_date("gsc", row["locale"]) or "") > at:
            counts["pages_kept_newer"] += 1
            continue
        row["gsc_clicks"], row["gsc_impressions"] = round(clicks), round(impressions)
        counts["pages"] += 1
        touched.add(row["locale"])
    for code in sorted(touched):
        store.touch("gsc", code, "gsc", at)
    return summary("gsc", args.file, locale, at, counts)


def ingest_crawl(store: Store, args, now: str) -> dict:
    at, counts, touched = observed_at(args.file), Counter(), set()
    with open(args.file, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"url", "status", "title", "word_count"} - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{args.file}: not a crawl.py --csv file (missing {sorted(missing)})")
        for raw in reader:
            url = normalize_url(raw["url"])
            known = url in store.inventory and store.inventory[url]["status"] is not None
            row = store.inventory_row(url)
            if known and (store.dataset_date("inventory", row["locale"]) or "") > at:
                counts["kept_newer"] += 1
                continue
            row.update(title=raw["title"], words=to_int(raw["word_count"]), status=to_int(raw["status"]))
            modified = raw.get("last_modified") or raw.get("lastmod")  # CMS or Screaming Frog exports carry one
            if modified:
                row["last_modified"] = modified
            counts["pages"] += 1
            touched.add(row["locale"])
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
    at, counts = observed_at(args.file), Counter()
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
    if "ai_overview" in serp["features"]:
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
           if registrable_host(r["url"]) == store.site["domain"] and url_key(r["url"]) != target]
    if own:
        risk += 1
        reasons.append(f"cannibalisation -1: the site already ranks in the top 10 with {own[0]} [measured: SERP]")
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
            "scores": scores, "reasons": reasons, "paa": (serp or {}).get("paa", []),
            "evidence": {"gsc_impressions": sum(r["demand"]["gsc_impressions"] or 0 for r in records),
                         "volume": sum(volume_number(r["demand"]["volume"]) for r in records)}}


# ---------------------------------------------------------------- commands

def status(store: Store, args, now: str) -> dict:
    datasets, stale, missing = {}, [], []
    for name in TTL_DAYS:
        entry = store.manifest["datasets"].get(name)
        ttl = entry["ttl_days"] if entry else TTL_DAYS[name]
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
    serp_ttl = (store.manifest["datasets"].get("serps") or {}).get("ttl_days", TTL_DAYS["serps"])
    gaps = {}
    for locale in store.locales:
        records = [r for (code, _), r in sorted(store.keywords.items()) if code == locale]
        active = [r for r in records if r["status"] != "skip"]
        needs_serp = []
        for record in active:
            snapshot = store.serp(locale, record["keyword"])
            if not snapshot or age_days(snapshot["fetched_at"], now) > serp_ttl:
                needs_serp.append(record)
        clusters = [c for c in store.clusters.values() if c["locale"] == locale]
        gaps[locale] = {
            "keywords": len(records),
            "unclustered": sum(r["cluster_id"] is None for r in active),
            "without_volume": sum(r["demand"]["volume"] is None for r in active),
            "without_gsc": sum(r["demand"]["gsc_impressions"] is None for r in active),
            "needs_serp": {"count": len(needs_serp), "keywords": [r["keyword"] for r in sorted(
                needs_serp, key=demand_rank, reverse=True)[:50]]},
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
    context, topics, excluded = scoring_context(store), [], Counter()
    for cluster in (store.clusters[c] for c in sorted(store.clusters)):
        if locale and cluster["locale"] != locale:
            continue
        if not cluster["keywords"]:
            excluded["empty"] += 1
        elif cluster["status"] in ("published", "skip"):
            excluded[cluster["status"]] += 1
        elif url_key(cluster["target_url"]) in context["live"]:
            excluded["live_target"] += 1
        else:
            score = score_cluster(store, cluster, context)
            slug = slugify(cluster["head_keyword"])
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
            "excluded": dict(sorted(excluded.items()))}


def set_status(store: Store, args, now: str) -> dict:
    url = normalize_url(args.url) if args.url else None
    if args.cluster:
        cluster = store.clusters.get(args.cluster)
        if not cluster:
            raise SystemExit(f"no cluster {args.cluster!r} in {store.dir}")
        previous, cluster["status"] = cluster["status"], args.status
        cluster["target_url"] = url or cluster["target_url"]
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
    init.add_argument("--locales", help="comma list, default locale first, e.g. en,ka,ru")

    ingest = commands.add_parser("ingest", help="merge a script's output or an export into the store")
    kinds = ingest.add_subparsers(dest="kind", required=True)
    for name, run, help_text in (
            ("keyword-ideas", ingest_keyword_ideas, "keyword_ideas.py JSON"),
            ("serps", ingest_serps, "serps.json {keyword: [top urls]}"),
            ("clusters", ingest_clusters, "serp_cluster.py JSON"),
            ("gsc", ingest_gsc, "gsc_analyze.py JSON, or a GSC Queries/Pages/query+page CSV"),
            ("crawl", ingest_crawl, "crawl.py --csv pages.csv"),
            ("volumes", ingest_volumes, "CSV keyword,volume[,difficulty] from a vendor export")):
        kind = kinds.add_parser(name, parents=[common], help=help_text)
        kind.add_argument("file")
        kind.set_defaults(run=run, writes=True)
        if name in ("keyword-ideas", "serps", "clusters", "volumes"):
            kind.add_argument("--locale", type=locale_code, required=True)
        elif name == "gsc":
            kind.add_argument("--locale", type=locale_code, help="locale of the queries (default: from page URLs)")
        if name == "serps":
            kind.add_argument("--details", help="JSON {keyword: {results: [{url, title, type}], features, paa, "
                                                "intent}}")
        if name == "volumes":
            kind.add_argument("--source", required=True, help="vendor name, e.g. semrush, ahrefs, keyword-planner")

    commands.add_parser("status", parents=[common], help="datasets, ages, stale and missing data, gaps per locale"
                        ).set_defaults(run=status, writes=False)
    topics = commands.add_parser("next-topics", parents=[common], help="clusters to write next, with reasons")
    topics.add_argument("--locale", type=locale_code)
    topics.add_argument("--limit", type=int, default=10)
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

    out = commands.add_parser("export", parents=[common], help="keywords, clusters or inventory as CSV or JSON")
    out.add_argument("dataset", choices=("keywords", "clusters", "inventory"))
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
