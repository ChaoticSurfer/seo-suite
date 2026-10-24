#!/usr/bin/env python3
"""Core Web Vitals field data (CrUX, real Chrome users, p75 over 28 days) + Lighthouse lab audit via the
free PageSpeed Insights API.

Usage:
  psi.py https://example.com/page                 # mobile
  psi.py URL --strategy desktop
  PSI_API_KEY=... psi.py URL                      # optional key: without one the shared quota is small
Outputs JSON: field metrics for the URL and the whole origin with good/needs-improvement/poor ratings,
Lighthouse category scores, and the biggest lab opportunities.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

from seo_lib import Finding, fetch, print_json

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
# metric key in CrUX -> (display name, good upper bound, poor lower bound, divisor to display units)
CWV_THRESHOLDS = {
    "LARGEST_CONTENTFUL_PAINT_MS": ("LCP ms", 2500, 4000, 1),
    "INTERACTION_TO_NEXT_PAINT": ("INP ms", 200, 500, 1),
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": ("CLS", 0.1, 0.25, 100),  # API reports CLS ×100
    "FIRST_CONTENTFUL_PAINT_MS": ("FCP ms", 1800, 3000, 1),
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": ("TTFB ms", 800, 1800, 1),
}
CORE_METRICS = ("LARGEST_CONTENTFUL_PAINT_MS", "INTERACTION_TO_NEXT_PAINT", "CUMULATIVE_LAYOUT_SHIFT_SCORE")


def rate(value: float, good: float, poor: float) -> str:
    if value <= good:
        return "good"
    return "poor" if value > poor else "needs-improvement"


def field_metrics(experience: dict | None) -> dict | None:
    if not experience or "metrics" not in experience:
        return None
    metrics = {}
    for key, (name, good, poor, divisor) in CWV_THRESHOLDS.items():
        if key in experience["metrics"]:
            value = experience["metrics"][key]["percentile"] / divisor
            metrics[name] = {"p75": value, "rating": rate(value, good, poor)}
    core = [metrics[CWV_THRESHOLDS[k][0]]["rating"] for k in CORE_METRICS if CWV_THRESHOLDS[k][0] in metrics]
    # PSI's rules: without LCP or CLS data there is no assessment (None); with too little INP data, LCP and CLS decide.
    passes = all(r == "good" for r in core) if "LCP ms" in metrics and "CLS" in metrics else None
    return {"passes_core_web_vitals": passes, "metrics": metrics, "api_overall_category": experience.get("overall_category")}


def opportunities(lighthouse: dict, limit: int = 8) -> list[dict]:
    rows = []
    for audit in lighthouse.get("audits", {}).values():
        details = audit.get("details") or {}
        savings = details.get("overallSavingsMs") or (audit.get("metricSavings") or {}).get("LCP")
        if savings and audit.get("score") is not None and audit["score"] < 0.9:
            rows.append({"audit": audit["id"], "title": audit.get("title"), "est_savings_ms": round(savings),
                         "display": audit.get("displayValue", "")})
    return sorted(rows, key=lambda r: -r["est_savings_ms"])[:limit]


def failed_seo_audits(lighthouse: dict) -> list[str]:
    refs = lighthouse.get("categories", {}).get("seo", {}).get("auditRefs", [])
    audits = lighthouse.get("audits", {})
    return [audits[r["id"]]["title"] for r in refs if r["id"] in audits and audits[r["id"]].get("score") == 0]


def lcp_element(lighthouse: dict) -> dict:
    # Lighthouse 13 (PSI since Oct 2025) replaced the largest-contentful-paint-element audit with this insight.
    details = lighthouse.get("audits", {}).get("lcp-breakdown-insight", {}).get("details") or {}
    return next((item for item in details.get("items", []) if item.get("type") == "node"), {})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--strategy", choices=("mobile", "desktop"), default="mobile")
    args = ap.parse_args()
    params = [("url", args.url), ("strategy", args.strategy)] + [
        ("category", c) for c in ("performance", "seo", "accessibility", "best-practices")]
    if os.environ.get("PSI_API_KEY"):
        params.append(("key", os.environ["PSI_API_KEY"]))
    result = fetch(f"{PSI_ENDPOINT}?{urllib.parse.urlencode(params)}", timeout=120)
    if result.status != 200:
        hint = ("Keyless requests share one small daily quota. Create a free API key (Google Cloud console → enable "
                "'PageSpeed Insights API' → Credentials → API key) and export PSI_API_KEY.") if result.status == 429 else ""
        print_json({"url": args.url, "error": result.error or f"PSI returned {result.status}", "hint": hint, "body": result.text[:300]})
        return 2
    data = json.loads(result.text)
    lighthouse = data.get("lighthouseResult", {})
    field = field_metrics(data.get("originLoadingExperience"))
    findings = []
    if field and field["passes_core_web_vitals"] is False:
        poor = [f"{name} p75={m['p75']} ({m['rating']})" for name, m in field["metrics"].items() if m["rating"] != "good"
                and name in ("LCP ms", "INP ms", "CLS")]
        findings.append(Finding("cwv-fail", "medium", f"Origin fails Core Web Vitals ({args.strategy}, CrUX p75)", "; ".join(poor)))
    print_json({
        "findings": findings,
        "url": args.url,
        "strategy": args.strategy,
        # PSI marks URL-level data that silently fell back to the origin with origin_fallback=true.
        "field_url": None if data.get("loadingExperience", {}).get("origin_fallback") else field_metrics(data.get("loadingExperience")),
        "field_origin": field_metrics(data.get("originLoadingExperience")),
        "field_note": "No field data means too little Chrome traffic for CrUX; rely on lab data and RUM.",
        "lab_scores": {k: round(v["score"] * 100) for k, v in lighthouse.get("categories", {}).items() if v.get("score") is not None},
        "lab_metrics": {a: lighthouse.get("audits", {}).get(a, {}).get("displayValue")
                        for a in ("largest-contentful-paint", "total-blocking-time", "cumulative-layout-shift", "speed-index",
                                  "server-response-time")},
        "lcp_element": lcp_element(lighthouse),
        "top_opportunities": opportunities(lighthouse),
        "failed_lighthouse_seo_audits": failed_seo_audits(lighthouse),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
