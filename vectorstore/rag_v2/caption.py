"""VLM captioning for textbook figures.

A German caption + keywords turns image retrieval into text retrieval, which
is far more reliable than matching a German question against raw pixels.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from PIL import Image

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("CAPTION_MODEL", "google/gemma-4-31b-it")
FALLBACK_MODEL = os.environ.get("CAPTION_FALLBACK", "mistralai/mistral-small-3.2-24b-instruct")

PROMPT = """Du bist Redakteur eines Chemie-Schulbuchs (Klasse 9/10, Berlin).
Beschreibe die Abbildung so, dass sie über eine deutsche Volltextsuche gefunden wird.

Antworte NUR mit gültigem JSON in genau diesem Schema:
{
  "type": "diagram" | "experiment" | "graph" | "table" | "photo" | "decorative" | "icon",
  "caption": "1-2 präzise deutsche Sätze: Was zeigt die Abbildung? Nenne die wichtigsten Stoffe, Teilchen, Geräte und Beschriftungen.",
  "keywords": ["3-8 deutsche Fachbegriffe"],
  "teaches_chemistry": true,
  "confidence": 0.0
}

Regeln:
- Sei streng. Fotos von Menschen, dekorative Hintergründe, Farbverläufe, Logos, reine Schmuckbilder: type="decorative", teaches_chemistry=false.
- Ein Foto ist nur dann teaches_chemistry=true, wenn es einen chemischen Sachverhalt oder ein Experiment zeigt.
- Erfinde keine Beschriftungen, die nicht sichtbar sind.
- "caption" muss konkrete Suchbegriffe enthalten, keine Floskeln wie "Abbildung aus dem Buch"."""


def _key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    for env in (Path(".env"), Path(__file__).resolve().parent.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENROUTER_API_KEY missing")


def _data_url(path: str, max_side: int = 768) -> str:
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _caption_with(path: str, model: str, retries: int, printed: str = "") -> dict:
    prompt = PROMPT
    if printed:
        prompt += (f"\n\nDer im Buch gedruckte Bildtext lautet:\n\"{printed}\"\n"
                   "Nutze ihn als Grundlage, übernimm seine Fachbegriffe und ergänze nur, "
                   "was du im Bild tatsächlich siehst.")
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": _data_url(path)}},
            ],
        }],
        "temperature": 0.1,
        "max_tokens": 600,
    }
    headers = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8080",
        "X-Title": "Fokus Chemie RAG v2",
    }
    last = None
    for attempt in range(retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            text = r.json()["choices"][0]["message"].get("content") or ""
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                raise ValueError(f"no JSON: {text[:200]}")
            data = json.loads(m.group())
            vlm_caption = str(data.get("caption", "")).strip()
            data["caption_vlm"] = vlm_caption
            data["caption_printed"] = printed
            data["caption"] = printed or vlm_caption
            kws = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
            data["keywords"] = _merge_keywords(kws, printed, limit=12)
            data["type"] = str(data.get("type", "decorative")).lower()
            data["teaches_chemistry"] = bool(data.get("teaches_chemistry", False)) or bool(printed)
            data["confidence"] = float(data.get("confidence", 0) or 0)
            data["model"] = model
            return data
        except Exception as exc:
            last = exc
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(str(last))


_STOP = {"der", "die", "das", "und", "oder", "von", "zu", "im", "in", "mit", "auf",
         "für", "ist", "ein", "eine", "einer", "eines", "dem", "den", "des", "sich",
         "bei", "aus", "als", "auch", "nicht", "wird", "werden", "sind", "hat", "haben"}


def _merge_keywords(existing: list[str], text: str, limit: int = 12) -> list[str]:
    out, seen = [], set()
    for word in list(existing) + re.findall(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9-]{3,}", text or ""):
        w = word.strip()
        key = w.lower()
        if key in _STOP or key in seen:
            continue
        seen.add(key)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def _infer_type(caption: str) -> str:
    c = caption.lower()
    if any(w in c for w in ("schema", "diagramm", "modell", "aufbau", "kreislauf", "fließschema", "grafik")):
        return "diagram"
    if "tabelle" in c:
        return "table"
    if any(w in c for w in ("verlauf", "messung", "kurve", "diagramm")):
        return "graph"
    if any(w in c for w in ("versuch", "experiment", "reaktion")):
        return "experiment"
    return "photo"


def _from_printed(printed: str, model: str, error: str = "") -> dict:
    return {"type": _infer_type(printed), "caption": printed, "caption_vlm": "",
            "caption_printed": printed, "keywords": _merge_keywords([], printed),
            "teaches_chemistry": True, "confidence": 0.5, "model": model, "error": error}


def caption_one(path: str, printed: str = "", model: str = DEFAULT_MODEL, retries: int = 3) -> dict:
    try:
        return _caption_with(path, model, retries, printed)
    except Exception as first:
        if model != FALLBACK_MODEL:
            try:
                return _caption_with(path, FALLBACK_MODEL, 2, printed)
            except Exception as second:
                if printed:
                    return _from_printed(printed, FALLBACK_MODEL, str(second))
                return {"type": "error", "caption": "", "keywords": [],
                        "teaches_chemistry": False, "confidence": 0.0,
                        "error": str(second), "model": FALLBACK_MODEL}
        if printed:
            return _from_printed(printed, model, str(first))
        return {"type": "error", "caption": "", "keywords": [], "teaches_chemistry": False,
                "confidence": 0.0, "error": str(first), "model": model}


def caption_images(images: list[dict], out_path: str, workers: int = 6,
                   model: str = DEFAULT_MODEL) -> list[dict]:
    """Caption all images, resuming from *out_path* if it already exists."""
    out = Path(out_path)
    cache: dict[str, dict] = {}
    if out.exists():
        for item in json.loads(out.read_text(encoding="utf-8")):
            cache[item["image_path"]] = item

    todo = [im for im in images if im["image_path"] not in cache]
    print(f"Captioning {len(todo)} images ({len(cache)} cached) with {model} ...")

    results = dict(cache)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(caption_one, im["image_path"],
                               im.get("caption_printed", ""), model): im for im in todo}
        done = 0
        for fut in as_completed(futures):
            im = futures[fut]
            data = fut.result()
            item = {**im, **data}
            results[item["image_path"]] = item
            done += 1
            if done % 10 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)}")
                out.write_text(json.dumps(list(results.values()), ensure_ascii=False, indent=1),
                               encoding="utf-8")

    ordered = [results[im["image_path"]] for im in images]
    out.write_text(json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8")
    return ordered
