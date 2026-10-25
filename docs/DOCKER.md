# 🐳 Docker setup

This is the most reproducible way to run the **KI-Tutor** and the rest of
SchoolHack when the native `setup.sh` route fails. It runs the same two services
that `run_demo.sh` starts, on Windows, macOS (Intel/Apple Silicon) and Linux:

| Compose service | Image | Host port | What it is |
|---|---|---:|---|
| `app` | `schoolhack-app:local` | **8000** | FastAPI app, student/teacher portal, `tutor.html` |
| `rag` | `schoolhack-rag:local` | **8080** | ChromaDB index + EmbeddingGemma 2 + reranker + OpenRouter |

The app reaches the RAG service inside the Compose network at
`http://rag:8080/api`; you do not need to edit any code.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2.24+)
- Internet for the first start (Python packages + ~3.8 GB models)
- ~8 GB free disk space and 8 GB RAM recommended
- An **OpenRouter API key** (`sk-or-...`). The app boots without it, but the
  KI-Tutor needs it to answer questions.

No Python, Git LFS, virtualenv or local model download is required on the host.

## 1. Get the code

```bash
# The KI-Tutor currently lives on anil-dev, NOT on main:
git clone --depth 1 --branch anil-dev https://github.com/RezaurRahman47/SchoolHack.git
cd SchoolHack
```

A plain `git clone` checks out `main`, where `backend-python/app/templates/tutor.html`
does not exist yet. Select the `anil-dev` branch on GitHub when downloading the
ZIP, or run `git checkout anil-dev` in an existing clone.

If `git clone` fails, the repository is public, so it is usually Git not being
installed or a network/proxy issue. On Windows install
[Git for Windows](https://git-scm.com/download/win), or use **Code → Download
ZIP** on GitHub and unzip it. Docker needs the project files, not a Git repo.

## 2. Add the key

```bash
cp .env.example .env
# edit .env and set OPENROUTER_API_KEY=sk-or-...
```

On Windows PowerShell: `Copy-Item .env.example .env`, then edit it with
`notepad .env`.

`vectorstore/.env` from the native setup also works; Compose reads both. The
key is passed at runtime and is **never baked into an image**.

## 3. Start

```bash
docker compose up --build
```

The first start does two slow things **once**:

1. builds the images (CPU-only PyTorch, so they stay much smaller than the
   default CUDA build);
2. downloads the two local models (~3.8 GB) into the `schoolhack_hf_models`
   Docker volume.

Watch the progress with:

```bash
docker compose logs -f rag
```

When both health checks pass, open:

- **App:** <http://localhost:8000> → login `admin` / `admin`
- **KI-Tutor:** Student portal → **KI-Tutor**
- **RAG status:** <http://localhost:8080/api/status>

Optional: warm the demo cache so the first four questions are instant:

```bash
curl -X POST http://localhost:8080/api/warmup \
  -H 'Content-Type: application/json' \
  -d '{"questions":["Was ist der pH-Wert?","Warum leitet eine Salzlösung Strom?","Was passiert bei einer Neutralisation?","Was sind Alkane?"]}'
```

> Do **not** open `backend-python/app/templates/tutor.html` directly in the
> browser. It is a Jinja template that extends `base.html` and calls
> `/api/tutor/chat`; it only works when the app is running. The same is true for
> all other templates.

Stop with `Ctrl+C` or:

```bash
docker compose down
```

Start again later (fast, models are cached):

```bash
docker compose up
```

## Everyday commands

```bash
docker compose ps                     # health/state
docker compose logs -f app rag        # logs
docker compose restart app            # just restart the app
docker compose up -d --build app      # rebuild only the app after code changes
docker compose down                   # stop, keep models + database
docker compose down -v                # stop and DELETE models + database
```

The SQLite database lives in the `schoolhack_app_data` volume, so progress and
tutor conversations survive restarts. To reset only the database:

```bash
docker compose down
docker volume rm schoolhack_app_data
docker compose up
```

## Port conflicts

Change the host ports in `.env`:

```env
APP_PORT=8010
RAG_PORT=8081
```

Then open <http://localhost:8010>. Inside the containers the ports stay
8000/8080, so `RAG_BASE` does not change.

## Offline / slow venue Wi-Fi

The models are cached in a named volume. If you already ran the stack once on a
machine, you can move the cache to another machine with a USB stick:

```bash
# On the machine that has the models:
docker run --rm \
  -v schoolhack_hf_models:/models \
  -v "$PWD":/backup \
  alpine tar czf /backup/schoolhack-hf-models.tgz -C /models .

# On the venue machine, after cloning the repo:
docker volume create schoolhack_hf_models
docker run --rm \
  -v schoolhack_hf_models:/models \
  -v "$PWD":/backup \
  alpine tar xzf /backup/schoolhack-hf-models.tgz -C /models
docker compose up
```

On Windows PowerShell use `${PWD}` instead of `$PWD`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `tutor.html` / KI-Tutor is missing after cloning | You are on `main`; the tutor lives on `anil-dev`. Run `git checkout anil-dev` or clone with `--branch anil-dev`. |
| KI-Tutor says “Der KI-Tutor ist gerade nicht erreichbar.” | `OPENROUTER_API_KEY` missing/invalid, or `rag` is not healthy. Check `docker compose logs rag`. |
| `rag` restarts forever on first start | Model download failed (offline, proxy, disk full). Re-run `docker compose up`; the download resumes. |
| `port is already allocated` | A native RAG/app is still running on 8000/8080, or another container uses the port. Set `APP_PORT`/`RAG_PORT` in `.env`. |
| App opens but everything is slow | Expected on CPU: Docker cannot use Apple Metal (MPS) or a GPU here. New RAG questions take roughly 4–12 s. Cached questions are instant. |
| `no matching manifest` / exec format | Docker Desktop must use Linux containers. On Apple Silicon it builds arm64; don't force `platform: linux/amd64` unless you need it. |
| `Cannot connect to the Docker daemon` | Start Docker Desktop first, then re-run the command. |
| Need to use the old native setup | `./setup.sh && ./run_demo.sh` still works; Docker is additive. |

## Why this fixes the teammate setup

The native flow has four independent failure points: two Python virtualenvs, the
model download, the API key location, and wiring `RAG_BASE` between the two
servers. Compose pins the Python and system dependencies, downloads the models
into a persistent volume, reads the key from one `.env`, and hardcodes the
internal `rag:8080` address. The only thing it cannot provide is your OpenRouter
credentials — those must be shared separately.
