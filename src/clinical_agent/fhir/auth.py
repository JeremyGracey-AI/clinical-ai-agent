"""SMART on FHIR OAuth2 helpers (SMART App Launch v2).

Public HAPI sandbox needs no auth, so this is wired but optional. The scope
string uses the v2 `.cruds` suffixes:
  patient/Patient.r       -> read demographics
  patient/Observation.rs  -> read + search observations
  patient/Observation.c   -> create observations (assessment write-back)

Ref: https://build.fhir.org/ig/HL7/smart-app-launch/scopes-and-launch-context.html
"""
from __future__ import annotations

from urllib.parse import urlencode

from clinical_agent.config import Settings, get_settings


def build_authorize_url(authorize_endpoint: str, state: str,
                        settings: Settings | None = None) -> str:
    """Construct the SMART /authorize redirect URL."""
    s = settings or get_settings()
    params = {
        "response_type": "code",
        "client_id": s.smart_client_id,
        "redirect_uri": s.smart_redirect_uri,
        "scope": s.smart_scopes,
        "state": state,
        "aud": s.fhir_base_url,  # required by SMART: the FHIR base URL
    }
    return f"{authorize_endpoint}?{urlencode(params)}"


def token_exchange_payload(code: str, settings: Settings | None = None) -> dict:
    """Body for the POST /token authorization_code exchange."""
    s = settings or get_settings()
    return {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": s.smart_redirect_uri,
        "client_id": s.smart_client_id,
    }
