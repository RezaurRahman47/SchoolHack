# School Hack – v1

Adaptive chemistry tutor for **Klasse 9 in Berlin** (Rahmenlehrplan Berlin-Brandenburg).
Combines the three ideas of Khanmigo (AI tutor), ALEKS (adaptive path) and Carnegie Learning / MATHia
(mastery tracking) in one Python web app with separate student and teacher portals.

## Start it (laptop)

Needs Python 3.10+.

**Mac / Linux**
```bash
./run.sh
```
**Windows** – double-click `run.bat`

Then open **http://localhost:8000**.

Login for both portals: **admin / admin**

### AI tutor

The AI tutor page at `/student/tutor` answers chemistry, biology, physics and
mathematics questions. It works out of the box with one OpenRouter key:

```bash
cp .env.example .env     # then put OPENROUTER_API_KEY=sk-or-... into .env
```

The chat, the Socratic hints and the teacher summary all go to OpenRouter — the
request goes straight to the model, with nothing in front of it. Chemistry
practice questions still come from the deterministic question engine.

**Optional:** the RAG service on port 8080 serves the textbook extras (figures,
quiz/flashcard/statement generators). It never sits in front of the chat, and
chat works with or without it.

```bash
cd ../vectorstore
./run.sh
```

The RAG URL is configurable, so moving it to a VPS later needs no code change:
`RAG_BASE=https://rag.example.com/api` in `.env`. Health check:
`curl http://localhost:8080/api/status`.

## Use it on your phone

1. Start the app on your laptop (above). The script prints a line like `Handy: http://192.168.1.23:8000`.
2. Phone and laptop on the **same Wi-Fi** → open that address on the phone.
3. Install it like an app:
   - **iPhone (Safari):** Share → *Zum Home-Bildschirm*
   - **Android (Chrome):** ⋮ → *App installieren*
   - **Laptop (Chrome/Edge):** install icon in the address bar

For a link that works anywhere (team testing without same Wi-Fi), deploy the folder to Render / Railway / Fly.io
with the start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, or run `ngrok http 8000`.

## The key

```bash
cp .env.example .env     # then put your key in
```

| Key | What it turns on |
|---|---|
| `OPENROUTER_API_KEY` | **the only key the app uses**: KI-Tutor chat, Socratic hints, teacher summary |

`CHAT_MODEL` overrides the chat model (default `google/gemma-4-31b-it`).
Hints and the teacher summary fall back to built-in text when the model is
unreachable or the key is missing.

## What's in v1

| Area | Features |
|---|---|
| Login | Separate student and teacher portals, sessions, role check (a student can't open the teacher pages) |
| Student | Subject picker (Chemie live; Mathe, Bio, Physik "bald"), skill graph with mastery colours, test history |
| Test | 30 questions across 25 skills · pass at 20/30 · wrong answers come back in repeat rounds until all are correct · progress bar · "Tipp vom Tutor" per question |
| Grading | Done in code, never by the LLM. Recognises typical mistakes (sign errors, multiply vs divide, mL vs L, alkene vs alkane formula, unbalanced ion charges) and explains them |
| Adaptive | Each answer updates per-skill mastery (Elo-style); new tests are weighted toward weak skills |
| Teacher | KPIs, green/red score bars with pass line, pass/fail doughnut, right-vs-wrong per skill, weekly trend, mastery heatmap, class filter 9a/9b |
| Lücken-Agent | 5-step workflow: load data → detect weak skills → trace root causes in the prerequisite graph → form support groups → recommend actions |
| Mobile | Responsive layout + installable PWA, all assets bundled (no CDN needed) |

Topics covered (Klasse 9), in curriculum order: Unit 1 *Klare Verhältnisse – Quantitative Betrachtungen*
(Stoffmenge, molare Masse, Konzentration), Unit 2 *Säuren und Laugen – echt ätzend*, Unit 3
*Kohlenwasserstoffe – vom Campinggas zum Superbenzin*, Unit 4 *Alkohole – vom Holzgeist zum Glycerin*,
Unit 5 *Organische Säuren – Salatsauce, Entkalker & Co* and Unit 6 *Ester – Vielfalt der Produkte aus
Alkoholen und Säuren*. The teacher dashboard ships with a demo class of 24 fictional students so the
charts aren't empty.

## Project layout

```
app/
  main.py        routes (FastAPI)
  questions.py   skill graph + 30 question templates + grading
  db.py          SQLite storage + demo class
  agent.py       teacher gap-finder agent
  chat_llm.py    in-app chat model (OpenRouter) — the tutor without the RAG server
  vectorstore.py optional RAG/textbook client (sources + figures)
  llm.py         hints + teacher summary on OpenRouter (same key as chat)
  templates/     Jinja2 HTML pages
  static/        Tailwind CSS, Chart.js, fonts, icons, PWA files
```

Reset all data: delete the `data/` folder and restart.

## Team test checklist

- [ ] Student login → Chemie → start test → answer some wrong → submit → repeat round shows only the wrong ones
- [ ] Score ≥ 20 shows "Bestanden", < 20 "Noch nicht bestanden"
- [ ] Skill graph colours change after a test
- [ ] "Tipp vom Tutor" gives a hint without revealing the answer on the first try
- [ ] Teacher login → charts load → 9a / 9b filter → "Analyse starten" shows gaps and groups
- [ ] Student login cannot open `/teacher`
- [ ] Phone: layout readable, app installs to home screen
- [ ] KI-Tutor answers a chemistry question with the RAG server **stopped**
- [ ] KI-Tutor answers a chemistry question with the RAG server **running** (same answer — chat never waits for it)
- [ ] Note any wrong chemistry in a question (screenshot + test number)

## Known limits of v1

- One shared demo account per portal (admin/admin) – no real user management yet
- Mathe, Biologie, Physik are placeholders
- Questions come from templates; model-generated question banks are the next step
