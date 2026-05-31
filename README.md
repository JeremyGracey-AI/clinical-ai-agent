---
title: Clinical AI Agent
emoji: 🩺
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.15.2
app_file: app.py
pinned: false
license: apache-2.0
---

# Clinical AI Agent

[![CI](https://github.com/JeremyGracey-AI/clinical-ai-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/JeremyGracey-AI/clinical-ai-agent/actions/workflows/ci.yml)

**Patient-grounded, citation-traceable clinical decision support on open standards.**

A 5-agent clinical companion that fuses a patient's live **SMART on FHIR** record with cited medical evidence through a **transparent RAG pipeline** — and scores its own faithfulness with a built-in evaluation harness.

> **Why this exists.** A scan of 9 frontier healthcare-AI companies (Abridge, Suki, Ambience, AKASA, CodaMetrix, Innovaccer, K Health, Ellipsis Health, OpenEvidence) found one unoccupied square: an *open, transparent* agent that grounds cited evidence in a *specific patient's live record* and *proves its own faithfulness*. OpenEvidence has citations but no patient context; Ambience has fusion but is Epic-locked and proprietary; everyone else is documentation or coding. This targets that gap.

---

## Runs offline out of the box

No API keys, no live FHIR server required. The repo ships with a deterministic stub LLM, a hashing embedder, an in-memory vector index over a built-in citable corpus, and synthetic FHIR fixtures.

```bash
pip install -e ".[dev]"
python -m pytest -q              # 36 tests, ~0.1s
python -m clinical_agent.cli     # full pipeline, prints grounded answer + Work IQ
python examples/run_pipeline.py  # four worked examples (see examples/)
python scripts/run_eval.py       # Work IQ scorecard across all demo patients
```

Going live is config-only — set `LLM_PROVIDER=openai` (or `anthropic`), `EMBED_PROVIDER=sentence-transformers`, `USE_CHROMA=true`, point `FHIR_BASE_URL` at any FHIR R4 server (e.g. `https://hapi.fhir.org/baseR4`), and run `scripts/smoke_test_fhir.py --live <patient_id>`. Full live checklist in [docs/FHIR.md](docs/FHIR.md#going-live--checklist).

<details>
<summary><b>Real output of <code>python -m clinical_agent.cli</code></b> (click to expand)</summary>

```
=== GROUNDED ANSWER ===
Based on the available evidence: LDL cholesterol >= 190 mg/dL warrants high-intensity
statin therapy; … Additionally, Glycemic targets: HbA1c >= 6.5% is diagnostic for
diabetes; … Values >= 8.0% indicate inadequate control … Verify against the cited
sources before acting.

**Patient data used:**
- [Observation/o-a1c] Hemoglobin A1c = 8.2 % @ 2026-05-01
- [Observation/o-egfr] eGFR = 52.0 mL/min/1.73m2 @ 2026-05-01
- [Observation/o-bp] Systolic blood pressure = 128.0 mmHg @ 2026-05-01
- [Observation/o-ldl] LDL cholesterol = 110.0 mg/dL @ 2026-05-01

**Evidence:**
- [ACC/AHA Cholesterol Guideline] … <https://www.ahajournals.org/doi/10.1161/CIR.0000000000000625>
- [ADA Standards of Care] … <https://diabetesjournals.org/care/issue/standards-of-care>
- [KDIGO CKD Guideline] … <https://kdigo.org/guidelines/ckd-evaluation-and-management/>

=== CONDITIONS FLAGGED ===
 - Inadequately controlled diabetes (HbA1c >= 8.0%)  (Hemoglobin A1c = 8.2 %)
 - Possible chronic kidney disease (eGFR < 60)  (eGFR = 52.0 mL/min/1.73m2)

=== CLINICAL WORK IQ ===
{ "clinical_work_iq": 98.0, "patient_id": "demo-1", "faithfulness": 0.9333,
  "faithfulness_method": "token_overlap", "citation_coverage": 1.0,
  "retrieval_precision": 0.6667, "retrieval_recall": 1.0, "safety_probe_recall": 1.0 }

=== TRACE ===
curator: 4 obs, 3 evidence chunks
study_plan: 2 conditions flagged
engagement: route=clinical
assessment: 2 items
work_iq: score=98.0
```

Full transcript + how each number arises: [examples/sample_output.md](examples/sample_output.md) · [docs/SESSION_FLOW.md](docs/SESSION_FLOW.md).
</details>

---

## The two differentiators

### 1. Evidence-Fusion dual-citation (`agents/curator.py`)
The Curator conditions retrieval on the patient's **actual** lab values, then emits a `GroundedAnswer` carrying **two** kinds of provenance:

- **Patient data used** — `[Observation/o-a1c] Hemoglobin A1c = 8.2 % @ 2026-05-01`
- **Evidence** — `[ADA Standards of Care] ... <https://...>`

This is what lets a clinician verify *why* an answer applies to *this* patient — the capability OpenEvidence structurally lacks.

### 2. Clinical Work IQ eval harness (`eval/rag_metrics.py`, `agents/work_iq.py`)
A reproducible scorecard almost no competitor ships:

| Metric | What it measures |
|---|---|
| Faithfulness | Share of answer content supported by retrieved context |
| Citation coverage | Answer carries both literature + patient provenance |
| Retrieval precision/recall | vs. a gold chunk set |
| Safety-probe recall | Abnormal synthetic cases the agent **must** flag |
| **Clinical Work IQ** | Weighted composite in [0, 100] |

---

## Architecture

```
Gradio UI ─▶ Orchestrator (LangGraph / plain-Python)
                │
   curator ─▶ study_plan ─▶ engagement ─▶ assessment ─▶ work_iq
      │            │             │             │
  Evidence-     Conditions   Scope-of-use   FHIR
  Fusion        Advisor      guardrail      write-back
  (RAG+FHIR)
```

| Agent | Role | FHIR |
|---|---|---|
| **Curator** | Evidence-Fusion Engine — patient-conditioned retrieval (+ refine loop) + dual citations | `GET /Patient/{id}` · `GET /Observation` |
| **Study Plan** | Conditions/Gap Advisor + curriculum with mastery-based difficulty | (consumes state) |
| **Engagement** | Scope-of-use guardrail + nudges, digest, confidence | — |
| **Assessment** | MCQ generation + scoring + mastery tracking (+ optional write-back) | `POST /Observation` |
| **Synthetic Work IQ** | Reproducible scorecard (token-overlap or LLM-judge) + analytics feed | synthetic fixtures |

SMART v2 scopes: `patient/Patient.r`, `patient/Observation.rs`, `patient/Observation.c`.
LLM backends: `stub` (offline default), `openai`, `anthropic`. Retrieval: in-memory (default) or ChromaDB. Three demo patients with distinct condition profiles.

---

## Session flow

One call to `run_pipeline(query, patient_id)` runs the five agents in a **fixed
linear order** — the Curator runs first so everyone downstream shares the same
patient context + evidence. State is a single dict that each agent adds to:

```
curator ──▶ study_plan ──▶ engagement ──▶ assessment ──▶ work_iq
  │             │              │              │              │
patient +    threshold      scope          comprehension  faithfulness,
evidence,    rules →        guardrail      items (+opt.    citation, safety
dual cites   conditions     (route)        write-back)     → Work IQ score
```

Real trace from the demo query:

```
curator: 4 obs, 3 evidence chunks
study_plan: 2 conditions flagged
engagement: route=clinical
assessment: 2 items
work_iq: score=98.0
```

The full step-by-step walkthrough — what each agent reads, calls, and writes, with
the real I/O at every step — is in **[docs/SESSION_FLOW.md](docs/SESSION_FLOW.md)**.
Per-agent contracts are in [docs/AGENTS.md](docs/AGENTS.md).

---

## Documentation

| Doc | What's in it |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design, the linear pipeline, `AgentState` lifecycle, offline-stub rationale, dual-citation model |
| [docs/SESSION_FLOW.md](docs/SESSION_FLOW.md) | Step-by-step trace of one request with real captured I/O |
| [docs/AGENTS.md](docs/AGENTS.md) | Per-agent reference cards (state in/out, FHIR scopes, extension points) |
| [docs/EVALUATION.md](docs/EVALUATION.md) | Work IQ metric formulas, weights, interpretation, adding a probe |
| [docs/FHIR.md](docs/FHIR.md) | SMART scopes, OAuth2 flow, search params, write-back, going live |
| [docs/EXTENDING.md](docs/EXTENDING.md) | Add a corpus doc / Conditions rule / agent; swap the LLM or embedder |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup, conventions, test philosophy |
| [examples/](examples/) | Runnable `run_pipeline.py` + captured `sample_output.md` |

**Strategy context** (why this product, not another scribe): see [Why this exists](#why-this-exists)
above — a scan of 9 frontier healthcare-AI companies found one unoccupied square:
an open, transparent agent that grounds *cited* evidence in a *specific patient's*
live FHIR record and proves its own faithfulness.

---

## Layout

```
src/clinical_agent/
  config.py  state.py  orchestrator.py  cli.py
  fhir/      client, auth (SMART OAuth2), patient, observation
  rag/       embeddings, corpus, retriever, ingest, llm, prompts
  agents/    curator, study_plan, engagement, assessment, work_iq
  eval/      synthetic fixtures, rag_metrics
  models/    patient, observation, citation (dual-citation primitives)
  ui/        layout (Gradio), citations (foundation-paper header)
scripts/     smoke_test_fhir.py, build_index.py, run_eval.py
tests/       fhir_client, retriever, dual_citation, work_iq, assessment,
             engagement, synthetic, metrics, patients   (36 tests)
app.py       Gradio Space entrypoint (8-tab UI, 3 demo patients)
web/         carbon-style Docker UI: FastAPI (server.py) + custom-JS dashboard
Dockerfile   Docker-SDK Space build (ignored by the Gradio Space)
```

---

## Live demos

Two front-ends over the **same** `run_pipeline()`:

| UI | Stack | Space |
|---|---|---|
| **Dashboard** (recommended) | Docker · FastAPI · custom JS — streaming answer, dual-citation chips, Work IQ gauge + radar | [jeremygracey-ai/clinical-ai-agent-ui](https://huggingface.co/spaces/jeremygracey-ai/clinical-ai-agent-ui) |
| **Gradio** | gradio SDK · 8 tabs | [jeremygracey-ai/clinical-ai-agent](https://huggingface.co/spaces/jeremygracey-ai/clinical-ai-agent) |

**Deploy your own.** Gradio Space: push the repo (`app.py` + `sdk: gradio` README frontmatter). Docker Space: build the root `Dockerfile` (`uvicorn server:app --app-dir web`); config lives in `web/space_readme.md`. Add `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` as Space secrets + set `LLM_PROVIDER` for a live LLM.

---

## Safety & scope

Decision **support**, not decision **making**. The Engagement guardrail refuses directive orders and frames every answer as "verify against the cited sources." Guideline thresholds in `rag/corpus.py` and `agents/study_plan.py` are illustrative — verify against current primary guidelines before any clinical use.

### Honest limitations (offline default)

This is a reference implementation; the offline stack is plumbing, not clinical reasoning. Specifically:

- **The stub LLM is extractive, not reasoning.** It composes answers from the top retrieved chunks and does *not* filter by applicability — e.g. the demo answer cites "LDL ≥ 190 → statin" even though the patient's LDL (110) is normal. Set `LLM_PROVIDER=openai` or `anthropic` for an LLM that weighs evidence against the patient. ([details](docs/ARCHITECTURE.md#why-a-stub-llm))
- **FHIR write-back is opt-in and off by default** (`write_back=False`); the demo never writes. ([details](docs/FHIR.md#write-back))
- **The Work IQ harness is a scaffold** — token-overlap faithfulness and a demo-specific gold set demonstrate the *shape* of a reproducible benchmark, not a clinical validation. ([what it is / isn't](docs/EVALUATION.md#what-this-is-not))

## Foundational research
- Lewis et al. 2020, *Retrieval-Augmented Generation* — https://arxiv.org/abs/2005.11401
- Singhal et al. 2023, *LLMs encode clinical knowledge* — https://www.nature.com/articles/s41586-023-06291-2
- SMART App Launch v2 — https://build.fhir.org/ig/HL7/smart-app-launch/scopes-and-launch-context.html
- HL7 FHIR Observation search — https://build.fhir.org/observation-search.html
