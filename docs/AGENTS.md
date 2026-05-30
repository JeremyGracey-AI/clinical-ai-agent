# Agent reference

One card per agent. Each lists the function signature, what it reads from and
writes to `AgentState`, any FHIR calls + SMART scopes, and where to extend it.
See [SESSION_FLOW.md](SESSION_FLOW.md) for how they chain together.

All agents share the signature `run_*(state, …) -> AgentState` and **mutate state
additively** — they never drop keys a prior agent wrote.

---

## 1. Curator — Evidence-Fusion Engine *(the moat)*

[`agents/curator.py`](../src/clinical_agent/agents/curator.py)

```python
run_curator(state, client: FHIRClient, retriever: Retriever | None = None) -> AgentState
```

| | |
|---|---|
| **Role** | Patient-conditioned retrieval + dual-citation generation |
| **Reads** | `query`, `patient_id` |
| **Writes** | `patient`, `observations`, `literature`, `patient_citations`, `answer` |
| **FHIR** | `GET /Patient/{id}` (`patient/Patient.r`), `GET /Observation?patient=…&_sort=-date&_count=20&status=final` (`patient/Observation.rs`) |
| **RAG** | `retriever.retrieve(conditioned_query)` → `list[LiteratureCitation]` |

**Key internals**
- `_conditioned_query(query, patient, obs)` — injects up to 6 observation
  `context_line()`s + patient demographics into the retrieval query.
- `_patient_citations(obs)` — one `PatientCitation` per observation that has a value.
- **Refine loop** — if nothing clears the confidence floor, it re-queries once with
  the abnormal findings appended at `min_score=0` (controlled by `RETRIEVAL_REFINE`).
  The trace line gains `(refined)` when this fires.

**Extend:** change how patient context is folded into the query, swap the embedder
([EXTENDING.md](EXTENDING.md#swap-the-embedder)), or enable the ChromaDB backend
([EXTENDING.md](EXTENDING.md#use-a-persistent-chromadb-index)).

---

## 2. Study Plan — Conditions/Gap Advisor

[`agents/study_plan.py`](../src/clinical_agent/agents/study_plan.py)

```python
run_study_plan(state) -> AgentState
flag_conditions(observations: list[Observation]) -> list[dict]
```

| | |
|---|---|
| **Role** | Compare observations to guideline thresholds; surface missed/undercoded conditions; build a cited curriculum |
| **Reads** | `observations` |
| **Writes** | `flagged_conditions`, `study_plan` |
| **FHIR** | none (consumes Curator state) |

**The `RULES` table** drives everything — `(loinc_code, comparator, threshold,
condition, evidence_chunk_id, topic)`. Each rule points at a corpus chunk so a
flag is always backed by evidence. `flag_conditions()` is reused by the Work IQ
safety probes, so adding a rule strengthens both the advisor and the eval.

Each module also carries its evidence **source + URL** and a `difficulty`
(`foundational` → `intermediate` → `advanced`) scaled from the learner's prior
`mastery` for that topic (from `learner_profile`); least-mastered topics are
ordered first.

> ⚠️ Thresholds are **illustrative**. Verify against current primary guidelines
> before any clinical use.

**Extend:** [EXTENDING.md → Add a Conditions rule](EXTENDING.md#add-a-conditions-rule).

---

## 3. Engagement — scope-of-use guardrail

[`agents/engagement.py`](../src/clinical_agent/agents/engagement.py)

```python
run_engagement(state) -> AgentState
classify(query: str) -> str   # "clinical" | "directive" | "off_domain"
```

| | |
|---|---|
| **Role** | Enforce decision *support* not decision *making*; deflect out-of-scope queries; surface nudges, digest, confidence |
| **Reads** | `query`, `answer`, `flagged_conditions`, `study_plan`, `literature` |
| **Writes** | `route`, `nudges`, `digest`, `confidence`; **mutates `answer.text`** for non-clinical routes |
| **FHIR** | none |

`make_nudges()` turns each queued module into an adherence prompt; `make_digest()`
rolls up open items; `confidence()` maps retrieval strength to high/moderate/low.
These are **separate state fields** — the clinical answer text is never mutated, so
the faithfulness metric stays meaningful.

- `directive` (e.g. "prescribe", "what dose should") → prepends a decision-support
  disclaimer to the answer.
- `off_domain` (e.g. "weather", "stock") → replaces the answer with a deflection.
- `clinical` → answer passes through unchanged.

> `route` is **advisory** — it records the classification but does not branch the
> pipeline (see [ARCHITECTURE.md](ARCHITECTURE.md#the-pipeline-is-linear-by-design)).
> Classification is keyword-based; a real deployment would use the LLM classifier.

**Extend:** broaden `DIRECTIVE_TERMS` / `OFF_DOMAIN_TERMS`, or replace `classify()`
with a model call.

---

## 4. Assessment — MCQ + scoring + mastery + write-back

[`agents/assessment.py`](../src/clinical_agent/agents/assessment.py)

```python
run_assessment(state, client: FHIRClient | None = None, write_back: bool = False) -> AgentState
generate_items(study_plan, llm=None) -> list[dict]       # 4-option MCQ per module
score_response(item, selected_index) -> dict             # correctness + rationale
update_mastery(profile, topic, correct) -> dict          # EMA in [0, 1]
```

| | |
|---|---|
| **Role** | Generate an evidence-anchored MCQ per module, grade responses, track mastery |
| **Reads** | `study_plan`, `patient_id`, optional `responses`, `learner_profile` |
| **Writes** | `assessment` (`{items, n_items, gradings, mastery, written_back}`), `learner_profile` |
| **FHIR** | `POST /Observation` (category `survey`, scope `patient/Observation.c`) — **only when `write_back=True`** |

Item generation uses the LLM when a real backend is configured (JSON MCQ from the
evidence chunk) and falls back to a **deterministic, evidence-anchored template**
offline — so the flow runs in CI. Each correct option is deterministically placed
among distractors via a hash of the chunk id. Mastery uses an exponential moving
average and feeds the Study Plan's difficulty scaling next session.

> `write_back` defaults to `False` in `run_pipeline()` **and** the Gradio UI, so
> the demo never writes to FHIR. In fixture mode a `POST` returns a fake
> `{"id": "fixture-created"}`; against a live server it returns the created
> resource. See [FHIR.md → Write-back](FHIR.md#write-back).

---

## 5. Work IQ — the validation differentiator

[`agents/work_iq.py`](../src/clinical_agent/agents/work_iq.py)

```python
run_work_iq(state) -> AgentState
```

| | |
|---|---|
| **Role** | Score the pipeline's own competence into a reproducible scorecard |
| **Reads** | `answer`, `literature`, `observations` |
| **Writes** | `work_iq` |
| **FHIR** | none (uses synthetic safety cases) |

Aggregates faithfulness, citation coverage, retrieval precision/recall, and
safety-probe recall into a single **Clinical Work IQ** in `[0, 100]`. Faithfulness
uses the deterministic token-overlap proxy by default, or an **LLM-as-judge** when
`JUDGE_FAITHFULNESS=true` with a real backend. With `record=True` the scorecard is
appended to the analytics history (the Analytics tab feed). The gold chunk set
(`DEMO_GOLD_CHUNKS`) is demo-specific. Full metric definitions and the composite
weights are in [EVALUATION.md](EVALUATION.md).

**Extend:** add a metric in [`eval/rag_metrics.py`](../src/clinical_agent/eval/rag_metrics.py)
and a weight in `composite_work_iq()`; add a safety case in
[`eval/synthetic.py`](../src/clinical_agent/eval/synthetic.py).
