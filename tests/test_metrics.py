"""Tests for the analytics history + LLM-judge faithfulness fallback."""
import os
import tempfile

from clinical_agent.eval.rag_metrics import (
    append_run,
    faithfulness_judge,
    load_history,
)


class _FakeLLM:
    def __init__(self, reply):
        self._reply = reply

    def chat(self, *, system, user):
        return self._reply


def test_analytics_round_trip():
    path = os.path.join(tempfile.mkdtemp(), "a.jsonl")
    append_run({"clinical_work_iq": 90.0}, path)
    append_run({"clinical_work_iq": 92.0}, path)
    hist = load_history(path)
    assert [h["clinical_work_iq"] for h in hist] == [90.0, 92.0]
    assert all("ts" in h for h in hist)


def test_load_history_missing_file():
    assert load_history("/nonexistent/does-not-exist.jsonl") == []


def test_faithfulness_judge_parses_score():
    assert faithfulness_judge("x", ["x"], _FakeLLM("The score is 0.9 out of 1.")) == 0.9


def test_faithfulness_judge_no_number_is_zero():
    assert faithfulness_judge("x", ["x"], _FakeLLM("no numeric score here")) == 0.0


def test_faithfulness_judge_empty_answer_is_one():
    assert faithfulness_judge("", ["x"], _FakeLLM("0.0")) == 1.0
