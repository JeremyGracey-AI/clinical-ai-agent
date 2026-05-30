"""Gradio UI. Lazily imported so the core package stays dependency-light.

Tabs: Grounded Answer · Conditions Advisor · Study Plan · Assessment ·
Clinical Work IQ · Analytics · Trace · About. Each run records its scorecard to
the analytics history so the Analytics tab shows a time series.
"""
from __future__ import annotations

import json

from clinical_agent.config import get_settings
from clinical_agent.eval.rag_metrics import load_history
from clinical_agent.eval.synthetic import PATIENTS
from clinical_agent.orchestrator import run_pipeline
from clinical_agent.ui.citations import render_header_md

_ANALYTICS_COLS = ["run", "patient", "work_iq", "faithfulness", "retr_recall", "safety"]


def _format_answer(state) -> str:
    ans = state.get("answer")
    body = ans.render_markdown() if ans else "_No answer._"
    head = []
    if state.get("confidence"):
        head.append(f"**Retrieval confidence:** `{state['confidence']}`")
    if state.get("digest"):
        head.append(f"**Session:** {state['digest']}")
    nudges = state.get("nudges") or []
    if nudges:
        head.append("**Nudges:**\n" + "\n".join(f"- {n}" for n in nudges))
    header = "\n\n".join(head)
    return f"{header}\n\n---\n\n{body}" if header else body


def _format_conditions(state) -> str:
    flags = state.get("flagged_conditions", [])
    if not flags:
        return "_No conditions flagged for this patient's current observations._"
    return "\n".join(
        f"- **{f['condition']}** (trigger: {f['trigger']})" for f in flags
    )


def _format_study_plan(state) -> str:
    mods = state.get("study_plan", [])
    if not mods:
        return "_No learning modules — nothing flagged._"
    lines = []
    for m in mods:
        src, url = m.get("evidence_source") or "", m.get("evidence_url") or ""
        ev = f"[{src}]({url})" if url else (src or "—")
        lines.append(
            f"{m['order']}. **{m['topic']}** · _{m['difficulty']}_ (mastery {m['mastery']})  \n"
            f"   {m['objective']}  \n"
            f"   _based on:_ {m['based_on']} · _evidence:_ {ev}"
        )
    return "\n".join(lines)


def _format_assessment(state) -> str:
    a = state.get("assessment", {})
    items = a.get("items", [])
    if not items:
        return "_No assessment items._"
    out = []
    for i, it in enumerate(items, 1):
        out.append(f"**Q{i} — {it['topic']}.** {it['question']}")
        for j, opt in enumerate(it.get("options", [])):
            mark = "  ✅" if j == it.get("answer_index") else ""
            out.append(f"- {chr(65 + j)}. {opt}{mark}")
        if it.get("rationale"):
            out.append(f"  \n_Rationale:_ {it['rationale']}")
        out.append("")
    return "\n".join(out)


def _format_work_iq(state) -> str:
    return "```json\n" + json.dumps(state.get("work_iq", {}), indent=2) + "\n```"


def _analytics_rows() -> list[list]:
    hist = load_history(get_settings().analytics_path)
    rows = []
    for i, r in enumerate(hist[-50:], 1):
        rows.append([i, r.get("patient_id"), r.get("clinical_work_iq"),
                     r.get("faithfulness"), r.get("retrieval_recall"),
                     r.get("safety_probe_recall")])
    return rows


def _run(query: str, patient_id: str):
    state = run_pipeline(query, patient_id, use_fixtures=True, record_analytics=True)
    return (_format_answer(state), _format_conditions(state), _format_study_plan(state),
            _format_assessment(state), _format_work_iq(state),
            _analytics_rows(), "\n".join(state.get("trace", [])))


def build_demo():
    import gradio as gr  # lazy

    patients = list(PATIENTS)

    with gr.Blocks(title="Clinical AI Agent") as demo:
        gr.Markdown(render_header_md())
        with gr.Row():
            query = gr.Textbox(label="Clinical question", scale=3,
                               value="How should I manage this patient's diabetes?")
            patient_id = gr.Dropdown(label="Patient", choices=patients,
                                     value="demo-1", scale=1)
        run_btn = gr.Button("Run pipeline", variant="primary")
        with gr.Tabs():
            with gr.Tab("Grounded Answer"):
                answer = gr.Markdown()
            with gr.Tab("Conditions Advisor"):
                conditions = gr.Markdown()
            with gr.Tab("Study Plan"):
                study_plan = gr.Markdown()
            with gr.Tab("Assessment"):
                assessment = gr.Markdown()
            with gr.Tab("Clinical Work IQ"):
                work_iq = gr.Markdown()
            with gr.Tab("Analytics"):
                gr.Markdown("Clinical Work IQ per run (most recent 50):")
                analytics = gr.Dataframe(headers=_ANALYTICS_COLS, value=_analytics_rows(),
                                         interactive=False, wrap=True)
            with gr.Tab("Trace"):
                trace = gr.Textbox(label="Agent trace", lines=6)
            with gr.Tab("About"):
                gr.Markdown(render_header_md())
        run_btn.click(
            _run, [query, patient_id],
            [answer, conditions, study_plan, assessment, work_iq, analytics, trace],
        )
    return demo
