#!/usr/bin/env python3
"""Readability and quality heuristics for one text, aimed at blog posts an LLM wrote or translated.

It points at patterns reviewers associate with unedited model output: chatbot leftovers and placeholders, chat-reply
phrases, stock phrases, repeated sentences and phrases, uniform sentence length, em-dash and "Label: text" list habits,
generic openings and closings, heavy hedging, statistics with no source, and question headings answered with filler.
Placeholders in prompt templates the post shows are reported apart, at low severity: any placeholder inside quotation
marks, and the [..] and {{..}} slots on a line that opens like a prompt, numbered or not ("Prompt:", "User:", "Copy
this prompt", "Act as a"), under a section heading (h2-h6) that names prompts, or in a post with 10 or more unquoted
slots. TODO, lorem ipsum, XX% and 2025-XX-XX date markers are not slots: they stay leftovers unless quoted. Known
limit: a placeholder in an example model output the post shows (the "[Your Name]" signing an example email) still
reads as a leftover. It also flags text that the hidden attribute or an inline style hides (display:none, transparent
text, off-screen positioning...), and comments, when they address AI systems (Bing lists prompt injection as abuse;
Google's spam policies cover attempts to manipulate generative AI answers). Accordions, tabs, the collapsed content
of <details>, React streaming segments a script shows, and code samples are not hidden text; text hidden inside a
<details> still is. Known limit: a hidden <b>, <em> or <a> that a parent's end tag closes is not reopened in the
paragraphs after it, as browsers reopen it, so text it hides there is missed.

There is deliberately no "probability this was AI-written" score. Such detectors are unreliable: OpenAI withdrew its
own AI-text classifier in July 2023 for low accuracy, and detectors flag non-native English writing as AI-generated
far more often than native writing (Liang et al., Patterns, 2023). Google judges content by quality and purpose, not
by how it was made (using generative AI alone does not set the page-quality rating), so the useful question is "is
this accurate, edited and worth reading?", not "was this AI?".

Usage:
  ai_text_check.py https://blog.example.com/post
  ai_text_check.py --file draft.md                 # HTML or Markdown (.md, .markdown, .mdx)
  cat draft.txt | ai_text_check.py -               # stdin: HTML if it starts with '<', else Markdown or plain text
  ai_text_check.py --file post.ka.html --lang ka   # override the detected language (ka-GE counts as ka)
Outputs JSON {"url" | "file", "language", "words", "metrics": {...}, "findings": [...]}; ids start with "ai-text-".
Markdown template syntax ({{ site.baseurl }}, {% include %}) is read as text, so check drafts that use it as built HTML.

Every metric and finding is a heuristic: the thresholds are rules of thumb, not published standards, and human writers
trip them too. Treat hits as places to edit and fact-check. English phrase lists follow WikiProject AI Cleanup's "Signs
of AI writing" and the excess-vocabulary study of Kobak et al. (Science Advances, 2025); the ru, ka, de, es and fr
lists are short calques of the English chatbot leftovers and stock phrases, not measured on corpora. Languages
without a list (it, pt, nl, pl, tr, uk...) get only the language-independent checks.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import Counter
from html.parser import HTMLParser

from seo_lib import Finding, fetch, load_local, print_json, sort_findings
from translation_check import (
    WORD_RE, MainContent, detect_language, is_markdown_path, main_content, markdown_to_html, primary_subtag,
)

MIN_WORDS = 150  # below this, rates and spreads mean little: only leftovers, chat phrases, placeholders and hidden text
MIN_SENTENCES_FOR_SPREAD = 15
LOW_SENTENCE_CV = 0.35  # [heuristic] sentence-length stdev / mean below this reads as monotone ("low burstiness")
STOCK_PHRASES_PER_1000 = 3.0  # [heuristic]
MIN_STOCK_HITS = 3
EM_DASH_PER_1000 = 6.0  # [heuristic] English only; WikiProject AI Cleanup dates this sign 2022 to September 2026
HEDGES_PER_1000 = 20.0  # [heuristic]
LABEL_LIST_SHARE, MIN_LABEL_ITEMS = 0.5, 5  # [heuristic] most list items shaped "Label: explanation"
NGRAM_SIZE, NGRAM_MIN_COUNT, NGRAM_MANY = 5, 3, 5  # a 5-word phrase 3+ times (twice over), or one phrase 5+ times
REPEATED_SENTENCE_MIN_WORDS = 6
OPENING_BLOCKS = CLOSING_BLOCKS = 2
EXAMPLES = 5
EM_DASH_LANGUAGES = {"en"}  # Russian, Spanish, French and others use the dash as ordinary punctuation

_W = r"(?<!\w)"  # phrase boundaries that also work for Cyrillic and Georgian
_E = r"(?!\w)"

# A model talking about itself or the chat, pasted into the post by mistake (rater guidelines name "As an AI language
# model"). People rarely write these on purpose.
MODEL_LEFTOVERS = {
    "en": [r"as an ai(?: language)? model", r"as a large language model", r"as an ai assistant",
           r"i (?:cannot|can't|am unable to) (?:browse|access the internet)", r"i don't have (?:access to )?real-time",
           r"as of my (?:last )?(?:knowledge )?(?:update|cutoff)", r"my knowledge cutoff", r"regenerate response",
           r"here(?:'s| is) (?:a|the|your) (?:revised|rewritten|improved|updated) (?:version|draft)",
           r"here(?:'s| is) the (?:\w+ )?translation"],
    "ru": [r"как (?:ии|ai)[- ]?(?:модель|ассистент)", r"как языковая модель", r"как искусственный интеллект,",
           r"я не могу (?:просматривать|просмотреть|получить доступ)", r"вот (?:переработанная|исправленная|улучшенная) версия",
           r"вот перевод", r"на момент моего последнего обновления"],
    "ka": [r"როგორც ხელოვნური ინტელექტის", r"როგორც ენობრივი მოდელი", r"აი თარგმანი"],
    "de": [r"als (?:ki-)?sprachmodell", r"als künstliche intelligenz",
           r"hier ist (?:die|eine) (?:überarbeitete|verbesserte) (?:version|fassung)", r"hier ist die übersetzung"],
    "es": [r"como (?:un )?modelo de lenguaje", r"como (?:una )?inteligencia artificial,",
           r"aquí (?:tienes|está) (?:la|una) (?:versión revisada|traducción)"],
    "fr": [r"en tant que modèle de langage", r"en tant qu'(?:ia|intelligence artificielle)",
           r"voici (?:la|une) (?:version révisée|traduction)"],
}
# Chat-reply phrasing that bloggers also write ("I hope this helps", "feel free to adjust"): a weak tell only.
CHATBOT_PHRASES = {
    "en": [r"i hope this helps", r"(?:certainly|sure|absolutely)! here(?:'s| is)",
           r"let me know if you(?:'d| would)? (?:like|need|want)", r"feel free to (?:adjust|modify|customi[sz]e|tweak)",
           r"is not publicly available"],
    "ru": [r"надеюсь, это (?:поможет|было полезно)", r"конечно! вот", r"дайте (?:мне )?знать, если"],
    "ka": [r"იმედი მაქვს, ეს დაგეხმარებათ", r"იმედია, ეს დაგეხმარებათ", r"რა თქმა უნდა! აი"],
    "de": [r"ich hoffe, (?:das|dies) hilft", r"sicher! hier"],
    "es": [r"espero que (?:esto|esta información) (?:te|le) (?:ayude|sea útil)", r"¡claro! aquí"],
    "fr": [r"j'espère que cela (?:vous )?(?:aide|aidera)", r"bien sûr ?! voici"],
}
# Placeholders an LLM leaves for the writer to fill: checked in every language. Template slots are also how prompt
# templates mark what the reader fills in; the leftover markers are not.
TEMPLATE_SLOT_PLACEHOLDERS = [
    re.compile(r"\[(?:insert|add|your|placeholder|link|source|citation|name|company|date|number|statistic|example|"
               r"вставьте|добавьте|укажите|ваш|ваше|ваша|ссылка|источник|ჩასვით|დაამატეთ|მიუთითეთ|თქვენი|ბმული|წყარო|"
               r"einfügen|fügen|ihr|ihre|quelle|inserte|insertar|añadir|tu|fuente|enlace|insérer|insérez|ajouter|votre|lien)"
               r"(?!\w)[^\]]{0,60}\]", re.I),
    re.compile(r"\{\{\s*[\w -]+\s*\}\}"),  # {{product name}}; a dotted template variable ({{ site.baseurl }}) is code
]
LEFTOVER_MARKERS = [
    re.compile(r"\blorem ipsum\b", re.I), re.compile(r"\bINSERT_[A-Z_]+\b"),
    re.compile(r"\b(?:19|20)\d\d-XX-XX\b"), re.compile(r"\bXX(?:[.,]X+)?\s?%"), re.compile(r"\((?:add|insert) [^)]{1,60} here\)", re.I),
    # Markers only ("TODO:", "[TODO ...]", "(TBD)"): a "TODO list" is prose. Case-sensitive: Spanish "todo" is a word.
    re.compile(r"\b(?:TODO|TBD|FIXME)\s*:|[\[(]\s*(?:TODO|TBD|FIXME)\b[^\])]{0,60}[\])]"),
]
# Placeholders a post shows on purpose, in prompt templates: quoted (any kind), or, for slots only, on a prompt line,
# under a section heading (h2-h6) that names prompts, or in a prompt collection.
QUOTED_SPAN = re.compile(r"\"[^\"]*\"|“[^”]*”|«[^»]*»|„[^“”]*[“”]")
# A block that starts like a prompt, numbered or not: a "Prompt:" or "User:" label, "Copy this prompt" or "Act as a(n)".
# Not "You are a": second-person prose opens that way too ("You are a short walk from the baths").
PROMPT_LINE = re.compile(r"\s*(?:\d{1,3}[.)]\s*)?(?:(?:prompt|user)\s*:|copy this prompt\b|act as an?\b)", re.I)
PROMPT_HEADING = re.compile(r"(?<!\w)prompts?(?!\w)", re.I)  # "Best ChatGPT prompts for...", "ChatGPT-Prompts für..."
# [heuristic] this many unquoted slots make a post a prompt library; leftovers come in 1-3
TEMPLATE_COLLECTION_PLACEHOLDERS = 10
# Stock vocabulary and phrasing that model output overuses.
STOCK_PHRASES = {
    "en": [r"delv(?:e|es|ed|ing)", r"tapestr(?:y|ies)", r"(?:is|stands as|serves as) a testament to", r"testament to",
           r"(?:plays?|playing) a (?:crucial|pivotal|vital|key|significant) role", r"pivotal", r"intricate", r"meticulous(?:ly)?",
           r"showcas(?:e|es|ing)", r"underscor(?:e|es|ed|ing)", r"boasts?", r"vibrant", r"nestled", r"in the heart of",
           r"ever-(?:evolving|changing)", r"evolving landscape", r"navigat(?:e|ing) the (?:complexities|landscape|world)",
           r"embark(?:s|ing)? on", r"unlock(?:s|ing)? the (?:potential|power|secrets)", r"harness(?:es|ing)? the power",
           r"elevate your", r"seamless(?:ly)?", r"game[- ]changer", r"realm", r"a myriad of", r"plethora",
           r"it(?:'s| is) (?:important|worth|crucial) (?:to note|noting|to remember)", r"foster(?:s|ing|ed)?", r"multifaceted",
           r"interplay", r"garner(?:s|ed|ing)?", r"indelible mark", r"deeply rooted", r"rich (?:cultural )?heritage",
           r"valuable insights", r"resonat(?:e|es|ing) with", r"not only\b[^.]{1,60}\bbut also", r"whether you(?:'re| are) an?\b[^.]{1,40}\bor\b"],
    "ru": [r"важно отметить", r"стоит отметить", r"играет (?:ключевую|важную|решающую|жизненно важную) роль",
           r"является (?:ярким )?свидетельством", r"богат(?:ое|ым) (?:культурн(?:ое|ым) )?наследи(?:е|ем)", r"в самом сердце",
           r"раскры(?:ть|вает) (?:весь )?потенциал", r"не только\b[^.]{1,60}\bно и"],
    "ka": [r"მნიშვნელოვანია აღინიშნოს", r"აღსანიშნავია, რომ", r"(?:გადამწყვეტ|მნიშვნელოვან|საკვანძო) როლს ასრულებს",
           r"მდიდარი (?:კულტურული )?მემკვიდრეობა"],
    "de": [r"es ist wichtig zu beachten", r"spielt eine (?:entscheidende|zentrale|wichtige) rolle", r"ein zeugnis (?:für|von)",
           r"eintauchen", r"reiches (?:kulturelles )?erbe", r"im herzen von", r"das volle potenzial"],
    "es": [r"es importante destacar", r"cabe destacar", r"(?:desempeña|juega) un papel (?:crucial|fundamental|clave)",
           r"un testimonio de", r"rico patrimonio", r"en el corazón de", r"sumergirse en", r"todo su potencial"],
    "fr": [r"il est important de noter", r"joue un rôle (?:crucial|clé|essentiel|central)", r"témoignage de",
           r"riche patrimoine", r"au cœur de", r"plonger dans", r"tout son potentiel"],
}
GENERIC_OPENERS = {
    "en": [r"in today's (?:fast-paced|digital|modern|ever-changing|rapidly evolving|competitive) (?:world|landscape|age|era)",
           r"in (?:an|the) (?:ever-evolving|ever-changing|rapidly evolving) (?:world|landscape|realm) of", r"in an era (?:of|where|when)",
           r"have you ever wondered", r"whether you(?:'re| are) a (?:beginner|seasoned|novice|first-time)",
           r"welcome to (?:our|the|this) (?:ultimate|comprehensive|complete|definitive) guide",
           r"in this (?:article|blog post|post|guide),? (?:we(?:'ll| will)|you(?:'ll| will)) (?:explore|delve|dive|discuss|learn|look at|walk)",
           r"when it comes to", r"(?:let's|let us) (?:dive|delve) (?:in|into|right in)"],
    "ru": [r"в (?:современном|сегодняшнем|нашем) (?:быстро меняющемся |цифровом )?мире", r"в наше время", r"в эпоху",
           r"в этой статье (?:мы )?(?:рассмотрим|расскажем|разберём|разберем|поговорим)", r"вы когда-нибудь задумывались",
           r"давайте (?:разберёмся|разберемся|погрузимся)"],
    "ka": [r"თანამედროვე (?:სწრაფად ცვალებად )?სამყაროში", r"დღევანდელ (?:ციფრულ |სწრაფად ცვალებად )?სამყაროში",
           r"ამ სტატიაში (?:ჩვენ )?განვიხილავთ", r"ოდესმე დაფიქრებულხართ", r"მოდით, (?:განვიხილოთ|ჩავუღრმავდეთ)"],
    "de": [r"in der heutigen (?:schnelllebigen|digitalen|modernen) welt",
           r"in diesem (?:artikel|beitrag|leitfaden) (?:erfahren sie|werden wir|zeigen wir)",
           r"haben sie sich (?:jemals|schon einmal) gefragt", r"tauchen wir (?:ein|tiefer ein)"],
    "es": [r"en el mundo (?:actual|de hoy|digital|moderno)", r"en la era (?:digital|actual)",
           r"en este artículo,? (?:exploraremos|veremos|descubrirás|analizaremos)", r"¿alguna vez te has preguntado"],
    "fr": [r"dans le monde (?:d'aujourd'hui|actuel|numérique|moderne)", r"à l'ère (?:du numérique|numérique|actuelle)",
           r"dans cet article,? (?:nous (?:allons|verrons|explorerons)|vous découvrirez)", r"vous êtes-vous déjà demandé"],
}
GENERIC_CLOSERS = {
    "en": [r"in conclusion", r"to (?:sum|wrap) (?:it |things )?up", r"in summary", r"all in all", r"at the end of the day",
           r"by following these (?:tips|steps|strategies|guidelines)", r"the possibilities are endless",
           r"(?:happy|enjoy) (?:coding|cooking|reading|travell?ing|exploring)!", r"we hope (?:this|you found this) (?:guide|article|post)",
           r"stay tuned", r"embrace the (?:journey|future|power)"],
    "ru": [r"в заключение", r"подводя (?:итог|итоги)", r"надеемся, (?:эта статья|этот материал|это руководство)", r"в целом,"],
    "ka": [r"დასკვნის სახით", r"შეჯამების სახით", r"ყოველივე ზემოთქმულიდან გამომდინარე", r"იმედი გვაქვს, ეს სტატია"],
    "de": [r"zusammenfassend (?:lässt sich sagen|kann man sagen)", r"abschließend", r"alles in allem",
           r"wir hoffen, (?:dieser|dass dieser) (?:artikel|leitfaden)"],
    "es": [r"en conclusión", r"en resumen", r"en definitiva", r"para concluir", r"esperamos que (?:esta guía|este artículo)"],
    "fr": [r"en conclusion", r"en résumé", r"pour conclure", r"en fin de compte", r"nous espérons que (?:ce guide|cet article)"],
}
HEDGES = {
    "en": [r"may(?!\s+\d)", r"might", r"could", r"possibly", r"potentially", r"perhaps", r"arguably", r"somewhat", r"relatively",
           r"tends? to", r"in some cases", r"to some extent", r"generally"],
    "ru": [r"возможно", r"вероятно", r"как правило", r"в некоторых случаях", r"в определ[её]нной степени", r"может быть",
           r"относительно"],
    "ka": [r"ალბათ", r"შესაძლოა", r"როგორც წესი", r"ზოგ შემთხვევაში", r"გარკვეულწილად"],
    "de": [r"möglicherweise", r"eventuell", r"vielleicht", r"könnten?", r"in der regel", r"in einigen fällen", r"gewissermaßen"],
    "es": [r"posiblemente", r"quizás?", r"podrían?", r"generalmente", r"en algunos casos", r"en cierta medida", r"relativamente"],
    "fr": [r"peut-être", r"possiblement", r"pourrai(?:t|ent)", r"généralement", r"dans certains cas", r"dans une certaine mesure"],
}
# First sentence under a question heading that delays the answer.
FILLER_ANSWERS = [r"great question", r"good question", r"this is a (?:common|great|good|frequently asked) question",
                  r"it depends", r"there are (?:many|several|a number of) (?:factors|things|reasons|ways)", r"when it comes to",
                  r"(?:let's|let us) (?:dive|delve|explore|take a (?:closer )?look)", r"before we (?:dive|answer|get)",
                  r"understanding [^.]{1,40} is (?:crucial|important|essential|key)",
                  r"хороший вопрос", r"это зависит", r"давайте разбер[её]мся", r"прежде чем", r"когда речь (?:идёт|идет) о",
                  r"существует (?:множество|много) (?:факторов|причин|способов)",
                  r"კარგი კითხვაა", r"ეს დამოკიდებულია", r"მოდით, განვიხილოთ",
                  r"gute frage", r"das kommt (?:ganz )?darauf an", r"lassen sie uns", r"wenn es um",
                  r"buena pregunta", r"depende", r"veamos", r"cuando se trata de",
                  r"bonne question", r"cela dépend", r"voyons", r"(?:lorsqu|quand) il s'agit de"]
QUESTION_HEADING = re.compile(
    r"\?\s*$|^(?:how|what|why|when|which|who|where|can|is|are|do|does|should|"
    r"как|что|почему|когда|какой|какая|какие|зачем|можно|сколько|"
    r"როგორ|რა|რატომ|როდის|რომელი|სად|რამდენი|"
    r"wie|was|warum|wann|welche|"
    r"cómo|qué|por qué|cuándo|cuál|"
    r"comment|que|pourquoi|quand|quel|quelle)(?!\w)", re.I)
STATISTIC_CLAIMS = [
    re.compile(r"\d+(?:[.,]\d+)?\s?%"),
    re.compile(r"\d+(?:[.,]\d+)?\s?(?:percent|per cent|процент\w*|პროცენტ\w*|prozent|por ciento|pour cent)", re.I),
    re.compile(r"\d+(?:[.,]\d+)?\s?(?:x|×|times) (?:more|faster|less|higher|lower|better|cheaper)", re.I),
    re.compile(r"в \d+(?:[.,]\d+)? раза?", re.I),
    re.compile(r"(?:studies|research|surveys?|experts|data) (?:show|shows|suggest|suggests|indicate|indicates|found|reveal|reveals)", re.I),
    re.compile(r"according to (?:a |one |recent |the latest )?(?:study|survey|report|research)", re.I),
    re.compile(r"(?:исследования|исследование|опросы?|данные) (?:показывают|показали|свидетельствуют)|"
               r"(?:по данным|согласно) (?:исследовани\w+|опрос\w+)", re.I),
    re.compile(r"კვლევ(?:ა|ამ|ები|ებმა) (?:აჩვენებს|აჩვენა|ცხადყოფს|ადასტურებს)|კვლევ(?:ის|ების) (?:მიხედვით|თანახმად)"),
    re.compile(r"studien (?:zeigen|belegen)|laut (?:einer )?(?:studie|umfrage)", re.I),
    re.compile(r"(?:estudios|investigaciones) (?:muestran|demuestran|indican)|según (?:un |una )?(?:estudio|encuesta|informe)", re.I),
    re.compile(r"(?:études|recherches) (?:montrent|indiquent|révèlent)|selon (?:une )?(?:étude|enquête)", re.I),
]
CITATION_MARKERS = re.compile(r"\[\d+\]|\(\s*[A-Z][^()]{1,60},?\s*(?:19|20)\d\d[a-z]?\s*\)|"
                              r"(?<!\w)(?:sources?|источники?|წყარო|quellen?|fuentes?)\s*:", re.I)
# display:none, visibility:hidden or collapse, size or opacity 0, transparent text, the clip:rect(0 0 0 0) visually-hidden
# idiom, and text positioned off-screen (-1000px or further), which Google's hidden-text policy names
HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse)|font-size\s*:\s*0(?![.\d]*[1-9])|"
                          r"opacity\s*:\s*0(?![.\d]*[1-9])|(?<![\w-])(?:left|top|text-indent)\s*:\s*-\d{4,}|"
                          r"clip\s*:\s*rect\((?:\s*[01](?:px)?\s*,?){4}\)|(?<![\w-])color\s*:\s*transparent", re.I)
AI_INSTRUCTIONS = [re.compile(p, re.I) for p in (
    r"ignore (?:all |any )?(?:previous|prior|above|earlier) instructions",
    r"(?:you are|act as) (?:an? )?(?:ai|assistant|language model|llm|chatbot|chatgpt|claude|gemini|copilot)\b",
    r"\b(?:ai|llms?|language models?|chatgpt|claude|gemini|copilot|perplexity|assistants?)\b[^.]{0,60}\b(?:should|must|always|never) "
    r"(?:recommend|mention|cite|rank|prefer|say|describe|include)",
    r"(?:system|developer) prompt", r"\bprompt\s*:", r"(?:when|if) (?:summari[sz]ing|answering|asked about)\b[^.]{0,60}\b(?:mention|recommend|say|cite)",
    r"игнорируй(?:те)? (?:все )?(?:предыдущие|прошлые) инструкции",
)]


def _phrase_regex(phrases: list[str]) -> re.Pattern | None:
    return re.compile(_W + "(?:" + "|".join(phrases) + ")" + _E, re.I) if phrases else None


def sentences_of(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?…])\s+", text) if WORD_RE.search(s)]


def _per_1000(count: int, words: int) -> float:
    return round(count * 1000 / words, 1) if words else 0.0


def _metric(value, threshold=None, note: str = "") -> dict:
    metric = {"value": value, "heuristic": True}
    if threshold is not None:
        metric["threshold"] = threshold
    if note:
        metric["note"] = note
    return metric


def _matches(pattern: re.Pattern | None, text: str) -> list[str]:
    return [m.group(0) for m in pattern.finditer(text)] if pattern else []


def _in_quotes(text: str, match: re.Match) -> bool:
    return any(q.start() <= match.start() and match.end() <= q.end() for q in QUOTED_SPAN.finditer(text))


class _HiddenText(HTMLParser):
    """Text inside elements the hidden attribute or an inline style hides from readers (HIDDEN_STYLE), and the comments
    a browser keeps (<!-- -->, and the bogus <!...>, <?...> and </ ...>; a '<!--' inside a <script> is script text).
    The panels of disclosure widgets (role=region or tabpanel, an element named by aria-controls) are accordions and
    tabs a reader can open, which Google's hidden-text policy allows; the React streaming segments a script moves into
    the page (`streamed_segments`) are shown; and code (pre, code, script...) shows prompts on purpose: none counts.
    The collapsed content of <details> has no hidden attribute or hiding style, so it is not hidden text; text hidden
    inside a <details> is, since opening it shows nothing. The hidden attribute alone is no sign of a widget. Omitted
    and misnested end tags follow HTML's parsing rules: an end tag closes the elements left open inside it, unless its
    element is out of scope or is inline with a block open inside it (a misnested </a> or </b> leaves the blocks
    open); the next list item (<li>, <dt>, <dd>), table row or cell closes an open one, an <option> or <optgroup> closes
    the current <option>, and a block start closes an open <p>. Table parts outside a <table> are ignored, as browsers
    ignore them. Known limit: a hidden <b>, <em> or <a> an ancestor's end tag closes is not reopened after it, as
    browsers do (<p><em style="font-size:0"></p><p>... hides the next paragraph)."""

    _VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    _CODE = {"pre", "code", "script", "style", "template", "textarea"}
    _DISCLOSURE_ROLES = {"region", "tabpanel"}
    # HTML's "special" elements. A new list item closes an open one only across the others and <address>, <div>, <p>;
    # an inline element's end tag is ignored while one of them is open inside it.
    _SPECIAL = {"address", "applet", "area", "article", "aside", "base", "basefont", "bgsound", "blockquote", "body", "br",
                "button", "caption", "center", "col", "colgroup", "dd", "details", "dir", "div", "dl", "dt", "embed",
                "fieldset", "figcaption", "figure", "footer", "form", "frame", "frameset", "h1", "h2", "h3", "h4", "h5", "h6",
                "head", "header", "hgroup", "hr", "html", "iframe", "img", "input", "keygen", "li", "link", "listing", "main",
                "marquee", "menu", "meta", "nav", "noembed", "noframes", "noscript", "object", "ol", "p", "param",
                "plaintext", "pre", "script", "search", "section", "select", "source", "style", "summary", "table", "tbody",
                "td", "template", "textarea", "tfoot", "th", "thead", "title", "tr", "track", "ul", "wbr", "xmp"}
    _LIST_ITEM_STOPS = _SPECIAL - {"address", "div", "p"}
    # start tag: (open elements it closes, open elements that end the search), as in HTML's parsing rules
    _IMPLIED_END = {"li": ({"li"}, _LIST_ITEM_STOPS), "dt": ({"dt", "dd"}, _LIST_ITEM_STOPS),
                    "dd": ({"dt", "dd"}, _LIST_ITEM_STOPS),
                    "tr": ({"tr"}, {"table"}), "td": ({"td", "th"}, {"tr", "table"}), "th": ({"td", "th"}, {"tr", "table"}),
                    "tbody": ({"thead", "tbody", "tfoot"}, {"table"}), "tfoot": ({"thead", "tbody", "tfoot"}, {"table"})}
    _TABLE_PARTS = {"caption", "colgroup", "tbody", "td", "tfoot", "th", "thead", "tr"}  # HTML ignores them outside a table
    _CLOSES_P = {"address", "article", "aside", "blockquote", "dd", "details", "div", "dl", "dt", "fieldset", "figcaption",
                 "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "li", "main",
                 "menu", "nav", "ol", "p", "pre", "section", "table", "ul"}
    _P_SCOPE = {"button", "table", "td", "th", "caption", "object", "template"}
    # HTML's "has an element in scope": an end tag is ignored when one of these is open inside its element
    _SCOPE = {"applet", "caption", "html", "table", "td", "th", "marquee", "object", "template"}
    _END_TAG_SCOPE = {"li": _SCOPE | {"ol", "ul"}, "p": _SCOPE | {"button"},
                      **{t: {"html", "table", "template"} for t in _TABLE_PARTS | {"table"}}}
    # HTML's formatting elements: their misnested end tag runs the adoption agency
    _FORMATTING = {"a", "b", "big", "code", "em", "font", "i", "nobr", "s", "small", "strike", "strong", "tt", "u"}

    def __init__(self, streamed_segments: set[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden: list[str] = []
        self.comments: list[str] = []
        self._stack: list[tuple[str, str]] = []  # (tag, "concealed" | "code" | "")
        self._controlled: set[str] = set()  # ids named by aria-controls so far: the panels of accordions and tabs
        self._streamed = streamed_segments  # ids of the hidden React segments a script moves into the page

    def _is_open(self, tag: str) -> bool:
        return any(open_tag == tag for open_tag, _ in self._stack)

    def _close_open(self, closes: set[str], stops: set[str]) -> None:
        """Pop the innermost open element in `closes` and all inside it, unless one in `stops` is nearer."""
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] in closes:
                del self._stack[i:]
                return
            if self._stack[i][0] in stops:
                return

    def _pop_current(self, tag: str) -> None:
        if self._stack and self._stack[-1][0] == tag:
            self._stack.pop()

    def handle_starttag(self, tag, attrs):
        if tag in self._TABLE_PARTS and not self._is_open("table"):
            return
        if tag in self._IMPLIED_END:
            self._close_open(*self._IMPLIED_END[tag])
        if tag in ("option", "optgroup"):  # they close an open <option> only when it is the current element
            self._pop_current("option")
        if tag == "optgroup" and self._is_open("select"):  # and, in a <select>, then the current <optgroup>
            self._pop_current("optgroup")
        if tag in self._CLOSES_P:
            self._close_open({"p"}, self._P_SCOPE)
        if tag in self._VOID:
            return
        a = {k: (v or "") for k, v in attrs}
        self._controlled.update(a.get("aria-controls", "").split())
        shown = (a.get("role", "").lower() in self._DISCLOSURE_ROLES or a.get("id") in self._controlled
                 or a.get("id") in self._streamed)
        if tag in self._CODE:
            state = "code"
        elif ("hidden" in a or HIDDEN_STYLE.search(a.get("style", ""))) and not shown:
            state = "concealed"
        else:
            state = ""
        self._stack.append((tag, state))

    def handle_endtag(self, tag):
        scope = self._END_TAG_SCOPE.get(tag, self._SCOPE)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                self._end_element(i)
                return
            if self._stack[i][0] in scope:
                return  # an end tag whose element is not in scope is ignored

    def _end_element(self, i: int) -> None:
        """Close the element at i for its end tag, as HTML does when special elements are open inside it."""
        blocks = [j for j in range(i + 1, len(self._stack)) if self._stack[j][0] in self._SPECIAL]
        if self._stack[i][0] in self._SPECIAL or not blocks:
            del self._stack[i:]
        elif self._stack[i][0] in self._FORMATTING:  # the adoption agency: the blocks move out of the formatting element
            self._stack[i:] = [e for e in self._stack[i + 1:blocks[-1] + 1] if e[0] in self._SPECIAL | self._FORMATTING]
        # any other end tag with a special element open inside it is ignored

    def handle_comment(self, data):
        self.comments.append(data.strip())

    handle_pi = unknown_decl = handle_comment  # <?...> and <![CDATA[...]]> are comments to a browser too

    def handle_data(self, data):
        states = {state for _, state in self._stack}
        if "concealed" in states and "code" not in states and data.strip():
            self.hidden.append(data.strip())


# React streams server-rendered content in <div hidden id="S:n">, and a $RC("B:n","S:n") script then moves it to the
# <template id="B:n"> placeholder: readers see it.
REACT_REVEAL_CALL = re.compile(r'\$RC\("([^"]+)","([^"]+)"\)')
# Fenced and inline code in a Markdown draft: examples of markup, not markup the page carries.
MARKDOWN_CODE = re.compile(r"^[ \t]*(```|~~~).*?(?:^[ \t]*\1[^\n]*$|\Z)|`[^`\n]+`", re.S | re.M)


def hidden_instruction_hits(source: str, is_html: bool) -> list[tuple[str, str]]:
    """(where, text) for comments and hidden elements that address AI systems. A Markdown draft is scanned too, minus
    its code: Markdown allows raw HTML, and most renderers publish it as written."""
    if not is_html:
        source = MARKDOWN_CODE.sub(" ", source)
    streamed = {segment for placeholder, segment in REACT_REVEAL_CALL.findall(source)
                if f'<template id="{placeholder}"' in source}
    parser = _HiddenText(streamed)
    parser.feed(source)
    parser.close()
    places = [("HTML comment", text) for text in parser.comments] + [("hidden element", text) for text in parser.hidden]
    return [(where, text) for where, text in places if any(p.search(text) for p in AI_INSTRUCTIONS)]


def analyse(content: MainContent, source: str, is_html: bool, lang: str) -> tuple[dict, list[Finding]]:
    out: list[Finding] = []
    add = lambda *args: out.append(Finding(*args))
    prose = [b for b in content.blocks if not re.fullmatch(r"h[1-6]", b.kind)]
    text = " ".join(b.text for b in prose)
    words = len(WORD_RE.findall(text))
    sentences = [s for b in prose for s in sentences_of(b.text)]
    metrics: dict = {}

    # --- always: leftovers, placeholders, hidden instructions (one hit is enough)
    leftovers = _matches(_phrase_regex([p for ps in MODEL_LEFTOVERS.values() for p in ps]), content.text)
    metrics["model_leftovers"] = _metric(leftovers)
    if leftovers:
        add("ai-text-model-leftover", "high",
            f"[heuristic] {len(leftovers)} chatbot leftover(s) in the text (raters treat phrases like 'As an AI language "
            "model' as a sign of unedited AI content)", " | ".join(leftovers[:EXAMPLES]))
    chat = _matches(_phrase_regex([p for ps in CHATBOT_PHRASES.values() for p in ps]), content.text)
    metrics["chatbot_phrases"] = _metric(chat)
    if chat:
        add("ai-text-chatbot-phrase", "low",
            f"[heuristic] {len(chat)} phrase(s) typical of chatbot replies; people write them too, so delete only those "
            "pasted from a chat", " | ".join(chat[:EXAMPLES]))
    # (text, is a slot, quoted, shown on purpose): quotation marks mark any kind; a prompt line, or a section heading
    # (h2-h6) above the block that names prompts, marks slots only. The h1 is the post's title, not a section.
    hits, outline = [], {}
    for b in content.blocks:
        if re.fullmatch(r"h[1-6]", b.kind):
            level = int(b.kind[1])
            outline = {n: text for n, text in outline.items() if n < level} | {level: b.text}
        prompt_block = bool(PROMPT_LINE.match(b.text)
                            or any(PROMPT_HEADING.search(text) for n, text in outline.items() if n > 1))
        for slot, patterns in ((True, TEMPLATE_SLOT_PLACEHOLDERS), (False, LEFTOVER_MARKERS)):
            for m in (m for p in patterns for m in p.finditer(b.text)):
                quoted = _in_quotes(b.text, m)
                hits.append((m.group(0), slot, quoted, quoted or (slot and prompt_block)))
    placeholders = [h for h, _, _, _ in hits]
    # Unquoted slots make a collection, those in prompt sections included, so a library's sections whose headings
    # don't say "prompts" are covered too. Quoted prompts never do: they don't hide a leftover in the prose.
    collection = sum(1 for _, slot, quoted, _ in hits if slot and not quoted) >= TEMPLATE_COLLECTION_PLACEHOLDERS
    unfilled = [h for h, slot, _, in_template in hits if not (in_template or (slot and collection))]
    in_templates = [h for h, slot, _, in_template in hits if in_template or (slot and collection)]
    metrics["placeholders"] = _metric(placeholders)
    if unfilled:
        add("ai-text-placeholder", "high", f"[heuristic] {len(unfilled)} unfilled placeholder(s)", " | ".join(unfilled[:EXAMPLES]))
    if in_templates:
        add("ai-text-quoted-placeholder", "low",
            f"[heuristic] {len(in_templates)} placeholder(s) in prompt templates the post shows (inside quotation marks, "
            "or a bracketed slot on a 'Prompt:', 'User:' or 'Act as a...' line, under a section heading that names "
            "prompts, or "
            f"one of the {TEMPLATE_COLLECTION_PLACEHOLDERS}+ slots of a prompt library): fine if deliberate; check none "
            "is a leftover", " | ".join(in_templates[:EXAMPLES]))
    hidden = hidden_instruction_hits(source, is_html)
    metrics["hidden_ai_instructions"] = _metric([f"{where}: {text[:120]}" for where, text in hidden])
    if hidden:
        in_element = any(where == "hidden element" for where, _ in hidden)
        add("ai-text-hidden-instructions", "critical" if in_element else "high",
            f"[heuristic] {len(hidden)} hidden passage(s) address AI systems; remove them (Bing treats prompt injection as "
            "abuse, Google's spam policies cover manipulating AI answers)", " | ".join(f"{w}: {t[:100]}" for w, t in hidden[:EXAMPLES]))

    metrics["words"] = words
    metrics["sentences"] = len(sentences)
    if words < MIN_WORDS:
        add("ai-text-short-text", "info", f"[heuristic] Only {words} words of prose: rate and spread checks skipped (need {MIN_WORDS})")
        return metrics, out

    # --- vocabulary and set phrases (per language)
    stock = _matches(_phrase_regex(STOCK_PHRASES.get(lang, [])), text)
    rate = _per_1000(len(stock), words)
    metrics["stock_phrases"] = _metric({"per_1000_words": rate, "top": Counter(s.lower() for s in stock).most_common(10)},
                                       STOCK_PHRASES_PER_1000, "" if lang in STOCK_PHRASES else f"no phrase list for '{lang}'")
    if len(stock) >= MIN_STOCK_HITS and rate >= STOCK_PHRASES_PER_1000:
        add("ai-text-stock-phrases", "medium" if rate >= 2 * STOCK_PHRASES_PER_1000 else "low",
            f"[heuristic] {len(stock)} stock phrases typical of model output ({rate} per 1,000 words); rewrite them in "
            "plain, specific words", ", ".join(f"{p} ×{n}" for p, n in Counter(s.lower() for s in stock).most_common(EXAMPLES)))
    hedges = _matches(_phrase_regex(HEDGES.get(lang, [])), text)
    rate = _per_1000(len(hedges), words)
    metrics["hedging"] = _metric({"per_1000_words": rate}, HEDGES_PER_1000, "" if lang in HEDGES else f"no hedge list for '{lang}'")
    if rate >= HEDGES_PER_1000:
        add("ai-text-hedging", "low", f"[heuristic] {rate} hedges per 1,000 words (may, might, possibly...): state what is "
            "known, and source it", ", ".join(f"{p} ×{n}" for p, n in Counter(h.lower() for h in hedges).most_common(EXAMPLES)))

    # --- openings and closings
    opening, closing = prose[:OPENING_BLOCKS], prose[-CLOSING_BLOCKS:]
    intro = _matches(_phrase_regex(GENERIC_OPENERS.get(lang, [])), " ".join(b.text for b in opening))
    outro = _matches(_phrase_regex(GENERIC_CLOSERS.get(lang, [])), " ".join(b.text for b in closing))
    metrics["generic_opening"], metrics["generic_closing"] = _metric(intro), _metric(outro)
    if intro:
        add("ai-text-generic-intro", "low", f"[heuristic] Stock opening: '{intro[0]}' (start with the answer or the specific "
            "point instead)", " | ".join(b.text[:120] for b in opening))
    if outro:
        add("ai-text-generic-outro", "low", f"[heuristic] Stock closing: '{outro[0]}' (end on a specific takeaway, or just "
            "stop)", " | ".join(b.text[:120] for b in closing))

    # --- repetition
    # Digits are kept: data sentences that differ only in their figures are not repeats.
    normalised = Counter(" ".join(re.findall(r"\w+", s.casefold())) for s in sentences
                         if len(WORD_RE.findall(s)) >= REPEATED_SENTENCE_MIN_WORDS)
    repeated = [(s, n) for s, n in normalised.most_common() if n > 1]
    metrics["repeated_sentences"] = _metric(len(repeated))
    if repeated:
        add("ai-text-repeated-sentence", "medium", f"[heuristic] {len(repeated)} sentence(s) appear more than once",
            " | ".join(f"{s[:80]} ×{n}" for s, n in repeated[:EXAMPLES]))
    grams: Counter = Counter()
    for b in prose:
        tokens = [t.casefold() for t in WORD_RE.findall(b.text)]
        grams.update(" ".join(tokens[i:i + NGRAM_SIZE]) for i in range(len(tokens) - NGRAM_SIZE + 1))
    frequent = [(g, n) for g, n in grams.most_common() if n >= NGRAM_MIN_COUNT]
    metrics["repeated_phrases"] = _metric(frequent[:10], NGRAM_MIN_COUNT)
    if len(frequent) >= 2 or (frequent and frequent[0][1] >= NGRAM_MANY):
        add("ai-text-repeated-phrases", "low", f"[heuristic] {len(frequent)} five-word phrase(s) repeat {NGRAM_MIN_COUNT}+ times",
            ", ".join(f"'{g}' ×{n}" for g, n in frequent[:EXAMPLES]))

    # --- rhythm and punctuation habits
    lengths = [len(WORD_RE.findall(s)) for s in sentences if len(WORD_RE.findall(s)) >= 3]
    cv = round(statistics.pstdev(lengths) / statistics.mean(lengths), 2) if len(lengths) >= MIN_SENTENCES_FOR_SPREAD else None
    metrics["sentence_length"] = _metric({"mean_words": round(statistics.mean(lengths), 1) if lengths else None,
                                          "coefficient_of_variation": cv}, LOW_SENTENCE_CV)
    if cv is not None and cv < LOW_SENTENCE_CV:
        add("ai-text-uniform-sentences", "low",
            f"[heuristic] Sentence lengths barely vary (coefficient of variation {cv}): mix short and long sentences")
    dashes = len(re.findall(r"—|(?<=\s)–(?=\s)", text))
    rate = _per_1000(dashes, words)
    applies = lang in EM_DASH_LANGUAGES
    metrics["em_dashes"] = _metric({"per_1000_words": rate}, EM_DASH_PER_1000 if applies else None,
                                   "" if applies else f"not judged for '{lang}', where the dash is ordinary punctuation")
    if applies and rate >= EM_DASH_PER_1000:
        add("ai-text-em-dash-density", "low", f"[heuristic] {dashes} em dashes ({rate} per 1,000 words): a weak sign of "
            "model style, weaker in newer models; use commas, colons or full stops where they read better")
    items = [b for b in content.blocks if b.kind == "li"]
    labelled = [b for b in items if (m := re.match(r"^\s*([^:.!?]{1,40}):\s+\S", b.text)) and len(m.group(1).split()) <= 5]
    share = round(len(labelled) / len(items), 2) if items else 0.0
    metrics["label_lists"] = _metric({"list_items": len(items), "label_colon_items": len(labelled), "share": share,
                                      "colons_per_1000_words": _per_1000(text.count(":"), words)}, LABEL_LIST_SHARE)
    if len(labelled) >= MIN_LABEL_ITEMS and share >= LABEL_LIST_SHARE:
        add("ai-text-label-lists", "low", f"[heuristic] {len(labelled)} of {len(items)} list items are 'Label: explanation' "
            "(a model habit); turn some into prose or plain bullets", " | ".join(b.text[:60] for b in labelled[:EXAMPLES]))

    # --- claims and answers
    unsupported = []
    for i, b in enumerate(prose):
        next_links = prose[i + 1].links if i + 1 < len(prose) else []
        if b.links or next_links or CITATION_MARKERS.search(b.text):
            continue
        unsupported += [s for s in sentences_of(b.text) if any(p.search(s) for p in STATISTIC_CLAIMS)]
    metrics["unsupported_statistics"] = _metric(len(unsupported))
    if unsupported:
        add("ai-text-unsupported-stat", "medium",
            f"[heuristic] {len(unsupported)} sentence(s) state a statistic or 'studies show' with no link or citation nearby: "
            "fact-check each and cite the source, or cut it (models invent figures)", " | ".join(s[:120] for s in unsupported[:EXAMPLES]))
    filler = _phrase_regex(FILLER_ANSWERS)
    weak = []
    for i, b in enumerate(content.blocks):
        if b.kind not in ("h2", "h3", "h4") or not QUESTION_HEADING.search(b.text):
            continue
        answer = next((n for n in content.blocks[i + 1:i + 2] if not re.fullmatch(r"h[1-6]", n.kind)), None)
        first = sentences_of(answer.text)[0] if answer and sentences_of(answer.text) else ""
        if first and filler.match(first.strip()):
            weak.append(f"{b.text} -> {first[:80]}")
    metrics["filler_answers"] = _metric(len(weak))
    if weak:
        add("ai-text-filler-answer", "low", f"[heuristic] {len(weak)} question heading(s) open with filler instead of the "
            "answer (answer in the first sentence: that is what snippets and AI answers quote)", " | ".join(weak[:EXAMPLES]))
    return metrics, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="page URL, or - to read stdin")
    ap.add_argument("--file", help="local HTML or Markdown file")
    ap.add_argument("--lang", help="language code to use instead of the detected one")
    args = ap.parse_args()
    if bool(args.url) == bool(args.file):
        ap.error("give a URL, - for stdin, or --file")
    where: dict = {}
    if args.file:
        where["file"] = args.file
        if is_markdown_path(args.file):
            with open(args.file, encoding="utf-8") as fh:
                source = fh.read()
            page, is_html = markdown_to_html(source), False
        else:
            source = page = load_local(args.file).text
            is_html = True
        base = "https://localhost/"
    elif args.url == "-":
        where["file"] = "<stdin>"
        source = sys.stdin.read()
        is_html = source.lstrip().startswith("<")
        page, base = (source if is_html else markdown_to_html(source)), "https://localhost/"
    else:
        result = fetch(args.url)
        if result.error or result.status >= 400:
            print_json({"url": args.url, "status": result.status, "error": result.error or f"HTTP {result.status}: not checking an error page"})
            return 2
        where["url"], source, page, is_html, base = result.final_url, result.text, result.text, True, result.final_url
    content = main_content(page, base)
    detected = detect_language(content.prose)
    lang = primary_subtag(args.lang or detected.lang or "")  # ka-GE uses the ka lists
    metrics, findings = analyse(content, source, is_html, lang)
    print_json({**where, "language": lang or None, "language_source": "--lang" if args.lang else "detected",
                "words": metrics["words"],
                "note": "Every item is a heuristic, not a verdict. No AI-written probability is given: such scores are "
                        "unreliable, and Google judges quality, not how text was produced.",
                "metrics": metrics, "findings": sort_findings(findings)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
