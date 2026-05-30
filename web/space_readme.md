---
title: Clinical AI Agent UI
emoji: 🩺
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
fullWidth: true
header: mini
license: apache-2.0
---

# Clinical AI Agent — dashboard

A bespoke **FastAPI + custom-JS** dashboard over the
[clinical-ai-agent](https://github.com/JeremyGracey-AI/clinical-ai-agent) pipeline
— patient-grounded, citation-traceable clinical decision support on open standards
(SMART on FHIR + transparent RAG).

Pick a patient, ask a clinical question, and watch the answer stream in with
**dual-citation provenance** (patient data ⟷ literature), a **Conditions Advisor**,
a live **Clinical Work IQ** radar, and an analytics history.

Runs fully offline (deterministic stub LLM, synthetic FHIR fixtures). For a real
LLM, add `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) as a Space secret and set
`LLM_PROVIDER`. The companion Gradio Space is at
`jeremygracey-ai/clinical-ai-agent`.
