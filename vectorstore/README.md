# 🧪 ChemieRAG — Fokus Chemie

Multimodales RAG-System für **Fokus Chemie 9/10** (Berlin/Brandenburg).
Es beantwortet Schülerfragen in **2–3 kurzen Sätzen**, nur mit Belegstellen aus
dem Schulbuch, und zeigt höchstens **eine** Abbildung — und nur, wenn sie die
Frage wirklich beantwortet.

## ⚡ Schnellstart

Alles läuft aus diesem Ordner:

```bash
cd /Volumes/2TBSSD/anilexternal/Documents/Schoolhack/SchoolHack/vectorstore

# 1. Key (einmalig)
echo 'OPENROUTER_API_KEY=sk-or-...' > .env

# 2. Server starten
.venv-v2/bin/python server.py        # http://localhost:8080
```

Die App (SchoolHack) läuft separat auf **http://localhost:8000** und spricht den
RAG-Server auf Port 8080 an.

## 🏁 Hackathon-Demo (schnellste Variante)

**RAG bleibt auf dem Mac (MPS).** Nur die SchoolHack-App wird nach außen
geöffnet — die App ruft den RAG-Server serverseitig über `localhost:8080` auf,
also bleiben Embeddings und Reranker lokal und schnell.

```bash
# Terminal 1 — RAG
cd SchoolHack/vectorstore && ./run.sh

# Cache für die Demo-Fragen vorwärmen (einmal, ~10 s)
curl -X POST http://localhost:8080/api/warmup \
  -H 'Content-Type: application/json' \
  -d '{"questions":[
    "Was ist der pH-Wert?",
    "Warum leitet eine Salzlösung Strom?",
    "Was passiert bei einer Neutralisation?",
    "Was sind Alkane?"
  ]}'

# Terminal 2 — SchoolHack
cd SchoolHack/backend-python && ./run.sh     # http://localhost:8000

# Optional: öffentliche URL für Judges (nur Port 8000!)
cloudflared tunnel --url http://localhost:8000
```

Gemessene Werte auf diesem Mac (MPS, warm):

| Fall | Zeit |
|---|---:|
| Frage im Warmup-Cache | **0.001 s** |
| Neue Frage ohne Bild | **~2.8 s** |
| Neue Frage mit Bild (LLM + Vision parallel) | **~3.0–3.8 s** |
| Vorher (GLM + 30 Reranker-Kandidaten) | 4.4–14.0 s |

Wichtig: **nicht** Port 8080 tunneln. Der RAG-Server soll lokal bleiben; nur die
App (8000) braucht eine öffentliche URL.

### Später auf einen günstigen VPS

Der API-Vertrag bleibt gleich. Nur `RAG_BASE` ändern:

```bash
# backend-python/.env
RAG_BASE=https://rag.dein-vps.de/api
```

Auf einem **CPU-VPS** (8 GB RAM, 4 vCPU) den schnellen Modus starten:

```bash
RAG_RERANK_CANDIDATES=8 RAG_IMAGE_RERANK=4 RAG_IMAGE_VLM_CHECK=0 ./run.sh
```

Auf einem **GPU-VPS** (T4/L4, 8–16 GB VRAM) die Defaults lassen. Erwartung:
CPU-VPS ~6–9 s, GPU-VPS ~3–5 s pro Antwort. Für maximale Skalierung später
Embedding + Rerank auf hosted APIs umstellen und den Index einmal neu bauen.

### Index neu bauen

```bash
.venv-v2/bin/python -m rag_v2.ingest --out processed_data_v2
```

Dauert ca. **4 Minuten** (EmbeddingGemma 2 auf MPS). Bilder und Captions werden
in `processed_data_v2/` gecacht; ein zweiter Lauf ist schneller.

## 🧠 Was steckt drin (v2)

| Baustein | Modell / Verfahren |
|---|---|
| Text- und Bild-Embeddings | `google/embeddinggemma-2`, 768-d, gemeinsamer Raum |
| Text-Retrieval | EmbeddingGemma 2 + BM25, fusioniert |
| Reranking | `BAAI/bge-reranker-v2-m3` (multilingual) |
| Bild-Captions | gedruckter Bildtext aus dem PDF + VLM (`google/gemma-4-31b-it`) |
| Bild-Freigabe | Seiten-Nähe + Caption-Match + abschließender VLM-JA/NEIN-Check |
| Antwort-LLM | `z-ai/glm-5.3-flash` (Fallback: Gemma 4 / Mistral) |

Der Index enthält **243 Text-Chunks** aus 6 Kapiteln und **162 Abbildungen**
(aus 190 extrahierten; dekorative Bilder werden verworfen).

### Warum die Antworten kurz sind

Der System-Prompt begrenzt auf **max. 3 Sätze / 60 Wörter**, verbietet
Begrüßungen, Aufzählungen und Allgemeinwissen und lässt die Antwort mit der
direkten Antwort beginnen. Zusätzlich werden nur die **besten 2–3** Belegstellen
übergeben. Ist der Kontext zu schwach, sagt der Tutor das ehrlich, statt zu
raten.

### Warum die Bilder relevant sind

1. Gedruckte Bildunterschriften werden räumlich aus dem PDF extrahiert
   (`caption_printed`) und sind das stärkste Suchsignal.
2. Bilder werden nur auf den zitierten Seiten (±1) gesucht.
3. Ein multilingualer Reranker bewertet Frage ↔ Caption.
4. Ein Vision-Modell prüft abschließend, ob die Abbildung den gefragten Aspekt
   zeigt. Sonst wird **kein** Bild angezeigt.

## 📁 Struktur

```
vectorstore/
├── rag_v2/
│   ├── extract.py      # Layout, Spalten, Überschriften, Bilder, Captions
│   ├── clean.py        # Ligaturen, Soft-Hyphens, Chunking
│   ├── caption.py      # VLM-Captions
│   ├── embed.py        # EmbeddingGemma 2
│   ├── ingest.py       # kompletter Index-Bau
│   ├── store.py        # Chroma + BM25 + Reranker + Bild-Gating
│   ├── agent.py        # kurze Antworten, Quellen, Bild-Freigabe
│   └── eval.py         # 20 Testfragen ohne LLM
├── processed_data_v2/  # Chroma, Bilder, Captions, Text-Chunks
├── frontend/           # Standalone-UI (Port 8080)
├── server.py           # FastAPI (v2, Fallback auf v1)
├── .venv-v2/           # Python 3.12 (EmbeddingGemma 2, Reranker)
└── .venv/              # altes v1-Environment (CLIP)
```

## 💰 Kosten

| Vorgang | Kosten |
|---|---|
| Index komplett neu bauen | **$0** (lokal) + ca. **$0.03** VLM-Captions |
| Eine Chat-Antwort | **ca. $0.0003** (GLM-5.3-Flash) |
| 300 Fragen/Tag | **ca. $0.09/Tag** |

Der Teuerste Posten ist nicht der Index, sondern die Chat-Antworten — und die
sind durch die kurzen Antworten deutlich günstiger als vorher.

## 🔌 API

| Endpoint | Methode | Body |
|---|---|---|
| `/api/status` | GET | — |
| `/api/chat` | POST | `{question, topic?, core_principle?}` |
| `/api/search` | POST | `{query, n_results, filter_type?}` |
| `/api/images/{filename}` | GET | — |
| `/api/topics` | GET | — |

## 🧪 Retrieval testen (ohne LLM)

```bash
.venv-v2/bin/python -m rag_v2.eval
```

Zeigt für 20 typische Fragen die Top-3-Textstellen, Scores und die
Bild-Entscheidung. Gut zum Kalibrieren, bevor man am Prompt dreht.

## 🗂 v1 (Legacy)

`vector_db/` + `chemie_rag` + `clip-ViT-B-32` bleibt als Fallback erhalten.
Nicht mehr für neue Arbeit verwenden: CLIP-Textsuche auf deutschen Sätzen ist
zu schwach, und die alten Captions waren fast leer.
