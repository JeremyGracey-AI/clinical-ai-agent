"""Hit a FHIR server (or fixtures) and print a Patient + recent Observations.

Usage:
  python scripts/smoke_test_fhir.py            # offline fixtures
  python scripts/smoke_test_fhir.py --live ID  # live HAPI, real patient id
"""
import sys

from clinical_agent.fhir.client import FHIRClient
from clinical_agent.fhir.observation import search_observations
from clinical_agent.fhir.patient import get_patient


def main():
    live = "--live" in sys.argv
    patient_id = sys.argv[-1] if live and len(sys.argv) > 2 else "demo-1"
    client = FHIRClient(use_fixtures=not live)

    patient = get_patient(client, patient_id)
    print("PATIENT:", patient.model_dump())
    for o in search_observations(client, patient_id, count=10):
        print("  OBS:", o.context_line())


if __name__ == "__main__":
    main()
