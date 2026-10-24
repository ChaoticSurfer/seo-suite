---
name: seo-international
description: International and multilingual SEO. Covers hreflang (HTML, HTTP header or sitemap), x-default, language and region codes, return links, URL structure (ccTLD vs subdomain vs subfolder), locale-adaptive serving pitfalls, translation quality vs machine translation at scale, per-market keyword research, and currency/address signals. Use when the user says "hreflang", "multilingual site", "translate my site for SEO", "expand to another country", "wrong language showing in Google", "en-GB vs en-US", "Georgian and English versions", "x-default", or "which URL structure for countries". Not for a full audit (use seo-audit), a domain move (seo-migration), general crawling or canonical bugs (seo-technical), or local Business Profile work (seo-local).
---

# International SEO

Show each market's searchers the right language and region version, and make sure Google understands which pages are alternates of each other.

## When to use / not

- **Use for:**
  - Planning a multi-language or multi-country site.
  - Auditing or fixing hreflang.
  - Choosing a URL structure.
  - Researching keywords per market.
  - Reviewing translated content.
- **Not for:**
  - A single-language site serving one country. Nothing here applies beyond `<html lang>`.
  - A Google Business Profile per country: use **seo-local**.

## Inputs: decide, don't ask

Decide each input from evidence, record it under *Assumptions*, and carry on (`${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`).

| Input | Decide from | Default when evidence is thin |
|---|---|---|
| Current markets: language × country pairs (e.g. `ka-GE`, `en-GB`, `ru`), and the fallback | `<html lang>`, ccTLD, hreflang, currency and addresses on the page; the x-default target | The fallback is the version the root URL serves. New markets to enter: a business decision, ask — batched at the end |
| URL structure and hosts: where the alternates live | hreflang alternates, the language switcher's links, the crawl | No alternates yet: recommend subfolders (see Checks) |
| How hreflang is (or will be) emitted: HTML `<link>`, HTTP `Link` header or XML sitemap, and the CMS or framework that does it | `page_audit.py --facts` (`facts.hreflang`, and the `link` header in `facts.response_headers`); `hreflang_links` from `sitemap_check.py`; the repo | No hreflang yet: recommend the method the stack emits most easily |
| How translations are produced: human, machine with human review, or raw machine output | The language review in step 3 `[estimate]` | Unknown: say so, and recommend human review where text reads as machine output |
| Search Console export per country (Performance → Countries filter), Bing/Yandex data where relevant | What's configured or already in the workspace | Run without them. Ask — batched at the end, naming what each adds |

## Workflow

`S="${CLAUDE_PLUGIN_ROOT}/scripts"`.

0. **Read the research store first** (`${CLAUDE_PLUGIN_ROOT}/references/research-store.md`), when `seo-research/` exists:
   ```bash
   mkdir -p seo-work
   python3 "$S/research_store.py" status > seo-work/store-status.json
   python3 "$S/research_store.py" export keywords --locale ka --format csv > seo-work/store-keywords-ka.csv   # once per locale
   ```
   - `seo-research/site.json` → `locales` and `markets` (each market's `hl`, `gl` and `url_prefix`) start the markets and URL-structure inputs. Check them against the pages.
   - Step 5 reuses every locale whose `keywords` are fresh (90-day TTL) and researches only the locales `status` lists as stale or missing. Note what you reused and its age for *Assumptions* and the work log.
1. **Per-page check.** Run this for each language version of a key template, in parallel:
   ```bash
   python3 "$S/page_audit.py" https://example.com/en/pricing > seo-work/intl-en.json
   python3 "$S/page_audit.py" https://example.com/ka/pricing > seo-work/intl-ka.json
   ```
   It flags:
   - `hreflang-invalid`: a code not shaped like an ISO 639-1 language + optional ISO 15924 script + optional ISO 3166-1 alpha-2 region (so `es-419` and `fil` are flagged), plus `UK`/`EU`/`UN` regions. It checks the shape only, not the code lists: a region-only code that looks like a language, such as `gb`, passes, so check each language code by hand.
   - `hreflang-duplicate`.
   - `hreflang-no-self`.
   - `hreflang-no-x-default`.

   Also confirm each version's canonical is **self-referencing**, not pointing at another language.
2. **Cluster reciprocity.** Every alternate must link back, or Google ignores the pair (§6). Start from a hub that links to every language:
   ```bash
   python3 "$S/crawl.py" https://example.com --max-pages 500 > seo-work/intl-crawl.json
   ```
   The crawl reports `hreflang-no-return` when page A lists B but B doesn't list A.
   - **Script gap:** reciprocity is only checked between pages the crawl reached.
   - **Script gap:** hreflang in XML sitemaps isn't checked for reciprocity (HTML `<link>` and HTTP `Link` header hreflang are). `sitemap_check.py` only counts `xhtml:link` alternates (`hreflang_links`).

   For sitemap-based hreflang, read a sample of the sitemap XML and check it by hand.
3. **Language really matches.** Google detects language from **visible content** and ignores `lang` attributes and URLs (§6). Read the main text on each version:
   - Is it actually translated?
   - Are navigation and boilerplate translated?
   - Is it in the declared script (Georgian Mkhedruli for `ka`, not Latin transliteration)?
4. **Locale-adaptive behaviour.** Fetch the same URL with no `Accept-Language` header; `page_audit.py` sends none, just like Googlebot.
   - If the server redirects by IP or language, Googlebot (mostly from US IPs) may only ever see one version (§6).
   - The fix: separate URLs per locale plus hreflang, and a non-forced language suggestion banner instead of an automatic redirect.
5. **Per-market keyword research.** Run this per market whose store keywords are stale or missing (step 0), in parallel. The local language and country codes matter:
   ```bash
   python3 "$S/keyword_ideas.py" "ინგლისურის რეპეტიტორი" --hl ka --gl ge > seo-work/kw-ka-ge.json
   python3 "$S/keyword_ideas.py" "english tutor tbilisi" --hl en --gl ge > seo-work/kw-en-ge.json
   ```
   Never just translate the source keyword list. Check what locals actually type, including script mixing and transliteration (e.g. Georgian users sometimes type Georgian words in Latin letters). Pass the results to **seo-keywords** for clustering.
6. **Triage:**
   ```bash
   python3 "$S/triage.py" seo-work/intl-*.json
   ```
   Map each hreflang issue to the template or generator that emits it. Then fix it in code (diff first) per autonomy level (references/autonomy.md) and re-run step 1.
7. **Write back to the research store.** Each locale's ideas go in under the store locale that version serves:
   ```bash
   python3 "$S/research_store.py" init --site https://example.com --locales en,ka,ru
   python3 "$S/research_store.py" ingest keyword-ideas seo-work/kw-ka-ge.json --locale ka
   ```
   - `init` creates the store (default locale first: the version the root URL serves), adds new locales, and refuses another domain. If it refuses, skip the ingests.
   - For a locale served on a subdomain or ccTLD, set `markets[locale].url_prefix` in `seo-research/site.json` by hand (`"https://ka.example.com/"`), so the store files that version's URLs under the right locale.

## Checks

- **Codes** (§6):
  - Language uses ISO 639-1 (`ka`, `en`, `ru`). An optional region uses ISO 3166-1 alpha-2 (`GE`, `GB`, `US`). An optional script uses ISO 15924 (`zh-Hans`).
  - A region alone is invalid (`be` = Belarusian).
  - `en-UK`, `-EU` and `-UN` are ignored. Use `en-GB`.
  - Codes are case-insensitive.
- **Self-reference and return links** (§6):
  - Each page lists itself and every alternate.
  - Every pair links both ways.
  - URLs are fully qualified. Cross-domain is allowed.
- **x-default** (§6): the fallback for unmatched users, typically a language picker or the global English page. Recommended, not required.
- **One method is enough** (§6): HTML, header or sitemap. Combining them adds nothing, and inconsistent sets cause conflicts.
- **Canonical + hreflang** (§1, §6):
  - Each version's canonical points to itself.
  - Canonicalising all languages to one version kills the other versions.
  - hreflang URLs must be the canonical, 200, indexable URLs. Never http or redirecting.
- **Regional variants:** with several regional versions of a language (`en-GB`, `en-US`), also provide a generic `en` catch-all or use x-default (§6).
- **URL structure** (§6). All three work; pick for operations, not myths:

  | Option | Geo signal | Cost / authority | Notes |
  |---|---|---|---|
  | ccTLD (`example.ge`) | Strongest | Separate authority per domain; highest cost | |
  | Subdomain (`ge.example.com`) | Middling | Separately hosted | |
  | Subfolder (`example.com/ka/`) | | Shares authority; cheapest | Default recommendation for most sites |

  URL parameters (`?lang=ka`) are not recommended.
- **Geo signals** (§6): ccTLD, hreflang, local addresses and phone numbers, local currency, local links, Business Profile. Server IP is weak. The geo meta tag is ignored.
- **Translation quality** (§4): machine translation published at scale without review is **scaled content abuse**. Translated pages need:
  - Human review.
  - Local examples, prices, units and legal details.
  - Translated titles, meta descriptions, alt text and structured data text.
  - Translated image file names where practical (§3).
- **Content parity:** an alternate should be equivalent content, not a stub. Partial translations (a translated header over an English body) confuse language detection.
- **Currency and address:** show local currency (₾ GEL for Georgia), local address/phone format and local payment and delivery details on the market's pages. The structured data must match (`priceCurrency: "GEL"`).

### Example: Georgia (`ka-GE`)

- Google dominates search in Georgia. Yandex has a small share among Russian speakers. Prefer `ka`, `en` and, where the audience needs it, `ru` versions. Verify current market share before committing resources `[needs data]`.
- Georgian has its own script (Mkhedruli). Check that the fonts render, `<html lang="ka">` is set, and slugs are either readable Georgian (percent-encoded) or consistent Latin transliteration. Pick one and keep it.
- Bilingual search behaviour is common (English brand terms plus Georgian modifiers). Research both, with `--hl ka --gl ge` and `--hl en --gl ge`.
- For local businesses, combine this skill with **seo-local** (Business Profile in Georgian and English, Tbilisi/Batumi location pages only where real locations exist).

## Data: free vs paid

- **Free path:**
  - Bundled scripts (page_audit, crawl reciprocity, keyword_ideas per locale).
  - Search Console country and language filters.
  - The built-in browser for checking rendered language.
  - Google Trends per country.
- **Semrush / Ahrefs** add per-country keyword volumes and difficulty, and each competitor's traffic share by country. Only paid tools have this. They're justified when choosing *which* markets to enter or how to size them.
  - **Cost:** query only the target country database, export the top N with display limits, and cache the results in `seo-work/` (tools.md `## Semrush`, `## Ahrefs`, `## Cost-optimisation playbook`).
  - **Check coverage:** some small markets, including Georgia, have thin databases in these tools. Check `[vendor data]` row counts before trusting them.
- **DataForSEO Keywords Data API** gives Google Ads volumes per location and language, pay-as-you-go. It's the cheapest path to real volumes for one or two markets (tools.md `## DataForSEO`).
- **Screaming Frog** adds hreflang reciprocity checks across a full crawl, including sitemap-based hreflang. Justified for large multi-locale sites (tools.md `## Screaming Frog`).

## Output

```
# International SEO — <site> — <date>
Markets: … · Structure: … · hreflang method: …
## Cluster health: pages checked N · invalid codes N · missing self N · missing return links N · x-default y/n [measured]
## P0–P3 fix plan (triage.py + manual items), each fix pointing at the template/generator
## Language/translation review per market [estimate] (sampled pages, what's untranslated or machine-like)
## Per-market keyword findings (autocomplete [measured]; volumes [needs data] unless a paid/Ads source was used)
## Structure recommendation (if asked) with trade-offs
## Assumptions (markets, fallback, hreflang method, translation process: each decision and its evidence; research-store data reused, with its age)
## Not verified [needs data]
```

## Pitfalls & myths

- **hreflang doesn't consolidate ranking signals or fix duplicate content between languages.** It only swaps in the right version where a version already ranks.
- **hreflang is not a directive.** If the content language contradicts it, Google trusts the content.
- **Automatic IP or language redirects** hide versions from Googlebot. Never force them.
- **`<html lang>` is good practice for accessibility and other engines, but Google ignores it** for language detection (§6).
- **A canonical across languages** (e.g. `/ka/` canonical → `/en/`) deindexes the Georgian page.
- **Translating keywords literally** misses how locals search. Research each market natively.

## Log the work

Append to `SEO-WORKLOG.md` per `${CLAUDE_PLUGIN_ROOT}/references/worklog.md`: the markets and URLs checked, script outputs, cluster health numbers, template or generator files changed, translation issues raised, paid units spent per market database, and the next re-check date (14 days after hreflang fixes, then once Search Console shows country traffic shifting, about 4–8 weeks).
