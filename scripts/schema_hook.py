#!/usr/bin/env python3
"""PostToolUse hook for Edit|Write: check the JSON-LD in an edited markup file with schema_rules.py.

hooks/hooks.json runs it with the hook's JSON on stdin. The edit has already happened, so the hook only tells Claude:
  exit 2, stderr        JSON-LD that doesn't parse, leftover placeholders, or an object without @type.
  exit 0, JSON stdout   Google's missing required or recommended fields, and the other schema_rules findings, as
                        additionalContext. "Required" there means required for a rich result, not for valid markup,
                        so it never blocks: blocking would push the model to invent offers, reviews or ratings.
  exit 0, no output     Anything else, at once: other file types (checked before schema_rules loads), JSON files
                        without a schema.org @context, and blocks a template fills at runtime ({{ }}, {% %}, JSX, PHP).
The script-tag, template-expression and placeholder patterns are adapted from AgriciDaniel/claude-seo
hooks/validate-schema.py (MIT).
"""
from __future__ import annotations

import json
import os
import re
import sys

MARKUP_EXTENSIONS = (".html", ".htm", ".astro", ".liquid", ".njk", ".hbs", ".jsx", ".tsx", ".vue", ".svelte", ".php",
                     ".ejs", ".erb", ".twig")
COMPONENT_EXTENSIONS = (".jsx", ".tsx", ".vue", ".svelte", ".astro")
JSON_LD_EXTENSION = ".jsonld"
JSON_EXTENSION = ".json"  # checked only when it declares a schema.org @context
MAX_FILE_BYTES = 10 * 1024 * 1024
NO_INVENTED_VALUES = ("Add a property only with a value the page really shows; never invent offers, reviews, ratings "
                      "or other values to meet a rich-result rule.")

# A quoted attribute value is one token, so a ">" inside it can't end the tag; the unquoted class excludes both quotes,
# so an unclosed tag full of apostrophes can't backtrack exponentially.
_ATTRS = r'(?:"[^"]*"|\'[^\']*\'|[^"\'>])*'
SCRIPT_TAG_RE = re.compile(r"<script\b(" + _ATTRS + r")>(.*?)</script\s*>", re.DOTALL | re.IGNORECASE)
LD_JSON_TYPE_RE = re.compile(r"""(?:^|\s)type\s*=\s*(?:"application/ld\+json"|'application/ld\+json'|"""
                             r"""application/ld\+json(?=\s|$))""", re.IGNORECASE)
# A component's script body that is an expression, not JSON: {schema}, {JSON.stringify(...)}, {@html ...}, ${...}
COMPONENT_EXPRESSION_RE = re.compile(r"^(?:\{\{|\{@html\b|\$\{|\{\s*[A-Za-z_$][\w$.]*)")
TEMPLATE_MARKERS = ("{{", "{%", "<%", "<?", "${")
BRACKET_PLACEHOLDER_RE = re.compile(r"\[(?:your|insert|business name|city|state|phone|address|url|email)\b[^\]]*\]",
                                    re.IGNORECASE)
BARE_PLACEHOLDER_RE = re.compile(r"\bREPLACE(?:_[A-Z]+)*\b")


def file_kind(path: str) -> str:
    """'markup', 'jsonld', 'json', or '' for a file the hook ignores."""
    lower = path.lower()
    if lower.endswith(MARKUP_EXTENSIONS):
        return "markup"
    if lower.endswith(JSON_LD_EXTENSION):
        return "jsonld"
    if lower.endswith(JSON_EXTENSION):
        return "json"
    return ""


def is_runtime_template(body: str, path: str) -> bool:
    return any(marker in body for marker in TEMPLATE_MARKERS) or (
        path.lower().endswith(COMPONENT_EXTENSIONS) and bool(COMPONENT_EXPRESSION_RE.match(body)))


def parsed_blocks(content: str, path: str, kind: str) -> tuple[list[str], list]:
    """(errors, parsed JSON-LD blocks) for one file."""
    if kind == "json":
        if "schema.org" not in content:
            return [], []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return [], []  # a .json file that isn't JSON is not this hook's business
        tops = data if isinstance(data, list) else [data]
        declares_schema_org = any(isinstance(top, dict) and "schema.org" in json.dumps(top.get("@context"))
                                  for top in tops)
        return [], [data] if declares_schema_org else []
    bodies = [content] if kind == "jsonld" else [body.strip() for attributes, body in SCRIPT_TAG_RE.findall(content)
                                                  if LD_JSON_TYPE_RE.search(attributes)]
    errors, blocks = [], []
    for number, body in enumerate(bodies, 1):
        try:
            blocks.append(json.loads(body))
        except json.JSONDecodeError as exc:
            if kind == "markup" and is_runtime_template(body, path):
                continue  # filled in at runtime; nothing to check statically
            errors.append(f"JSON-LD block {number} does not parse: {exc}")
    return errors, blocks


def structure_errors(block, number: int) -> list[str]:
    """Objects without @type (a @graph container needs none, its members do) and leftover placeholders."""
    errors = []
    for top in block if isinstance(block, list) else [block]:
        if isinstance(top, dict) and "@graph" in top:
            members = top["@graph"]
            if not isinstance(members, list):
                errors.append(f"JSON-LD block {number}: @graph must be a list of objects")
                continue
        else:
            members = [top]
        untyped = sum(1 for member in members if not isinstance(member, dict) or "@type" not in member)
        if untyped:
            errors.append(f"JSON-LD block {number}: {untyped} top-level object(s) without @type")
    text = json.dumps(block, ensure_ascii=False)
    for placeholder in sorted(set(BRACKET_PLACEHOLDER_RE.findall(text) + BARE_PLACEHOLDER_RE.findall(text))):
        errors.append(f"JSON-LD block {number}: leftover placeholder {placeholder}")
    return errors


def check_file(content: str, path: str, kind: str) -> tuple[list[str], list[str]]:
    """(blocking errors, advice) for one edited file."""
    from schema_rules import validate_json_ld

    errors, blocks = parsed_blocks(content, path, kind)
    for number, block in enumerate(blocks, 1):
        errors += structure_errors(block, number)
    _, findings = validate_json_ld(blocks)
    advice = [f"[{finding.severity}] {finding.message} ({finding.evidence})" for finding in findings]
    return errors, advice


def main() -> int:
    payload = json.load(sys.stdin)
    path = (payload.get("tool_input") or {}).get("file_path") or ""
    kind = file_kind(path)
    if not kind or not os.path.isfile(path) or os.path.getsize(path) > MAX_FILE_BYTES:
        return 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        errors, advice = check_file(fh.read(), path, kind)
    if errors:
        print(f"JSON-LD in {path} needs fixing:\n" + "\n".join(f"- {line}" for line in errors), file=sys.stderr)
        if advice:
            print("Also, without blocking:\n" + "\n".join(f"- {line}" for line in advice), file=sys.stderr)
        return 2
    if advice:
        context = (f"Schema check of {path} (schema_rules.py):\n" + "\n".join(f"- {line}" for line in advice)
                   + f"\n{NO_INVENTED_VALUES}")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
