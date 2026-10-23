"""Ingest the Dang et al. (2025) durian article into the RAG corpus.

    python scripts/ingest_durian_source.py            # dry run (default)
    python scripts/ingest_durian_source.py --commit   # write + embed

The PDF is located by content hash through data/MANIFEST.csv, so folder
reorganisation cannot break it. The dry run resolves, extracts and checks
the database but loads no model and writes nothing.
"""
import argparse
from pathlib import Path

from sqlalchemy import or_, select

from agriworldmodel.corpus.sources import resolve_pdf_by_sha256
from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.session import SessionLocal
from agriworldmodel.evidence.schemas import (
    EvidenceSourceCreate,
    EvidenceSourceType,
)
from agriworldmodel.retrieval.document_ingestion import (
    extract_pdf_chunks,
    ingest_pdf_document,
)
from agriworldmodel.retrieval.embedding import BGEM3DenseEmbedder

REPO_ROOT = Path(__file__).resolve().parents[1]

# Identity of the source: the file's content hash and its DOI.
PDF_SHA256 = (
    "5e8a648d3694d60fa1143a14246a0385cb93c4ce9e91ff315ffd6d5ec058eb0e"
)
DOI = "10.3390/plants14081185"
DOI_URL = f"https://doi.org/{DOI}"

TITLE = (
    "Combining Organic and Foliar Fertilization "
    "to Enhance Soil Fertility and Mitigate "
    "Physiological Disorders of Durian "
    "(Durio zibethinus Murr.) Fruit in the Tropics"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit", action="store_true",
        help="write to the database and load BGE-M3 (default: dry run)")
    args = parser.parse_args()

    # ---------------------------------------------------------------
    # 1. Resolve the local source by hash (fails on a renamed-but-
    #    changed or missing file).
    # ---------------------------------------------------------------
    pdf_path, manifest_row = resolve_pdf_by_sha256(REPO_ROOT, PDF_SHA256)
    print("PDF:", pdf_path)
    print("source_id:", manifest_row.source_id)

    # ---------------------------------------------------------------
    # 2. Extraction-only preflight, before any model is loaded.
    # ---------------------------------------------------------------
    extracted = extract_pdf_chunks(pdf_path)
    pages = sorted({chunk.page_number for chunk in extracted})
    print()
    print("Extraction preflight")
    print("--------------------")
    print("Chunks:", len(extracted))
    print("Pages with text:", len(pages))
    print("Page range:", pages[0], "->", pages[-1])

    # ---------------------------------------------------------------
    # 3. Identity check against the database. A hash match is the same
    #    document; a DOI match with a different hash is a conflict that
    #    needs a human, not a second silent copy.
    # ---------------------------------------------------------------
    with SessionLocal() as session:
        existing = session.scalars(
            select(EvidenceSource).where(or_(
                EvidenceSource.url == DOI_URL,
                EvidenceSource.source_metadata["sha256"].astext
                == PDF_SHA256,
            ))
        ).all()

        if existing:
            recorded = existing[0].source_metadata.get("sha256")
            if recorded != PDF_SHA256:
                raise RuntimeError(
                    f"DOI {DOI} is stored with a different file hash "
                    f"({recorded}); resolve manually before ingesting.")
            print()
            print("Source already exists; not ingesting a duplicate.")
            print("Existing source_id:", existing[0].id)
            return

        if not args.commit:
            print()
            print("Dry run: nothing written, no model loaded.")
            print("Re-run with --commit to ingest and embed.")
            return

        # -----------------------------------------------------------
        # 4. Load the real production embedder and register everything.
        # -----------------------------------------------------------
        print()
        print("Loading BAAI/bge-m3...")
        embedder = BGEM3DenseEmbedder(use_fp16=True, devices=["cuda:0"])
        print("Embedding model:", embedder.model_name)

        source = EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title=TITLE,
            publisher="Plants (MDPI)",
            published_year=2025,
            url=DOI_URL,
            language="en",
            source_metadata={
                "doi": DOI,
                "journal": "Plants",
                "volume": "14",
                "issue": "8",
                "article_number": "1185",
                "study_region": "Vietnamese Mekong Delta",
                "source_role": "real_research_evidence",
                # Link back to data/SOURCES.csv.
                "source_id": manifest_row.source_id,
            },
        )

        try:
            result = ingest_pdf_document(
                session,
                pdf_path=pdf_path,
                source=source,
                embedder=embedder,
                crop="durian",
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

    print()
    print("================================")
    print("INGESTION SUCCESS")
    print("================================")
    print("source_id:", result.source_id)
    print("chunks:", result.chunk_count)
    print("pages with text:", result.page_count_with_text)


if __name__ == "__main__":
    main()
