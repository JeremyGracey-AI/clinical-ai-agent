# SMART on FHIR integration

The agent is **vendor-neutral**: it runs against any FHIR R4 server, not a single
EHR. By default it uses synthetic fixtures so nothing external is required; this
page covers both modes and how to go live.

Implementation: [`fhir/`](../src/clinical_agent/fhir/) — `client.py` (httpx +
fixtures), `auth.py` (SMART OAuth2), `patient.py`, `observation.py`.

---

## Two data modes

| | Fixture mode (default) | Live mode |
|---|---|---|
| Constructed as | `FHIRClient(use_fixtures=True)` | `FHIRClient()` (optionally `token=…`) |
| Source | `eval/synthetic.py` canned bundles | HTTP against `FHIR_BASE_URL` |
| Network / creds | none | network; auth if the server requires it |
| Used by | `run_pipeline()`, tests, CLI, UI | `scripts/smoke_test_fhir.py --live` |

```bash
# fixtures
python scripts/smoke_test_fhir.py
# live HAPI public sandbox, real patient id
python scripts/smoke_test_fhir.py --live <patient_id>
```

Fixture smoke output (verbatim):

```
PATIENT: {'id': 'demo-1', 'name': 'Jordan Rivers', 'gender': 'female', 'birth_date': '1968-04-12'}
  OBS: Hemoglobin A1c: 8.2 % (2026-05-01)
  OBS: eGFR: 52.0 mL/min/1.73m2 (2026-05-01)
  OBS: Systolic blood pressure: 128.0 mmHg (2026-05-01)
  OBS: LDL cholesterol: 110.0 mg/dL (2026-05-01)
```

---

## SMART v2 scopes

The system requests SMART App Launch **v2** scopes (the `.cruds` suffix form). Set
in `config.py` / `.env`:

| Scope | Grants | Used by |
|---|---|---|
| `patient/Patient.r` | read demographics | Curator |
| `patient/Observation.rs` | read **and** search observations | Curator |
| `patient/Observation.c` | create observations | Assessment write-back |

> **Read ≠ write.** A `.c` (create) scope does **not** imply read access, and `.r`
> does not imply create. Request every operation you need explicitly. The default
> `SMART_SCOPES` string requests all three plus `launch openid fhirUser`.

Ref: [SMART App Launch v2 — Scopes & Launch Context](https://build.fhir.org/ig/HL7/smart-app-launch/scopes-and-launch-context.html)

---

## The OAuth2 launch flow

`auth.py` provides the two pieces of the authorization-code flow. The **public
HAPI sandbox needs no auth**, so this is wired but optional.

```python
from clinical_agent.fhir.auth import build_authorize_url, token_exchange_payload

# 1. redirect the user to the EHR's /authorize
url = build_authorize_url("https://ehr.example/authorize", state="xyz")
#    → includes response_type, client_id, redirect_uri, scope, state,
#      and aud = FHIR_BASE_URL  (aud is REQUIRED by SMART)

# 2. exchange the returned ?code= for a token at the EHR's /token
payload = token_exchange_payload(code="abc")        # POST this form
# 3. hand the access_token to the client
client = FHIRClient(token=access_token)
```

> The token-exchange **request** is built for you; performing the POST and caching
> the returned `access_token` is left to the host app (it depends on your redirect
> handling). For the public sandbox you can skip all of this.

---

## Observation search parameters

`search_observations()` issues a search with these params
([HL7 Observation search](https://build.fhir.org/observation-search.html)):

| Param | Default sent | Purpose |
|---|---|---|
| `patient` | the patient id | subject filter |
| `_sort` | `-date` | most-recent first |
| `_count` | `50` (Curator passes `20`) | page size |
| `status` | `final` | finalized results only |
| `category` | optional | `vital-signs` / `laboratory` |
| `code` | optional | a specific LOINC measure |

---

## Write-back

`write_assessment_observation()` posts an assessment result as an `Observation`
with category `survey`:

```python
POST /Observation
{ "resourceType": "Observation", "status": "final",
  "category": [{"coding": [{"code": "survey", … }]}],
  "code": {"text": "Clinical learning assessment: diabetes"},
  "subject": {"reference": "Patient/demo-1"},
  "valueQuantity": {"value": 1.0, "unit": "score", … } }
```

> Write-back is **off by default** (`write_back=False` in `run_pipeline()` and the
> UI). Enable it explicitly and pass a live client:
> ```python
> run_pipeline(query, patient_id, use_fixtures=False, write_back=True)
> ```
> In fixture mode a `POST` returns `{"id": "fixture-created", …}` rather than a
> real `201` — useful for testing the plumbing without mutating a server.

---

## Going live — checklist

1. `FHIR_BASE_URL=https://hapi.fhir.org/baseR4` (or your server).
2. If the server needs auth, complete the OAuth2 flow and construct
   `FHIRClient(token=…)`.
3. `python scripts/smoke_test_fhir.py --live <patient_id>` — confirm a real
   Patient + Observations come back.
4. The threshold rules key off LOINC codes (`4548-4`, `48642-3`, `8480-6`,
   `13457-7`); make sure your server's observations carry those codes, or extend
   the `RULES` table ([EXTENDING.md](EXTENDING.md#add-a-conditions-rule)).
