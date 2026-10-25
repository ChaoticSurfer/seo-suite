"""claude_seo.py: clones AgriciDaniel/claude-seo into seo-suite's data folder, pulls main before each use, sets up its
runtime, and runs its tools (rendering, Search Console, technical drift).

Run: python3 -m unittest discover -s tests
No network: git, claude-seo's launcher, its venv Python and Chrome are stand-ins that record their arguments.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "claude_seo.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import claude_seo  # noqa: E402
from triage import FINDING_TABLE  # noqa: E402

PY = sys.executable

FAKE_GIT = f"""#!{PY}
import json, os, shutil, sys
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps({{"git": args}}) + "\\n")
fail = os.environ.get("FAKE_GIT_FAIL", "")
if args[0] == "clone":
    if fail == "clone":
        sys.stderr.write("fatal: unable to access 'https://github.com/AgriciDaniel/claude-seo.git/': Could not resolve host\\n")
        sys.exit(128)
    shutil.copytree(os.environ["FAKE_TEMPLATE"], args[-1])
    os.makedirs(os.path.join(args[-1], ".git"))
    sys.exit(0)
if args[0] == "-C" and args[2] == "pull":
    if fail == "pull":
        sys.stderr.write("fatal: unable to access 'https://github.com/AgriciDaniel/claude-seo.git/': Could not resolve host\\n")
        sys.exit(1)
    sys.exit(0)
if args[0] == "-C" and args[2] == "rev-parse":
    print("6be93f45064ffbadced572b5d5c95f55fd263af0")
    sys.exit(0)
sys.exit(99)
"""

FAKE_LAUNCHER = f"""#!{PY}
import json, os, sys
args = sys.argv[1:]
data = os.environ["CLAUDE_PLUGIN_DATA"]
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps({{"launcher": args, "data": data, "seo_data_dir": os.environ.get("CLAUDE_SEO_DATA_DIR")}}) + "\\n")
state = os.path.join(data, "fake-state.json")
if args[0] == "doctor":
    status = json.load(open(state)) if os.path.exists(state) else {{"ready": False, "browser_ready": False}}
    print(json.dumps(status))
    sys.exit(0 if status["ready"] else 3)
if args[0] == "setup":
    print("Creating isolated Claude SEO environment...")
    if os.environ.get("FAKE_SETUP_FAIL"):
        sys.stderr.write("Claude SEO setup failed: dependency installation failed with exit code 1\\n")
        sys.exit(1)
    os.makedirs(data, exist_ok=True)
    json.dump({{"ready": True, "browser_ready": True}}, open(state, "w"))
    sys.exit(0)
tool, rest = args[1], args[2:]
if tool == "render_page.py":
    if os.environ.get("FAKE_RENDER_FAIL"):
        sys.stderr.write("Error: net::ERR_NAME_NOT_RESOLVED\\n")
        sys.exit(1)
    with open(rest[rest.index("-o") + 1], "w") as fh:
        fh.write("<html><body><h1>rendered by playwright</h1></body></html>")
    sys.exit(0)
if tool == "drift_compare.py":
    answer = json.load(open(os.environ["FAKE_DRIFT"]))[rest[0]]
    print(json.dumps(answer))
    sys.exit(1 if "error" in answer else 0)
if tool == "gsc_query.py" and os.environ.get("FAKE_GSC"):
    print(open(os.environ["FAKE_GSC"]).read())
    sys.exit(0)
if tool == "drift_baseline.py":
    print(json.dumps({{"status": "ok", "baseline_id": 7, "url": rest[0]}}))
    sys.exit(0)
print(json.dumps({{"tool": tool, "args": rest}}))
sys.exit(int(os.environ.get("FAKE_TOOL_EXIT", "0")))
"""

# Shaped after claude-seo's scripts/google_auth.py: the flow reads the module-level OAUTH_SCOPES, which asks for the
# Indexing API scope by default.
FAKE_GOOGLE_AUTH = """
import json, os
OAUTH_SCOPES = ("https://www.googleapis.com/auth/indexing https://www.googleapis.com/auth/webmasters "
                "https://www.googleapis.com/auth/analytics.readonly")
SCOPES = {"gsc_readonly": "https://www.googleapis.com/auth/webmasters.readonly",
          "gsc_write": "https://www.googleapis.com/auth/webmasters",
          "indexing": "https://www.googleapis.com/auth/indexing"}

def run_oauth_flow(creds_path):
    with open(os.environ["FAKE_GOOGLE_OUT"], "w") as fh:
        json.dump({"scope": OAUTH_SCOPES, "creds": creds_path}, fh)

class _Call:
    def __init__(self, kwargs):
        self.kwargs = kwargs
    def execute(self):
        with open(os.environ["FAKE_GOOGLE_OUT"], "w") as fh:
            json.dump(self.kwargs, fh)
        return {}

class _Sitemaps:
    def submit(self, **kwargs):
        return _Call(kwargs)

class _Service:
    def sitemaps(self):
        return _Sitemaps()

def build_service(api_name, version, scopes):
    if os.environ.get("FAKE_NO_CREDENTIALS"):
        return None
    with open(os.environ["FAKE_GOOGLE_OUT"] + ".scopes", "w") as fh:
        json.dump({"api": api_name, "version": version, "scopes": scopes}, fh)
    return _Service()
"""

FAKE_CHROME = """#!/bin/sh
printf "%s\\n" "$@" > "$0.args"
for a; do case "$a" in --user-data-dir=*) [ -d "${a#*=}" ] && echo yes > "$0.profile";; esac; done
echo "<html><body><h1>rendered by chrome</h1></body></html>"
"""


class ClaudeSeoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])
        self.data = os.path.join(self.tmp, "data")
        self.bin = os.path.join(self.tmp, "bin")
        self.log = os.path.join(self.tmp, "calls.jsonl")
        template = os.path.join(self.tmp, "template")
        os.makedirs(os.path.join(template, "scripts"))
        os.makedirs(self.bin)
        self.write(os.path.join(self.bin, "git"), FAKE_GIT, executable=True)
        self.write(os.path.join(template, "scripts", "claude-seo"), FAKE_LAUNCHER, executable=True)
        self.write(os.path.join(template, "scripts", "google_auth.py"), FAKE_GOOGLE_AUTH)
        self.env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin", "HOME": self.tmp, "SEO_SUITE_DATA": self.data,
                    "FAKE_LOG": self.log, "FAKE_TEMPLATE": template, "CHROME": os.path.join(self.tmp, "no-chrome")}

    @staticmethod
    def write(path, text, executable=False):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        if executable:
            os.chmod(path, 0o755)

    def run_helper(self, *args, **env):
        return subprocess.run([PY, SCRIPT, *args], env={**self.env, **env}, cwd=self.tmp, capture_output=True,
                              text=True, timeout=60)

    def calls(self, kind):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as fh:
            return [entry for entry in map(json.loads, fh) if kind in entry]

    @property
    def clone(self):
        return os.path.join(self.data, "vendor", "claude-seo")

    @property
    def runtime(self):
        return os.path.join(self.data, "claude-seo-runtime")

    def mark_ready(self, browser=True):
        os.makedirs(self.runtime, exist_ok=True)
        self.write(os.path.join(self.runtime, "fake-state.json"), json.dumps({"ready": True, "browser_ready": browser}))

    # -- install, update, setup

    def test_first_use_clones_main_into_the_data_folder_and_sets_up_the_runtime(self):
        proc = self.run_helper("ensure")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        clone = self.calls("git")[0]["git"]
        self.assertEqual(clone[:4], ["clone", "--branch", "main", "--single-branch"])
        self.assertEqual(clone[-2:], ["https://github.com/AgriciDaniel/claude-seo.git", self.clone])
        launcher = [c["launcher"][0] for c in self.calls("launcher")]
        self.assertEqual(launcher, ["doctor", "setup", "doctor"])
        self.assertEqual({c["data"] for c in self.calls("launcher")}, {self.runtime})
        report = json.loads(proc.stdout)
        self.assertEqual(report["commit"], "6be93f45064ffbadced572b5d5c95f55fd263af0")
        self.assertTrue(report["browser_ready"])

    def test_every_later_use_pulls_main_and_skips_a_ready_setup(self):
        self.run_helper("ensure")
        os.remove(self.log)
        proc = self.run_helper("ensure")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls("git")[0]["git"], ["-C", self.clone, "pull", "--ff-only"])
        self.assertEqual([c["launcher"][0] for c in self.calls("launcher")], ["doctor"])

    def test_the_location_comes_from_seo_suites_data_folder(self):
        hooks_data = os.path.join(self.tmp, "hooks-data")
        env = {k: v for k, v in self.env.items() if k != "SEO_SUITE_DATA"}
        proc = subprocess.run([PY, SCRIPT, "ensure"], env={**env, "CLAUDE_PLUGIN_DATA": hooks_data,
                                                          "CLAUDE_SEO_DATA_DIR": "/elsewhere"},
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.isdir(os.path.join(hooks_data, "vendor", "claude-seo")))
        self.assertEqual({c["data"] for c in self.calls("launcher")}, {os.path.join(hooks_data, "claude-seo-runtime")})
        self.assertEqual({c["seo_data_dir"] for c in self.calls("launcher")}, {None}, "claude-seo's own override leaks")

    def test_missing_git_fails_loudly(self):
        os.remove(os.path.join(self.bin, "git"))
        proc = self.run_helper("ensure", PATH=self.bin)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("git", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_no_network_fails_loudly_with_gits_reason(self):
        for step in ("clone", "pull"):
            with self.subTest(step=step):
                if step == "pull":
                    self.run_helper("ensure")
                proc = self.run_helper("run", "gsc_query.py", "sites", FAKE_GIT_FAIL=step)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("Could not resolve host", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)

    def test_a_failed_setup_fails_loudly_with_its_reason(self):
        proc = self.run_helper("ensure", FAKE_SETUP_FAIL="1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("dependency installation failed", proc.stderr)

    def test_setup_reruns_when_chromium_is_missing_and_a_render_needs_it(self):
        self.run_helper("ensure")
        self.mark_ready(browser=False)
        os.remove(self.log)
        self.assertEqual(self.run_helper("ensure").returncode, 0)
        self.assertEqual([c["launcher"][0] for c in self.calls("launcher")], ["doctor"], "only rendering needs Chromium")
        os.remove(self.log)
        self.assertEqual(self.run_helper("ensure", "--browser").returncode, 0)
        self.assertEqual([c["launcher"][0] for c in self.calls("launcher")], ["doctor", "setup", "doctor"])

    # -- run

    def test_run_passes_the_tool_and_its_arguments_through(self):
        proc = self.run_helper("run", "gsc_query.py", "--property", "sc-domain:example.com", "--json",
                               FAKE_TOOL_EXIT="4")
        self.assertEqual(proc.returncode, 4)
        self.assertEqual(json.loads(proc.stdout), {"tool": "gsc_query.py",
                                                   "args": ["--property", "sc-domain:example.com", "--json"]})

    def test_run_never_uses_the_indexing_api(self):
        for args in (["indexing_notify.py", "https://example.com/"], ["google_auth.py", "--auth", "--creds", "c.json"]):
            with self.subTest(tool=args[0]):
                proc = self.run_helper("run", *args)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("Indexing API", proc.stderr)
                self.assertEqual(self.calls("launcher"), [], "refused before anything ran")
        self.assertEqual(self.run_helper("run", "google_auth.py", "--check", "gsc").returncode, 0)

    # -- render

    def test_render_writes_the_playwright_dom_for_render_diff(self):
        out = os.path.join(self.tmp, "rendered.html")
        proc = self.run_helper("render", "https://example.com/", "-o", out)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        run = [c["launcher"] for c in self.calls("launcher") if c["launcher"][0] == "run"]
        self.assertEqual(run, [["run", "render_page.py", "https://example.com/", "--mode", "always", "-o", out]])
        with open(out, encoding="utf-8") as fh:
            self.assertIn("rendered by playwright", fh.read())
        report = json.loads(proc.stdout)
        self.assertEqual(report["engine"], "claude-seo render_page.py")
        self.assertEqual(report["rendered"], out)

    def test_render_falls_back_to_headless_chrome_only_when_setup_fails(self):
        chrome = os.path.join(self.tmp, "chrome-stub")
        self.write(chrome, FAKE_CHROME, executable=True)
        out = os.path.join(self.tmp, "rendered.html")
        proc = self.run_helper("render", "https://example.com/", "-o", out, FAKE_SETUP_FAIL="1", CHROME=chrome)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["engine"], "chrome-headless")
        self.assertIn("dependency installation failed", report["fallback_reason"])
        with open(out, encoding="utf-8") as fh:
            self.assertIn("rendered by chrome", fh.read())
        with open(chrome + ".args", encoding="utf-8") as fh:
            args = fh.read().split("\n")[:-1]
        self.assertEqual(args[-2:], ["--dump-dom", "https://example.com/"])
        self.assertIn("--headless", args)
        for flag in ("--virtual-time-budget", "--timeout"):
            self.assertTrue(any(arg.startswith(flag + "=") for arg in args), args)
        profile = next(arg for arg in args if arg.startswith("--user-data-dir="))
        self.assertTrue(os.path.exists(chrome + ".profile"), "the profile didn't exist while Chrome ran")
        self.assertFalse(os.path.exists(profile.split("=", 1)[1]), "the profile is left behind")

    def test_render_with_no_setup_and_no_chrome_says_rendering_was_not_checked(self):
        out = os.path.join(self.tmp, "rendered.html")
        proc = self.run_helper("render", "https://example.com/", "-o", out, FAKE_SETUP_FAIL="1")
        self.assertEqual(proc.returncode, 1)
        report = json.loads(proc.stdout)
        self.assertIn("JavaScript rendering not checked", report["error"])
        self.assertIn("dependency installation failed", report["error"])
        self.assertFalse(os.path.exists(out))

    def test_a_page_that_fails_to_render_does_not_fall_back(self):
        chrome = os.path.join(self.tmp, "chrome-stub")
        self.write(chrome, FAKE_CHROME, executable=True)
        out = os.path.join(self.tmp, "rendered.html")
        proc = self.run_helper("render", "https://example.com/", "-o", out, FAKE_RENDER_FAIL="1", CHROME=chrome)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERR_NAME_NOT_RESOLVED", json.loads(proc.stdout)["error"])
        self.assertFalse(os.path.exists(chrome + ".args"), "Chrome is the fallback for a failed setup only")

    def test_chrome_that_never_settles_is_killed_at_the_cap(self):
        chrome = os.path.join(self.tmp, "chrome-stub")
        self.write(chrome, "#!/bin/sh\nexec sleep 30\n", executable=True)
        out = os.path.join(self.tmp, "rendered.html")
        original = claude_seo.CHROME_KILL_SECONDS
        claude_seo.CHROME_KILL_SECONDS = 1
        self.addCleanup(setattr, claude_seo, "CHROME_KILL_SECONDS", original)
        result = claude_seo.render_with_chrome(chrome, "https://example.com/", out)
        self.assertIn("killed", result["error"])
        self.assertFalse(os.path.exists(out))

    # -- technical drift: one snapshot per crawl run

    def write_crawl_csv(self, urls):
        path = os.path.join(self.tmp, "pages.csv")
        rows = ["url,depth,status"] + [f"{url},0,200" for url in urls + [urls[0]]]  # a repeated row is one URL
        self.write(path, "\n".join(rows) + "\n")
        return path

    def test_drift_compares_each_crawled_url_and_baselines_new_ones(self):
        a, b, c = "https://example.com/", "https://example.com/new/", "https://example.com/broken/"
        drift = {
            a: {"status": "ok", "url": a, "baseline_id": 3, "summary": {"critical": 1, "warning": 1, "info": 0},
                "triggered_findings": [
                    {"rule": "noindex_added", "severity": "CRITICAL", "triggered": True, "old_value": "index",
                     "new_value": "noindex", "message": "noindex directive added"},
                    {"rule": "title_changed", "severity": "WARNING", "triggered": True, "old_value": "Old",
                     "new_value": "New", "message": "Title changed"}]},
            b: {"error": "No baseline found for https://example.com/new. Run `drift baseline` first."},
            c: {"error": "Fetch failed: HTTP 503"},
        }
        fake = os.path.join(self.tmp, "drift.json")
        self.write(fake, json.dumps(drift))
        proc = self.run_helper("drift", "--crawl-csv", self.write_crawl_csv([a, b, c]), "--workers", "1",
                               FAKE_DRIFT=fake)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snapshot = json.loads(proc.stdout)
        self.assertEqual(snapshot["urls"], 3)
        self.assertEqual({p["url"]: p["action"] for p in snapshot["pages"]},
                         {a: "compared", b: "baselined", c: "error"})
        self.assertEqual([f["id"] for f in snapshot["findings"]],
                         ["technical-drift-critical", "technical-drift-warning"])
        self.assertIn(a, snapshot["findings"][0]["message"])
        self.assertIn("noindex", snapshot["findings"][0]["evidence"])
        tools = [c["launcher"][1:3] for c in self.calls("launcher") if c["launcher"][0] == "run"]
        self.assertIn(["drift_baseline.py", b], tools)
        self.assertNotIn(["drift_baseline.py", a], tools, "a compared page keeps its known-good baseline")
        compare = next(c["launcher"] for c in self.calls("launcher") if c["launcher"][1:2] == ["drift_compare.py"])
        self.assertIn("--skip-cwv", compare)

    def test_drift_rebaseline_takes_a_new_baseline_for_every_url(self):
        urls = ["https://example.com/", "https://example.com/a/"]
        proc = self.run_helper("drift", "--crawl-csv", self.write_crawl_csv(urls), "--rebaseline")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual({p["action"] for p in json.loads(proc.stdout)["pages"]}, {"baselined"})
        tools = [c["launcher"][1] for c in self.calls("launcher") if c["launcher"][0] == "run"]
        self.assertEqual(sorted(tools), ["drift_baseline.py", "drift_baseline.py"])

    def test_every_drift_finding_id_has_a_triage_row(self):
        self.assertEqual(sorted(set(claude_seo.DRIFT_FINDING_IDS.values()) - set(FINDING_TABLE)), [])

    # -- Search Console data as the CSV gsc_analyze.py, rank_snapshot.py and research_store.py read

    def test_gsc_export_writes_a_query_page_csv_for_our_analysis(self):
        answer = {"property": "sc-domain:example.com", "row_count": 2, "error": None, "warnings": [],
                  "totals": {"clicks": 30, "impressions": 1000}, "totals_complete": True,
                  "rows": [{"keys": ["tbilisi tours", "https://example.com/"], "query": "tbilisi tours",
                            "page": "https://example.com/", "clicks": 25, "impressions": 600, "ctr": 4.17,
                            "position": 3.2},
                           {"keys": ["kazbegi", "https://example.com/k/"], "query": "kazbegi",
                            "page": "https://example.com/k/", "clicks": 5, "impressions": 400, "ctr": 1.25,
                            "position": 8.9}]}
        fake = os.path.join(self.tmp, "gsc.json")
        self.write(fake, json.dumps(answer))
        out = os.path.join(self.tmp, "query_page.csv")
        proc = self.run_helper("gsc-export", "--property", "sc-domain:example.com", "--start-date", "2026-09-25",
                               "--end-date", "2026-10-22", "--dimensions", "query,page", "-o", out, FAKE_GSC=fake)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        query = next(c["launcher"] for c in self.calls("launcher") if c["launcher"][1:2] == ["gsc_query.py"])
        self.assertEqual(query[2:], ["--property", "sc-domain:example.com", "--start-date", "2026-09-25",
                                     "--end-date", "2026-10-22", "--dimensions", "query,page", "--limit", "25000",
                                     "--json"])
        from gsc_analyze import load_rows
        rows = load_rows(out)
        self.assertEqual([(r["query"], r["page"], r["clicks"]) for r in rows],
                         [("tbilisi tours", "https://example.com/", 25), ("kazbegi", "https://example.com/k/", 5)])
        self.assertAlmostEqual(rows[0]["ctr"], 0.0417)
        self.assertEqual(json.loads(proc.stdout)["rows"], 2)

    def test_gsc_export_without_a_sign_in_names_the_fix(self):
        fake = os.path.join(self.tmp, "gsc.json")
        self.write(fake, json.dumps({"rows": [], "error": "Could not build GSC service. Check service account "
                                                         "credentials."}))
        proc = self.run_helper("gsc-export", "--property", "sc-domain:example.com", "--start-date", "2026-09-25",
                               "--end-date", "2026-10-22", "-o", os.path.join(self.tmp, "q.csv"), FAKE_GSC=fake)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("google-signin", proc.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "q.csv")))

    # -- Search Console sign-in and sitemap submission, never the Indexing API scope

    def venv_python(self):
        bin_dir = os.path.join(self.runtime, ".venv", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        os.symlink(PY, os.path.join(bin_dir, "python"))

    def test_google_signin_asks_only_for_search_console_scopes(self):
        self.run_helper("ensure")
        self.venv_python()
        out = os.path.join(self.tmp, "google.json")
        for flags, scope in (([], "https://www.googleapis.com/auth/webmasters.readonly"),
                             (["--sitemap-write"], "https://www.googleapis.com/auth/webmasters")):
            with self.subTest(flags=flags):
                proc = self.run_helper("google-signin", "--client-secret", "client.json", *flags, FAKE_GOOGLE_OUT=out)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                with open(out, encoding="utf-8") as fh:
                    seen = json.load(fh)
                self.assertEqual(seen["scope"], scope)
                self.assertNotIn("indexing", seen["scope"])
                self.assertEqual(os.path.realpath(seen["creds"]), os.path.realpath(os.path.join(self.tmp, "client.json")))

    def test_submit_sitemap_uses_the_search_console_write_scope(self):
        self.run_helper("ensure")
        self.venv_python()
        out = os.path.join(self.tmp, "google.json")
        proc = self.run_helper("submit-sitemap", "--site", "sc-domain:example.com", "--sitemap",
                               "https://example.com/sitemap.xml", FAKE_GOOGLE_OUT=out)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"siteUrl": "sc-domain:example.com",
                                             "feedpath": "https://example.com/sitemap.xml"})
        with open(out + ".scopes", encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["scopes"], ["https://www.googleapis.com/auth/webmasters"])
        proc = self.run_helper("submit-sitemap", "--site", "sc-domain:example.com", "--sitemap",
                               "https://example.com/sitemap.xml", FAKE_GOOGLE_OUT=out, FAKE_NO_CREDENTIALS="1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("google-signin --client-secret", proc.stderr)


if __name__ == "__main__":
    unittest.main()
