"""Tests for the EXPERIMENTAL quantum-kernel retrieval backend.

The dimensionality-reduction unit tests always run (pure Python). The end-to-end
backend tests require the optional ``[quantum]`` extra (Qiskit); they skip cleanly
when it is absent, mirroring how the suite treats other optional integrations.
"""
import importlib.util
import math

import pytest

from clinical_agent.rag.quantum_kernel import reduce_dim

_HAS_QISKIT = importlib.util.find_spec("qiskit_machine_learning") is not None
requires_qiskit = pytest.mark.skipif(
    not _HAS_QISKIT, reason="install the [quantum] extra (qiskit) to run this test"
)


# ---- reduce_dim: pure-Python, always runs --------------------------------

def test_reduce_dim_is_deterministic_and_normalised():
    vec = [float(i % 7) for i in range(256)]
    a = reduce_dim(vec, 4)
    b = reduce_dim(vec, 4)
    assert a == b  # deterministic
    assert len(a) == 4
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-9)  # L2-normalised


def test_reduce_dim_pads_when_target_exceeds_source():
    out = reduce_dim([1.0, 0.0], 4)
    assert len(out) == 4
    assert math.isclose(sum(x * x for x in out), 1.0, rel_tol=1e-9)


def test_reduce_dim_handles_zero_vector():
    out = reduce_dim([0.0] * 16, 4)
    assert out == [0.0, 0.0, 0.0, 0.0]  # no division-by-zero blow-up


# ---- end-to-end backend: requires the [quantum] extra --------------------

@requires_qiskit
def test_quantum_backend_returns_provenance(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_BACKEND", "quantum_kernel")
    monkeypatch.setenv("QUANTUM_QUBITS", "4")
    from clinical_agent.config import get_settings
    get_settings.cache_clear()
    from clinical_agent.rag.retriever import Retriever

    r = Retriever()
    # confirm we are actually on the quantum path, not a silent cosine fallback
    assert r._backend is not None and r._backend.__class__.__name__ == "QuantumKernelBackend"

    hits = r.retrieve("elevated HbA1c diabetes glycemic control", min_score=0.0)
    assert hits, "expected at least one hit"
    top = hits[0]
    assert top.url.startswith("http")
    assert top.source and top.chunk_id
    # diabetes/HbA1c chunk should surface among the top hits for a diabetes query
    assert any(h.chunk_id == "ada-hba1c-001" for h in hits)
    get_settings.cache_clear()


@requires_qiskit
def test_quantum_scores_are_valid_fidelities(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_BACKEND", "quantum_kernel")
    from clinical_agent.config import get_settings
    get_settings.cache_clear()
    from clinical_agent.rag.retriever import Retriever

    r = Retriever()
    scored = r._backend.score("kidney disease eGFR")
    assert scored
    for s, _chunk in scored:
        assert 0.0 <= s <= 1.0 + 1e-9  # fidelities live in [0, 1]
    get_settings.cache_clear()


def test_missing_qiskit_falls_back_to_cosine(monkeypatch):
    """With the backend requested but the import failing, Retriever must fall
    back to the in-memory cosine index rather than crash."""
    monkeypatch.setenv("RETRIEVAL_BACKEND", "quantum_kernel")
    from clinical_agent.config import get_settings
    get_settings.cache_clear()

    import clinical_agent.rag.retriever as retr_mod

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _boom(name, *args, **kwargs):
        if name.startswith("clinical_agent.rag.quantum_kernel"):
            raise ImportError("simulated missing [quantum] extra")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _boom)
    r = retr_mod.Retriever()
    assert r._backend is None  # fell back to in-memory cosine
    hits = r.retrieve("elevated HbA1c diabetes glycemic control")
    assert any(h.chunk_id == "ada-hba1c-001" for h in hits)
    get_settings.cache_clear()
