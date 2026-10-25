"""LLM extras (Socratic hints, teacher summary) — OpenRouter, same key as chat.

Everything the app sends to a model goes through ``OPENROUTER_API_KEY``:
the KI-Tutor chat, the hints, and the teacher summary. Without a key every
function falls back to the built-in text, so the lesson never breaks.

There is deliberately no second provider here: one key, no conflicting keys.
"""
from __future__ import annotations

from . import chat_llm


def available() -> bool:
    """True when a usable OpenRouter key is configured."""
    return chat_llm.available()


def ask(system: str, prompt: str, max_tokens: int = 600) -> str | None:
    """Ask the model; ``None`` when there is no key or the call failed."""
    return chat_llm.ask(system, prompt, max_tokens)


TUTOR_SYSTEM = (
    "Du bist ein geduldiger Chemie-Tutor für Schüler der 9. Klasse in Berlin (Rahmenlehrplan Berlin-Brandenburg). "
    "Antworte auf Deutsch, kurz (max. 4 Sätze), sokratisch: stelle eine Leitfrage und gib einen Tipp. "
    "Verrate die richtige Antwort NICHT beim ersten Versuch. Die korrekte Lösung wird dir mitgeteilt, "
    "sie ist verlässlich (vom Code berechnet) – widersprich ihr nie."
)


def tutor_hint(question: dict, given: str | None, attempt: int, error: str | None) -> str:
    fallback = error or "Lies die Aufgabe noch einmal genau. Welche Formel oder Regel passt hier?"
    if attempt >= 2:
        fallback = f"Lösungsweg: {question.get('explanation', '')}"
    prompt = (f"Aufgabe: {question['prompt']}\nKorrekte Lösung (nicht verraten, außer Versuch ≥ 2): "
              f"{question['answer']} {question.get('unit', '')}\nErklärung: {question.get('explanation', '')}\n"
              f"Antwort des Schülers: {given or '(noch keine)'}\nErkannter Fehlertyp: {error or 'unbekannt'}\n"
              f"Versuch Nr.: {attempt}")
    return ask(TUTOR_SYSTEM, prompt, 300) or fallback
