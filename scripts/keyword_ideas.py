#!/usr/bin/env python3
"""Expand seed keywords through public autocomplete (Google, Bing, YouTube) and group them by intent and theme.

Autocomplete shows what people actually type, ordered roughly by popularity, but gives NO search volume.
Pair the output with Search Console impressions, Google Ads Keyword Planner ranges, or a paid tool for volume.

The expansion follows --hl: en, ka, ru, he, ar, de and es have their own letters, question words, modifiers and
intent words (LANGUAGES). Another --hl uses the English table and says so under warnings.
`completions` is the demand count per seed and engine: what the engine suggested for the bare seed, minus the seed
itself. Autocomplete echoes any query it has a signal for, so a seed that only echoes itself counts 0, and an echo
never makes a keyword. null means the engine could not be read, which is not 0.

The endpoints are unofficial and undocumented: keep --delay at 0.25 s or more and the runs modest. Yandex suggest
is left out on purpose (YANDEX_LEFT_OUT).

Usage:
  keyword_ideas.py "seo audit"
  keyword_ideas.py "english tutor" --hl en --gl gb --sources google,bing,youtube --deep
  keyword_ideas.py "ინგლისური ენის კურსები" --hl ka --gl ge --sources google
Outputs JSON: keywords [{keyword, sources, modifier, intent}], clusters {theme: [keywords]},
completions {seed: {source: count or null}}, language (the table used), warnings.
"""
from __future__ import annotations

import argparse
import json
import re
import string
import sys
import time
import unicodedata
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass

from seo_lib import fetch, print_json

SOURCES = ("google", "bing", "youtube")
YANDEX_LEFT_OUT = ("Yandex suggest is left out. Its endpoint is public and robots.txt allows it, but the Yandex "
                   "Search licence (yandex.ru/legal/termsofuse, clause 6.6) forbids automatic requests except through "
                   "the paid Yandex Search API")
INTENT_ORDER = ("transactional", "commercial", "informational", "navigational")  # first match wins
NOTE = ("No search volume: autocomplete only proves the query is typed. Validate with GSC impressions / "
        "Keyword Planner / a paid tool.")


@dataclass(frozen=True)
class Language:
    letters: str  # one query per letter after the seed
    deep: tuple[str, ...]  # --deep: one query per start after the seed (two letters; Arabic: ال and a letter)
    before_seed: tuple[str, ...]  # question words, and words the language puts before a noun ("best", "buy")
    after_seed: tuple[str, ...]  # modifiers
    intent_words: dict[str, tuple[str, ...]]  # per intent; a trailing * takes any ending (ფასები* matches ფასების)
    stopwords: str  # words that never name a theme


def pairs(firsts, seconds: str) -> tuple[str, ...]:
    return tuple(first + second for first in firsts for second in seconds)


HEBREW_LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"  # final forms (ך ם ן ף ץ) never start a word
ARABIC_LETTERS = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"

# Question words come from each language's Wikipedia article on question words. The other words come from Wiktionary
# translations, and a modifier is kept only when Google autocomplete returned it for a test seed on 2026-10-25.
# The English table is the one this script always used.
LANGUAGES = {
    "en": Language(
        letters=string.ascii_lowercase,
        deep=pairs("abcdefghilmnoprstw", "aeiou"),
        before_seed=("how", "what", "why", "when", "where", "who", "which", "can", "is", "does", "should"),
        after_seed=("best", "vs", "review", "price", "cost", "cheap", "near me", "for beginners", "alternative", "free",
                    "online"),
        intent_words={
            "transactional": ("buy", "price", "prices", "pricing", "cost", "cheap", "discount", "coupon", "deal",
                              "order", "hire", "book", "near me", "for sale", "subscription"),
            "commercial": ("best", "top", "vs", "versus", "review", "reviews", "compare", "comparison", "alternative",
                           "alternatives", "rated"),
            "informational": ("how", "what", "why", "when", "where", "who", "which", "guide", "tutorial", "example",
                              "examples", "meaning", "definition", "ideas", "tips", "is", "does", "can"),
            "navigational": ("login", "log in", "sign in", "app", "website", "official", "contact", "phone number"),
        },
        stopwords="a an the to for of in on and or with without is are be do does can how what why when where who "
                  "which my your near me vs",
    ),
    # Georgian, Mkhedruli. Adjectives come before the noun, so "best" and "free" go before the seed. Case endings
    # are written on the word, hence the * stems; რამდენი and რომელი stay whole (რამდენიმე is "several").
    "ka": Language(
        letters="აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ",
        deep=pairs("ბგდვკლმნპრსტქშცხ", "აეიოუ"),
        before_seed=("როგორ", "რა", "რატომ", "როდის", "სად", "ვინ", "რომელი", "რამდენი", "რა ღირს", "საუკეთესო",
                     "უფასო"),
        after_seed=("ფასი", "ფასები", "იაფად", "ონლაინ", "დამწყებთათვის", "ახლოს"),
        intent_words={
            "transactional": ("ფასი", "ფასის", "ფასად", "ფასით", "ფასები*", "ღირს", "ღირებულება*", "იაფ*",
                              "ფასდაკლება*", "ყიდვა", "ყიდვის", "ვიყიდო", "იყიდება", "შეძენა", "შეკვეთა*", "მიტანა*",
                              "ჯავშანი", "დაჯავშნა", "ქირავდება", "ქირით", "ჩემთან ახლოს"),
            "commercial": ("საუკეთესო*", "ტოპ", "top", "vs", "შედარებ*", "მიმოხილვ*", "შეფასებ*", "რეიტინგ*",
                           "ალტერნატივ*"),
            "informational": ("როგორ", "რა", "რატომ", "როდის", "სად", "ვინ", "რომელი", "რამდენი", "რას", "რისთვის",
                              "არის", "ნიშნავს", "განმარტებ*", "ინსტრუქცი*", "რჩევ*", "მაგალით*", "იდეა", "იდეები"),
            "navigational": ("შესვლა", "ავტორიზაცია", "ოფიციალური*", "აპლიკაცია", "app", "კონტაქტი", "ტელეფონის ნომერი",
                             "ცხელი ხაზი"),
        },
        stopwords="და ან თუ რომ არის ეს ის რა როგორ რატომ როდის სად ვინ რომელი რამდენი",
    ),
    # Russian, Cyrillic. ъ, ы and ь never start a word and ё is typed as е, so they get no letter query. "стоит"
    # alone is not a price ("стоит ли" is "is it worth"), only "сколько стоит" is.
    "ru": Language(
        letters="абвгдежзийклмнопрстуфхцчшщэюя",
        deep=pairs("бвгдзклмнпрстч", "аеиоу"),
        before_seed=("как", "что такое", "почему", "зачем", "когда", "где", "кто", "какой", "сколько", "можно ли",
                     "стоит ли", "лучший", "купить"),
        after_seed=("цена", "стоимость", "отзывы", "онлайн", "бесплатно", "для начинающих", "рядом", "или", "купить"),
        intent_words={
            "transactional": ("купить", "куплю", "покупк*", "цена", "цены", "цене", "цену", "цен", "ценой", "ценам",
                              "ценами", "ценах", "стоимост*", "сколько стоит", "сколько стоят", "дешев*", "недорог*",
                              "скидк*", "промокод*", "заказать", "заказ", "доставк*", "аренд*", "забронировать",
                              "бронировани*", "продаж*", "продается", "продам", "рядом со мной", "подписк*", "нанять",
                              "в наличии"),
            "commercial": ("лучш*", "топ", "рейтинг*", "отзыв*", "обзор*", "сравнени*", "сравнить", "vs", "аналог*",
                           "альтернатив*"),
            "informational": ("как", "что", "что такое", "почему", "зачем", "когда", "где", "кто", "какой", "какая",
                              "какое", "какие", "каким", "сколько", "ли", "инструкци*", "руководств*", "пример",
                              "примеры", "значение", "определение", "идеи", "советы", "своими руками"),
            "navigational": ("вход", "войти", "личный кабинет", "официальный сайт", "приложение", "контакты",
                             "номер телефона", "горячая линия", "логин", "login"),
        },
        stopwords="и в во на с со к ко по о об от до за из у для или а но не ли же как что почему зачем когда где кто "
                  "какой какая какие сколько это",
    ),
    # Hebrew. The article and prepositions are written on the word (ה, ב, ל), so the common joined forms are listed.
    # מי is not an intent word: it is also "water of" (מי פנים).
    "he": Language(
        letters=HEBREW_LETTERS,
        deep=pairs("הבלמ", HEBREW_LETTERS),
        before_seed=("איך", "מה", "למה", "מתי", "איפה", "מי", "איזה", "כמה", "האם"),
        after_seed=("מחיר", "מחירים", "זול", "מומלץ", "מומלצים", "חוות דעת", "המלצות", "הכי טוב", "אונליין"),
        intent_words={
            "transactional": ("מחיר", "המחיר", "במחיר", "מחירים", "המחירים", "מחירי", "מחירון", "עלות", "העלות",
                              "כמה עולה", "כמה זה עולה", "זול", "זולה", "זולים", "זולות", "הכי זול", "הנחה", "הנחות",
                              "קופון", "מבצע", "מבצעים", "לקנות", "קנייה", "רכישה", "רכישת", "להזמין", "הזמנה",
                              "הזמנת", "משלוח", "השכרה", "השכרת", "להשכרה", "למכירה", "קרוב אליי", "מנוי"),
            "commercial": ("הכי טוב", "הכי טובה", "הכי טובים", "הטוב ביותר", "הטובה ביותר", "הטובים ביותר", "מומלץ",
                           "מומלצת", "מומלצים", "מומלצות", "המלצה", "המלצות", "ביקורת", "ביקורות", "חוות דעת",
                           "השוואה", "השוואת", "לעומת", "vs", "דירוג", "טופ", "חלופה", "חלופות"),
            "informational": ("איך", "כיצד", "מה", "מה זה", "למה", "מדוע", "מתי", "איפה", "היכן", "איזה", "איזו",
                              "אילו", "כמה", "האם", "מדריך", "הסבר", "פירוש", "משמעות", "דוגמה", "דוגמאות", "טיפים",
                              "רעיונות"),
            "navigational": ("כניסה", "התחברות", "אתר רשמי", "האתר הרשמי", "אפליקציה", "צור קשר", "מספר טלפון",
                             "שירות לקוחות"),
        },
        stopwords="של את על עם או גם לא זה זו הוא היא מה מי איך למה מתי איפה איזה כמה האם",
    ),
    # Arabic. --deep tries the article ال, then each letter, since most words after a seed start with it. Hamza
    # forms match their bare alef (أفضل = افضل). من, ما and أي are not intent words: they also mean "from", "not"
    # and "any".
    "ar": Language(
        letters=ARABIC_LETTERS,
        deep=pairs(("ال",), ARABIC_LETTERS),
        before_seed=("كيف", "ما هو", "ما هي", "لماذا", "متى", "أين", "كم", "هل", "أي", "أفضل"),
        after_seed=("سعر", "أسعار", "تكلفة", "رخيص", "تقييم", "مجانا", "اون لاين", "بالقرب مني"),
        intent_words={
            "transactional": ("سعر", "السعر", "بسعر", "سعره", "أسعار", "الأسعار", "بأسعار", "تكلفة", "تكلفه", "التكلفة",
                              "كم سعر", "بكم", "يكلف", "كم يكلف", "رخيص", "رخيصة", "رخيصه", "أرخص", "خصم", "خصومات",
                              "تخفيض*", "كوبون", "كود خصم", "شراء", "اشتري", "للبيع", "إيجار", "للإيجار", "حجز",
                              "توصيل", "بالقرب مني", "قريب مني", "اشتراك"),
            "commercial": ("أفضل", "الأفضل", "أحسن", "الأحسن", "vs", "مقارنة", "مقارنه", "تقييم", "تقييمات", "مراجعة",
                           "مراجعات", "بديل", "بدائل", "توب"),
            "informational": ("كيف", "لماذا", "متى", "أين", "ماذا", "ما هو", "ما هي", "ما معنى", "معنى", "ما الفرق",
                              "كم", "هل", "شرح", "دليل", "طريقة", "نصائح", "مثال", "أمثلة", "تعريف", "أفكار"),
            "navigational": ("تسجيل الدخول", "الموقع الرسمي", "موقع رسمي", "تطبيق", "رقم الهاتف", "رقم هاتف",
                             "خدمة العملاء", "اتصل بنا"),
        },
        stopwords="في من على الى إلى عن مع و او أو هل كيف ما ماذا لماذا متى أين اين كم أي اي هو هي",
    ),
    # German. Umlauts get letter queries; matching ignores them, so "gunstig" typed without one still counts.
    "de": Language(
        letters=string.ascii_lowercase + "äöü",
        deep=pairs("abdefghklmnprstwz", "aeiou"),
        before_seed=("wie", "was", "warum", "wann", "wo", "wer", "welche", "kann man", "ist", "beste"),
        after_seed=("kaufen", "preis", "kosten", "günstig", "test", "erfahrungen", "vergleich", "vs", "online",
                    "kostenlos", "für anfänger", "in der nähe", "alternative"),
        intent_words={
            "transactional": ("kaufen", "kauf", "bestellen", "preis*", "kosten", "kostet", "günstig*", "billig*",
                              "rabatt*", "gutschein*", "angebot*", "mieten", "buchen", "zu verkaufen", "in der nähe",
                              "in meiner nähe", "abo", "abonnement"),
            "commercial": ("beste", "bester", "bestes", "besten", "top", "vs", "versus", "test", "testsieger",
                           "erfahrung", "erfahrungen", "bewertung*", "vergleich*", "alternative", "alternativen"),
            "informational": ("wie", "was", "was ist", "warum", "wieso", "weshalb", "wann", "wo", "wer", "welche",
                              "welcher", "welches", "kann", "ist", "anleitung", "tipps", "ideen", "beispiel",
                              "beispiele", "bedeutung", "definition", "erklärung"),
            "navigational": ("login", "anmelden", "einloggen", "app", "offizielle website", "offizielle seite",
                             "website", "kontakt", "telefonnummer", "hotline"),
        },
        stopwords="der die das den dem des ein eine einen einem einer und oder in im am an auf aus bei für mit nach "
                  "von zu zum zur ist sind wie was warum wann wo wer welche kann man nicht nähe meiner vs",
    ),
    # Spanish. Matching ignores accents, as most queries drop them ("como" for "cómo"). qué alone is not an intent
    # word: without its accent it is "que", the commonest conjunction. Nor is vale alone, which is also "okay"; only
    # "cuánto vale" is a price.
    "es": Language(
        letters=string.ascii_lowercase + "ñ",
        deep=pairs("bcdefglmnprstv", "aeiou"),
        before_seed=("cómo", "qué", "por qué", "cuándo", "dónde", "quién", "cuál", "cuánto", "se puede", "mejor",
                     "comprar"),
        after_seed=("precio", "barato", "opiniones", "mejores", "comparativa", "vs", "online", "gratis",
                    "para principiantes", "cerca de mí", "comprar"),
        intent_words={
            "transactional": ("comprar", "compra", "precio", "precios", "cuesta", "cuestan", "cuánto cuesta",
                              "cuánto cuestan", "cuánto vale", "cuánto valen", "costo", "coste", "barato", "barata",
                              "baratos", "baratas", "oferta", "ofertas", "descuento*", "cupón", "código de descuento",
                              "reservar", "reserva", "alquiler", "alquilar", "en venta", "se vende", "cerca de mí",
                              "suscripción", "contratar"),
            "commercial": ("mejor", "mejores", "top", "vs", "versus", "opinión", "opiniones", "reseña", "reseñas",
                           "comparativa", "comparación", "comparar", "alternativa", "alternativas", "ranking"),
            "informational": ("cómo", "por qué", "qué es", "qué significa", "cuándo", "dónde", "quién", "cuál",
                              "cuánto", "guía", "tutorial", "ejemplo", "ejemplos", "significado", "definición",
                              "ideas", "consejos", "se puede"),
            "navigational": ("iniciar sesión", "login", "acceder", "app", "aplicación", "página oficial",
                             "sitio oficial", "web oficial", "contacto", "número de teléfono", "atención al cliente"),
        },
        stopwords="el la los las un una unos unas de del a al en y o con sin para por que qué es cómo como cuándo "
                  "cuando dónde donde quién quien cuál cual cuánto cuanto se puede mi mí cerca vs",
    ),
}


def fold(text: str) -> str:
    """Lower case without accents or hamza marks, for matching only: "cómo" = "como", "أفضل" = "افضل", "ё" = "е"."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch))


def clean(text: str) -> str:
    return " ".join(text.lower().split())  # as research_store.py cleans a keyword


def phrase_pattern(phrase: str) -> str:
    words = phrase.rstrip("*").split()
    return r"\s+".join(re.escape(fold(word)) for word in words) + (r"\w*" if phrase.endswith("*") else "")


def intent_patterns(language: Language) -> list[tuple[str, re.Pattern]]:
    return [(intent, re.compile(r"(?<!\w)(?:" + "|".join(map(phrase_pattern, language.intent_words[intent])) +
                                r")(?!\w)")) for intent in INTENT_ORDER]


INTENT_PATTERNS = {code: intent_patterns(language) for code, language in LANGUAGES.items()}
STOPWORDS = {code: {fold(word) for word in language.stopwords.split()} for code, language in LANGUAGES.items()}


def table_for(hl: str) -> str:
    """The LANGUAGES key for an --hl value's language (ka-GE → ka), or "en" when there is no table for it."""
    code = hl.lower().split("-")[0]
    return code if code in LANGUAGES else "en"


def suggest(source: str, query: str, hl: str, gl: str) -> list[str] | None:
    """The engine's suggestions for query, or None when it could not be read: a failure is not zero suggestions."""
    if source == "google":
        url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "hl": hl, "gl": gl, "q": query})
    elif source == "youtube":
        url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "ds": "yt", "hl": hl, "gl": gl, "q": query})
    elif source == "bing":
        url = "https://api.bing.com/osjson.aspx?" + urllib.parse.urlencode({"query": query, "market": f"{hl}-{gl.upper()}"})
    else:
        raise ValueError(f"unknown source {source}")
    result = fetch(url, timeout=10)
    if result.status != 200:
        return None
    try:
        data = json.loads(result.text)
    except json.JSONDecodeError:
        return None
    if not (isinstance(data, list) and len(data) > 1 and isinstance(data[1], list)):  # not [query, [suggestions]]
        return None
    return [s for s in data[1] if isinstance(s, str)]


def completions(suggestions: list[str], query: str) -> list[str]:
    """The suggestions minus the echo: the engine returns the query itself (or it without accents) whenever it has
    any signal for it, so the echo is no evidence of demand."""
    typed = fold(clean(query))
    return [s for s in suggestions if fold(clean(s)) != typed]


def classify_intent(keyword: str, language: str = "en") -> str:
    """The first intent in INTENT_ORDER whose words the keyword contains, by the language's table (English when it
    has none); "unclear" when none match."""
    text = fold(keyword)
    for intent, pattern in INTENT_PATTERNS[table_for(language)]:
        if pattern.search(text):
            return intent
    return "unclear"


def theme_of(keyword: str, seed_tokens: set[str], stopwords: set[str]) -> str:
    tokens = [t for t in re.findall(r"[\w']+", keyword.lower()) if fold(t) not in seed_tokens | stopwords]
    return tokens[0] if tokens else "(head term)"


def expansion_queries(seed: str, language: Language, deep: bool) -> list[tuple[str, str]]:
    """(query, modifier) pairs: the seed, the seed + each letter, words before and after the seed, and with deep the
    seed + each two-letter start."""
    queries = [(seed, "seed")]
    queries += [(f"{seed} {c}", f"+{c}") for c in language.letters]
    queries += [(f"{w} {seed}", f"{w}+") for w in language.before_seed]
    queries += [(f"{seed} {w}", f"+{w}") for w in language.after_seed]
    if deep:
        queries += [(f"{seed} {d}", f"+{d}") for d in language.deep]
    return queries


def expand(seed: str, sources: list[str], hl: str, gl: str, language: str, deep: bool,
           delay: float) -> tuple[dict[str, dict], dict[str, int | None], Counter]:
    """Keywords found for one seed, its completion count per engine, and the requests each engine failed."""
    found: dict[str, dict] = {}
    seed_completions: dict[str, int | None] = {}
    failed: Counter = Counter()

    def add(keyword: str, source: str, modifier: str) -> None:
        keyword = clean(keyword)
        entry = found.setdefault(keyword, {"keyword": keyword, "sources": [], "modifier": modifier,
                                           "intent": classify_intent(keyword, language)})
        if source not in entry["sources"]:
            entry["sources"].append(source)

    for query, modifier in expansion_queries(seed, LANGUAGES[language], deep):
        for source in sources:
            suggestions = suggest(source, query, hl, gl)
            if suggestions is None:
                failed[source] += 1
            real = completions(suggestions or [], query)
            if modifier == "seed":
                seed_completions[source] = None if suggestions is None else len(real)
                if real:  # completions prove people type the seed; its echo alone would not
                    add(seed, source, "seed")
            for keyword in real:
                add(keyword, source, modifier)
            time.sleep(delay)
    return found, seed_completions, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("seed", nargs="+", help="one or more seed phrases")
    ap.add_argument("--hl", default="en", help="interface language, which also picks the expansion table: en, ka, "
                                               "ru, he, ar, de, es (another language uses en)")
    ap.add_argument("--gl", default="us", help="country, e.g. us, gb, ge")
    ap.add_argument("--sources", default="google,bing", help="comma list of google,bing,youtube")
    ap.add_argument("--deep", action="store_true", help="also try two-letter starts after the seed (70–90 more "
                                                        "requests per source; Arabic: ال + each letter)")
    ap.add_argument("--delay", type=float, default=0.25)
    args = ap.parse_args()
    sources = list(dict.fromkeys(s.strip() for s in args.sources.split(",") if s.strip()))  # each engine once
    for source in sources:
        if source == "yandex":
            raise SystemExit(f"--sources yandex: {YANDEX_LEFT_OUT}")
        if source not in SOURCES:
            raise SystemExit(f"--sources {source}: unknown engine (use {','.join(SOURCES)})")
    language = table_for(args.hl)
    warnings = [] if language == args.hl.lower().split("-")[0] else [
        f"--hl {args.hl}: no expansion table for this language, so the English letters, question words and intent "
        f"words were used"]

    keywords: dict[str, dict] = {}
    seed_completions: dict[str, dict[str, int | None]] = {}
    failed: Counter = Counter()
    for seed in args.seed:
        found, counts, seed_failed = expand(seed, sources, args.hl, args.gl, language, args.deep, args.delay)
        keywords.update({k: v for k, v in found.items() if k not in keywords})
        seed_completions[seed] = counts
        failed.update(seed_failed)
    requests = sum(len(expansion_queries(seed, LANGUAGES[language], args.deep)) for seed in args.seed)
    warnings += [f"{source}: {failed[source]} of {requests} requests failed, so its suggestions are incomplete"
                 for source in sources if failed[source]]
    seed_tokens = {fold(t) for s in args.seed for t in re.findall(r"[\w']+", s.lower())}
    clusters = defaultdict(list)
    for kw in keywords:
        clusters[theme_of(kw, seed_tokens, STOPWORDS[language])].append(kw)
    ordered = dict(sorted(clusters.items(), key=lambda kv: -len(kv[1])))
    print_json({
        "seeds": args.seed, "locale": f"{args.hl}-{args.gl}", "language": language, "sources": sources,
        "total": len(keywords),
        "completions": seed_completions,
        "intent_counts": dict(Counter(v["intent"] for v in keywords.values())),
        "multi_source": [k for k, v in keywords.items() if len(v["sources"]) > 1][:50],
        "clusters": ordered,
        "keywords": list(keywords.values()),
        "warnings": warnings,
        "note": NOTE,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
