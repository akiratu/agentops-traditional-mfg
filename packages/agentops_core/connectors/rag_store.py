"""RAG (Retrieval-Augmented Generation) knowledge base for AgentOps.

PoC scope:
- Maintain a ChromaDB collection per factory.
- Embed SOPSource documents + past RCAFinding summaries using sentence-transformers
  (local, no external API needed, fits on-prem constraint).
- Provide a `search_knowledge_base(agent_id, query, top_k)` tool callable
  by the Trace Analyzer ReAct loop.

Design notes:
- Collection name: ``factory_<factory_id>`` so knowledge is factory-scoped.
- Persistence path is ``<repo_root>/data/rag/<factory_id>`` (on-prem disk).
- Model: ``all-MiniLM-L6-v2`` (small, fast, good for English+Chinese short texts).
  Swap to ``BAAI/bge-large-zh-v1.5`` for stronger Chinese domain performance.
- Documents are chunked by paragraph; each chunk gets metadata:
  { source: "sop"|"rca", sop_source_id?, rca_finding_id?, agent_id? }.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

import chromadb
from chromadb.api.types import Include
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (can be overridden via env / pydantic-settings later)
# ---------------------------------------------------------------------------
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
DEFAULT_PERSIST_ROOT = Path(__file__).parent.parent.parent.parent.parent / "data" / "rag"
CHUNK_SIZE = 512  # characters (paragraph-level for SOPs)
CHUNK_OVERLAP = 64


class RAGStore:
    """Per-factory ChromaDB collection wrapper."""

    def __init__(
        self,
        factory_id: UUID | str,
        *,
        persist_root: Path | None = None,
        embed_model_name: str = DEFAULT_EMBED_MODEL,
    ):
        self.factory_id = str(factory_id)
        self.persist_root = persist_root or DEFAULT_PERSIST_ROOT
        self.persist_dir = self.persist_root / self.factory_id
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=f"factory_{self.factory_id}",
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = SentenceTransformer(embed_model_name)
        log.info(
            "RAGStore ready for factory %s (%s docs)",
            self.factory_id,
            self.collection.count(),
        )

    # -----------------------------------------------------------------------
    # Ingestion
    # -----------------------------------------------------------------------
    def upsert_sop(
        self,
        sop_source_id: str,
        text: str,
        *,
        agent_id: str | None = None,
        source_title: str | None = None,
    ) -> None:
        """Chunk and embed an SOP document."""
        chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        for i, chunk in enumerate(chunks):
            doc_id = _stable_id("sop", sop_source_id, i)
            ids.append(doc_id)
            embeddings.append(self.embedder.encode(chunk).tolist())
            metadatas.append(
                {
                    "source": "sop",
                    "sop_source_id": sop_source_id,
                    "agent_id": agent_id,
                    "chunk_index": i,
                    "title": source_title or sop_source_id,
                }
            )
            documents.append(chunk)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        log.info("Upserted %d chunks for SOP %s", len(chunks), sop_source_id)

    def upsert_rca_finding(
        self,
        finding_id: str,
        summary: str,
        failure_cases_json: str,
        *,
        agent_id: str,
    ) -> None:
        """Embed an accepted RCA finding so future analyzers can learn from it."""
        # Include failure cases so search hits the actual gap, not just summary
        full_text = f"{summary}\n\nFailure cases:\n{failure_cases_json}"
        doc_id = _stable_id("rca", finding_id, 0)
        embedding = self.embedder.encode(full_text).tolist()
        self.collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[
                {
                    "source": "rca",
                    "rca_finding_id": finding_id,
                    "agent_id": agent_id,
                    "chunk_index": 0,
                    "title": f"RCA {finding_id}",
                }
            ],
            documents=[full_text],
        )
        log.info("Upserted RCA finding %s", finding_id)

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = 5,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top-k chunks with metadata and distance."""
        embedding = self.embedder.encode(query).tolist()
        where_filter: dict[str, Any] | None = None
        if agent_id:
            where_filter = {"agent_id": agent_id}

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where_filter,
            include=[Include.metadatas, Include.documents, Include.distances],
        )
        out: list[dict[str, Any]] = []
        for i in range(len(results["ids"][0])):
            out.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "distance": results["distances"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
            )
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Simple sliding-window chunking by characters."""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        # Try to break at newline if near boundary
        if end < len(text):
            nl = text.rfind("\n", end - overlap, end + overlap)
            if nl != -1:
                end = nl
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
    return chunks


def _stable_id(prefix: str, source_id: str, chunk_idx: int) -> str:
    """Deterministic doc id so re-upserts are idempotent."""
    raw = f"{prefix}:{source_id}:{chunk_idx}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]
