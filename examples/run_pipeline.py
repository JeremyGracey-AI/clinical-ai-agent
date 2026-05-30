"""Worked examples of driving the Clinical AI Agent programmatically.

Runs fully offline (synthetic fixtures + stub LLM/embedder). Run with:

    python examples/run_pipeline.py

See docs/SESSION_FLOW.md for a narrated trace of what each step does, and
examples/sample_output.md for the expected output of this script.
"""
from __future__ import annotations

from clinical_agent.agents.curator import run_curator
from clinical_agent.fhir.client import FHIRClient
from clinical_agent.orchestrator import run_pipeline
from clinical_agent.rag.retriever import Retriever


def example_1_full_pipeline() -> None:
    """The common case: one call, dual-cited answer + conditions + scorecard."""
    print("\n=== Example 1: full pipeline ===")
    state = run_pipeline("How should I manage this patient's diabetes?", "demo-1")

    # The GroundedAnswer renders both provenance blocks (patient data + evidence).
    print(state["answer"].render_markdown())

    print("\nConditions flagged:")
    for f in state["flagged_conditions"]:
        print(f"  - {f['condition']}  (evidence: {f['evidence_chunk_id']})")

    print(f"\nClinical Work IQ: {state['work_iq']['clinical_work_iq']}")


def example_2_inspect_partial_state() -> None:
    """State is additive — run a single agent and inspect what it wrote."""
    print("\n=== Example 2: run only the Curator, inspect partial state ===")
    state = {"query": "kidney function concerns", "patient_id": "demo-1", "trace": []}
    state = run_curator(state, FHIRClient(use_fixtures=True), Retriever())

    print(f"  observations pulled : {len(state['observations'])}")
    print(f"  evidence retrieved  : {[c.chunk_id for c in state['literature']]}")
    print(f"  patient citations   : {[c.render() for c in state['patient_citations']]}")


def example_3_guardrail_routes() -> None:
    """The Engagement guardrail rewrites the answer for non-clinical queries."""
    print("\n=== Example 3: scope-of-use guardrail ===")
    for q in ["What dose of insulin should I prescribe?", "what is the weather today"]:
        state = run_pipeline(q, "demo-1")
        print(f"  query={q!r}\n    route={state['route']}  ->  {state['answer'].text[:90]}…")


def example_4_optional_write_back() -> None:
    """Enable FHIR write-back. In fixture mode the POST returns a fake id."""
    print("\n=== Example 4: assessment write-back (fixture mode) ===")
    state = run_pipeline("manage diabetes", "demo-1", use_fixtures=True, write_back=True)
    print(f"  items generated : {state['assessment']['n_items']}")
    print(f"  written_back ids: {state['assessment']['written_back']}")


def example_5_learner_profile_and_grading() -> None:
    """Prior mastery scales difficulty; supplied responses get graded."""
    print("\n=== Example 5: learner profile + graded responses ===")
    state = run_pipeline("manage diabetes", "demo-1",
                         learner_profile={"diabetes": 0.9},   # high prior mastery
                         responses={"diabetes": 0})            # answer choice A
    mod = next(m for m in state["study_plan"] if m["topic"] == "diabetes")
    print(f"  diabetes module difficulty : {mod['difficulty']}  (was 'foundational')")
    print(f"  gradings                   : {state['assessment']['gradings']}")
    print(f"  updated mastery            : {state['assessment']['mastery']}")


if __name__ == "__main__":
    example_1_full_pipeline()
    example_2_inspect_partial_state()
    example_3_guardrail_routes()
    example_4_optional_write_back()
    example_5_learner_profile_and_grading()
