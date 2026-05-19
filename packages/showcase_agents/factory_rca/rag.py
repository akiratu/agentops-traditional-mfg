"""Embedding-based RAG over historical incident corpus.

- Uses an `LLMProvider` for embeddings (provider-agnostic).
- Stores corpus embeddings on disk (.cache/rag_index.json) keyed by a hash
  of the corpus content so it auto-rebuilds when corpus changes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from corpus import CORPUS, doc_to_search_text
from providers import LLMProvider, make_provider

CACHE_DIR = Path(__file__).parent / ".cache"
INDEX_FILE = CACHE_DIR / "rag_index.json"


def _corpus_fingerprint(corpus: list[dict]) -> str:
    serialized = json.dumps(
        [(d["id"], doc_to_search_text(d)) for d in corpus],
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def build_or_load_index(
    provider: LLMProvider | None = None,
    api_key: str | None = None,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Return {'fingerprint': str, 'vectors': {doc_id: list[float]}}.

    `provider` is preferred; `api_key` is a backwards-compatible fallback
    that auto-builds a provider via the factory.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fp = _corpus_fingerprint(CORPUS)

    if INDEX_FILE.exists():
        try:
            cached = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            if cached.get("fingerprint") == fp and "vectors" in cached:
                return cached
        except Exception:
            pass

    if provider is None:
        provider = make_provider(api_key=api_key)
    vectors: dict[str, list[float]] = {}
    total = len(CORPUS)
    for i, doc in enumerate(CORPUS, 1):
        if on_progress:
            on_progress(f"建索引中... {i}/{total} ({doc['id']})")
        text = doc_to_search_text(doc)
        vectors[doc["id"]] = provider.embed(text, task_type="RETRIEVAL_DOCUMENT")

    payload = {"fingerprint": fp, "vectors": vectors}
    INDEX_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def search(
    query: str,
    provider: LLMProvider | None = None,
    api_key: str | None = None,
    top_k: int = 3,
    min_score: float = 0.55,
    index: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return top-K most similar docs from the corpus."""
    if provider is None:
        provider = make_provider(api_key=api_key)
    if index is None:
        index = build_or_load_index(provider=provider)
    q_vec = provider.embed(query, task_type="RETRIEVAL_QUERY")

    scored: list[tuple[float, dict]] = []
    by_id = {d["id"]: d for d in CORPUS}
    for doc_id, vec in index["vectors"].items():
        doc = by_id.get(doc_id)
        if not doc:
            continue
        score = _cosine(q_vec, vec)
        scored.append((score, doc))

    scored.sort(key=lambda t: t[0], reverse=True)
    out: list[dict] = []
    for score, doc in scored[:top_k]:
        if score < min_score:
            continue
        out.append({**doc, "score": round(score, 3)})
    return out
