"""Tests for the Evidence-Fusion dual-citation logic (the differentiator)."""
from clinical_agent.agents.curator import run_curator
from clinical_agent.fhir.client import FHIRClient
from clinical_agent.rag.retriever import Retriever
from clinical_agent.state import AgentState


def _run():
    state: AgentState = {"query": "manage diabetes", "patient_id": "demo-1", "trace": []}
    return run_curator(state, FHIRClient(use_fixtures=True), Retriever())


def test_answer_has_both_citation_types():
    state = _run()
    ans = state["answer"]
    assert ans.literature, "must cite published evidence"
    assert ans.patient, "must cite patient data"


def test_patient_citations_reference_fhir_resources():
    state = _run()
    for pc in state["answer"].patient:
        assert pc.resource.startswith("Observation/")
        assert pc.value


def test_rendered_markdown_shows_dual_provenance():
    md = _run()["answer"].render_markdown()
    assert "Patient data used:" in md
    assert "Evidence:" in md
