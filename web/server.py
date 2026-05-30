"""FastAPI backend for the carbon-style clinical dashboard.

Wraps the existing ``run_pipeline()`` (unchanged) behind a small JSON + SSE API and
serves a bespoke static frontend. This is the Docker-SDK Space entrypoint:

    uvicorn server:app --app-dir web --host 0.0.0.0 --port 7860

Secrets (e.g. ANTHROPIC_API_KEY) stay server-side and are never sent to the client.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Fallback for running from source without `pip install` (local dev). In the
# Docker image the package is installed, so this is a harmless no-op.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from clinical_agent.config import get_settings  # noqa: E402
from clinical_agent.eval.rag_metrics import load_history  # noqa: E402
from clinical_agent.eval.synthetic import OBSERVATIONS, PATIENTS  # noqa: E402
from clinical_agent.models.observation import Observation  # noqa: E402
from clinical_agent.orchestrator import run_pipeline  # noqa: E402
from clinical_agent.rag.llm import get_llm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")

app = FastAPI(title="Clinical AI Agent", docs_url="/api/docs")
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _name(resource: dict) -> str:
    names = resource.get("name") or []
    if not names:
        return resource.get("id", "unknown")
    n = names[0]
    return (" ".join(n.get("given", [])) + " " + n.get("family", "")).strip()


def _state_to_json(state: dict) -> dict:
    ans = state.get("answer")
    lit = ans.literature if ans else []
    pat = ans.patient if ans else []
    return {
        "answer_text": ans.text if ans else "",
        "patient_citations": [
            {"resource": c.resource, "label": c.label, "value": c.value, "effective": c.effective}
            for c in pat
        ],
        "literature": [
            {"chunk_id": c.chunk_id, "title": c.title, "source": c.source,
             "url": c.url, "score": c.score}
            for c in lit
        ],
        "flagged_conditions": state.get("flagged_conditions", []),
        "study_plan": state.get("study_plan", []),
        "assessment": state.get("assessment", {}),
        "work_iq": state.get("work_iq", {}),
        "route": state.get("route"),
        "confidence": state.get("confidence"),
        "digest": state.get("digest"),
        "nudges": state.get("nudges", []),
        "trace": state.get("trace", []),
    }


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/api/config")
def config():
    s = get_settings()
    return {"llm_provider": s.llm_provider, "llm_ready": s.llm_ready,
            "backend": getattr(get_llm(), "name", "stub"), "offline": s.offline}


@app.get("/api/patients")
def patients():
    out = []
    for pid, resource in PATIENTS.items():
        labs = [Observation.from_fhir(o["resource"]) for o in OBSERVATIONS.get(pid, [])]
        out.append({
            "id": pid,
            "name": _name(resource),
            "gender": resource.get("gender"),
            "birth_date": resource.get("birthDate"),
            "labs": [{"label": o.display or o.code, "value": o.value, "unit": o.unit}
                     for o in labs],
        })
    return out


def _run(body: dict) -> dict:
    query = (body.get("query") or "").strip() or "How should I manage this patient?"
    patient_id = body.get("patient_id") or "demo-1"
    state = run_pipeline(query, patient_id, record_analytics=True)
    return _state_to_json(state)


@app.post("/api/run")
async def run(request: Request):
    return JSONResponse(_run(await request.json()))


@app.post("/api/stream")
async def stream(request: Request):
    """Run the pipeline, then SSE-stream the answer word-by-word for a live feel,
    followed by one final event carrying the full structured result."""
    data = _run(await request.json())

    async def gen():
        for word in data["answer_text"].split(" "):
            yield f"data: {json.dumps({'delta': word + ' '})}\n\n"
            await asyncio.sleep(0.018)
        yield f"data: {json.dumps({'done': True, 'result': data})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/analytics")
def analytics():
    return load_history(get_settings().analytics_path)


@app.get("/healthz")
def healthz():
    return {"ok": True}
