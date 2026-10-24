"""Layout-aware extraction for the Fokus Chemie e-book PDF."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from statistics import median

import pymupdf
from PIL import Image

from .clean import clean_line, clean_text, is_heading, looks_like_page_number, normalise_space

# Feature labels that prefix a TOC entry but are not part of the title.
TOC_PREFIXES = re.compile(
    r"^(Selbst untersucht|Chemie erlebt|Methode|Auf einen Blick|Teste dich|"
    r"Weitergedacht|Erinnere dich)\s+",
    re.I,
)


def load_toc(doc: pymupdf.Document) -> list[dict]:
    """Parse the printed table of contents (PDF pages 7-9 in this edition).

    Returns entries with the printed page number and a level guess.
    """
    entries: list[dict] = []
    for pno in range(6, 9):
        lines = [clean_line(x) for x in doc[pno].get_text("text").splitlines()]
        lines = [x for x in lines if x]
        pending: list[str] = []
        for line in lines:
            if looks_like_page_number(line):
                title = " ".join(pending).strip()
                pending = []
                if not title:
                    continue
                title = TOC_PREFIXES.sub("", title).strip()
                if len(title) < 4:
                    continue
                # ALL CAPS entries are chapters; everything else is a section.
                level = 1 if title.upper() == title and len(title.split()) <= 8 else 2
                entries.append({"title": title, "printed_page": int(line), "level": level})
            else:
                pending.append(line)
    # De-duplicate while keeping order, and attach each section to its chapter.
    seen, out = set(), []
    chapter = ""
    for e in entries:
        key = (e["title"].lower(), e["printed_page"])
        if key in seen:
            continue
        seen.add(key)
        if e["level"] == 1:
            chapter = e["title"]
        e["chapter"] = chapter
        # Printed page 8 is PDF page 13 in this edition; chapters have a divider
        # page, sections start one page earlier. The window is used to stop
        # matching a sidebar title (e.g. "Gefahrenhinweise") to the appendix.
        e["pdf_page"] = e["printed_page"] + (5 if e["level"] == 1 else 4)
        out.append(e)
    return out


def _body_size(blocks: list[dict]) -> float:
    vals = []
    for b in blocks:
        if len(b["text"]) >= 40:
            vals.extend([b["size"]] * min(len(b["text"]) // 40, 8))
    return median(vals) if vals else 9.0


def _page_blocks(page: pymupdf.Page) -> list[dict]:
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        lines, sizes, bold = [], [], False
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            txt = "".join(s.get("text", "") for s in spans)
            lines.append(txt)
            sizes.extend(s.get("size", 0) for s in spans)
            bold = bold or any("Bold" in s.get("font", "") for s in spans)
        text = clean_text("\n".join(lines))
        if not text:
            continue
        x0, y0, x1, y1 = b["bbox"]
        out.append({
            "text": text,
            "size": max(sizes) if sizes else 0.0,
            "bold": bold,
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "width": x1 - x0,
        })
    return out


def _ordered_blocks(page: pymupdf.Page, blocks: list[dict]) -> list[dict]:
    """Read a two-column textbook page in the right order.

    Full-width blocks (headings, boxes, tables) split the page into horizontal
    bands; inside each band the left column is read before the right column.
    """
    mid = page.rect.width / 2
    full = [b for b in blocks if b["width"] > page.rect.width * 0.55 or (b["x0"] < mid < b["x1"] and b["width"] > mid * 0.8)]
    left = [b for b in blocks if b not in full and b["x1"] <= mid + 12]
    right = [b for b in blocks if b not in full and b["x0"] >= mid - 12]
    # Anything that fit neither bucket (wide-ish single column) joins the full tier.
    rest = [b for b in blocks if b not in full and b not in left and b not in right]
    full.extend(rest)

    full.sort(key=lambda b: (b["y0"], b["x0"]))
    left.sort(key=lambda b: (b["y0"], b["x0"]))
    right.sort(key=lambda b: (b["y0"], b["x0"]))

    ordered: list[dict] = []
    edges = [0.0] + [f["y0"] for f in full] + [page.rect.height + 1]
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        band_l = [b for b in left if lo <= b["y0"] < hi]
        band_r = [b for b in right if lo <= b["y0"] < hi]
        ordered.extend(sorted(band_l, key=lambda b: b["y0"]))
        ordered.extend(sorted(band_r, key=lambda b: b["y0"]))
        if i < len(full):
            ordered.append(full[i])
    return ordered


def _running_lines(doc: pymupdf.Document, start_page: int, end_page: int) -> set[str]:
    """Repeated header/footer lines (e.g. the chapter title on every page)."""
    counts: dict[str, int] = {}
    for pno in range(start_page, end_page + 1):
        page = doc[pno - 1]
        blocks = _page_blocks(page)
        candidates = [b for b in blocks if b["y0"] < 65 or b["y1"] > page.rect.height - 55]
        for b in candidates:
            t = normalise_space(b["text"]).lower()
            if 3 < len(t) < 90:
                counts[t] = counts.get(t, 0) + 1
    threshold = max(6, int((end_page - start_page + 1) * 0.12))
    return {t for t, n in counts.items() if n >= threshold}


_TOKEN_RE = re.compile(r"[a-zäöüß0-9]+")
_STOP = {"der", "die", "das", "und", "oder", "von", "zu", "im", "in", "mit", "auf",
         "für", "ist", "ein", "eine", "einer", "eines", "dem", "den", "des", "sich"}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1}


_SKIP_SECTIONS = {"teste dich", "weitergedacht", "aufgaben", "losungen", "lösungen",
                  "gefahrenhinweise", "sicherheitshinweise"}
_FORMULA = re.compile(r"\b(?:CH\d|H\d|O\d|SO\d|CO\d|NO\d|pH|mol|g/mol|°C|%)\b", re.I)


def _plausible_heading(text: str, size: float, body: float) -> bool:
    """Reject axis labels, formulas and figure captions before calling something a heading."""
    nt = normalise_space(text)
    if not is_heading(nt, size, body):
        return False
    letters = re.findall(r"[A-Za-zÄÖÜäöüß]", nt)
    if len(letters) < 5:
        return False
    if re.fullmatch(r"[\d\s.,%°+\-–—/()]+", nt):
        return False
    # Figure captions in this book look like "2 Fruchtester und ..." / "4 Handwärmer ...".
    if re.match(r"^\d+\s+", nt):
        return False
    words = re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", nt)
    if len(words) < 2:
        return False
    if _FORMULA.search(nt) and len(words) < 4:
        return False
    return True


def _find_title(text: str, toc: list[dict], page: int) -> tuple[dict | None, str | None]:
    """Find the TOC entry a heading block corresponds to.

    Handles both ``Title  Body text...`` in one block and headings whose
    words were re-ordered by the PDF (e.g. "echt ätzend Säuren und Laugen").
    Only entries near *page* are considered, so a sidebar such as
    "Gefahrenhinweise" does not hijack the chapter from the appendix.
    """
    low = normalise_space(text).lower()
    near = [e for e in toc if abs(page - e["pdf_page"]) <= 4]
    for e in near:
        title = normalise_space(e["title"]).lower()
        if low.startswith(title):
            return e, "prefix"
    if len(low) <= 120:
        toks = _tokens(low)
        best = None
        for e in near:
            tt = _tokens(e["title"])
            if not tt:
                continue
            score = len(toks & tt) / len(tt)
            if score >= 0.8 and len(low) <= len(normalise_space(e["title"])) + 55:
                if best is None or score > best[0]:
                    best = (score, e)
        if best:
            return best[1], "fuzzy"
    return None, None


def extract_text_chunks(
    pdf_path: str,
    toc: list[dict] | None = None,
    start_page: int = 13,
    end_page: int = 146,
    target: int = 1000,
    max_size: int = 1400,
) -> list[dict]:
    from .clean import chunk_text_blocks

    doc = pymupdf.open(pdf_path)
    toc = toc if toc is not None else load_toc(doc)
    running = _running_lines(doc, start_page, end_page)

    chapters = sorted([e for e in toc if e["level"] == 1], key=lambda e: e["pdf_page"])

    def chapter_at(p: int) -> str:
        cur = ""
        for e in chapters:
            if e["pdf_page"] <= p:
                cur = e["title"]
            else:
                break
        return cur

    all_blocks: list[dict] = []
    chapter = ""
    section = ""

    for pno in range(start_page, min(end_page, len(doc)) + 1):
        page = doc[pno - 1]
        head = page.get_text("text")[:500].lower()
        # Dedicated end-of-chapter exercise pages would otherwise pollute the
        # explanatory corpus and inherit the previous section.
        if "teste dich" in head or "weitergedacht" in head:
            continue
        chapter = chapter_at(pno)   # page map is authoritative
        blocks = _page_blocks(page)
        body = _body_size(blocks)
        ordered = _ordered_blocks(page, blocks)

        for b in ordered:
            t = b["text"]
            nt = normalise_space(t)

            if looks_like_page_number(t) or nt.lower() in running:
                continue
            if len(nt) < 2:
                continue
            # Marginal line numbers in this e-book (30, 35, 40, ...).
            if re.fullmatch(r"\d{1,3}", nt):
                continue

            matched, how = _find_title(nt, toc, pno)

            if matched and how == "prefix":
                title = normalise_space(matched["title"])
                if matched["level"] == 1:
                    chapter, section = title, title
                else:
                    chapter = matched.get("chapter") or chapter
                    section = title
                all_blocks.append({"text": title, "page": pno, "section": section,
                                   "chapter": chapter, "type": "heading"})
                if section.lower() in _SKIP_SECTIONS:
                    continue
                rest = nt[len(title):].strip(" .:–-")
                if rest:
                    all_blocks.append({"text": rest, "page": pno, "section": section,
                                       "chapter": chapter, "type": "text"})
                continue

            if matched and how == "fuzzy":
                title = normalise_space(matched["title"])
                if matched["level"] == 1:
                    chapter, section = title, title
                else:
                    chapter = matched.get("chapter") or chapter
                    section = title
                all_blocks.append({"text": title, "page": pno, "section": section,
                                   "chapter": chapter, "type": "heading"})
                continue

            if _plausible_heading(nt, b["size"], body):
                heading = nt
                # Only a genuine chapter title may change the chapter.
                if nt.upper() == nt and 2 <= len(nt.split()) <= 8:
                    chapter, section = heading, heading
                else:
                    section = heading
                all_blocks.append({"text": heading, "page": pno, "section": section,
                                   "chapter": chapter, "type": "heading"})
                continue

            if section.lower() in _SKIP_SECTIONS:
                continue

            all_blocks.append({"text": nt, "page": pno, "section": section,
                               "chapter": chapter, "type": "text"})

    # Drop headings from the body stream but keep their metadata on the chunks.
    body_blocks = [b for b in all_blocks if b["type"] != "heading"]
    chunks = chunk_text_blocks(body_blocks, target=target, max_size=max_size)
    for c in chunks:
        c["source"] = "Fokus Chemie 9/10 (Berlin/Brandenburg)"
    doc.close()
    return chunks


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def _dhash(img: Image.Image, size: int = 8) -> int:
    g = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            bits = (bits << 1) | (px[row * (size + 1) + col] > px[row * (size + 1) + col + 1])
    return bits


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _is_uniform(img: Image.Image) -> bool:
    small = img.convert("L").resize((32, 32))
    px = list(small.getdata())
    mean = sum(px) / len(px)
    var = sum((p - mean) ** 2 for p in px) / len(px)
    return var < 40  # nearly flat colour / gradient


def extract_images(
    pdf_path: str,
    out_dir: str,
    min_side: int = 200,
    max_side: int = 1024,
    jpeg_quality: int = 88,
    start_page: int = 13,
    end_page: int = 146,
) -> list[dict]:
    doc = pymupdf.open(pdf_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    seen_md5: set[str] = set()
    seen_hash: list[int] = []
    results: list[dict] = []
    counter = 0

    for pno in range(start_page, min(end_page, len(doc)) + 1):
        page = doc[pno - 1]
        page_text = page.get_text("text")
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            if not info:
                continue
            w, h = info.get("width", 0), info.get("height", 0)
            if min(w, h) < min_side:
                continue
            if w / max(h, 1) > 6 or h / max(w, 1) > 6:
                continue

            rects = page.get_image_rects(xref)
            if rects:
                r = rects[0]
                area_ratio = (r.width * r.height) / (page.rect.width * page.rect.height)
                if area_ratio > 0.72 and len(page_text) > 250:
                    continue  # full-page background behind real text

            md5 = hashlib.md5(info["image"]).hexdigest()
            if md5 in seen_md5:
                continue

            from io import BytesIO
            try:
                im = Image.open(BytesIO(info["image"])).convert("RGB")
            except Exception:
                continue
            if _is_uniform(im):
                continue
            dh = _dhash(im)
            if any(_hamming(dh, prev) <= 5 for prev in seen_hash):
                continue

            seen_md5.add(md5)
            seen_hash.append(dh)
            counter += 1
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            name = f"page{pno}_img{counter}.jpg"
            path = out / name
            im.save(path, "JPEG", quality=jpeg_quality, optimize=True)

            rect = rects[0] if rects else None
            caption = _find_caption(page, rect, _body_size(_page_blocks(page))) if rect else ""
            results.append({
                "image_path": str(path),
                "filename": name,
                "page": pno,
                "xref": xref,
                "bbox": [round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1)] if rect else None,
                "width": im.width,
                "height": im.height,
                "caption_printed": caption,
            })
    doc.close()
    return results


_TASK_VERBS = ("beschreibe", "formuliere", "erkläre", "begründe", "nenne", "erläutere",
               "berechne", "bestimme", "entwickle", "erstelle", "vergleiche", "gib",
               "notiere", "zeichne", "untersuche", "werte", "deute", "leite", "skizziere",
               "ordne", "diskutiere", "stelle", "prüfe", "begründe", "benenne")


def _looks_like_task(text: str) -> bool:
    t = text.strip()
    if re.match(r"^[A-Z]\d+\s", t):          # exercise label "B1 ...", "E1 ..."
        return True
    m = re.match(r"^\d{1,2}[\s\u2002\u2009]+([A-Za-zÄÖÜäöüß]+)", t)
    if m and m.group(1).lower() in _TASK_VERBS:
        return True
    if "(▶" in t or "Aufgabe" in t or t.lower().startswith(("im text", "in dem text")):
        return True
    if re.search(r"\b[a-c]\)\s", t):          # sub-task list "a) ... b) ..."
        return True
    # Long prompts often contain an imperative somewhere after the intro.
    if len(t) > 70 and any(re.search(rf"\b{v}\b", t.lower()) for v in _TASK_VERBS):
        return True
    return False


def _find_caption(page: pymupdf.Page, rect, body_size: float) -> str:
    """Find the printed figure caption near *rect*.

    In this book captions are 8.5 pt (body is 9.8 pt), sit directly below the
    image and start with a number, e.g. "2  Brennstoffe Holz, Steinkohle ...".
    """
    if rect is None:
        return ""
    best: tuple[float, float, str] | None = None
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        lines = b.get("lines", [])
        txt = clean_line(" ".join("".join(s.get("text", "") for s in l.get("spans", [])) for l in lines))
        # Marginal line numbers sometimes prefix a caption: "65 4 Biuretreaktion ..."
        txt = re.sub(r"^\d{1,3}\s+(?=\d{1,2}[\s\u2002\u2009]+[A-ZÄÖÜ])", "", txt)
        if not txt or len(txt) < 6 or len(txt) > 220:
            continue
        if _looks_like_task(txt):
            continue
        x0, y0, x1, y1 = b["bbox"]
        below = y0 - rect.y1
        above = rect.y0 - y1
        if not (-6 <= below <= 70 or -6 <= above <= 70):
            continue
        overlap = max(0.0, min(x1, rect.x1) - max(x0, rect.x0))
        if overlap < min(rect.width, x1 - x0) * 0.12:
            continue
        sizes = [s.get("size", 0) for l in lines for s in l.get("spans", [])]
        size = max(sizes) if sizes else body_size

        score = 0.0
        if re.match(r"^(Abb\.|Bild|Abbildung|Fig\.)\s*\d*", txt, re.I):
            score += 5
        if re.match(r"^\d{1,2}[\s\u2002\u2009]+[A-ZÄÖÜ]", txt):
            score += 4
        if size < body_size * 0.97:
            score += 2
        if 8 <= len(txt) <= 190:
            score += 1.5
        if txt.endswith((".", "!", "?")):
            score += 0.5
        if -6 <= below <= 70:
            score += 1.0
        dist = min(abs(below), abs(above))
        score += max(0.0, 2.0 - dist / 35.0)

        if best is None or score > best[0] or (score == best[0] and dist < best[1]):
            best = (score, dist, txt)

    return best[2] if best and best[0] >= 6.5 else ""
