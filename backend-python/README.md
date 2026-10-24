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

### Textbook tutor (RAG) — recommended

The chemistry chat gets its short, book-grounded answers from a local service on
port 8080. Start it in a second terminal before using the Chemie subtopics:

```bash
cd ../vectorstore
./run.sh
```

Without it, the chat falls back to the built-in "Kerninformation" for each skill
(no book passages, no images). Health check:
`curl http://localhost:8080/api/status`.

The RAG URL is configurable, so moving to a VPS later needs no code change:
`RAG_BASE=https://rag.example.com/api` in `.env`.

## Use it on your phone

1. Start the app on your laptop (above). The script prints a line like `Handy: http://192.168.1.23:8000`.
2. Phone and laptop on the **same Wi-Fi** → open that address on the phone.
3. Install it like an app:
   - **iPhone (Safari):** Share → *Zum Home-Bildschirm*
   - **Android (Chrome):** ⋮ → *App installieren*
   - **Laptop (Chrome/Edge):** install icon in the address bar

For a link that works anywhere (team testing without same Wi-Fi), deploy the folder to Render / Railway / Fly.io
with the start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, or run `ngrok http 8000`.

## Turn on the Claude tutor (optional)

Without a key, the app works fully with built-in hints. With a key, the tutor gives Socratic hints and the
teacher agent writes its summary with Claude.

```bash
cp .env.example .env     # then put your key into .env
```

## What's in v1

| Area | Features |
|---|---|
| Login | Separate student and teacher portals, sessions, role check (a student can't open the teacher pages) |
| Student | Subject picker (Chemie live; Mathe, Bio, Physik "bald"), skill graph with mastery colours, test history |
| Test | 30 questions across 15 skills · pass at 20/30 · wrong answers come back in repeat rounds until all are correct · progress bar · "Tipp vom Tutor" per question |
| Grading | Done in code, never by the LLM. Recognises typical mistakes (sign errors, multiply vs divide, mL vs L, alkene vs alkane formula, unbalanced ion charges) and explains them |
| Adaptive | Each answer updates per-skill mastery (Elo-style); new tests are weighted toward weak skills |
| Teacher | KPIs, green/red score bars with pass line, pass/fail doughnut, right-vs-wrong per skill, weekly trend, mastery heatmap, class filter 9a/9b |
| Lücken-Agent | 5-step workflow: load data → detect weak skills → trace root causes in the prerequisite graph → form support groups → recommend actions |
| Mobile | Responsive layout + installable PWA, all assets bundled (no CDN needed) |

Topics covered (Klasse 9): Säuren und Laugen, Stoffmenge und Mol, Kohlenwasserstoffe, plus the 7/8 prerequisites
(Ionen, Salzformeln). The teacher dashboard ships with a demo class of 24 fictional students so the charts aren't empty.

## Project layout

```
app/
  main.py        routes (FastAPI)
  questions.py   skill graph + 15 question templates + grading
  db.py          SQLite storage + demo class
  agent.py       teacher gap-finder agent
  llm.py         Claude API wrapper (optional)
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
- [ ] Note any wrong chemistry in a question (screenshot + test number)

## Known limits of v1

- One shared demo account per portal (admin/admin) – no real user management yet
- Mathe, Biologie, Physik are placeholders
- Questions come from templates; Claude-generated question banks are the next step
