# Contributing

## Dev setup

```bash
pip install -e ".[dev]"     # core + pytest + ruff   (no network/keys needed)
python -m pytest -q          # 36 tests, ~0.1s
python -m clinical_agent.cli # end-to-end offline smoke
python scripts/run_eval.py   # Work IQ scorecard across all demo patients
```

For the full production stack (LangGraph, ChromaDB, sentence-transformers, Gradio,
OpenAI): `pip install -e ".[full]"`.

## Layout

`src/clinical_agent/` is the package; see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#module-map) for the module map and
[docs/AGENTS.md](docs/AGENTS.md) for per-agent contracts.

## Conventions

- **Offline-first.** Every change must keep `pip install -e ".[dev]" && pytest`
  green with no network and no API keys. Heavy/optional backends stay behind lazy
  imports (see how `OpenAILLM`, `SentenceTransformerEmbedder`, and the Gradio/
  LangGraph imports are done) so the core package stays light.
- **Temperature 0.** Clinical generation is deterministic. Don't introduce
  non-zero temperature defaults.
- **Always cite.** Anything that produces a clinical claim must carry provenance —
  preserve the dual-citation contract (`GroundedAnswer` with both `literature` and
  `patient`).
- **State is additive.** Agents `state.update(...)` and append a `trace` line; they
  don't delete keys earlier agents wrote. New output keys go in
  `AgentState` ([state.py](src/clinical_agent/state.py)).
- **Lint:** `ruff check src tests` (line length 100, target py310).

## Tests

Add a test under `tests/` for any new agent or metric. The suite is the contract:
`test_dual_citation.py` guards the differentiator (both citation types present),
`test_work_iq.py` guards the eval invariants (all safety probes caught, composite
bounds). Mirror that style — assert the *property*, not just that code runs.

## Adding features

See [docs/EXTENDING.md](docs/EXTENDING.md) for step-by-step recipes (corpus doc,
Conditions rule, LLM/embedder swap, new agent).

## Safety note

Threshold values in `rag/corpus.py` and `agents/study_plan.py` are **illustrative**.
This is a reference implementation and portfolio artifact — decision *support*, not
decision *making*. Don't represent its output as validated clinical guidance.
