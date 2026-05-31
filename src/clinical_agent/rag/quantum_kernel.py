"""EXPERIMENTAL quantum-kernel similarity backend for the retriever.

This is a *demonstrator*, not a speedup. It replaces the classical cosine score
``<q, d>`` with a **quantum fidelity kernel**: each embedding is encoded into a
parametrised quantum feature state ``|phi(x)>`` and similarity is the overlap

    k(q, d) = |<phi(q) | phi(d)>|^2    in [0, 1]

estimated on a simulator (Qiskit Aer / statevector). For this repo's tiny corpus
and 256-dim hashing embeddings, classical cosine is exact and instant; the quantum
kernel is slower, approximate (with shots), and offers no advantage. It exists to
demonstrate quantum-machine-learning competency (feature maps, fidelity kernels,
simulator vs. shots) inside a real RAG pipeline. See docs/QUANTUM.md.

Design notes
------------
* High-dim embeddings (``_DIM=256``) cannot be amplitude-encoded onto a handful
  of qubits, so we first project to ``n_qubits`` features with a deterministic,
  structure-preserving block-sum reduction (no training, no randomness — keeps the
  pipeline reproducible like the rest of the offline stack).
* Reduced features are scaled into angles and fed to a ``ZZFeatureMap``; the kernel
  is Qiskit ML's ``FidelityQuantumKernel``.
* If ``qiskit-machine-learning`` is not installed, construction raises and the
  Retriever falls back to in-memory cosine (same pattern as the Chroma backend).
"""
from __future__ import annotations

import math


def reduce_dim(vec: list[float], n: int) -> list[float]:
    """Deterministically project ``vec`` to length ``n`` by summing contiguous
    blocks, then L2-normalise. Structure-preserving and reproducible — tokens that
    co-locate in the hashing embedder stay correlated after reduction."""
    d = len(vec)
    if n >= d:
        out = list(vec) + [0.0] * (n - d)
    else:
        out = [0.0] * n
        # spread d dims across n buckets as evenly as possible
        for i, v in enumerate(vec):
            out[i % n] += v
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


class QuantumKernelBackend:
    """Fidelity-kernel retrieval scorer over the seed corpus.

    Same ``score(query) -> list[(similarity, chunk)]`` contract as the in-memory
    and Chroma backends, so it slots into ``Retriever`` unchanged.
    """

    def __init__(self, chunks: list[dict], embedder, settings):
        # Lazy imports — only when this backend is actually selected.
        import numpy as np
        from qiskit_machine_learning.kernels import FidelityQuantumKernel

        self._np = np
        self.n = max(1, int(settings.quantum_qubits))
        self.chunks = chunks
        self.embedder = embedder

        # Qiskit >=2.1 ships the functional `zz_feature_map`; the `ZZFeatureMap`
        # class is deprecated and removed in 3.0. Prefer the function, fall back
        # to the class on older Qiskit.
        try:
            from qiskit.circuit.library import zz_feature_map
            feature_map = zz_feature_map(feature_dimension=self.n, reps=1)
        except ImportError:  # pragma: no cover - older Qiskit
            from qiskit.circuit.library import ZZFeatureMap
            feature_map = ZZFeatureMap(feature_dimension=self.n, reps=1)
        # Default fidelity uses a statevector simulator (exact). Shots can be
        # wired via a sampler-backed ComputeUncompute fidelity if desired; we keep
        # the exact path as the offline default for determinism.
        self.kernel = FidelityQuantumKernel(feature_map=feature_map)

        # Encode corpus once. Angles in [0, pi] keep the map well-conditioned.
        self._doc_vecs = self._np.array(
            [self._encode(c["title"]) for c in chunks], dtype=float
        )

    def _encode(self, text: str) -> list[float]:
        emb = self.embedder.embed(text)
        reduced = reduce_dim(emb, self.n)
        # map normalised features (roughly [-1, 1]) into angle range [0, pi]
        return [math.pi * (0.5 * (x + 1.0)) for x in reduced]

    def score(self, query: str) -> list[tuple[float, dict]]:
        qv = self._np.array([self._encode(query)], dtype=float)
        # kernel matrix shape (1, n_docs); entries are fidelities in [0, 1]
        kmat = self.kernel.evaluate(x_vec=qv, y_vec=self._doc_vecs)[0]
        scored = [(float(kmat[i]), self.chunks[i]) for i in range(len(self.chunks))]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
