# Demo away from home — three options

Your Mac can stay at home. Pick one option for the venue laptop.

## A. Clone and run the whole stack on the venue laptop (recommended)

This is the only option that gives you a real `localhost` with RAG, SQLite and
the API, exactly like on your Mac.

```bash
git clone <your-repo-url>
cd SchoolHack

./setup.sh          # Python >= 3.10 required; installs both venvs
# put your OpenRouter key into vectorstore/.env
./run_demo.sh       # RAG :8080 + SchoolHack :8000
```

Open **http://localhost:8000** (login `admin / admin`). SQLite is seeded
automatically on first start.

The v2 index (21 MB) is committed, so **you do not need the PDF** and you do not
have to re-ingest. The two models download once (~3.8 GB). To avoid the download
at the venue, copy these folders from your Mac to the same path on the demo
laptop before the demo (USB stick works):

```
~/.cache/huggingface/hub/models--google--embeddinggemma-2
~/.cache/huggingface/hub/models--BAAI--bge-reranker-v2-m3
```

Then run `SKIP_MODELS=1 ./setup.sh` (or just skip that step if the venv exists).

## B. Use the home Mac with Tailscale + SSH port forwarding

This gives you **`localhost:8000` and `localhost:8080` on the venue laptop**,
but the processes still run on your Mac at home. Needs Tailscale on both
machines and SSH access to the Mac.

On the Mac:

```bash
# one-time: enable Remote Login in System Settings > General > Sharing
tailscale up
caffeinate -dims ./run_demo.sh
tailscale ip -4          # note the 100.x.y.z address
whoami                   # your SSH user
```

On the venue laptop (Tailscale installed and logged into the same account):

```bash
ssh -N -L 8000:localhost:8000 -L 8080:localhost:8080 <user>@<100.x.y.z>
```

Keep that SSH session open, then open **http://localhost:8000**. API requests to
`http://localhost:8080/api/...` also work through the tunnel. SQLite is on the
Mac, so the teacher dashboard/chat history is the same data.

If SSH asks for a password, either enter the Mac password or add your public key
to `~/.ssh/authorized_keys` on the Mac beforehand.

## C. Cloudflare Tunnel (browser-only, fastest to set up)

Use this if you cannot install Tailscale/SSH on the venue laptop. Only the web
app is exposed; the RAG API stays local.

On the Mac:

```bash
caffeinate -dims ./run_demo.sh
./scripts/tunnel.sh        # prints https://....trycloudflare.com
```

Open the printed URL on any device. Images work because SchoolHack proxies them
through `/api/rag-image/...`.

**Do not tunnel port 8080** — the RAG API has no authentication. The app's
server-side calls to `localhost:8080` stay on the Mac.

## Tomorrow checklist

- [ ] `./setup.sh` completed on the demo laptop
- [ ] `vectorstore/.env` contains a working `OPENROUTER_API_KEY`
- [ ] models cached (`SKIP_MODELS=1` if copied via USB)
- [ ] `./run_demo.sh` starts both servers
- [ ] open `http://localhost:8000`, login `admin/admin`
- [ ] ask the four warm-up questions once
- [ ] Wi-Fi/hotspot available; Mac not sleeping (`caffeinate`)
