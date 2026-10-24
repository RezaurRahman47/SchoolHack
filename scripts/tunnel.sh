#!/usr/bin/env bash
# Public URL for the SchoolHack app (port 8000) during the demo.
# Do NOT expose 8080: the RAG API has no auth, and the app calls it locally.
set -e
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is missing. Install: brew install cloudflared"
  exit 1
fi
echo "Opening a public tunnel to http://localhost:8000 ..."
echo "Share the https://....trycloudflare.com URL. Login: admin / admin"
exec cloudflared tunnel --url http://localhost:8000
