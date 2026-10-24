"""EmbeddingGemma 2 wrapper — one 768-d space for text, captions and images."""
from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer

from .mps_lock import MODEL_LOCK

MODEL_NAME = "google/embeddinggemma-2"
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    with MODEL_LOCK:
        if _model is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            _model = SentenceTransformer(
                MODEL_NAME, device=device, config_kwargs={"audio_config": None}
            )
    return _model


def embed_queries(texts: list[str] | str) -> list[list[float]]:
    m = get_model()
    with MODEL_LOCK:
        e = m.encode(texts, prompt_name="QuestionAnswering",
                     normalize_embeddings=True, batch_size=1)
    return e.tolist() if hasattr(e, "tolist") else [e.tolist()]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Text passages / captions. Caller supplies ``title: ... | text: ...``."""
    m = get_model()
    with MODEL_LOCK:
        e = m.encode(texts, normalize_embeddings=True, batch_size=8,
                     show_progress_bar=len(texts) > 32)
    return e.tolist()


def embed_interleaved(texts: list[str], images: list[str]) -> list[list[float]]:
    items = [{"text": t, "image": p} for t, p in zip(texts, images)]
    m = get_model()
    with MODEL_LOCK:
        e = m.encode(items, normalize_embeddings=True, batch_size=4,
                     show_progress_bar=len(items) > 16)
    return e.tolist()


def embed_images(paths: list[str]) -> list[list[float]]:
    items = [{"image": p} for p in paths]
    m = get_model()
    with MODEL_LOCK:
        e = m.encode(items, normalize_embeddings=True, batch_size=4,
                     show_progress_bar=len(items) > 16)
    return e.tolist()
