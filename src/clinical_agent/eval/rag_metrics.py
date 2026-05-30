"""Reproducible eval harness — the validation differentiator.

Metrics:
  - faithfulness:      fraction of answer tokens supported by retrieved context
  - citation_coverage: does a grounded answer carry >=1 literature + patient cite?
  - retrieval_precision/recall: vs. an expected gold chunk set
  - safety_probe_recall: fraction of abnormal synthetic cases correctly flagged

All metrics roll up into a single composite "Clinical Work IQ" score.
"""
from __future__ import annotations

import re

from clinical_agent.models.citation import GroundedAnswer

_STOP = set("the a an of to and or is are be in on for with that this it as at by from "
            "based available evidence verify against cited sources additionally".split())


def _content_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 2}


def faithfulness(answer_text: str, context: list[str]) -> float:
    """Token-overlap groundedness: what share of answer content appears in context."""
    ans = _content_tokens(answer_text)
    if not ans:
        return 1.0
    ctx = set()
    for c in context:
        ctx |= _content_tokens(c)
    supported = len(ans & ctx)
    return round(supported / len(ans), 4)


def citation_coverage(answer: GroundedAnswer) -> float:
    """1.0 if the answer carries both literature and patient provenance, else partial."""
    score = 0.0
    if answer.literature:
        score += 0.5
    if answer.patient:
        score += 0.5
    return score


def retrieval_prf(retrieved_ids: list[str], gold_ids: set[str]) -> dict[str, float]:
    if not retrieved_ids:
        return {"precision": 0.0, "recall": 0.0}
    hits = sum(1 for r in retrieved_ids if r in gold_ids)
    precision = hits / len(retrieved_ids)
    recall = hits / len(gold_ids) if gold_ids else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4)}


def safety_probe_recall(flag_fn) -> dict:
    """Run every SAFETY_CASE through a condition-flagging fn; measure recall."""
    from clinical_agent.eval.synthetic import SAFETY_CASES
    from clinical_agent.models.observation import Observation

    caught, total, details = 0, 0, []
    for desc, raw_obs, expected_topics in SAFETY_CASES:
        observations = [Observation.from_fhir(o["resource"]) for o in raw_obs]
        flags = flag_fn(observations)
        found_topics = {f["topic"] for f in flags}
        ok = expected_topics.issubset(found_topics)
        caught += int(ok)
        total += 1
        details.append({"case": desc, "expected": sorted(expected_topics),
                        "found": sorted(found_topics), "passed": ok})
    return {"recall": round(caught / total, 4) if total else 0.0,
            "caught": caught, "total": total, "details": details}


def faithfulness_judge(answer_text: str, context: list[str], llm) -> float:
    """LLM-as-judge groundedness in [0, 1] (used when JUDGE_FAITHFULNESS=true).

    A stricter, paraphrase-aware alternative to the token-overlap proxy. Falls back
    to 0.0 if the model returns no parseable score."""
    if not answer_text.strip():
        return 1.0
    ctx = "\n".join(f"- {c}" for c in context)
    raw = llm.chat(
        system="You are a strict clinical faithfulness grader. Reply with ONLY a number.",
        user=("Rate 0.0-1.0 how fully every claim in the ANSWER is supported by the "
              f"CONTEXT (1.0 = fully grounded).\nCONTEXT:\n{ctx}\n\nANSWER: {answer_text}"),
    )
    m = re.search(r"[01](?:\.\d+)?", raw)
    return round(min(1.0, max(0.0, float(m.group()))), 4) if m else 0.0


def composite_work_iq(*, faithfulness_score: float, citation_cov: float,
                      retrieval: dict, safety: dict) -> float:
    """Weighted 'Clinical Work IQ' index in [0, 100]."""
    parts = {
        "faithfulness": (faithfulness_score, 0.30),
        "citation_coverage": (citation_cov, 0.20),
        "retrieval_recall": (retrieval.get("recall", 0.0), 0.20),
        "safety_recall": (safety.get("recall", 0.0), 0.30),
    }
    score = sum(val * w for val, w in parts.values())
    return round(score * 100, 1)


def append_run(scorecard: dict, path: str) -> dict:
    """Append a scorecard to the JSONL analytics history (Analytics tab feed)."""
    import json
    import os
    import time
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rec = {**scorecard, "ts": round(time.time(), 3)}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def load_history(path: str) -> list[dict]:
    """Read the analytics history (newest last). Returns [] if absent/empty."""
    import json
    import os
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out
