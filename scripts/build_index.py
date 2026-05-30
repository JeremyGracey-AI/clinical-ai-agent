"""Ingest data/corpus/ and report the resulting retriever index size."""
from clinical_agent.rag.ingest import ingest_corpus_dir
from clinical_agent.rag.retriever import Retriever


def main():
    extra = ingest_corpus_dir()
    r = Retriever(extra_chunks=extra)
    print(f"Indexed {len(r.chunks)} chunks "
          f"({len(extra)} from corpus dir + {len(r.chunks) - len(extra)} seed).")
    hits = r.retrieve("elevated HbA1c diabetes management")
    print("Sample query -> top hits:")
    for h in hits:
        print(f"  [{h.score}] {h.source}: {h.title[:70]}...")


if __name__ == "__main__":
    main()
