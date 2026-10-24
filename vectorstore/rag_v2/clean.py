"""Text cleaning helpers for the Fokus Chemie PDF.

The book is an e-book PDF with a real text layer, but extraction is noisy:
soft hyphens, ligatures, private-use glyphs, thin spaces and column layouts.
Everything here is deterministic and unit-testable.
"""
from __future__ import annotations

import re
import unicodedata

LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
    "\uf6bb": "",      # private-use icon glyph
}

# Characters that should become a normal space.
SPACES = {
    "\u00a0", "\u2002", "\u2003", "\u2004", "\u2005", "\u2006", "\u2007",
    "\u2008", "\u2009", "\u200a", "\u202f", "\u205f", "\u3000",
}

# Private use area + control characters used as inline icons in this PDF.
_PUA = re.compile(r"[\ue000-\uf8ff\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise a raw PyMuPDF string."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)

    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)

    # Soft hyphen means "word continues here" -> join, never keep it.
    text = text.replace("\u00ad", "")
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = text.replace("\ufeff", "")

    for ch in SPACES:
        text = text.replace(ch, " ")

    text = _PUA.sub(" ", text)

    # A hyphen at a line break is a syllabification: re-join the word.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Same, but PyMuPDF sometimes already turned the break into a space.
    text = re.sub(r"(\w)- (\w)", r"\1\2", text)

    # Some icon chars leave a dangling marker before a word.
    text = text.replace("\x07", " ").replace("\x03", " ")

    text = text.replace("−", "-")  # minus sign -> ASCII for formulas
    text = _MULTISPACE.sub(" ", text)
    text = _MULTINEWLINE.sub("\n\n", text)
    return text.strip()


def clean_line(text: str) -> str:
    """Clean a single visual line, keeping it on one line."""
    text = clean_text(text)
    text = text.replace("\n", " ")
    return _MULTISPACE.sub(" ", text).strip()


def normalise_space(text: str) -> str:
    return _MULTISPACE.sub(" ", text.replace("\n", " ")).strip()


def looks_like_page_number(text: str) -> bool:
    t = text.strip()
    return bool(re.fullmatch(r"\d{1,3}", t))


def is_heading(text: str, size: float, body_size: float) -> bool:
    """Conservative heading test based on typography and textbook patterns."""
    t = normalise_space(text)
    if not t or len(t) > 140:
        return False
    if looks_like_page_number(t):
        return False
    if t.endswith((".", "!", "?", ";", ",")):
        return False
    if re.match(r"^(Exp\.|Abb\.|Bild|Tabelle|Quelle)\b", t, re.I):
        return False
    if re.match(r"^\d+(\.\d+)*\s+\S", t) and len(t) < 90:
        return True
    if re.match(r"^(Merke|Versuch|Experiment|Aufgabe|Definition|Zusammenfassung|"
                r"Auf einen Blick|Weitergedacht|Chemie erlebt)\b", t, re.I):
        return True
    if body_size and size >= body_size * 1.28 and len(t) <= 90:
        return True
    return False


def chunk_text_blocks(
    blocks: list[dict],
    target: int = 1000,
    max_size: int = 1400,
    min_size: int = 180,
    overlap: int = 140,
) -> list[dict]:
    """Merge ordered text blocks into overlapping, sentence-aligned chunks.

    Each block is ``{"text": str, "page": int, "section": str, "type": str}``.
    Chunks never start or end inside a word.
    """
    chunks: list[dict] = []
    buf: list[dict] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        text = "\n\n".join(b["text"] for b in buf).strip()
        if len(text) >= min_size:
            chunks.append({
                "text": text,
                "page": buf[0]["page"],
                "pages": sorted({b["page"] for b in buf}),
                "section": buf[0].get("section") or "",
                "chapter": buf[0].get("chapter") or "",
                "type": _chunk_type(text, buf[0].get("section", "")),
            })
        buf = []
        buf_len = 0

    for b in blocks:
        t = b["text"].strip()
        if not t:
            continue
        # Never let one chunk span two sections or two pages: this keeps
        # citations exact and stops exercise pages bleeding into summaries.
        if buf and b.get("section") and buf[-1].get("section") and b["section"] != buf[-1]["section"]:
            flush()
        if buf and b["page"] != buf[-1]["page"]:
            flush()
        add = len(t) + (2 if buf else 0)
        if buf and buf_len + add > max_size:
            prev = "\n\n".join(x["text"] for x in buf)
            flush()
            tail = _sentence_tail(prev, overlap)
            if tail:
                buf = [{"text": tail, "page": b["page"], "section": b.get("section", ""),
                        "chapter": b.get("chapter", ""), "type": "text"}]
                buf_len = len(tail)
        buf.append(b)
        buf_len += add
        if buf_len >= target:
            flush()

    flush()
    return chunks


def _sentence_tail(text: str, limit: int) -> str:
    """Last whole sentences of *text* up to *limit* chars (never mid-word)."""
    text = text.strip()
    if len(text) <= limit:
        return text
    tail = text[-limit:]
    m = re.search(r"(?<=[.!?])\s+", tail)
    if m:
        return tail[m.end():].strip()
    m = re.search(r"\s+", tail)
    return tail[m.end():].strip() if m else ""


def _chunk_type(text: str, section: str) -> str:
    blob = (section + " " + text).lower()
    if "auf einen blick" in section.lower():
        return "summary"
    if "versuch" in blob or "experiment" in blob or "durchführung" in blob:
        return "experiment"
    if "merke" in blob or "definition" in blob:
        return "definition"
    if "aufgabe" in blob or "übung" in blob:
        return "exercise"
    return "text"
