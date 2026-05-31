# Quantum Computing & This Project — An Honest Design Note

> **TL;DR.** Most of this repo (FHIR I/O, the 5-agent orchestration, dual-citation
> provenance, the Work IQ eval harness, the LLM call) has **no quantum surface
> area** — and that's the correct design. The one place with a genuine quantum
> analog is the **vector retriever's similarity score**, which we expose as an
> optional, clearly-labelled `quantum_kernel` backend. It is a
> **correctness-equivalent demonstrator, never a speedup.** This document explains
> exactly what does and does not translate, and why.

---

## 1. Where quantum has no role (≈90% of the build)

| Component | Why quantum doesn't help |
|---|---|
| 5-agent pipeline (`orchestrator.py`, `agents/`) | Sequential business logic + branching. Not a numerical bottleneck. |
| FHIR client / SMART OAuth2 (`fhir/`) | Network REST I/O. Classical. |
| Dual-citation models, Gradio/FastAPI UIs | Pure software engineering. |
| The LLM (`stub`/`openai`/`anthropic`) | Frontier LLMs do not run on quantum hardware, and won't in any relevant horizon. |
| Work IQ eval harness (`eval/`) | Token-overlap + set metrics. Trivially classical. |

A clinical decision-support system's value is in **transparency, grounding, and
provenance** — not in raw linear-algebra throughput. There is no operation here
that is slow enough, or large enough, for a quantum computer to matter.

## 2. The one plausible mapping: similarity search

The retriever (`rag/retriever.py`, `rag/embeddings.py`) is the only component doing
real vector math: it embeds the corpus and ranks documents by **cosine similarity**
`<q, d>`. This has a direct quantum-machine-learning analog — the **fidelity
kernel**:

```
k(q, d) = |<phi(q) | phi(d)>|^2     in [0, 1]
```

where `|phi(x)>` is the quantum state produced by a parametrised **feature map**.
Where cosine measures overlap of classical vectors, the fidelity kernel measures
overlap of the quantum states those vectors are encoded into. This is exactly what
[Qiskit ML's `FidelityQuantumKernel`](https://qiskit-community.github.io/qiskit-machine-learning/)
computes.

### What we shipped: `RETRIEVAL_BACKEND=quantum_kernel`

A third retriever backend (`rag/quantum_kernel.py`) sitting alongside the in-memory
cosine index and the ChromaDB backend, behind a config flag — mirroring how
`USE_CHROMA` already gates Chroma:

```bash
pip install -e ".[quantum]"           # qiskit + qiskit-aer + qiskit-machine-learning
RETRIEVAL_BACKEND=quantum_kernel \
QUANTUM_QUBITS=4 \
python -m clinical_agent.cli
```

Pipeline:

1. **Embed** with the existing stub/sentence-transformers embedder (unchanged).
2. **Reduce** the high-dim embedding (`_DIM=256`) to `QUANTUM_QUBITS` features via a
   deterministic, structure-preserving block-sum projection (`reduce_dim`). This is
   required because you cannot amplitude-encode 256 amplitudes onto 4 qubits, and a
   *deterministic* reduction keeps the offline stack reproducible.
3. **Encode** the reduced features as rotation angles into a `ZZFeatureMap`.
4. **Score** each (query, doc) pair with `FidelityQuantumKernel` on a **statevector
   simulator** (exact by default; `QUANTUM_SHOTS>0` reserved for sampled fidelity).
5. Return the same `LiteratureCitation` provenance objects — so every downstream
   agent is unchanged.

The backend exposes the identical `score(query) -> [(similarity, chunk)]` contract,
and falls back to in-memory cosine if Qiskit isn't installed (same graceful pattern
as Chroma). All **42 tests pass** with or without the extra.

## 3. Honest limitations — read this before claiming a benefit

- **No speedup. Slower, in fact.** For a ~6-chunk corpus and 256-dim hashing
  embeddings, classical cosine is exact and instant. Simulating a quantum kernel is
  strictly more expensive. On real hardware it would be slower *and* noisier.
- **The ranking is not identical to cosine.** The lossy reduction to 4 qubits
  changes the ordering of near-tied results (in our demo query, the LDL chunk edges
  out the diabetes chunk at rank 1). This is a fidelity-of-approximation artifact,
  not a feature. Increase `QUANTUM_QUBITS` to reduce it.
- **It is a competency demonstrator,** not a clinical or performance improvement —
  consistent with the README's "honest limitations" framing for the stub LLM and
  the Work IQ scaffold.

## 4. What does *not* translate, and the standard misconceptions

- **"Quantum RAG via HHL."** The Harrow–Hassidim–Lloyd linear-systems algorithm is
  the usual source of "exponential speedup" claims. In practice it requires QRAM
  (efficient quantum data loading) that doesn't exist at scale, well-conditioned
  sparse matrices, and returns the answer *as a quantum state* — reading it out
  often erases the speedup. For a system whose entire purpose is reading out and
  **displaying** cited provenance, this is an especially poor fit. See
  [Aaronson, "Read the fine print", *Nature Physics* 2015](https://www.nature.com/articles/nphys3272).
- **Grover search over the corpus.** Only a quadratic speedup, and it requires the
  corpus in superposition — far more overhead than a small clinical index is worth.
- **Quantum LLMs.** Not a thing in any deployable sense; out of scope.

## 5. Where a quantum angle *could* legitimately grow (research directions)

- **Larger quantum kernels on a real QML benchmark.** Swap the demo corpus for a
  labelled retrieval/classification set and compare quantum-kernel vs. RBF-kernel
  SVM — the setting where quantum kernels are actually studied
  ([Havlíček et al., *Nature* 2019](https://www.nature.com/articles/s41586-019-0980-2)).
- **Variational quantum classifiers** for the conditions/gap flags in `study_plan`,
  as a QML study (not a production claim).
- **Hardware execution** via `qiskit-ibm-runtime`, to characterise noise vs. the
  statevector baseline this backend already provides.

## References

- Qiskit Machine Learning — Quantum Kernels: <https://qiskit-community.github.io/qiskit-machine-learning/>
- Havlíček et al. 2019, *Supervised learning with quantum-enhanced feature spaces*, Nature — <https://www.nature.com/articles/s41586-019-0980-2>
- Schuld & Killoran 2019, *Quantum ML in feature Hilbert spaces*, PRL — <https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.122.040504>
- Aaronson 2015, *Read the fine print*, Nature Physics (caveats on HHL/QML speedups) — <https://www.nature.com/articles/nphys3272>
- Harrow, Hassidim, Lloyd 2009, *Quantum algorithm for linear systems of equations* — <https://arxiv.org/abs/0811.3171>
