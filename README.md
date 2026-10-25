# School Hack — ChemTutor

Chemistry practice app for **Klasse 9 (Berlin)** with a student portal, a KI-Tutor
chat and a teacher dashboard. Python + FastAPI + SQLite: one program and one
OpenRouter key.

> This file only explains **how to start the app on your own laptop**, step by step.
> If you have never started a Python project before, follow the steps in order and
> copy the commands exactly as they are written.

---

## Before you start

You need two things.

**1. Python 3.10 or newer.** Open a terminal and check:

```bash
python3 --version
```

If it prints `Python 3.10` (or higher), you are ready. If it says
*command not found*, install Python first:

- **macOS:** `brew install python@3.12` — or download it from <https://www.python.org/downloads/>
- **Windows:** download it from <https://www.python.org/downloads/> and **tick
  "Add Python to PATH"** during the installation.

**2. An OpenRouter API key** — this is what the AI tutor uses:

1. Go to <https://openrouter.ai> and sign up (free).
2. Open **Keys** → **Create key**.
3. Copy the key. It looks like `sk-or-v1-...`.

Signing up and creating a key are free. Most models need a little credit on your
OpenRouter account; if the account has none, the chat answers *"nicht erreichbar"*
just like a missing key. Without a key the app still starts and everything else
works — only the chat stays silent.

---

## Step 1 — Download the project

```bash
git clone https://github.com/RezaurRahman47/SchoolHack.git
cd SchoolHack
```

No Git installed? Open the GitHub page, click the green **Code** button →
**Download ZIP**, unzip it, and open a terminal in that folder instead.

## Step 2 — Go into the app folder

```bash
cd backend-python
```

All the following commands are typed inside this folder. If you type `ls`
(macOS/Linux) or `dir` (Windows) you should see `app`, `requirements.txt`,
`run.sh`.

## Step 3 — Create a virtual environment

A *virtual environment* is a private box for this project's packages. It keeps the
project separate from the rest of your computer, and you only create it once:

```bash
python3 -m venv .venv
```

On Windows the command is the same.

## Step 4 — Turn the virtual environment on

```bash
source .venv/bin/activate        # macOS / Linux
```

```powershell
.venv\Scripts\activate           # Windows (PowerShell)
```

Your terminal line now starts with `(.venv)`. That means it is on.

> Repeat this step **every time** you open a new terminal for this project. If you
> see `command not found: uvicorn` later, you probably forgot it.
>
> Windows: if PowerShell says *"running scripts is disabled on this system"*, run
> `Set-ExecutionPolicy -Scope Process RemoteSigned` first, then try again — or use
> `cmd` and `.venv\Scripts\activate.bat`.

## Step 5 — Install the dependencies

```bash
pip install -r requirements.txt
```

This installs what the app needs (FastAPI, Uvicorn, Jinja2 — a few small packages,
about 10 seconds).

## Step 6 — Add your API key

Create your personal settings file from the example:

```bash
cp .env.example .env             # macOS / Linux
```

```powershell
copy .env.example .env           # Windows
```

Open the new `.env` file in any text editor and put your key after the `=`:

```
OPENROUTER_API_KEY=sk-or-v1-...your own key here...
```

Save the file. (`.env` is ignored by Git, so your key stays on your machine and is
never uploaded.)

## Step 7 — Start the app

```bash
python -m uvicorn app.main:app --reload --port 8000
```

You should see something like:

```
Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Leave this terminal open.** The app runs as long as the terminal is open; press
`Ctrl + C` to stop it. The database is created automatically on the first start at
`backend-python/data/chemtutor.db` — you never have to create it yourself.

## Step 8 — Open it in your browser

Go to **<http://localhost:8000>** and log in:

| | Username | Password |
|---|---|---|
| Student | `admin` | `admin` |
| Teacher | `admin` | `admin` |

Good places to look: **KI-Tutor** (the chat), **Tests**, and **Profil → Mein
Lernprofil**.

---

## Starting it again later

Steps 3–6 are one-time only. To start the app another day:

```bash
cd SchoolHack/backend-python
source .venv/bin/activate        # .venv\Scripts\activate  on Windows
python -m uvicorn app.main:app --reload --port 8000
```

---

## Shortcut: one command instead of steps 3–7

The project ships small start scripts that create the venv, install the
dependencies and read `.env` for you:

```bash
./run.sh                         # from the backend-python folder (macOS / Linux)
```

On Windows, double-click `run.bat`.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `python3: command not found` | Python is not installed — see **Before you start** |
| `command not found: uvicorn` | The venv is not active → `source .venv/bin/activate`, or always use `python -m uvicorn ...` |
| Chat answers *"Der KI-Tutor ist gerade nicht erreichbar."* | The key in `backend-python/.env` is missing or wrong — or the OpenRouter account has no credit |
| `Address already in use` (port 8000) | Another program is already using port 8000 → close it, or start with `--port 8001` and open <http://localhost:8001> |
| The page looks old after an update | Hard reload the browser: `Cmd + Shift + R` (Mac) / `Ctrl + Shift + R` (Windows) |
| `ModuleNotFoundError: No module named 'app'` | You are in the wrong folder → `cd backend-python` and run the command there |

---

## Want to know more?

- [backend-python/README.md](backend-python/README.md) — the app in detail, plus the team test checklist
- [docs/technical-flow.md](docs/technical-flow.md) — how the parts fit together
- [docs/business-flow.md](docs/business-flow.md) — what the product is for
