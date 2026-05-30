"""Run the Clinical Work IQ harness across every demo patient + a synthetic case.

Usage:  python scripts/run_eval.py
Prints a per-patient scorecard table and the shared safety-probe result.
"""
from clinical_agent.agents.study_plan import flag_conditions
from clinical_agent.eval.rag_metrics import safety_probe_recall
from clinical_agent.eval.synthetic import PATIENTS
from clinical_agent.orchestrator import run_pipeline


def main() -> None:
    print(f"{'patient':9} {'workIQ':>6} {'faith':>6} {'cov':>4} {'recall':>6} "
          f"{'safety':>6}  conditions")
    print("-" * 64)
    for pid in PATIENTS:
        s = run_pipeline("assess and manage this patient", pid)
        wq = s["work_iq"]
        conds = ", ".join(sorted(f["topic"] for f in s["flagged_conditions"])) or "—"
        print(f"{pid:9} {wq['clinical_work_iq']:6} {wq['faithfulness']:6} "
              f"{wq['citation_coverage']:4} {wq['retrieval_recall']:6} "
              f"{wq['safety_probe_recall']:6}  {conds}")

    safety = safety_probe_recall(flag_conditions)
    print("-" * 64)
    print(f"Safety probes: {safety['caught']}/{safety['total']} caught "
          f"(recall {safety['recall']})")
    for d in safety["details"]:
        mark = "PASS" if d["passed"] else "FAIL"
        print(f"  [{mark}] {d['case']}: expected {d['expected']} found {d['found']}")


if __name__ == "__main__":
    main()
