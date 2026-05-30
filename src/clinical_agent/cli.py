"""CLI smoke entrypoint: runs the full pipeline offline and prints the result."""
from __future__ import annotations

import json

from clinical_agent.orchestrator import run_pipeline


def smoke() -> None:
    state = run_pipeline(
        "How should I manage this patient's diabetes?", "demo-1", use_fixtures=True
    )
    ans = state["answer"]
    print("=== GROUNDED ANSWER ===")
    print(ans.render_markdown())
    print("\n=== CONDITIONS FLAGGED ===")
    for f in state["flagged_conditions"]:
        print(f" - {f['condition']}  ({f['trigger']})")
    print("\n=== CLINICAL WORK IQ ===")
    print(json.dumps(state["work_iq"], indent=2))
    print("\n=== TRACE ===")
    print("\n".join(state["trace"]))


if __name__ == "__main__":
    smoke()
