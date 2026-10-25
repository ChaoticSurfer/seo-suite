"""keyword_ideas.py: expansion in the seed's own language (en, ka, ru, he, ar, de, es), demand counts without the
echoed query, intent words per language, and output that research_store.py ingests. The engines are faked with
Google and Bing autocomplete responses recorded on 2026-10-25, so no test touches the network.
Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import string
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import keyword_ideas as ki  # noqa: E402
from seo_lib import FetchResult  # noqa: E402

KA_SEED = "ინგლისური ენის კურსები"
RU_SEED = "репетитор английского"
# Google, --hl ka --gl ge, recorded 2026-10-25: every query of the Georgian expansion that returned anything. The
# other letters, question words and modifiers returned [].
GOOGLE_KA_COURSES = {
    KA_SEED: ["ინგლისური ენის კურსები ქუთაისში", "ინგლისური ენის კურსები", "ინგლისური ენის კურსები ზრდასრულთათვის",
              "ინგლისური ენის კურსები ბავშვებისთვის", "ინგლისური ენის კურსები ბათუმში", "ინგლისური ენის კურსები ონლაინ",
              "ინგლისური ენის კურსები საზღვარგარეთ", "ინგლისური ენის კურსები ბრიტანეთში",
              "ინგლისური ენის კურსები ვარკეთილში", "ინგლისური ენის კურსები თბილისში"],
    f"{KA_SEED} ბ": ["ინგლისური ენის კურსები ბავშვებისთვის", "ინგლისური ენის კურსები ბათუმში",
                     "ინგლისური ენის კურსები ბრიტანეთში"],
    f"{KA_SEED} ვ": ["ინგლისური ენის კურსები ვარკეთილში"],
    f"{KA_SEED} ზ": ["ინგლისური ენის კურსები ზრდასრულთათვის"],
    f"{KA_SEED} თ": ["ინგლისური ენის კურსები თბილისში"],
    f"{KA_SEED} ო": ["ინგლისური ენის კურსები ონლაინ", "ინგლისური ენის უფასო ონლაინ კურსები"],
    f"{KA_SEED} ს": ["ინგლისური ენის კურსები საზღვარგარეთ", "ინგლისური ენის სასერთიფიკატო კურსები",
                     "ინგლისური ენის საზაფხულო კურსები", "ინგლისური ენის სალაპარაკო კურსები"],
    f"{KA_SEED} უ": ["ინგლისური ენის უფასო კურსები", "ინგლისური ენის შემსწავლელი უფასო კურსები",
                     "ინგლისური ენის უფასო ონლაინ კურსები"],
    f"{KA_SEED} ქ": ["ინგლისური ენის კურსები ქუთაისში"],
    f"{KA_SEED} შ": ["ინგლისური ენის შემსწავლელი კურსები", "ინგლისური ენის შემსწავლელი უფასო კურსები"],
    f"{KA_SEED} ონლაინ": ["ინგლისური ენის კურსები ონლაინ", "ინგლისური ენის უფასო ონლაინ კურსები"],
}
# Google, --hl ka --gl ge, recorded 2026-10-25: the two shapes of zero demand. "Money picture" returns only itself,
# "money frame" returns nothing.
GOOGLE_KA_NO_DEMAND = {"ფულის სურათი": ["ფულის სურათი"], "ფულის ჩარჩო": []}
# Google and Bing, --hl ru --gl ge, recorded 2026-10-25, trimmed to these queries.
GOOGLE_RU_TUTOR = {
    RU_SEED: ["репетитор английского", "репетитор английского языка", "репетитор английского языка онлайн",
              "репетитор английского минск", "репетитор английского харьков", "репетитор английского вакансии",
              "репетитор английского днепр", "репетитор английского одесса", "репетитор английского языка для взрослых",
              "репетитор английского украина"],
    f"{RU_SEED} о": ["репетитор английского онлайн", "репетитор английского одесса", "репетитор английского олх",
                     "репетитор английского онлайн украина", "репетитор английского онлайн вакансии",
                     "репетитор английского онлайн беларусь", "репетитор английского онлайн олх",
                     "репетитор английского олх украина", "репетитор английского офлайн",
                     "репетитор английского одесса форум"],
    f"{RU_SEED} ц": ["репетитор английского цена", "репетитор английского цена за час",
                     "репетитор английского украина цена", "репетитор английского цена киев",
                     "репетитор английского ціна",
                     "репетитор английского одесса цена", "репетитор английского харьков цена",
                     "репетитор английского днепр цена", "репетитор английского минск цена",
                     "репетитор английского москва цена"],
    f"{RU_SEED} и": ["репетитор английского или репетитор по английскому", "репетитор английского измаил",
                     "репетитор английского иркутск", "репетитор английского израиль цена",
                     "репетитор английского инстаграм", "репетитор английского и немецкого", "репетитор английского ии",
                     "репетитор английского ижевск", "репетитор английского ирпень", "репетитор английского израиль"],
    f"сколько {RU_SEED}": ["сколько зарабатывает репетитор английского", "сколько стоит репетитор английского языка",
                           "сколько зарабатывает репетитор английского в месяц",
                           "сколько стоит репетитор английского в час", "сколько стоит репетитор английского в москве",
                           "сколько зарабатывает репетитор английского в москве",
                           "сколько стоит репетитор английского в украине",
                           "сколько стоит репетитор английского в минске",
                           "сколько стоит репетитор английского в германии", "сколько берет репетитор английского"],
    f"лучший {RU_SEED}": ["лучший репетитор английского", "лучший ии репетитор английского языка"],
    f"{RU_SEED} отзывы": ["репетитор английского отзывы", "репетитор английского языка отзывы",
                          "репетитор английского языка бишкек отзывы", "репетитор английского языка в ташкенте отзывы"],
    f"{RU_SEED} недорого": ["репетитор английского недорого"],  # the echo and nothing else
}
BING_RU_TUTOR = {
    RU_SEED: ["репетитор английского", "репетитор английского языка", "репетитор английского языка онлайн",
              "репетитор английского онлайн", "репетитор английского минск телефон"],
    f"{RU_SEED} о": ["репетитор английского онлайн"],
    f"{RU_SEED} я": ["репетитор английского языка", "репетитор английского языка онлайн"],
    f"{RU_SEED} онлайн": ["репетитор английского онлайн"],
}
# Google, --hl es --gl es, recorded 2026-10-25: the echo comes back without the accent the query was typed with.
GOOGLE_ES_LAPTOP = {
    "portátil comprar": ["portatil comprar", "portátil comprar aire acondicionado", "portatil comprar barato",
                         "comprar portatil reacondicionado", "comprar portatil hp", "comprar portatil apple",
                         "comprar portatil a plazos", "comprar portatil lenovo", "comprar portatil segunda mano",
                         "comprar portatil dell"],
}
# Real completions from the 2026-10-25 recordings, with the intent their words show.
INTENT_EXAMPLES = {
    "ka": {"სასტუმრო იაფად ბათუმში": "transactional", "ბაკურიანი სასტუმრო ფასები": "transactional",
           "რა ღირს სასტუმრო ბათუმში": "transactional", "საუკეთესო სასტუმროები ბათუმში": "commercial",
           "როგორ ვისწავლოთ ინგლისური ენა": "informational", "რა არის სასტუმრო": "informational",
           "ინგლისური ენის კურსები თბილისში": "unclear"},
    "ru": {"репетитор английского цена за час": "transactional",
           "сколько стоит репетитор английского языка": "transactional",
           "английский язык учебник купить": "transactional", "английский язык рядом со мной": "transactional",
           "репетитор английского отзывы": "commercial", "лучший репетитор английского": "commercial",
           "сколько зарабатывает репетитор английского": "informational",
           "стоит ли изучать английский язык": "informational", "репетитор английского": "unclear"},
    "he": {"כמה עולה טיול מאורגן ליפן": "transactional", "טיול מאורגן זול לאירופה": "transactional",
           "רופא שיניים מומלץ בירושלים": "commercial", "רופא שיניים הכי טוב בארץ": "commercial",
           "איך אומרים טיול מאורגן באנגלית": "informational", "טיול מאורגן ליפן": "unclear"},
    "ar": {"كم تكلفة السياحة في جورجيا لمدة اسبوع": "transactional", "فندق رخيص في مكه": "transactional",
           "فندق بالقرب مني رخيص": "transactional", "افضل اماكن السياحة في جورجيا": "commercial",
           "تقييم فندق مون بيتش الغردقة": "commercial", "هل السياحه في جورجيا امنه": "informational",
           "كيف السياحه في جورجيا": "informational", "السياحة في جورجيا للعوائل": "unclear"},
    "de": {"was kostet englisch nachhilfe": "transactional", "laptop günstig media markt": "transactional",
           "englisch nachhilfe in meiner nähe": "transactional", "laptop testsieger 2026": "commercial",
           "jumper laptop erfahrungen": "commercial", "wie gibt man englisch nachhilfe": "informational",
           "ist georgien eine reise wert": "informational", "georgien reisezeit": "unclear"},
    "es": {"clases de ingles precio por hora": "transactional",
           "cuanto cuesta un viaje a georgia europa": "transactional",
           "clases de inglés cerca de mí gratis": "transactional",
           "cuánto cuestan las clases de inglés": "transactional",
           "cuanto valen las clases de inglés": "transactional", "clases de ingles opiniones": "commercial",
           "comparativa portatil gaming": "commercial", "como dar clases de inglés desde cero": "informational",
           "dónde dan clases de inglés": "informational", "viaje a georgia y armenia": "unclear"},
}
# Plural, case and construct forms of the price words, beyond the recorded ones above. A question word leads most of
# them, so a missing form reads as informational.
PRICE_WORD_FORMS = {
    "ru": ("сколько стоят курсы английского", "узнать цену на курсы", "курсы английского с ценами",
           "репетитор английского в ценах"),
    "es": ("cuánto vale un viaje a georgia",),
    "he": ("מחירי טיסות לגאורגיה", "השכרת רכב בתבילסי", "הזמנת מלון בתבילסי", "רכישת כרטיסי טיסה"),
    "ar": ("كم يكلف فندق في تبليسي", "بكم فندق في تبليسي"),
}
# What keyword_ideas.py sent for an English seed before the per-language tables, which must not change.
OLD_ENGLISH_BEFORE = ["how", "what", "why", "when", "where", "who", "which", "can", "is", "does", "should"]
OLD_ENGLISH_AFTER = ["best", "vs", "review", "price", "cost", "cheap", "near me", "for beginners", "alternative",
                     "free", "online"]
OLD_ENGLISH_DEEP = [c + d for c in "abcdefghilmnoprstw" for d in "aeiou"]

GEORGIAN_LETTERS = {chr(code) for code in range(0x10D0, 0x10F1)}  # the 33 letters of Mkhedruli, ა to ჰ
LATIN = re.compile(r"[a-z]")


class RecordedEngines:
    """Stands in for seo_lib.fetch: answers each autocomplete URL from recorded responses ([] for a query nobody
    recorded) and keeps every request."""

    def __init__(self, google: dict | None = None, bing: dict | None = None, failing: tuple[str, ...] = ()):
        self.recorded = {"google": google or {}, "bing": bing or {}}
        self.failing = failing
        self.requests: list[tuple[str, str, dict]] = []

    def __call__(self, url: str, timeout: float = 20.0) -> FetchResult:
        parts = urllib.parse.urlsplit(url)
        params = dict(urllib.parse.parse_qsl(parts.query))
        source = "bing" if parts.hostname == "api.bing.com" else "youtube" if params.get("ds") == "yt" else "google"
        query = params["query"] if source == "bing" else params["q"]
        self.requests.append((source, query, params))
        if source in self.failing:
            return FetchResult(url, url, 429, {}, b"", [], 1)
        body = json.dumps([query, self.recorded.get(source, {}).get(query, [])], ensure_ascii=False).encode()
        return FetchResult(url, url, 200, {"content-type": "application/json; charset=utf-8"}, body, [], 1)

    def queries(self, source: str = "google") -> list[str]:
        return [query for engine, query, _ in self.requests if engine == source]


def run(engines: RecordedEngines, *args: str) -> dict:
    """keyword_ideas.py's main() against the recorded engines, with no delay; returns its JSON."""
    with mock.patch.object(ki, "fetch", engines), \
            mock.patch.object(sys, "argv", ["keyword_ideas.py", *args, "--delay", "0"]), \
            contextlib.redirect_stdout(io.StringIO()) as out:
        ki.main()
    return json.loads(out.getvalue())


def keywords_of(output: dict) -> dict[str, dict]:
    return {item["keyword"]: item for item in output["keywords"]}


def expansions(queries: list[str], seed: str) -> list[str]:
    """What each query added to the seed, before or after it."""
    return [query.replace(seed, "").strip() for query in queries if query != seed]


class ExpansionTest(unittest.TestCase):
    def test_a_georgian_seed_is_expanded_with_georgian_letters_and_words_only(self):
        engines = RecordedEngines(GOOGLE_KA_COURSES)
        run(engines, KA_SEED, "--hl", "ka", "--gl", "ge", "--sources", "google")
        added = expansions(engines.queries(), KA_SEED)
        self.assertEqual([a for a in added if LATIN.search(a)], [])
        self.assertEqual({a for a in added if len(a) == 1}, GEORGIAN_LETTERS)
        self.assertIn(f"როგორ {KA_SEED}", engines.queries())
        self.assertIn(f"{KA_SEED} ფასი", engines.queries())
        self.assertEqual({(p["hl"], p["gl"]) for _, _, p in engines.requests}, {("ka", "ge")})

    def test_a_russian_seed_is_expanded_with_cyrillic_letters_and_words_only(self):
        engines = RecordedEngines(GOOGLE_RU_TUTOR, BING_RU_TUTOR)
        run(engines, RU_SEED, "--hl", "ru", "--gl", "ge", "--sources", "google,bing")
        for source in ("google", "bing"):
            with self.subTest(source=source):
                added = expansions(engines.queries(source), RU_SEED)
                self.assertEqual([a for a in added if LATIN.search(a)], [])
                letters = {a for a in added if len(a) == 1}
                self.assertTrue(letters <= set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя"), letters)
                self.assertGreaterEqual(len(letters), 28)
                self.assertIn(f"как {RU_SEED}", engines.queries(source))
                self.assertIn(f"{RU_SEED} цена", engines.queries(source))
        self.assertEqual({p["market"] for engine, _, p in engines.requests if engine == "bing"}, {"ru-GE"})

    def test_hebrew_and_arabic_seeds_use_their_own_script(self):
        scripts = {"he": (0x05D0, 0x05EA), "ar": (0x0621, 0x064A)}
        for hl, (first, last) in scripts.items():
            with self.subTest(hl=hl):
                engines = RecordedEngines()
                seed = {"he": "טיול מאורגן", "ar": "فندق"}[hl]
                run(engines, seed, "--hl", hl, "--gl", "il" if hl == "he" else "ae", "--sources", "google", "--deep")
                added = expansions(engines.queries(), seed)
                self.assertEqual([a for a in added if LATIN.search(a)], [])
                letters = {a for a in added if len(a) == 1}
                self.assertGreaterEqual(len(letters), 22)
                self.assertTrue(all(first <= ord(c) <= last for c in letters), letters)
        self.assertIn("فندق الب", engines.queries())  # Arabic --deep: the article ال, then each letter

    def test_german_and_spanish_add_their_own_letters(self):
        for hl, seed, extra in (("de", "englisch nachhilfe", "äöü"), ("es", "clases de inglés", "ñ")):
            with self.subTest(hl=hl):
                engines = RecordedEngines()
                run(engines, seed, "--hl", hl, "--gl", hl, "--sources", "google")
                letters = {a for a in expansions(engines.queries(), seed) if len(a) == 1}
                self.assertEqual(letters, set(string.ascii_lowercase) | set(extra))

    def test_deep_uses_the_seed_language(self):
        engines = RecordedEngines()
        run(engines, KA_SEED, "--hl", "ka", "--gl", "ge", "--sources", "google", "--deep")
        two_letter = [a for a in expansions(engines.queries(), KA_SEED) if len(a) == 2]
        self.assertGreater(len(two_letter), 50)
        self.assertTrue(all(set(a) <= GEORGIAN_LETTERS for a in two_letter), two_letter[:5])

    def test_an_english_seed_is_expanded_as_before(self):
        engines = RecordedEngines()
        run(engines, "seo audit", "--hl", "en", "--gl", "gb", "--sources", "google", "--deep")
        expected = ["seo audit"] + [f"seo audit {c}" for c in string.ascii_lowercase]
        expected += [f"{p} seo audit" for p in OLD_ENGLISH_BEFORE] + [f"seo audit {s}" for s in OLD_ENGLISH_AFTER]
        expected += [f"seo audit {d}" for d in OLD_ENGLISH_DEEP]
        self.assertEqual(engines.queries(), expected)

    def test_another_language_uses_the_english_table_and_says_so(self):
        output = run(RecordedEngines(), "cours d'anglais", "--hl", "fr", "--gl", "fr", "--sources", "google")
        self.assertEqual(output["language"], "en")
        self.assertTrue(any("--hl fr" in warning for warning in output["warnings"]), output["warnings"])
        self.assertEqual(run(RecordedEngines(), KA_SEED, "--hl", "ka", "--gl", "ge")["warnings"], [])


class DemandTest(unittest.TestCase):
    def test_completions_count_the_suggestions_minus_the_echo(self):
        output = run(RecordedEngines(GOOGLE_KA_COURSES), KA_SEED, "--hl", "ka", "--gl", "ge", "--sources", "google")
        self.assertEqual(output["language"], "ka")
        self.assertEqual(output["completions"], {KA_SEED: {"google": 9}})
        seed = keywords_of(output)[KA_SEED]
        self.assertEqual((seed["sources"], seed["modifier"]), (["google"], "seed"))
        self.assertIn("ინგლისური ენის უფასო ონლაინ კურსები", keywords_of(output))

    def test_a_seed_that_only_echoes_itself_has_no_demand(self):
        output = run(RecordedEngines(GOOGLE_KA_NO_DEMAND), "ფულის სურათი", "ფულის ჩარჩო", "--hl", "ka", "--gl", "ge",
                     "--sources", "google")
        self.assertEqual(output["completions"], {"ფულის სურათი": {"google": 0}, "ფულის ჩარჩო": {"google": 0}})
        self.assertEqual((output["keywords"], output["total"]), ([], 0))

    def test_an_echo_never_makes_a_keyword(self):
        output = run(RecordedEngines(GOOGLE_RU_TUTOR, BING_RU_TUTOR), RU_SEED, "--hl", "ru", "--gl", "ge",
                     "--sources", "google,bing")
        self.assertEqual(output["completions"], {RU_SEED: {"google": 9, "bing": 4}})
        keywords = keywords_of(output)
        self.assertNotIn("репетитор английского недорого", keywords)  # only ever its own echo
        self.assertEqual(sorted(keywords["репетитор английского онлайн"]["sources"]), ["bing", "google"])
        self.assertIn("репетитор английского языка онлайн", output["multi_source"])
        self.assertEqual(keywords["репетитор английского цена"]["intent"], "transactional")

    def test_the_echo_is_found_without_its_accents(self):
        output = run(RecordedEngines(GOOGLE_ES_LAPTOP), "portátil comprar", "--hl", "es", "--gl", "es",
                     "--sources", "google")
        self.assertEqual(output["completions"], {"portátil comprar": {"google": 9}})
        self.assertNotIn("portatil comprar", keywords_of(output))

    def test_an_engine_that_cannot_be_read_is_unmeasured_not_zero(self):
        output = run(RecordedEngines(GOOGLE_RU_TUTOR, failing=("bing",)), RU_SEED, "--hl", "ru", "--gl", "ge",
                     "--sources", "google,bing")
        self.assertEqual(output["completions"], {RU_SEED: {"google": 9, "bing": None}})
        self.assertTrue(any(w.startswith("bing:") for w in output["warnings"]), output["warnings"])
        self.assertFalse(any("bing" in item["sources"] for item in output["keywords"]))


class IntentTest(unittest.TestCase):
    def test_intent_words_per_language(self):
        for language, examples in INTENT_EXAMPLES.items():
            for keyword, intent in examples.items():
                with self.subTest(language=language, keyword=keyword):
                    self.assertEqual(ki.classify_intent(keyword, language), intent)

    def test_every_form_of_a_price_word_is_transactional(self):
        for language, keywords in PRICE_WORD_FORMS.items():
            for keyword in keywords:
                with self.subTest(language=language, keyword=keyword):
                    self.assertEqual(ki.classify_intent(keyword, language), "transactional")
        self.assertEqual(ki.classify_intent("ценный совет", "ru"), "unclear")  # a word that starts like цен
        self.assertEqual(ki.classify_intent("vale la pena viajar a georgia", "es"), "unclear")  # vale is "okay" too

    def test_without_a_language_the_english_words_apply(self):
        self.assertEqual(ki.classify_intent("english tutor near me"), "transactional")
        self.assertEqual(ki.classify_intent("how to become an english tutor"), "informational")
        self.assertEqual(ki.classify_intent("english tutor jobs"), "unclear")
        self.assertEqual(ki.classify_intent("репетитор английского цена"), "unclear")  # the store's call, unchanged


class ThemeTest(unittest.TestCase):
    def test_themes_skip_the_languages_function_words(self):
        output = run(RecordedEngines(GOOGLE_RU_TUTOR), RU_SEED, "--hl", "ru", "--gl", "ge", "--sources", "google")
        self.assertIn("немецкого", output["clusters"])  # "…и немецкого": "и" is not a theme
        for stopword in ("и", "в", "для", "или", "сколько", "как"):
            self.assertNotIn(stopword, output["clusters"])

    def test_a_seed_word_typed_without_its_accent_is_still_the_seed(self):
        engines = RecordedEngines({"clases de inglés": ["clases de ingles online", "clases de inglés gratis"]})
        output = run(engines, "clases de inglés", "--hl", "es", "--gl", "es", "--sources", "google")
        self.assertEqual(output["clusters"]["online"], ["clases de ingles online"])


def answering(body: str):
    """A fetch whose every reply is a 200 with this body."""
    return lambda url, timeout=20.0: FetchResult(url, url, 200, {"content-type": "application/json"}, body.encode(),
                                                 [], 1)


class SourcesTest(unittest.TestCase):
    def test_each_engine_is_asked_once_however_often_it_is_named(self):
        engines = RecordedEngines(GOOGLE_RU_TUTOR, failing=("bing",))
        output = run(engines, RU_SEED, "--hl", "ru", "--gl", "ge", "--sources", "google,bing,bing")
        self.assertEqual(output["sources"], ["google", "bing"])
        self.assertEqual(len(engines.queries("bing")), len(engines.queries("google")))
        requests = len(engines.queries("google"))
        self.assertEqual([w for w in output["warnings"] if w.startswith("bing:")],
                         [f"bing: {requests} of {requests} requests failed, so its suggestions are incomplete"])

    def test_a_reply_of_the_wrong_shape_is_unmeasured_not_a_crash(self):
        for body in ("{}", '["q", null]', '["q"]', '"x"'):
            with self.subTest(body=body):
                output = run(answering(body), "seo audit", "--sources", "google")
                self.assertEqual(output["completions"], {"seo audit": {"google": None}})
                self.assertTrue(any(w.startswith("google:") for w in output["warnings"]), output["warnings"])


    def test_yandex_is_refused_with_the_reason(self):
        engines = RecordedEngines()
        with self.assertRaises(SystemExit) as refused:
            run(engines, RU_SEED, "--hl", "ru", "--gl", "ge", "--sources", "google,yandex")
        self.assertIn("yandex", str(refused.exception))
        self.assertIn("Search API", str(refused.exception))
        self.assertEqual(engines.requests, [])

    def test_an_unknown_engine_is_named(self):
        engines = RecordedEngines()
        with self.assertRaises(SystemExit) as refused:
            run(engines, "seo audit", "--sources", "google,duckduckgo")
        self.assertIn("duckduckgo", str(refused.exception))
        self.assertEqual(engines.requests, [])


class StoreCompatibilityTest(unittest.TestCase):
    def test_research_store_ingests_the_output(self):
        cases = (("ka", "ge", KA_SEED, RecordedEngines(GOOGLE_KA_COURSES), "google"),
                 ("ru", "ge", RU_SEED, RecordedEngines(GOOGLE_RU_TUTOR, BING_RU_TUTOR), "google,bing"))
        with tempfile.TemporaryDirectory() as work:
            store = os.path.join(work, "seo-research")
            self.store_cli("init", "--site", "https://example.com", "--locales", "ka,ru", "--dir", store)
            for locale, gl, seed, engines, sources in cases:
                with self.subTest(locale=locale):
                    output = run(engines, seed, "--hl", locale, "--gl", gl, "--sources", sources)
                    path = os.path.join(work, f"kw-{locale}.json")
                    with open(path, "w", encoding="utf-8") as fh:
                        json.dump(output, fh, ensure_ascii=False)
                    summary = self.store_cli("ingest", "keyword-ideas", path, "--locale", locale, "--dir", store)
                    self.assertEqual(summary["added"], len(output["keywords"]))

    def store_cli(self, *args: str) -> dict:
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "research_store.py"), *args],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
