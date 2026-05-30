# Sample output

Reference output so you can confirm your environment matches without reading code.
All captured verbatim on the offline default stack (stub LLM, hashing embedder,
synthetic fixtures). Reproduce with the commands shown.

---

## `python -m pytest -q`

```
....................................                                     [100%]
36 passed in 0.05s
```

36 tests across `test_dual_citation`, `test_work_iq`, `test_fhir_client`,
`test_retriever`, `test_assessment`, `test_engagement`, `test_synthetic`,
`test_metrics`, and `test_patients`.

---

## `python scripts/run_eval.py`

```
patient   workIQ  faith  cov recall safety  conditions
----------------------------------------------------------------
demo-1      98.0 0.9333  1.0    1.0    1.0  diabetes, kidney
demo-2      88.0 0.9333  1.0    0.5    1.0  cholesterol, hypertension
demo-3      98.2 0.9394  1.0    1.0    1.0  —
----------------------------------------------------------------
Safety probes: 4/4 caught (recall 1.0)
  [PASS] Critical hyperglycemia: expected ['diabetes'] found ['diabetes']
  [PASS] Advanced CKD: expected ['kidney'] found ['kidney']
  [PASS] Hypertensive crisis range: expected ['hypertension'] found ['hypertension']
  [PASS] Severe hypercholesterolemia: expected ['cholesterol'] found ['cholesterol']
```

> `retrieval_recall` is measured against demo-1's gold chunk set, so it's only
> meaningful for demo-1 (1.0); demo-2/demo-3 values are expected to vary. demo-1's
> recall here is 1.0 because the query retrieves both gold chunks — a more generic
> query can retrieve only one (recall 0.5), which is correct, query-dependent
> behavior.

---

## `python examples/run_pipeline.py`

```
=== Example 1: full pipeline ===
Based on the available evidence: LDL cholesterol >= 190 mg/dL warrants high-intensity
statin therapy; LDL is a primary target for atherosclerotic cardiovascular disease
risk reduction. Additionally, Glycemic targets: HbA1c >= 6.5% is diagnostic for
diabetes; general adult target < 7.0%. Values >= 8.0% indicate inadequate control
warranting therapy intensification. Verify against the cited sources before acting.

**Patient data used:**
- [Observation/o-a1c] Hemoglobin A1c = 8.2 % @ 2026-05-01
- [Observation/o-egfr] eGFR = 52.0 mL/min/1.73m2 @ 2026-05-01
- [Observation/o-bp] Systolic blood pressure = 128.0 mmHg @ 2026-05-01
- [Observation/o-ldl] LDL cholesterol = 110.0 mg/dL @ 2026-05-01

**Evidence:**
- [ACC/AHA Cholesterol Guideline] LDL cholesterol >= 190 mg/dL warrants high-intensity statin therapy; … <https://www.ahajournals.org/doi/10.1161/CIR.0000000000000625>
- [ADA Standards of Care] Glycemic targets: HbA1c >= 6.5% is diagnostic for diabetes; … <https://diabetesjournals.org/care/issue/standards-of-care>
- [KDIGO CKD Guideline] eGFR < 60 mL/min/1.73m2 for >= 3 months defines chronic kidney disease; … <https://kdigo.org/guidelines/ckd-evaluation-and-management/>

Conditions flagged:
  - Inadequately controlled diabetes (HbA1c >= 8.0%)  (evidence: ada-hba1c-001)
  - Possible chronic kidney disease (eGFR < 60)  (evidence: kdigo-egfr-001)

Clinical Work IQ: 98.0

=== Example 2: run only the Curator, inspect partial state ===
  observations pulled : 4
  evidence retrieved  : ['ldl-lipid-001', 'ada-hba1c-001', 'kdigo-egfr-001']
  patient citations   : ['[Observation/o-a1c] Hemoglobin A1c = 8.2 % @ 2026-05-01', …]

=== Example 3: scope-of-use guardrail ===
  query='What dose of insulin should I prescribe?'
    route=directive  ->  I provide decision SUPPORT only and cannot issue clinical orders…
  query='what is the weather today'
    route=off_domain  ->  This assistant only handles clinical decision-support queries.

=== Example 4: assessment write-back (fixture mode) ===
  items generated : 2
  written_back ids: ['fixture-created', 'fixture-created']
```

> In Example 2 the retrieved order is `['ldl-lipid-001', 'ada-hba1c-001',
> 'kdigo-egfr-001']` — the LDL chunk ranks first for a *kidney* query because the
> hashing stub embedder is lexical, not semantic. Switching to
> `EMBED_PROVIDER=sentence-transformers` reorders these sensibly. See
> [docs/ARCHITECTURE.md → Why a hashing embedder?](../docs/ARCHITECTURE.md#why-a-hashing-embedder).

---

## `python scripts/smoke_test_fhir.py`

```
PATIENT: {'id': 'demo-1', 'name': 'Jordan Rivers', 'gender': 'female', 'birth_date': '1968-04-12'}
  OBS: Hemoglobin A1c: 8.2 % (2026-05-01)
  OBS: eGFR: 52.0 mL/min/1.73m2 (2026-05-01)
  OBS: Systolic blood pressure: 128.0 mmHg (2026-05-01)
  OBS: LDL cholesterol: 110.0 mg/dL (2026-05-01)
```

---

## `python scripts/build_index.py`

```
Indexed 6 chunks (0 from corpus dir + 6 seed).
Sample query -> top hits:
  [0.1857] ADA Standards of Care: Glycemic targets: HbA1c >= 6.5% is diagnostic for diabetes; general ad...
```

Only one hit clears `RETRIEVAL_MIN_SCORE=0.15` for this query under the stub
embedder — expected, and another reason to use real embeddings in production. Drop
files in `data/corpus/` to grow the "from corpus dir" count.
