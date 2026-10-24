#!/usr/bin/env bash
# Start the v2 RAG server on http://localhost:8080
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv-v2/bin/python" ]; then
  echo "Missing .venv-v2. See README.md (Python 3.12 + sentence-transformers>=6.1)."
  exit 1
fi

# Demo tuning (fast). For a cheap CPU VPS:
#   RAG_RERANK_CANDIDATES=8 RAG_IMAGE_RERANK=4 RAG_IMAGE_VLM_CHECK=0 ./run.sh
export RAG_RERANK_CANDIDATES="${RAG_RERANK_CANDIDATES:-16}"
export RAG_IMAGE_RERANK="${RAG_IMAGE_RERANK:-8}"
export RAG_IMAGE_VLM_CHECK="${RAG_IMAGE_VLM_CHECK:-1}"
export RAG_CHAT_CACHE="${RAG_CHAT_CACHE:-256}"

exec .venv-v2/bin/python server.py
