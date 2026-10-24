#!/usr/bin/env bash
# One-time setup for the full ChemTutor demo (SchoolHack + local RAG).
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

echo "== ChemTutor demo setup =="

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

# --- RAG environment ------------------------------------------------------
if [ ! -x vectorstore/.venv-v2/bin/python ]; then
  echo "Creating vectorstore/.venv-v2 ..."
  "$PY" -m venv vectorstore/.venv-v2
  vectorstore/.venv-v2/bin/python -m pip install -q --upgrade pip
  echo "Installing RAG dependencies (torch etc., first run can take 5–10 min) ..."
  vectorstore/.venv-v2/bin/python -m pip install -r vectorstore/requirements-v2.txt
else
  echo "vectorstore/.venv-v2 already exists — skipping install."
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
[ -f vectorstore/.env ] || cp vectorstore/.env.example vectorstore/.env
[ -f backend-python/.env ] || cp backend-python/.env.example backend-python/.env

if grep -q '^OPENROUTER_API_KEY=sk-or-\.\.\.' vectorstore/.env 2>/dev/null; then
  echo
  echo "!! Add your OpenRouter key to vectorstore/.env before the demo:"
  echo "   OPENROUTER_API_KEY=sk-or-..."
fi

# --- models ---------------------------------------------------------------
if [ "${SKIP_MODELS:-0}" != "1" ]; then
  echo "Downloading/caching embedding + reranker models (~3.8 GB, one time) ..."
  vectorstore/.venv-v2/bin/python scripts/download_models.py || {
    echo "Model download failed. You can rerun: vectorstore/.venv-v2/bin/python scripts/download_models.py"
  }
else
  echo "SKIP_MODELS=1 — skipping model download."
fi

# --- verification ---------------------------------------------------------
vectorstore/.venv-v2/bin/python scripts/check_setup.py || true

echo
echo "Setup done."
echo "Next: put your OpenRouter key in vectorstore/.env, then run ./run_demo.sh"
