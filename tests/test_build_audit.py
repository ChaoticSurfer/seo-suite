"""build_audit.py: AEOTester's static-site stack detection (detectStack, findStaticRoot), ported, and an offline
audit of every built page with page_audit.py's checks, before deploy and in CI.
Run: python3 -m unittest discover -s tests
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "build_audit.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_audit import detect_stack, find_static_root  # noqa: E402

GOOD_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Tbilisi day tours with local guides</title>
<meta name="description" content="Small-group day tours from Tbilisi to Kazbegi, Mtskheta and Kakheti, with hotel pickup.">
<link rel="canonical" href="https://geotour.example/"></head><body><h1>Day tours</h1>
<p>{words}</p><a href="/blog/post/">Kazbegi in a day</a></body></html>""".format(words="word " * 400)
UNTITLED_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"></head><body><h1>Post</h1>
<p>{words}</p></body></html>""".format(words="word " * 400)


class ProjectFolder(unittest.TestCase):
    """A temporary project folder; the tests are in the subclasses."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(subprocess.run, ["rm", "-rf", self.root])

    def touch(self, *names, text=""):
        for name in names:
            path = os.path.join(self.root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)

    def package(self, deps=None, build=True):
        self.touch("package.json", text=json.dumps({"dependencies": deps or {},
                                                     "scripts": {"build": "x"} if build else {}}))


class StackDetectionTest(ProjectFolder):
    def test_framework_config_files_and_dependencies(self):
        cases = [
            (["next.config.mjs"], None, "nextjs", ["out", ".next/server/app", ".next/server/pages"]),
            ([], {"astro": "^5"}, "astro", ["dist"]),
            (["hugo.toml"], None, "hugo", ["public"]),
            ([".eleventy.js"], None, "eleventy", ["_site"]),
            (["vite.config.ts"], None, "vite-spa", ["dist"]),
        ]
        for files, deps, stack_id, output_dirs in cases:
            with self.subTest(stack=stack_id):
                self.root = tempfile.mkdtemp()
                self.addCleanup(subprocess.run, ["rm", "-rf", self.root])
                self.touch(*files)
                if deps:
                    self.package(deps)
                stack = detect_stack(self.root)
                self.assertEqual((stack["id"], stack["output_dirs"]), (stack_id, output_dirs))

    def test_hugo_with_a_legacy_config_needs_content_and_layouts(self):
        self.touch("config.toml")
        self.assertEqual(detect_stack(self.root)["id"], "static-html")
        self.touch("content/_index.md", "layouts/index.html")
        stack = detect_stack(self.root)
        self.assertEqual((stack["id"], stack["build_command"], stack["source_public_dir"]), ("hugo", "hugo", "static"))

    def test_database_cms_sites(self):
        self.touch("wp-content/themes/x/style.css")
        self.assertEqual(detect_stack(self.root)["id"], "wordpress")
        self.root = tempfile.mkdtemp()
        self.addCleanup(subprocess.run, ["rm", "-rf", self.root])
        self.touch("composer.json", text=json.dumps({"require": {"drupal/core": "^11"}}))
        self.assertEqual(detect_stack(self.root)["id"], "other-cms")

    def test_build_command_comes_from_the_package_scripts(self):
        self.package({"next": "15"}, build=True)
        self.assertEqual(detect_stack(self.root)["build_command"], "npm run build")
        self.package({"@11ty/eleventy": "3"}, build=False)
        self.assertEqual(detect_stack(self.root)["build_command"], "npx @11ty/eleventy")

    def test_the_static_root_is_the_shallowest_folder_with_an_index(self):
        self.assertIsNone(find_static_root(self.root))
        self.touch("assets/deep/a/index.html", "site/index.html")
        self.assertEqual(find_static_root(self.root), "site")
        self.touch("index.html")
        self.assertEqual(find_static_root(self.root), ".")

    def test_an_unconventional_folder_is_found_and_node_modules_is_skipped(self):
        self.touch("node_modules/pkg/index.html", "web/root/index.html")
        self.assertEqual(find_static_root(self.root), "web/root")


class BuildAuditTest(ProjectFolder):
    def run_audit(self, *flags):
        proc = subprocess.run([sys.executable, SCRIPT, self.root, *flags], capture_output=True, text=True, timeout=60)
        return proc, json.loads(proc.stdout)

    def test_every_built_page_is_audited_under_its_url(self):
        self.package({"astro": "^5"})
        self.touch("dist/index.html", text=GOOD_PAGE)
        self.touch("dist/blog/post/index.html", text=UNTITLED_PAGE)
        self.touch("dist/404.html", text=UNTITLED_PAGE)
        proc, report = self.run_audit()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((report["stack"]["id"], report["mode"], report["served_root"]), ("astro", "full", "dist"))
        self.assertEqual(report["base_url"], "https://geotour.example", "guessed from the home page's canonical")
        self.assertEqual((report["pages_audited"], report["total_pages"]), (2, 2), "404.html is not a content page")
        missing = next(row for row in report["page_issue_summary"] if row["id"] == "title-missing")
        self.assertEqual((missing["pages"], missing["examples"]), (1, ["https://geotour.example/blog/post/"]))

    def test_fail_on_gates_ci(self):
        self.touch("index.html", text=UNTITLED_PAGE)
        proc, report = self.run_audit("--base-url", "https://geotour.example", "--fail-on", "medium")
        self.assertEqual((proc.returncode, report["stack"]["id"]), (1, "static-html"))
        proc, _ = self.run_audit("--base-url", "https://geotour.example", "--fail-on", "critical")
        self.assertEqual(proc.returncode, 0)

    def test_a_framework_without_build_output_says_how_to_build(self):
        self.package({"astro": "^5"})
        proc, report = self.run_audit()
        self.assertEqual((proc.returncode, report["mode"], report["pages_audited"]), (0, "needs-build", 0))
        self.assertIn("npm run build", " ".join(report["notes"]))

    def test_a_database_cms_is_report_only(self):
        self.touch("wp-config.php")
        _, report = self.run_audit()
        self.assertEqual((report["mode"], report["pages_audited"]), ("report-only", 0))

    def test_max_pages_caps_the_audit_and_says_so(self):
        for name in ("index.html", "a.html", "b.html"):
            self.touch(name, text=GOOD_PAGE)
        _, report = self.run_audit("--max-pages", "2")
        self.assertEqual((report["pages_audited"], report["total_pages"]), (2, 3))
        self.assertIn("first 2 of 3", " ".join(report["notes"]))


if __name__ == "__main__":
    unittest.main()
