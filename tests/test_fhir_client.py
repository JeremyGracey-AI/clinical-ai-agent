from clinical_agent.fhir.client import FHIRClient
from clinical_agent.fhir.observation import search_observations
from clinical_agent.fhir.patient import get_patient


def test_fixture_patient():
    client = FHIRClient(use_fixtures=True)
    p = get_patient(client, "demo-1")
    assert p.id == "demo-1"
    assert "Jordan" in (p.name or "")


def test_fixture_observations():
    client = FHIRClient(use_fixtures=True)
    obs = search_observations(client, "demo-1")
    codes = {o.code for o in obs}
    assert "4548-4" in codes  # HbA1c present
    assert all(o.value is not None for o in obs)
