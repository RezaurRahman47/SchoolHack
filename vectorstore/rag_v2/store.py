"""Hybrid retrieval (dense + BM25) with page-aware image gating."""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
import torch
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from .embed import embed_queries
from .mps_lock import MODEL_LOCK

COLLECTION = "chemie_rag_v2"
# Demo defaults. For a cheap CPU VPS set RAG_RERANK_CANDIDATES=8.
TEXT_RERANK = int(os.environ.get("RAG_RERANK_CANDIDATES", "16"))
IMAGE_RERANK = int(os.environ.get("RAG_IMAGE_RERANK", "8"))
TOKEN_RE = re.compile(r"[a-zäöüß0-9]+")
STOP = {"der", "die", "das", "und", "oder", "von", "zu", "im", "in", "mit", "auf",
        "für", "ist", "ein", "eine", "einer", "eines", "dem", "den", "des", "sich",
        "bei", "aus", "als", "auch", "nicht", "wird", "werden", "sind", "hat",
        "haben", "wie", "was", "warum", "welche", "welcher", "welches", "man",
        "sich", "es", "am", "an", "so", "dass", "kann", "können", "muss", "müssen"}


SYNONYMS = {
    "strom": ["leitfähigkeit", "elektrisch", "ladung", "ionen", "ladungsträger"],
    "leiten": ["leitfähigkeit", "elektrisch", "ionen", "ladungsträger"],
    "leitfähigkeit": ["strom", "ionen", "ladungsträger", "frei beweglich"],
    "salzlösung": ["ionen", "natriumchlorid", "kochsalz", "ionensubstanz"],
    "salz": ["ionen", "ionensubstanz", "natriumchlorid"],
    "ionen": ["ladungsträger", "frei beweglich"],
    "siedepunkt": ["siedetemperatur"],
    "siedetemperatur": ["siedepunkt"],
    "löslich": ["löslichkeit", "mischbar"],
    "löslichkeit": ["löslich", "mischbar"],
    "kalkseife": ["kalkseifen", "hartes", "wasser"],
    "hartes": ["wasserhärte", "kalk"],
    "konzentration": ["stoffmengenkonzentration"],
    "stoffmengenkonzentration": ["konzentration", "c"],
    "verseifung": ["verseifen", "seife"],
    "ester": ["carbonsäureester", "veresterung"],
    "isomere": ["isomer", "struktur"],
    "exotherm": ["wärmeabgabe", "energie"],
    "endotherm": ["wärmeaufnahme", "energie"],
    "neutralisation": ["säure", "base", "salzlösung", "wasser", "reaktion"],
    "alkan": ["kohlenwasserstoff", "methan", "ethan", "propan", "butan"],
    "alkane": ["kohlenwasserstoffe", "methan", "ethan", "propan", "butan"],
    "siedepunkt": ["siedetemperatur", "van der waals", "zwischenmolekulare kräfte"],
    "siedetemperatur": ["siedepunkt", "van der waals"],
    "kalkseife": ["kalkseifen", "seife", "calcium", "magnesium", "hartes wasser"],
    "kalkseifen": ["kalkseife", "seife", "calcium", "magnesium"],
    "verseifung": ["seife", "fett", "natronlauge", "glycerin"],
    "indikator": ["farbumschlag", "universalindikator", "lackmus", "ph-wert"],
    "ethanol": ["alkohol", "wasserstoffbrücken", "löslichkeit"],
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP and len(t) > 1]


def expand_tokens(text: str) -> list[str]:
    toks = tokenize(text)
    out = list(toks)
    for t in toks:
        out.extend(SYNONYMS.get(t, []))
    return out


def expand_query(text: str) -> str:
    extra = []
    for t in tokenize(text):
        extra.extend(SYNONYMS.get(t, []))
    if not extra:
        return text
    # Keep order, drop duplicates.
    return text + " " + " ".join(dict.fromkeys(extra))


@dataclass
class Hit:
    id: str
    text: str
    meta: dict
    dense: float
    bm25: float
    score: float
    rerank: float = 0.0


_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    with MODEL_LOCK:
        if _reranker is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device=device, max_length=512)
        return _reranker


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class RAGStore:
    def __init__(self, data_dir: str = "processed_data_v2"):
        self.data_dir = Path(data_dir)
        client = chromadb.PersistentClient(
            path=str(self.data_dir / "chroma"),
            settings=Settings(anonymized_telemetry=False),
        )
        self.col = client.get_collection(COLLECTION)
        data = self.col.get(include=["documents", "metadatas"])
        self.ids = data["ids"]
        self.docs = data["documents"]
        self.metas = data["metadatas"]

        self.text_idx = [i for i, m in enumerate(self.metas) if m.get("type") == "text"]
        self.cap_idx = [i for i, m in enumerate(self.metas) if m.get("type") == "image_caption"]

        self.text_bm25 = BM25Okapi([tokenize(self.docs[i]) for i in self.text_idx])
        self.cap_bm25 = BM25Okapi([
            tokenize(self.docs[i] + " " + self.metas[i].get("keywords", ""))
            for i in self.cap_idx
        ])
        self.cap_paths = [self.metas[i].get("image_path", "") for i in self.cap_idx]

    # ------------------------------------------------------------------ text
    def search_text(self, query: str, k: int = 3, candidates: int = 40) -> list[Hit]:
        q = embed_queries([query])[0]
        res = self.col.query(
            query_embeddings=[q], n_results=candidates,
            where={"type": "text"},
            include=["documents", "metadatas", "distances"],
        )
        dense: dict[str, tuple[str, dict, float]] = {}
        for i, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                      res["metadatas"][0], res["distances"][0]):
            dense[i] = (doc, meta, 1.0 - float(dist))

        tokens = expand_tokens(query)
        bm = self.text_bm25.get_scores(tokens)
        order = sorted(range(len(self.text_idx)), key=lambda j: -bm[j])[:candidates]
        bm_map = {self.ids[self.text_idx[j]]: float(bm[j]) for j in order}
        bm_max = max(bm_map.values(), default=1.0) or 1.0
        q_tokens = set(tokenize(query))

        hits = []
        for i, (doc, meta, score) in dense.items():
            b = bm_map.get(i, 0.0) / bm_max
            fused = 0.85 * score + 0.15 * b
            # Prefer the book's own "Auf einen Blick" summaries and definitions.
            if meta.get("chunk_type") in ("summary", "definition"):
                fused *= 1.03
            sec = set(tokenize((meta.get("section", "") + " " + meta.get("chapter", ""))))
            if len(q_tokens & sec) >= 2:
                fused *= 1.05
            hits.append(Hit(i, doc, meta, score, b, fused))
        hits.sort(key=lambda h: -h.score)
        hits = self._dedupe(hits)[:TEXT_RERANK]
        if hits:
            rerank_query = expand_query(query)
            with MODEL_LOCK:
                rr = get_reranker().predict([(rerank_query, h.text) for h in hits])
            top = max(h.score for h in hits) or 1.0
            for h, s in zip(hits, rr):
                h.rerank = float(s)
                h.score = 0.72 * _sigmoid(float(s)) + 0.28 * (h.score / top)
            hits.sort(key=lambda h: -h.score)
        return hits[:k]

    def _dedupe(self, hits: list[Hit]) -> list[Hit]:
        out, seen = [], set()
        for h in hits:
            key = " ".join(h.text[:140].lower().split())
            if key in seen:
                continue
            seen.add(key)
            out.append(h)
        return out

    # ----------------------------------------------------------------- images
    def search_images(self, query: str, pages: list[int], top_text: float,
                      k: int = 1) -> list[dict]:
        q = embed_queries([query])[0]
        page_set = set()
        for p in pages:
            page_set.update({p - 1, p, p + 1})
        where = {"$and": [
            {"type": {"$in": ["image", "image_caption", "image_visual"]}},
            {"page": {"$in": sorted(page_set)}},
        ]}
        res = self.col.query(query_embeddings=[q], n_results=24, where=where,
                             include=["metadatas", "distances"])
        groups: dict[str, dict[str, float]] = {}
        meta_by_path: dict[str, dict] = {}
        for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
            path = meta.get("image_path", "")
            if not path:
                continue
            t = meta.get("type")
            groups.setdefault(path, {})[t] = 1.0 - float(dist)
            meta_by_path[path] = meta

        # BM25 over the printed/VLM captions — exact German terms matter here.
        cap_bm = self.cap_bm25.get_scores(expand_tokens(query))
        path_bm: dict[str, float] = {}
        for j, path in enumerate(self.cap_paths):
            path_bm[path] = max(path_bm.get(path, 0.0), float(cap_bm[j]))
        bm_max = max(path_bm.values(), default=0.0) or 1.0

        scored = []
        for path, s in groups.items():
            meta = meta_by_path[path]
            if meta.get("image_type") == "decorative" or not meta.get("teaches_chemistry"):
                continue
            parts = [(s.get("image", 0.0), 0.40), (s.get("image_caption", 0.0), 0.40),
                     (s.get("image_visual", 0.0), 0.20)]
            parts = [(v, w) for v, w in parts if v]
            if not parts:
                continue
            dense = sum(v * w for v, w in parts) / sum(w for _, w in parts)
            combined = 0.70 * dense + 0.30 * (path_bm.get(path, 0.0) / bm_max)
            scored.append((combined, path, meta))

        scored.sort(key=lambda x: -x[0])
        if scored:
            top = scored[:IMAGE_RERANK]
            captions = [(m.get("caption_printed") or m.get("caption", "")) for _, _, m in top]
            with MODEL_LOCK:
                rr = get_reranker().predict([(expand_query(query), c) for c in captions])
            max_combined = max(s for s, _, _ in top) or 1.0
            scored = [(0.50 * _sigmoid(float(s)) + 0.50 * (combined / max_combined),
                       path, meta, float(s))
                      for (combined, path, meta), s in zip(top, rr)]
            scored.sort(key=lambda x: -x[0])

        # One image per printed caption/page, best match only.
        q_tokens = set(tokenize(expand_query(query)))
        seen, out = set(), []
        for score, path, meta, rr_score in scored:
            key = (meta.get("page"), (meta.get("caption_printed") or meta.get("caption", ""))[:60])
            if key in seen:
                continue
            seen.add(key)
            if score < max(0.72, 0.95 * top_text):
                continue
            caption = meta.get("caption_printed") or meta.get("caption", "")
            cap_tokens = set(tokenize(caption + " " + meta.get("keywords", "")))
            if rr_score < 0.10 and len(q_tokens & cap_tokens) < 2:
                continue
            out.append({
                "url": f"/api/images/{meta['filename']}",
                "filename": meta["filename"],
                "page": meta.get("page"),
                "section": meta.get("section", ""),
                "caption": meta.get("caption_printed") or meta.get("caption", ""),
                "keywords": meta.get("keywords", ""),
                "relevance": round(score, 3),
            })
            if len(out) >= k:
                break
        return out


    def search_images_any(self, query: str, k: int = 3, min_score: float = 0.62) -> list[dict]:
        """Image search without a page restriction (used by /api/search)."""
        q = embed_queries([query])[0]
        res = self.col.query(query_embeddings=[q], n_results=20,
                             where={"type": "image"},
                             include=["metadatas", "distances"])
        scored = []
        for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
            if meta.get("image_type") == "decorative" or not meta.get("teaches_chemistry"):
                continue
            scored.append((1.0 - float(dist), meta))
        if not scored:
            return []
        top = scored[:IMAGE_RERANK]
        captions = [(m.get("caption_printed") or m.get("caption", "")) for _, m in top]
        with MODEL_LOCK:
            rr = get_reranker().predict([(expand_query(query), c) for c in captions])
        mx = max(s for s, _ in top) or 1.0
        ranked = [(0.50 * _sigmoid(float(s)) + 0.50 * (sc / mx), m, float(s))
                  for (sc, m), s in zip(top, rr)]
        ranked.sort(key=lambda x: -x[0])

        q_tokens = set(tokenize(expand_query(query)))
        out, seen = [], set()
        for score, meta, rr_score in ranked:
            key = (meta.get("page"), (meta.get("caption_printed") or meta.get("caption", ""))[:60])
            if key in seen or score < min_score:
                continue
            caption = meta.get("caption_printed") or meta.get("caption", "")
            cap_tokens = set(tokenize(caption + " " + meta.get("keywords", "")))
            if rr_score < 0.10 and len(q_tokens & cap_tokens) < 2:
                continue
            seen.add(key)
            out.append({
                "url": f"/api/images/{meta['filename']}",
                "filename": meta["filename"],
                "page": meta.get("page"),
                "chapter": meta.get("chapter", ""),
                "section": meta.get("section", ""),
                "caption": meta.get("caption_printed") or meta.get("caption", ""),
                "keywords": meta.get("keywords", ""),
                "relevance": round(score, 3),
            })
            if len(out) >= k:
                break
        return out


_store: RAGStore | None = None


def get_store() -> RAGStore:
    global _store
    if _store is None:
        _store = RAGStore()
    return _store
