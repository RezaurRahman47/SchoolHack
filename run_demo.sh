#!/usr/bin/env bash
# Start the complete demo: RAG (8080) + SchoolHack (8000).
set -e
cd "$(dirname "$0")"

if [ ! -x vectorstore/.venv-v2/bin/python ] || [ ! -x backend-python/.venv/bin/python ]; then
  echo "Setup missing. Run ./setup.sh first."
  exit 1
fi

if lsof -ti :8080 >/dev/null 2>&1; then
  echo "Port 8080 is already in use. Stop the old RAG server first."
  exit 1
fi
if lsof -ti :8000 >/dev/null 2>&1; then
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

echo "Starting SchoolHack on :8000 ..."
(
  cd backend-python
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
  # Use `python -m` so a moved venv (stale console-script shebang) still works.
  exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
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
echo "  RAG API    : http://localhost:8080/api/status"
echo "============================================================"
echo

# Warm the demo cache (optional; safely ignored without an API key).
echo "Warming demo questions ..."
curl -s -m 120 -X POST http://localhost:8080/api/warmup \
  -H 'Content-Type: application/json' \
  -d '{"questions":["Was ist der pH-Wert?","Warum leitet eine Salzlösung Strom?","Was passiert bei einer Neutralisation?","Was sind Alkane?"]}' \
  >/dev/null 2>&1 || true

echo "Ready. Press Ctrl+C to stop both servers."
wait
