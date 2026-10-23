#!/usr/bin/env bash
# Start ChemTutor on Mac/Linux. Phones on the same Wi-Fi open http://<laptop-ip>:8000
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] && export $(grep -v '^#' .env | xargs)
echo "Laptop:  http://localhost:8000"
IP=$( (ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}') )
[ -n "$IP" ] && echo "Handy:   http://$IP:8000   (gleiches WLAN)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
