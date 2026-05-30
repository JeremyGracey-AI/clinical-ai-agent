"""Vector retriever with provenance tagging.

Two backends, same interface:
  - in-memory cosine index (offline default) — deterministic, zero deps.
  - ChromaDB persistent collection (set ``USE_CHROMA=true``, needs the [full] extra)
    — we supply our own embeddings, so no model download is triggered.

Every hit is returned as a LiteratureCitation so downstream agents always have
provenance. An optional ``topics`` filter supports hybrid (vector + metadata)
retrieval; with ``topics=None`` the default path is unchanged.
"""
from __future__ import annotations

from clinical_agent.config import get_settings
from clinical_agent.models.citation import LiteratureCitation
from clinical_agent.rag.corpus import SEED_CORPUS
from clinical_agent.rag.embeddings import cosine, get_embedder


class _ChromaBackend:
    """Persistent ChromaDB collection indexed with our own embeddings."""

    def __init__(self, chunks: list[dict], embedder, settings):
        import chromadb  # lazy — only when USE_CHROMA=true
        client = chromadb.PersistentClient(path=settings.chroma_dir)
        self.col = client.get_or_create_collection(
            "clinical_corpus", metadata={"hnsw:space": "cosine"})
        self.embedder = embedder
        self.by_id = {c["chunk_id"]: c for c in chunks}
        self.col.upsert(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=[embedder.embed(c["title"]) for c in chunks],
            documents=[c["title"] for c in chunks],
            metadatas=[{"source": c["source"], "url": c["url"]} for c in chunks],
        )

    def score(self, query: str) -> list[tuple[float, dict]]:
        qv = self.embedder.embed(query)
        n = max(1, self.col.count())
        res = self.col.query(query_embeddings=[qv], n_results=n)
        out: list[tuple[float, dict]] = []
        for cid, dist in zip(res["ids"][0], res["distances"][0]):
            c = self.by_id.get(cid)
            if c is not None:
                out.append((1.0 - dist, c))  # cosine distance -> similarity
        out.sort(key=lambda x: x[0], reverse=True)
        return out


class Retriever:
    def __init__(self, extra_chunks: list[dict] | None = None):
        self.settings = get_settings()
        self.embedder = get_embedder()
        self.chunks = SEED_CORPUS + (extra_chunks or [])
        self._backend: _ChromaBackend | None = None
        if self.settings.use_chroma:
            try:
                self._backend = _ChromaBackend(self.chunks, self.embedder, self.settings)
            except Exception:
                self._backend = None  # graceful fallback to in-memory
        if self._backend is None:
            self._index = [(c, self.embedder.embed(c["title"])) for c in self.chunks]

    def _score(self, query: str) -> list[tuple[float, dict]]:
        if self._backend is not None:
            return self._backend.score(query)
        qv = self.embedder.embed(query)
        scored = [(cosine(qv, vec), c) for c, vec in self._index]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def retrieve(self, query: str, top_k: int | None = None,
                 min_score: float | None = None,
                 topics: list[str] | None = None) -> list[LiteratureCitation]:
        top_k = top_k or self.settings.retrieval_top_k
        min_score = self.settings.retrieval_min_score if min_score is None else min_score

        scored = self._score(query)
        if topics:  # hybrid: keep only chunks whose metadata topics intersect
            tset = set(topics)
            scored = [(s, c) for s, c in scored if tset & set(c.get("topics", []))]

        hits: list[LiteratureCitation] = []
        for score, c in scored[:top_k]:
            if score < min_score:
                continue
            hits.append(LiteratureCitation(
                chunk_id=c["chunk_id"], title=c["title"],
                source=c["source"], url=c["url"], score=round(score, 4),
            ))
        return hits
