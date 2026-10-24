---
name: chemie-vectorstore
description: >-
  Connect to and query the Fokus Chemie RAG stores. Use when reusing, querying or
  extending the vector database in another app, script or service. Covers the
  current v2 store (EmbeddingGemma 2, text + images, reranker), the legacy v1
  CLIP store, direct ChromaDB access, and the FastAPI server.
---

# Chemie Vector Store — Integration Guide

There are **two** indexes. Use **v2** unless you have a reason not to.

| | v2 (current) | v1 (legacy) |
|---|---|---|
| Chroma dir | `processed_data_v2/chroma` | `vector_db/chroma` |
| Collection | `chemie_rag_v2` | `chemie_rag` |
| Model | `google/embeddinggemma-2` (768-d, text + image + audio) | `clip-ViT-B-32` (512-d) |
| Text chunks | 243 | 149 |
| Images | 162 | 58 |
| Image metadata | printed caption + VLM caption + keywords + type | pixels + mostly empty caption |
| Retrieval | dense + BM25 + `bge-reranker-v2-m3` + page-aware image gating | dense only |

⚠️ **Never mix models.** A v2 query must use EmbeddingGemma 2; a v1 query must
use CLIP. Query and stored vectors must share the same space.

## Quick Facts (v2)

| Property | Value |
|---|---|
| Base directory | `/Volumes/2TBSSD/anilexternal/Documents/Schoolhack/SchoolHack/vectorstore` |
| Chroma dir | `processed_data_v2/chroma` |
| Collection | `chemie_rag_v2` |
| Embedding model | `google/embeddinggemma-2`, 768-d, normalized |
| Records | 729 (243 text + 162 captions + 162 image+caption + 162 image-only) |
| Image files | `processed_data_v2/images/*.jpg` (max 1024 px) |
| Captions | `processed_data_v2/images_captioned.json` |
| Text chunks | `processed_data_v2/text_chunks.json` |
| Live API | `http://localhost:8080/api/` |
| Source PDF | 184 pages; content used = pages 13–149 |

The book is *Fokus Chemie 9/10 Berlin/Brandenburg*. Text chunks carry the real
chapter (6 chapters), section, page and type (`text`, `summary`, `experiment`,
`definition`).

---

## Option A — Use the existing retrieval stack (recommended)

This gives you hybrid retrieval, the reranker, the short-answer prompt and the
final vision check for images. Run from the `vectorstore` directory with
`.venv-v2/bin/python`.

```python
from rag_v2.store import RAGStore
from rag_v2.agent import ChemieAgentV2

store = RAGStore("processed_data_v2")
hits = store.search_text("Warum leitet eine Salzlösung Strom?", k=3)
for h in hits:
    print(h.meta["page"], h.meta["section"], round(h.score, 3), h.text[:200])

agent = ChemieAgentV2(store)
out = agent.chat("Was ist der pH-Wert?", topic="pH-Skala einordnen")
print(out["answer"])      # 2–3 sentences, <= 60 words
print(out["sources"])     # [{page, section, chapter, relevance}]
print(out["images"])      # 0 or 1 image, already relevance-checked
```

`RAGStore.search_images(query, pages, top_text_score, k=1)` restricts candidates
to the cited pages ±1. `search_images_any(query, k=1, min_score=0.72)` searches
the whole book but is stricter.

---

## Option B — Direct ChromaDB + EmbeddingGemma 2

Use this for a custom UI or a non-Python service. Install:

```bash
pip install "sentence-transformers>=6.1" chromadb pillow
```

```python
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

VS = "/Volumes/2TBSSD/anilexternal/Documents/Schoolhack/SchoolHack/vectorstore"
client = chromadb.PersistentClient(
    path=f"{VS}/processed_data_v2/chroma",
    settings=Settings(anonymized_telemetry=False),
)
col = client.get_collection("chemie_rag_v2")
model = SentenceTransformer("google/embeddinggemma-2", device="mps",
                            config_kwargs={"audio_config": None})

q = model.encode("Was ist der pH-Wert?", prompt_name="QuestionAnswering",
                 normalize_embeddings=True)

# Text passages
res = col.query(query_embeddings=[q], n_results=5, where={"type": "text"},
                include=["documents", "metadatas", "distances"])
for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
    print(meta["page"], meta["section"], doc[:200])

# Image captions (printed caption is the strongest signal)
res = col.query(query_embeddings=[q], n_results=5, where={"type": "image_caption"},
                include=["documents", "metadatas", "distances"])
for meta in res["metadatas"][0]:
    print(meta["page"], meta["image_path"], meta["caption"])
```

### Prefixes / input formats

- Query: `prompt_name="QuestionAnswering"` (or `"SearchQuery"`).
- Document: `"title: {section} | text: {content}"` — do **not** use
  `prompt_name="Document"` when you have a real title.
- Caption: `"title: {section} | text: {caption + keywords}"`.
- Pure image: `model.encode({"image": "/abs/path.jpg"})`.
- Image + caption together:
  `model.encode({"text": "title: ... | text: ... <|image|>", "image": "/abs/path.jpg"})`.

The model is 768-d and supports Matryoshka truncation to 512/256/128 — if you
truncate, re-normalize and truncate queries and documents identically.

### v2 metadata

Text (`type: "text"`):
```python
{"type": "text", "page": 32, "chapter": "SÄUREN UND LAUGEN – ECHT ÄTZEND",
 "section": "Basische Lösungen", "chunk_type": "text", "source": "Fokus Chemie ..."}
```

Image (`type: "image"`, `"image_caption"` or `"image_visual"`):
```python
{"type": "image", "page": 46, "chapter": "NEUTRALISATION – SALZE",
 "section": "Neutralisation", "image_path": "processed_data_v2/images/page46_img60.jpg",
 "filename": "page46_img60.jpg", "caption": "2 Reaktion einer sauren ...",
 "caption_printed": "2 Reaktion einer sauren ...", "caption_vlm": "...",
 "keywords": "Neutralisation, Säure, Base, Indikator", "image_type": "experiment",
 "teaches_chemistry": True, "confidence": 1.0}
```

---

## Option C — REST API

Start the server **from the vectorstore directory**:

```bash
cd /Volumes/2TBSSD/anilexternal/Documents/Schoolhack/SchoolHack/vectorstore
.venv-v2/bin/python server.py       # http://localhost:8080
```

| Endpoint | Method | Body |
|---|---|---|
| `/api/status` | GET | — |
| `/api/chat` | POST | `{question, topic?, core_principle?}` |
| `/api/search` | POST | `{query, n_results, filter_type?}` |
| `/api/images/{filename}` | GET | — |
| `/api/topics` | GET | — |

```python
import requests
r = requests.post("http://localhost:8080/api/chat", json={
    "question": "Warum leitet eine Salzlösung Strom?",
    "topic": "Ionenladung bestimmen",
}).json()
print(r["answer"])    # short, grounded
print(r["images"])    # [] or one checked image
```

`/api/search` with `filter_type="text"` returns `{text, metadata, relevance,
distance}`. With `filter_type="image"` it returns the same shape, with
`metadata.image_path` set to the filename.

---

## Rebuilding the v2 index

```bash
cd /Volumes/2TBSSD/anilexternal/Documents/Schoolhack/SchoolHack/vectorstore
.venv-v2/bin/python -m rag_v2.ingest --out processed_data_v2
```

Steps: layout-aware text extraction (13–149) → printed-caption extraction →
VLM captions for the remaining figures → EmbeddingGemma 2 embeddings → Chroma.
It is idempotent: images/captions are cached in `processed_data_v2`, so only
changed steps run. Full rebuild ≈ 4 minutes on this Mac; captioning 190 images
≈ 2 minutes and ≈ $0.03 with Gemma 4 31B.

To add another PDF, pass `--pdf /path/to/book.pdf` and change the page range in
`rag_v2/extract.py` (`start_page`, `end_page`), then rebuild. Re-embed **all**
text with the same model.

## Legacy v1

`vector_db/chroma` + `chemie_rag` + `clip-ViT-B-32` is kept only as a fallback.
If you must query it, use CLIP 512-d and the old `vector_engine.VectorStoreEngine`.
Do not use it for new work.
