"""Chemie RAG vectorstore client.

Connects to the Fokus Chemie ChromaDB via the running FastAPI server at
http://localhost:8080/api/ (Option B — REST API from the chemie-vectorstore skill).

Falls back gracefully if the server is unreachable — every call returns an empty
result rather than raising, so SchoolHack keeps working without the RAG server.

⚠️ The vectorstore uses clip-ViT-B-32 (512-dim) embeddings. Never bypass the
   REST API and use a different model or queries will return garbage.
"""
from __future__ import annotations

import logging
import os
from typing import Literal

import urllib.request
import urllib.error
import json

log = logging.getLogger(__name__)

# Demo: local Mac. Later: point this at the VPS, e.g.
#   RAG_BASE=https://rag.example.com/api
RAG_BASE = os.getenv("RAG_BASE", "http://localhost:8080/api").rstrip("/")
RAG_ORIGIN = RAG_BASE[:-4] if RAG_BASE.endswith("/api") else RAG_BASE
TIMEOUT = 20  # first v2 query loads the embedding + reranker models
GENERATE_TIMEOUT = 180  # LLM generators (quiz / flashcards / statements) are slow


def _post(path: str, payload: dict, timeout: int = TIMEOUT) -> dict | None:
    """POST to the RAG server; return parsed JSON or None on any error."""
    url = f"{RAG_BASE}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as exc:
        log.debug("RAG server unreachable: %s", exc)
        return None
    except Exception as exc:
        log.warning("RAG request failed: %s", exc)
        return None


def _get(path: str) -> dict | None:
    """GET from the RAG server; return parsed JSON or None on any error."""
    url = f"{RAG_BASE}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        log.debug("RAG GET failed: %s", exc)
        return None


def proxy_image_url(url: str) -> str:
    """Map a RAG image URL/filename to the SchoolHack image proxy path."""
    if not url:
        return ""
    filename = url.split("?")[0].rstrip("/").split("/")[-1]
    return f"/api/rag-image/{filename}" if filename else ""


def fetch_image(filename: str) -> tuple[bytes, str] | None:
    """Download a textbook image from the RAG server (bytes, content-type)."""
    name = filename.rsplit("/", 1)[-1]
    if not name:
        return None
    url = f"{RAG_BASE}/images/{name}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            return resp.read(), resp.headers.get("Content-Type", "image/jpeg")
    except Exception as exc:
        log.debug("RAG image fetch failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Return True if the RAG server is reachable."""
    result = _get("/status")
    return result is not None


def search_text(query: str, n_results: int = 5) -> list[dict]:
    """Search for text chunks relevant to *query*.

    Returns a list of dicts:
      {text, metadata: {page, chapter, chunk_type, source}, relevance, distance}
    """
    result = _post("/search", {"query": query, "n_results": n_results, "filter_type": "text"})
    if result is None:
        return []
    return result.get("results", [])


def search_images(query: str, n_results: int = 3) -> list[dict]:
    """Search for image chunks relevant to *query*.

    Returns a list of dicts:
      {text, metadata: {page, image_path, caption, width, height}, relevance, distance}
    """
    result = _post("/search", {"query": query, "n_results": n_results, "filter_type": "image"})
    if result is None:
        return []
    return result.get("results", [])


def rag_context_for_skill(skill_name: str, n_text: int = 4, n_images: int = 2) -> dict:
    """Fetch the most relevant RAG context for a chemistry skill name.

    Returns::

        {
          "available": bool,
          "text_chunks": [...],   # list of {text, metadata, relevance}
          "images": [...],        # list of {url, caption, page, relevance}
          "query": str,
        }
    """
    if not is_available():
        return {"available": False, "text_chunks": [], "images": [], "query": skill_name}

    text_chunks = search_text(skill_name, n_text)
    raw_images = search_images(skill_name, n_images)

    # Convert image_path → a URL that the SchoolHack server can proxy
    images = []
    for img in raw_images:
        meta = img.get("metadata", {})
        path = meta.get("image_path", "")
        filename = path.split("/")[-1] if path else ""
        images.append({
            "url": proxy_image_url(filename),
            "caption": meta.get("caption", ""),
            "page": meta.get("page", ""),
            "relevance": round(img.get("relevance", 0), 2),
        })

    return {
        "available": True,
        "text_chunks": text_chunks,
        "images": images,
        "query": skill_name,
    }


def rag_chat(question: str, topic: str = "", core_principle: str = "") -> dict | None:
    """Ask the RAG chat endpoint. Returns the full response dict or None."""
    payload = {"question": question}
    if topic:
        payload["topic"] = topic
    if core_principle:
        payload["core_principle"] = core_principle
    result = _post("/chat", payload)
    # The RAG server returns image URLs pointing at :8080; rewrite them through
    # this server so phones on the LAN can load them too.
    if result:
        for img in result.get("images", []) or []:
            img["url"] = proxy_image_url(img.get("url") or img.get("filename") or "")
    return result


# ---------------------------------------------------------------------------
# Generated study material (quiz, flashcards, statements, topic overview)
# ---------------------------------------------------------------------------

def _generate(path: str, payload: dict, empty_key: str, fallback: str) -> dict:
    """Call a RAG generator endpoint and always return a usable dict."""
    result = _post(path, payload, timeout=GENERATE_TIMEOUT)
    if result is None:
        return {"error": "RAG-Server nicht erreichbar. Bitte später erneut versuchen.", empty_key: []}
    if result.get("error"):
        return result
    if not result.get(empty_key):
        return {"error": fallback, empty_key: []}
    return result


def rag_quiz(topic: str, num_questions: int = 5) -> dict:
    """Generate an MCQ quiz from the textbook."""
    return _generate("/quiz", {"topic": topic, "num_questions": num_questions},
                     "questions", "Konnte kein Quiz erstellen.")


def rag_flashcards(topic: str, num_cards: int = 8) -> dict:
    """Generate flashcards from the textbook."""
    return _generate("/flashcards", {"topic": topic, "num_cards": num_cards},
                     "cards", "Konnte keine Lernkarten erstellen.")


def rag_statements(topic: str, num_statements: int = 6) -> dict:
    """Generate true/false statements from the textbook."""
    return _generate("/statements", {"topic": topic, "num_statements": num_statements},
                     "statements", "Konnte keine Aussagen erstellen.")


def rag_explore(topic: str) -> dict:
    """Generate a short RAG-grounded overview of a topic."""
    result = _post("/explore", {"topic": topic}, timeout=GENERATE_TIMEOUT)
    if result is None:
        return {"error": "RAG-Server nicht erreichbar. Bitte später erneut versuchen.", "summary": ""}
    return result
