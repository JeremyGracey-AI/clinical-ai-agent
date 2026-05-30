# Evaluation — the Clinical Work IQ harness

The eval harness is the project's second differentiator: a **reproducible
scorecard almost no competitor ships** (competitor validation is typically
vendor-marketing, not reproducible science). It runs entirely on synthetic data,
so it is PHI-free and deterministic.

Implementation: [`eval/rag_metrics.py`](../src/clinical_agent/eval/rag_metrics.py)
(metrics) + [`agents/work_iq.py`](../src/clinical_agent/agents/work_iq.py)
(wiring) + [`eval/synthetic.py`](../src/clinical_agent/eval/synthetic.py)
(fixtures & safety cases).

---

## The scorecard

```json
{
  "clinical_work_iq": 98.0,
  "patient_id": "demo-1",
  "faithfulness": 0.9333,
  "faithfulness_method": "token_overlap",
  "citation_coverage": 1.0,
  "retrieval_precision": 0.6667,
  "retrieval_recall": 1.0,
  "safety_probe_recall": 1.0,
  "safety_detail": [ … per-case pass/fail … ]
}
```

Run it across every demo patient with `python scripts/run_eval.py`, which prints a
per-patient scorecard table and the shared safety-probe result.

---

## Metrics, one by one

### Faithfulness — `faithfulness(answer_text, context)`

Token-overlap groundedness: of the answer's **content tokens** (lowercased,
stop-words and ≤2-char tokens removed), what share also appear in the retrieved
context?

```
faithfulness = |answer_tokens ∩ context_tokens| / |answer_tokens|
```

Returns `1.0` for an empty answer (nothing unsupported). In the demo, 0.9333.

> **Limitation:** this is a lexical proxy for groundedness, not entailment. It
> rewards copying context (which the extractive `StubLLM` does by construction)
> and can miss paraphrase or contradiction. The stop-word list is tuned to the
> stub's boilerplate ("based", "available", "verify", …) so those don't inflate
> the score.
>
> **LLM-as-judge alternative (built in).** Set `JUDGE_FAITHFULNESS=true` with a real
> backend (`LLM_PROVIDER=openai`/`anthropic`) and Work IQ uses
> `faithfulness_judge()` instead — it asks the model to rate 0–1 how fully every
> claim is supported by the context, and falls back to `0.0` if no score parses.
> The scorecard records which was used in `faithfulness_method`.

### Citation coverage — `citation_coverage(answer)`

Does a grounded answer carry **both** kinds of provenance?

```
+0.5 if answer.literature is non-empty
+0.5 if answer.patient    is non-empty
→ 1.0 when both present
```

This directly measures the dual-citation property that the whole product is built
around.

### Retrieval precision / recall — `retrieval_prf(retrieved_ids, gold_ids)`

Standard set-overlap against a gold chunk set:

```
precision = |retrieved ∩ gold| / |retrieved|
recall    = |retrieved ∩ gold| / |gold|
```

The demo gold set is `{"ada-hba1c-001", "kdigo-egfr-001"}` (the two conditions the
demo patient should trigger). The demo retrieves 3 chunks, 2 of them gold →
precision 0.6667, recall 1.0.

### Safety-probe recall — `safety_probe_recall(flag_fn)`

The most clinically important metric. Runs every case in `SAFETY_CASES` — abnormal
synthetic records the agent **must** catch — through the condition flagger and
measures recall:

```
recall = (cases where expected_topics ⊆ found_topics) / (total cases)
```

The four shipped cases (all pass in the demo):

| Case | Observation | Must flag |
|---|---|---|
| Critical hyperglycemia | HbA1c 11.5 % | `diabetes` |
| Advanced CKD | eGFR 28 | `kidney` |
| Hypertensive crisis range | SBP 182 | `hypertension` |
| Severe hypercholesterolemia | LDL 220 | `cholesterol` |

Because the probes call the **same** `flag_conditions()` the Study Plan agent uses,
the eval tests the real code path, not a parallel reimplementation.

---

## Composite — `composite_work_iq(...)`

A weighted index in `[0, 100]`:

| Component | Weight |
|---|---|
| Faithfulness | 0.30 |
| Citation coverage | 0.20 |
| Retrieval recall | 0.20 |
| Safety recall | 0.30 |

```
work_iq = 100 × (0.30·faith + 0.20·citation + 0.20·recall + 0.30·safety)
```

Safety and faithfulness carry the most weight — a system that misses a critical
lab or hallucinates is penalized hardest. Worked demo value:

```
100 × (0.30·0.9333 + 0.20·1.0 + 0.20·1.0 + 0.30·1.0)
= 100 × (0.2800 + 0.20 + 0.20 + 0.30) = 98.0
```

---

## Running it

```bash
python -m clinical_agent.cli      # prints the full scorecard + safety_detail
python -m pytest tests/test_work_iq.py -v
```

`tests/test_work_iq.py` asserts the invariants: faithfulness bounds, full citation
coverage, **all safety probes caught** (`recall == 1.0`), the demo patient flags
exactly `{diabetes, kidney}`, and the composite hits 100 when every input is
perfect.

## Adding a safety probe

See [EXTENDING.md → Add a Conditions rule](EXTENDING.md#add-a-conditions-rule) —
adding a rule + a `SAFETY_CASES` entry extends both the advisor and this harness
in one change.

## What this is *not*

A token-overlap + threshold harness is a **scaffold for a real eval**, not a
clinical validation. It demonstrates the *shape* of a reproducible benchmark —
faithfulness, coverage, retrieval quality, safety recall, one composite index —
which is the credible signal the landscape analysis calls for. Promoting it to a
published benchmark means: real LLM-judge faithfulness, a larger and externally
reviewed gold/safety set, and prospective clinical review.
