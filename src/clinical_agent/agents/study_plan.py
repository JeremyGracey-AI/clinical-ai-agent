"""Study Plan Agent + Conditions/Gap Advisor.

Conditions Advisor: compares observation values to guideline thresholds and
surfaces potentially missed / undercoded conditions WITH supporting evidence —
an open, transparent take on the market's highest-value coding/quality signal.
Thresholds are illustrative; verify against current primary guidelines.
"""
from __future__ import annotations

from clinical_agent.models.observation import Observation
from clinical_agent.rag.corpus import SEED_CORPUS
from clinical_agent.state import AgentState

_CHUNKS = {c["chunk_id"]: c for c in SEED_CORPUS}


def _difficulty(mastery: float) -> str:
    """Scale module depth to prior mastery (0..1) for this topic."""
    if mastery >= 0.8:
        return "advanced"
    if mastery >= 0.4:
        return "intermediate"
    return "foundational"


# (loinc_code, comparator, threshold, condition, evidence_chunk_id, topic)
RULES = [
    ("4548-4", ">=", 8.0, "Inadequately controlled diabetes (HbA1c >= 8.0%)",
     "ada-hba1c-001", "diabetes"),
    ("48642-3", "<", 60.0, "Possible chronic kidney disease (eGFR < 60)",
     "kdigo-egfr-001", "kidney"),
    ("8480-6", ">=", 140.0, "Stage 2 hypertension (systolic BP >= 140)",
     "acc-bp-001", "hypertension"),
    ("13457-7", ">=", 190.0, "Severe hypercholesterolemia (LDL >= 190)",
     "ldl-lipid-001", "cholesterol"),
]


def _cmp(value: float, comparator: str, threshold: float) -> bool:
    return value >= threshold if comparator == ">=" else value < threshold


def flag_conditions(observations: list[Observation]) -> list[dict]:
    """Apply the ``RULES`` thresholds to observations; return one dict per hit
    (condition, trigger, evidence_chunk_id, topic, observation_id). Reused by the
    Work IQ safety probes, so it is the single source of condition-detection truth."""
    flags = []
    by_code = {o.code: o for o in observations if o.value is not None}
    for code, comp, thr, condition, chunk_id, topic in RULES:
        o = by_code.get(code)
        if o and _cmp(o.value, comp, thr):
            flags.append({
                "condition": condition,
                "trigger": f"{o.display or code} = {o.value} {o.unit or ''}".strip(),
                "evidence_chunk_id": chunk_id,
                "topic": topic,
                "observation_id": o.id,
            })
    return flags


def run_study_plan(state: AgentState) -> AgentState:
    """Conditions/Gap Advisor. Reads ``observations``; writes ``flagged_conditions``
    and an ordered, evidence-linked ``study_plan``."""
    observations = state.get("observations", [])
    profile = state.get("learner_profile") or {}  # {topic: mastery 0..1}
    flags = flag_conditions(observations)

    modules = []
    for f in flags:
        chunk = _CHUNKS.get(f["evidence_chunk_id"], {})
        mastery = float(profile.get(f["topic"], 0.0))
        modules.append({
            "topic": f["topic"],
            "objective": f"Understand and manage: {f['condition']}",
            "based_on": f["trigger"],
            "evidence_chunk_id": f["evidence_chunk_id"],
            "evidence_source": chunk.get("source"),
            "evidence_url": chunk.get("url"),
            "difficulty": _difficulty(mastery),
            "mastery": round(mastery, 2),
        })

    # least-mastered topics first; stable sort preserves rule order on ties
    modules.sort(key=lambda m: m["mastery"])
    for i, m in enumerate(modules):
        m["order"] = i + 1

    state.update(
        flagged_conditions=flags,
        study_plan=modules,
        trace=state.get("trace", []) + [f"study_plan: {len(flags)} conditions flagged"],
    )
    return state
