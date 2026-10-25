"""Docs consistency: every skill has the agreed shape, every script/flag the docs mention really exists, and no
section of google-rules.md goes unchecked for more than about six months."""
import datetime
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
REQUIRED_SECTIONS = ["## When to use", "## Workflow", "## Data: free vs paid", "## Output", "## Log the work"]
ROUTER_SKILL = "seo-suite"  # the router has its own shape: level detection, routing table, shared rules
GOOGLE_RULES = os.path.join(ROOT, "references", "google-rules.md")
GOOGLE_RULES_MAX_AGE_DAYS = 183  # about six months: re-check a section against its sources before it expires
SECTION_CHECKED = re.compile(r"\(checked (\d{4}-\d{2}-\d{2})\)$")
CLAUDE_SEO_TOOL = re.compile(r"\brun [a-z_]+\.py\b")  # claude_seo.py run TOOL ...: the flags after TOOL are claude-seo's
SCRIPT_CALL = re.compile(r"(?:scripts|\$S\"?)/([a-z_]+\.py)((?:[^\n`|]*))")  # also "$S/x.py" after S=…/scripts


def markdown_files():
    for base, _, files in os.walk(ROOT):
        if os.path.relpath(base, ROOT).split(os.sep)[0] in ("tests", ".git", "project-reports"):  # local, per-project output
            continue
        for name in files:
            if name.endswith(".md"):
                yield os.path.join(base, name)


def script_flags(script: str) -> set[str]:
    with open(os.path.join(SCRIPTS, script), encoding="utf-8") as fh:
        return set(re.findall(r'add_argument\("(--[a-z0-9-]+)"', fh.read()))


class DocsTest(unittest.TestCase):
    def test_scans_the_docs(self):
        self.assertGreater(len(list(markdown_files())), 20, "markdown_files() must actually find the docs")

    def test_skills_have_frontmatter_and_sections(self):
        skills_dir = os.path.join(ROOT, "skills")
        for name in sorted(n for n in os.listdir(skills_dir) if n != ROUTER_SKILL):
            path = os.path.join(skills_dir, name, "SKILL.md")
            with self.subTest(skill=name):
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                front = re.match(r"^---\nname: (.+)\ndescription: (.+?)\n---\n", text, re.S)
                self.assertIsNotNone(front, "frontmatter must start with name + description")
                self.assertEqual(front.group(1).strip(), name)
                self.assertLessEqual(len(front.group(2)), 1024, "description too long")
                for section in REQUIRED_SECTIONS:
                    self.assertIn(section, text)

    def test_referenced_scripts_and_flags_exist(self):
        available = set(os.listdir(SCRIPTS))
        for path in markdown_files():
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for script, rest in SCRIPT_CALL.findall(text):
                with self.subTest(doc=os.path.relpath(path, ROOT), script=script):
                    self.assertIn(script, available)
                    if script == "claude_seo.py":
                        rest = CLAUDE_SEO_TOOL.split(rest)[0]
                    unknown = set(re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*)", rest)) - script_flags(script)
                    self.assertEqual(unknown, set(), f"unknown flags for {script}")

    def test_referenced_reference_files_exist(self):
        for path in markdown_files():
            with open(path, encoding="utf-8") as fh:
                refs = set(re.findall(r"references/([a-z-]+\.md)", fh.read()))
            for ref in refs:
                with self.subTest(doc=os.path.relpath(path, ROOT), ref=ref):
                    self.assertTrue(os.path.exists(os.path.join(ROOT, "references", ref)))

    def test_google_rules_sections_were_checked_recently(self):
        with open(GOOGLE_RULES, encoding="utf-8") as fh:
            headings = re.findall(r"^## (.+)$", fh.read(), re.M)
        self.assertGreater(len(headings), 10, "google-rules.md must keep its numbered sections")
        for heading in headings:
            with self.subTest(section=heading):
                checked = SECTION_CHECKED.search(heading)
                self.assertIsNotNone(checked, "end the heading with (checked YYYY-MM-DD)")
                age = (datetime.date.today() - datetime.date.fromisoformat(checked.group(1))).days
                self.assertLessEqual(age, GOOGLE_RULES_MAX_AGE_DAYS,
                                     "re-check this section against its sources, then update its checked date")


if __name__ == "__main__":
    unittest.main()
