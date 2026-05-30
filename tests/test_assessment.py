"""Tests for MCQ generation, scoring, and mastery tracking."""
from clinical_agent.agents.assessment import (
    generate_items,
    score_response,
    update_mastery,
)
from clinical_agent.orchestrator import run_pipeline


def test_generate_items_deterministic_mcq():
    modules = [{"topic": "diabetes", "evidence_chunk_id": "ada-hba1c-001"}]
    items = generate_items(modules)
    it = items[0]
    assert len(it["options"]) == 4
    assert 0 <= it["answer_index"] < 4
    assert it["options"][it["answer_index"]]            # correct option is non-empty
    assert generate_items(modules) == items             # deterministic offline


def test_score_response():
    it = generate_items([{"topic": "diabetes", "evidence_chunk_id": "ada-hba1c-001"}])[0]
    assert score_response(it, it["answer_index"])["correct"] is True
    assert score_response(it, (it["answer_index"] + 1) % 4)["correct"] is False


def test_update_mastery_ema():
    p = {}
    assert update_mastery(p, "diabetes", True)["diabetes"] == 0.5
    assert update_mastery(p, "diabetes", True)["diabetes"] == 0.75
    assert update_mastery(p, "diabetes", False)["diabetes"] == 0.375


def test_mastery_drives_difficulty():
    base = run_pipeline("manage diabetes", "demo-1")
    advanced = run_pipeline("manage diabetes", "demo-1", learner_profile={"diabetes": 0.9})
    base_mod = next(m for m in base["study_plan"] if m["topic"] == "diabetes")
    adv_mod = next(m for m in advanced["study_plan"] if m["topic"] == "diabetes")
    assert base_mod["difficulty"] == "foundational"
    assert adv_mod["difficulty"] == "advanced"


def test_responses_are_graded():
    s = run_pipeline("manage diabetes", "demo-1", responses={"diabetes": 0})
    assert s["assessment"]["gradings"]
    assert any(g["topic"] == "diabetes" for g in s["assessment"]["gradings"])
    assert "diabetes" in s["assessment"]["mastery"]
