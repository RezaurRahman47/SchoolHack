#!/bin/sh
# Download the two local models once, then start the RAG server.
set -eu

: "${HF_HOME:=/models/huggingface}"
export HF_HOME

READY_MARKER="$HF_HOME/.schoolhack-models-ready"

case "${OPENROUTER_API_KEY:-}" in
    ""|"sk-or-...")
        echo "WARNING: OPENROUTER_API_KEY is missing or still the example value."
        echo "         The app will start, but the KI-Tutor cannot answer."
        ;;
esac

if [ ! -f "$READY_MARKER" ]; then
    echo "============================================================"
    echo " First start: downloading the local models (~3.8 GB, one time)"
    echo " Cache: $HF_HOME  (Docker volume hf_models)"
    echo " This can take 5-20 minutes depending on the connection."
    echo "============================================================"
    python /app/download_models.py
    touch "$READY_MARKER"
    echo "Models ready."
fi

exec python /app/server.py
