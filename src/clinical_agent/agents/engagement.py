"""Engagement Agent — conversational layer + scope-of-use guardrail.

Guardrail enforces decision SUPPORT, not decision MAKING: it deflects out-of-scope
queries and refuses directive orders, mitigating automation bias (the field's #2
cited risk). Returns the Curator's GroundedAnswer with a verification reminder.
"""
from __future__ import annotations

from clinical_agent.state import AgentState

# queries that request directive clinical action — must be deflected to a clinician
DIRECTIVE_TERMS = (
    "prescribe", "order ", "should i give", "what dose should",
    "diagnose definitively", "stop the medication", "discharge the patient",
)
OFF_DOMAIN_TERMS = ("weather", "stock", "sports", "movie")


def classify(query: str) -> str:
    """Keyword route a query into 'directive', 'off_domain', or 'clinical'. A real
    deployment would use the LLM here; keywords keep it deterministic and offline."""
    q = query.lower()
    if any(t in q for t in DIRECTIVE_TERMS):
        return "directive"
    if any(t in q for t in OFF_DOMAIN_TERMS):
        return "off_domain"
    return "clinical"


def make_nudges(study_plan: list[dict]) -> list[str]:
    """Adherence prompts tied to each queued learning module."""
    return [
        f"Review {m['topic']} (triggered by {m['based_on']}) — "
        f"see {m.get('evidence_source') or 'the cited guideline'}."
        for m in study_plan
    ]


def make_digest(flags: list[dict], study_plan: list[dict]) -> str:
    """One-line session roll-up of open items."""
    if not flags:
        return "No conditions flagged from the current observations; nothing queued."
    topics = ", ".join(sorted({f["topic"] for f in flags}))
    return (f"{len(flags)} condition(s) flagged ({topics}); "
            f"{len(study_plan)} learning module(s) queued.")


def confidence(literature: list) -> str:
    """Surface retrieval confidence (decision-support transparency, not a verdict)."""
    if not literature:
        return "low"
    top = max((getattr(c, "score", 0.0) for c in literature), default=0.0)
    if len(literature) >= 3 and top >= 0.17:
        return "high"
    if literature:
        return "moderate"
    return "low"


def run_engagement(state: AgentState) -> AgentState:
    """Scope-of-use guardrail. Reads ``query`` + ``answer``; writes ``route`` and
    mutates ``answer.text`` for non-clinical routes. ``route`` is advisory: it
    records the classification but does not branch the pipeline."""
    route = classify(state["query"])
    answer = state.get("answer")

    if route == "off_domain":
        note = "This assistant only handles clinical decision-support queries."
        if answer:
            answer.text = note
    elif route == "directive" and answer:
        answer.text = (
            "I provide decision SUPPORT only and cannot issue clinical orders or "
            "prescriptions. Here is the relevant grounded evidence for a clinician "
            "to weigh: " + answer.text
        )

    flags = state.get("flagged_conditions", [])
    plan = state.get("study_plan", [])
    state.update(
        route=route,
        answer=answer,
        nudges=make_nudges(plan),
        digest=make_digest(flags, plan),
        confidence=confidence(state.get("literature", [])),
        trace=state.get("trace", []) + [f"engagement: route={route}"],
    )
    return state
