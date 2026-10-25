"""Text helpers for the chemistry chat.

The tutor should always answer in plain German, directly and compactly.  These
helpers are intentionally dependency-free and are also mirrored in
``vectorstore/rag_v2/agent.py`` so both services enforce the same limits.
"""
from __future__ import annotations

import re

MAX_SENTENCES = 3
MAX_WORDS = 60

_ABBREVIATIONS = (
    "z. B.", "z.B.", "d. h.", "d.h.", "bzw.", "ca.", "v. a.", "v.a.",
    "Abb.", "Nr.", "S.", "Dr.", "Prof.", "usw.", "max.", "min.",
    "evtl.", "ggf.", "inkl.", "lt.", "u. a.", "u.a.",
)

# Only strip real preambles, never the start of a factual sentence such as
# "Klar ist, dass ..." or "Sicher ist, dass ...".
_PREAMBLE = re.compile(
    r"^(?:"
    r"(?:gerne|natürlich|klar|selbstverständlich|sicher|also|nun|zunächst|okay|ok)\s*[!,.:;]\s*"
    r"|(?:gute frage|das ist eine (?:sehr )?gute frage)\s*[!,.:;]?\s*"
    r"|hier ist (?:die|eine) (?:kurze )?antwort\s*[:!.,;]?\s*"
    r"|kurz gesagt\s*[,:;!]\s*"
    r"|(?:a|antwort|die antwort(?: ist)?|lösung|buchkontext|kontext|merksatz)\s*[:!.,;]\s*"
    # English (the app can be switched to English)
    r"|(?:sure|of course|certainly|great question|good question)\s*[!,.:;]\s*"
    r"|here(?:'s| is) (?:the|a) (?:short )?answer\s*[:!.,;]?\s*"
    r"|(?:answer|the answer is|solution)\s*[:!.,;]\s*"
    r")+",
    re.IGNORECASE,
)

# A book refusal means "the retrieval had nothing useful".  Only these are
# retried with general chemistry knowledge.  Safety refusals must be preserved!
_BOOK_REFUSAL_MARKERS = (
    "das steht in diesem buchabschnitt nicht",
    "das steht nicht in diesem buch",
    "dazu finde ich im buch nichts",
    "keine passenden informationen",
    "keine informationen im buch",
    "im buch steht dazu nichts",
    "das buch sagt dazu nichts",
    "frag mich gern zu einem chemie-thema aus dem buch",
    "der chemie-tutor ist gerade nicht erreichbar",
    "the chemistry tutor can't be reached",
)

# Generic "I cannot help with this" answers.  These may be safety refusals
# (self-harm, violence, cheating) and therefore must not be retried or replaced
# by a "tutor unavailable" message.  They are only used to suppress textbook
# sources/images, because a refusal is not grounded in the book.
_SOFT_REFUSAL_MARKERS = (
    "dazu finde ich nichts",
    "dazu finde ich keine information",
    "dazu habe ich keine information",
    "dazu habe ich leider keine information",
    "dazu habe ich nichts",
    "dazu gibt es keine information",
    "dazu liegt mir keine information",
    "keine informationen dazu",
    "ich kann diese frage gerade nicht beantworten",
    "ich kann diese frage nicht beantworten",
    "ich kann das nicht beantworten",
    "ich kann dir das nicht beantworten",
    "ich kann dir dabei nicht helfen",
    "es tut mir leid, aber",
    "i can't answer",
    "i cannot answer",
    "i can't help with",
    "i cannot help with",
    "i'm sorry, but",
    "i don't have information",
)

# Word-boundary check: substring matching would also hit "als kinetische
# Energie" or "als Kind".
_SOFT_REFUSAL_REGEX = re.compile(r"\bals\s+ki\b")


def is_refusal(text: str) -> bool:
    """True only for a book/service refusal that should be retried."""
    low = re.sub(r"\s+", " ", str(text or "").lower())
    return any(marker in low for marker in _BOOK_REFUSAL_MARKERS)


def is_soft_refusal(text: str) -> bool:
    """True for a safety/generic refusal that must be returned unchanged."""
    low = re.sub(r"\s+", " ", str(text or "").lower())
    return (any(marker in low for marker in _SOFT_REFUSAL_MARKERS)
            or bool(_SOFT_REFUSAL_REGEX.search(low)))


def clean_topic(value: object, fallback: str = "Chemie", max_len: int = 120) -> str:
    """Make a client-supplied topic safe and compact for the LLM prompt."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_len] or fallback


def _plain_text(value: object) -> str:
    text = str(value or "")
    if not text:
        return ""

    # Markdown / HTML noise.
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[\d+\]\s*", "", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*•–]|\d+[.)])\s+", "", text, flags=re.M)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text, flags=re.S)
    text = re.sub(r"__(.*?)__", r"\1", text, flags=re.S)
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", text)
    text = text.replace("|", " ")

    return re.sub(r"\s+", " ", text).strip(" \t\r\n-–—")


def _cap_sentences(text: str, max_sentences: int) -> str:
    # Protect abbreviations and ellipses so they are not treated as sentence
    # ends while splitting.
    protected = text.replace("...", "\u2026")
    for abbreviation in _ABBREVIATIONS:
        protected = protected.replace(abbreviation, abbreviation.replace(".", "\u2024"))
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\u2024", protected)

    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", protected) if part.strip()]
    return " ".join(parts[:max_sentences])


def _cap_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text

    cut = " ".join(words[:max_words])
    last_end = max((m.start() for m in re.finditer(r"[.!?](?=\s|$)", cut)), default=-1)
    if last_end >= len(cut) // 2:
        return cut[: last_end + 1]

    # Keep the hard cap exact: the ellipsis itself counts as the final word.
    cut = " ".join(words[: max(max_words - 1, 1)]).rstrip(" ,;:-–—")
    if not cut.endswith((".", "!", "?", "\u2026")):
        cut += " …"
    return cut


def clean_answer(text: str, max_sentences: int = MAX_SENTENCES, max_words: int = MAX_WORDS) -> str:
    """Normalise an LLM answer to plain, direct prose within the chat limits."""
    cleaned = _plain_text(text)
    if not cleaned:
        return ""

    cleaned = _PREAMBLE.sub("", cleaned).strip()
    if not cleaned:
        return ""

    cleaned = _cap_sentences(cleaned, max_sentences)
    cleaned = _cap_words(cleaned, max_words)
    cleaned = cleaned.replace("\u2024", ".").replace("\u2026", "…")

    if cleaned and cleaned[-1] not in ".!?…":
        cleaned += "."
    return cleaned
