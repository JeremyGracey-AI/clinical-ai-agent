# Corpus directory

Drop **citable clinical evidence** here as `.md` or `.txt` files, then build the
index:

```bash
python scripts/build_index.py
```

## How ingestion works

[`rag/ingest.py`](../../src/clinical_agent/rag/ingest.py) reads every `.md`/`.txt`
file in this directory and chunks it into ≈600-word windows with 100-word overlap.
Each chunk becomes a retrievable `LiteratureCitation`:

| Field | Value |
|---|---|
| `chunk_id` | `<filename>:<chunk-index>` |
| `title` | the chunk text (what the embedder matches on) |
| `source` | the filename |
| `url` | `file://<absolute path>` |

These are **added to** the built-in `SEED_CORPUS` (the ADA / KDIGO / ACC-AHA /
Lewis / Singhal snippets in [`rag/corpus.py`](../../src/clinical_agent/rag/corpus.py)),
not a replacement for it.

## Guidance

- Prefer short, self-contained, factual passages — the retriever embeds the whole
  chunk, so tighter chunks retrieve more precisely (smaller for dosages/thresholds,
  larger for narrative).
- This folder is intentionally empty in the repo. Files you add here are local
  evidence; `.gitignore` does **not** ignore them, so don't commit anything you
  can't redistribute (respect source licenses).
- For a versioned, web-citable source with a real URL, add it to `SEED_CORPUS`
  instead — see [docs/EXTENDING.md](../../docs/EXTENDING.md#add-a-corpus-document).
