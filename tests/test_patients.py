"""Tests that the three demo patients exercise distinct condition profiles."""
from clinical_agent.orchestrator import run_pipeline


def test_demo1_diabetes_kidney():
    s = run_pipeline("assess this patient", "demo-1")
    assert {f["topic"] for f in s["flagged_conditions"]} == {"diabetes", "kidney"}


def test_demo2_hypertension_cholesterol():
    s = run_pipeline("assess this patient", "demo-2")
    assert {f["topic"] for f in s["flagged_conditions"]} == {"hypertension", "cholesterol"}


def test_demo3_flags_nothing():
    s = run_pipeline("assess this patient", "demo-3")
    assert s["flagged_conditions"] == []
    assert s["study_plan"] == []
    # a healthy patient still produces a valid, bounded scorecard
    assert 0 <= s["work_iq"]["clinical_work_iq"] <= 100
