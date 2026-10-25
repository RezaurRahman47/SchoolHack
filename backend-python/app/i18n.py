"""Language of the current request: German by default, English on request.

The pages are translated in the browser (static/i18n.js + static/i18n/en.js),
so templates, questions and stored data stay German and grading is unchanged.
The server only needs the language for text it writes itself: what the model
is asked to write, and a few messages that join model text with fixed text.

The choice lives in a cookie (not the session), so it survives log-in and
log-out.
"""
from __future__ import annotations

from contextvars import ContextVar

LANGS = ("de", "en")
COOKIE = "lang"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365

_current: ContextVar[str] = ContextVar("lang", default="de")

# Appended to the system prompt when the student uses the app in English.
# The prompts themselves stay German; this one line changes the output.
EN_NOTE = ("\n\nWICHTIG / IMPORTANT: The user has switched School Hack to English. "
           "Write every text meant for the student or teacher in English, also inside JSON "
           "fields (question, options, answer, explanation, hint). Keep chemical formulas as they are.")


def from_cookie(value: str | None) -> str:
    return value if value in LANGS else "de"


def set_current(lang: str) -> None:
    _current.set(from_cookie(lang))


def current() -> str:
    return _current.get()


def pick(de: str, en: str) -> str:
    """The German or English version of a text, for the current request."""
    return en if _current.get() == "en" else de
