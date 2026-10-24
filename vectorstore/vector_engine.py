"""
Chemie RAG — Vector Store Engine
Uses EmbeddingGemma 2 for multimodal embeddings (text + images)
and ChromaDB as the vector database.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Optional
from PIL import Image

import chromadb
from chromadb.config import Settings

from pdf_processor import TextChunk, ImageChunk


class VectorStoreEngine:
    """
    Manages the vector store with EmbeddingGemma 2 embeddings.
    Supports both text and image embeddings in a unified space.
    """

    COLLECTION_NAME = "chemie_rag"

    def __init__(
        self,
        persist_dir: str = "vector_db",
        embedding_dim: int = 768,
        use_gpu: bool = False,
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim
        self.model = None
        # Detect best available device
        import torch
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_dir / "chroma"),
            settings=Settings(anonymized_telemetry=False),
        )

    def load_model(self):
        """Load multimodal embedding model."""
        if self.model is not None:
            return

        print("⏳ Loading multimodal embedding model (clip-ViT-B-32)...")
        from sentence_transformers import SentenceTransformer

        try:
            self.model = SentenceTransformer(
                "clip-ViT-B-32",
                device=self.device,
            )
            print(f"✓ Multimodal model loaded on {self.device}")
        except Exception as e:
            print(f"⚠ Loading on {self.device} failed ({e}), using CPU...")
            self.device = "cpu"
            self.model = SentenceTransformer(
                "clip-ViT-B-32",
                device="cpu",
            )
            print("✓ Multimodal model loaded on cpu")


    def get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        return self.chroma_client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for text chunks."""
        self.load_model()
        if hasattr(self.model, "encode_document"):
            embeddings = self.model.encode_document(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        else:
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        self.load_model()
        if hasattr(self.model, "encode_query"):
            embedding = self.model.encode_query(
                [query],
                normalize_embeddings=True,
            )
        else:
            embedding = self.model.encode(
                [query],
                normalize_embeddings=True,
            )
        return embedding[0].tolist()

    def embed_images(self, image_paths: list[str]) -> list[list[float]]:
        """Generate embeddings for images."""
        self.load_model()
        images = []
        for path in image_paths:
            try:
                img = Image.open(path).convert("RGB")
                images.append(img)
            except Exception as e:
                print(f"  ⚠ Could not load image {path}: {e}")

        if not images:
            return []

        if hasattr(self.model, "encode_document"):
            embeddings = self.model.encode_document(
                images,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        else:
            embeddings = self.model.encode(
                images,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return embeddings.tolist()


    def index_text_chunks(self, chunks: list[TextChunk], batch_size: int = 32):
        """Index text chunks into the vector store."""
        collection = self.get_or_create_collection()

        print(f"⏳ Indexing {len(chunks)} text chunks...")

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.text for c in batch]
            ids = [f"text_{c.chunk_id}" for c in batch]
            metadatas = [
                {
                    "type": "text",
                    "page": c.page_number,
                    "chapter": c.chapter,
                    "chunk_type": c.chunk_type,
                    "source": c.metadata.get("source", ""),
                }
                for c in batch
            ]

            embeddings = self.embed_text(texts)

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            print(f"  ✓ Indexed batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}")

        print(f"✓ All {len(chunks)} text chunks indexed")

    def index_image_chunks(self, chunks: list[ImageChunk], batch_size: int = 8):
        """Index image chunks into the vector store."""
        collection = self.get_or_create_collection()

        print(f"⏳ Indexing {len(chunks)} image chunks...")

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            paths = [c.image_path for c in batch]
            ids = [f"img_{c.chunk_id}" for c in batch]

            # Caption text serves as the document for retrieval context
            documents = [
                c.caption if c.caption else f"Bild auf Seite {c.page_number}"
                for c in batch
            ]

            metadatas = [
                {
                    "type": "image",
                    "page": c.page_number,
                    "chapter": c.chapter,
                    "image_path": c.image_path,
                    "caption": c.caption,
                    "width": c.width,
                    "height": c.height,
                }
                for c in batch
            ]

            embeddings = self.embed_images(paths)

            if embeddings:
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
            print(f"  ✓ Indexed image batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}")

        print(f"✓ All {len(chunks)} image chunks indexed")

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_type: Optional[str] = None,
    ) -> list[dict]:
        """Search the vector store for relevant content."""
        collection = self.get_or_create_collection()

        query_embedding = self.embed_query(query)

        where_filter = None
        if filter_type:
            where_filter = {"type": filter_type}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        if results and results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                entry = {
                    "id": results["ids"][0][idx],
                    "text": results["documents"][0][idx] if results["documents"] else "",
                    "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
                    "distance": results["distances"][0][idx] if results["distances"] else 0.0,
                    "relevance": 1.0 - (results["distances"][0][idx] if results["distances"] else 0.0),
                }
                formatted.append(entry)

        return formatted

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        collection = self.get_or_create_collection()
        count = collection.count()

        # Get type breakdown
        text_count = 0
        image_count = 0
        try:
            all_items = collection.get(include=["metadatas"])
            for meta in all_items["metadatas"]:
                if meta.get("type") == "text":
                    text_count += 1
                elif meta.get("type") == "image":
                    image_count += 1
        except Exception:
            pass

        return {
            "total_chunks": count,
            "text_chunks": text_count,
            "image_chunks": image_count,
            "collection_name": self.COLLECTION_NAME,
            "persist_dir": str(self.persist_dir),
        }

    def is_indexed(self) -> bool:
        """Check if any data has been indexed."""
        try:
            collection = self.get_or_create_collection()
            return collection.count() > 0
        except Exception:
            return False
