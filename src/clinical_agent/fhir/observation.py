"""Observation search + write-back.

Search scope:  patient/Observation.rs
Create scope:  patient/Observation.c

Search params per HL7 FHIR: patient, category, code, date, _sort, _count, status.
Ref: https://build.fhir.org/observation-search.html
"""
from __future__ import annotations

from clinical_agent.fhir.client import FHIRClient
from clinical_agent.models.observation import Observation


def search_observations(
    client: FHIRClient,
    patient_id: str,
    *,
    category: str | None = None,
    code: str | None = None,
    count: int = 50,
) -> list[Observation]:
    params: dict[str, str | int] = {
        "patient": patient_id,
        "_sort": "-date",
        "_count": count,
        "status": "final",
    }
    if category:
        params["category"] = category
    if code:
        params["code"] = code

    bundle = client.get("Observation", params=params)
    entries = bundle.get("entry", []) or []
    return [Observation.from_fhir(e["resource"]) for e in entries if "resource" in e]


def write_assessment_observation(
    client: FHIRClient, patient_id: str, score: float, topic: str
) -> dict:
    """POST an assessment result as an Observation (category=survey)."""
    body = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "survey",
        }]}],
        "code": {"text": f"Clinical learning assessment: {topic}"},
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": score, "unit": "score", "system": "http://unitsofmeasure.org"},
    }
    return client.post("Observation", body)
