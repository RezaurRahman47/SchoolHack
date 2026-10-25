#!/usr/bin/env bash
# Start the demo: RAG (8080) + SchoolHack (8000), or the app alone.
#
#   ./run_demo.sh          full stack  (chat + textbook sources and figures)
#   ./run_demo.sh app      app only    (chat still works, without textbook sources)
#   APP_ONLY=1 ./run_demo.sh
set -e
cd "$(dirname "$0")"

MODE="${1:-full}"
if [ "${APP_ONLY:-0}" = "1" ]; then
  MODE="app"
fi
if [ "$MODE" != "app" ] && [ "$MODE" != "full" ]; then
  echo "Unknown mode '$MODE'. Use: ./run_demo.sh [full|app]"
  exit 1
fi

# The app itself needs only a light venv (no torch, no models). `app` mode
# creates it on the spot, so a fresh clone can start the chat right away.
if [ ! -x backend-python/.venv/bin/python ]; then
  if [ "$MODE" = "app" ]; then
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
      echo "ERROR: Python >= 3.10 is required (macOS: brew install python@3.12)."
      exit 1
    fi
    echo "First run: creating backend-python/.venv and installing the app (a few seconds) ..."
    "$PY" -m venv backend-python/.venv
    backend-python/.venv/bin/python -m pip install -q --upgrade pip
    backend-python/.venv/bin/python -m pip install -q -r backend-python/requirements.txt
  else
    echo "Setup missing. Run ./setup.sh first."
    exit 1
  fi
fi
[ -f backend-python/.env ] || cp backend-python/.env.example backend-python/.env
if [ "$MODE" = "full" ] && [ ! -x vectorstore/.venv-v2/bin/python ]; then
  echo "RAG venv missing. Run ./setup.sh first, or use './run_demo.sh app' to skip the RAG server."
  exit 1
fi

if [ "$MODE" = "full" ] && lsof -nP -iTCP:8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 8080 is already in use. Stop the old RAG server first."
  exit 1
fi
if lsof -nP -iTCP:8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 8000 is already in use. Stop the old SchoolHack server first."
  exit 1
fi

RAG_PID=""
APP_PID=""

cleanup() {
  [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null || true
  [ -n "$RAG_PID" ] && kill "$RAG_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Keep a Mac awake during the demo.
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dims -w $$ >/dev/null 2>&1 &
fi

if [ "$MODE" = "full" ]; then
  echo "Starting RAG server on :8080 ..."
  (cd vectorstore && ./run.sh) &
  RAG_PID=$!

  for _ in $(seq 1 60); do
    if curl -sf -m 2 http://localhost:8080/api/status >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! curl -sf -m 2 http://localhost:8080/api/status >/dev/null 2>&1; then
    echo "RAG server did not start. Check the log above."
    exit 1
  fi
else
  echo "App-only mode: chat runs on the in-app model (no textbook sources)."
fi

echo "Starting SchoolHack on :8000 ..."
(
  cd backend-python
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
  # `python -m` so a moved venv (stale console-script shebang) still works;
  # --reload so an edit to the code or a template applies without a restart.
  exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &
APP_PID=$!

for _ in $(seq 1 40); do
  if curl -sf -m 2 http://localhost:8000/login/student >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -sf -m 2 http://localhost:8000/login/student >/dev/null 2>&1; then
  echo "SchoolHack did not start. Check the traceback above."
  exit 1
fi

IP=$( (ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}') )
echo
echo "============================================================"
echo "  SchoolHack : http://localhost:8000        (login admin/admin)"
[ -n "$IP" ] && echo "  Same Wi-Fi : http://$IP:8000"
[ "$MODE" = "full" ] && echo "  RAG API    : http://localhost:8080/api/status"
echo "============================================================"
echo

# Say it plainly if the one key that chat needs is still a placeholder.
if ! grep -qE '^OPENROUTER_API_KEY=sk-or-[^.]{20,}' \
     backend-python/.env .env vectorstore/.env 2>/dev/null; then
  echo "!! No OPENROUTER_API_KEY found. The KI-Tutor will answer with"
  echo "   'nicht erreichbar' until you put your key in backend-python/.env:"
  echo "     OPENROUTER_API_KEY=sk-or-..."
  echo
fi

if [ "$MODE" = "full" ]; then
  # Warm the demo cache (optional; safely ignored without an API key).
  echo "Warming demo questions ..."
  curl -s -m 120 -X POST http://localhost:8080/api/warmup \
    -H 'Content-Type: application/json' \
    -d '{"questions":["Was ist der pH-Wert?","Warum leitet eine Salzlösung Strom?","Was passiert bei einer Neutralisation?","Was sind Alkane?"]}' \
    >/dev/null 2>&1 || true

  echo "Ready. Press Ctrl+C to stop both servers."
else
  echo "Ready. Press Ctrl+C to stop the server."
fi
wait
