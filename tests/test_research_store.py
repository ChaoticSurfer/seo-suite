"""Research store: init, every ingest format, merge provenance, TTL staleness, next-topics, set-status, glossary and
export. Inputs have the exact shapes keyword_ideas.py, serp_cluster.py, gsc_analyze.py and crawl.py write (the last
three are run for real here). Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import codecs
import contextlib
import csv
import datetime as dt
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import research_store as rs  # noqa: E402

DAY = 86400
NOTE = ("No search volume: autocomplete only proves the query is typed. Validate with GSC impressions / "
        "Keyword Planner / a paid tool.")

# keyword_ideas.py "english tutor" --hl en --gl gb --sources google,bing (real run 2026-10-24, trimmed), plus one
# suggestion shaped like personal data (an invalid, all-zero phone number) that must never reach the store.
KEYWORD_IDEAS_EN = {
    "seeds": ["english tutor"], "locale": "en-gb", "sources": ["google", "bing"], "total": 6,
    "intent_counts": {"unclear": 4, "transactional": 1, "informational": 1},
    "multi_source": ["english tutor", "english tutor near me", "english tutor jobs", "english tutor online"],
    "clusters": {"(head term)": ["english tutor"], "near": ["english tutor near me"], "jobs": ["english tutor jobs"],
                 "online": ["english tutor online"], "become": ["how to become an english tutor"],
                 "000": ["english tutor 000 000 0000"]},
    "keywords": [
        {"keyword": "english tutor", "sources": ["google", "bing"], "modifier": "seed", "intent": "unclear"},
        {"keyword": "english tutor near me", "sources": ["google", "bing"], "modifier": "seed", "intent": "transactional"},
        {"keyword": "english tutor jobs", "sources": ["google", "bing"], "modifier": "seed", "intent": "unclear"},
        {"keyword": "english tutor online", "sources": ["google", "bing"], "modifier": "seed", "intent": "unclear"},
        {"keyword": "how to become an english tutor", "sources": ["bing", "google"], "modifier": "how+",
         "intent": "informational"},
        {"keyword": "english tutor 000 000 0000", "sources": ["google"], "modifier": "+0", "intent": "unclear"},
    ],
    "note": NOTE,
}
# keyword_ideas.py "ინგლისური ენის კურსები" --hl ka --gl ge --sources google (real run 2026-10-24, trimmed)
KEYWORD_IDEAS_KA = {
    "seeds": ["ინგლისური ენის კურსები"], "locale": "ka-ge", "sources": ["google"], "total": 3,
    "intent_counts": {"unclear": 3}, "multi_source": [],
    "clusters": {"(head term)": ["ინგლისური ენის კურსები"], "ქუთაისში": ["ინგლისური ენის კურსები ქუთაისში"],
                 "ონლაინ": ["ინგლისური ენის კურსები ონლაინ"]},
    "keywords": [
        {"keyword": "ინგლისური ენის კურსები ქუთაისში", "sources": ["google"], "modifier": "seed", "intent": "unclear"},
        {"keyword": "ინგლისური ენის კურსები", "sources": ["google"], "modifier": "seed", "intent": "unclear"},
        {"keyword": "ინგლისური ენის კურსები ონლაინ", "sources": ["google"], "modifier": "seed", "intent": "unclear"},
    ],
    "note": NOTE,
}


def urls(*paths):
    return [f"https://{p}" for p in paths]


TUTOR_SITES = ["tutorhub.test/english", "learnly.test/tutors/english", "www.example.com/tutors/", "speakwell.test/",
               "lingo.test/english-tutors", "tutorfind.test/english", "classgap.test/en", "eduhire.test/tutor",
               "abc-tutors.test/", "langmatch.test/"]
# Handmade top-10s: "english tutor" and "english tutor online" share 5 URLs (one page), "near me" shares 2 with
# "english tutor" (interlink), "how to become…" is a forum-heavy SERP and "jobs" is unrelated.
SERPS_EN = {
    "english tutor": urls(*TUTOR_SITES),
    "english tutor online": urls(*TUTOR_SITES[:5], *[f"online{i}.test/" for i in range(5)]),
    "english tutor near me": urls(TUTOR_SITES[5], TUTOR_SITES[6], "www.example.com/blog/find-a-tutor/",
                                  *[f"local{i}.test/" for i in range(7)]),
    "how to become an english tutor": urls("www.reddit.com/r/TEFL/comments/abc/", "www.quora.com/How-to-tutor",
                                           *[f"guide{i}.test/become-a-tutor" for i in range(5)], "news.test/tutoring",
                                           "video.test/watch?v=1", "old.reddit.com/r/ESL/comments/def/"),
    "english tutor jobs": urls(*[f"jobs{i}.test/english-tutor" for i in range(10)]),
}
FORUM_TYPES = {"reddit": "forum/UGC", "quora": "forum/UGC", "guide": "guide/article", "news": "news", "video": "video"}
DETAILS_EN = {  # the seo-serp-researcher details shape: page type per result, features, PAA, dominant intent
    "how to become an english tutor": {
        "results": [{"url": u, "title": f"Result {i}",
                     "type": next(t for k, t in FORUM_TYPES.items() if k in u)}
                    for i, u in enumerate(SERPS_EN["how to become an english tutor"])],
        "features": ["People Also Ask", "Video"],
        "paa": ["Do you need a degree to be an English tutor?", "How much do English tutors earn?"],
        "intent": "informational"},
    "english tutor": {
        "results": [{"url": u, "title": f"Tutor {i}", "type": "service/landing" if i < 8 else "listicle"}
                    for i, u in enumerate(SERPS_EN["english tutor"])],
        "features": ["AI Overview", "Local pack"], "paa": [], "intent": "commercial"},
}
# A Search Console query+page export (API / Looker Studio columns)
GSC_QUERY_PAGE = """query,page,clicks,impressions,ctr,position
english tutor,https://example.com/tutors/,10,200,5%,8.2
english tutor,https://example.com/blog/find-a-tutor/,2,100,2%,15.0
english tutor online,https://example.com/tutors/,5,80,6.25%,9.1
ინგლისური ენის კურსები,https://example.com/ka/courses/,3,50,6%,12.0
english tutor 000 000 0000,https://example.com/tutors/,0,12,0%,30.0
rare english query,https://example.com/blog/find-a-tutor/,0,3,0%,40.0
"""
# crawl.py --csv header and rows
CRAWL_HEADER = ["url", "depth", "status", "final_url", "indexable", "title", "title_len", "description_len",
                "h1_count", "canonical", "word_count", "inlinks", "internal_outlinks", "schema_types", "download_ms",
                "issues"]
CRAWL_ROWS = [
    ["https://example.com/", 0, 200, "https://example.com/", True, "Example tutors", 14, 120, 1, "https://example.com/",
     450, 0, 12, "Organization", 120, ""],
    ["https://example.com/tutors/", 1, 200, "https://example.com/tutors/", True, "English tutor lessons | Example", 31,
     140, 1, "https://example.com/tutors/", 900, 5, 10, "Service", 130, ""],
    ["https://example.com/blog/find-a-tutor/", 2, 200, "https://example.com/blog/find-a-tutor/", True,
     "How to find an English tutor", 28, 150, 1, "https://example.com/blog/find-a-tutor/", 1200, 3, 9,
     "BlogPosting", 140, ""],
    ["https://example.com/ka/courses/", 1, 200, "https://example.com/ka/courses/", True, "ინგლისური ენის კურსები", 22,
     130, 1, "https://example.com/ka/courses/", 700, 2, 9, "", 150, ""],
    ["https://example.com/ru/", 1, 200, "https://example.com/ru/", True, "Репетитор английского", 21, 110, 1,
     "https://example.com/ru/", 500, 2, 9, "", 150, ""],
    ["https://example.com/old-page", 1, 301, "https://example.com/tutors/", False, "", 0, 0, 0, "", 0, 1, 0, "", 90,
     "redirect"],
]
SEMRUSH_VOLUMES = 'Keyword,Volume,Keyword Difficulty,CPC (USD)\nenglish tutor near me,"1,900",34,2.10\nenglish tutor,"2,400",61,3.05\n'


def run_script(name: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *args], capture_output=True, text=True,
                          timeout=60)


def run_in_process(directory: str, *args) -> str:
    """research_store.py's main() in this process, for a test that runs hundreds of commands; returns its stdout."""
    with mock.patch.object(sys, "argv", ["research_store.py", *args, "--dir", directory]), \
            contextlib.redirect_stdout(io.StringIO()) as out:
        rs.main()
    return out.getvalue()


def write_file(path: str, content, age_days: float = 0) -> str:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False))
    stamp = time.time() - age_days * DAY
    os.utime(path, (stamp, stamp))
    return path


def crawl_csv(rows=CRAWL_ROWS) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CRAWL_HEADER)
    writer.writerows(rows)
    return buffer.getvalue()


def crawl_row(url: str, status: int = 200, title: str = "A page") -> list:
    return [url, 1, status, url, status == 200, title, len(title), 100, 1, url, 500, 1, 5, "", 100, ""]


def days_ago(days: int) -> str:
    return (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=days)).isoformat()


def store_bytes(directory: str) -> dict[str, bytes]:
    files = {}
    for base, _, names in os.walk(directory):
        for name in names:
            if name != ".lock":
                with open(os.path.join(base, name), "rb") as fh:
                    files[os.path.relpath(os.path.join(base, name), directory)] = fh.read()
    return files


class StoreCase(unittest.TestCase):
    """A fresh copy of one store built through the whole pipeline: ideas (en, ka), volumes, GSC, SERPs, clusters,
    crawl, and the jobs cluster marked skip."""
    inputs: str
    base: str

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.inputs = cls.tmp.name
        cls.base = os.path.join(cls.inputs, "base-store")
        files = cls.files = {
            "ideas_en": write_file(os.path.join(cls.inputs, "kw-en.json"), KEYWORD_IDEAS_EN, age_days=10),
            "ideas_ka": write_file(os.path.join(cls.inputs, "kw-ka.json"), KEYWORD_IDEAS_KA),
            "semrush": write_file(os.path.join(cls.inputs, "semrush.csv"), SEMRUSH_VOLUMES, age_days=5),
            "gsc": write_file(os.path.join(cls.inputs, "gsc_query_page.csv"), GSC_QUERY_PAGE, age_days=10),
            "serps": write_file(os.path.join(cls.inputs, "serps.json"), SERPS_EN),
            "details": write_file(os.path.join(cls.inputs, "details.json"), DETAILS_EN),
            "crawl": write_file(os.path.join(cls.inputs, "pages.csv"), crawl_csv()),
        }
        clustered = run_script("serp_cluster.py", files["serps"])
        assert clustered.returncode == 0, clustered.stderr
        files["clusters"] = write_file(os.path.join(cls.inputs, "clusters.json"), clustered.stdout)
        cls.pipeline = [
            ["init", "--site", "https://example.com", "--locales", "en,ka,ru"],
            ["ingest", "keyword-ideas", files["ideas_en"], "--locale", "en"],
            ["ingest", "keyword-ideas", files["ideas_ka"], "--locale", "ka"],
            ["ingest", "volumes", files["semrush"], "--locale", "en", "--source", "semrush"],
            ["ingest", "gsc", files["gsc"]],
            ["ingest", "serps", files["serps"], "--locale", "en", "--details", files["details"]],
            ["ingest", "clusters", files["clusters"], "--locale", "en"],
            ["ingest", "crawl", files["crawl"]],
        ]
        cls.results = [cls.cli_in(cls.base, *step) for step in cls.pipeline]
        jobs = next(c for c in cls.load(cls.base).clusters.values() if c["head_keyword"] == "english tutor jobs")
        cls.cli_in(cls.base, "set-status", "--cluster", jobs["cluster_id"], "--status", "skip")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def cli_in(directory: str, *args):
        result = run_script("research_store.py", *args, "--dir", directory)
        assert result.returncode == 0, f"{args}: {result.stderr}"
        return json.loads(result.stdout) if result.stdout.lstrip().startswith(("{", "[")) else result.stdout

    @staticmethod
    def load(directory: str) -> rs.Store:
        return rs.Store(directory)

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.dir = os.path.join(self.work.name, "seo-research")
        shutil.copytree(self.base, self.dir)

    def cli(self, *args):
        return self.cli_in(self.dir, *args)

    def cli_fails(self, *args, directory: str | None = None) -> str:
        result = run_script("research_store.py", *args, "--dir", directory or self.dir)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        return result.stderr

    def fresh(self, name: str, locales: str = "en,ka,ru") -> str:
        directory = os.path.join(self.work.name, name)
        self.cli_in(directory, "init", "--site", "https://example.com", "--locales", locales)
        return directory

    def input_file(self, name: str, content, age_days: float = 0) -> str:
        return write_file(os.path.join(self.work.name, name), content, age_days)

    def keyword(self, keyword: str, locale: str = "en") -> dict:
        return self.load(self.dir).keywords[(locale, keyword)]

    def cluster_of(self, head: str) -> dict:
        return next(c for c in self.load(self.dir).clusters.values() if c["head_keyword"] == head)


class InitTest(StoreCase):
    def test_init_writes_every_file_and_a_gitignore_for_lock_and_temp_files(self):
        for name in ("site.json", "manifest.json", "keywords.jsonl", "clusters.json", "competitors.json",
                     "inventory.csv", ".gitignore"):
            self.assertTrue(os.path.exists(os.path.join(self.dir, name)), name)
        with open(os.path.join(self.dir, ".gitignore"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), ".lock\n*.tmp\n")
        self.assertEqual([p for p in store_bytes(self.dir) if p.endswith(".tmp")], [], "atomic writes leave no temp files")

    def test_reinit_adds_locales_and_keeps_data(self):
        before = len(self.load(self.dir).keywords)
        self.cli("init", "--site", "https://www.example.com/", "--locales", "en,de")
        store = self.load(self.dir)
        self.assertEqual(store.locales, ["en", "ka", "ru", "de"])
        self.assertEqual(len(store.keywords), before)

    def test_init_for_another_domain_is_refused(self):
        self.assertIn("is the store for example.com", self.cli_fails("init", "--site", "https://other.test"))

    def test_init_without_locales_assumes_en_and_says_so(self):
        fresh = os.path.join(self.work.name, "fresh")
        self.cli_in(fresh, "init", "--site", "https://example.com")
        site = self.load(fresh).site
        self.assertEqual(site["locales"], ["en"])
        self.assertTrue(site["assumptions"])

    def test_a_store_written_before_the_newer_fields_still_reads_and_upgrades(self):
        clusters_path, inventory_path = os.path.join(self.dir, "clusters.json"), os.path.join(self.dir, "inventory.csv")
        old = [{k: v for k, v in c.items() if k not in ("head_source", "target_source", "brief_slug")}
               for c in rs.read_json(clusters_path)]
        next(c for c in old if c["head_keyword"] == "how to become an english tutor")["status"] = "briefed"
        write_file(clusters_path, old)
        with open(inventory_path, encoding="utf-8", newline="") as fh:
            rows = [{k: v for k, v in row.items() if k not in ("crawled_at", "gsc_at")} for row in csv.DictReader(fh)]
        write_file(inventory_path, rs.csv_text(rs.INVENTORY_COLUMNS[:-2], rows))
        os.remove(os.path.join(self.dir, "posts.csv"))
        for args in (("status",), ("next-topics",), ("export", "clusters", "--format", "csv"),
                     ("export", "inventory", "--format", "csv"), ("export", "posts", "--format", "json")):
            self.cli(*args)
        self.cli("ingest", "crawl", self.files["crawl"])
        self.assertEqual(self.cluster_of("english tutor")["target_source"], "gsc")
        # a cluster that had left planned gets the brief name next-topics gave it, and keeps it from then on
        self.assertEqual(self.cluster_of("how to become an english tutor")["brief_slug"], "how-to-become-an-english-tutor")
        self.assertIsNone(self.cluster_of("english tutor")["brief_slug"])
        with open(inventory_path, encoding="utf-8") as fh:
            self.assertEqual(fh.readline().strip(), ",".join(rs.INVENTORY_COLUMNS))

    def test_a_weak_or_outdated_gsc_target_of_an_older_store_is_dropped_on_load(self):
        # the store's first version took the first page with 10% of a query's impressions as its target, home page
        # included, and never moved it when a newer export named another page
        path = os.path.join(self.dir, "keywords.jsonl")
        records = rs.read_jsonl(path)
        at = rs.observed_at(self.files["gsc"])
        weak = next(r for r in records if r["keyword"] == "how to become an english tutor")
        weak["demand"].update(gsc_impressions=1, gsc_position=80.0, gsc_pages=["https://example.com/"])
        weak["target_url"] = "https://example.com/"
        for field in ("demand.gsc_impressions", "demand.gsc_position", "demand.gsc_pages", "target_url"):
            weak["provenance"][field] = {"source": "gsc", "at": at}
        next(r for r in records if r["keyword"] == "english tutor online")["target_url"] = "https://example.com/old/"
        write_file(path, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records))
        topic = next(t for t in self.cli("next-topics")["topics"] if t["head_keyword"] == "how to become an english tutor")
        self.assertEqual((topic["target_url"], topic["scores"]["cannibalisation"]), (None, 0), topic["reasons"])
        self.cli("ingest", "crawl", self.files["crawl"])
        record = self.keyword("how to become an english tutor")
        self.assertEqual((record["target_url"], record["demand"]["gsc_pages"]), (None, []))
        self.assertNotIn("target_url", record["provenance"])
        self.assertEqual(self.keyword("english tutor online")["target_url"], "https://example.com/tutors/")

    def test_a_cluster_keyword_missing_from_keywords_jsonl_is_named(self):
        cluster_id = self.cluster_of("english tutor")["cluster_id"]
        path = os.path.join(self.dir, "keywords.jsonl")  # as a hand edit or a git merge resolution can leave it
        with open(path, encoding="utf-8") as fh:
            lines = [line for line in fh if '"keyword": "english tutor online"' not in line]
        write_file(path, "".join(lines))
        for args in (("status",), ("next-topics",), ("export", "clusters", "--format", "csv")):
            with self.subTest(command=args[0]):
                stderr = self.cli_fails(*args)
                for fragment in ("clusters.json", cluster_id, "'english tutor online'", "keywords.jsonl"):
                    self.assertIn(fragment, stderr)

    def test_a_store_written_before_head_and_target_sources_keeps_the_declared_ones(self):
        # the store's first version kept a clusters file's head and target, with no head_source or target_source
        path = os.path.join(self.dir, "clusters.json")
        old = [{k: v for k, v in c.items() if k not in ("head_source", "target_source", "brief_slug")}
               for c in rs.read_json(path)]
        main = next(c for c in old if c["head_keyword"] == "english tutor")
        declared = "https://example.com/blog/find-a-tutor/"  # live, and no keyword's target
        main.update(head_keyword="english tutor online", target_url=declared)
        write_file(path, old)
        report = self.cli("next-topics")
        self.assertNotIn(main["cluster_id"], [t["cluster_id"] for t in report["topics"]])
        self.assertEqual(report["excluded"].get("live_target"), 1)
        self.cli("ingest", "crawl", self.files["crawl"])
        cluster = self.load(self.dir).clusters[main["cluster_id"]]
        self.assertEqual((cluster["head_keyword"], cluster["head_source"], cluster["target_url"],
                          cluster["target_source"]), ("english tutor online", "input", declared, "input"))
        # the next clusters file without a head lets the store pick it again
        self.cli("ingest", "clusters", self.input_file("clusters-again.json", rs.read_json(self.files["clusters"])),
                 "--locale", "en")
        cluster = self.load(self.dir).clusters[main["cluster_id"]]
        self.assertEqual((cluster["head_keyword"], cluster["head_source"]), ("english tutor", "picked"))

    def test_a_cluster_whose_interlinks_are_not_a_list_is_named(self):
        path = os.path.join(self.dir, "clusters.json")  # a hand edit or a git merge resolution
        original = rs.read_json(path)
        for name, change in (("missing", lambda c: c.pop("interlinks")), ("null", lambda c: c.update(interlinks=None))):
            with self.subTest(interlinks=name):
                clusters = json.loads(json.dumps(original))
                change(clusters[0])
                write_file(path, clusters)
                for args in (("status",), ("next-topics",)):
                    stderr = self.cli_fails(*args)
                    for fragment in ("clusters.json", clusters[0]["cluster_id"], "interlinks", "a list of cluster ids"):
                        self.assertIn(fragment, stderr)

    def test_an_interlink_to_a_cluster_missing_from_clusters_json_is_named(self):
        path = os.path.join(self.dir, "clusters.json")  # as a hand edit or a git merge resolution can leave it
        clusters = rs.read_json(path)
        gone = next(c for c in clusters if c["head_keyword"] == "english tutor near me")
        linked = next(c for c in clusters if gone["cluster_id"] in c["interlinks"])
        write_file(path, [c for c in clusters if c is not gone])
        for args in (("status",), ("next-topics",), ("export", "clusters", "--format", "csv")):
            with self.subTest(command=args[0]):
                stderr = self.cli_fails(*args)
                for fragment in ("clusters.json", linked["cluster_id"], repr(gone["cluster_id"])):
                    self.assertIn(fragment, stderr)

    def test_commands_before_init_fail_without_creating_the_folder(self):
        missing = os.path.join(self.work.name, "nowhere")
        self.assertIn("no research store", self.cli_fails("status", directory=missing))
        self.assertFalse(os.path.exists(missing))


class IngestTest(StoreCase):
    def test_keyword_ideas_records_sources_intent_and_market(self):
        summary = self.results[1]
        self.assertEqual((summary["added"], summary["skipped_personal_data"]), (5, 1))
        record = self.keyword("english tutor near me")
        self.assertEqual(record["demand"]["autocomplete_sources"], ["bing", "google"])
        self.assertEqual(record["intent"], "transactional")
        self.assertEqual(record["status"], "planned")
        self.assertNotIn(("en", "english tutor 000 000 0000"), self.load(self.dir).keywords)
        self.assertEqual(self.load(self.dir).site["markets"]["ka"], {"hl": "ka", "gl": "ge"})
        self.assertIn(("ka", "ინგლისური ენის კურსები ონლაინ"), self.load(self.dir).keywords)

    def test_keyword_ideas_for_another_language_or_unknown_locale_are_refused(self):
        self.assertIn("not the language of locale en",
                      self.cli_fails("ingest", "keyword-ideas", self.files["ideas_ka"], "--locale", "en"))
        self.assertIn("is not in this store", self.cli_fails("ingest", "keyword-ideas", self.files["ideas_en"],
                                                             "--locale", "de"))

    def test_a_locale_with_a_region_is_that_regions_market_in_any_order(self):
        us = self.input_file("kw-us.json", dict(KEYWORD_IDEAS_EN, locale="en-us"))  # keyword_ideas.py's default --gl
        directory = self.fresh("en-gb", locales="en-gb")
        stderr = self.cli_fails("ingest", "keyword-ideas", us, "--locale", "en-gb", directory=directory)
        for fragment in (us, "--gl us", "--gl gb", "init --locales en-us"):
            self.assertIn(fragment, stderr)
        self.cli_in(directory, "ingest", "keyword-ideas", self.files["ideas_en"], "--locale", "en-gb")
        self.assertEqual(self.load(directory).site["markets"]["en-gb"], {"hl": "en", "gl": "gb"})

    def test_keyword_ideas_for_another_market_of_the_locale_are_refused(self):
        us = self.input_file("kw-us.json", dict(KEYWORD_IDEAS_EN, locale="en-us"))
        stderr = self.cli_fails("ingest", "keyword-ideas", us, "--locale", "en")
        for fragment in (us, "--gl us", "--gl gb", "site.json", "markets.en.gl"):
            self.assertIn(fragment, stderr)
        self.assertEqual(self.load(self.dir).site["markets"]["en"]["gl"], "gb")
        # a file without a region fills nothing and clashes with nothing, in either order
        region_less = self.input_file("kw-en.json", dict(KEYWORD_IDEAS_EN, locale="en"))
        self.cli("ingest", "keyword-ideas", region_less, "--locale", "en")
        self.assertEqual(self.load(self.dir).site["markets"]["en"]["gl"], "gb")
        directory = self.fresh("region-less-first")
        for path in (region_less, self.files["ideas_en"]):
            self.cli_in(directory, "ingest", "keyword-ideas", path, "--locale", "en")
        self.assertEqual(self.load(directory).site["markets"]["en"], {"hl": "en", "gl": "gb"})

    def test_volumes_keep_vendor_source_and_date(self):
        demand = self.keyword("english tutor near me")["demand"]
        self.assertEqual((demand["volume"], demand["volume_source"], demand["difficulty"], demand["difficulty_source"]),
                         (1900, "semrush", 34, "semrush"))
        self.assertEqual(demand["volume_date"], rs.observed_at(self.files["semrush"])[:10])

    def test_keyword_planner_utf16_export_with_title_rows_keeps_ranges_as_written(self):
        export = "Keyword Stats 2026-10-24\nAll locations\nKeyword\tCurrency\tAvg. monthly searches\n" \
                 "english tutor\tGBP\t1K – 10K\n"
        path = os.path.join(self.work.name, "planner.csv")
        with open(path, "wb") as fh:
            fh.write(codecs.BOM_UTF16_LE + export.encode("utf-16-le"))
        self.cli("ingest", "volumes", path, "--locale", "en", "--source", "keyword-planner")
        demand = self.keyword("english tutor")["demand"]
        self.assertEqual((demand["volume"], demand["volume_source"]), ("1K – 10K", "keyword-planner"))
        self.assertEqual(rs.volume_number(demand["volume"]), 1000)

    def test_gsc_query_page_rows_set_demand_pages_target_and_inventory(self):
        summary = self.results[4]
        self.assertEqual((summary["skipped_personal_data"], summary["skipped_below_min_impressions"]), (1, 1))
        record = self.keyword("english tutor")
        self.assertEqual(record["demand"]["gsc_impressions"], 300)
        self.assertEqual(record["demand"]["gsc_position"], 10.5)  # impression-weighted (8.2×200 + 15×100) / 300
        self.assertEqual(record["demand"]["gsc_pages"], ["https://example.com/tutors/",
                                                         "https://example.com/blog/find-a-tutor/"])
        self.assertEqual(record["target_url"], "https://example.com/tutors/")
        self.assertEqual(record["provenance"]["target_url"]["source"], "gsc")
        ka = self.keyword("ინგლისური ენის კურსები", "ka")  # locale from the /ka/ page URL
        self.assertEqual(ka["demand"]["gsc_impressions"], 50)
        row = self.load(self.dir).inventory["https://example.com/tutors/"]
        self.assertEqual((row["gsc_clicks"], row["gsc_impressions"], row["locale"]), (15, 292, "en"))

    def test_gsc_analyze_report_is_ingested_with_its_cannibalisation_pages(self):
        report = run_script("gsc_analyze.py", self.files["gsc"])
        self.assertEqual(report.returncode, 0, report.stderr)
        path = self.input_file("gsc.json", report.stdout)
        fresh = os.path.join(self.work.name, "fresh")
        self.cli_in(fresh, "init", "--site", "https://example.com", "--locales", "en,ka")
        self.cli_in(fresh, "ingest", "gsc", path)
        record = self.load(fresh).keywords[("en", "english tutor")]
        self.assertEqual(record["demand"]["gsc_impressions"], 300)
        self.assertEqual(len(record["demand"]["gsc_pages"]), 2)

    def test_queries_csv_without_pages_needs_a_locale_in_a_multilingual_store(self):
        path = self.input_file("Queries.csv", "Top queries,Clicks,Impressions,CTR,Position\n"
                                              "english tutor online,4,120,3.3%,7.5\n")
        self.assertIn("pass --locale", self.cli_fails("ingest", "gsc", path))
        self.cli("ingest", "gsc", path, "--locale", "en")
        self.assertEqual(self.keyword("english tutor online")["demand"]["gsc_impressions"], 120)

    def test_serps_store_snapshot_features_paa_and_intent(self):
        path = os.path.join(self.dir, "serps", "en", hashlib.sha1("how to become an english tutor".encode()).hexdigest()
                            + ".json")
        with open(path, encoding="utf-8") as fh:
            snapshot = json.load(fh)
        self.assertEqual(snapshot["features"], ["people_also_ask", "video"])
        self.assertEqual(len(snapshot["paa"]), 2)
        self.assertEqual(snapshot["results"][0], {"url": "https://www.reddit.com/r/TEFL/comments/abc/",
                                                  "title": "Result 0", "type": "forum/ugc"})
        record = self.keyword("english tutor")
        self.assertEqual(record["serp_features"], ["ai_overview", "local_pack"])
        self.assertEqual((record["intent"], record["provenance"]["intent"]["source"]), ("commercial", "serp"))

    def test_competitors_count_shared_serps_and_exclude_the_site(self):
        competitors = self.load(self.dir).competitors
        self.assertNotIn("example.com", competitors)
        self.assertEqual(competitors["tutorhub.test"]["keywords_shared"], 2)
        self.assertEqual(competitors["tutorhub.test"]["locales"], ["en"])

    def test_clusters_get_stable_ids_heads_targets_and_interlinks(self):
        main = self.cluster_of("english tutor")
        self.assertEqual(main["keywords"], ["english tutor", "english tutor online"])
        self.assertEqual(main["target_url"], "https://example.com/tutors/")  # from the keywords' GSC page
        near = self.cluster_of("english tutor near me")
        self.assertEqual(main["interlinks"], [near["cluster_id"]])
        self.assertEqual(near["interlinks"], [main["cluster_id"]])
        self.assertEqual(self.keyword("english tutor online")["cluster_id"], main["cluster_id"])
        before = {c["cluster_id"]: c["keywords"] for c in self.load(self.dir).clusters.values()}
        reordered = self.input_file("serps-reordered.json", dict(reversed(list(SERPS_EN.items()))))
        clustered = run_script("serp_cluster.py", reordered)
        summary = self.cli("ingest", "clusters", self.input_file("clusters-2.json", clustered.stdout), "--locale", "en")
        self.assertEqual(summary["clusters_reused"], 4)
        self.assertEqual({c["cluster_id"]: c["keywords"] for c in self.load(self.dir).clusters.values()}, before)

    def test_regrouped_keywords_move_and_the_emptied_cluster_is_kept(self):
        near = self.cluster_of("english tutor near me")
        merged = {"keywords": 3, "clusters": [{"id": 0, "keywords": ["english tutor", "english tutor online",
                                                                    "english tutor near me"]}],
                  "interlink_clusters": [], "note": "…"}
        self.cli("ingest", "clusters", self.input_file("merged.json", merged), "--locale", "en")
        store = self.load(self.dir)
        self.assertEqual(store.clusters[near["cluster_id"]]["keywords"], [])
        self.assertEqual(store.keywords[("en", "english tutor near me")]["cluster_id"],
                         self.cluster_of("english tutor")["cluster_id"])
        self.assertEqual(self.cli("next-topics")["excluded"]["empty"], 1)

    def test_older_clusters_file_is_refused(self):
        old = self.input_file("old-clusters.json", rs.read_json(self.files["clusters"]), age_days=30)
        self.assertIn("older than the stored en clusters", self.cli_fails("ingest", "clusters", old, "--locale", "en"))

    def test_crawl_fills_inventory_with_locale_from_the_path_and_cluster_from_targets(self):
        inventory = self.load(self.dir).inventory
        self.assertEqual(inventory["https://example.com/ka/courses/"]["locale"], "ka")
        self.assertEqual(inventory["https://example.com/ru/"]["locale"], "ru")
        self.assertEqual(inventory["https://example.com/old-page"]["status"], 301)
        tutors = inventory["https://example.com/tutors/"]
        self.assertEqual((tutors["words"], tutors["cluster_id"]), (900, self.cluster_of("english tutor")["cluster_id"]))

    def test_reingesting_the_same_files_changes_no_byte(self):
        before = store_bytes(self.dir)
        for step in self.pipeline[1:]:
            self.cli(*step)
        self.assertEqual(store_bytes(self.dir), before)


class MergeTest(StoreCase):
    def test_newest_volume_wins_with_its_source_and_older_data_is_ignored(self):
        older = self.input_file("ahrefs-old.csv", "Keyword,Volume,Difficulty\nenglish tutor near me,1500,20\n",
                                age_days=20)
        self.assertEqual(self.cli("ingest", "volumes", older, "--locale", "en", "--source", "ahrefs")["unchanged"], 1)
        self.assertEqual(self.keyword("english tutor near me")["demand"]["volume_source"], "semrush")
        newer = self.input_file("ahrefs.csv", "Keyword,Volume,Difficulty\nenglish tutor near me,1500,\n")
        self.cli("ingest", "volumes", newer, "--locale", "en", "--source", "ahrefs")
        record = self.keyword("english tutor near me")
        self.assertEqual((record["demand"]["volume"], record["demand"]["volume_source"]), (1500, "ahrefs"))
        self.assertEqual(record["provenance"]["demand.volume"], {"source": "ahrefs", "at": rs.observed_at(newer)})
        # an empty cell never overwrites: Semrush's difficulty stays, with its source
        self.assertEqual((record["demand"]["difficulty"], record["demand"]["difficulty_source"]), (34, "semrush"))
        manifest = self.load(self.dir).manifest["datasets"]["volumes"]
        self.assertEqual(manifest["sources"], ["ahrefs", "semrush"])

    def test_autocomplete_evidence_accumulates_and_the_guess_never_replaces_a_serp_intent(self):
        youtube = dict(KEYWORD_IDEAS_EN, sources=["youtube"],
                       keywords=[{"keyword": "english tutor", "sources": ["youtube"], "modifier": "seed",
                                  "intent": "unclear"}])
        self.cli("ingest", "keyword-ideas", self.input_file("kw-yt.json", youtube), "--locale", "en")
        record = self.keyword("english tutor")
        self.assertEqual(record["demand"]["autocomplete_sources"], ["bing", "google", "youtube"])
        self.assertEqual((record["intent"], record["provenance"]["intent"]["source"]), ("commercial", "serp"))
        self.assertEqual(record["first_seen"], rs.observed_at(self.files["ideas_en"]))

    def test_older_serp_snapshot_does_not_replace_a_newer_one(self):
        older = self.input_file("serps-old.json", {"english tutor": urls("stale.test/")}, age_days=40)
        self.assertEqual(self.cli("ingest", "serps", older, "--locale", "en")["kept_newer"], 1)
        self.assertEqual(len(self.load(self.dir).serp("en", "english tutor")["results"]), 10)

    def test_cluster_targets_heads_and_priorities_do_not_depend_on_ingest_order(self):
        ideas = ["ingest", "keyword-ideas", self.files["ideas_en"], "--locale", "en"]
        serps = ["ingest", "serps", self.files["serps"], "--locale", "en", "--details", self.files["details"]]
        clusters = ["ingest", "clusters", self.files["clusters"], "--locale", "en"]
        gsc = ["ingest", "gsc", self.files["gsc"]]
        late, early = self.fresh("gsc-last"), self.fresh("gsc-first")
        for step in (ideas, serps, clusters, gsc):
            self.cli_in(late, *step)
        for step in (ideas, gsc, serps, clusters):
            self.cli_in(early, *step)
        late_files, early_files = store_bytes(late), store_bytes(early)
        for name in ("clusters.json", "inventory.csv", "competitors.json"):
            self.assertEqual(late_files[name], early_files[name], name)
        main = next(c for c in self.load(late).clusters.values() if c["head_keyword"] == "english tutor")
        self.assertEqual(main["target_url"], "https://example.com/tutors/")
        for step in (ideas, serps, clusters, gsc):
            self.cli_in(late, *step)
        self.assertEqual(store_bytes(late), late_files, "re-ingesting the same files changes no byte")

    def test_the_store_is_the_same_in_any_ingest_order(self):
        # the pipeline's inputs, with a GSC row under the minimum for a keyword the ideas suggest, and a query that only
        # GSC and the vendor know (so its intent is the store's own guess, dated by whichever input came first). Also an
        # older SERP of "english tutor near me", with the page types, features and intent the newer one lacks and
        # domains the newer top 10 lost, and a newer ideas file: it suggests "english tutor" again, from fewer engines
        # (the evidence is dated by its newest input), and adds an engine for "english tutor online".
        gsc = self.input_file("gsc-any-order.csv", GSC_QUERY_PAGE
                              + "how to become an english tutor,https://example.com/,0,1,0%,80\n"
                              + "english tutor prices,https://example.com/prices/,1,20,5%,12.0\n", age_days=10)
        volumes = self.input_file("volumes-any-order.csv", SEMRUSH_VOLUMES + "english tutor prices,320,20,1.50\n",
                                  age_days=5)
        near = "english tutor near me"
        older_top10 = SERPS_EN[near][:7] + urls("gone.test/near", "www.reddit.com/r/near/", "local9.test/")
        older_serps = self.input_file("serps-near-older.json", {near: older_top10}, age_days=15)
        older_details = self.input_file("details-near-older.json", {near: {
            "results": [{"url": u, "title": f"Near {i}", "type": "local" if i % 2 else "guide/article"}
                        for i, u in enumerate(older_top10)],
            "features": ["Local pack"], "intent": "commercial"}}, age_days=15)
        ideas = dict(KEYWORD_IDEAS_EN, sources=["google", "youtube"], keywords=[
            {"keyword": "english tutor", "sources": ["google"], "modifier": "seed", "intent": "unclear"},
            {"keyword": "english tutor online", "sources": ["youtube"], "modifier": "seed", "intent": "unclear"}])
        newer_ideas = self.input_file("kw-en-newer.json", ideas, age_days=3)
        steps = [step for step in self.pipeline[1:] if step[1] not in ("gsc", "volumes")]
        steps += [["ingest", "gsc", gsc], ["ingest", "volumes", volumes, "--locale", "en", "--source", "semrush"],
                  ["ingest", "serps", older_serps, "--locale", "en", "--details", older_details],
                  ["ingest", "keyword-ideas", newer_ideas, "--locale", "en"]]
        # the listed order and its reverse give each pair of SERP files, and of English ideas files, in both orders
        rng, every = random.Random(2026), tuple(range(len(steps)))
        orders = sorted({every, every[::-1], *(tuple(rng.sample(every, len(every))) for _ in range(22))})
        self.assertGreaterEqual(len(orders), 20)
        first = None
        for number, order in enumerate(orders):
            directory = os.path.join(self.work.name, f"order-{number}")
            run_in_process(directory, "init", "--site", "https://example.com", "--locales", "en,ka,ru")
            for index in order:
                run_in_process(directory, *steps[index])
            files = store_bytes(directory)
            files["keywords.jsonl"] = re.sub(rb'"updated_at": "[^"]*"', b'"updated_at": ""', files["keywords.jsonl"])
            briefs = {t["cluster_id"]: t["brief"] for t in json.loads(run_in_process(directory, "next-topics"))["topics"]}
            if first is None:
                first = files, briefs
                continue
            names = " → ".join(f"{steps[i][1]} {os.path.basename(steps[i][2])}" for i in order)
            self.assertEqual(sorted(files), sorted(first[0]), names)
            for name in ("clusters.json", "keywords.jsonl", *sorted(files)):
                self.assertEqual(files[name], first[0][name], f"{name} after {names}")
            self.assertEqual(briefs, first[1], names)

    def test_a_gsc_target_follows_the_newest_export_in_any_order(self):
        header = "query,page,clicks,impressions,ctr,position\n"
        older = self.input_file("gsc-a.csv", header + "english tutor,https://example.com/a/,5,100,5%,5\n")
        newer = self.input_file("gsc-b.csv", header + "english tutor,https://example.com/b/,9,300,3%,4\n")
        dates = {older: days_ago(30), newer: days_ago(20)}
        for name, order in (("a-then-b", (older, newer)), ("b-then-a", (newer, older))):
            directory = self.fresh(name)
            for path in order:
                self.cli_in(directory, "ingest", "gsc", path, "--as-of", dates[path])
            record = self.load(directory).keywords[("en", "english tutor")]
            self.assertEqual((record["target_url"], record["demand"]["gsc_pages"]),
                             ("https://example.com/b/", ["https://example.com/b/"]), name)
        # a still newer export where only the home page gets the impressions: no page owns the query any more
        home = self.input_file("gsc-home.csv", header + "english tutor,https://example.com/,9,300,3%,4\n")
        self.cli_in(directory, "ingest", "gsc", home, "--as-of", days_ago(10))
        record = self.load(directory).keywords[("en", "english tutor")]
        self.assertEqual((record["target_url"], record["demand"]["gsc_pages"]), (None, []))
        self.assertNotIn("target_url", record["provenance"])
        # a target set with set-status is never replaced by GSC
        self.cli_in(directory, "set-status", "--keyword", "english tutor", "--locale", "en", "--status", "planned",
                    "--url", "https://example.com/c/")
        self.cli_in(directory, "ingest", "gsc", newer, "--as-of", days_ago(1))
        self.assertEqual(self.load(directory).keywords[("en", "english tutor")]["target_url"], "https://example.com/c/")

    def test_a_result_the_newer_details_leave_undescribed_keeps_its_description_in_any_order(self):
        keyword = "how to become an english tutor"
        top10 = SERPS_EN[keyword]
        older = self.input_file("serps-described.json", {keyword: top10}, age_days=20)
        described = self.input_file("details-described.json", {keyword: DETAILS_EN[keyword]}, age_days=20)
        newer = self.input_file("serps-bare.json", {keyword: top10}, age_days=2)
        bare = self.input_file("details-bare.json", {keyword: {"results": [{"url": u} for u in top10[:3]]}}, age_days=2)
        steps = {older: ["ingest", "serps", older, "--locale", "en", "--details", described],
                 newer: ["ingest", "serps", newer, "--locale", "en", "--details", bare]}
        types = [r["type"].lower() for r in DETAILS_EN[keyword]["results"]]
        for name, order in (("older-first", (older, newer)), ("newer-first", (newer, older))):
            directory = self.fresh(name)
            for path in order:
                self.cli_in(directory, *steps[path])
            snapshot = self.load(directory).serp("en", keyword)
            self.assertEqual([r["type"] for r in snapshot["results"]], types, name)

    def test_an_older_serp_file_after_a_newer_one_gives_the_same_store(self):
        # the older fetch has --details (page types, features, intent) and domains the newer top 10 lost; the newer one
        # has no details. The newer snapshot stays in either order, and the older fetch counts as in the other order.
        keyword = "how to become an english tutor"
        older = self.input_file("serps-typed.json", {keyword: SERPS_EN[keyword]}, age_days=20)
        details = self.input_file("details-typed.json", {keyword: DETAILS_EN[keyword]}, age_days=20)
        newer = self.input_file("serps-plain.json", {keyword: SERPS_EN[keyword][2:] + urls("new1.test/", "new2.test/")},
                                age_days=2)
        steps = {older: ["ingest", "serps", older, "--locale", "en", "--details", details],
                 newer: ["ingest", "serps", newer, "--locale", "en"]}
        stores = {}
        for name, order in (("older-first", (older, newer)), ("newer-first", (newer, older))):
            directory = self.fresh(name)
            for path in order:
                self.cli_in(directory, *steps[path])
            stores[name] = store_bytes(directory)
            stores[name]["keywords.jsonl"] = re.sub(rb'"updated_at": "[^"]*"', b'"updated_at": ""',
                                                    stores[name]["keywords.jsonl"])
            store = self.load(directory)
            snapshot = store.serp("en", keyword)
            self.assertEqual(snapshot["fetched_at"], rs.observed_at(newer), name)
            self.assertEqual(sum(bool(r["type"]) for r in snapshot["results"]), 8, name)
            record = store.keywords[("en", keyword)]
            self.assertEqual((record["first_seen"], record["intent"]), (rs.observed_at(older), "informational"), name)
            self.assertIn("quora.com", store.competitors, name)  # in the older top 10 only
            self.assertEqual(store.competitors["quora.com"]["keywords_shared"], 0, name)
        for file in sorted(set(stores["older-first"]) | set(stores["newer-first"])):
            self.assertEqual(stores["newer-first"].get(file), stores["older-first"].get(file), file)

    def test_autocomplete_evidence_is_dated_by_its_newest_input_in_any_order(self):
        older = self.files["ideas_en"]  # 10 days old: "english tutor" from google and bing
        google = dict(KEYWORD_IDEAS_EN, sources=["google"], keywords=[
            {"keyword": "english tutor", "sources": ["google"], "modifier": "seed", "intent": "unclear"}])
        newer = self.input_file("kw-google.json", google, age_days=2)
        for name, order in (("older-first", (older, newer)), ("newer-first", (newer, older))):
            directory = self.fresh(name)
            for path in order:
                self.cli_in(directory, "ingest", "keyword-ideas", path, "--locale", "en")
            record = self.load(directory).keywords[("en", "english tutor")]
            self.assertEqual((record["demand"]["autocomplete_sources"],
                              record["provenance"]["demand.autocomplete_sources"]["at"]),
                             (["bing", "google"], rs.observed_at(newer)), name)
            before = store_bytes(directory)
            self.cli_in(directory, "ingest", "keyword-ideas", newer, "--locale", "en")
            self.assertEqual(store_bytes(directory), before, f"{name}: re-ingesting the same file changes no byte")

    def test_intent_provenance_does_not_depend_on_ingest_order(self):
        gsc = self.input_file("gsc-3d.csv", GSC_QUERY_PAGE, age_days=3)  # newer than the 10-day-old ideas file
        ideas_first, gsc_first = self.fresh("ideas-first"), self.fresh("gsc-first")
        self.cli_in(ideas_first, "ingest", "keyword-ideas", self.files["ideas_en"], "--locale", "en")
        self.cli_in(ideas_first, "ingest", "gsc", gsc)
        self.cli_in(gsc_first, "ingest", "gsc", gsc)
        self.cli_in(gsc_first, "ingest", "keyword-ideas", self.files["ideas_en"], "--locale", "en")
        for keyword in ("english tutor", "english tutor online"):
            self.assertEqual(self.load(gsc_first).keywords[("en", keyword)]["provenance"]["intent"],
                             {"source": "keyword_ideas", "at": rs.observed_at(self.files["ideas_en"])})
            self.assertEqual(self.load(ideas_first).keywords[("en", keyword)]["provenance"]["intent"],
                             self.load(gsc_first).keywords[("en", keyword)]["provenance"]["intent"])
        # a query only GSC knows carries the store's own wording guess, which any real intent source replaces
        ka = self.load(gsc_first).keywords[("ka", "ინგლისური ენის კურსები")]
        self.assertEqual(ka["provenance"]["intent"]["source"], "wording-guess")

    def test_vendor_placeholders_never_replace_a_volume(self):
        for cell in ("-", "n/a", "N/A", "", "—", "unknown"):
            self.assertIsNone(rs.parse_volume(cell), cell)
        self.assertEqual(rs.parse_volume("1K – 10K"), "1K – 10K")
        self.assertEqual(rs.parse_volume("1,900"), 1900)
        newer = self.input_file("ahrefs-dash.csv", "Keyword,Volume\nenglish tutor near me,-\nenglish tutor,n/a\n")
        self.assertEqual(self.cli("ingest", "volumes", newer, "--locale", "en", "--source", "ahrefs")["unchanged"], 2)
        demand = self.keyword("english tutor near me")["demand"]
        self.assertEqual((demand["volume"], demand["volume_source"]), (1900, "semrush"))

    def test_a_serp_without_details_keeps_no_old_features_or_paa(self):
        keyword = "how to become an english tutor"
        newer = self.input_file("serps-new.json", {keyword: urls(*[f"new{i}.test/" for i in range(10)])})
        self.cli("ingest", "serps", newer, "--locale", "en")
        snapshot = self.load(self.dir).serp("en", keyword)
        self.assertEqual((snapshot["fetched_at"], snapshot["features"], snapshot["paa"]),
                         (rs.observed_at(newer), None, None))
        self.assertEqual(self.keyword(keyword)["provenance"]["serp_features"]["at"], rs.observed_at(self.files["serps"]))
        topic = next(t for t in self.cli("next-topics")["topics"] if t["head_keyword"] == keyword)
        self.assertEqual(topic["paa"], [])

    def test_each_inventory_row_is_dated_on_its_own(self):
        directory = self.fresh("rows")
        old = self.input_file("full-old.csv", crawl_csv([crawl_row("https://example.com/tutors/", 200, "Old title"),
                                                         crawl_row("https://example.com/")]), age_days=60)
        blog = self.input_file("blog.csv", crawl_csv([crawl_row("https://example.com/blog/x/")]))
        gone = self.input_file("full-20d.csv", crawl_csv([crawl_row("https://example.com/tutors/", 404, ""),
                                                          crawl_row("https://example.com/")]), age_days=20)
        for path in (old, blog):
            self.cli_in(directory, "ingest", "crawl", path)
        summary = self.cli_in(directory, "ingest", "crawl", gone)
        self.assertEqual((summary["pages"], summary.get("kept_newer", 0)), (2, 0))
        tutors = self.load(directory).inventory["https://example.com/tutors/"]
        self.assertEqual((tutors["status"], tutors["crawled_at"]), (404, rs.observed_at(gone)))
        self.assertEqual(self.cli_in(directory, "ingest", "crawl", old)["kept_newer"], 2)

    def test_a_locale_subdomain_is_the_site_not_a_competitor(self):
        site_path = os.path.join(self.dir, "site.json")
        site = rs.read_json(site_path)
        site["markets"]["ka"]["url_prefix"] = "https://ka.example.com/"
        write_file(site_path, site)
        keyword = "ინგლისური ენის კურსები"
        serps = self.input_file("serps-ka.json", {keyword: urls("ka.example.com/kursebi/",
                                                               *[f"ka{i}.test/" for i in range(9)])})
        self.cli("ingest", "serps", serps, "--locale", "ka")
        clusters = self.input_file("clusters-ka.json", {"clusters": [{"id": 0, "keywords": [keyword]}]})
        self.cli("ingest", "clusters", clusters, "--locale", "ka")
        self.assertNotIn("ka.example.com", self.load(self.dir).competitors)
        topic = self.cli("next-topics", "--locale", "ka")["topics"][0]
        self.assertTrue(any("already ranks in the top 10 with https://ka.example.com/kursebi/" in r
                            for r in topic["reasons"]), topic["reasons"])

    def test_rows_of_another_site_are_skipped(self):
        other = crawl_row("https://other-site.test/page", 200, "Other")
        summary = self.cli("ingest", "crawl", self.input_file("mixed.csv", crawl_csv([CRAWL_ROWS[1], other])))
        self.assertEqual((summary["pages"], summary["skipped_other_site"]), (1, 1))
        self.assertNotIn("https://other-site.test/page", self.load(self.dir).inventory)
        self.assertIn("every row is from another site",
                      self.cli_fails("ingest", "crawl", self.input_file("other.csv", crawl_csv([other]))))
        gsc = self.input_file("gsc-other.csv", "query,page,clicks,impressions,ctr,position\n"
                                               "english tutor,https://other-site.test/page,1,999,1%,3\n"
                                               "english tutor online,https://www.example.com/tutors/,5,80,6.25%,9.1\n")
        self.assertEqual(self.cli("ingest", "gsc", gsc)["skipped_other_site"], 1)
        self.assertEqual(self.keyword("english tutor")["demand"]["gsc_impressions"], 300)


class InputCheckTest(StoreCase):
    def assert_clean_failure(self, args, *fragments):
        before = store_bytes(self.dir)
        stderr = self.cli_fails(*args)
        for fragment in fragments:
            self.assertIn(fragment, stderr)
        self.assertEqual(store_bytes(self.dir), before, "a failed ingest writes nothing")

    def test_a_bad_details_entry_writes_no_serp_file(self):
        serps = self.input_file("serps-ab.json", {"alpha kw": urls("a.test/"), "beta kw": urls("b.test/")})
        details = self.input_file("details-ab.json", {"beta kw": {"results": [{"title": "no url"}]}})
        self.assert_clean_failure(["ingest", "serps", serps, "--locale", "en", "--details", details],
                                  details, "beta kw", "url")
        self.assertFalse(os.path.exists(self.load(self.dir).serp_file("en", "alpha kw")))

    def test_malformed_inputs_fail_with_a_message(self):
        ideas = self.input_file("kw-bad.json", dict(KEYWORD_IDEAS_EN, keywords=[{"sources": ["google"]}]))
        self.assert_clean_failure(["ingest", "keyword-ideas", ideas, "--locale", "en"], ideas, "keyword")
        clusters = self.input_file("clusters-bad.json", {"clusters": [{"keywords": ["english tutor"]}]})
        self.assert_clean_failure(["ingest", "clusters", clusters, "--locale", "en"], clusters, "'id'")
        cp1252 = os.path.join(self.work.name, "cp1252.csv")
        with open(cp1252, "wb") as fh:
            fh.write("Keyword,Volume\ncafé tutor,10\n".encode("cp1252"))
        self.assert_clean_failure(["ingest", "volumes", cp1252, "--locale", "en", "--source", "semrush"],
                                  cp1252, "UTF-8")
        self.assert_clean_failure(["ingest", "crawl", cp1252], cp1252, "UTF-8")
        gsc = self.input_file("gsc-bad.csv", "query,page,clicks,impressions,ctr,position\n"
                                             "english tutor,https://example.com/tutors/,1,lots,1%,3\n")
        self.assert_clean_failure(["ingest", "gsc", gsc], gsc, "lots")
        report = self.input_file("gsc-bad.json", {"rows": 1, "striking_distance": [{"query": "english tutor"}]})
        self.assert_clean_failure(["ingest", "gsc", report], report, "striking_distance[0]")
        self.assertIn("not a locale code", self.cli_fails("init", "--site", "https://example.com",
                                                          "--locales", "en,english"))

    def test_a_string_where_a_list_belongs_is_refused(self):
        ideas = self.input_file("kw-str.json", dict(KEYWORD_IDEAS_EN, keywords=[{"keyword": "english tutor",
                                                                                 "sources": "google"}]))
        self.assert_clean_failure(["ingest", "keyword-ideas", ideas, "--locale", "en"], "sources", "list")
        serps = self.input_file("serps-1.json", {"english tutor": SERPS_EN["english tutor"]})
        details = self.input_file("details-str.json", {"english tutor": {"features": "AI Overview"}})
        self.assert_clean_failure(["ingest", "serps", serps, "--locale", "en", "--details", details], "features", "list")
        clusters = self.input_file("clusters-str.json", {"clusters": [{"id": 0, "keywords": "seo kw"}]})
        self.assert_clean_failure(["ingest", "clusters", clusters, "--locale", "en"], "keywords", "list")
        numbers = self.input_file("serps-num.json", {"english tutor": [1, 2]})
        self.assert_clean_failure(["ingest", "serps", numbers, "--locale", "en"], numbers)

    def test_only_the_questions_of_a_vendor_paa_block_are_kept(self):
        raw = [{"type": "people_also_ask_element", "title": "Q?",
                "expanded_element": [{"url": "https://x.test/", "description": "raw answer text from the vendor"}]},
               "Plain question?", "x" * 500]
        details = self.input_file("details-raw.json", {"english tutor": {
            "results": [{"url": SERPS_EN["english tutor"][0], "title": "T" * 500, "type": "listicle"}], "paa": raw}})
        serps = self.input_file("serps-raw.json", {"english tutor": SERPS_EN["english tutor"]})
        self.cli("ingest", "serps", serps, "--locale", "en", "--details", details)
        snapshot = self.load(self.dir).serp("en", "english tutor")
        self.assertEqual(snapshot["paa"][:2], ["Q?", "Plain question?"])
        self.assertEqual(len(snapshot["paa"][2]), rs.TEXT_LIMIT)
        self.assertEqual(len(snapshot["results"][0]["title"]), rs.TEXT_LIMIT)
        self.assertNotIn("raw answer text", json.dumps(snapshot))

    def test_phone_numbers_in_local_formats_are_dropped_and_number_lists_kept(self):
        # all-zero or fictional numbers (07700 900xxx is Ofcom's drama range): nothing here can reach a person
        for keyword in ("tutor +995 500 00 00 00", "tutor 500 00 00 00", "tutor 500-00-00-00", "tutor 123 45 67 89",
                        "tutor +44 20 0000 0000", "tutor 020 0000 0000", "tutor (020) 0000 0000",
                        "tutor 07700 900000", "english tutor 000 000 0000", "tutor 500000000",
                        "tutor someone@example.invalid"):
            with self.subTest(keyword=keyword):
                self.assertTrue(rs.has_personal_data(keyword))
        for keyword in ("100 200 300 word essay", "top 100 500 1000 words", "ielts 6.5 7.0 7.5", "tutor 2026-10-24",
                        "english tutor", "c++ tutor"):
            with self.subTest(keyword=keyword):
                self.assertFalse(rs.has_personal_data(keyword))

    def test_digit_and_year_lists_are_kept_and_georgian_mobiles_dropped_even_when_round(self):
        # the review's probes, and the formats in their usual grouping: all-zero digits, Ofcom's drama ranges
        # (07700 900xxx, 020 7946 0xxx) or the review's own 5XX XX XX XX probes; the store never calls or messages any
        for keyword in ("tutor 550 10 20 30", "tutor 590 10 20 30", "tutor +995 500 00 00 00", "tutor 500 00 00 00",
                        "tutor 07700 900123", "tutor +44 20 7946 0958", "tutor 020 7946 0958"):
            with self.subTest(keyword=keyword):
                self.assertTrue(rs.has_personal_data(keyword))
        for keyword in ("1 2 3 4 5 6 7 8 9 times tables", "gcse grades 9 8 7 6 5 4 3 2 1", "2023 2024 2025 tax brackets",
                        "1990 2000 2010 census data", "100 200 300 word essay", "top 100 500 1000 words"):
            with self.subTest(keyword=keyword):
                self.assertFalse(rs.has_personal_data(keyword))

    def test_malformed_interlinks_are_refused(self):
        for name, links in (("number", 5), ("list-end", [{"from": [0], "to": 1}]), ("no-to", [{"from": 0}]),
                            ("string", ["0-1"]), ("true", [{"from": True, "to": 0}])):
            with self.subTest(interlink_clusters=links):
                groups = [{"id": 0, "keywords": ["english tutor"]}, {"id": 1, "keywords": ["english tutor jobs"]}]
                clusters = self.input_file(f"interlinks-{name}.json", {"clusters": groups, "interlink_clusters": links})
                self.assert_clean_failure(["ingest", "clusters", clusters, "--locale", "en"], clusters,
                                          "interlink_clusters")
        # true is no cluster id either, though Python counts it as the number 1
        clusters = self.input_file("id-true.json", {"clusters": [{"id": True, "keywords": ["english tutor"]}]})
        self.assert_clean_failure(["ingest", "clusters", clusters, "--locale", "en"], clusters, "clusters[0]", "'id'")


class StatusTest(StoreCase):
    def test_stale_and_missing_datasets_per_locale(self):
        report = self.cli("status")
        stale = {(s["dataset"], s["locale"]) for s in report["stale"]}
        self.assertEqual(stale, {("gsc", "en"), ("gsc", "ka")})  # GSC export 10 days old, TTL 7
        self.assertFalse(report["datasets"]["keywords"]["locales"]["en"]["stale"])  # 10 days old, TTL 90
        self.assertEqual(report["datasets"]["gsc"]["ttl_days"], 7)
        missing = {(m["dataset"], m["locale"]) for m in report["missing"]}
        self.assertTrue({("keywords", "ru"), ("serps", "ka"), ("clusters", "ka"), ("glossary", "en")} <= missing)
        self.assertNotIn(("inventory", "ru"), missing)

    def test_gaps_per_locale(self):
        gaps = self.cli("status")["gaps"]
        self.assertEqual(gaps["en"]["keywords"], 5)
        self.assertEqual((gaps["en"]["unclustered"], gaps["en"]["needs_serp"]["count"]), (0, 0))
        self.assertEqual(gaps["ka"]["needs_serp"]["count"], 3)
        self.assertEqual(gaps["ka"]["needs_serp"]["keywords"][0], "ინგლისური ენის კურსები")  # GSC demand first

    def test_ttl_can_be_tuned_in_the_manifest(self):
        path = os.path.join(self.dir, "manifest.json")
        manifest = rs.read_json(path)
        manifest["datasets"]["gsc"]["ttl_days"] = 28
        write_file(path, manifest)
        self.assertEqual(self.cli("status")["stale"], [])
        self.assertEqual(self.cli("status")["gaps"]["en"]["stale_gsc"]["count"], 0)

    def test_a_ttl_that_is_not_a_number_is_named(self):
        path = os.path.join(self.dir, "manifest.json")
        for value in ("28", True):  # hand edits, as tuning a TTL is
            with self.subTest(ttl_days=value):
                manifest = rs.read_json(path)
                manifest["datasets"]["gsc"]["ttl_days"] = value
                write_file(path, manifest)
                stderr = self.cli_fails("status")
                for fragment in ("manifest.json", "datasets.gsc.ttl_days", "a number of days"):
                    self.assertIn(fragment, stderr)

    def test_a_partial_refresh_leaves_the_old_volumes_listed(self):
        old = self.input_file("semrush-old.csv", "Keyword,Volume\n" + "".join(f"kw {i},{100 + i}\n" for i in range(3)),
                              age_days=120)
        self.cli("ingest", "volumes", old, "--locale", "en", "--source", "semrush")
        self.cli("ingest", "volumes", self.input_file("ahrefs.csv", "Keyword,Volume\nkw 0,150\n"), "--locale", "en",
                 "--source", "ahrefs")
        report = self.cli("status")
        self.assertNotIn(("volumes", "en"), {(s["dataset"], s["locale"]) for s in report["stale"]})  # newest is fresh
        self.assertEqual(report["gaps"]["en"]["stale_volumes"], {"count": 2, "keywords": ["kw 2", "kw 1"]})

    def test_a_partial_gsc_refresh_leaves_the_old_queries_and_pages_listed(self):
        fresh = self.input_file("gsc-fresh.csv", "query,page,clicks,impressions,ctr,position\n"
                                                 "english tutor,https://example.com/tutors/,12,220,5%,8.0\n")
        self.cli("ingest", "gsc", fresh)
        gaps = self.cli("status")["gaps"]
        self.assertEqual(gaps["en"]["stale_gsc"], {"count": 1, "keywords": ["english tutor online"]})
        self.assertEqual(gaps["ka"]["stale_gsc"]["count"], 1)
        self.assertEqual(gaps["en"]["stale_gsc_pages"], {"count": 1, "urls": ["https://example.com/blog/find-a-tutor/"]})

    def test_a_section_crawl_leaves_the_rest_of_an_old_crawl_listed(self):
        directory = self.fresh("crawls")
        self.cli_in(directory, "ingest", "crawl", self.input_file("old.csv", crawl_csv(), age_days=60))
        self.cli_in(directory, "ingest", "crawl", self.input_file("blog.csv", crawl_csv(CRAWL_ROWS[2:3])))
        report = self.cli_in(directory, "status")
        self.assertNotIn(("inventory", "en"), {(s["dataset"], s["locale"]) for s in report["stale"]})  # newest is fresh
        self.assertEqual(report["gaps"]["en"]["stale_inventory"],
                         {"count": 3, "urls": ["https://example.com/", "https://example.com/old-page",
                                               "https://example.com/tutors/"]})
        self.assertEqual(report["gaps"]["ka"]["stale_inventory"]["count"], 1)

    def test_init_removes_duplicate_locales(self):
        directory = os.path.join(self.work.name, "dups")
        self.cli_in(directory, "init", "--site", "https://example.com", "--locales", "en,EN,ka")
        self.assertEqual(self.load(directory).locales, ["en", "ka"])
        self.assertEqual(len(self.cli_in(directory, "status")["missing"]), len(rs.TTL_DAYS) * 2)


class AsOfTest(StoreCase):
    def test_a_previous_period_export_with_its_as_of_never_replaces_the_current_one(self):
        current = self.input_file("last_28d.csv", "query,page,clicks,impressions,ctr,position\n"
                                                  "english tutor,https://example.com/tutors/,40,900,4.4%,4\n")
        previous = self.input_file("previous_28d.csv", "query,page,clicks,impressions,ctr,position\n"
                                                       "english tutor,https://example.com/old-tutors/,1,60,1.7%,25\n")
        self.cli("ingest", "gsc", current, "--as-of", days_ago(2))
        summary = self.cli("ingest", "gsc", previous, "--as-of", days_ago(30))  # saved later, covers an older period
        self.assertEqual(summary["observed_at"], f"{days_ago(30)}T00:00:00+00:00")
        record = self.keyword("english tutor")
        demand = record["demand"]
        self.assertEqual((demand["gsc_impressions"], demand["gsc_position"], demand["gsc_pages"]),
                         (900, 4.0, ["https://example.com/tutors/"]))
        self.assertEqual(record["provenance"]["demand.gsc_impressions"]["at"], f"{days_ago(2)}T00:00:00+00:00")

    def test_every_ingest_takes_as_of_and_a_bad_date_is_refused(self):
        parser = rs.build_parser()
        for kind, extra in (("keyword-ideas", ["--locale", "en"]), ("serps", ["--locale", "en"]),
                            ("clusters", ["--locale", "en"]), ("gsc", []), ("crawl", []),
                            ("volumes", ["--locale", "en", "--source", "semrush"]), ("posts", [])):
            with self.subTest(kind=kind):
                args = parser.parse_args(["ingest", kind, "file", *extra, "--as-of", "2026-01-31"])
                self.assertEqual(args.as_of, "2026-01-31T00:00:00+00:00")
                self.assertIsNone(parser.parse_args(["ingest", kind, "file", *extra]).as_of)
        self.assertEqual(parser.parse_args(["ingest", "crawl", "f", "--as-of", "2026-01-31T10:00:00Z"]).as_of,
                         "2026-01-31T10:00:00+00:00")
        crawl = self.files["crawl"]
        self.assertIn("in the future", self.cli_fails("ingest", "crawl", crawl, "--as-of", days_ago(-2)))
        self.assertIn("not a date", self.cli_fails("ingest", "crawl", crawl, "--as-of", "last week"))
        summary = self.cli("ingest", "crawl", crawl, "--as-of", days_ago(1))
        self.assertEqual(summary["kept_newer"], 6)  # the store's crawl (file time today) is newer


class PostsTest(StoreCase):
    def test_posts_of_a_csv_export_are_never_proposed_again(self):
        become = self.cluster_of("how to become an english tutor")
        export = self.input_file("posts.csv", "URL,Title,Status,Publish date\n"
                                              "https://example.com/blog/become-an-english-tutor/,"
                                              "How to Become an English Tutor in 2026,published,2026-09-01\n"
                                              "https://example.com/blog/tutor-jobs/,English tutor jobs in London,drafted,\n"
                                              "https://other-site.test/blog/x/,Elsewhere,published,\n")
        summary = self.cli("ingest", "posts", export)
        self.assertEqual((summary["added"], summary["skipped_other_site"], summary["without_cluster"]), (2, 1, 0))
        report = self.cli("next-topics", "--locale", "en")
        heads = [t["head_keyword"] for t in report["topics"]]
        self.assertNotIn("how to become an english tutor", heads)
        self.assertIn("english tutor", heads)  # the jobs post names it too, but the longer "english tutor jobs" wins
        self.assertEqual(report["excluded"], {"post": 1, "skip": 1})
        self.assertEqual(report["covered_by_posts"], [{"cluster_id": become["cluster_id"],
                                                       "head_keyword": "how to become an english tutor",
                                                       "posts": ["https://example.com/blog/become-an-english-tutor/"]}])
        posts = {p["url"]: p for p in self.cli("export", "posts", "--format", "json")}
        first = posts["https://example.com/blog/become-an-english-tutor/"]
        self.assertEqual((first["status"], first["publish_date"], first["slug"], first["cluster_id"], first["locale"]),
                         ("published", "2026-09-01", "become-an-english-tutor", become["cluster_id"], "en"))
        self.assertEqual(posts["https://example.com/blog/tutor-jobs/"]["status"], "drafted")
        self.assertEqual(self.cli("status")["gaps"]["en"]["posts"], {"count": 2, "without_cluster": 0})
        before = store_bytes(self.dir)
        self.cli("ingest", "posts", export)
        self.assertEqual(store_bytes(self.dir), before, "re-ingesting the same export changes no byte")

    def test_posts_by_slug_from_json_before_the_clusters_exist(self):
        directory = self.fresh("posts-first", "en,ka")
        later = days_ago(-10)
        export = self.input_file("posts.json", [
            {"slug": "english-tutor-near-me", "locale": "en", "title": "Find a tutor near you", "status": "",
             "publish_date": later},
            {"url": "https://example.com/ka/blog/%E1%83%99%E1%83%A3%E1%83%A0%E1%83%A1%E1%83%94%E1%83%91%E1%83%98/",
             "title": "ინგლისური ენის კურსები & ფასები", "status": "scheduled", "date": later + "T09:00:00"},
        ])
        self.assertEqual(self.cli_in(directory, "ingest", "posts", export)["without_cluster"], 2)
        self.cli_in(directory, "ingest", "clusters", self.files["clusters"], "--locale", "en")
        self.cli_in(directory, "ingest", "clusters", self.input_file("ka.json", {"clusters": [
            {"id": 0, "keywords": ["ინგლისური ენის კურსები"]}]}), "--locale", "ka")
        near = next(c for c in self.load(directory).clusters.values() if c["head_keyword"] == "english tutor near me")
        en = self.cli_in(directory, "next-topics", "--locale", "en")
        self.assertEqual(en["covered_by_posts"], [{"cluster_id": near["cluster_id"], "head_keyword": near["head_keyword"],
                                                   "posts": ["english-tutor-near-me"]}])
        self.assertEqual(self.cli_in(directory, "next-topics", "--locale", "ka")["excluded"], {"post": 1})
        posts = self.cli_in(directory, "export", "posts", "--format", "json")
        self.assertEqual([(p["locale"], p["status"], p["title"]) for p in posts],
                         [("en", "scheduled", "Find a tutor near you"),
                          ("ka", "scheduled", "ინგლისური ენის კურსები & ფასები")])
        self.assertEqual(posts[1]["slug"], "კურსები")

    def test_a_post_at_a_cluster_target_covers_it_and_newer_exports_win(self):
        cluster = self.cluster_of("english tutor")
        older = self.input_file("old.csv", "url,title,status\nhttps://example.com/tutors/,Our lessons,drafted\n",
                                age_days=3)
        newer = self.input_file("new.csv", "url,title,status\nhttps://example.com/tutors/,Our lessons,published\n")
        self.cli("ingest", "posts", newer)
        self.assertEqual(self.cli("ingest", "posts", older)["kept_newer"], 1)
        self.assertEqual(self.cli("export", "posts", "--format", "json")[0]["status"], "published")
        self.assertIn({"cluster_id": cluster["cluster_id"], "head_keyword": "english tutor",
                       "posts": ["https://example.com/tutors/"]}, self.cli("next-topics")["covered_by_posts"])

    def test_the_seo_blog_review_post_inventory_is_ingested(self):
        inventory = self.input_file("review-posts.csv", "cluster,lang,url,indexable,canonical,title,word_count,"
                                                        "date_published,date_modified\n"
                                                        "1,ka,https://example.com/ka/blog/x/,true,,ინგლისური ენის "
                                                        "კურსები ონლაინ,900,2026-09-01,2026-09-02\n")
        self.assertEqual(self.cli("ingest", "posts", inventory)["without_cluster"], 1)  # ka has no clusters yet
        post = self.cli("export", "posts", "--locale", "ka", "--format", "json")[0]
        self.assertEqual((post["locale"], post["status"], post["publish_date"], post["slug"]),
                         ("ka", "published", "2026-09-01", "x"))

    def test_an_hreflang_code_with_a_region_counts_as_its_language(self):
        # seo-blog-review's lang column is the page's hreflang code as declared (translation_check.py)
        inventory = self.input_file("review-posts-region.csv", "cluster,lang,url,title,date_published\n"
                                                               "1,en-GB,https://example.com/blog/a/,A post,2026-09-01\n"
                                                               "1,ka-GE,https://example.com/ka/blog/x/,პოსტი,2026-09-01\n")
        self.assertEqual(self.cli("ingest", "posts", inventory)["added"], 2)
        self.assertEqual([p["locale"] for p in self.cli("export", "posts", "--format", "json")], ["en", "ka"])
        german = self.input_file("review-posts-de.csv", "lang,url\nde-DE,https://example.com/de/blog/x/\n")
        stderr = self.cli_fails("ingest", "posts", german)
        self.assertIn("locale 'de' is not in this store", stderr)
        self.assertNotIn("de-de", stderr)

    def test_cms_column_and_status_names_are_not_read(self):
        # only plain columns, seo-blog-review's inventory and the store's own statuses are read
        export = self.input_file("cms.csv", "url,post_title,post_status,post_date,published_at\n"
                                            "https://example.com/blog/a/,A post,draft,2026-09-01,2026-09-01\n")
        self.cli("ingest", "posts", export)
        post = self.cli("export", "posts", "--format", "json")[0]
        self.assertEqual((post["title"], post["status"], post["publish_date"]), ("", "published", ""))
        for status in ("publish", "future", "draft", "pending", "private", "trash"):
            with self.subTest(status=status):
                rows = self.input_file(f"{status}.csv", f"url,status\nhttps://example.com/blog/b/,published\n"
                                                        f"https://example.com/blog/c/,{status}\n")
                self.assertIn(f"row 2 status {status!r} must be one of planned, briefed, drafted, scheduled, published",
                              self.cli_fails("ingest", "posts", rows))
        wordpress = self.input_file("wp.csv", "post_name,link,permalink\na,https://example.com/blog/a/,"
                                              "https://example.com/blog/a/\n")
        self.assertIn("no url or slug column", self.cli_fails("ingest", "posts", wordpress))
        rest = self.input_file("rest.json", [{"url": "https://example.com/blog/d/", "title": {"rendered": "D"}}])
        self.assertIn("row 1 title must be text", self.cli_fails("ingest", "posts", rest))

    def test_bad_posts_exports_fail_with_a_message(self):
        slug_only = self.input_file("slug.csv", "slug,title\nsome-post,Some post\n")
        self.assertIn("pass --locale", self.cli_fails("ingest", "posts", slug_only))
        self.assertEqual(self.cli("ingest", "posts", slug_only, "--locale", "ka")["added"], 1)
        self.assertIn("no url or slug column", self.cli_fails("ingest", "posts", self.input_file("x.csv", "title\nA\n")))


class NextTopicsTest(StoreCase):
    def test_order_scores_reasons_and_exclusions(self):
        report = self.cli("next-topics", "--locale", "en")
        self.assertIn("[heuristic", report["heuristic"])
        heads = [t["head_keyword"] for t in report["topics"]]
        # "english tutor" targets /tutors/ only because GSC sends it the impressions, so it stays, as a refresh (below)
        self.assertEqual(heads, ["how to become an english tutor", "english tutor near me", "english tutor"])
        first, second, _ = report["topics"]
        self.assertEqual(first["scores"], {"intent_fit": 3, "demand": 2, "serp_gap": 3, "cannibalisation": 0})
        self.assertEqual(first["priority"], 8)
        self.assertEqual(first["brief"], "briefs/en/how-to-become-an-english-tutor.md")
        self.assertEqual(len(first["paa"]), 2)
        self.assertEqual(second["scores"], {"intent_fit": 0, "demand": 3, "serp_gap": 0, "cannibalisation": 1})
        self.assertTrue(any("1900 (semrush" in r for r in second["reasons"]))
        self.assertTrue(any("find-a-tutor" in r for r in second["reasons"]))
        self.assertEqual(second["interlinks"][0]["head_keyword"], "english tutor")
        self.assertEqual(report["excluded"], {"skip": 1})  # the jobs cluster
        self.assertEqual(len(self.cli("next-topics", "--limit", "1")["topics"]), 1)

    def test_a_gsc_inferred_live_target_stays_as_a_refresh_and_a_declared_one_leaves(self):
        cluster = self.cluster_of("english tutor")
        self.assertEqual((cluster["target_url"], cluster["target_source"]), ("https://example.com/tutors/", "gsc"))
        topic = next(t for t in self.cli("next-topics")["topics"] if t["cluster_id"] == cluster["cluster_id"])
        self.assertTrue(any(r.startswith("cannibalisation -1: refresh https://example.com/tutors/ rather than add a page")
                            for r in topic["reasons"]), topic["reasons"])
        self.cli("set-status", "--cluster", cluster["cluster_id"], "--status", "planned", "--url",
                 "https://example.com/tutors/")
        self.assertEqual(self.cluster_of("english tutor")["target_source"], "set-status")
        self.assertEqual(self.cli("next-topics", "--locale", "en")["excluded"], {"live_target": 1, "skip": 1})

    def test_a_weak_or_home_gsc_page_never_becomes_a_target(self):
        path = self.input_file("weak.csv", "query,page,clicks,impressions,ctr,position\n"
                                           "how to become an english tutor,https://example.com/,0,1,0%,80\n"
                                           "english tutor near me,https://example.com/blog/near/,0,40,0%,25\n"
                                           "english tutor jobs,https://example.com/,1,100,1%,5\n")
        self.cli("ingest", "gsc", path)
        for keyword in ("how to become an english tutor", "english tutor near me", "english tutor jobs"):
            self.assertIsNone(self.keyword(keyword)["target_url"], keyword)
        report = self.cli("next-topics", "--locale", "en")
        self.assertEqual(report["topics"][0]["head_keyword"], "how to become an english tutor")
        self.assertNotIn("live_target", report["excluded"])

    def test_brief_slugs_never_collide(self):
        directory = self.fresh("slugs", "en")
        groups = [{"id": i, "keywords": [k]} for i, k in enumerate(("c tutor", "c++ tutor", "c# tutor"))]
        self.cli_in(directory, "ingest", "clusters", self.input_file("c.json", {"clusters": groups}), "--locale", "en")
        os.makedirs(os.path.join(directory, "briefs", "en"))
        write_file(os.path.join(directory, "briefs", "en", "c-tutor.md"), "# brief\n")
        topics = {t["head_keyword"]: t for t in self.cli_in(directory, "next-topics")["topics"]}
        self.assertEqual({head: t["brief"] for head, t in topics.items()},
                         {"c tutor": "briefs/en/c-tutor.md", "c++ tutor": "briefs/en/c-tutor-en-002.md",
                          "c# tutor": "briefs/en/c-tutor-en-003.md"})
        self.assertEqual({head: t["brief_exists"] for head, t in topics.items()},
                         {"c tutor": True, "c++ tutor": False, "c# tutor": False})

    def test_a_brief_keeps_its_path_once_the_cluster_leaves_planned(self):
        directory = self.fresh("frozen", "en")
        groups = {"clusters": [{"id": 0, "keywords": ["c tutor", "c tutor online"]}, {"id": 1, "keywords": ["c++ tutor"]}]}
        self.cli_in(directory, "ingest", "clusters", self.input_file("c2.json", groups), "--locale", "en")
        brief = {t["cluster_id"]: t["brief"] for t in self.cli_in(directory, "next-topics")["topics"]}
        self.assertEqual(brief, {"en-001": "briefs/en/c-tutor.md", "en-002": "briefs/en/c-tutor-en-002.md"})
        os.makedirs(os.path.join(directory, "briefs", "en"))
        write_file(os.path.join(directory, brief["en-002"]), "# brief\n")
        self.cli_in(directory, "set-status", "--cluster", "en-002", "--status", "briefed")
        self.assertEqual(self.load(directory).clusters["en-002"]["brief_slug"], "c-tutor-en-002")
        # a volume re-picks the head of en-001, still planned: the brief of en-002 stays where it was written
        volume = self.input_file("c-vol.csv", "Keyword,Volume\nc tutor online,900\n")
        self.cli_in(directory, "ingest", "volumes", volume, "--locale", "en", "--source", "semrush")
        topics = {t["cluster_id"]: t for t in self.cli_in(directory, "next-topics")["topics"]}
        self.assertEqual(topics["en-001"]["brief"], "briefs/en/c-tutor-online.md")
        self.assertEqual((topics["en-002"]["brief"], topics["en-002"]["brief_exists"]), (brief["en-002"], True))
        # the other way round: a frozen name is taken, so an earlier planned cluster that comes to share it moves
        directory = self.fresh("frozen-first", "en")
        self.cli_in(directory, "ingest", "volumes", volume, "--locale", "en", "--source", "semrush")
        self.cli_in(directory, "ingest", "clusters", self.input_file("c3.json", groups), "--locale", "en")
        brief = {t["cluster_id"]: t["brief"] for t in self.cli_in(directory, "next-topics")["topics"]}
        self.assertEqual(brief, {"en-001": "briefs/en/c-tutor-online.md", "en-002": "briefs/en/c-tutor.md"})
        self.cli_in(directory, "set-status", "--cluster", "en-002", "--status", "drafted")
        self.cli_in(directory, "ingest", "volumes", self.input_file("c-vol2.csv", "Keyword,Volume\nc tutor,5000\n"),
                    "--locale", "en", "--source", "semrush")
        brief = {t["cluster_id"]: t["brief"] for t in self.cli_in(directory, "next-topics")["topics"]}
        self.assertEqual(brief, {"en-001": "briefs/en/c-tutor-en-001.md", "en-002": "briefs/en/c-tutor.md"})

    def test_a_home_or_low_ranking_gsc_page_is_no_cannibalisation(self):
        path = self.input_file("gsc-weak-pages.csv", "query,page,clicks,impressions,ctr,position\n"
                                                     "how to become an english tutor,https://example.com/,2,60,3%,6\n"
                                                     "how to become an english tutor,https://example.com/blog/x/,0,40,0%,45\n")
        self.cli("ingest", "gsc", path)
        self.assertEqual(self.keyword("how to become an english tutor")["demand"]["gsc_pages"], [])
        topic = next(t for t in self.cli("next-topics")["topics"] if t["head_keyword"] == "how to become an english tutor")
        self.assertEqual((topic["target_url"], topic["scores"]["cannibalisation"]), (None, 0), topic["reasons"])

    def test_limit_must_be_positive(self):
        for value in ("0", "-1"):
            self.assertIn("must be 1 or more", self.cli_fails("next-topics", "--limit", value))

    def test_cannibalisation_counts_competing_pages_and_titles(self):
        store = self.load(self.dir)
        cluster = next(c for c in store.clusters.values() if c["head_keyword"] == "english tutor")
        score = rs.score_cluster(store, cluster, rs.scoring_context(store))
        # two of our URLs get impressions (−2), /blog/find-a-tutor/ has the head in its title (−1) and the target is a
        # live page GSC inferred (−1, refresh it), capped at 3; the SERP's www.example.com/tutors/ is the target itself
        self.assertEqual(score["scores"], {"intent_fit": 1, "demand": 4, "serp_gap": -1, "cannibalisation": 3})
        self.assertEqual(score["priority"], 1)
        self.assertEqual(store.clusters[cluster["cluster_id"]]["priority"], 1)  # saved with the store


class SetStatusTest(StoreCase):
    def test_cluster_status_and_url_flow_to_its_keywords(self):
        cluster = self.cluster_of("how to become an english tutor")
        url = "https://example.com/blog/become-an-english-tutor/"
        result = self.cli("set-status", "--cluster", cluster["cluster_id"], "--status", "briefed", "--url", url)
        self.assertEqual(result["keywords_updated"], 1)
        record = self.keyword("how to become an english tutor")
        self.assertEqual((record["status"], record["target_url"]), ("briefed", url))
        topic = self.cli("next-topics")["topics"][0]
        self.assertEqual((topic["status"], topic["target_url"]), ("briefed", url))

    def test_published_cluster_leaves_next_topics(self):
        cluster = self.cluster_of("how to become an english tutor")
        self.cli("set-status", "--cluster", cluster["cluster_id"], "--status", "published")
        report = self.cli("next-topics")
        self.assertEqual([t["head_keyword"] for t in report["topics"]], ["english tutor near me", "english tutor"])
        self.assertEqual(report["excluded"]["published"], 1)

    def test_scheduled_sits_between_drafted_and_published_and_leaves_next_topics(self):
        self.assertEqual(rs.STATUSES.index("scheduled"), rs.STATUSES.index("drafted") + 1)
        self.assertEqual(rs.STATUSES.index("published"), rs.STATUSES.index("scheduled") + 1)
        cluster = self.cluster_of("how to become an english tutor")
        self.cli("set-status", "--cluster", cluster["cluster_id"], "--status", "scheduled", "--url",
                 "https://example.com/blog/become-an-english-tutor/")
        report = self.cli("next-topics", "--locale", "en")
        self.assertNotIn(cluster["cluster_id"], [t["cluster_id"] for t in report["topics"]])
        self.assertEqual(report["excluded"]["scheduled"], 1)
        self.assertEqual(self.keyword("how to become an english tutor")["status"], "scheduled")

    def test_keyword_status_alone(self):
        self.cli("set-status", "--keyword", "English Tutor Online", "--locale", "en", "--status", "skip")
        self.assertEqual(self.keyword("english tutor online")["status"], "skip")
        self.assertEqual(self.cluster_of("english tutor")["status"], "planned")

    def test_unknown_targets_and_statuses_fail(self):
        self.assertIn("no cluster", self.cli_fails("set-status", "--cluster", "en-999", "--status", "briefed"))
        self.assertIn("needs --locale", self.cli_fails("set-status", "--keyword", "english tutor", "--status", "skip"))
        self.assertIn("invalid choice", self.cli_fails("set-status", "--cluster", "en-001", "--status", "done"))


class GlossaryTest(StoreCase):
    def test_add_show_and_omitted_fields_are_kept(self):
        self.cli("glossary", "add", "--locale", "ka", "--term", "Claude", "--translation", "Claude",
                 "--do-not-translate", "--note", "brand name")
        self.cli("glossary", "add", "--locale", "ka", "--term", "tutor", "--translation", "რეპეტიტორი")
        self.cli("glossary", "add", "--locale", "ka", "--term", "Claude", "--translation", "Claude")
        terms = self.cli("glossary", "show", "--locale", "ka")["terms"]
        self.assertEqual(terms["Claude"], {"translation": "Claude", "note": "brand name", "do_not_translate": True})
        self.assertEqual(terms["tutor"]["translation"], "რეპეტიტორი")
        self.assertEqual(self.load(self.dir).manifest["datasets"]["glossary"]["records"], 2)
        self.assertEqual(self.cli("status")["gaps"]["ka"]["glossary_terms"], 2)


class ExportTest(StoreCase):
    def test_keywords_csv_filtered_by_locale(self):
        rows = list(csv.DictReader(io.StringIO(self.cli("export", "keywords", "--locale", "ka", "--format", "csv"))))
        self.assertEqual(list(rows[0]), rs.KEYWORD_COLUMNS)
        self.assertEqual({r["locale"] for r in rows}, {"ka"})
        self.assertEqual(len(rows), 3)

    def test_clusters_and_inventory(self):
        clusters = self.cli("export", "clusters", "--format", "json")
        self.assertEqual([c["cluster_id"] for c in clusters], sorted(c["cluster_id"] for c in clusters))
        inventory = list(csv.DictReader(io.StringIO(self.cli("export", "inventory", "--format", "csv"))))
        self.assertEqual(list(inventory[0]), rs.INVENTORY_COLUMNS)
        self.assertEqual([r["locale"] for r in inventory], sorted(r["locale"] for r in inventory))
        tutors = next(r for r in inventory if r["url"] == "https://example.com/tutors/")
        self.assertEqual((tutors["gsc_impressions"], tutors["status"]), ("292", "200"))


if __name__ == "__main__":
    unittest.main()
