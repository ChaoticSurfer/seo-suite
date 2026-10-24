"""Research store: init, every ingest format, merge provenance, TTL staleness, next-topics, set-status, glossary and
export. Inputs have the exact shapes keyword_ideas.py, serp_cluster.py, gsc_analyze.py and crawl.py write (the last
three are run for real here). Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import codecs
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

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


def write_file(path: str, content, age_days: float = 0) -> str:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False))
    stamp = time.time() - age_days * DAY
    os.utime(path, (stamp, stamp))
    return path


def crawl_csv() -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CRAWL_HEADER)
    writer.writerows(CRAWL_ROWS)
    return buffer.getvalue()


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
        return result.stderr

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


class NextTopicsTest(StoreCase):
    def test_order_scores_reasons_and_exclusions(self):
        report = self.cli("next-topics", "--locale", "en")
        self.assertIn("[heuristic", report["heuristic"])
        heads = [t["head_keyword"] for t in report["topics"]]
        self.assertEqual(heads, ["how to become an english tutor", "english tutor near me"])
        first, second = report["topics"]
        self.assertEqual(first["scores"], {"intent_fit": 3, "demand": 2, "serp_gap": 3, "cannibalisation": 0})
        self.assertEqual(first["priority"], 8)
        self.assertEqual(first["brief"], "briefs/en/how-to-become-an-english-tutor.md")
        self.assertEqual(len(first["paa"]), 2)
        self.assertEqual(second["scores"], {"intent_fit": 0, "demand": 3, "serp_gap": 0, "cannibalisation": 1})
        self.assertTrue(any("1900 (semrush" in r for r in second["reasons"]))
        self.assertTrue(any("find-a-tutor" in r for r in second["reasons"]))
        self.assertEqual(second["interlinks"][0]["head_keyword"], "english tutor")
        # "english tutor" already has a live page (/tutors/, 200 in the crawl); the jobs cluster is skipped
        self.assertEqual(report["excluded"], {"live_target": 1, "skip": 1})
        self.assertEqual(len(self.cli("next-topics", "--limit", "1")["topics"]), 1)

    def test_cannibalisation_counts_competing_pages_and_titles(self):
        store = self.load(self.dir)
        cluster = next(c for c in store.clusters.values() if c["head_keyword"] == "english tutor")
        score = rs.score_cluster(store, cluster, rs.scoring_context(store))
        # two of our URLs get impressions (−2) and /blog/find-a-tutor/ has the head in its title (−1); the SERP's
        # www.example.com/tutors/ is the target itself, so it is not counted
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
        self.assertEqual([t["head_keyword"] for t in report["topics"]], ["english tutor near me"])
        self.assertEqual(report["excluded"]["published"], 1)

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
