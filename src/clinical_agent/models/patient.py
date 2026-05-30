"""Minimal Pydantic Patient model parsed from a FHIR R4 Patient resource."""
from __future__ import annotations

from pydantic import BaseModel


class Patient(BaseModel):
    id: str
    name: str | None = None
    gender: str | None = None
    birth_date: str | None = None

    @classmethod
    def from_fhir(cls, resource: dict) -> "Patient":
        name = None
        names = resource.get("name") or []
        if names:
            n = names[0]
            given = " ".join(n.get("given", []))
            family = n.get("family", "")
            name = (given + " " + family).strip() or n.get("text")
        return cls(
            id=resource.get("id", "unknown"),
            name=name,
            gender=resource.get("gender"),
            birth_date=resource.get("birthDate"),
        )

    def context_line(self) -> str:
        """Compact one-liner for prompt injection."""
        bits = [f"Patient {self.id}"]
        if self.gender:
            bits.append(self.gender)
        if self.birth_date:
            bits.append(f"DOB {self.birth_date}")
        return ", ".join(bits)
