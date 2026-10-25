#!/usr/bin/env python3
"""Audit a site's build output offline: find the stack and the folder it serves, then run page_audit.py's checks on
every built page under its real URL. For fixes checked before deploy, and for CI.

Usage:
  build_audit.py REPO [--base-url https://example.com] [--max-pages 500] [--fail-on high]
Stack detection (detect_stack) and served-root discovery (find_static_root) are ported from AEOTester,
shapito27/aeotester-site-audit skills/audit/scripts/lib/site.mjs (MIT, Ruslan Saifullin).
Modes: full (pages audited), needs-build (a framework with no build output yet: the note names the build command),
report-only (WordPress or another database CMS: pages aren't in the repo), no-pages (no HTML found).
Outputs JSON like crawl.py (page_issue_summary, worst_pages) for triage.py, without crawl.py's link-graph checks.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse

from crawl import summarize_page_issues
from page_audit import audit_page
from seo_lib import SEVERITY_ORDER, extract_page, load_local, print_json

MAX_FILE_BYTES = 2 * 1024 * 1024
SKIP_DIRS = {"node_modules", ".git", ".hg", ".svn", "vendor", "bower_components", ".cache", ".next", ".astro",
             ".vercel", ".netlify", ".wrangler", "coverage", ".idea", ".vscode"}
CONVENTIONAL_STATIC_ROOTS = ("public", "site", "www", "docs", "dist", "build", "src", "html", "_site")
STATIC_ROOT_SEARCH_DEPTH = 4
ERROR_PAGE_RE = re.compile(r"^(?:404|500|50x)\.html?$", re.IGNORECASE)
HTML_RE = re.compile(r"\.html?$", re.IGNORECASE)
CANONICAL_RE = re.compile(r"<link[^>]+rel=[\"']?canonical[\"']?[^>]*href=[\"']([^\"']+)", re.IGNORECASE)
OG_URL_RE = re.compile(r"<meta[^>]+property=[\"']og:url[\"'][^>]*content=[\"']([^\"']+)", re.IGNORECASE)
NO_BASE_URL = "https://localhost"


def read_text(path: str) -> str | None:
    if not os.path.isfile(path) or os.path.getsize(path) > MAX_FILE_BYTES:
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def read_json(path: str) -> dict:
    text = read_text(path)
    if text is None:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_existing(root: str, names: list[str]) -> str | None:
    return next((name for name in names if os.path.exists(os.path.join(root, name))), None)


def walk_files(folder: str, max_depth: int = 12):
    """Files under folder in name order, skipping dependency, VCS and dot folders (but not .well-known)."""
    for base, dirs, files in os.walk(folder):
        depth = os.path.relpath(base, folder).count(os.sep) + (base != folder)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and (not d.startswith(".") or d == ".well-known")
                         and depth < max_depth)
        for name in sorted(files):
            yield os.path.join(base, name)


def has_html(folder: str) -> bool:
    return os.path.isdir(folder) and any(HTML_RE.search(path) for path in walk_files(folder, STATIC_ROOT_SEARCH_DEPTH))


def detect_stack(root: str) -> dict:
    """The site's stack: id, evidence, and for built sites the output folders, source public folder and build command."""
    pkg = read_json(os.path.join(root, "package.json"))
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    npm_build = "npm run build" if (pkg.get("scripts") or {}).get("build") else None

    def built(stack_id, evidence, output_dirs, source_public_dir, build_command):
        return {"id": stack_id, "evidence": evidence, "output_dirs": output_dirs,
                "source_public_dir": source_public_dir, "build_command": build_command}

    wordpress = first_existing(root, ["wp-config.php", "wp-config-sample.php", "wp-content", "wp-includes"])
    theme_css = read_text(os.path.join(root, "style.css")) or ""
    if wordpress or re.search(r"Theme Name:", theme_css, re.IGNORECASE) or (
            os.path.exists(os.path.join(root, "functions.php")) and os.path.exists(os.path.join(root, "index.php"))):
        return {"id": "wordpress", "evidence": wordpress or "WordPress theme files (style.css / functions.php)"}
    composer = read_text(os.path.join(root, "composer.json")) or ""
    if (re.search(r"drupal/core|craftcms/cms|statamic/cms|joomla", composer, re.IGNORECASE)
            or (pkg.get("engines") or {}).get("ghost") or "ghost" in deps):
        return {"id": "other-cms", "evidence": "database-backed CMS (composer.json / Ghost theme)"}

    config = first_existing(root, ["next.config.js", "next.config.mjs", "next.config.ts", "next.config.cjs"])
    if config or "next" in deps:
        return built("nextjs", config or "next in package.json", ["out", ".next/server/app", ".next/server/pages"],
                     "public", npm_build)
    config = first_existing(root, ["astro.config.mjs", "astro.config.js", "astro.config.ts", "astro.config.mts"])
    if config or "astro" in deps:
        return built("astro", config or "astro in package.json", ["dist"], "public", npm_build)
    config = first_existing(root, ["hugo.toml", "hugo.yaml", "hugo.yml", "hugo.json"])
    legacy = first_existing(root, ["config.toml", "config.yaml", "config.yml"])
    if config or (legacy and first_existing(root, ["layouts", "themes"]) and os.path.exists(os.path.join(root, "content"))):
        return built("hugo", config or f"{legacy} + content/", ["public"], "static", "hugo")
    config = first_existing(root, [".eleventy.js", "eleventy.config.js", "eleventy.config.mjs", "eleventy.config.cjs"])
    if config or "@11ty/eleventy" in deps:
        return built("eleventy", config or "@11ty/eleventy in package.json", ["_site"], None,
                     npm_build or "npx @11ty/eleventy")
    config = first_existing(root, ["vite.config.js", "vite.config.mjs", "vite.config.ts", "vite.config.mts"])
    if config or "vite" in deps:
        return built("vite-spa", config or "vite in package.json", ["dist"], "public", npm_build)
    return {"id": "static-html", "evidence": "plain HTML files"}


def find_static_root(root: str) -> str | None:
    """The folder a static host serves at "/": the root, a conventional folder, else the shallowest with an index."""
    if os.path.exists(os.path.join(root, "index.html")):
        return "."
    for folder in CONVENTIONAL_STATIC_ROOTS:
        if os.path.exists(os.path.join(root, folder, "index.html")):
            return folder
    found = [os.path.relpath(os.path.dirname(path), root).replace(os.sep, "/")
             for path in walk_files(root, STATIC_ROOT_SEARCH_DEPTH) if re.search(r"[\\/]index\.html?$", path, re.I)]
    return min(found, key=lambda rel: rel.count("/"), default=None)


def url_path_for(rel_file: str) -> str:
    path = "/" + rel_file
    return re.sub(r"index\.html?$", "", path, flags=re.IGNORECASE) if re.search(r"/index\.html?$", path, re.I) else path


def page_files(served: str) -> list[str]:
    """Built HTML pages relative to the served folder, shallowest first and index first; error pages left out."""
    files = [os.path.relpath(path, served).replace(os.sep, "/") for path in walk_files(served) if HTML_RE.search(path)]
    files.sort(key=lambda rel: (rel.count("/"), 0 if re.search(r"(^|/)index\.html?$", rel, re.I) else 1, rel))
    return [rel for rel in files if not ERROR_PAGE_RE.match(rel)]


def guess_base_url(root: str, served: str, home: str | None) -> str | None:
    """The site's origin from the home page's canonical or og:url, else a CNAME file."""
    text = read_text(os.path.join(served, home)) if home else None
    match = text and (CANONICAL_RE.search(text) or OG_URL_RE.search(text))
    if match:
        parts = urllib.parse.urlsplit(match.group(1))
        if parts.scheme in ("http", "https") and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    for folder in (served, root):
        cname = (read_text(os.path.join(folder, "CNAME")) or "").strip()
        if cname:
            return f"https://{cname.split()[0]}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="the site's repo or project folder")
    ap.add_argument("--base-url", help="the live origin, e.g. https://example.com (guessed when omitted)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--fail-on", choices=("critical", "high", "medium", "low"),
                    help="exit 1 if any page has a finding this severe (for CI)")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    stack = detect_stack(root)
    report = {"root": root, "stack": stack, "mode": "full", "served_root": None, "base_url": None, "total_pages": 0,
              "pages_audited": 0, "notes": [], "page_issue_summary": [], "worst_pages": []}
    if stack["id"] in ("wordpress", "other-cms"):
        report["mode"] = "report-only"
        report["notes"].append("Content lives in a database, so pages can't be audited from the repo: audit the live "
                               "site with crawl.py.")
    elif stack.get("output_dirs"):
        report["served_root"] = next((d for d in stack["output_dirs"] if has_html(os.path.join(root, d))), None)
        if not report["served_root"]:
            report["mode"] = "needs-build"
            build = f" with `{stack['build_command']}`" if stack["build_command"] else ""
            report["notes"].append(f"No build output found ({', '.join(stack['output_dirs'])}). Build the site "
                                   f"first{build}, then re-run.")
    else:
        report["served_root"] = find_static_root(root)
        if not report["served_root"]:
            report["mode"] = "no-pages"
            report["notes"].append("No HTML pages found in this folder.")
    if not report["served_root"]:
        print_json(report)
        return 0

    served = os.path.normpath(os.path.join(root, report["served_root"]))
    files = page_files(served)
    base = (args.base_url or guess_base_url(root, served, files[0] if files else None) or "").rstrip("/")
    if not base:
        base = NO_BASE_URL
        report["notes"].append(f"No base URL found: URLs are under {NO_BASE_URL}, so canonical checks compare "
                               "against it. Pass --base-url.")
    audited = files[:args.max_pages]
    if len(files) > len(audited):
        report["notes"].append(f"Audited the first {len(audited)} of {len(files)} pages (--max-pages).")
    per_page = {}
    for rel in audited:
        url = base + url_path_for(rel)
        per_page[url] = audit_page(extract_page(load_local(os.path.join(served, rel), url)), from_file=True)
    report["page_issue_summary"], report["worst_pages"] = summarize_page_issues(per_page)
    report.update(base_url=base, total_pages=len(files), pages_audited=len(audited))
    print_json(report)
    worst = min((SEVERITY_ORDER[f.severity] for findings in per_page.values() for f in findings), default=None)
    return 1 if args.fail_on and worst is not None and worst <= SEVERITY_ORDER[args.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
