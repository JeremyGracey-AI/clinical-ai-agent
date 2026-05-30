"""Curator -> Evidence-Fusion Engine (the moat).

Does what no competitor offers in open form: conditions retrieval on THIS
patient's live FHIR data, then emits a GroundedAnswer carrying BOTH
literature citations and patient-data citations.

Flow:
  1. Pull Patient + recent Observations (FHIR).
  2. Build a patient-CONDITIONED retrieval query (inject real lab values).
  3. Retrieve evidence (provenance-tagged).
  4. Generate a grounded answer.
  5. Attach dual citations: which patient data + which literature were used.
"""
from __future__ import annotations

from clinical_agent.config import get_settings
from clinical_agent.fhir.client import FHIRClient
from clinical_agent.fhir.observation import search_observations
from clinical_agent.fhir.patient import get_patient
from clinical_agent.models.citation import GroundedAnswer, PatientCitation
from clinical_agent.models.observation import Observation
from clinical_agent.models.patient import Patient
from clinical_agent.rag.llm import get_llm
from clinical_agent.rag.prompts import SYSTEM_GROUNDED
from clinical_agent.rag.retriever import Retriever
from clinical_agent.state import AgentState


def _conditioned_query(query: str, patient: Patient, obs: list[Observation]) -> str:
    """Inject patient context so retrieved evidence is specific to THIS patient."""
    facts = "; ".join(o.context_line() for o in obs[:6])
    return f"{query} | patient: {patient.context_line()} | findings: {facts}"


def _patient_citations(obs: list[Observation]) -> list[PatientCitation]:
    cites = []
    for o in obs:
        if o.value is None:
            continue
        cites.append(PatientCitation(
            resource=f"Observation/{o.id}",
            label=o.display or o.code or "observation",
            value=f"{o.value} {o.unit}".strip(),
            effective=o.effective,
        ))
    return cites


def run_curator(state: AgentState, client: FHIRClient,
                retriever: Retriever | None = None) -> AgentState:
    """Evidence-Fusion Engine. Reads ``query`` + ``patient_id``; writes ``patient``,
    ``observations``, ``literature``, ``patient_citations``, and the dual-cited
    ``answer``. Conditions retrieval on this patient's live values, then emits a
    ``GroundedAnswer`` carrying both literature and patient-data provenance."""
    retriever = retriever or Retriever()
    patient_id = state["patient_id"]

    # 1. live patient context
    patient = get_patient(client, patient_id)
    observations = search_observations(client, patient_id, count=20)

    # 2. patient-conditioned retrieval (with a one-shot refine loop)
    cq = _conditioned_query(state["query"], patient, observations)
    literature = retriever.retrieve(cq)
    refined = False
    if get_settings().retrieval_refine and not literature:
        # nothing cleared the confidence floor — broaden with abnormal findings
        broadened = cq + " | " + " ".join(
            o.display or o.code or "" for o in observations if o.value is not None)
        literature = retriever.retrieve(broadened, min_score=0.0)
        refined = True

    # 3. grounded generation over fused context
    context = [c.title for c in literature] + [o.context_line() for o in observations]
    llm = get_llm()
    text = llm.generate(system=SYSTEM_GROUNDED, user=state["query"], context=context)

    # 4. dual citations
    patient_cites = _patient_citations(observations)
    answer = GroundedAnswer(text=text, literature=literature, patient=patient_cites)

    state.update(
        patient=patient,
        observations=observations,
        literature=literature,
        patient_citations=patient_cites,
        answer=answer,
        trace=state.get("trace", []) + [
            f"curator: {len(observations)} obs, {len(literature)} evidence chunks"
            + (" (refined)" if refined else "")
        ],
    )
    return state
