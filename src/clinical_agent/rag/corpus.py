"""Built-in seed corpus of citable clinical-guideline snippets + foundation papers.

Each entry carries full provenance so retrieval yields real LiteratureCitations
offline. In production, rag/ingest.py adds chunked PDFs/markdown from data/corpus/.
Threshold values reflect widely cited clinical guidelines and are included for
demonstration; verify against current primary guidelines before any clinical use.
"""
from __future__ import annotations

SEED_CORPUS: list[dict] = [
    {
        "chunk_id": "ada-hba1c-001",
        "title": "Glycemic targets: HbA1c >= 6.5% is diagnostic for diabetes; "
                 "general adult target < 7.0%. Values >= 8.0% indicate inadequate control "
                 "warranting therapy intensification.",
        "source": "ADA Standards of Care",
        "url": "https://diabetesjournals.org/care/issue/standards-of-care",
        "topics": ["diabetes", "hba1c", "glycemic", "endocrine"],
    },
    {
        "chunk_id": "kdigo-egfr-001",
        "title": "eGFR < 60 mL/min/1.73m2 for >= 3 months defines chronic kidney disease; "
                 "eGFR 45-59 is CKD stage G3a. Declining eGFR warrants nephrology evaluation "
                 "and medication dose review.",
        "source": "KDIGO CKD Guideline",
        "url": "https://kdigo.org/guidelines/ckd-evaluation-and-management/",
        "topics": ["kidney", "egfr", "ckd", "renal", "nephrology"],
    },
    {
        "chunk_id": "acc-bp-001",
        "title": "Stage 2 hypertension is systolic BP >= 140 or diastolic >= 90 mmHg; "
                 "antihypertensive pharmacotherapy is recommended alongside lifestyle change.",
        "source": "ACC/AHA Hypertension Guideline",
        "url": "https://www.ahajournals.org/doi/10.1161/HYP.0000000000000065",
        "topics": ["hypertension", "blood pressure", "bp", "cardiovascular"],
    },
    {
        "chunk_id": "ldl-lipid-001",
        "title": "LDL cholesterol >= 190 mg/dL warrants high-intensity statin therapy; "
                 "LDL is a primary target for atherosclerotic cardiovascular disease risk reduction.",
        "source": "ACC/AHA Cholesterol Guideline",
        "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000000625",
        "topics": ["cholesterol", "ldl", "lipid", "statin", "cardiovascular"],
    },
    {
        "chunk_id": "lewis-rag-2020",
        "title": "Retrieval-Augmented Generation combines a parametric seq2seq model with a "
                 "non-parametric dense vector index, producing more factual, grounded, and "
                 "verifiable generation on knowledge-intensive tasks.",
        "source": "Lewis et al. 2020",
        "url": "https://arxiv.org/abs/2005.11401",
        "topics": ["rag", "retrieval", "grounding", "nlp", "method"],
    },
    {
        "chunk_id": "singhal-medpalm-2023",
        "title": "Large language models encode clinical knowledge; instruction prompt tuning "
                 "(Med-PaLM) improves factuality and safety, but human evaluation reveals gaps "
                 "requiring grounding and clinician oversight.",
        "source": "Singhal et al. 2023",
        "url": "https://www.nature.com/articles/s41586-023-06291-2",
        "topics": ["clinical", "llm", "medpalm", "evaluation", "safety", "method"],
    },
]
