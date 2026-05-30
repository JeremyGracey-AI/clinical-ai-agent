"""Tests for the synthetic fixtures + deterministic case generator."""
from clinical_agent.agents.study_plan import flag_conditions
from clinical_agent.eval.synthetic import (
    PATIENTS,
    fixture_get,
    generate_synthetic_patient,
)
from clinical_agent.models.observation import Observation


def _topics(bundle):
    obs = [Observation.from_fhir(o["resource"]) for o in bundle["observations"]]
    return {f["topic"] for f in flag_conditions(obs)}


def test_three_demo_patients_served():
    assert {"demo-1", "demo-2", "demo-3"} <= set(PATIENTS)
    assert fixture_get("Patient/demo-2", {})["id"] == "demo-2"
    bundle = fixture_get("Observation", {"patient": "demo-2"})
    assert bundle["type"] == "searchset" and bundle["entry"]


def test_generator_is_deterministic():
    assert generate_synthetic_patient("alpha") == generate_synthetic_patient("alpha")
    b = generate_synthetic_patient("alpha")
    assert b["patient"]["resourceType"] == "Patient"
    assert len(b["observations"]) == 4


def test_edge_case_critical_flags_everything():
    assert _topics(generate_synthetic_patient("z", edge_case="critical")) == {
        "diabetes", "kidney", "hypertension", "cholesterol"}


def test_edge_case_missing_value_is_safe():
    bundle = generate_synthetic_patient("y", edge_case="missing_value")
    obs = [Observation.from_fhir(o["resource"]) for o in bundle["observations"]]
    assert any(o.value is None for o in obs)
    flag_conditions(obs)  # must not raise on a missing value
