---
name: chemie-vectorstore
description: >-
  Teaches how to connect to and query the Chemie RAG ChromaDB vector store
  from an external project. Use this skill when the user wants to reuse,
  query, or extend the existing vector database (processed_data/, vector_db/)
  in a new app, script, or service. Covers direct Python ChromaDB access,
  REST API access via the running FastAPI server, and embedding new documents.
---

⚠️ Critical: Always use clip-ViT-B-32 when querying — any other model produces incompatible vectors since query and stored embeddings must share the same space.

# Chemie Vector Store — Integration Guide

This skill explains how to access the **Fokus Chemie ChromaDB vector store**
from any other project. There are three access patterns — choose the one that
fits your use case.

## Quick Facts

| Property | Value |
|---|---|
| **Vector DB location** | `vector_db/chroma/` (ChromaDB persistent dir) |
| **Collection name** | `chemie_rag` |
| **Embedding model** | `clip-ViT-B-32` (sentence-transformers, 512-dim) |
| **Total chunks** | 207 (149 text + 58 images) |
| **Live REST API** | `http://localhost:8080/api/` |
| **Image files** | `processed_data/images/*.jpeg` |

---

## Option A — Direct Python Client (Same Machine, No Server Needed)

Best when your new project runs on the **same machine** and you want full
ChromaDB access without starting the FastAPI server.

### 1. Install dependencies

```bash
pip install chromadb sentence-transformers Pillow torch
```

### 2. Connect and query

```python
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

VECTORSTORE_PATH = "/Volumes/2TBSSD/anilexternal/Documents/vectorstore/vector_db/chroma"

client = chromadb.PersistentClient(
    path=VECTORSTORE_PATH,
    settings=Settings(anonymized_telemetry=False),
)
collection = client.get_collection("chemie_rag")
print(f"Total chunks: {collection.count()}")   # -> 207

# Load the SAME embedding model used at ingestion time
model = SentenceTransformer("clip-ViT-B-32")

query = "Was ist der pH-Wert?"
query_vec = model.encode([query], normalize_embeddings=True)[0].tolist()

# -- Text search --
results = collection.query(
    query_embeddings=[query_vec],
    n_results=5,
    where={"type": "text"},
    include=["documents", "metadatas", "distances"],
)
for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"Page {meta['page']}: {doc[:200]}")

# -- Image search --
img_results = collection.query(
    query_embeddings=[query_vec],
    n_results=3,
    where={"type": "image"},
    include=["metadatas", "distances"],
)
for meta in img_results["metadatas"][0]:
    print(f"Image: {meta['image_path']}  (page {meta['page']})")
```

### Metadata schema

**Text chunks** (`type: "text"`):
```python
{
    "type":       "text",
    "page":       14,
    "chapter":    "1.1 ...",
    "chunk_type": "text",   # text | definition | experiment | exercise
    "source":     "Fokus Chemie ....pdf",
}
```

**Image chunks** (`type: "image"`):
```python
{
    "type":       "image",
    "page":       12,
    "image_path": "/abs/path/processed_data/images/page12_img3.jpeg",
    "caption":    "Abb. ...",   # may be empty
    "width":      640,
    "height":     480,
}
```

---

## Option B — REST API (Any Language)

The FastAPI server must be running:
```bash
cd /Volumes/2TBSSD/anilexternal/Documents/vectorstore
.venv/bin/python server.py    # http://localhost:8080
```

### Endpoints

| Endpoint | Method | Body / Params |
|---|---|---|
| `/api/status` | GET | — |
| `/api/search` | POST | `{query, n_results, filter_type}` |
| `/api/chat`   | POST | `{question}` |
| `/api/images/{filename}` | GET | — |

### Examples

```bash
# Raw vector search
curl -X POST http://localhost:8080/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "Ionenbindung", "n_results": 5, "filter_type": "text"}'
```

```python
import requests

# Search
r = requests.post('http://localhost:8080/api/search', json={
    'query': 'Atombau Elektronenschalen',
    'n_results': 5,
    'filter_type': 'text',
})
for chunk in r.json()['results']:
    print(chunk['metadata']['page'], chunk['text'][:200])

# RAG chat (returns answer + images)
r = requests.post('http://localhost:8080/api/chat', json={
    'question': 'Erklaere den Aufbau eines Atoms'
})
data = r.json()
print(data['answer'])    # LLM answer grounded in RAG
print(data['images'])    # [{url, caption, page, relevance}, ...]
```

```javascript
// JavaScript / fetch
const res = await fetch('http://localhost:8080/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'pH-Wert Skala', n_results: 3 }),
});
const { results } = await res.json();
results.forEach(r => console.log(r.metadata.page, r.text.slice(0, 100)));
```

---

## Option C — Import VectorStoreEngine Class Directly

Copy `vector_engine.py` into your project, or add to `sys.path`:

```python
import sys
sys.path.insert(0, "/Volumes/2TBSSD/anilexternal/Documents/vectorstore")

from vector_engine import VectorStoreEngine

vs = VectorStoreEngine(persist_dir="/Volumes/2TBSSD/anilexternal/Documents/vectorstore/vector_db")

results = vs.search("Oxidation und Reduktion", n_results=5, filter_type="text")
for r in results:
    print(r["metadata"]["page"], r["text"][:200], f"relevance={r['relevance']:.2f}")

imgs = vs.search("Periodensystem Tabelle", n_results=3, filter_type="image")
for img in imgs:
    print(img["metadata"]["image_path"])

print(vs.get_stats())
```

---

## Adding New PDFs

```python
from pdf_processor import PDFProcessor
from vector_engine import VectorStoreEngine

with PDFProcessor("Inputs/unit-2/new_book.pdf") as proc:
    text_chunks  = proc.extract_text_chunks()
    image_chunks = proc.extract_images()

vs = VectorStoreEngine(persist_dir="vector_db")
vs.index_text_chunks(text_chunks)
vs.index_image_chunks(image_chunks)
print(vs.get_stats())
```

Or via CLI:
```bash
.venv/bin/python ingest.py
```

---

## Requirements for External Projects

```
chromadb>=0.4.0
sentence-transformers>=2.7.0
torch>=2.0.0
Pillow>=10.0.0
```

> IMPORTANT: Always use `clip-ViT-B-32` as the embedding model.
> Any other model produces incompatible vectors — queries will return garbage.
> The query embedding model must exactly match the ingestion embedding model.

> Apple Silicon (MPS): VectorStoreEngine auto-detects `mps` for acceleration.
