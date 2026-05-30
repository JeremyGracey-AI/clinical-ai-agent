"""FHIR R4 client. Live HTTP against any FHIR server, or offline fixtures.

Set use_fixtures=True (default when no network / for tests) to serve canned
Patient/Observation bundles from clinical_agent.eval.synthetic — so the whole
app runs with zero external dependencies.
"""
from __future__ import annotations

from typing import Any

import httpx

from clinical_agent.config import Settings, get_settings


class FHIRClient:
    def __init__(self, settings: Settings | None = None, *, token: str | None = None,
                 use_fixtures: bool = False):
        self.settings = settings or get_settings()
        self.token = token
        self.use_fixtures = use_fixtures
        self._base = self.settings.fhir_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/fhir+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # ---- low-level ----
    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        if self.use_fixtures:
            from clinical_agent.eval.synthetic import fixture_get
            return fixture_get(path, params or {})
        resp = httpx.get(f"{self._base}/{path.lstrip('/')}", params=params,
                         headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: dict) -> dict:
        if self.use_fixtures:
            return {**body, "id": "fixture-created", "resourceType": body.get("resourceType")}
        resp = httpx.post(f"{self._base}/{path.lstrip('/')}", json=body,
                          headers={**self._headers(),
                                   "Content-Type": "application/fhir+json"}, timeout=30)
        resp.raise_for_status()
        return resp.json()
