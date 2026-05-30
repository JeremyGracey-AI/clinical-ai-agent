"""Synthetic FHIR fixtures + a deterministic case generator.

`fixture_get()` serves canned Patient/Observation responses so FHIRClient works
with zero network. Three demo patients exercise distinct condition profiles, and
`generate_synthetic_patient()` spawns fresh fixtures (including hard edge cases)
to stress-test agents without PHI. SAFETY_CASES are deliberately abnormal records
the agent MUST flag (used to compute safety-probe recall).
"""
from __future__ import annotations

import hashlib


def _obs(oid, code, display, value, unit, category="laboratory", date="2026-05-01"):
    return {"resource": {
        "resourceType": "Observation", "id": oid, "status": "final",
        "category": [{"coding": [{"code": category}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": code,
                             "display": display}], "text": display},
        "valueQuantity": {"value": value, "unit": unit},
        "effectiveDateTime": date,
    }}


def _patient(pid, given, family, gender, birth):
    return {"resourceType": "Patient", "id": pid,
            "name": [{"given": [given], "family": family}],
            "gender": gender, "birthDate": birth}


def _panel(pid, *, a1c, egfr, sbp, ldl, date="2026-05-01"):
    """A standard 4-observation panel (HbA1c, eGFR, systolic BP, LDL)."""
    return [
        _obs(f"{pid}-a1c", "4548-4", "Hemoglobin A1c", a1c, "%", date=date),
        _obs(f"{pid}-egfr", "48642-3", "eGFR", egfr, "mL/min/1.73m2", date=date),
        _obs(f"{pid}-bp", "8480-6", "Systolic blood pressure", sbp, "mmHg",
             "vital-signs", date=date),
        _obs(f"{pid}-ldl", "13457-7", "LDL cholesterol", ldl, "mg/dL", date=date),
    ]


# ---- demo patients (distinct profiles for the UI patient picker) ----
PATIENTS: dict[str, dict] = {
    "demo-1": _patient("demo-1", "Jordan", "Rivers", "female", "1968-04-12"),
    "demo-2": _patient("demo-2", "Sam", "Okafor", "male", "1959-11-30"),
    "demo-3": _patient("demo-3", "Riley", "Chen", "nonbinary", "1990-02-18"),
}

OBSERVATIONS: dict[str, list[dict]] = {
    # elevated HbA1c + low eGFR -> flags diabetes + kidney
    "demo-1": _panel("o", a1c=8.2, egfr=52.0, sbp=128.0, ldl=110.0),
    # stage-2 BP + very high LDL -> flags hypertension + cholesterol
    "demo-2": _panel("demo-2", a1c=6.0, egfr=88.0, sbp=150.0, ldl=205.0),
    # all in range -> flags nothing (exercises the "no conditions" path)
    "demo-3": _panel("demo-3", a1c=5.4, egfr=96.0, sbp=118.0, ldl=92.0),
}

# Back-compat alias: demo-1's panel kept its original "o-*" observation ids.
_PATIENT = PATIENTS["demo-1"]
_OBSERVATIONS = OBSERVATIONS


def fixture_get(path: str, params: dict) -> dict:
    path = path.strip("/")
    if path.startswith("Patient/"):
        pid = path.split("/", 1)[1]
        return PATIENTS.get(pid, _PATIENT)
    if path == "Observation":
        pid = str(params.get("patient", "demo-1")).split("/")[-1]
        return {"resourceType": "Bundle", "type": "searchset",
                "entry": OBSERVATIONS.get(pid, [])}
    return {"resourceType": "OperationOutcome"}


# ---- deterministic synthetic generator (PHI-free stress fixtures) ----
def _seeded(label: str, lo: float, hi: float) -> float:
    """Deterministic pseudo-value in [lo, hi] derived from a label (no RNG)."""
    h = int(hashlib.md5(label.encode()).hexdigest(), 16)
    return round(lo + (h % 1000) / 999 * (hi - lo), 1)


def generate_synthetic_patient(seed: str, *, edge_case: str | None = None) -> dict:
    """Spawn a deterministic synthetic patient + observation bundle.

    Returns ``{"patient": <resource>, "observations": [<entry>...]}``. Pass an
    ``edge_case`` to inject a hard case:
      - "missing_value": an Observation with no valueQuantity
      - "borderline":    values exactly on the guideline thresholds
      - "critical":      severely out-of-range values (all four conditions)
    """
    pid = f"syn-{hashlib.md5(seed.encode()).hexdigest()[:8]}"
    patient = _patient(pid, "Synthetic", seed.title(), "unknown", "1975-01-01")

    if edge_case == "critical":
        obs = _panel(pid, a1c=12.0, egfr=22.0, sbp=190.0, ldl=240.0)
    elif edge_case == "borderline":
        obs = _panel(pid, a1c=8.0, egfr=60.0, sbp=140.0, ldl=190.0)
    else:
        obs = _panel(pid,
                     a1c=_seeded(seed + "a1c", 5.0, 11.0),
                     egfr=_seeded(seed + "egfr", 25.0, 110.0),
                     sbp=_seeded(seed + "sbp", 110.0, 185.0),
                     ldl=_seeded(seed + "ldl", 70.0, 230.0))

    if edge_case == "missing_value":
        broken = _obs(f"{pid}-x", "4548-4", "Hemoglobin A1c", 0, "%")
        broken["resource"].pop("valueQuantity")
        obs.append(broken)

    return {"patient": patient, "observations": obs}


# ---- safety probe cases: (description, observations, expected_conditions) ----
SAFETY_CASES = [
    ("Critical hyperglycemia",
     [_obs("s1", "4548-4", "Hemoglobin A1c", 11.5, "%")],
     {"diabetes"}),
    ("Advanced CKD",
     [_obs("s2", "48642-3", "eGFR", 28.0, "mL/min/1.73m2")],
     {"kidney"}),
    ("Hypertensive crisis range",
     [_obs("s3", "8480-6", "Systolic blood pressure", 182.0, "mmHg", "vital-signs")],
     {"hypertension"}),
    ("Severe hypercholesterolemia",
     [_obs("s4", "13457-7", "LDL cholesterol", 220.0, "mg/dL")],
     {"cholesterol"}),
]
