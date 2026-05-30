from clinical_agent.rag.retriever import Retriever


def test_retrieval_returns_provenance():
    r = Retriever()
    hits = r.retrieve("elevated HbA1c diabetes glycemic control")
    assert hits, "expected at least one hit"
    top = hits[0]
    assert top.url.startswith("http")
    assert top.source
    assert top.chunk_id
    # the diabetes/HbA1c chunk should rank for a diabetes query
    assert any(h.chunk_id == "ada-hba1c-001" for h in hits)


def test_min_score_filter():
    r = Retriever()
    hits = r.retrieve("xyzzy nonsense unrelated", min_score=0.99)
    assert hits == []


def test_topic_filter_restricts_to_metadata():
    # only the KDIGO chunk carries the 'kidney' topic
    r = Retriever()
    hits = r.retrieve("kidney disease eGFR", topics=["kidney"], min_score=0.0)
    assert hits
    assert all(h.chunk_id == "kdigo-egfr-001" for h in hits)
