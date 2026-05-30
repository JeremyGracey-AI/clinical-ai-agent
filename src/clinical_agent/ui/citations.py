"""Foundation-paper citations — single source of truth for header + About panel."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    authors: str
    year: int
    title: str
    venue: str
    url: str


FOUNDATION_PAPERS: list[Citation] = [
    Citation("Lewis, P. et al.", 2020,
             "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
             "NeurIPS", "https://arxiv.org/abs/2005.11401"),
    Citation("Singhal, K. et al.", 2023,
             "Large language models encode clinical knowledge",
             "Nature", "https://www.nature.com/articles/s41586-023-06291-2"),
]


def render_header_md() -> str:
    lines = [
        "### 🩺 Clinical AI Agent",
        "_Patient-grounded · citation-traceable · SMART on FHIR · transparent RAG_",
        "",
        "**Built on foundational research:**",
    ]
    for c in FOUNDATION_PAPERS:
        lines.append(f"- {c.authors} ({c.year}). [{c.title}]({c.url}). *{c.venue}*.")
    return "\n".join(lines)
