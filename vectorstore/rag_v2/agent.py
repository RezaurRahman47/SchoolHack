"""Short, grounded chemistry tutor on top of the v2 index."""
from __future__ import annotations

import copy
import json
import os
import re
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .store import RAGStore, get_store

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Gemma 4 is a no-reasoning model and measured ~2x faster than GLM here.
PRIMARY = os.environ.get("CHAT_MODEL", "google/gemma-4-31b-it")
FALLBACKS = ["mistralai/mistral-small-3.2-24b-instruct", "z-ai/glm-5.3-flash"]
CACHE_SIZE = int(os.environ.get("RAG_CHAT_CACHE", "256"))
# On a cheap CPU VPS set RAG_IMAGE_VLM_CHECK=0 to skip the extra vision call.
IMAGE_VLM_CHECK = os.environ.get("RAG_IMAGE_VLM_CHECK", "1") != "0"

# Reuse TLS connections to OpenRouter (saves 100–300 ms per call).
SESSION = requests.Session()

SYSTEM = (
    "Du bist ein Chemie-Tutor für Klasse 9/10 in Berlin. Antworte auf Deutsch.\n"
    "Regeln:\n"
    "- Maximal 3 kurze Sätze, insgesamt höchstens 60 Wörter.\n"
    "- Beginne direkt mit der Antwort. Keine Begrüßung, keine Einleitung, keine Wiederholung "
    "der Frage, keine Überschriften, keine Aufzählung, kein Markdown.\n"
    "- Nutze nur den bereitgestellten Buchkontext. Ergänze kein Allgemeinwissen.\n"
    "- Wenn der Kontext die Frage nicht beantwortet: \"Das steht in diesem Buchabschnitt nicht.\" "
    "und stelle eine kurze Rückfrage.\n"
    "- Nenne chemische Formeln korrekt (H₂O, CO₂, NaCl, H⁺, OH⁻).\n"
    "- Keine Seitenzahl, außer der Schüler fragt danach."
)

GEN_SYSTEM = (
    "Du bist ein erfahrener Chemie-Lehrer für Klasse 9/10 (Berlin/Brandenburg). "
    "Arbeite ausschließlich mit dem bereitgestellten Schulbuch-Kontext. "
    "Antworte auf Deutsch und gib, wenn verlangt, ausschließlich gültiges JSON zurück."
)


def _key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    for env in (Path(".env"), Path(__file__).resolve().parent.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENROUTER_API_KEY missing")


def _post(model: str, system: str, user: str, max_tokens: int = 500) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if model.startswith("z-ai/glm"):
        payload["reasoning"] = {"effort": "low"}
    r = SESSION.post(OPENROUTER_URL, headers={
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8080",
        "X-Title": "Fokus Chemie RAG v2",
    }, json=payload, timeout=60)
    r.raise_for_status()
    return (r.json()["choices"][0]["message"].get("content") or "").strip()


def _call(system: str, user: str, max_tokens: int = 500) -> str:
    last = ""
    for model in [PRIMARY] + FALLBACKS:
        try:
            text = _post(model, system, user, max_tokens)
            if text:
                return text
        except Exception as exc:
            last = str(exc)
    raise RuntimeError(last or "LLM unavailable")


def _clean_answer(text: str) -> str:
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"^(Das ist eine (sehr )?gute Frage[.!]?\s*|Gerne[.!]?\s*)", "", text,
                  flags=re.I)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    # Protect German abbreviations so "z. B." is not treated as a sentence end.
    abbrevs = ["z. B.", "z.B.", "d. h.", "d.h.", "bzw.", "ca.", "v. a.", "v.a.",
               "Abb.", "Nr.", "S.", "Dr.", "Prof.", "usw.", "max.", "min."]
    for a in abbrevs:
        text = text.replace(a, a.replace(".", "\u2024"))
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 3:
        text = " ".join(sentences[:3]).strip()
    return text.replace("\u2024", ".")


_IMG_CACHE: dict[tuple[str, str], bool] = {}


def _image_is_relevant(question: str, image_path: str, caption: str) -> bool:
    """Final cross-modal gate: does this figure really address the question?"""
    key = (question.strip().lower(), image_path)
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]
    try:
        from .caption import DEFAULT_MODEL, OPENROUTER_URL, _data_url, _key
        prompt = (
            f"Frage: {question}\nBildtext: {caption}\n\n"
            "Beantwortet oder illustriert dieses Bild genau den in der Frage genannten Aspekt? "
            "Antworte JA nur, wenn dieser Aspekt (z. B. Siedepunkt, Löslichkeit, pH-Wert, Kalkseife, "
            "Neutralisation) im Bild zu sehen ist. Antworte NEIN, wenn es nur dasselbe Stoffgebiet ist. "
            "Nur JA oder NEIN."
        )
        r = requests.post(OPENROUTER_URL, headers={
            "Authorization": f"Bearer {_key()}", "Content-Type": "application/json",
        }, json={
            "model": DEFAULT_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": _data_url(image_path)}},
            ]}],
            "temperature": 0, "max_tokens": 5,
        }, timeout=60)
        r.raise_for_status()
        txt = (r.json()["choices"][0]["message"].get("content") or "").strip().upper()
        ok = txt.startswith("JA")
    except Exception:
        ok = False
    if len(_IMG_CACHE) > 500:
        _IMG_CACHE.clear()
    _IMG_CACHE[key] = ok
    return ok


def _parse_json(text: str) -> dict | None:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


class ChemieAgentV2:
    def __init__(self, store: RAGStore | None = None):
        self.store = store or get_store()
        self._cache: OrderedDict[tuple[str, str, str], dict] = OrderedDict()

    # ------------------------------------------------------------------ chat
    def chat(self, question: str, topic: str = "", core_principle: str = "") -> dict:
        key = (question.strip().lower(), topic.strip(), core_principle.strip())
        if key in self._cache:
            self._cache.move_to_end(key)
            return copy.deepcopy(self._cache[key])
        result = self._chat_uncached(question, topic, core_principle)
        self._cache[key] = copy.deepcopy(result)
        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return result

    def _chat_uncached(self, question: str, topic: str = "", core_principle: str = "") -> dict:
        hits = self.store.search_text(question, k=3)
        # Below this, the top passage is usually only loosely related. Refuse
        # instead of letting the model answer from general knowledge.
        strong = bool(hits and hits[0].score >= 0.68)

        if strong:
            context = "\n\n".join(
                f"[{i + 1}] S. {h.meta.get('page')} · {h.meta.get('section', '')}\n{h.text[:1100]}"
                for i, h in enumerate(hits)
            )
        elif core_principle:
            context = f"[Merksatz] {core_principle}"
        else:
            context = ""

        if not context:
            return {
                "question": question,
                "answer": "Das steht in diesem Buchabschnitt nicht. Frag mich gern zu einem "
                          "Chemie-Thema aus dem Buch.",
                "sources": [], "images": [], "topic": topic,
            }

        user = (f"Thema: {topic}\n" if topic else "") + \
               f"Frage: {question}\n\nBuchkontext:\n{context}"

        # Find the image candidate first (local, ~0.1 s), then run the vision
        # check in parallel with the answer model. Both are network-bound.
        images_candidate = []
        if strong:
            images_candidate = self.store.search_images(
                question, [h.meta.get("page", 0) for h in hits[:3]], hits[0].dense, k=1
            )
            if not images_candidate:
                images_candidate = self.store.search_images_any(question, k=1, min_score=0.72)

        if images_candidate:
            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(self._checked_image, question, images_candidate[0])
                answer = _clean_answer(_call(SYSTEM, user, 500))
                images = fut.result()
        else:
            answer = _clean_answer(_call(SYSTEM, user, 500))
            images = []

        sources, seen = [], set()
        for h in (hits if strong else []):
            if len(sources) >= 2:
                break
            if sources and h.score < 0.70:
                continue
            p = h.meta.get("page")
            if p in seen:
                continue
            seen.add(p)
            sources.append({
                "page": p,
                "section": h.meta.get("section", ""),
                "chapter": h.meta.get("chapter", ""),
                "relevance": round(h.score, 2),
            })

        if "steht in diesem buchabschnitt nicht" in answer.lower():
            sources, images = [], []
        return {"question": question, "answer": answer, "sources": sources,
                "images": images, "topic": topic}

    def _checked_image(self, question: str, img: dict) -> list[dict]:
        path = self.store.data_dir / "images" / img.get("filename", "")
        if not img.get("filename") or not path.exists():
            return []
        if not IMAGE_VLM_CHECK:
            return [img]
        if _image_is_relevant(question, str(path), img.get("caption", "")):
            return [img]
        return []

    # -------------------------------------------------------------- generators
    def _context(self, query: str, n: int = 8) -> str:
        hits = self.store.search_text(query, k=n)
        return "\n\n".join(
            f"[Quelle {i + 1} | Seite {h.meta.get('page')} | {h.meta.get('section', '')}]\n{h.text}"
            for i, h in enumerate(hits)
        )

    def generate_quiz(self, topic: str | None = None, num_questions: int = 5) -> dict:
        ctx = self._context(topic or "wichtige Konzepte der Chemie", 8)
        user = f"""Erstelle ein Quiz mit genau {num_questions} Multiple-Choice-Fragen zu diesem Kontext:

{ctx}

{"Thema: " + topic if topic else "Wähle verschiedene Themen aus dem Kontext."}

JSON-Format:
{{"title":"...","topic":"...","questions":[{{"id":1,"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct_answer":"B","explanation":"...","page_reference":42}}]}}
Gib NUR das JSON zurück."""
        data = _parse_json(_call(GEN_SYSTEM, user, 2500))
        return data or {"title": f"Quiz: {topic or 'Chemie'}", "topic": topic or "Allgemein",
                        "questions": [], "error": "Konnte Quiz nicht generieren."}

    def generate_flashcards(self, topic: str | None = None, num_cards: int = 8) -> dict:
        ctx = self._context(topic or "wichtige Definitionen und Konzepte", 8)
        user = f"""Erstelle genau {num_cards} Lernkarten zu diesem Kontext:

{ctx}

{"Thema: " + topic if topic else "Wähle die wichtigsten Konzepte."}

JSON:
{{"topic":"...","cards":[{{"id":1,"front":"...","back":"...","difficulty":"leicht|mittel|schwer","tags":["..."],"page_reference":42}}]}}
Gib NUR das JSON zurück."""
        data = _parse_json(_call(GEN_SYSTEM, user, 2500))
        return data or {"topic": topic or "Allgemein", "cards": [],
                        "error": "Konnte Lernkarten nicht generieren."}

    def generate_statements(self, topic: str | None = None, num_statements: int = 6) -> dict:
        ctx = self._context(topic or "chemische Konzepte und Fakten", 8)
        user = f"""Erstelle genau {num_statements} Richtig/Falsch-Aussagen zu diesem Kontext:

{ctx}

{"Thema: " + topic if topic else "Wähle verschiedene Themen."}
Mische etwa 50/50. Falsche Aussagen sollen typische Schülerfehler abbilden.

JSON:
{{"topic":"...","statements":[{{"id":1,"statement":"...","is_true":true,"explanation":"...","correction":"...","page_reference":42}}]}}
Gib NUR das JSON zurück."""
        data = _parse_json(_call(GEN_SYSTEM, user, 2500))
        return data or {"topic": topic or "Allgemein", "statements": [],
                        "error": "Konnte Aussagen nicht generieren."}

    def explore_topic(self, topic: str) -> dict:
        hits = self.store.search_text(topic, k=8)
        ctx = "\n\n".join(
            f"[S. {h.meta.get('page')} | {h.meta.get('section', '')}]\n{h.text}" for h in hits
        )
        user = f"""Fasse das Thema "{topic}" in höchstens 120 Wörtern zusammen.
Struktur: 1) Kernaussage in einem Satz, 2) zwei wichtige Fakten, 3) ein Merksatz.
Nutze nur diesen Kontext:

{ctx}"""
        answer = _call(GEN_SYSTEM + " Halte dich sehr kurz.", user, 700)
        return {
            "topic": topic,
            "summary": answer,
            "sources": [{"page": h.meta.get("page"), "section": h.meta.get("section", "")}
                        for h in hits[:4]],
        }

    def get_available_topics(self) -> list[str]:
        chapters = sorted({m.get("chapter", "") for m in self.store.metas if m.get("chapter")})
        return chapters
