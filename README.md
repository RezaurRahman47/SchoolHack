# School Hack — ChemTutor

Chemistry practice app for **Klasse 9 (Berlin)** with a student portal, a KI-Tutor
chat and a teacher dashboard. Python + FastAPI + SQLite: one program and one
OpenRouter key.

> This file only explains **how to start the app on your own laptop**, step by step.
> If you have never started a Python project before, follow the steps in order and
> copy the commands exactly as they are written.

## Put it online (free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/RezaurRahman47/SchoolHack/tree/safick_v1)

Click the button, sign in to Render with GitHub, paste your `OPENROUTER_API_KEY`
when asked (optional) and click **Deploy**. After 2–4 minutes you get a public link
such as `https://schoolhack.onrender.com` that anyone can open. It deploys the
branch `safick_v1` with the settings in [`render.yaml`](render.yaml); details and
the manual way are in [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md).

---

## Before you start

You need two things.

**1. Python 3.10 or newer.** Open a terminal and check:

```bash
python3 --version                # macOS / Linux
python --version                 # Windows
```

If it prints `Python 3.10` (or higher), you are ready. If it says
*command not found*, install Python first:

- **macOS:** `brew install python@3.12` — or download it from <https://www.python.org/downloads/>
- **Windows:** download it from <https://www.python.org/downloads/> and **tick
  "Add Python to PATH"** during the installation. Then close the terminal, open a
  new one and run `python --version` again.

> On Windows the command is `python`, not `python3`. Every step below shows both.

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
**Download ZIP**, unzip it and open a terminal in the unzipped folder (for example
`SchoolHack-main`) instead of running the two lines above.

## Step 2 — Go into the app folder

```bash
cd backend-python
```

All the following commands are typed inside this folder. If you type `ls`
(macOS/Linux) or `dir` (Windows) you should see `app`, `requirements.txt` and
`run.sh`.

## Step 3 — Create a virtual environment

A *virtual environment* is a private box for this project's packages. It keeps the
project separate from the rest of your computer, and you only create it once:

```bash
python3 -m venv .venv            # macOS / Linux
```

```powershell
python -m venv .venv             # Windows
```

This creates the folder `backend-python/.venv` — you never have to touch it.

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

You are still in the `backend-python` folder. Create your personal settings file
from the example file:

```bash
cp .env.example .env             # macOS / Linux
```

```powershell
copy .env.example .env           # Windows
```

The full path of this new file is:

```
SchoolHack/backend-python/.env
```

Open it in a text editor and put your key behind `OPENROUTER_API_KEY=`:

- `code .env` — VS Code
- `open -e .env` — TextEdit (macOS)
- `notepad .env` — Notepad (Windows)

Or edit it right in the terminal: `nano .env`, type or paste the line, then press
`Ctrl + O`, `Enter` and `Ctrl + X`.

The line must look exactly like this, only with your own key instead of `...`:

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

**German or English:** use the **DE | EN** switch at the top right (on a phone:
**Profil → Sprache**, or **Settings**). Everything switches, including test
questions, answers and the AI tutor's replies. The choice is remembered.

---

## German and English (for developers)

The app is written in German. English is added in the browser, so templates,
questions and grading stay as they are:

| File | What it does |
|---|---|
| `backend-python/app/static/i18n/en.js` | German → English dictionary, plus patterns for text with numbers or names |
| `backend-python/app/static/i18n.js` | Swaps the shown text (also text added later by JavaScript, popups and chart labels). Form values stay German, so grading is unchanged |
| `backend-python/app/i18n.py` | Remembers the language (cookie) and asks the AI model to answer in English |

**Added new German text?** Add it to `en.js`: the exact German text as the key, the
English as the value. To find anything missing, switch to EN, open the page and run
`SH_I18N.missing()` in the browser console.

---

## Starting it again later

Steps 2–6 (venv, packages, key) are one-time only. To start the app another day,
open a new terminal and run:

```bash
cd SchoolHack/backend-python        # the folder you cloned or unzipped
source .venv/bin/activate           # .venv\Scripts\activate   on Windows
python -m uvicorn app.main:app --reload --port 8000
```

If you are already inside the project folder, skip the first line and use
`cd backend-python`.

---

## Shortcut: one script instead of steps 3–5 and 7

The project also ships start scripts that create the venv, install the packages
and create `.env` from the example:

```bash
./run.sh                         # from the backend-python folder (macOS / Linux)
```

On Windows, double-click `run.bat`.

You still add your key once (Step 6) — both scripts print a reminder if the key is
still missing.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `python3: command not found` | Python is not installed — or you are on Windows, where the command is `python` (see **Before you start**) |
| `command not found: uvicorn` | The venv is not active → `source .venv/bin/activate`, or always use `python -m uvicorn ...` |
| Chat answers *"Der KI-Tutor ist gerade nicht erreichbar."* | The key in `backend-python/.env` is missing or wrong — or the OpenRouter account has no credit |
| You cannot find `.env` | It sits next to `requirements.txt`: `SchoolHack/backend-python/.env` (Step 6) |
| `Address already in use` (port 8000) | Another program is already using port 8000 → close it, or start with `--port 8001` and open <http://localhost:8001> |
| The page looks old after an update | Hard reload the browser: `Cmd + Shift + R` (Mac) / `Ctrl + Shift + R` (Windows) |
| `ModuleNotFoundError: No module named 'app'` | You are in the wrong folder → `cd backend-python` and run the command there |

---

## Want to know more?

- [backend-python/README.md](backend-python/README.md) — the app in detail, plus the team test checklist
- [docs/technical-flow.md](docs/technical-flow.md) — how the parts fit together
- [docs/business-flow.md](docs/business-flow.md) — what the product is for
