# Research store: research once, reuse everywhere

Keyword, SERP and Search Console research is the slow and costly part of SEO. The research store keeps it in one
folder per site, so the next skill (a brief, a blog post, a translation review, a refresh) starts from what is already
known, re-fetches only what has gone stale, and writes its new findings back.

`scripts/research_store.py` owns the folder. Skills read it through `status`, `next-topics` and `export`, and write to
it only through `ingest`, `set-status` and `glossary add`. The one file skills edit by hand is `site.json`
(money pages, templates, stack, assumptions, market details).

## 1. Where it lives and what never goes in

- **Location:** `<project>/seo-research/`. Every command takes `--dir DIR` to use another folder.
- **Versioned with the repo.** Every file is line-based and sorted, so diffs are small and reviewable. `init` writes a
  `.gitignore` inside the store for its `.lock` and `*.tmp` files.
- **Never in the store:**
  - **Secrets:** API keys, tokens, cookies, passwords.
  - **Raw paid responses.** The credit guard caches those in `${CLAUDE_PLUGIN_DATA}/credit-guard/cache/`
    (`references/paid-tools-automation.md` §8). The store keeps only the derived columns (keyword, volume,
    difficulty), each with the vendor's name and the date.
  - **Personal data.** Every ingest drops a keyword that contains an e-mail address or a phone number and counts it
    as `skipped_personal_data`. GSC queries can still carry people's names: read the export before committing it.
  - **Page bodies and fetched HTML.** Those stay in `seo-work/`.
- **Vendor terms.** Semrush's API terms forbid caching its data for more than one month without written consent
  (`references/paid-tools-automation.md` §1, terms §3.3). The 30-day volumes TTL matches that, but git history keeps
  old values. Before committing Semrush-sourced volumes, get that consent or keep those volumes out of the committed
  store. Whether user-supplied exports fall under the same rule is [UNVERIFIED].

## 2. Files

| File | One record per | Written by |
|---|---|---|
| `manifest.json` | dataset: `updated_at`, `sources`, `records`, `ttl_days`, `locales` (locale → date of its newest data) | every write |
| `site.json` | the site: `site`, `domain`, `locales` (the first is the default), `markets`, `money_pages`, `templates`, `stack`, `assumptions` | `init`, `ingest keyword-ideas` (fills `markets[locale].hl/gl`), skills by hand |
| `keywords.jsonl` | keyword + locale | every `ingest`, `set-status` |
| `clusters.json` | cluster | `ingest clusters`, `set-status`; `priority` is recomputed on every write |
| `serps/<locale>/<sha1 of the keyword>.json` | keyword + locale | `ingest serps` |
| `competitors.json` | domain | `ingest serps` (derived from every stored SERP) |
| `inventory.csv` | URL | `ingest crawl`, `ingest gsc`; `cluster_id` is derived from cluster targets |
| `glossary/<locale>.json` | term | `glossary add` |
| `briefs/<locale>/<slug>.md` | brief | skills; `next-topics` names the path and says whether it exists |

`records` counts the rows in the store that carry that dataset's data. For `gsc` that is keywords with GSC impressions
plus inventory rows with GSC clicks.

### keywords.jsonl

```json
{"keyword": "english tutor", "locale": "en", "intent": "commercial", "cluster_id": "en-001",
 "demand": {"autocomplete_sources": ["bing", "google"], "gsc_impressions": 300, "gsc_position": 10.5,
            "gsc_pages": ["https://example.com/tutors/", "https://example.com/blog/find-a-tutor/"],
            "volume": 2400, "volume_source": "semrush", "volume_date": "2026-10-19",
            "difficulty": 61, "difficulty_source": "semrush"},
 "serp_features": ["ai_overview", "local_pack"], "target_url": "https://example.com/tutors/", "status": "planned",
 "notes": "", "first_seen": "2026-10-14T09:00:00+00:00", "updated_at": "2026-10-24T13:07:46+00:00",
 "provenance": {"intent": {"source": "serp", "at": "2026-10-24T13:07:46+00:00"},
                "demand.volume": {"source": "semrush", "at": "2026-10-19T08:12:00+00:00"}}}
```

(An example record, shown wrapped; the file holds one record per line.)

- **`provenance`** holds the source and date of every value a merge decided (see §5). `demand.gsc_pages` lists the
  site's URLs that hold at least 10% of the query's impressions, the same rule as `gsc_analyze.py`'s cannibalisation
  check. Two or more pages there is a cannibalisation signal.
- **`status`** is one of `planned`, `briefed`, `drafted`, `published`, `skip`.
- **`intent`** starts as `keyword_ideas.py`'s wording-based guess, whose patterns are English only. A SERP read
  (`--details`) replaces it.

### clusters.json

```json
{"cluster_id": "en-003", "locale": "en", "head_keyword": "how to become an english tutor",
 "keywords": ["how to become an english tutor"], "role": "cluster", "target_url": null,
 "interlinks": [], "priority": 8, "status": "planned"}
```

- `cluster_id` is `<locale>-<number>` and never changes (§5).
- `role` is `pillar`, `cluster` or `support`. New clusters start as `cluster`; `seo-keywords` sets pillars and supports
  by adding `role` to the cluster entries before ingesting them.
- `interlinks` lists cluster ids whose SERPs share 2–3 URLs (from `serp_cluster.py`).

### serps/&lt;locale&gt;/&lt;sha1&gt;.json

```json
{"keyword": "how to become an english tutor", "locale": "en", "fetched_at": "2026-10-24T13:07:46+00:00",
 "results": [{"url": "https://www.reddit.com/r/TEFL/comments/abc/", "title": "…", "type": "forum/ugc"}],
 "features": ["people_also_ask", "video"], "paa": ["Do you need a degree to be an English tutor?"]}
```

The file name is the SHA-1 of the keyword as stored (lower-cased, single spaces, UTF-8). `type` uses the
`seo-serp-researcher` page types, lower-cased: `guide/article`, `listicle`, `category`, `product`, `service/landing`,
`tool/calculator`, `forum/ugc`, `video`, `news`, `local`, `homepage`, `other`.

### competitors.json, inventory.csv, glossary

- **competitors.json:** `{domain, locales, keywords_shared, last_seen}`. `keywords_shared` counts the stored SERPs
  (keyword + locale) that the domain appears in. The site's own domain is left out.
- **inventory.csv:** `url, locale, title, cluster_id, words, last_modified, status, gsc_clicks, gsc_impressions`.
  `status` is the HTTP status from the crawl. `last_modified` is filled only when the crawl CSV has a `last_modified`
  or `lastmod` column (a CMS or Screaming Frog export). `cluster_id` lists, `;`-separated, the clusters that target
  that URL.
- **glossary/&lt;locale&gt;.json:** `{"term": {"translation": "…", "note": "…", "do_not_translate": false}}`, one file
  per target language. It is the glossary that `references/ai-content-review.md` §11 injects into the translation
  prompt.

### Locales

Locale codes are stored lower-case: `en`, `ka`, `ru`, `ru-ge`. A URL's locale is decided in this order:

1. `site.json → markets[locale].url_prefix`, when set (for subdomains or ccTLDs: `"https://ka.example.com/"`);
2. a first path segment that is a store locale (`/ka/blog/…` → `ka`);
3. otherwise the default locale, the first in `locales`.

## 3. Commands

`S="${CLAUDE_PLUGIN_ROOT}/scripts"`. Every command prints JSON, except `export --format csv`, which prints CSV.

| Command | Does |
|---|---|
| `init --site URL [--locales en,ka,ru]` | Creates the store, or adds locales to an existing one. Refuses a different domain |
| `ingest keyword-ideas FILE --locale LOC` | `keyword_ideas.py` output. Refuses a file fetched with another `--hl` |
| `ingest serps FILE --locale LOC [--details FILE]` | `serps.json` (`{keyword: [top-10 urls]}`), plus optional titles, page types, features, PAA and intent |
| `ingest clusters FILE --locale LOC` | `serp_cluster.py` output. Optional per-cluster `head_keyword`, `role`, `target_url` |
| `ingest gsc FILE [--locale LOC]` | `gsc_analyze.py` JSON (`.json`) or a GSC Queries, Pages or query+page CSV |
| `ingest crawl FILE` | `crawl.py --csv` pages file |
| `ingest volumes FILE --locale LOC --source NAME` | A keyword/volume[/difficulty] export from Semrush, Ahrefs, DataForSEO or Keyword Planner |
| `status` | Datasets, their age per locale, `stale` and `missing` lists, `gaps` per locale |
| `next-topics [--locale LOC] [--limit N]` | Clusters without a published target, best first, with every reason (§7) |
| `set-status (--cluster ID or --keyword KW --locale LOC) --status S [--url URL]` | Moves a cluster or keyword along the pipeline |
| `glossary add --locale LOC --term T --translation X [--do-not-translate] [--note N]` | Adds or updates a term |
| `glossary show --locale LOC` | Prints the locale's glossary |
| `export DATASET [--locale LOC] --format csv or json` | `keywords`, `clusters` or `inventory` |

**Input details:**
- **GSC:** a CSV gives every row; a `gsc_analyze.py` report gives only its top lists (striking distance, CTR
  under-performers, questions, cannibalisation). Prefer the CSV. A query that isn't in the store yet is added only with
  at least 10 impressions (`skipped_below_min_impressions` counts the rest). A query's locale comes from its page URL;
  a Queries.csv without pages needs `--locale` when the store has more than one locale.
- **Volumes:** headers are matched by name (`Keyword`, `Volume`, `Search Volume`, `Avg. monthly searches`,
  `Keyword Difficulty`, `KD`, `Difficulty`), comma or tab separated, UTF-8 or UTF-16 (Keyword Planner), with any title
  rows above the header skipped. A range such as `1K – 10K` is kept as written and ranks as its lower bound.
- **SERP details** (`--details`), the shape `seo-serp-researcher` writes:
  ```json
  {"english tutor": {"results": [{"url": "https://…", "title": "…", "type": "service/landing"}],
                     "features": ["AI Overview", "Local pack"], "paa": ["…"], "intent": "commercial"}}
  ```
  Features are normalised to `ai_overview`, `local_pack`, `people_also_ask` and so on.

## 4. What each ingest updates

| Ingest | Keywords | Other files |
|---|---|---|
| keyword-ideas | creates; `intent` (guess), `demand.autocomplete_sources` | `site.json` markets `hl`/`gl` |
| serps | creates; `serp_features`; `intent` from details | the SERP file, `competitors.json` |
| clusters | creates; `cluster_id` | `clusters.json` |
| gsc | creates (≥ 10 impressions); `demand.gsc_impressions`, `gsc_position`, `gsc_pages`; `target_url` when empty | `inventory.csv` GSC columns |
| crawl | — | `inventory.csv` title, words, status, last_modified |
| volumes | creates; `demand.volume`, `volume_source`, `volume_date`, `difficulty`, `difficulty_source` | — |

## 5. Merge rules

1. **Never drop data.** An ingest only adds and updates. A keyword missing from the new file stays. An empty cell or a
   missing field never blanks a stored value. A cluster emptied by regrouping stays, and `status` counts it under
   `empty_clusters`.
2. **The newest value wins, per field, with its source and date kept.** An input's date is its file's modification
   time: when the data was fetched or exported. Keep the original files (`cp -p` keeps the time; a plain copy makes
   old data look new). An older file never replaces a newer value. The winner's source and date go to `provenance`;
   volumes also fill `volume_source` and `volume_date`.
3. **Demand evidence accumulates.** Autocomplete engines are added, never removed. GSC impressions and position are a
   period's totals, so a newer export replaces them rather than adding to them.
4. **A SERP-read intent beats the wording guess.** Once `--details` has set an intent, a later `keyword_ideas.py`
   ingest never replaces it.
5. **Clusters keep their ids.** A clusters file is applied as a whole, and a file older than the stored clusters of
   that locale is refused. Each incoming group reuses the stored cluster that holds most of its keywords; otherwise it
   gets the next free id. Keywords move to the newest grouping; interlinks accumulate.
   - `head_keyword`: the input's, else re-picked at each clusters ingest while the cluster is `planned`: the strongest
     demand evidence, then the shortest phrase, then alphabetical. From `briefed` on it stays, so briefs keep their
     slug.
   - `target_url`: the input's, else kept, else the most common `target_url` of its keywords (which GSC fills with the
     page that already gets the impressions).
6. **Inventory:** crawl fields come from the crawl and GSC columns from GSC. A row already filled by a newer file of
   that locale is kept; a URL new to the store is always added.
7. **set-status:** sets the status (and the target URL, with `--url`). A cluster's keywords that had its previous
   status follow it, so a keyword marked `skip` on its own stays `skip`.
8. **Glossary:** a newer `add` replaces the translation. An omitted `--note` keeps the stored note, and
   `--do-not-translate` is only ever switched on.
9. **Deterministic and safe:** records are sorted, JSON keys are sorted, and re-ingesting the same files changes no
   byte. Every file is written to a temporary file and renamed into place, and commands take a lock on the store, so
   parallel subagents can't lose each other's writes.

## 6. TTLs and staleness

| Dataset | TTL (days) | Refreshed by | Why this TTL |
|---|---|---|---|
| keywords | 90 | `keyword_ideas.py`, then `ingest keyword-ideas` | Query wording changes slowly |
| volumes | 30 | the vendor export, then `ingest volumes` | Vendors refresh monthly; Semrush terms cap caching at a month (§1) |
| serps | 30 | `seo-serp-researcher` or WebSearch, then `ingest serps` | Rankings and SERP features move |
| gsc | 7 | a GSC export, then `ingest gsc` | GSC data is daily; weekly is enough for planning |
| inventory | 30 | `crawl.py --csv`, then `ingest crawl` | Pages are added and changed |
| competitors | 90 | derived from SERPs | The competitor set changes slowly |
| clusters, glossary | none | decisions, not observations | Re-cluster when the SERPs are refreshed |

- `status` reports a dataset as **stale** for a locale when its newest data there is older than the TTL, and as
  **missing** when that locale has none. Refresh only those.
- `gaps.<locale>.needs_serp` lists keywords with no SERP or one older than the SERP TTL, strongest demand first (up to
  50, with the full count).
- To change a TTL for one project, edit `ttl_days` in `manifest.json`; `status` reads it from there.

## 7. next-topics priority [heuristic]

`priority = intent_fit (0..3) + demand (0..4) + serp_gap (-1..3) − cannibalisation (0..3)`. This is a heuristic, not a
Google metric, and it is scored for an article or blog page. Every point comes with a reason string and an evidence tag.

| Part | Scored from |
|---|---|
| **intent_fit** | With 5 or more typed results in the head keyword's SERP: the share that are guides, listicles, news or forum threads, × 3. Otherwise the head's intent: informational 3, commercial 2, unclear 1, transactional or navigational 0 |
| **demand** | The evidence ladder from `seo-keywords`: GSC impressions ≥ 10 on any keyword 4 · a vendor volume 3 · suggested by 2+ engines 2 · one engine 1 · nothing 0 |
| **serp_gap** | Forum or UGC results in the head's top 10 (type `forum/ugc`, or reddit, quora, stackexchange, stackoverflow), up to 3. −1 when an AI Overview is shown. PAA questions are listed, not scored |
| **cannibalisation** | −2 when 2+ of the site's URLs get impressions for the cluster, or −1 for one URL that isn't the target · −1 when another cluster targets the same URL · −1 when the site already ranks in the head's top 10 with another URL · −1 when a live page's title contains the head keyword. Capped at 3 |

- **Left out:** clusters marked `published` or `skip`, clusters with no keywords, and clusters whose target URL is
  live in the inventory (HTTP 200). Those are refreshes, not new topics. `excluded` counts each.
- **Ties** go to more GSC impressions, then more volume, then more keywords, then the cluster id.
- **Each topic** carries the cluster fields, `scores`, `evidence` (GSC impressions and volume summed), `reasons`,
  `paa`, `interlinks` (the linked clusters' heads, targets and statuses) and `brief` (the path
  `briefs/<locale>/<slug of the head>.md`) with `brief_exists`.

## 8. How skills use the store

Every skill that needs keyword, SERP, GSC or page data follows the same loop:

1. **Read first:** run `status`, plus `export` of the dataset it needs (or `next-topics`).
2. **Reuse fresh data** as it is.
3. **Fetch only the missing or stale pieces:** the `stale` and `missing` entries and `gaps.<locale>.needs_serp`.
4. **Write results back** with `ingest`, `set-status` or `glossary add`.
5. **Say what was reused** in the report's *Assumptions* and in `SEO-WORKLOG.md` (`references/worklog.md`), with
   ages, e.g. "Reused from seo-research: en keywords (keyword_ideas, 12 days old), en SERPs (9 days). Refreshed: GSC
   (was 9 days old, TTL 7)."

| Skill or agent | Reads | Writes |
|---|---|---|
| `seo-keywords` | `status`, `export keywords`, `export clusters` | ideas per locale, SERPs and details, clusters, volumes for the shortlist, GSC |
| `seo-content` and the blog builder | `next-topics --locale`, the SERP file and PAA of the chosen cluster, `glossary show` | `briefs/<locale>/<slug>.md`; `set-status` to `briefed`, `drafted`, `published` with `--url` |
| `seo-blog-review` | the per-language target query (`export keywords --locale`), `glossary show` | glossary terms the review approved (`glossary add`) |
| `seo-analytics` | `status` (GSC age) | `ingest gsc` |
| `seo-audit`, `seo-technical` | `export inventory` | `ingest crawl` |
| `seo-competitors` | `competitors.json` | SERPs through `seo-keywords` |
| `seo-international` | `site.json` locales and markets | `init --locales`, `markets[locale].url_prefix` by hand |
| `seo-serp-researcher` (agent) | — | `<output>.serps.json` and the details JSON; the caller ingests both |

Subagents collect data in parallel into files under `seo-work/`; one process ingests them. The lock makes parallel
ingests safe, but a single ingester keeps the run's report simple.

## 9. Worked example: a blog in English, Georgian and Russian

`example.com` has an English blog at `/blog/`, Georgian at `/ka/blog/` and Russian at `/ru/blog/`, the last written
for Russian speakers in Georgia.

**1. Create the store** (English is the default locale):
```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"
python3 "$S/research_store.py" init --site https://example.com --locales en,ka,ru
python3 "$S/research_store.py" status
```
Everything is `missing`.

**2. Research each language natively.** Never translate the English list (`references/ai-content-review.md` §7).
```bash
python3 "$S/keyword_ideas.py" "english tutor" --hl en --gl gb --sources google,bing > seo-work/kw-en.json
python3 "$S/keyword_ideas.py" "ინგლისური ენის კურსები" --hl ka --gl ge --sources google > seo-work/kw-ka.json
python3 "$S/keyword_ideas.py" "репетитор английского" --hl ru --gl ge --sources google,bing > seo-work/kw-ru.json
python3 "$S/research_store.py" ingest keyword-ideas seo-work/kw-en.json --locale en
python3 "$S/research_store.py" ingest keyword-ideas seo-work/kw-ka.json --locale ka
python3 "$S/research_store.py" ingest keyword-ideas seo-work/kw-ru.json --locale ru
```
In the test run on 2026-10-24 [measured], the English seed returned 576 suggestions from Google and Bing, and the
Georgian seed returned 10 from Google.

**3. Add what the site already earns** (one query+page export for the whole property; locales come from the paths):
```bash
python3 "$S/research_store.py" ingest gsc seo-work/gsc_query_page.csv
```

**4. SERPs for the shortlist, then clusters, per locale.** Give each `seo-serp-researcher` batch about 10 keywords
from `gaps.<locale>.needs_serp`, merge the batches into one `serps.json` and one details file per locale, then:
```bash
python3 "$S/research_store.py" ingest serps seo-work/serps-ka.json --locale ka --details seo-work/serps-ka-details.json
python3 "$S/serp_cluster.py" seo-work/serps-ka.json --same-page 4 --interlink 2 > seo-work/clusters-ka.json
python3 "$S/research_store.py" ingest clusters seo-work/clusters-ka.json --locale ka
```

**5. The inventory, and volumes where a tool covers the language:**
```bash
python3 "$S/crawl.py" https://example.com/ --max-pages 2000 --csv seo-work/pages.csv > seo-work/crawl.json
python3 "$S/research_store.py" ingest crawl seo-work/pages.csv
# the cluster heads are the shortlist to look up in the vendor tool, within the budget
python3 "$S/research_store.py" export clusters --locale en --format csv > seo-work/en-heads.csv
python3 "$S/research_store.py" ingest volumes seo-work/semrush-en.csv --locale en --source semrush
```
Georgian volumes stay `[needs data]` unless a tool shows its method: Ads-based tools can target Georgia but not the
Georgian language (`references/ai-content-review.md` §7) [inference]. The `ka` demand score then rests on GSC and
autocomplete.

**6. Glossaries for the translation pipeline:**
```bash
python3 "$S/research_store.py" glossary add --locale ka --term "Example" --translation "Example" --do-not-translate --note "brand"
python3 "$S/research_store.py" glossary add --locale ru --term "tutor" --translation "репетитор"
```

**7. Pick the next post and move it along:**
```bash
python3 "$S/research_store.py" next-topics --locale en --limit 5
python3 "$S/research_store.py" set-status --cluster en-003 --status briefed
python3 "$S/research_store.py" set-status --cluster en-003 --status published --url https://example.com/blog/become-an-english-tutor/
```
In the test run, with a handmade SERP for each keyword, the top English topic came out like this [measured: test run
2026-10-24; the SERP URLs were invented]:
```json
{"cluster_id": "en-003", "head_keyword": "how to become an english tutor", "priority": 8,
 "scores": {"intent_fit": 3, "demand": 2, "serp_gap": 3, "cannibalisation": 0},
 "reasons": ["intent fit 3/3: head keyword intent 'informational' (from keyword_ideas); no typed SERP to confirm the page type [heuristic]",
             "demand 2/4: suggested by 2 engines; no volume [measured: suggested]",
             "SERP gap 3: 3 forum or UGC results in the top 10 [heuristic: weak results are beatable]"],
 "brief": "briefs/en/how-to-become-an-english-tutor.md", "brief_exists": false}
```
"english tutor" ranked lower (priority 2), because the site already ranks in its top 10 with `/tutors/`
(cannibalisation −1). The translated versions of a post get their own `ka` and `ru` clusters and target queries, never
a translated English keyword.

**8. A month later:** `status` lists `gsc` (7-day TTL) and `serps` (30-day TTL) as stale for every locale, while
keywords (90 days) are still fresh. The next skill refreshes GSC and the `needs_serp` keywords, re-ingests them,
re-clusters, and reuses the rest.

## 10. Limits

- An input's date is its file's modification time. A copy without `-p`, or a fresh git checkout, makes old data look
  new.
- The wording-based intent guess knows English patterns only, so `ka` and `ru` keywords stay `unclear` until a SERP
  read sets their intent.
- The title check in cannibalisation is an exact substring. Georgian and Russian inflect, so it under-matches there.
- A `gsc_analyze.py` report holds only its top lists; the CSV is the complete source.
- Each keyword record is about 0.7 KB, so 10,000 keywords are about 7 MB. That is fine for a repo; a store far larger
  than that needs a database.
- The store doesn't fetch anything. Keeping it fresh is the skills' job, guided by `status`.
