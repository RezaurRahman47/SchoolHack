# syntax=docker/dockerfile:1.7
#
# Two images are built from this file:
#   target "rag" -> Chemie RAG API + local EmbeddingGemma/reranker models (:8080)
#   target "app" -> SchoolHack FastAPI app (:8000)
#
# Build/run them together with docker compose (see docker-compose.yml).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# libgomp is needed by the CPU build of PyTorch.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*


# ---------------------------------------------------------------------------
# RAG service (vectorstore/server.py)
# ---------------------------------------------------------------------------
FROM base AS rag

WORKDIR /app

# Install CPU-only PyTorch first. Without this, pip pulls the CUDA wheels on
# x86_64 and the image grows by several GB for no benefit in this demo.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
COPY vectorstore/requirements-v2.txt ./requirements-v2.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url "${TORCH_INDEX_URL}" torch torchvision \
    && pip install -r requirements-v2.txt

# Runtime code (the ingest-only modules are kept for the legacy fallback).
COPY vectorstore/server.py \
     vectorstore/vector_engine.py \
     vectorstore/chemie_agent.py \
     vectorstore/pdf_processor.py \
     ./
COPY vectorstore/rag_v2 ./rag_v2
COPY vectorstore/frontend ./frontend

# Committed vector index + textbook images (~20 MB, no PDF needed).
COPY vectorstore/processed_data_v2 ./processed_data_v2

# Cached once in the hf_models Docker volume on first start.
COPY scripts/download_models.py ./download_models.py
COPY docker/rag-entrypoint.sh /usr/local/bin/rag-entrypoint
RUN chmod +x /usr/local/bin/rag-entrypoint

ENV HF_HOME=/models/huggingface \
    PORT=8080
EXPOSE 8080

ENTRYPOINT ["rag-entrypoint"]


# ---------------------------------------------------------------------------
# SchoolHack web app (backend-python/)
# ---------------------------------------------------------------------------
FROM base AS app

WORKDIR /app

COPY backend-python/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY backend-python/app ./app

# A named volume is mounted here by compose, so student progress survives
# `docker compose down`. The first start creates and seeds the SQLite DB.
RUN mkdir -p /app/data

ENV RAG_BASE=http://rag:8080/api
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
