# Windows setup (native PowerShell)

The `setup.sh` / `run_demo.sh` scripts are **macOS/Linux only**. On Windows use
the commands below. The RAG index is already in the repo, so the PDF is not
needed. Python runs the local models on the CPU, so answers are slower than on
an Apple Silicon Mac (~6–12 s instead of ~3–4 s).

## 0. Prerequisites

- Windows 10/11
- Python **3.12** from <https://python.org> (tick “Add python.exe to PATH”)
- Git for Windows
- Internet (pip, Hugging Face models, OpenRouter)

Open **PowerShell** in the folder where you want the repo.

## 1. Clone

```powershell
git clone https://github.com/RezaurRahman47/SchoolHack.git
cd SchoolHack
```

## 2. Create the two Python environments

```powershell
py -3.12 -m venv vectorstore\.venv-v2
vectorstore\.venv-v2\Scripts\python.exe -m pip install --upgrade pip
vectorstore\.venv-v2\Scripts\python.exe -m pip install -r vectorstore\requirements-v2.txt

py -3.12 -m venv backend-python\.venv
backend-python\.venv\Scripts\python.exe -m pip install --upgrade pip
backend-python\.venv\Scripts\python.exe -m pip install -r backend-python\requirements.txt
```

If `py -3.12` is not found, use `python` instead (must be >= 3.10).

## 3. Environment files

```powershell
Copy-Item vectorstore\.env.example vectorstore\.env
notepad vectorstore\.env
```

Put your key in that file:

```
OPENROUTER_API_KEY=sk-or-...
```

Optionally (the same key can go here instead — the app reads both files):

```powershell
Copy-Item backend-python\.env.example backend-python\.env
notepad backend-python\.env
```

The default `RAG_BASE=http://localhost:8080/api` is correct for a local demo.
The RAG server is optional: chat also works with just `backend-python` running
(no textbook sources or figures).

## 4. (Optional) Download the local models (one time, ~3.8 GB)

Only needed for the RAG/textbook server. Skip it if you just want chat — the
tutor answers without the index.

```powershell
vectorstore\.venv-v2\Scripts\python.exe scripts\download_models.py
```

To avoid the download at the venue, copy these two folders from the Mac on a
USB stick to `%USERPROFILE%\.cache\huggingface\hub\`:

```
models--google--embeddinggemma-2
models--BAAI--bge-reranker-v2-m3
```

## 5. (Optional) Start the RAG server (window 1)

```powershell
cd vectorstore

# CPU-fast mode
$env:RAG_RERANK_CANDIDATES="8"
$env:RAG_IMAGE_RERANK="4"
$env:RAG_IMAGE_VLM_CHECK="0"

.venv-v2\Scripts\python.exe server.py
```

Leave this window open. Health check:
<http://localhost:8080/api/status>

## 6. Start SchoolHack

Open a **second** PowerShell window (or the first one, if you skipped step 5):

```powershell
cd SchoolHack\backend-python
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000> and log in with `admin / admin`.
SQLite is created automatically in `backend-python\data\`.

## 7. Warm the demo cache (optional but recommended)

In a third PowerShell window:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/warmup `
  -ContentType "application/json" `
  -Body '{"questions":["Was ist der pH-Wert?","Warum leitet eine Salzlösung Strom?","Was passiert bei einer Neutralisation?","Was sind Alkane?"]}'
```

## Stopping

Close the two PowerShell windows, or press `Ctrl+C` in each.

## Troubleshooting

- **`python` opens the Microsoft Store:** install Python 3.12 from python.org
  and reopen PowerShell.
- **Port already in use:**
  ```powershell
  Get-NetTCPConnection -LocalPort 8000,8080 -State Listen |
    Select-Object LocalPort,OwningProcess
  Stop-Process -Id <PID>
  ```
- **No answer / “Kerninformation” only:** `vectorstore\.env` has no valid
  `OPENROUTER_API_KEY`, or there is no internet.
- **Model download fails:** copy the two Hugging Face cache folders as above.
- **Very slow:** Windows uses CPU. Keep the three `RAG_*` variables set as in
  step 5. A CUDA GPU is not used by this build.

## Alternative: WSL (closest to the Mac setup)

If WSL is allowed on the laptop, the macOS/Linux scripts work unchanged:

```powershell
wsl --install -d Ubuntu
```

Inside Ubuntu:

```bash
sudo apt update && sudo apt install -y git python3.12 python3.12-venv
git clone https://github.com/RezaurRahman47/SchoolHack.git
cd SchoolHack
./setup.sh
./run_demo.sh
```

Then open <http://localhost:8000> in the Windows browser (WSL2 forwards
localhost). Models run on the CPU.
