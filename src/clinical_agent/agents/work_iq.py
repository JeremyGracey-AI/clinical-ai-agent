"""Synthetic Work IQ Agent — scores the pipeline's own competence.

Produces a reproducible "Clinical Work IQ" scorecard: faithfulness, citation
coverage, retrieval recall, and safety-probe recall. Almost no competitor ships
this; here it's a first-class, publishable benchmark.

Faithfulness uses the deterministic token-overlap proxy by default; set
JUDGE_FAITHFULNESS=true (with a real LLM backend) to use the LLM-as-judge instead.
"""
from __future__ import annotations

from clinical_agent.agents.study_plan import flag_conditions
from clinical_agent.config import get_settings
from clinical_agent.eval.rag_metrics import (
    append_run,
    citation_coverage,
    composite_work_iq,
    faithfulness,
    faithfulness_judge,
    retrieval_prf,
    safety_probe_recall,
)
from clinical_agent.rag.llm import get_llm
from clinical_agent.state import AgentState

# gold evidence chunks expected for the demo patient (HbA1c high + eGFR low)
DEMO_GOLD_CHUNKS = {"ada-hba1c-001", "kdigo-egfr-001"}


def run_work_iq(state: AgentState, record: bool = False) -> AgentState:
    """Reads ``answer``, ``literature``, ``observations``; writes the ``work_iq``
    scorecard (faithfulness, citation coverage, retrieval P/R, safety-probe recall,
    and the composite Clinical Work IQ). See docs/EVALUATION.md for the formulas.
    Set ``record=True`` to append the scorecard to the analytics history."""
    settings = get_settings()
    answer = state.get("answer")
    literature = state.get("literature", [])
    observations = state.get("observations", [])

    context = [c.title for c in literature] + [o.context_line() for o in observations]
    answer_text = answer.text if answer else ""

    if settings.judge_faithfulness:
        llm = get_llm()
        faith = (faithfulness_judge(answer_text, context, llm)
                 if getattr(llm, "name", "stub") != "stub"
                 else faithfulness(answer_text, context))
        faith_method = "llm_judge" if getattr(llm, "name", "stub") != "stub" else "token_overlap"
    else:
        faith = faithfulness(answer_text, context)
        faith_method = "token_overlap"

    cov = citation_coverage(answer) if answer else 0.0
    retrieved_ids = [c.chunk_id for c in literature]
    retr = retrieval_prf(retrieved_ids, DEMO_GOLD_CHUNKS)
    safety = safety_probe_recall(flag_conditions)

    score = composite_work_iq(
        faithfulness_score=faith, citation_cov=cov, retrieval=retr, safety=safety
    )

    scorecard = {
        "clinical_work_iq": score,
        "patient_id": state.get("patient_id"),
        "faithfulness": faith,
        "faithfulness_method": faith_method,
        "citation_coverage": cov,
        "retrieval_precision": retr["precision"],
        "retrieval_recall": retr["recall"],
        "safety_probe_recall": safety["recall"],
        "safety_detail": safety["details"],
    }

    if record:
        try:
            append_run({k: v for k, v in scorecard.items() if k != "safety_detail"},
                       settings.analytics_path)
        except OSError:
            pass  # analytics is best-effort; never fail the pipeline on I/O

    state.update(
        work_iq=scorecard,
        trace=state.get("trace", []) + [f"work_iq: score={score}"],
    )
    return state
