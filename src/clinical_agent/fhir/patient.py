"""GET /Patient/{id} -> Patient model.  Scope: patient/Patient.r"""
from __future__ import annotations

from clinical_agent.fhir.client import FHIRClient
from clinical_agent.models.patient import Patient


def get_patient(client: FHIRClient, patient_id: str) -> Patient:
    resource = client.get(f"Patient/{patient_id}")
    return Patient.from_fhir(resource)
