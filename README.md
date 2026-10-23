# School Hack

Kid-friendly Grade 9 chemistry learning app for the Berlin curriculum, with German and English UI content. This repository includes both a standalone browser version and an earlier FastAPI version with SQLite persistence and student/teacher portals.

## Project versions

| Path | Description |
|---|---|
| `website/` | Current standalone website. Open `website/index.html` directly or serve it with VS Code Live Server. No build step. Demo login: `admin / admin`. |
| `backend-python/` | FastAPI application with student and teacher portals, adaptive chemistry tests, local SQLite storage, and teacher analytics. |

## Run the Python app on Windows

Requires Python 3.10 or newer.

1. Open a terminal in `backend-python/`.
2. Run `run.bat` (or double-click it in File Explorer). The script creates a local virtual environment, installs dependencies, and starts Uvicorn.
3. Open [http://localhost:8000](http://localhost:8000).
4. Sign in to either portal with `admin / admin`.

The SQLite database is created under `backend-python/data/` on first startup. For optional Claude-generated hints and teacher summaries, copy `.env.example` to `.env` and configure `ANTHROPIC_API_KEY`. Without a key, built-in hints and summaries remain available.

## Run the standalone website

Open `website/index.html` in a browser, or use VS Code Live Server. User progress is stored in the browser's local storage. Its AI hints use built-in fallbacks when the page is run locally.

## Workflows and architecture

- [Business workflow](docs/business-flow.md): student learning journey and teacher gap-analysis process.
- [Technical workflow](docs/technical-flow.md): app architecture, request sequences, persistence, and component responsibilities.

## Main features

- Adaptive 30-question chemistry tests across 15 skills, with repeat rounds for incorrect answers.
- Code-based grading, per-skill mastery updates, feedback, and optional Socratic tutor hints.
- Teacher dashboard with class analytics and an explainable gap-finder workflow.
- Responsive UI and installable PWA for the Python version.

For additional backend details and the team test checklist, see [backend-python/README.md](backend-python/README.md).
