#!/usr/bin/env bash
# One-time setup for ChemTutor.
#
#   ./setup.sh         full stack  (app + local RAG service and its models)
#   ./setup.sh app     app only    (chat + tests; no torch, no model download)
#
# Chat needs just one OpenRouter key; the RAG service is optional enrichment
# (textbook sources, figures, quiz/flashcard generators).
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

MODE="${1:-full}"
if [ "$MODE" != "app" ] && [ "$MODE" != "full" ]; then
  echo "Unknown mode '$MODE'. Use: ./setup.sh [full|app]"
  exit 1
fi

echo "== ChemTutor setup ($MODE) =="

# --- pick a Python >= 3.10 ------------------------------------------------
PY=""
for c in python3.12 python3.13 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
      PY="$c"
      break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: Python >= 3.10 is required."
  echo "  macOS:  brew install python@3.12   (or install from python.org)"
  echo "  Then:   ./setup.sh"
  exit 1
fi
echo "Using $($PY --version) ($PY)"

# --- RAG environment (optional: only the textbook extras need it) ----------
if [ "$MODE" = "full" ]; then
  if [ ! -x vectorstore/.venv-v2/bin/python ]; then
    echo "Creating vectorstore/.venv-v2 ..."
    "$PY" -m venv vectorstore/.venv-v2
    vectorstore/.venv-v2/bin/python -m pip install -q --upgrade pip
    echo "Installing RAG dependencies (torch etc., first run can take 5–10 min) ..."
    vectorstore/.venv-v2/bin/python -m pip install -r vectorstore/requirements-v2.txt
  else
    echo "vectorstore/.venv-v2 already exists — skipping install."
  fi
else
  echo "App-only: skipping the RAG venv and its ~3.8 GB of models."
fi

# --- SchoolHack environment ----------------------------------------------
if [ ! -x backend-python/.venv/bin/python ]; then
  echo "Creating backend-python/.venv ..."
  "$PY" -m venv backend-python/.venv
  backend-python/.venv/bin/python -m pip install -q --upgrade pip
  backend-python/.venv/bin/python -m pip install -q -r backend-python/requirements.txt
else
  echo "backend-python/.venv already exists — skipping install."
fi

# --- env files ------------------------------------------------------------
[ -f backend-python/.env ] || cp backend-python/.env.example backend-python/.env
if [ "$MODE" = "full" ]; then
  [ -f vectorstore/.env ] || cp vectorstore/.env.example vectorstore/.env
fi

if ! grep -qE '^OPENROUTER_API_KEY=sk-or-[^.]{20,}' \
     backend-python/.env vectorstore/.env 2>/dev/null; then
  echo
  echo "!! Add your OpenRouter key before the demo:"
  echo "   backend-python/.env"
  echo "   OPENROUTER_API_KEY=sk-or-..."
fi

# --- models ---------------------------------------------------------------
# Only the optional RAG service (textbook sources) needs these; chat works
# without them. Skip with: SKIP_MODELS=1 ./setup.sh
if [ "$MODE" = "full" ] && [ "${SKIP_MODELS:-0}" != "1" ]; then
  echo "Downloading/caching embedding + reranker models (~3.8 GB, one time) ..."
  vectorstore/.venv-v2/bin/python scripts/download_models.py || {
    echo "Model download failed. You can rerun: vectorstore/.venv-v2/bin/python scripts/download_models.py"
  }
elif [ "$MODE" = "full" ]; then
  echo "SKIP_MODELS=1 — skipping model download."
fi

# --- verification ---------------------------------------------------------
if [ -x vectorstore/.venv-v2/bin/python ]; then
  vectorstore/.venv-v2/bin/python scripts/check_setup.py || true
fi

echo
echo "Setup done ($MODE)."
echo "Next: put your OpenRouter key in backend-python/.env (or vectorstore/.env), then:"
if [ "$MODE" = "full" ]; then
  echo "  ./run_demo.sh        full stack (chat + textbook sources, uses :8080)"
else
  echo "  ./run_demo.sh app    app only   (chat without the RAG server)"
fi
