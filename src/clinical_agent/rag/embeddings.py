"""Embedding backends. Stub (offline, deterministic) or sentence-transformers."""
from __future__ import annotations

import hashlib
import math
import re

from clinical_agent.config import get_settings

_DIM = 256


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class StubEmbedder:
    """Deterministic hashing bag-of-words embedder — no model download needed.

    Good enough for demos, tests, and CI. Cosine similarity is meaningful because
    shared tokens hash to shared dimensions.
    """

    dim = _DIM

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % _DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # lazy import
        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


def get_embedder():
    s = get_settings()
    if s.embed_provider == "sentence-transformers":
        return SentenceTransformerEmbedder(s.embed_model)
    return StubEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # vectors are pre-normalized
