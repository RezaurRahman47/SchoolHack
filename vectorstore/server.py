"""
Chemie RAG — FastAPI Server
Serves the interactive web application and the RAG API.
"""

import os
import json
import base64
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent


# ─── Load Environment Variables ───────────────────────────
def load_dotenv():
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_dotenv()

# ─── App Setup ────────────────────────────────────────────

app = FastAPI(
    title="Chemie RAG — Interaktive Lernplattform",
    description="RAG-basierte Lernapp für Fokus Chemie (9./10. Klasse)",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global instances (lazy-loaded) ──────────────────────

_vector_store = None
_agent = None


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            from vector_engine import VectorStoreEngine
            _vector_store = VectorStoreEngine(persist_dir=str(BASE_DIR / "vector_db"))
        except Exception as e:
            print(f"Vector engine not initialized: {e}")
            return None
    return _vector_store


def get_agent():
    global _agent
    if _agent is None:
        # Prefer the v2 index (EmbeddingGemma 2 + printed captions + reranker).
        if (BASE_DIR / "processed_data_v2" / "chroma").exists():
            try:
                from rag_v2.agent import ChemieAgentV2
                from rag_v2.store import RAGStore
                _agent = ChemieAgentV2(RAGStore(str(BASE_DIR / "processed_data_v2")))
                print("✓ v2 agent ready")
                return _agent
            except Exception as e:
                print(f"v2 agent not initialized: {e}")
        vs = get_vector_store()
        if vs is not None:
            try:
                from chemie_agent import ChemieAgent
                _agent = ChemieAgent(vs)
            except Exception as e:
                print(f"Chemie agent not initialized: {e}")
                return None
    return _agent


def _warmup_models() -> None:
    """Load the embedding + reranker models before the first student arrives."""
    if not (BASE_DIR / "processed_data_v2" / "chroma").exists():
        return
    try:
        from rag_v2.embed import get_model
        from rag_v2.store import get_reranker
        get_model()
        get_reranker()
        agent = get_agent()
        if agent is not None and hasattr(agent, "store"):
            agent.store.search_text("Was ist der pH-Wert?", k=1)
        print("✓ embedding + reranker warm")
    except Exception as exc:
        print(f"warmup failed: {exc}")


threading.Thread(target=_warmup_models, daemon=True).start()


# ─── Request/Response Models ─────────────────────────────

class ChatRequest(BaseModel):
    question: str
    topic: Optional[str] = ""
    core_principle: Optional[str] = ""


class WarmupRequest(BaseModel):
    questions: list[str] = []


class QuizRequest(BaseModel):
    topic: Optional[str] = None
    num_questions: int = 5


class FlashcardRequest(BaseModel):
    topic: Optional[str] = None
    num_cards: int = 8


class StatementRequest(BaseModel):
    topic: Optional[str] = None
    num_statements: int = 6


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5
    filter_type: Optional[str] = None


class TopicRequest(BaseModel):
    topic: str


# ─── API Routes ──────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """Check if the vector store is indexed and ready."""
    agent = get_agent()
    if agent is not None and hasattr(agent, "store"):
        s = agent.store
        return {"ready": True, "stats": {
            "total_chunks": len(s.ids), "text_chunks": len(s.text_idx),
            "image_chunks": len(s.cap_idx), "collection": "chemie_rag_v2",
            "mode": "v2 (EmbeddingGemma 2 + reranker)",
        }}
    vs = get_vector_store()
    if vs is not None and vs.is_indexed():
        stats = vs.get_stats()
        return {"ready": True, "stats": stats}
    return {
        "ready": False,
        "mode": "demo_and_test",
        "stats": {
            "total_chunks": "Demo-Modus aktiv (Bereit zum Testen)",
            "message": "Führe `python ingest.py` aus, um das vollständige PDF zu vektorisieren."
        }
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat with the textbook — ask questions and get RAG-grounded answers."""
    if not req.question.strip():
        raise HTTPException(400, "Frage darf nicht leer sein.")

    # 1. Preferred path: v2 agent (short grounded answer + page-gated image).
    agent = get_agent()
    if agent is not None:
        try:
            if hasattr(agent, "store"):
                result = agent.chat(req.question, req.topic or "", req.core_principle or "")
            else:
                result = agent.chat(req.question)
            result.setdefault("images", [])
            return result
        except Exception as e:
            print(f"Agent chat error: {e}")

    # 2. Legacy fallback: retrieve and quote the textbook.
    vs = get_vector_store()
    rag_results = []
    if vs is not None and vs.is_indexed():
        rag_results = vs.search(req.question, n_results=4)

    # 3. Direct RAG response from the vectorized textbook
    if rag_results:
        best = rag_results[0]
        page = best["metadata"].get("page", "?")
        chapter = best["metadata"].get("chapter", "")

        sources = [
            {
                "source_num": idx + 1,
                "page": r["metadata"].get("page", "?"),
                "chapter": r["metadata"].get("chapter", ""),
            }
            for idx, r in enumerate(rag_results)
        ]

        # Format excerpt with clean paragraphs
        clean_text = best["text"].strip()
        answer = (
            f"**Gefunden im Schulbuch \"Fokus Chemie\" (Seite {page}{' · ' + chapter if chapter else ''}):**\n\n"
            f"{clean_text}\n\n"
            f"> 💡 *Dieser Ausschnitt wurde mit semantischer Vektorsuche (Ähnlichkeit: {best['relevance']:.1%}) direkt aus deinem PDF abgerufen.*"
        )
        return {
            "question": req.question,
            "answer": answer,
            "sources": sources,
        }

    return {
        "question": req.question,
        "answer": "Keine passenden Informationen im Schulbuch gefunden.",
        "sources": [],
    }



@app.post("/api/warmup")
async def warmup(req: WarmupRequest):
    """Pre-run demo questions so the first real click is fast (cache + TLS)."""
    agent = get_agent()
    if agent is None or not hasattr(agent, "chat"):
        return {"warmed": 0}
    questions = [q.strip() for q in req.questions if q.strip()][:20]
    for q in questions:
        try:
            agent.chat(q)
        except Exception as exc:
            print(f"warmup question failed: {exc}")
    return {"warmed": len(questions)}


@app.post("/api/quiz")
async def generate_quiz(req: QuizRequest):
    """Generate a multiple-choice quiz."""
    agent = get_agent()
    if agent is not None:
        try:
            return agent.generate_quiz(topic=req.topic, num_questions=req.num_questions)
        except Exception as e:
            print(f"Agent quiz error: {e}")

    # Interactive test quiz
    topic = req.topic or "Atombau & Periodensystem"
    return {
        "title": f"Quiz: {topic}",
        "topic": topic,
        "questions": [
            {
                "id": 1,
                "question": "Welche Teilchen befinden sich im Atomkern?",
                "options": [
                    "A) Nur Elektronen",
                    "B) Protonen und Neutronen",
                    "C) Protonen und Elektronen",
                    "D) Nur Neutronen"
                ],
                "correct_answer": "B",
                "explanation": "Der Atomkern besteht aus positiv geladenen Protonen und ungeladenen Neutronen (Nukleonen). Elektronen kreisen in der Hülle.",
                "page_reference": 14
            },
            {
                "id": 2,
                "question": "Was gibt die Hauptgruppennummer im Periodensystem an?",
                "options": [
                    "A) Die Anzahl der Protonen",
                    "B) Die Anzahl der besetzten Elektronenschalen",
                    "C) Die Anzahl der Außenelektronen (Valenzelektronen)",
                    "D) Die Atommasse in Gramm"
                ],
                "correct_answer": "C",
                "explanation": "Elemente derselben Hauptgruppe haben die gleiche Anzahl an Valenzelektronen und weisen daher ähnliche chemische Eigenschaften auf.",
                "page_reference": 24
            },
            {
                "id": 3,
                "question": "Welche Edelgaskonfiguration wird bei der Ionenbindung angestrebt?",
                "options": [
                    "A) 2 Elektronen auf allen Schalen",
                    "B) 8 Valenzelektronen (Oktettregel)",
                    "C) Keine Elektronen auf der Außenschale",
                    "D) Beliebige Anzahl an Elektronen"
                ],
                "correct_answer": "B",
                "explanation": "Atome streben die energetisch günstige Edelgaskonfiguration an, meist mit 8 Außenelektronen (Oktettregel), bzw. 2 beim Helium.",
                "page_reference": 36
            },
            {
                "id": 4,
                "question": "Was passiert bei einer Oxidation dem ursprünglichen Verständnis nach?",
                "options": [
                    "A) Aufnahme von Sauerstoff",
                    "B) Abgabe von Sauerstoff",
                    "C) Aufnahme von Wasserstoff",
                    "D) Absinken der Temperatur"
                ],
                "correct_answer": "A",
                "explanation": "Im klassischen Sinne ist eine Oxidation die Vereinigung eines Stoffes mit Sauerstoff (z.B. Verbrennung von Magnesium zu Magnesiumoxid).",
                "page_reference": 48
            },
            {
                "id": 5,
                "question": "Welche chemische Formel beschreibt Kochsalz?",
                "options": [
                    "A) HCl",
                    "B) NaOH",
                    "C) NaCl",
                    "D) CO₂"
                ],
                "correct_answer": "C",
                "explanation": "Kochsalz ist Natriumchlorid (NaCl), ein Ionengitter aus Na⁺- und Cl⁻-Ionen.",
                "page_reference": 38
            }
        ][:req.num_questions]
    }


@app.post("/api/flashcards")
async def generate_flashcards(req: FlashcardRequest):
    """Generate study flashcards."""
    agent = get_agent()
    if agent is not None:
        try:
            return agent.generate_flashcards(topic=req.topic, num_cards=req.num_cards)
        except Exception as e:
            print(f"Agent flashcard error: {e}")

    topic = req.topic or "Fokus Chemie Grundlagen"
    cards = [
        {
            "id": 1,
            "front": "Was ist die Kernladungszahl (Ordnungszahl)?",
            "back": "Sie entspricht der Anzahl der Protonen im Atomkern und bestimmt das chemische Element im Periodensystem.",
            "difficulty": "leicht",
            "tags": ["Atombau", "PSE"],
            "page_reference": 15
        },
        {
            "id": 2,
            "front": "Wie lautet die Oktettregel?",
            "back": "Hauptgruppenatome gehen Bindungen ein, um eine Außenschale mit 8 Elektronen (Edelgaskonfiguration) zu erreichen.",
            "difficulty": "mittel",
            "tags": ["Bindungen", "Reaktivität"],
            "page_reference": 36
        },
        {
            "id": 3,
            "front": "Was unterscheidet ein Kation von einem Anion?",
            "back": "Kationen sind positiv geladene Ionen (Elektronen abgegeben), Anionen sind negativ geladen (Elektronen aufgenommen).",
            "difficulty": "leicht",
            "tags": ["Ionen", "Salze"],
            "page_reference": 37
        },
        {
            "id": 4,
            "front": "Was ist eine exotherme Reaktion?",
            "back": "Eine chemische Reaktion, bei der Energie (meist als Wärme oder Licht) an die Umgebung abgegeben wird (ΔH < 0).",
            "difficulty": "mittel",
            "tags": ["Thermodynamik", "Energie"],
            "page_reference": 52
        },
        {
            "id": 5,
            "front": "Wie ist ein Ionengitter aufgebaut?",
            "back": "Ein dreidimensionales, regelmäßiges Raumgitter aus Kationen und Anionen, zusammengehalten durch ungerichtete elektrostatische Anziehungskräfte.",
            "difficulty": "schwer",
            "tags": ["Salze", "Kristalle"],
            "page_reference": 39
        },
        {
            "id": 6,
            "front": "Was ist ein Katalysator?",
            "back": "Ein Stoff, der die Aktivierungsenergie einer chemischen Reaktion senkt und sie beschleunigt, ohne dabei selbst verbraucht zu werden.",
            "difficulty": "mittel",
            "tags": ["Kinetik", "Reaktionen"],
            "page_reference": 60
        },
        {
            "id": 7,
            "front": "Was gibt die Massenzahl eines Atoms an?",
            "back": "Die Summe der Protonen und Neutronen im Atomkern (Nukleonenzahl).",
            "difficulty": "leicht",
            "tags": ["Atombau", "Isotope"],
            "page_reference": 16
        },
        {
            "id": 8,
            "front": "Was sind Isotope?",
            "back": "Atome desselben Elements mit gleicher Protonenzahl, aber unterschiedlicher Anzahl an Neutronen (z. B. ¹²C und ¹⁴C).",
            "difficulty": "schwer",
            "tags": ["Isotope", "Atombau"],
            "page_reference": 17
        }
    ]
    return {"topic": topic, "cards": cards[:req.num_cards]}


@app.post("/api/statements")
async def generate_statements(req: StatementRequest):
    """Generate true/false statements."""
    agent = get_agent()
    if agent is not None:
        try:
            return agent.generate_statements(topic=req.topic, num_statements=req.num_statements)
        except Exception as e:
            print(f"Agent statements error: {e}")

    topic = req.topic or "Chemie 9./10. Schuljahr"
    statements = [
        {
            "id": 1,
            "statement": "Alle Atome eines Elements haben immer exakt dieselbe Anzahl an Neutronen.",
            "is_true": False,
            "explanation": "Atome desselben Elements können unterschiedliche Neutronenzahlen haben; man nennt sie Isotope.",
            "correction": "Atome desselben Elements haben stets die gleiche Protonenzahl, aber die Neutronenzahl kann variieren (Isotope).",
            "page_reference": 16
        },
        {
            "id": 2,
            "statement": "Edelgase wie Helium, Neon und Argon sind chemisch besonders reaktionsträge.",
            "is_true": True,
            "explanation": "Edelgase besitzen bereits eine vollbesetzte Außenschale (Edelgaskonfiguration) und müssen keine weiteren Elektronen aufnehmen oder abgeben.",
            "correction": "",
            "page_reference": 26
        },
        {
            "id": 3,
            "statement": "Bei einer chemischen Reaktion bleibt die Gesamtmasse der beteiligten Stoffe erhalten.",
            "is_true": True,
            "explanation": "Gesetz von der Erhaltung der Masse: In einem geschlossenen System ist die Masse der Ausgangsstoffe gleich der Masse der Reaktionsprodukte.",
            "correction": "",
            "page_reference": 30
        },
        {
            "id": 4,
            "statement": "Salzlösungen leiten den elektrischen Strom, weil sich freie Elektronen durch die Flüssigkeit bewegen.",
            "is_true": False,
            "explanation": "In wässrigen Salzlösungen leiten frei bewegliche Ionen (Kationen und Anionen) den Strom, nicht freie Elektronen.",
            "correction": "In Salzlösungen erfolgt die elektrische Leitung durch frei bewegliche Ionen (Hydrathüllen).",
            "page_reference": 41
        },
        {
            "id": 5,
            "statement": "Metalle stehen im Periodensystem überwiegend links und in der Mitte.",
            "is_true": True,
            "explanation": "Der Großteil aller chemischen Elemente sind Metalle. Sie befinden sich links und in der Mitte des Periodensystems.",
            "correction": "",
            "page_reference": 25
        },
        {
            "id": 6,
            "statement": "Ein Katalysator verschiebt das chemische Gleichgewicht zugunsten der Produkte.",
            "is_true": False,
            "explanation": "Ein Katalysator beschleunigt nur das Erreichen des Gleichgewichts durch Senkung der Aktivierungsenergie, ändert aber nicht die Lage des Gleichgewichts.",
            "correction": "Ein Katalysator beschleunigt Hin- und Rückreaktion gleichermaßen und verändert die Gleichgewichtslage nicht.",
            "page_reference": 62
        }
    ]
    return {"topic": topic, "statements": statements[:req.num_statements]}


@app.post("/api/explore")
async def explore_topic(req: TopicRequest):
    """Get a comprehensive topic overview."""
    agent = get_agent()
    if agent is not None:
        try:
            return agent.explore_topic(req.topic)
        except Exception as e:
            print(f"Agent explore error: {e}")

    summary = (
        f"# Thema: {req.topic}\n\n"
        f"## 1. Überblick\n"
        f"Das Thema **{req.topic}** ist ein Kernbestandteil des Chemieunterrichts der 9. und 10. Jahrgangsstufe. "
        f"Hierbei werden stoffliche Eigenschaften auf atomarer und molekularer Ebene mit makroskopischen "
        f"Phänomenen verknüpft.\n\n"
        f"## 2. Wichtige Konzepte\n"
        f"- **Teilchenmodell & Atombau**: Verständnis der Kern-Hülle-Struktur und der Elektronenschalen.\n"
        f"- **Reaktionsverhalten**: Wie und warum Stoffe miteinander reagieren (Triebkraft: Edelgaskonfiguration).\n"
        f"- **Energieumwandlung**: Exotherme vs. endotherme Prozesse und die Rolle der Aktivierungsenergie.\n\n"
        f"## 3. Typische Formeln und Gleichungen\n"
        f"- Bildung von Salzen: `2 Na + Cl₂ → 2 NaCl`\n"
        f"- Wasserbildung: `2 H₂ + O₂ → 2 H₂O`\n\n"
        f"## 4. Merksatz\n"
        f"**Merke**: Chemische Reaktionen sind Vorgänge, bei denen aus Ausgangsstoffen (Edukten) neue Stoffe (Produkte) "
        f"mit neuen Eigenschaften entstehen, begleitet von Energieumsatz."
    )
    return {
        "topic": req.topic,
        "summary": summary,
        "sources": [
            {"source_num": 1, "page": 12, "chapter": f"Kapitel {req.topic}"},
            {"source_num": 2, "page": 28, "chapter": "Fokus Chemie Sekundarstufe I"}
        ]
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    """Direct vector search (v2 if available)."""
    agent = get_agent()
    if agent is not None and hasattr(agent, "store"):
        store = agent.store
        if req.filter_type == "image":
            imgs = store.search_images_any(req.query, req.n_results)
            results = [{
                "id": im.get("filename"), "text": im.get("caption", ""),
                "metadata": {"page": im.get("page"), "section": im.get("section", ""),
                             "image_path": im.get("filename"),
                             "caption": im.get("caption", ""),
                             "keywords": im.get("keywords", "")},
                "relevance": im.get("relevance", 0),
                "distance": round(1 - im.get("relevance", 0), 3),
            } for im in imgs]
        else:
            hits = store.search_text(req.query, k=req.n_results)
            results = [{
                "id": h.id, "text": h.text, "metadata": h.meta,
                "relevance": round(h.score, 3), "distance": round(1 - h.dense, 3),
            } for h in hits]
        return {"query": req.query, "results": results}

    vs = get_vector_store()
    if vs is not None:
        results = vs.search(query=req.query, n_results=req.n_results, filter_type=req.filter_type)
        return {"query": req.query, "results": results}
    return {"query": req.query, "results": []}


@app.get("/api/topics")
async def get_topics():
    """Get available topics/chapters."""
    agent = get_agent()
    if agent is not None:
        try:
            topics = agent.get_available_topics()
            if topics:
                return {"topics": topics}
        except Exception:
            pass
    return {
        "topics": [
            "1.1 Bau der Atome & Schalenmodell",
            "1.2 Das Periodensystem der Elemente",
            "2.1 Die Ionenbindung & Salze",
            "2.2 Die Elektronenpaarbindung",
            "3.1 Chemische Reaktionen & Energie",
            "3.2 Säuren und Laugen",
            "4.1 Redoxreaktionen & Elektrochemie"
        ]
    }


@app.get("/api/images/{image_name}")
async def serve_image(image_name: str):
    """Serve extracted images (v2 first, then the legacy folder)."""
    safe = Path(image_name).name
    for folder in ("processed_data_v2/images", "processed_data/images"):
        image_path = BASE_DIR / folder / safe
        if image_path.exists():
            return FileResponse(str(image_path))
    raise HTTPException(404, "Bild nicht gefunden")


# ─── Serve Frontend ──────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend page."""
    frontend_path = BASE_DIR / "frontend/index.html"
    if not frontend_path.exists():
        raise HTTPException(500, "Frontend not found")
    return HTMLResponse(content=frontend_path.read_text(encoding="utf-8"))


@app.get("/style.css")
async def serve_css():
    css_path = BASE_DIR / "frontend/style.css"
    if not css_path.exists():
        raise HTTPException(500, "CSS not found")
    return FileResponse(str(css_path), media_type="text/css")


@app.get("/app.js")
async def serve_js():
    js_path = BASE_DIR / "frontend/app.js"
    if not js_path.exists():
        raise HTTPException(500, "JS not found")
    return FileResponse(str(js_path), media_type="application/javascript")


# ─── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"\n🧪 Chemie RAG — Starting Server on http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

