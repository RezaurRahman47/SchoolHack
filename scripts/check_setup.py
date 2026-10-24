"""Fast pre-demo check. No heavy imports.

    python3 scripts/check_setup.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VS = ROOT / "vectorstore"
APP = ROOT / "backend-python"
ok = True


def line(label: str, good: bool, detail: str = "", fatal: bool = False) -> None:
    global ok
    mark = "✓" if good else ("✗" if fatal else "!")
    print(f"  {mark} {label}{(' — ' + detail) if detail else ''}")
    if fatal and not good:
        ok = False


def main() -> int:
    print("== Pre-demo check ==")

    line("vectorstore/.venv-v2", (VS / ".venv-v2/bin/python").exists(), fatal=True)
    line("backend-python/.venv", (APP / ".venv/bin/python").exists(), fatal=True)

    chroma = VS / "processed_data_v2/chroma/chroma.sqlite3"
    line("v2 index (chroma.sqlite3)", chroma.exists(), str(chroma.relative_to(ROOT)), fatal=True)

    images = VS / "processed_data_v2/images"
    n_img = len(list(images.glob("*.jpg"))) if images.exists() else 0
    line("indexed images", n_img >= 150, f"{n_img} JPGs", fatal=True)

    chunks = VS / "processed_data_v2/text_chunks.json"
    line("text chunks manifest", chunks.exists(), fatal=True)

    env = VS / ".env"
    key = ""
    if env.exists():
        for raw in env.read_text(encoding="utf-8").splitlines():
            if raw.startswith("OPENROUTER_API_KEY="):
                key = raw.split("=", 1)[1].strip()
    key_ok = bool(key) and "..." not in key and len(key) > 20
    line("OPENROUTER_API_KEY", key_ok, "set in vectorstore/.env" if key_ok else
         "MISSING — RAG answers need a key (app falls back without it)")

    cache = Path.home() / ".cache/huggingface/hub"
    for name in ("models--google--embeddinggemma-2", "models--BAAI--bge-reranker-v2-m3"):
        d = cache / name
        files = list(d.rglob("model.safetensors")) if d.exists() else []
        size = max((f.stat().st_size for f in files), default=0)
        line(name.replace("models--", ""), size > 100_000_000,
             f"{size / 1e9:.1f} GB cached" if size else "not cached — run scripts/download_models.py")

    data_dir = APP / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / ".write_test").write_text("ok")
        (data_dir / ".write_test").unlink()
        line("SQLite directory writable", True, str(data_dir.relative_to(ROOT)))
    except Exception as exc:
        line("SQLite directory writable", False, str(exc), fatal=True)

    print()
    if ok:
        print("Ready. Run ./run_demo.sh")
        print("Demo login: admin / admin")
    else:
        print("Not ready — fix the ✗ items above, then rerun this check.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
