"""Build the v2 index: cleaned text + printed/VLM image captions + image vectors."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import time
from pathlib import Path

import chromadb
from chromadb.config import Settings

from .caption import caption_images
from .embed import embed_documents, embed_images, embed_interleaved
from .extract import extract_images, extract_text_chunks, load_toc

COLLECTION = "chemie_rag_v2"


def _find_pdf(explicit: str | None) -> str:
    if explicit:
        return explicit
    hits = glob.glob(str(Path.home() / "Downloads" / "Fokus Chemie*.pdf"))
    if not hits:
        raise SystemExit("Full PDF not found; pass --pdf")
    return max(hits, key=os.path.getsize)


def _caption_body(im: dict) -> str:
    printed = (im.get("caption_printed") or "").strip()
    vlm = (im.get("caption_vlm") or "").strip()
    kws = im.get("keywords") or []
    parts = []
    if printed:
        parts.append(f"Bildtext: {printed}")
    if vlm and vlm.lower() != printed.lower():
        parts.append(vlm)
    if kws:
        parts.append("Begriffe: " + ", ".join(kws))
    if im.get("chapter"):
        parts.append("Kapitel: " + im["chapter"])
    if im.get("section"):
        parts.append("Abschnitt: " + im["section"])
    return ". ".join(p.rstrip(".") for p in parts) + "."


def _low_value(text: str) -> bool:
    """Drop safety-only blocks, tables of numbers and chart axes."""
    if not text:
        return True
    alpha = sum(ch.isalpha() for ch in text)
    if alpha / max(len(text), 1) < 0.35:
        return True
    low = text.lower()
    if len(re.findall(r"\b[HPE]\d{3}\b", text)) >= 3 and len(text) < 700:
        return True
    safety = sum(k in low for k in ("schutzbrille", "schutzhandschuhe", "laborkittel",
                                    "abzug", "entsorgung", "ghs", "vorsicht"))
    if safety >= 3 and len(text) < 700:
        return True
    if text.strip().startswith("▶") and len(text) < 300:
        return True
    return False


def _dedupe_texts(chunks: list[dict]) -> list[dict]:
    out, seen = [], set()
    for c in sorted(chunks, key=lambda x: -len(x["text"])):
        key = " ".join(c["text"].lower().split())[:220]
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return sorted(out, key=lambda x: (x["page"], x["section"]))


def build(pdf: str, out_dir: str, rebuild: bool = True, skip_caption: bool = False) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # 1. Text
    chunks = extract_text_chunks(pdf)
    chunks = [c for c in chunks if c["type"] != "exercise" and len(c["text"]) >= 120
              and not _low_value(c["text"])]
    chunks = _dedupe_texts(chunks)
    (out / "text_chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(f"Text chunks kept: {len(chunks)}")

    # 2. Images (extract + caption once)
    manifest = out / "images_manifest.json"
    captioned = out / "images_captioned.json"
    if manifest.exists():
        images = json.loads(manifest.read_text(encoding="utf-8"))
    else:
        images = extract_images(pdf, str(out / "images"))
        manifest.write_text(json.dumps(images, ensure_ascii=False, indent=1), encoding="utf-8")
    if not skip_caption and not captioned.exists():
        images = caption_images(images, str(captioned), workers=6)
    elif captioned.exists():
        images = json.loads(captioned.read_text(encoding="utf-8"))

    # 3. Attach chapter/section to images from the nearest text chunk page.
    page_meta = {}
    for c in chunks:
        p = c["page"]
        if p not in page_meta or len(c["text"]) > len(page_meta[p]["text"]):
            page_meta[p] = c

    def nearest(p: int):
        for d in range(0, 8):
            for q in (p - d, p + d):
                if q in page_meta:
                    return page_meta[q]
        return None

    kept_images = []
    for im in images:
        printed = (im.get("caption_printed") or "").strip()
        if im.get("type") == "error":
            continue
        if not (printed or (im.get("teaches_chemistry") and im.get("type") != "decorative")):
            continue
        meta = nearest(im["page"])
        im["chapter"] = meta["chapter"] if meta else ""
        im["section"] = meta["section"] if meta else ""
        kept_images.append(im)
    (out / "images_indexed.json").write_text(json.dumps(kept_images, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(f"Images kept: {len(kept_images)} / {len(images)}")

    # 4. Connect to Chroma
    client = chromadb.PersistentClient(
        path=str(out / "chroma"), settings=Settings(anonymized_telemetry=False)
    )
    if rebuild:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    def upsert(ids, embs, docs, metas):
        for i in range(0, len(ids), 64):
            col.upsert(ids=ids[i:i + 64], embeddings=embs[i:i + 64],
                       documents=docs[i:i + 64], metadatas=metas[i:i + 64])

    # 5. Text records
    text_ids, text_docs, text_metas = [], [], []
    for i, c in enumerate(chunks):
        text_ids.append(f"text_{i}")
        text_docs.append(c["text"])
        text_metas.append({
            "type": "text", "page": int(c["page"]), "chapter": c.get("chapter", ""),
            "section": c.get("section", ""), "chunk_type": c.get("type", "text"),
            "source": c.get("source", ""),
        })
    print("Embedding text chunks ...")
    text_embs = embed_documents([
        f"title: {c.get('section') or c.get('chapter') or 'Fokus Chemie'} | text: {c['text']}"
        for c in chunks
    ])
    upsert(text_ids, text_embs, text_docs, text_metas)

    # 6. Image records: caption text, interleaved (caption+image), pure image
    cap_ids, cap_docs, cap_metas, cap_texts = [], [], [], []
    mix_ids, mix_texts, mix_paths, mix_metas = [], [], [], []
    vis_ids, vis_paths, vis_metas = [], [], []
    for i, im in enumerate(kept_images):
        body = _caption_body(im)
        meta = {
            "type": "image_caption", "page": int(im["page"]),
            "chapter": im.get("chapter", ""), "section": im.get("section", ""),
            "image_path": im["image_path"], "filename": im["filename"],
            "caption": im.get("caption", ""), "caption_printed": im.get("caption_printed", ""),
            "caption_vlm": im.get("caption_vlm", ""),
            "keywords": ", ".join(im.get("keywords") or []),
            "image_type": im.get("type", ""), "teaches_chemistry": bool(im.get("teaches_chemistry")),
            "confidence": float(im.get("confidence", 0) or 0),
            "width": int(im.get("width", 0)), "height": int(im.get("height", 0)),
        }
        title = im.get("section") or im.get("chapter") or "Fokus Chemie"
        cap_ids.append(f"imgcap_{i}")
        cap_docs.append(body)
        cap_texts.append(f"title: {title} | text: {body}")
        cap_metas.append(meta)

        mix_ids.append(f"imgmix_{i}")
        mix_texts.append(f"title: {title} | text: {body} <|image|>")
        mix_paths.append(im["image_path"])
        mix_metas.append({**meta, "type": "image"})

        vis_ids.append(f"imgvis_{i}")
        vis_paths.append(im["image_path"])
        vis_metas.append({**meta, "type": "image_visual"})

    print("Embedding image captions ...")
    cap_embs = embed_documents(cap_texts)
    upsert(cap_ids, cap_embs, cap_docs, cap_metas)

    print("Embedding image+caption vectors ...")
    mix_embs = embed_interleaved(mix_texts, mix_paths)
    upsert(mix_ids, mix_embs, cap_docs, mix_metas)

    print("Embedding pure image vectors ...")
    vis_embs = embed_images(vis_paths)
    upsert(vis_ids, vis_embs, cap_docs, vis_metas)

    stats = {
        "text": len(chunks), "images": len(kept_images),
        "records": len(text_ids) + len(cap_ids) + len(mix_ids) + len(vis_ids),
        "collection": COLLECTION, "seconds": round(time.time() - t0, 1),
    }
    (out / "build_stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print("DONE", stats)
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf")
    ap.add_argument("--out", default="processed_data_v2")
    ap.add_argument("--no-rebuild", action="store_true")
    ap.add_argument("--skip-caption", action="store_true")
    a = ap.parse_args()
    build(_find_pdf(a.pdf), a.out, rebuild=not a.no_rebuild, skip_caption=a.skip_caption)
