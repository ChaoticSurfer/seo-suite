"""schema_hook.py: the PostToolUse Edit|Write hook that checks JSON-LD in edited markup with schema_rules.py.

Exit 2 (Claude reads stderr) only for JSON-LD that doesn't parse, leftover placeholders and a missing @type. Missing
required or recommended fields come back as additionalContext. Other files exit at once.
Run: python3 -m unittest discover -s tests
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOOK = os.path.join(ROOT, "scripts", "schema_hook.py")


def ld(body: str) -> str:
    return f'<html><head><script type="application/ld+json" nonce="abc">{body}</script></head><body></body></html>'


ARTICLE = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": "Tbilisi in a day",
                      "image": "https://example.com/a.jpg", "datePublished": "2026-10-01",
                      "dateModified": "2026-10-02",
                      "author": {"@type": "Person", "name": "Nino", "url": "https://example.com/nino",
                                 "sameAs": ["https://www.linkedin.com/in/nino"], "jobTitle": "Guide",
                                 "image": "https://example.com/nino.jpg"}})


class SchemaHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])

    def edit(self, name: str, content: str, tool: str = "Write"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        payload = {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": {"file_path": path}}
        return subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True,
                              timeout=30)

    def context(self, proc) -> str:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        output = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUse")
        return output["additionalContext"]

    # -- blocking (exit 2)

    def test_json_ld_that_does_not_parse_blocks(self):
        proc = self.edit("page.html", ld('{"@context": "https://schema.org", "@type": "Article",}'))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("page.html", proc.stderr)
        self.assertIn("does not parse", proc.stderr)

    def test_leftover_placeholders_block(self):
        for value in ("[Business Name]", "[Phone]", "REPLACE_WITH_URL", "[insert address]"):
            with self.subTest(value=value):
                body = json.dumps({"@context": "https://schema.org", "@type": "LocalBusiness", "name": value,
                                   "address": "Rustaveli 1, Tbilisi"})
                proc = self.edit("page.html", ld(body))
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("placeholder", proc.stderr)

    def test_a_missing_type_blocks(self):
        proc = self.edit("page.html", ld(json.dumps({"@context": "https://schema.org", "name": "Geotour"})))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("@type", proc.stderr)

    def test_a_graph_needs_types_on_its_members_not_on_itself(self):
        article = {key: value for key, value in json.loads(ARTICLE).items() if key != "@context"}
        graph = {"@context": "https://schema.org", "@graph": [article]}
        self.assertEqual(self.edit("page.html", ld(json.dumps(graph))).returncode, 0)
        graph["@graph"].append({"name": "untyped"})
        proc = self.edit("page.html", ld(json.dumps(graph)))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("@type", proc.stderr)

    # -- advice (additionalContext, exit 0)

    def test_missing_required_fields_are_advice_that_forbids_inventing_values(self):
        body = json.dumps({"@context": "https://schema.org", "@type": "Product", "name": "Kazbegi tour"})
        text = self.context(self.edit("tour.html", ld(body)))
        self.assertIn("offers", text)
        self.assertIn("tour.html", text)
        self.assertIn("never invent", text)

    def test_an_array_type_is_checked_without_crashing(self):
        body = json.dumps({"@context": "https://schema.org", "@type": ["Product", "Thing"], "name": "Kazbegi tour"})
        self.assertIn("offers", self.context(self.edit("tour.html", ld(body))))

    def test_complete_markup_says_nothing(self):
        proc = self.edit("post.html", ld(ARTICLE))
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "", ""))

    # -- what is skipped

    def test_other_files_exit_at_once(self):
        for name in ("app.py", "notes.txt", "package.json", "tsconfig.json"):
            with self.subTest(name=name):
                proc = self.edit(name, ld('{"broken": ') if not name.endswith(".json") else '{"broken": ')
                self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "", ""))

    def test_the_extension_check_comes_before_any_schema_import(self):
        probe = (f"import sys; sys.path.insert(0, {os.path.dirname(HOOK)!r}); import schema_hook; "
                 "print(sorted(m for m in ('schema_rules', 'seo_lib') if m in sys.modules))")
        proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.stdout.strip(), "[]", proc.stderr)

    def test_template_expressions_are_not_reported_as_broken_json(self):
        cases = {
            "product.liquid": ld("{{ product | json_ld }}"),
            "tour.njk": ld('{"@context": "https://schema.org", "@type": "ItemList", "itemListElement": ['
                           '{% for t in tours %}{"@type": "ListItem", "position": {{ loop.index }}}{% endfor %}]}'),
            "Seo.tsx": ld("{JSON.stringify(schema)}"),
            "page.php": ld("<?php echo json_encode($schema); ?>"),
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                proc = self.edit(name, content)
                self.assertEqual((proc.returncode, proc.stderr), (0, ""))

    def test_json_files_count_only_with_a_schema_org_context(self):
        body = {"@context": "https://schema.org", "@type": "Product", "name": "Kazbegi tour"}
        self.assertIn("offers", self.context(self.edit("product.json", json.dumps(body))))
        self.assertEqual(self.edit("data.json", json.dumps({"name": "x", "@type": "Thing"})).stdout, "")
        proc = self.edit("product.jsonld", '{"@context": "https://schema.org", "@type": "Product",')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("does not parse", proc.stderr)

    def test_a_deleted_file_is_not_an_error(self):
        payload = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(self.tmp, "gone.html")}}
        proc = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "", ""))

    def test_an_unclosed_tag_full_of_quotes_does_not_hang(self):
        content = "<script type=\"application/ld+json\" " + "a='b' " * 20000 + "x"
        started = time.monotonic()
        proc = self.edit("page.html", content)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(time.monotonic() - started, 10)


class SchemaHookConfigTest(unittest.TestCase):
    def test_its_own_hook_entry_never_blocks_unrelated_work(self):
        with open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as fh:
            hooks = json.load(fh)["hooks"]
        entries = [entry for entry in hooks["PostToolUse"]
                   if any("schema_hook.py" in " ".join(h.get("args", [])) for h in entry["hooks"])]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matcher"], "Edit|Write")
        (hook,) = entries[0]["hooks"]
        self.assertEqual(hook["command"], "python3")
        self.assertEqual(hook["onFailure"], "continue")
        self.assertLessEqual(hook["timeout"], 15)


if __name__ == "__main__":
    unittest.main()
