"""Claude API wrapper. Works without a key (falls back to built-in explanations)."""
from __future__ import annotations

import os

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

_client = None


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _get():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def ask(system: str, prompt: str, max_tokens: int = 600) -> str | None:
    if not available():
        return None
    try:
        msg = _get().messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                     messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception as e:  # network/key problems must never break the lesson
        print("Claude API error:", e)
        return None


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
