# SEO for Beginners — the essentials, in priority order

## How Claude uses this guide

Load this guide when the user is new to SEO: they say they "don't know SEO", ask what a term means, or ask
"where do I start?". When working with them:

- **Plain language.** Explain each term the first time it comes up, in one short sentence (the glossary at the end
  has the wording). No acronyms without spelling them out.
- **One action at a time.** Give the next concrete step and stop there. Don't hand over a 50-item list.
- **Explain WHY before HOW.** One sentence on what the problem costs them, then the steps to fix it.
- **Show only the top 3–5 findings.** Run triage first (`triage.py`) and show only the P0/P1 items in
  plain words. Mention that more items exist and offer them later.
- **Say where to click.** When a step happens in Google Search Console or another tool, give the exact menu
  path, e.g. *Search Console → Indexing → Pages*.
- **Celebrate quick wins.** When something gets fixed, say so and say what it unlocks.
- **Be honest about time.** SEO takes months. Never promise rankings or traffic.
- **Warn about scams.** Treat these as red flags: "guaranteed #1 on Google", "1,000 backlinks for $50",
  "instant indexing", "secret algorithm". Explain why each one is a red flag.
- **Use analogies sparingly**, only where one makes an idea click.
- **Never change their site, Search Console or CDN settings without asking first.** Code changes go to them
  as a diff for approval before anything is applied.

---

## Is SEO worth it? How long does it take?

- **What SEO is.** SEO (search engine optimisation) helps search engines find, understand and trust your
  pages, so they show them to people searching for what you offer.
- **It is slow.** Fixing technical problems can show results within weeks. New content and reputation usually
  take **3–12 months** to pay off, and competitive topics can take longer. Anyone promising days is guessing
  or lying.
- **It compounds.** Paid ads stop the day you stop paying. A page that ranks keeps bringing visitors.
- **Nobody controls Google.** You can only make your site the best answer and remove obstacles. Google
  explicitly says nobody can pay for a better ranking.
- **Free tools cover most needs.** Google Search Console, Bing Webmaster Tools and this plugin's scripts are
  enough for most small sites. Paid tools such as Semrush and Ahrefs mostly add competitor data and search
  volumes. They are useful later and not needed to start.

---

## Pillar 1 — Technical foundation (can Google reach and read your site?)

**What it is.** Making sure search engines can *reach* your pages (crawling), *store* them (indexing) and
*read* them correctly (rendering), quickly and on a phone. If this fails, nothing else matters: great
content on a page Google can't see brings zero visitors.

**What it consists of**
- [ ] **Crawling.** Google's robot ("Googlebot") is allowed in and isn't blocked by `robots.txt` (a small
  file listing what robots may visit) or by a security service such as Cloudflare.
- [ ] **Indexing.** Pages return status **200**, which means "OK". Pages you want found don't carry a
  `noindex` tag, which tells Google "don't list this page".
- [ ] **Rendering.** The important text and links are in the page's HTML, not only drawn later by JavaScript.
- [ ] **Speed (Core Web Vitals).** Google's three speed and stability measures:
  - LCP (main content appears): ≤ 2.5 s.
  - INP (page reacts to taps): ≤ 200 ms.
  - CLS (layout doesn't jump around): ≤ 0.1.
- [ ] **Mobile.** The site works well on phones. Google indexes the *mobile* version of your site.
- [ ] **HTTPS.** The padlock is in the address bar, and the `http://` address forwards to `https://`.
- [ ] **Structure and internal links.** Every important page can be reached by clicking links from your
  homepage, ideally within 3 clicks.
- [ ] **Sitemap.** A file (`sitemap.xml`) lists your real pages for Google. It is submitted in Search
  Console and named in `robots.txt`.
- [ ] **No broken pages.** No links point to "404 – not found" pages, and old URLs forward (redirect) to
  their new home.
- [ ] **One address per page.** Each page uses a "canonical" tag, which says "this is the main address of
  this page", to avoid duplicates.

**Why it matters.** Google only ranks what it can crawl and index. One wrong line in robots.txt, or a
forgotten `noindex` left over from the development site, can remove a whole website from Google.

**How to do it yourself (free)**
1. **Set up Google Search Console** at search.google.com/search-console. Add your site, preferably as a
   "Domain" property, and verify it as the tool instructs.
2. **Submit your sitemap.** In Search Console go to *Indexing → Sitemaps* and enter `sitemap.xml`, or the
   address your website system gives you.
3. **Check what's indexed.** Go to *Indexing → Pages*. "Not indexed" lists the reasons. Ask Claude to explain
   any reason you don't understand.
4. **Check speed.** Go to *Experience → Core Web Vitals*, or test a page at pagespeed.web.dev.
5. **Check one important page.** Paste its address into the search bar at the top of Search Console
   (URL Inspection). It shows whether Google can index it.
6. **Run the plugin checks.** Ask Claude to run the site checks: robots.txt, sitemap and a small crawl.

**Common mistakes**
- Leaving "Discourage search engines" ticked in WordPress, or a `noindex` copied over from a staging site.
- Blocking the whole site in robots.txt (`Disallow: /`).
- A security wall such as a Cloudflare challenge that blocks search or AI robots.
- Huge uncompressed images that make the page slow.
- Changing URLs without redirects, which loses the rankings the old pages had.
- Menus built so the links only appear after clicking with JavaScript. Robots don't click.

**Which seo-suite skill to ask for**
- "Run a quick SEO audit of my site" → **seo-audit**
- "Why isn't my page on Google?" / "Is my site indexed?" → **seo-technical**
- "Is my site fast enough?" → **seo-technical** (it uses `psi.py`)
- "I'm moving to a new domain/website" → **seo-migration**

---

## Pillar 2 — Content & copywriting (does your page answer what people search for?)

**What it is.** Writing pages that match what people actually type into Google ("search intent"), answer it
better than anyone else, and make the reader trust you enough to act (buy, call, sign up).

**What it consists of**
- [ ] **Search intent.** Know what the searcher wants. There are four types:
  - Learn something (informational).
  - Compare options (commercial).
  - Buy or book (transactional).
  - Find a specific site (navigational).
- [ ] **Keyword research.** The words real people use. They are often not the words you use internally.
- [ ] **One clear topic per page.** Two pages shouldn't compete for the same search ("cannibalisation").
- [ ] **A clear title and description.** The `<title>` (the blue link in Google) and the meta description
  (the grey text under it) say exactly what the page offers.
- [ ] **Answer first.** The main answer sits near the top, then the details. Use headings, short paragraphs,
  lists and tables.
- [ ] **E-E-A-T** (Experience, Expertise, Authoritativeness, Trust). Show who wrote the page and why they
  know, cite sources, and publish real contact details. **Trust matters most.**
- [ ] **Originality.** First-hand experience, your own photos, your own data. Avoid rewording other sites.
- [ ] **Freshness.** Update facts, prices and dates when they really change. Changing only the date is
  treated as a trick.
- [ ] **A conversion path.** Every page has a clear next step (button, form, phone number).
- [ ] **Copyright**, meaning content you're allowed to use: see below.

**Copyright & originality: what you must know**
- **Your text must be yours.** Copying or "spinning" (automatically rewording) other sites' text is
  **scraping**, which Google's spam policies forbid. It can also break copyright law.
- **Duplicate text inside your own site**, such as the same paragraph on 50 city pages, makes those pages
  weak. Each page needs unique value.
- **Manufacturer descriptions.** Shops that copy the manufacturer's product text look like every other shop.
  Add your own details, photos and FAQs.
- **Images.** Only use images you took, bought a licence for, or that have a free licence that allows your
  use (e.g. a Creative Commons licence that permits commercial use; check the conditions). "Found it on
  Google Images" is **not** a licence.
- **DMCA / copyright removal.** If someone copies *your* content, you can ask Google to remove the copy
  through its legal removal request (Google's "Legal removals" process). Content removed this way can
  also hurt the copier.
- **AI-written text** is allowed by Google **if it is genuinely helpful and checked by a human**. Rules:
  - Fact-check everything.
  - Add your own experience.
  - Never mass-produce hundreds of pages ("scaled content abuse" is against Google's rules).

**Why it matters.** Technical SEO gets you seen. Content is what gets you *chosen*, by Google and by the
person reading.

**How to do it yourself (free)**
1. **Ask Claude for keyword ideas:** "find keyword ideas for *[your service]* in *[your country]*". It uses
   Google/Bing autocomplete. These show what people type but **not** how many people type it.
2. **Search the keyword yourself** and look at the top 5 results. Are they guides, product pages or lists?
   Make the same *type* of page, only better.
3. **Write the answer first**, then the details. Read it aloud: would a customer understand it?
4. **Write a title** under about 60 characters with the main topic first and your brand last, e.g.
   "Wedding Photographer in Tbilisi — Packages & Prices | YourName".
5. **Add who you are.** An author name, a short bio, real photos, a contact page.
6. **After 4–8 weeks**, open Search Console → *Performance* to see which searches show your page.

**Common mistakes**
- Writing for "Google" instead of a person, e.g. repeating the keyword 30 times ("keyword stuffing").
- Aiming for a word count. Google has no preferred length.
- One giant page about everything, or ten thin pages about the same thing.
- Publishing 100 AI pages in a week.
- Using images from the internet without a licence.

**Which seo-suite skill to ask for**
- "Find keywords for my business" → **seo-keywords**
- "Improve this page for Google" → **seo-onpage**
- "Review my blog / which pages should I update or delete?" → **seo-content**
- "Write a content plan" → **seo-strategy** + **seo-content**

---

## Pillar 3 — Backlinks & authority (do other sites vouch for you?)

**What it is.** A **backlink** is a link from another website to yours. Google treats good links as
recommendations: a link from a respected local newspaper says "this business is real and worth visiting".

**What it consists of**
- [ ] **Quality over quantity.** One link from a relevant, real, respected site is worth more than hundreds
  from junk sites.
- [ ] **Relevance.** Links from sites in your industry or city.
- [ ] **Natural anchor text.** The clickable words of the link should read naturally (your brand name, the
  page topic), not the same exact keyword everywhere.
- [ ] **Mentions.** Your brand named in articles, directories and reviews, ideally with a link.

**Ways to *earn* links (allowed)**
1. **Be worth linking to.** Original data, a useful free tool, a definitive guide, great photos.
2. **Digital PR.** Send a genuinely newsworthy story or survey result to journalists and bloggers.
3. **Partnerships.** Suppliers, partners, clients, schools or events you sponsor often list you.
4. **Local links.** Chamber of commerce, local business directories, local news, community sites.
5. **Unlinked mentions.** Find articles that mention you without a link and politely ask them to add one.
6. **Broken-link reclamation.** If other sites link to *your* old pages that now show "404", redirect those
   old addresses to the right new page. You win those links back for free.
7. **Your own profiles.** Google Business Profile, social profiles, industry associations.

**Forbidden (can get you penalised)**
- **Buying links** that pass ranking value, including "guest post packages" and "1,000 links for $50".
- **PBNs** (private blog networks): fake sites built only to link to you.
- **Link exchanges at scale** ("I link you, you link me").
- **Automated link-building tools** and comment or forum spam.
- Sponsored or paid links are fine **only** if marked `rel="sponsored"` (or `nofollow`).

**Disavowing** (telling Google to ignore bad links): almost never needed. Google already ignores most spam.
Only consider it if Search Console shows a **manual action** for unnatural links, or you knowingly bought
links in the past.

**Why it matters.** When many pages answer a question equally well, reputation helps decide who ranks
higher. It is a big factor in local "near me" results too.

**How to do it yourself (free)**
1. Open Search Console → *Links* to see who already links to you.
2. List 10 partners, suppliers or associations that could list you. Ask Claude to draft polite emails.
   **You** send them.
3. Search your brand name in quotes. Note any mentions without a link.
4. Ask Claude to find your broken pages that have links, and redirect them.

**Common mistakes**
- Paying for link packages.
- Expecting links to fix a slow or thin site. They won't.
- Spammy outreach to hundreds of sites.
- Panicking about "toxic links" because a tool shows a scary score.

**Which seo-suite skill to ask for**
- "How do I get backlinks?" / "Check my links" → **seo-links**
- "Who are my competitors in Google and why do they rank?" → **seo-competitors**

---

## 4. On-page basics (one page at a time)

**What it consists of**
- One clear `<h1>` heading.
- A descriptive title and meta description.
- A readable URL (`/wedding-photography-prices`, not `/page?id=123`).
- Image "alt text": a short description of each image for blind users and for Google.
- Links to related pages on your site.
- Structured data where it fits. This is hidden code that labels things like your business, products or
  articles for Google ("schema").

**Do it:** ask "check this page" → **seo-onpage**. It runs `page_audit.py` and gives before/after
suggestions. For structured data, ask → **seo-schema**.

**Common mistakes**
- Missing or duplicate titles.
- Images without alt text.
- Adding FAQ or HowTo structured data hoping for stars or dropdowns in Google. Google no longer shows these.

---

## 5. Local SEO (if customers come to you, or you go to them)

**What it consists of**
- **A Google Business Profile** (the box on Google Maps):
  - Your real business name only (no keywords stuffed in).
  - An exact address (no PO boxes, no virtual offices).
  - Correct hours.
  - The most specific category.
  - Photos.
- **Reviews.** Ask happy customers and reply to every review. Never buy reviews or pay for good ones.
- **Consistent details.** The same name, address and phone number everywhere online.
- **Local pages.** A page per real location or service area, each with genuinely local content.

Google ranks local results by **relevance, distance and prominence**. You can't pay for a better local
ranking.

**Do it:** ask "help with my Google Maps listing" → **seo-local**.

---

## 6. AI search (Google AI Overviews, ChatGPT, Perplexity)

**What it is.** AI tools now answer questions directly and cite websites as sources.

**What helps**
- **Normal good SEO is the foundation.** Google says AI Overviews need no special code or files. A page just
  needs to be indexed and allowed to show a snippet.
- **Answer questions clearly near the top of the page**, with facts, numbers and sources.
- **Be indexed in Bing too.** ChatGPT search leans heavily on Bing. Set up Bing Webmaster Tools
  (bing.com/webmasters); you can import your site from Search Console.
- **Don't block the "search" robots** of AI tools in robots.txt if you want to be cited (OAI-SearchBot,
  Claude-SearchBot, PerplexityBot). You *can* still block the "training" robots (GPTBot, ClaudeBot,
  Google-Extended).
- **`llms.txt`.** Google says it doesn't use this file. It's optional, not a magic switch.

**Do it:** ask "can AI tools find and cite my site?" → **seo-ai-search**.

---

## 7. Measuring progress (free)

- **Google Search Console** shows searches, clicks, positions, indexing and speed. Check *Performance*
  monthly and compare the last 3 months with the 3 months before.
- **Google Analytics 4 (GA4)** shows what visitors do after they arrive (calls, sales, sign-ups).
- **Bing Webmaster Tools** is the same idea for Bing, which also feeds ChatGPT and Copilot.
- **Track a few numbers only:**
  - Clicks from Google.
  - Conversions (enquiries or sales).
  - Number of indexed pages.
  - Core Web Vitals status.

**Do it:** export *Performance → Search results* (top right **Export**) and ask "analyse my Search Console
data" → **seo-analytics**. It finds "almost ranking" searches and pages with low click rates.

---

## 8. A 90-day starter plan

**Days 1–7: foundation**
1. Set up Search Console and Bing Webmaster Tools. Submit the sitemap.
2. Ask Claude: "run a quick SEO audit of my site". Fix only the top 3 problems.
3. Set up or claim your Google Business Profile, if you're a local business.

**Days 8–30: fix and focus**
4. Fix indexing errors from *Indexing → Pages*.
5. Pick your 5–10 most important pages (services and products). Improve their titles, headings and first
   paragraph (**seo-onpage**).
6. Do keyword research for your main service (**seo-keywords**). Choose 3 topics to write about.

**Days 31–60: content**
7. Publish or rewrite the 3 best pages for those topics, with first-hand experience, photos and a clear
   next step.
8. Add an About page, author bios and real contact details (trust).
9. Ask 5 happy customers for reviews.

**Days 61–90: reputation and review**
10. Contact 10 partners or associations for listings or links (Claude drafts, you send).
11. Redirect any old broken URLs that other sites link to.
12. Compare Search Console's last 28 days with the start. Ask "what should I do next?" → **seo-strategy**.

*Expect small movements by day 90, not a breakthrough. Keep going.*

---

## Glossary

- **Algorithm update:** Google changing how it ranks pages. Rankings can move without you changing anything.
- **Alt text:** a short text description of an image, read by screen readers and search engines.
- **Anchor text:** the clickable words of a link.
- **Backlink:** a link from another website to yours.
- **Bing Webmaster Tools:** Bing's free version of Search Console.
- **Bot / crawler:** a program that visits web pages automatically (e.g. Googlebot).
- **Cannibalisation:** two of your own pages competing for the same search.
- **Canonical:** a tag saying "this is the main address of this page".
- **CLS:** Cumulative Layout Shift, how much the page jumps while loading (good ≤ 0.1).
- **Core Web Vitals:** Google's three user-experience speed measures (LCP, INP, CLS).
- **Crawling:** search engine robots visiting your pages.
- **CTR:** click-through rate, the share of people who saw your result and clicked it.
- **Disavow:** telling Google to ignore certain links. Rarely needed.
- **DMCA / legal removal:** a request to remove copied content.
- **E-E-A-T:** Experience, Expertise, Authoritativeness, Trust. Signals that real, credible people stand
  behind the content.
- **GA4:** Google Analytics 4, which measures what visitors do on your site.
- **Google Business Profile:** your business listing on Google Search and Maps.
- **H1 / headings:** the main title on the page (H1) and the section titles (H2, H3…).
- **HTTPS:** a secure connection (the padlock in the address bar).
- **Impressions:** how many times your page appeared in search results.
- **Indexing:** Google storing your page so it can show it in results.
- **INP:** Interaction to Next Paint, how fast the page reacts to taps and clicks (good ≤ 200 ms).
- **Internal link:** a link from one page of your site to another.
- **JavaScript rendering:** pages whose content is built by code in the browser. Some robots can't see it.
- **Keyword:** the words people type into a search engine.
- **LCP:** Largest Contentful Paint, how fast the main content appears (good ≤ 2.5 s).
- **Manual action:** a penalty applied by a Google employee. Shown in Search Console → *Security & Manual
  actions*.
- **Meta description:** the short summary text that can appear under your link in Google.
- **Mobile-first indexing:** Google uses the mobile version of your site to rank it.
- **Nofollow / sponsored:** link labels meaning "don't count this as a recommendation" or "this is paid".
- **Noindex:** a tag telling Google not to list a page.
- **Organic traffic:** visitors from unpaid search results.
- **PBN:** private blog network, fake sites made to create links. Forbidden.
- **Position / ranking:** where your page appears in results (1 = top).
- **Redirect (301):** automatically forwarding an old address to a new one, permanently.
- **robots.txt:** a file telling robots which parts of a site they may visit.
- **Schema / structured data:** hidden code that labels page content (business, product, article) for
  search engines.
- **Scraping:** copying other sites' content. Forbidden as an SEO tactic.
- **Search Console:** Google's free tool showing how your site performs in Google.
- **Search intent:** what the searcher actually wants (learn, compare, buy, find a site).
- **SERP:** search engine results page, the page of results Google shows.
- **Sitemap:** a file listing your pages for search engines.
- **Snippet:** the text Google shows under your link.
- **Status code:** the server's answer. 200 = OK, 301 = moved, 404 = not found, 500 = server error.
- **Thin content:** pages with little real value.
- **Title tag:** the page title shown as the blue link in Google.
- **URL:** the address of a page.
