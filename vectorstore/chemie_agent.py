"""
Chemie RAG — Interactive Agent
Uses OpenRouter (e.g. z-ai/glm-5.3-flash) or Anthropic with RAG context
to generate questions, flashcards, true/false statements, and chat with the textbook.
"""

import os
import json
import re
import random
from typing import Optional
from pathlib import Path

from vector_engine import VectorStoreEngine

# Load .env file automatically
def load_dotenv():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_dotenv()


class ChemieAgent:
    """
    Interactive chemistry learning agent powered by RAG + LLM (z-ai/glm-5.3-flash).
    Generates questions, flashcards, statements, and answers queries.
    """

    SYSTEM_PROMPT = """Du bist ein erfahrener Chemie-Lehrer für Schüler der 9. und 10. Klasse (Sekundarstufe I).
Du arbeitest mit dem Schulbuch "Fokus Chemie" (Berlin/Brandenburg).

WICHTIGE REGELN:
- Antworte IMMER auf Deutsch.
- Benutze nur Informationen aus dem bereitgestellten Kontext (RAG).
- Wenn du die Antwort nicht im Kontext findest, sage das ehrlich.
- Erkläre Konzepte altersgerecht und verständlich.
- Benutze korrekte chemische Fachbegriffe und Formeln.
- Verwende chemische Formeln korrekt (z.B. H₂O, CO₂, NaCl).
"""

    def __init__(self, vector_store: VectorStoreEngine, api_key: Optional[str] = None):
        self.vector_store = vector_store
        self.openrouter_api_key = (
            api_key
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = os.environ.get("MODEL_NAME", "z-ai/glm-5.3-flash")
        print(f"✓ ChemieAgent initialized with model: {self.model}")

    def _get_context(self, query: str, n_results: int = 6) -> str:
        """Retrieve relevant context from the vector store (text only)."""
        results = self.vector_store.search(query, n_results=n_results, filter_type="text")

        if not results:
            return "Kein relevanter Kontext gefunden."

        context_parts = []
        for i, r in enumerate(results):
            meta = r.get("metadata", {})
            page = meta.get("page", "?")
            chapter = meta.get("chapter", "")
            chunk_type = meta.get("chunk_type", "text")
            relevance = r.get("relevance", 0)

            header = f"[Quelle {i+1} | Seite {page}"
            if chapter:
                header += f" | {chapter}"
            header += f" | Typ: {chunk_type} | Relevanz: {relevance:.2f}]"

            context_parts.append(f"{header}\n{r['text']}")

        return "\n\n---\n\n".join(context_parts)

    def _get_relevant_images(self, query: str, n_results: int = 3) -> list[dict]:
        """Retrieve relevant images from the vector store for a query."""
        results = self.vector_store.search(query, n_results=n_results, filter_type="image")
        images = []
        for r in results:
            meta = r.get("metadata", {})
            image_path = meta.get("image_path", "")
            if not image_path:
                continue
            filename = Path(image_path).name
            images.append({
                "url": f"/api/images/{filename}",
                "caption": meta.get("caption", ""),
                "page": meta.get("page", "?"),
                "relevance": r.get("relevance", 0),
            })
        return images

    def _call_llm(self, system: str, user_message: str, max_tokens: int = 2000) -> str:
        """Call OpenRouter or Anthropic API."""
        if not self.openrouter_api_key:
            raise ValueError("No API key configured in .env or environment")

        import requests

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Chemie RAG Fokus Chemie",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_claude(self, system: str, user_message: str, max_tokens: int = 2000) -> str:
        """Backward-compatible alias for _call_llm."""
        return self._call_llm(system, user_message, max_tokens)

    # ─── Chat with Textbook ───────────────────────────────

    def chat(self, question: str) -> dict:
        """Answer a student's question using RAG context, including relevant images."""
        context = self._get_context(question)
        images = self._get_relevant_images(question, n_results=3)

        user_message = f"""Ein Schüler fragt: "{question}"

Beantworte die Frage basierend auf folgendem Kontext aus dem Schulbuch:

{context}

Antworte ausführlich, aber verständlich. Benutze Beispiele und chemische Formeln wenn hilfreich.
Gib am Ende an, auf welcher Seite im Buch man mehr dazu finden kann."""

        answer = self._call_llm(self.SYSTEM_PROMPT, user_message)

        return {
            "question": question,
            "answer": answer,
            "sources": self._extract_sources(context),
            "images": images,
        }

    # ─── Quiz Generator ───────────────────────────────────

    def generate_quiz(self, topic: Optional[str] = None, num_questions: int = 5) -> dict:
        """Generate a multiple-choice quiz on a topic."""
        query = topic or "wichtige Konzepte der Chemie"
        context = self._get_context(query, n_results=8)

        user_message = f"""Erstelle ein Quiz mit genau {num_questions} Multiple-Choice-Fragen basierend auf diesem Schulbuch-Kontext:

{context}

{"Thema: " + topic if topic else "Wähle verschiedene Themen aus dem Kontext."}

Gib das Quiz als JSON zurück mit folgendem Format:
{{
  "title": "Quiz-Titel",
  "topic": "Thema",
  "questions": [
    {{
      "id": 1,
      "question": "Frage-Text",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "B",
      "explanation": "Erklärung warum B richtig ist",
      "page_reference": 42
    }}
  ]
}}

WICHTIG: Gib NUR das JSON zurück, kein weiterer Text davor oder danach."""

        response = self._call_llm(self.SYSTEM_PROMPT, user_message, max_tokens=3000)

        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                quiz = json.loads(json_match.group())
                return quiz
        except json.JSONDecodeError:
            pass

        return {
            "title": f"Quiz: {topic or 'Chemie'}",
            "topic": topic or "Allgemein",
            "questions": [],
            "error": "Konnte Quiz nicht generieren. Bitte erneut versuchen.",
            "raw_response": response,
        }

    # ─── Flashcard Generator ──────────────────────────────

    def generate_flashcards(self, topic: Optional[str] = None, num_cards: int = 8) -> dict:
        """Generate study flashcards from the textbook content."""
        query = topic or "wichtige Definitionen und Konzepte"
        context = self._get_context(query, n_results=8)

        user_message = f"""Erstelle genau {num_cards} Lernkarten (Flashcards) basierend auf diesem Schulbuch-Kontext:

{context}

{"Thema: " + topic if topic else "Wähle die wichtigsten Konzepte aus dem Kontext."}

Gib die Karten als JSON zurück:
{{
  "topic": "Thema",
  "cards": [
    {{
      "id": 1,
      "front": "Frage / Begriff",
      "back": "Antwort / Definition / Erklärung",
      "difficulty": "leicht|mittel|schwer",
      "tags": ["tag1", "tag2"],
      "page_reference": 42
    }}
  ]
}}

WICHTIG: Gib NUR das JSON zurück, kein weiterer Text davor oder danach."""

        response = self._call_llm(self.SYSTEM_PROMPT, user_message, max_tokens=3000)

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                cards = json.loads(json_match.group())
                return cards
        except json.JSONDecodeError:
            pass

        return {
            "topic": topic or "Allgemein",
            "cards": [],
            "error": "Konnte Lernkarten nicht generieren.",
            "raw_response": response,
        }

    # ─── True/False Statement Generator ───────────────────

    def generate_statements(self, topic: Optional[str] = None, num_statements: int = 6) -> dict:
        """Generate true/false statements for comprehension testing."""
        query = topic or "chemische Konzepte und Fakten"
        context = self._get_context(query, n_results=8)

        user_message = f"""Erstelle genau {num_statements} Aussagen (Richtig/Falsch) basierend auf diesem Schulbuch-Kontext:

{context}

{"Thema: " + topic if topic else "Wähle verschiedene Themen."}

Mische richtige und falsche Aussagen (ca. 50/50). Die falschen Aussagen sollten typische Schüler-Fehler widerspiegeln.

Gib die Aussagen als JSON zurück:
{{
  "topic": "Thema",
  "statements": [
    {{
      "id": 1,
      "statement": "Aussage-Text",
      "is_true": true,
      "explanation": "Erklärung warum richtig/falsch",
      "correction": "Korrektur wenn falsch (leer wenn richtig)",
      "page_reference": 42
    }}
  ]
}}

WICHTIG: Gib NUR das JSON zurück, kein weiterer Text davor oder danach."""

        response = self._call_llm(self.SYSTEM_PROMPT, user_message, max_tokens=3000)

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                statements = json.loads(json_match.group())
                return statements
        except json.JSONDecodeError:
            pass

        return {
            "topic": topic or "Allgemein",
            "statements": [],
            "error": "Konnte Aussagen nicht generieren.",
            "raw_response": response,
        }

    # ─── Topic Explorer ───────────────────────────────────

    def explore_topic(self, topic: str) -> dict:
        """Get a comprehensive overview of a topic from the textbook."""
        context = self._get_context(topic, n_results=10)

        user_message = f"""Erstelle eine umfassende Zusammenfassung zum Thema "{topic}" basierend auf dem Schulbuch-Kontext:

{context}

Strukturiere die Antwort so:
1. **Überblick**: Kurze Einführung
2. **Wichtige Konzepte**: Die Kernideen erklärt
3. **Chemische Formeln/Reaktionen**: Falls relevant
4. **Beispiele**: Alltagsbeispiele
5. **Merke**: Die wichtigsten Punkte zum Merken

Formatiere die Antwort mit Markdown."""

        answer = self._call_llm(self.SYSTEM_PROMPT, user_message, max_tokens=3000)

        return {
            "topic": topic,
            "summary": answer,
            "sources": self._extract_sources(context),
        }

    # ─── Helpers ──────────────────────────────────────────

    def _extract_sources(self, context: str) -> list[dict]:
        """Extract source references from context string."""
        sources = []
        for match in re.finditer(r'\[Quelle (\d+) \| Seite (\d+)(?:\s*\|\s*([^|]*))?', context):
            sources.append({
                "source_num": int(match.group(1)),
                "page": int(match.group(2)),
                "chapter": match.group(3).strip() if match.group(3) else "",
            })
        return sources

    def get_available_topics(self) -> list[str]:
        """Get a list of topics/chapters available in the vector store."""
        collection = self.vector_store.get_or_create_collection()
        try:
            all_items = collection.get(include=["metadatas"])
            chapters = set()
            for meta in all_items["metadatas"]:
                chapter = meta.get("chapter", "")
                if chapter:
                    chapters.add(chapter)
            return sorted(list(chapters))
        except Exception:
            return []
