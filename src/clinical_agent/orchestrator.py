"""Orchestrator — two interchangeable backends for the SAME linear flow:

    curator -> study_plan -> engagement -> assessment -> work_iq -> END

The Curator (Evidence-Fusion Engine) runs first so every downstream agent shares
the same patient context + provenance-tagged evidence. The flow is strictly
linear — Engagement's ``route`` is advisory and does not branch the graph.

- ``run_pipeline()``      plain Python, zero extra deps — used by app.py, cli.py,
                          and the tests. This is the default.
- ``build_langgraph_app()`` the identical graph compiled as a LangGraph
                          StateGraph; opt-in (needs the ``[full]`` extra). Provided
                          for parity with the blueprint and LangGraph tooling — it
                          is never auto-selected.
"""
from __future__ import annotations

from clinical_agent.agents.assessment import run_assessment
from clinical_agent.agents.curator import run_curator
from clinical_agent.agents.engagement import run_engagement
from clinical_agent.agents.study_plan import run_study_plan
from clinical_agent.agents.work_iq import run_work_iq
from clinical_agent.fhir.client import FHIRClient
from clinical_agent.rag.retriever import Retriever
from clinical_agent.state import AgentState


def run_pipeline(query: str, patient_id: str, *, use_fixtures: bool = True,
                 write_back: bool = False, learner_profile: dict | None = None,
                 responses: dict | None = None,
                 record_analytics: bool = False) -> AgentState:
    """Run the full 5-agent pipeline. Defaults to offline fixture mode.

    Optional inputs:
      learner_profile  {topic: mastery 0..1} — drives Study Plan difficulty scaling.
      responses        {topic: selected_index} — graded by the Assessment agent.
      write_back       POST graded results back as FHIR Observations.
      record_analytics append the Work IQ scorecard to the analytics history.
    """
    client = FHIRClient(use_fixtures=use_fixtures)
    retriever = Retriever()

    state: AgentState = {"query": query, "patient_id": patient_id, "trace": []}
    if learner_profile:
        state["learner_profile"] = dict(learner_profile)
    if responses:
        state["responses"] = dict(responses)

    state = run_curator(state, client, retriever)
    state = run_study_plan(state)
    state = run_engagement(state)
    state = run_assessment(state, client, write_back=write_back)
    state = run_work_iq(state, record=record_analytics)
    return state


def build_langgraph_app():
    """Optional: compile the same flow as a LangGraph StateGraph (needs [full])."""
    from langgraph.graph import END, StateGraph  # lazy import

    client = FHIRClient(use_fixtures=True)
    retriever = Retriever()
    g = StateGraph(AgentState)
    g.add_node("curator", lambda s: run_curator(s, client, retriever))
    g.add_node("study_plan", run_study_plan)
    g.add_node("engagement", run_engagement)
    g.add_node("assessment", lambda s: run_assessment(s, client))
    g.add_node("work_iq", run_work_iq)
    g.set_entry_point("curator")
    g.add_edge("curator", "study_plan")
    g.add_edge("study_plan", "engagement")
    g.add_edge("engagement", "assessment")
    g.add_edge("assessment", "work_iq")
    g.add_edge("work_iq", END)
    return g.compile()
