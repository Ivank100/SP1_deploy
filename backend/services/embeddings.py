"""This file wraps embedding generation for lecture search features.
It turns text into vectors that the retrieval and indexing layers can reuse."""


# src/embedding_model.py
from typing import List

from ..core.config import EMBEDDING_MODEL, PG_DIM
from ..clients.openai import OpenAIClient


def _validate_embedding_dimensions(embeddings: List[List[float]]) -> None:
    if not embeddings:
        return

    actual_dim = len(embeddings[0])
    if actual_dim != PG_DIM:
        raise ValueError(
            f"Embedding dimension mismatch: model returned {actual_dim}, "
            f"but PGVECTOR_DIM is {PG_DIM}. Update .env so they match."
        )

    for emb in embeddings[1:]:
        if len(emb) != actual_dim:
            raise ValueError("Embedding API returned inconsistent vector dimensions")


def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """
    Embed texts using the configured OpenAI-compatible embeddings API.
    """
    if not texts:
        return []

    client = OpenAIClient()
    embeddings: List[List[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        batch_embeddings = client.embed(batch, model=EMBEDDING_MODEL)
        _validate_embedding_dimensions(batch_embeddings)
        embeddings.extend(batch_embeddings)

    return embeddings
