"""Tests for the Engagement guardrail, nudges, digest, and confidence."""
from clinical_agent.agents.engagement import (
    classify,
    confidence,
    make_digest,
    make_nudges,
)
from clinical_agent.models.citation import LiteratureCitation
from clinical_agent.orchestrator import run_pipeline


def test_classify_routes():
    assert classify("What dose should I prescribe?") == "directive"
    assert classify("what is the weather today") == "off_domain"
    assert classify("how should I manage diabetes") == "clinical"


def test_nudges_and_digest():
    plan = [{"topic": "diabetes", "based_on": "HbA1c = 8.2 %", "evidence_source": "ADA"}]
    assert make_nudges(plan) and "diabetes" in make_nudges(plan)[0]
    assert "diabetes" in make_digest([{"topic": "diabetes"}], plan)
    assert make_digest([], []).startswith("No conditions")


def test_confidence_levels():
    lits = [LiteratureCitation(chunk_id="c", title="t", source="s", url="http://x", score=0.2)
            for _ in range(3)]
    assert confidence(lits) == "high"
    assert confidence([]) == "low"


def test_clinical_route_does_not_mutate_answer():
    # the guardrail must leave clinical answers untouched (keeps faithfulness intact)
    s = run_pipeline("How should I manage this patient's diabetes?", "demo-1")
    assert s["route"] == "clinical"
    assert s["answer"].text.startswith("Based on the available evidence")
    assert s["confidence"] and s["digest"] and s["nudges"]


def test_directive_route_prepends_disclaimer():
    s = run_pipeline("What dose should I prescribe?", "demo-1")
    assert s["route"] == "directive"
    assert s["answer"].text.startswith("I provide decision SUPPORT only")
