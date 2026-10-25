#!/usr/bin/env python3
"""Run AgriciDaniel/claude-seo's tools from seo-suite: rendering, Search Console and technical drift.

claude-seo is installed on first need and never as a second plugin (no duplicate skills, router or edit hook). Its
main branch is cloned into <data>/vendor/claude-seo and pulled (--ff-only) before every use, never pinned, and its own
`scripts/claude-seo setup` builds its venv and Playwright Chromium (about 150 MB) in <data>/claude-seo-runtime. <data>
is seo-suite's data folder: SEO_SUITE_DATA (the hooks' CLAUDE_PLUGIN_DATA, exported at SessionStart), else
CLAUDE_PLUGIN_DATA, else ~/.claude/plugins/data/seo-suite, the folder the credit guard uses. This helper is standard
library only, so scheduled runs that allow just `Bash(python3 *)` can run it.

Usage:
  claude_seo.py ensure [--browser]        Clone or pull, then set up when needed. Prints the commit and readiness.
  claude_seo.py run TOOL [ARGS ...]       One claude-seo script, e.g. gsc_query.py or gsc_inspect.py.
  claude_seo.py render URL -o FILE        The rendered DOM for render_diff.py, from render_page.py --mode always.
                                          Headless Chrome only when claude-seo can't be installed or set up.
  claude_seo.py drift --crawl-csv pages.csv
                                          Technical drift for every URL of one crawl.py run: each is compared with
                                          its baseline (drift_compare.py), and URLs without one are baselined.
                                          One JSON snapshot per crawl run, findings in triage.py's shape.
  claude_seo.py gsc-export --property sc-domain:example.com --start-date D --end-date D [--dimensions query,page]
                [--country GEO] [--device mobile] -o query_page.csv
                                          Search Analytics rows (gsc_query.py) as the CSV that gsc_analyze.py,
                                          rank_snapshot.py and research_store.py read. The property is always given.
  claude_seo.py google-signin --client-secret FILE [--sitemap-write]
                                          Search Console sign-in through claude-seo's OAuth flow, asking only for
                                          webmasters.readonly (webmasters with --sitemap-write, for autonomy level 4).
  claude_seo.py submit-sitemap --site PROPERTY --sitemap URL

Never the Indexing API: Google allows it only for JobPosting and BroadcastEvent pages, so `run` refuses
indexing_notify.py and google_auth.py --auth (that flow asks for the indexing scope). Fails loudly, with the reason,
when git, Python 3.11-3.14 (claude-seo's range) or the network are missing. Exit 1: claude-seo unavailable or the
step failed; exit 2: refused.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, NamedTuple

from credit_guard import locked
from seo_lib import print_json

REPO_URL = "https://github.com/AgriciDaniel/claude-seo.git"
DOCTOR_NOT_READY = 3  # `claude-seo doctor` exit code for "setup required"
OUTPUT_TAIL_LINES = 15
SEARCH_CONSOLE_READ_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
SEARCH_CONSOLE_WRITE_SCOPE = "https://www.googleapis.com/auth/webmasters"
INDEXING_API_REFUSAL = ("seo-suite never uses the Indexing API: Google allows it only for pages with JobPosting, or "
                        "BroadcastEvent in a VideoObject. Sign in with `claude_seo.py google-signin`, and submit a "
                        "sitemap instead (`claude_seo.py submit-sitemap`, autonomy level 4).")

# drift_compare.py severities -> triage.py ids and seo-suite severities
DRIFT_FINDING_IDS = {"CRITICAL": "technical-drift-critical", "WARNING": "technical-drift-warning",
                     "INFO": "technical-drift-info"}
DRIFT_SEVERITIES = {"CRITICAL": "high", "WARNING": "medium", "INFO": "info"}
DRIFT_NO_BASELINE = "No baseline found"  # drift_compare.py's error for a URL it has never baselined
DRIFT_EVIDENCE_CHARS = 300

# The headless-Chrome fallback: a fresh profile, the default User-Agent (a Googlebot one from a non-Google IP looks
# spoofed), 10 s of page time for scripts and fetches to settle, Chrome stops loading after 30 s of real time, and a
# page whose script never yields is killed at 60 s.
CHROME_APPS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium")
CHROME_COMMANDS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
CHROME_SETTLE_MS = 10000
CHROME_LOAD_CAP_MS = 30000
CHROME_KILL_SECONDS = 60

# Run in claude-seo's venv Python: its own OAuth flow and API client, with seo-suite's scope.
SIGNIN_CODE = """import sys
sys.path.insert(0, sys.argv[1])
import google_auth
if not isinstance(getattr(google_auth, "OAUTH_SCOPES", None), str) or not hasattr(google_auth, "run_oauth_flow"):
    sys.exit("claude-seo's google_auth.py no longer has OAUTH_SCOPES and run_oauth_flow: update claude_seo.py")
google_auth.OAUTH_SCOPES = sys.argv[2]
google_auth.run_oauth_flow(sys.argv[3])
"""
SUBMIT_SITEMAP_CODE = """import json, sys
sys.path.insert(0, sys.argv[1])
import google_auth
service = google_auth.build_service("searchconsole", "v1", [sys.argv[2]])
if service is None:
    sys.exit("No Search Console sign-in with the webmasters scope. The user signs in once with: python3 "
             "claude_seo.py google-signin --client-secret client_secret.json --sitemap-write")
service.sitemaps().submit(siteUrl=sys.argv[3], feedpath=sys.argv[4]).execute()
print(json.dumps({"site": sys.argv[3], "sitemap": sys.argv[4], "submitted": True}))
"""


class Unavailable(Exception):
    """claude-seo could not be cloned, updated or set up; the message says why."""


class Paths(NamedTuple):
    data: str
    clone: str
    runtime: str
    launcher: str


def paths(env: Any) -> Paths:
    data = env.get("SEO_SUITE_DATA") or env.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        os.path.expanduser("~"), ".claude", "plugins", "data", "seo-suite")
    clone = os.path.join(data, "vendor", "claude-seo")
    return Paths(data, clone, os.path.join(data, "claude-seo-runtime"), os.path.join(clone, "scripts", "claude-seo"))


def launcher_env(env: Any, where: Paths) -> dict:
    """claude-seo keeps its runtime in CLAUDE_PLUGIN_DATA; its own CLAUDE_SEO_DATA_DIR override would move it."""
    child = {key: value for key, value in env.items() if key != "CLAUDE_SEO_DATA_DIR"}
    child["CLAUDE_PLUGIN_DATA"] = where.runtime
    return child


def tail(text: str) -> str:
    return "\n".join([line for line in text.splitlines() if line.strip()][-OUTPUT_TAIL_LINES:])


def checked(argv: list[str], env: Any, step: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(argv, env=env, capture_output=True, text=True)
    if proc.returncode:
        raise Unavailable(f"{step} failed (exit {proc.returncode}):\n{tail(proc.stderr or proc.stdout)}")
    return proc


def doctor(where: Paths, env: Any) -> dict:
    proc = subprocess.run([where.launcher, "doctor", "--json"], env=launcher_env(env, where), capture_output=True,
                          text=True)
    if proc.returncode not in (0, DOCTOR_NOT_READY):  # e.g. 2: no Python 3.11-3.14 on PATH
        raise Unavailable(f"claude-seo doctor failed (exit {proc.returncode}):\n{tail(proc.stderr or proc.stdout)}")
    return json.loads(proc.stdout)


def usable(status: dict, need_browser: bool) -> bool:
    return bool(status.get("ready")) and (bool(status.get("browser_ready")) or not need_browser)


def ensure(env: Any, need_browser: bool) -> dict:
    """Clone claude-seo's main branch or pull it, then run its setup when its runtime (or Chromium) isn't ready."""
    git = shutil.which("git", path=env.get("PATH"))
    if not git:
        raise Unavailable("git is not installed or not on PATH; claude-seo is cloned with git. Install git and re-run.")
    where = paths(env)
    with locked(os.path.dirname(where.clone)):  # parallel renders must not pull or set up at the same time
        if os.path.isdir(os.path.join(where.clone, ".git")):
            checked([git, "-C", where.clone, "pull", "--ff-only"], env, "git pull of claude-seo main")
        else:
            checked([git, "clone", "--branch", "main", "--single-branch", REPO_URL, where.clone], env,
                    "git clone of claude-seo")
        commit = checked([git, "-C", where.clone, "rev-parse", "HEAD"], env, "git rev-parse").stdout.strip()
        status = doctor(where, env)
        if not usable(status, need_browser):
            print("Setting up claude-seo (a venv and Playwright Chromium, about 150 MB); this takes a few minutes.",
                  file=sys.stderr)
            setup = subprocess.run([where.launcher, "setup"], env=launcher_env(env, where), capture_output=True,
                                   text=True)
            status = doctor(where, env)
            if not usable(status, need_browser):
                raise Unavailable(f"claude-seo setup failed (exit {setup.returncode}):\n"
                                  f"{tail(setup.stderr or setup.stdout)}")
    return {"clone": where.clone, "commit": commit, "runtime": where.runtime, "ready": True,
            "browser_ready": bool(status.get("browser_ready"))}


def run_tool(where: Paths, env: Any, tool: str, args: list[str], **capture: Any) -> subprocess.CompletedProcess:
    return subprocess.run([where.launcher, "run", tool, *args], env=launcher_env(env, where), text=True, **capture)


def uses_indexing_api(tool: str, args: list[str]) -> bool:
    return tool == "indexing_notify.py" or (tool == "google_auth.py" and "--auth" in args)


def cmd_ensure(args: argparse.Namespace, env: Any) -> int:
    print_json(ensure(env, need_browser=args.browser))
    return 0


def cmd_run(args: argparse.Namespace, env: Any) -> int:
    if uses_indexing_api(args.tool, args.tool_args):
        print(f"claude_seo.py: refused {args.tool}. {INDEXING_API_REFUSAL}", file=sys.stderr)
        return 2
    ensure(env, need_browser=False)
    return run_tool(paths(env), env, args.tool, args.tool_args).returncode


# ---------------------------------------------------------------------------------------------------------------- render

def find_chrome(env: Any) -> str | None:
    """CHROME when set (and only it), else the macOS apps, else the Linux binaries on PATH."""
    if env.get("CHROME"):
        return env["CHROME"] if os.access(env["CHROME"], os.X_OK) else None
    for app in CHROME_APPS:
        if os.access(app, os.X_OK):
            return app
    for name in CHROME_COMMANDS:
        found = shutil.which(name, path=env.get("PATH"))
        if found:
            return found
    return None


def render_with_chrome(chrome: str, url: str, output: str) -> dict:
    with tempfile.TemporaryDirectory() as profile:
        argv = [chrome, "--headless", "--use-mock-keychain", f"--user-data-dir={profile}",
                f"--virtual-time-budget={CHROME_SETTLE_MS}", f"--timeout={CHROME_LOAD_CAP_MS}", "--dump-dom", url]
        try:
            with open(output, "w", encoding="utf-8") as fh:
                subprocess.run(argv, stdout=fh, stderr=subprocess.DEVNULL, timeout=CHROME_KILL_SECONDS)
        except subprocess.TimeoutExpired:
            os.remove(output)
            return {"url": url, "error": f"Chrome was killed after {CHROME_KILL_SECONDS} s: the page's scripts never "
                                         "yielded"}
    if os.path.getsize(output) == 0:
        os.remove(output)
        return {"url": url, "error": "Chrome printed no DOM for this URL"}
    return {"url": url, "rendered": output, "engine": "chrome-headless"}


def render_with_claude_seo(env: Any, installed: dict, url: str, output: str) -> dict:
    proc = run_tool(paths(env), env, "render_page.py", [url, "--mode", "always", "-o", output], capture_output=True)
    if proc.returncode or not os.path.exists(output):
        return {"url": url, "error": f"claude-seo render_page.py failed on this URL (exit {proc.returncode}):\n"
                                     f"{tail(proc.stderr or proc.stdout)}"}
    return {"url": url, "rendered": output, "engine": "claude-seo render_page.py",
            "claude_seo_commit": installed["commit"], "render_log": tail(proc.stderr)}


def cmd_render(args: argparse.Namespace, env: Any) -> int:
    try:
        installed = ensure(env, need_browser=True)
    except Unavailable as unavailable:
        chrome = find_chrome(env)
        if chrome:
            result = {**render_with_chrome(chrome, args.url, args.output), "fallback_reason": str(unavailable)}
        else:
            result = {"url": args.url, "error": f"JavaScript rendering not checked: claude-seo is unavailable "
                                                f"({unavailable}) and no Chrome or Chromium was found"}
    else:
        result = render_with_claude_seo(env, installed, args.url, args.output)
    print_json(result)
    return 1 if "error" in result else 0


# ----------------------------------------------------------------------------------------------------- technical drift

def crawl_urls(crawl_csv: str) -> list[str]:
    """Every URL of one crawl.py --csv run, once each, in crawl order."""
    with open(crawl_csv, newline="", encoding="utf-8") as fh:
        return list(dict.fromkeys(row["url"] for row in csv.DictReader(fh) if row["url"]))


def run_json_tool(where: Paths, env: Any, tool: str, args: list[str]) -> dict:
    proc = run_tool(where, env, tool, args, capture_output=True)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"{tool} printed no JSON (exit {proc.returncode}):\n{tail(proc.stderr or proc.stdout)}"}


def drift_page(where: Paths, env: Any, url: str, rebaseline: bool) -> dict:
    if not rebaseline:
        compared = run_json_tool(where, env, "drift_compare.py", [url, "--skip-cwv"])
        if "error" not in compared:
            return {"url": url, "action": "compared", "baseline_id": compared.get("baseline_id"),
                    "summary": compared.get("summary"), "triggered_findings": compared.get("triggered_findings", [])}
        if DRIFT_NO_BASELINE not in compared["error"]:
            return {"url": url, "action": "error", "error": compared["error"]}
    baseline = run_json_tool(where, env, "drift_baseline.py", [url, "--skip-cwv"])
    if "error" in baseline:
        return {"url": url, "action": "error", "error": baseline["error"]}
    return {"url": url, "action": "baselined", "baseline_id": baseline.get("baseline_id")}


def drift_findings(pages: list[dict]) -> list[dict]:
    findings = []
    for page in pages:
        for found in page.get("triggered_findings", []):
            evidence = f"{found['rule']}: {found['old_value']!r} -> {found['new_value']!r}"
            findings.append({"id": DRIFT_FINDING_IDS[found["severity"]], "severity": DRIFT_SEVERITIES[found["severity"]],
                             "message": f"{page['url']}: {found['message']}",
                             "evidence": evidence[:DRIFT_EVIDENCE_CHARS]})
    return findings


def cmd_drift(args: argparse.Namespace, env: Any) -> int:
    urls = crawl_urls(args.crawl_csv)
    installed = ensure(env, need_browser=False)
    where = paths(env)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pages = list(pool.map(lambda url: drift_page(where, env, url, args.rebaseline), urls))
    actions = [page["action"] for page in pages]
    print_json({
        "site": urls[0] if urls else "", "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "crawl_csv": args.crawl_csv, "claude_seo_commit": installed["commit"], "urls": len(urls),
        "counts": {action: actions.count(action) for action in ("compared", "baselined", "error")},
        "pages": pages, "findings": drift_findings(pages),
    })
    return 0


# ------------------------------------------------------------------------------------------------------ Search Console

GSC_ROW_LIMIT = 25000  # one Search Analytics request; gsc_query.py pages beyond it


def cmd_gsc_export(args: argparse.Namespace, env: Any) -> int:
    ensure(env, need_browser=False)
    tool_args = ["--property", args.property, "--start-date", args.start_date, "--end-date", args.end_date,
                 "--dimensions", args.dimensions, "--limit", str(args.limit), "--json"]
    tool_args += ["--country", args.country] if args.country else []
    tool_args += ["--device", args.device] if args.device else []
    result = run_json_tool(paths(env), env, "gsc_query.py", tool_args)
    if result.get("error"):
        print(f"gsc_query.py: {result['error']}\nWith no Search Console sign-in yet, the user signs in once with: "
              "python3 claude_seo.py google-signin --client-secret client_secret.json", file=sys.stderr)
        return 1
    dimensions = [name.strip() for name in args.dimensions.split(",") if name.strip()]
    with open(args.output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(dimensions + ["clicks", "impressions", "ctr", "position"])
        for row in result["rows"]:  # gsc_query.py gives ctr in percent
            writer.writerow([row[name] for name in dimensions]
                            + [row["clicks"], row["impressions"], f"{row['ctr']}%", row["position"]])
    print_json({"property": args.property, "start_date": args.start_date, "end_date": args.end_date,
                "dimensions": dimensions, "rows": len(result["rows"]), "totals": result.get("totals"),
                "totals_complete": result.get("totals_complete"), "warnings": result.get("warnings", []),
                "csv": args.output})
    return 0


def venv_python(where: Paths) -> str:
    python = os.path.join(where.runtime, ".venv", "Scripts" if os.name == "nt" else "bin",
                          "python.exe" if os.name == "nt" else "python")
    if not os.path.exists(python):
        raise Unavailable(f"claude-seo's runtime has no Python at {python}; its layout changed: update claude_seo.py")
    return python


def cmd_google_signin(args: argparse.Namespace, env: Any) -> int:
    ensure(env, need_browser=False)
    where = paths(env)
    scope = SEARCH_CONSOLE_WRITE_SCOPE if args.sitemap_write else SEARCH_CONSOLE_READ_SCOPE
    return subprocess.run([venv_python(where), "-c", SIGNIN_CODE, os.path.join(where.clone, "scripts"), scope,
                           os.path.abspath(args.client_secret)], env=launcher_env(env, where)).returncode


def cmd_submit_sitemap(args: argparse.Namespace, env: Any) -> int:
    ensure(env, need_browser=False)
    where = paths(env)
    return subprocess.run([venv_python(where), "-c", SUBMIT_SITEMAP_CODE, os.path.join(where.clone, "scripts"),
                           SEARCH_CONSOLE_WRITE_SCOPE, args.site, args.sitemap], env=launcher_env(env, where)).returncode


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    ensure_cmd = sub.add_parser("ensure", help="clone or pull claude-seo, then set it up when needed")
    ensure_cmd.add_argument("--browser", action="store_true", help="also require Playwright Chromium")
    ensure_cmd.set_defaults(handler=cmd_ensure)
    run_cmd = sub.add_parser("run", help="run one claude-seo script")
    run_cmd.add_argument("tool", help="a claude-seo script name, e.g. gsc_query.py")
    run_cmd.add_argument("tool_args", nargs=argparse.REMAINDER, help="the script's own arguments")
    run_cmd.set_defaults(handler=cmd_run)
    render_cmd = sub.add_parser("render", help="save the rendered DOM of one URL for render_diff.py")
    render_cmd.add_argument("url")
    render_cmd.add_argument("-o", "--output", required=True, help="file to write the rendered DOM to")
    render_cmd.set_defaults(handler=cmd_render)
    drift_cmd = sub.add_parser("drift", help="technical drift for every URL of one crawl run")
    drift_cmd.add_argument("--crawl-csv", required=True, help="crawl.py --csv output of this run")
    drift_cmd.add_argument("--rebaseline", action="store_true",
                           help="take a new baseline for every URL (after verified fixes), comparing nothing")
    drift_cmd.add_argument("--workers", type=int, default=4, help="URLs checked in parallel")
    drift_cmd.set_defaults(handler=cmd_drift)
    export_cmd = sub.add_parser("gsc-export", help="Search Console rows as a CSV for gsc_analyze.py")
    export_cmd.add_argument("--property", required=True, help="the Search Console property, e.g. sc-domain:example.com")
    export_cmd.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    export_cmd.add_argument("--end-date", required=True, help="YYYY-MM-DD (Search Console lags 2-3 days)")
    export_cmd.add_argument("--dimensions", default="query,page", help="comma-separated: query, page, country, device, date")
    export_cmd.add_argument("--country", help="ISO 3166-1 alpha-3 filter, e.g. GEO")
    export_cmd.add_argument("--device", choices=("desktop", "mobile", "tablet"))
    export_cmd.add_argument("--limit", type=int, default=GSC_ROW_LIMIT, help="most rows to fetch")
    export_cmd.add_argument("-o", "--output", required=True, help="the CSV to write")
    export_cmd.set_defaults(handler=cmd_gsc_export)
    signin_cmd = sub.add_parser("google-signin", help="Search Console OAuth sign-in (webmasters.readonly)")
    signin_cmd.add_argument("--client-secret", required=True, help="the OAuth client JSON from Google Cloud")
    signin_cmd.add_argument("--sitemap-write", action="store_true",
                            help="ask for the webmasters scope too, for sitemap submission (autonomy level 4)")
    signin_cmd.set_defaults(handler=cmd_google_signin)
    submit_cmd = sub.add_parser("submit-sitemap", help="submit a sitemap to Search Console (autonomy level 4)")
    submit_cmd.add_argument("--site", required=True, help="the Search Console property, e.g. sc-domain:example.com")
    submit_cmd.add_argument("--sitemap", required=True, help="the sitemap URL")
    submit_cmd.set_defaults(handler=cmd_submit_sitemap)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args, os.environ)
    except Unavailable as unavailable:
        print(f"claude-seo unavailable: {unavailable}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
