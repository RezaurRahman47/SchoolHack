"""
Chemie RAG — Ingest Pipeline
Run this script to process the PDF, generate embeddings, and build the vector store.
Usage: python ingest.py
"""

import os
import sys
import time
from pathlib import Path

from pdf_processor import PDFProcessor
from vector_engine import VectorStoreEngine


def main():
    # ─── Configuration ────────────────────────────────────
    PDF_DIR = Path("Inputs/unit-1")
    OUTPUT_DIR = Path("processed_data")
    VECTOR_DB_DIR = Path("vector_db")
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 80

    # Find PDF files
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {PDF_DIR}")
        sys.exit(1)

    print(f"{'=' * 60}")
    print(f"  🧪 Chemie RAG — Ingest Pipeline")
    print(f"  📚 Found {len(pdf_files)} PDF file(s)")
    print(f"{'=' * 60}\n")

    # ─── Process each PDF ─────────────────────────────────
    all_text_chunks = []
    all_image_chunks = []

    for pdf_path in pdf_files:
        print(f"\n📄 Processing: {pdf_path.name}")
        print(f"   Size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB\n")

        with PDFProcessor(str(pdf_path), str(OUTPUT_DIR)) as processor:
            # Extract text
            start = time.time()
            text_chunks = processor.extract_text_chunks(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
            )
            print(f"   ⏱ Text extraction: {time.time() - start:.1f}s")

            # Extract images
            start = time.time()
            image_chunks = processor.extract_images(min_size=100)
            print(f"   ⏱ Image extraction: {time.time() - start:.1f}s")

            all_text_chunks.extend(text_chunks)
            all_image_chunks.extend(image_chunks)

    print(f"\n{'─' * 60}")
    print(f"📊 Extraction complete:")
    print(f"   Text chunks:  {len(all_text_chunks)}")
    print(f"   Image chunks: {len(all_image_chunks)}")
    print(f"{'─' * 60}\n")

    # ─── Build Vector Store ───────────────────────────────
    print("🔧 Initializing vector store...")
    engine = VectorStoreEngine(persist_dir=str(VECTOR_DB_DIR))

    # Index text chunks
    if all_text_chunks:
        start = time.time()
        engine.index_text_chunks(all_text_chunks, batch_size=16)
        print(f"   ⏱ Text indexing: {time.time() - start:.1f}s")

    # Index images
    if all_image_chunks:
        start = time.time()
        engine.index_image_chunks(all_image_chunks, batch_size=4)
        print(f"   ⏱ Image indexing: {time.time() - start:.1f}s")

    # ─── Stats ────────────────────────────────────────────
    stats = engine.get_stats()
    print(f"\n{'=' * 60}")
    print(f"  ✅ INGESTION COMPLETE")
    print(f"  📦 Total chunks in vector store: {stats['total_chunks']}")
    print(f"     Text:   {stats['text_chunks']}")
    print(f"     Images: {stats['image_chunks']}")
    print(f"  💾 Stored in: {stats['persist_dir']}")
    print(f"{'=' * 60}\n")

    # Quick test search
    print("🔍 Quick test search: 'Atome'...")
    results = engine.search("Atome", n_results=3)
    for r in results:
        print(f"   [{r['relevance']:.2f}] Page {r['metadata'].get('page', '?')}: {r['text'][:100]}...")

    print("\n✓ Ready! Run `python server.py` to start the web application.\n")


if __name__ == "__main__":
    main()
