"""Assessment Agent — MCQ generation + scoring + mastery, with optional write-back.

Item generation uses the LLM when a real backend is configured, and falls back to
a deterministic, evidence-anchored template offline so the whole flow runs in CI.
Scoring returns the rationale + the evidence the correct answer rests on; mastery
is tracked per topic and feeds the Study Plan's difficulty scaling next session.
"""
from __future__ import annotations

import hashlib
import json

from clinical_agent.fhir.client import FHIRClient
from clinical_agent.fhir.observation import write_assessment_observation
from clinical_agent.rag.corpus import SEED_CORPUS
from clinical_agent.rag.llm import get_llm
from clinical_agent.rag.prompts import SYSTEM_ASSESSMENT
from clinical_agent.state import AgentState

_CHUNKS = {c["chunk_id"]: c for c in SEED_CORPUS}
_MASTERY_ALPHA = 0.5  # EMA weight on the latest result

_DISTRACTORS = [
    "No intervention or monitoring is indicated.",
    "The finding is unrelated to the patient's conditions.",
    "Routine evaluation can be safely deferred indefinitely.",
]


def _place_correct(correct: str, key: str) -> tuple[list[str], int]:
    """Deterministically position the correct option among the distractors."""
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % 4
    options = _DISTRACTORS[:]
    options.insert(idx, correct)
    return options, idx


def _item_from_chunk(topic: str, chunk: dict) -> dict:
    """Deterministic, evidence-anchored MCQ (offline default)."""
    title = chunk.get("title", "")
    correct = title.split(";")[0].strip() or title.strip()
    options, idx = _place_correct(correct, chunk.get("chunk_id", topic))
    return {
        "question": f"For {topic}, which statement reflects the cited guidance?",
        "options": options,
        "answer_index": idx,
        "rationale": f"{chunk.get('source', 'source')}: {correct}".strip(),
        "evidence_url": chunk.get("url"),
    }


def _item_via_llm(llm, topic: str, chunk: dict) -> dict:
    """LLM-authored MCQ; raises on malformed output so the caller can fall back."""
    user = (
        f"From the EVIDENCE, write ONE multiple-choice question (exactly 4 options) "
        f"testing understanding of {topic}. Respond ONLY with JSON of the form "
        '{"question": "...", "options": ["...","...","...","..."], '
        '"answer_index": 0, "rationale": "..."}.\n'
        f"EVIDENCE: {chunk.get('title','')} (source: {chunk.get('source','')})"
    )
    raw = llm.chat(system=SYSTEM_ASSESSMENT, user=user)
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    if not (isinstance(data.get("options"), list) and len(data["options"]) == 4):
        raise ValueError("expected 4 options")
    data.setdefault("rationale", chunk.get("title", ""))
    data["evidence_url"] = chunk.get("url")
    return data


def generate_items(study_plan: list[dict], llm=None) -> list[dict]:
    """One evidence-anchored MCQ per study module."""
    llm = llm or get_llm()
    use_llm = getattr(llm, "name", "stub") != "stub"
    items = []
    for m in study_plan:
        chunk = _CHUNKS.get(m["evidence_chunk_id"], {"chunk_id": m["evidence_chunk_id"]})
        try:
            mcq = _item_via_llm(llm, m["topic"], chunk) if use_llm else _item_from_chunk(m["topic"], chunk)
        except Exception:
            mcq = _item_from_chunk(m["topic"], chunk)  # robust fallback
        items.append({"topic": m["topic"], "evidence_chunk_id": m["evidence_chunk_id"], **mcq})
    return items


def score_response(item: dict, selected_index: int) -> dict:
    """Grade one response; return correctness + rationale + the supporting evidence."""
    correct = selected_index == item["answer_index"]
    return {
        "topic": item["topic"],
        "correct": correct,
        "rationale": item.get("rationale", ""),
        "evidence_chunk_id": item.get("evidence_chunk_id"),
    }


def update_mastery(profile: dict, topic: str, correct: bool) -> dict:
    """Exponential-moving-average mastery update in [0, 1]."""
    prior = float(profile.get(topic, 0.0))
    profile[topic] = round(prior * (1 - _MASTERY_ALPHA) + (1.0 if correct else 0.0) * _MASTERY_ALPHA, 3)
    return profile


def run_assessment(state: AgentState, client: FHIRClient | None = None,
                   write_back: bool = False) -> AgentState:
    """Reads ``study_plan`` (+ optional ``responses``/``learner_profile``); writes
    ``assessment`` (items, gradings, updated mastery). When ``write_back=True`` and a
    client is supplied, posts each result as an Observation (category ``survey``).
    Write-back is OFF by default."""
    plan = state.get("study_plan", [])
    items = generate_items(plan)

    # Grade any supplied responses ({topic: selected_index}) and update mastery.
    responses = state.get("responses") or {}
    profile = dict(state.get("learner_profile") or {})
    gradings = []
    for it in items:
        if it["topic"] in responses:
            g = score_response(it, int(responses[it["topic"]]))
            gradings.append(g)
            update_mastery(profile, it["topic"], g["correct"])

    result = {"items": items, "n_items": len(items),
              "gradings": gradings, "mastery": profile, "written_back": []}

    if write_back and client and items:
        for it in items:
            score = profile.get(it["topic"], 1.0)
            resp = write_assessment_observation(
                client, state["patient_id"], score=float(score), topic=it["topic"])
            result["written_back"].append(resp.get("id"))

    state.update(
        assessment=result,
        learner_profile=profile,
        trace=state.get("trace", []) + [f"assessment: {len(items)} items"],
    )
    return state
