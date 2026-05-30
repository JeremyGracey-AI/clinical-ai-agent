"""Dual-citation primitives — the differentiator.

Every grounded answer carries BOTH:
  - LiteratureCitation: the published evidence it rests on (corpus chunk + URL)
  - PatientCitation:     the specific FHIR data point it used (resource + value + date)

This is what lets a clinician verify *why* an answer applies to *this* patient.
"""
from __future__ import annotations

from pydantic import BaseModel


class LiteratureCitation(BaseModel):
    chunk_id: str
    title: str
    source: str          # e.g. "Lewis et al. 2020"
    url: str
    score: float = 0.0   # retrieval similarity

    def render(self) -> str:
        return f"[{self.source}] {self.title} <{self.url}>"


class PatientCitation(BaseModel):
    resource: str        # e.g. "Observation/123"
    label: str           # e.g. "Hemoglobin A1c"
    value: str           # e.g. "8.2 %"
    effective: str | None = None  # date

    def render(self) -> str:
        when = f" @ {self.effective[:10]}" if self.effective else ""
        return f"[{self.resource}] {self.label} = {self.value}{when}"


class GroundedAnswer(BaseModel):
    """An LLM answer with full dual provenance."""
    text: str
    literature: list[LiteratureCitation] = []
    patient: list[PatientCitation] = []

    def render_markdown(self) -> str:
        out = [self.text, ""]
        if self.patient:
            out.append("**Patient data used:**")
            out += [f"- {c.render()}" for c in self.patient]
            out.append("")
        if self.literature:
            out.append("**Evidence:**")
            out += [f"- {c.render()}" for c in self.literature]
        return "\n".join(out)
