@echo off
REM Start ChemTutor on Windows. Phones on the same Wi-Fi open http://<laptop-ip>:8000
cd /d %~dp0
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo Laptop: http://localhost:8000
echo Handy: ipconfig zeigt deine IPv4-Adresse, dann http://IP:8000 im Handy-Browser
uvicorn app.main:app --host 0.0.0.0 --port 8000
