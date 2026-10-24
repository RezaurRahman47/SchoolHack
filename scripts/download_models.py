"""Download/cache the two local models used by the RAG server.

Run with the v2 venv:
    vectorstore/.venv-v2/bin/python scripts/download_models.py
"""
from __future__ import annotations

import os
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

from sentence_transformers import CrossEncoder, SentenceTransformer  # noqa: E402


def main() -> None:
    t0 = time.time()
    print("• EmbeddingGemma 2 (text + image, 768-d) ...")
    SentenceTransformer(
        "google/embeddinggemma-2",
        device="cpu",
        config_kwargs={"audio_config": None},
    )
    print("• bge-reranker-v2-m3 ...")
    CrossEncoder("BAAI/bge-reranker-v2-m3", device="cpu", max_length=512)

    cache = Path.home() / ".cache" / "huggingface" / "hub"
    print(f"✓ models cached in {cache}")
    print(f"  done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
