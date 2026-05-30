"""Pydantic Observation model parsed from a FHIR R4 Observation resource."""
from __future__ import annotations

from pydantic import BaseModel


class Observation(BaseModel):
    id: str
    code: str | None = None          # LOINC code
    display: str | None = None       # human label, e.g. "Hemoglobin A1c"
    value: float | None = None
    unit: str | None = None
    effective: str | None = None     # effectiveDateTime
    status: str | None = None
    category: str | None = None      # vital-signs | laboratory | ...

    @classmethod
    def from_fhir(cls, resource: dict) -> "Observation":
        coding = ((resource.get("code") or {}).get("coding") or [{}])[0]
        vq = resource.get("valueQuantity") or {}
        cat = ((resource.get("category") or [{}])[0].get("coding") or [{}])[0]
        return cls(
            id=resource.get("id", "unknown"),
            code=coding.get("code"),
            display=coding.get("display") or (resource.get("code") or {}).get("text"),
            value=vq.get("value"),
            unit=vq.get("unit"),
            effective=resource.get("effectiveDateTime"),
            status=resource.get("status"),
            category=cat.get("code"),
        )

    def context_line(self) -> str:
        """Compact one-liner for patient-conditioned retrieval & prompts."""
        label = self.display or self.code or "observation"
        val = f"{self.value} {self.unit}".strip() if self.value is not None else "?"
        when = f" ({self.effective[:10]})" if self.effective else ""
        return f"{label}: {val}{when}"
