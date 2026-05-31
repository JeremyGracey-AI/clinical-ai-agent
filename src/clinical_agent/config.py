"""Central configuration. Reads from environment / .env; safe defaults run OFFLINE."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # FHIR / SMART
    fhir_base_url: str = "https://hapi.fhir.org/baseR4"
    smart_client_id: str = ""
    smart_redirect_uri: str = "http://localhost:7860/callback"
    smart_scopes: str = (
        "launch patient/Patient.r patient/Observation.rs "
        "patient/Observation.c openid fhirUser"
    )

    # LLM
    llm_provider: str = "stub"  # stub | openai | anthropic
    llm_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-haiku-4-5-20251001"
    llm_temperature: float = 0.0  # clinical determinism
    llm_max_tokens: int = 1024
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # RAG
    embed_provider: str = "stub"  # stub | sentence-transformers
    embed_model: str = "all-MiniLM-L6-v2"
    use_chroma: bool = False  # persist/retrieve via ChromaDB when True (needs [full])
    chroma_dir: str = "./data/chroma"
    # Retrieval scoring backend (advances Chroma's `use_chroma` flag with an
    # explicit selector). Order of precedence in Retriever: quantum_kernel ->
    # chroma (if use_chroma) -> in-memory cosine. "quantum_kernel" is an
    # EXPERIMENTAL, correctness-equivalent demonstrator — slower than cosine,
    # never a speedup. See docs/QUANTUM.md.
    retrieval_backend: str = "auto"  # auto | cosine | quantum_kernel
    quantum_qubits: int = 4  # feature-map width for the quantum_kernel backend
    quantum_shots: int = 0  # 0 = statevector (exact); >0 = sampled fidelity
    corpus_dir: str = "./data/corpus"
    retrieval_top_k: int = 4
    retrieval_min_score: float = Field(default=0.15)
    retrieval_refine: bool = True  # re-query once if best hit is below the floor

    # Evaluation
    judge_faithfulness: bool = False  # use the LLM as a faithfulness judge when True
    analytics_path: str = "./data/analytics.jsonl"  # Work IQ run history (Analytics tab)

    # Learner profile (mastery persisted across sessions; drives difficulty scaling)
    profile_path: str = "./data/learner_profile.json"

    @property
    def offline(self) -> bool:
        """True when no real LLM/embedding backend is configured."""
        return self.llm_provider == "stub" or self.embed_provider == "stub"

    @property
    def llm_ready(self) -> bool:
        """True when a real LLM backend is fully configured (provider + key)."""
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
