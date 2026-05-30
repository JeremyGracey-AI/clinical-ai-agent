# Extending the agent

Common changes, each grounded in the actual code. After any of these, run
`python -m pytest -q` and `python -m clinical_agent.cli` to confirm nothing broke.

---

## Add a corpus document

Two ways to add citable evidence:

**A. Drop a file** (no code) — put a `.md` or `.txt` file in `data/corpus/`, then:

```bash
python scripts/build_index.py
```

`rag/ingest.py` chunks it (≈600-word windows, 100-word overlap) and each chunk
becomes a `LiteratureCitation` with `url = file://…`. Current behavior with an
empty corpus dir:

```
Indexed 6 chunks (0 from corpus dir + 6 seed).
```

**B. Add a seed chunk** (versioned, citable URL) — append to `SEED_CORPUS` in
[`rag/corpus.py`](../src/clinical_agent/rag/corpus.py):

```python
{
    "chunk_id": "ada-screening-002",
    "title": "Adults with BMI ≥ 25 and one risk factor should be screened for "
             "diabetes; repeat every 3 years if normal.",
    "source": "ADA Standards of Care",
    "url": "https://diabetesjournals.org/care/issue/standards-of-care",
    "topics": ["diabetes", "screening"],
},
```

The retriever embeds the `title`, so write it as the citable, self-contained
sentence you want surfaced.

---

## Add a Conditions rule

This is the highest-leverage extension: one change strengthens the Conditions
Advisor **and** the Work IQ safety harness. Four coordinated edits:

1. **Rule** — add to `RULES` in [`agents/study_plan.py`](../src/clinical_agent/agents/study_plan.py):
   ```python
   ("2093-3", ">=", 240.0, "Elevated total cholesterol (>= 240 mg/dL)",
    "chol-total-001", "cholesterol"),
   ```
2. **Evidence** — add a `SEED_CORPUS` chunk with matching `chunk_id`
   (`"chol-total-001"`) so the flag is source-backed (see above).
3. **Safety probe** — add a case to `SAFETY_CASES` in
   [`eval/synthetic.py`](../src/clinical_agent/eval/synthetic.py):
   ```python
   ("Very high total cholesterol",
    [_obs("s5", "2093-3", "Total cholesterol", 300.0, "mg/dL")],
    {"cholesterol"}),
   ```
4. **Gold set** (optional) — if the new condition should count toward retrieval
   recall for the demo patient, add its `chunk_id` to `DEMO_GOLD_CHUNKS` in
   [`agents/work_iq.py`](../src/clinical_agent/agents/work_iq.py).

> Keep thresholds tied to a citable guideline and update the disclaimer if you add
> a domain. These values are illustrative, not validated.

---

## Swap the LLM

Set in `.env`:

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-…
LLM_TEMPERATURE=0          # keep deterministic for clinical output
```

`get_llm()` ([`rag/llm.py`](../src/clinical_agent/rag/llm.py)) returns `OpenAILLM`
when `LLM_PROVIDER=openai` and a key is set; otherwise the `StubLLM`.

**Anthropic** is also a first-class backend:

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-…
```

`AnthropicLLM` ([`rag/llm.py`](../src/clinical_agent/rag/llm.py)) implements the
same interface and is selected by `get_llm()` when `LLM_PROVIDER=anthropic` and a
key is present. If the provider is set but the key is missing, selection falls
back to the stub (so misconfiguration never crashes the pipeline).

Any backend just needs two methods: `generate(*, system, user, context) -> str`
(grounded answer) and `chat(*, system, user) -> str` (used for MCQ generation and
LLM-judge faithfulness).

---

## Swap the embedder

```bash
EMBED_PROVIDER=sentence-transformers
EMBED_MODEL=all-MiniLM-L6-v2
```

`get_embedder()` returns `SentenceTransformerEmbedder` (downloads the model on
first use) instead of the hashing `StubEmbedder`. This gives real semantic
retrieval — worth it because the stub embedder is weak (many queries leave only
one chunk above `RETRIEVAL_MIN_SCORE`). Any embedder needs `embed(text) ->
list[float]` returning **normalized** vectors (the retriever's `cosine()` assumes
unit length).

## Use a persistent ChromaDB index

The retriever ships a real ChromaDB backend (in addition to the default in-memory
cosine index):

```bash
USE_CHROMA=true        # needs the [full] extra (chromadb)
CHROMA_DIR=./data/chroma
```

`Retriever` then indexes the corpus into a persistent Chroma collection using
**our own embeddings** (so no model download is triggered) and queries it by
cosine distance. If chromadb isn't installed it falls back to in-memory
automatically. The default (`USE_CHROMA=false`) keeps the deterministic in-memory
path used by the tests.

---

## Add a new agent

1. Write `run_myagent(state) -> AgentState` that reads existing keys and writes
   new ones via `state.update(...)` plus a `trace` line (follow any agent in
   `agents/`).
2. Declare its output keys in `AgentState` ([`state.py`](../src/clinical_agent/state.py)).
3. Insert it into **both** execution backends in
   [`orchestrator.py`](../src/clinical_agent/orchestrator.py): the `run_pipeline()`
   call sequence and the `build_langgraph_app()` graph edges.
4. Surface it in the UI ([`ui/layout.py`](../src/clinical_agent/ui/layout.py)) as a
   new tab/formatter if it produces user-facing output.
5. Add a test in `tests/`.

---

## Use the LangGraph backend

```bash
pip install -e ".[full]"
```

```python
from clinical_agent.orchestrator import build_langgraph_app
app = build_langgraph_app()
final_state = app.invoke({"query": "manage diabetes", "patient_id": "demo-1", "trace": []})
```

Same five nodes, same order — but you get LangGraph's checkpointing, streaming,
and visualization on top.
