#!/usr/bin/env python3
"""Server access-log analysis for search and AI crawlers (Apache/Nginx combined format; .gz accepted).

Shows what Googlebot, Bingbot and AI bots actually request — crawl waste, errors served to bots, and
important URLs that are never crawled. This is first-party data no SEO SaaS has.
Usage:
  log_analyze.py access.log [access.log.1.gz ...]
  log_analyze.py access.log --verify-dns            # reverse+forward DNS check that "Googlebot" is really Google
  log_analyze.py access.log --sitemap-urls urls.txt # sitemap URLs Googlebot never requested
"""
from __future__ import annotations

import argparse
import gzip
import ipaddress
import re
import socket
import sys
import urllib.parse
from collections import Counter, defaultdict

from robots_check import CRAWLERS
from seo_lib import print_json

LINE = re.compile(r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>[A-Z]+) (?P<path>\S+)[^"]*" (?P<status>\d{3}) \S+ "[^"]*" "(?P<ua>[^"]*)"')
# Order matters: more specific tokens first so "Googlebot-Image" is not counted as plain Googlebot.
BOT_TOKENS = ["Googlebot-Image", "Googlebot-Video", "Googlebot-News", "Storebot-Google", "Google-InspectionTool",
              "AdsBot-Google", "GoogleOther"] + sorted(CRAWLERS, key=len, reverse=True)
VERIFIED_DOMAINS = {"Googlebot": (".googlebot.com", ".google.com"), "Bingbot": (".search.msn.com",)}


def bot_of(user_agent: str) -> str | None:
    ua = user_agent.lower()
    for token in BOT_TOKENS:
        if token.lower() in ua:
            return token
    return None


def open_log(path: str):
    return gzip.open(path, "rt", errors="replace") if path.endswith(".gz") else open(path, errors="replace")


def verify_ip(ip: str, domains: tuple[str, ...]) -> bool | None:
    """Reverse DNS must land in the bot's domain and resolve back to the IP. None: no proof either way, because the
    forward lookup failed or the log's host field is a hostname (Apache HostnameLookups On), not an IP."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return None
    try:
        host = socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        return False
    if not host.endswith(domains):
        return False
    try:
        # Without AI_ALL|AI_V4MAPPED macOS drops the AAAA record of IPv6-only hosts, e.g. Googlebot's crawl-2001-4860-….
        infos = socket.getaddrinfo(host, None, flags=socket.AI_ALL | socket.AI_V4MAPPED)
    except socket.gaierror:
        return None
    return address in {ipaddress.ip_address(info[4][0]) for info in infos}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--verify-dns", action="store_true")
    ap.add_argument("--sitemap-urls")
    args = ap.parse_args()

    hits = defaultdict(lambda: {"hits": 0, "status": Counter(), "paths": Counter(), "errors": Counter(), "days": Counter(),
                                "param_hits": 0, "ips": Counter()})
    unparsed = 0
    for path in args.logs:
        with open_log(path) as fh:
            for line in fh:
                m = LINE.match(line)
                if not m:
                    unparsed += 1
                    continue
                bot = bot_of(m["ua"])
                if not bot:
                    continue
                b = hits[bot]
                b["hits"] += 1
                b["status"][m["status"]] += 1
                b["paths"][m["path"]] += 1
                b["days"][m["time"].split(":", 1)[0]] += 1
                b["ips"][m["ip"]] += 1
                if "?" in m["path"]:
                    b["param_hits"] += 1
                if m["status"][0] in "45":
                    b["errors"][f'{m["status"]} {m["path"]}'] += 1

    report = {"unparsed_lines": unparsed, "bots": {}}
    for bot, b in sorted(hits.items(), key=lambda kv: -kv[1]["hits"]):
        entry = {
            "hits": b["hits"], "unique_urls": len(b["paths"]), "status": dict(b["status"]),
            "parameter_url_share": round(b["param_hits"] / b["hits"], 3), "hits_per_day": dict(b["days"]),
            "top_paths": b["paths"].most_common(15), "top_errors": b["errors"].most_common(15),
            "top_sections": Counter("/" + p.lstrip("/").split("/", 1)[0].split("?")[0] for p in b["paths"].elements()).most_common(10),
        }
        if args.verify_dns and bot in VERIFIED_DOMAINS:
            ips = [ip for ip, _ in b["ips"].most_common(30)]
            checks = {ip: verify_ip(ip, VERIFIED_DOMAINS[bot]) for ip in ips}
            entry["unverified_ips"] = [ip for ip, ok in checks.items() if ok is False]
            # no proof either way: forward DNS failed, or the host field is not an IP
            entry["unverifiable_ips"] = [ip for ip, ok in checks.items() if ok is None]
        report["bots"][bot] = entry
    if args.sitemap_urls:
        with open(args.sitemap_urls, encoding="utf-8") as fh:
            wanted = {urllib.parse.urlsplit(u.strip()).path or "/" for u in fh if u.strip()}
        crawled = {urllib.parse.urlsplit(p).path for p in hits["Googlebot"]["paths"]} if "Googlebot" in hits else set()
        never = sorted(wanted - crawled)
        report["sitemap_paths_never_crawled_by_googlebot"] = {"count": len(never), "examples": never[:30]}
    print_json(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
