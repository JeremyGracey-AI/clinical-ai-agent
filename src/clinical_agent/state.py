"""Shared agent state flowing through the orchestrator pipeline.

`AgentState` is the single dict every agent receives and returns. The contract is
**additive**: an agent reads keys written by earlier agents and `state.update(...)`s
its own outputs (plus a `trace` line) — it never deletes a key a prior agent wrote.
Because of this you can inspect the partial result after any agent.

Who writes what (order = pipeline order; see docs/ARCHITECTURE.md and docs/AGENTS.md):

    key                  written by    notes
    -------------------  ------------  --------------------------------------------
    query, patient_id    (input)       the request
    learner_profile      input/Asmt    {topic: mastery 0..1}; drives difficulty scaling
    responses            (input)       {topic: selected_index} to grade (optional)
    patient              Curator       parsed demographics
    observations         Curator       recent vitals/labs (FHIR search)
    literature           Curator       retrieved evidence chunks (provenance-tagged)
    patient_citations    Curator       FHIR data points used in the answer
    answer               Curator       GroundedAnswer; mutated in place by Engagement
    flagged_conditions   Study Plan    threshold-rule hits (Conditions Advisor)
    study_plan           Study Plan    ordered learning modules
    route                Engagement    'clinical' | 'directive' | 'off_domain' (advisory)
    nudges, digest       Engagement    adherence prompts + session roll-up
    confidence           Engagement    retrieval confidence ('high'|'moderate'|'low')
    assessment           Assessment    MCQ items, gradings, mastery (+ write-back ids)
    work_iq              Work IQ        the Clinical Work IQ scorecard
    trace                every agent   human-readable execution log
"""
from __future__ import annotations

from typing import Any, TypedDict

from clinical_agent.models.citation import GroundedAnswer, LiteratureCitation, PatientCitation
from clinical_agent.models.observation import Observation
from clinical_agent.models.patient import Patient


class AgentState(TypedDict, total=False):
    # input
    query: str
    patient_id: str
    learner_profile: dict[str, float]   # {topic: mastery 0..1}
    responses: dict[str, int]           # {topic: selected_index} to grade

    # populated by Curator (Evidence-Fusion Engine)
    patient: Patient | None
    observations: list[Observation]
    literature: list[LiteratureCitation]
    patient_citations: list[PatientCitation]

    # populated by downstream agents
    answer: GroundedAnswer | None
    study_plan: list[dict[str, Any]]
    flagged_conditions: list[dict[str, Any]]
    nudges: list[str]
    digest: str
    confidence: str
    assessment: dict[str, Any]
    work_iq: dict[str, Any]

    # control
    route: str          # set by Engagement; advisory — does NOT branch the pipeline
    trace: list[str]
