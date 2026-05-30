"""Corpus ingestion: chunk markdown/text files in CORPUS_DIR into retriever chunks.

Smaller chunks for precise facts, larger for narrative context. Returns chunk
dicts compatible with Retriever(extra_chunks=...).
"""
from __future__ import annotations

import os

from clinical_agent.config import get_settings


def _chunk_text(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + size]))
        i += size - overlap
    return chunks


def ingest_corpus_dir(corpus_dir: str | None = None) -> list[dict]:
    corpus_dir = corpus_dir or get_settings().corpus_dir
    out: list[dict] = []
    if not os.path.isdir(corpus_dir):
        return out
    for fname in sorted(os.listdir(corpus_dir)):
        if fname.startswith(".") or fname.lower().startswith("readme"):
            continue  # skip hidden files and the folder's own docs (not evidence)
        if not fname.lower().endswith((".md", ".txt")):
            continue
        path = os.path.join(corpus_dir, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for j, chunk in enumerate(_chunk_text(text)):
            out.append({
                "chunk_id": f"{fname}:{j}",
                "title": chunk,
                "source": fname,
                "url": f"file://{os.path.abspath(path)}",
                "topics": [],
            })
    return out
