"""
Chemie RAG — PDF Processor
Extracts text chunks and images from PDF pages using PyMuPDF.
Designed for the Fokus Chemie textbook (9./10. Schuljahr).
"""

import fitz  # PyMuPDF
import os
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TextChunk:
    """A chunk of text extracted from the PDF."""
    chunk_id: str
    text: str
    page_number: int
    chapter: str = ""
    section: str = ""
    chunk_type: str = "text"  # text, heading, definition, experiment
    metadata: dict = field(default_factory=dict)


@dataclass
class ImageChunk:
    """An image extracted from the PDF."""
    chunk_id: str
    image_path: str
    page_number: int
    caption: str = ""
    width: int = 0
    height: int = 0
    chapter: str = ""
    metadata: dict = field(default_factory=dict)


class PDFProcessor:
    """Extracts and chunks content from chemistry PDF textbooks."""

    # Common chemistry section/topic patterns in German
    HEADING_PATTERNS = [
        r'^\d+\.\d+',           # e.g., "1.1 Atombau"
        r'^Kapitel\s+\d+',      # e.g., "Kapitel 1"
        r'^Versuch',            # Experiment/Versuch
        r'^Aufgabe',            # Exercise/Aufgabe
        r'^Merke',              # Remember/Merke
        r'^Definition',         # Definition
        r'^Zusammenfassung',    # Summary
    ]

    def __init__(self, pdf_path: str, output_dir: str = "processed_data"):
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.doc = fitz.open(pdf_path)

    def _generate_id(self, content: str, page: int) -> str:
        """Generate a deterministic ID for a chunk."""
        raw = f"{content[:100]}_{page}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _classify_chunk(self, text: str) -> str:
        """Classify what type of content a chunk is."""
        text_lower = text.lower().strip()
        if any(kw in text_lower for kw in ['versuch', 'experiment', 'durchführung', 'beobachtung']):
            return "experiment"
        if any(kw in text_lower for kw in ['merke', 'definition', 'merksatz']):
            return "definition"
        if any(kw in text_lower for kw in ['aufgabe', 'übung']):
            return "exercise"
        if re.match(r'^\d+(\.\d+)*\s', text_lower):
            return "heading"
        return "text"

    def _detect_chapter(self, text: str, current_chapter: str) -> str:
        """Try to detect chapter/section from text."""
        match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)', text.strip())
        if match:
            return f"{match.group(1)} {match.group(2)[:60]}"
        return current_chapter

    def extract_text_chunks(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
        min_chunk_length: int = 40
    ) -> list[TextChunk]:
        """Extract text from PDF and split into overlapping chunks."""
        chunks: list[TextChunk] = []
        current_chapter = ""

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text("text")

            if not text or len(text.strip()) < min_chunk_length:
                continue

            # Clean text
            text = self._clean_text(text)

            # Detect chapter/section
            lines = text.split('\n')
            for line in lines[:5]:
                new_chapter = self._detect_chapter(line, current_chapter)
                if new_chapter != current_chapter:
                    current_chapter = new_chapter
                    break

            # Split into chunks with overlap
            page_chunks = self._split_text(
                text, chunk_size, chunk_overlap, min_chunk_length
            )

            for chunk_text in page_chunks:
                chunk_type = self._classify_chunk(chunk_text)
                chunk_id = self._generate_id(chunk_text, page_num + 1)
                chunks.append(TextChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    page_number=page_num + 1,
                    chapter=current_chapter,
                    chunk_type=chunk_type,
                    metadata={
                        "source": os.path.basename(self.pdf_path),
                        "total_pages": len(self.doc),
                    }
                ))

        print(f"✓ Extracted {len(chunks)} text chunks from {len(self.doc)} pages")
        return chunks

    def extract_images(self, min_size: int = 100) -> list[ImageChunk]:
        """Extract images from PDF pages."""
        image_chunks: list[ImageChunk] = []

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = self.doc.extract_image(xref)
                    if not base_image:
                        continue

                    image_bytes = base_image["image"]
                    image_ext = base_image.get("ext", "png")
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)

                    # Skip tiny images (icons, bullets, etc.)
                    if width < min_size or height < min_size:
                        continue

                    # Save image
                    img_filename = f"page{page_num + 1}_img{img_index}.{image_ext}"
                    img_path = self.images_dir / img_filename
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    # Try to find nearby caption text
                    caption = self._find_image_caption(page, img_index)

                    chunk_id = self._generate_id(img_filename, page_num + 1)
                    image_chunks.append(ImageChunk(
                        chunk_id=chunk_id,
                        image_path=str(img_path),
                        page_number=page_num + 1,
                        caption=caption,
                        width=width,
                        height=height,
                        metadata={
                            "source": os.path.basename(self.pdf_path),
                            "format": image_ext,
                        }
                    ))

                except Exception as e:
                    print(f"  ⚠ Could not extract image {img_index} on page {page_num + 1}: {e}")

        print(f"✓ Extracted {len(image_chunks)} images from {len(self.doc)} pages")
        return image_chunks

    def _find_image_caption(self, page, img_index: int) -> str:
        """Attempt to find a caption near an image."""
        text = page.get_text("text")
        lines = text.split('\n')
        # Look for lines starting with "Abb." or "Bild" (German figure captions)
        for line in lines:
            stripped = line.strip()
            if re.match(r'^(Abb\.|Bild|Abbildung|Fig\.)\s*\d*', stripped):
                return stripped
        return ""

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove page headers/footers (common patterns)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        # Remove very short orphan lines
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 2 or stripped == '':
                cleaned.append(line)
        return '\n'.join(cleaned).strip()

    def _split_text(
        self, text: str, chunk_size: int, overlap: int, min_length: int
    ) -> list[str]:
        """Split text into overlapping chunks, trying to break at sentence boundaries."""
        if len(text) <= chunk_size:
            return [text] if len(text) >= min_length else []

        chunks = []
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 1 <= chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if len(current_chunk) >= min_length:
                    chunks.append(current_chunk)
                # Start new chunk with overlap from end of previous
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para

                # If single paragraph is too long, split by sentences
                if len(current_chunk) > chunk_size * 1.5:
                    sentences = re.split(r'(?<=[.!?])\s+', current_chunk)
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 1 <= chunk_size:
                            current_chunk += (" " if current_chunk else "") + sent
                        else:
                            if len(current_chunk) >= min_length:
                                chunks.append(current_chunk)
                            current_chunk = sent

        if current_chunk and len(current_chunk) >= min_length:
            chunks.append(current_chunk)

        return chunks

    def close(self):
        self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
