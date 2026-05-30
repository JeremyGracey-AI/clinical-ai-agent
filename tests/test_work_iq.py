"""Tests for the Work IQ eval harness."""
from clinical_agent.agents.study_plan import flag_conditions
from clinical_agent.eval.rag_metrics import (
    citation_coverage,
    composite_work_iq,
    faithfulness,
    safety_probe_recall,
)
from clinical_agent.models.citation import GroundedAnswer, LiteratureCitation, PatientCitation
from clinical_agent.orchestrator import run_pipeline


def test_faithfulness_perfect_when_answer_in_context():
    ctx = ["HbA1c above eight indicates inadequate diabetes control"]
    assert faithfulness("inadequate diabetes control", ctx) == 1.0


def test_faithfulness_low_when_unsupported():
    ctx = ["kidney function eGFR chronic disease"]
    assert faithfulness("unicorn rainbow telescope", ctx) < 0.5


def test_citation_coverage_full():
    ans = GroundedAnswer(
        text="x",
        literature=[LiteratureCitation(chunk_id="c", title="t", source="s", url="http://x")],
        patient=[PatientCitation(resource="Observation/1", label="A1c", value="8.2 %")],
    )
    assert citation_coverage(ans) == 1.0


def test_safety_probes_all_caught():
    result = safety_probe_recall(flag_conditions)
    assert result["recall"] == 1.0, result["details"]


def test_full_pipeline_produces_scorecard():
    state = run_pipeline("manage diabetes", "demo-1", use_fixtures=True)
    wq = state["work_iq"]
    assert 0 <= wq["clinical_work_iq"] <= 100
    assert wq["safety_probe_recall"] == 1.0
    # demo patient should flag exactly diabetes + kidney
    topics = {f["topic"] for f in state["flagged_conditions"]}
    assert topics == {"diabetes", "kidney"}


def test_composite_bounds():
    s = composite_work_iq(faithfulness_score=1.0, citation_cov=1.0,
                          retrieval={"recall": 1.0}, safety={"recall": 1.0})
    assert s == 100.0
