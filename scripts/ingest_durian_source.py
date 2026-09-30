from pathlib import Path

from sqlalchemy import select

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.session import SessionLocal
from agriworldmodel.evidence.schemas import EvidenceSourceCreate, EvidenceSourceType
from agriworldmodel.retrieval.document_ingestion import extract_pdf_chunks, ingest_pdf_document
from agriworldmodel.retrieval.embedding import BGEM3DenseEmbedder

PDF_PATH = Path(
    "data/evidence/durian/"
    "dang_2025_durian_fertilization.pdf"
)

DOI_URL = (
    "https://doi.org/"
    "10.3390/plants14081185"
)

TITLE = (
    "Combining Organic and Foliar Fertilization "
    "to Enhance Soil Fertility and Mitigate "
    "Physiological Disorders of Durian "
    "(Durio zibethinus Murr.) Fruit in the Tropics"
)


def main() -> None:
    # ---------------------------------------------------------------
    # 1. Verify local source
    # ---------------------------------------------------------------
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    print("PDF:")
    print(PDF_PATH.resolve())

    # ---------------------------------------------------------------
    # 2. Extraction-only preflight
    #
    # Do this BEFORE loading BGE-M3 so a malformed/scanned PDF
    # fails cheaply.
    # ---------------------------------------------------------------
    extracted = extract_pdf_chunks(PDF_PATH)

    pages = sorted(
        {
            chunk.page_number for chunk in extracted
        }
    )

    print()
    print("Extraction preflight")
    print("--------------------")
    print("Chunks:", len(extracted))
    print("Pages with text:", len(pages))
    print("Page range:", pages[0], "->", pages[-1])

    print()
    print("First extracted chunk:")
    print("Locator:", extracted[0].locator)
    print(extracted[0].content[:500])

    # ---------------------------------------------------------------
    # 3. Load the real production embedder
    # ---------------------------------------------------------------
    print()
    print("Loading BAAI/bge-m3...")

    embedder = BGEM3DenseEmbedder(
        use_fp16=True,
        devices=["cuda:0"],
    )

    print("Embedding model:", embedder.model_name)

    # ---------------------------------------------------------------
    # 4. Register document + chunks + embeddings
    # ---------------------------------------------------------------
    with SessionLocal() as session:
        # Simple idempotency guard for this known source.
        existing = session.scalar(
            select(EvidenceSource).where(EvidenceSource.url == DOI_URL)
        )

        if existing is not None:
            print()
            print("Source already exists; not ingesting a duplicate.")
            print("Existing source_id:", existing.id)
            return

        source = EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,

            title=TITLE,
            publisher="Plants (MDPI)",
            published_year=2025,

            url=DOI_URL,
            language="en",

            source_metadata={
                "doi": (
                    "10.3390/"
                    "plants14081185"
                ),

                "journal": "Plants",
                "volume": "14",
                "issue": "8",
                "article_number": "1185",

                "study_region": "Vietnamese Mekong Delta",
                "source_role": "real_research_evidence",
            },
        )

        try:
            result = ingest_pdf_document(
                session,
                pdf_path=PDF_PATH,
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