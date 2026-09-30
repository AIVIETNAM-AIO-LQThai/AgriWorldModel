from pathlib import Path

import pytest
from sqlalchemy import select

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.models.knowledge_chunk import KnowledgeChunk
from agriworldmodel.evidence.schemas import EvidenceSourceCreate, EvidenceSourceType
from agriworldmodel.retrieval import document_ingestion
from agriworldmodel.retrieval.document_ingestion import (
    DocumentIngestionError,
    chunk_text, extract_pdf_chunks, ingest_pdf_document
)
from agriworldmodel.retrieval.embedding import EMBEDDING_DIMENSION


class FakePage:
    def __init__(self, text: str | None):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    def __init__(self, pages):
        self.pages = pages


class FakeEmbedder:
    model_name = "fixture-embedder"
    dimension = EMBEDDING_DIMENSION

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            [1.0]
            + [0.0]
            * (
                EMBEDDING_DIMENSION
                - 1
            )
            for _ in texts
        ]

    def embed_query(self, text: str
    ) -> list[float]:
        return (
            [1.0]
            + [0.0]
            * (
                EMBEDDING_DIMENSION
                - 1
            )
        )


class FailingEmbedder(FakeEmbedder):
    def __init__(self):
        self.calls = 0

    def embed_documents(self, texts: list[str],) -> list[list[float]]:
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("Synthetic embedding failure.")
        return super().embed_documents(texts)


def make_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.pdf"

    # The fake PdfReader handles content;
    # bytes exist only for hashing/path checks.
    path.write_bytes(b"%PDF fixture")

    return path


def patch_reader(monkeypatch, pages):
    monkeypatch.setattr(
        document_ingestion,
        "PdfReader",
        lambda _: FakeReader(pages),
    )

# -------------------------------------------------------------------
# 1. Chunking must be deterministic and size bounded.
# -------------------------------------------------------------------
def test_chunk_text_is_deterministic():
    text = " ".join(
        f"word{i}"
        for i in range(500)
    )

    first = chunk_text(
        text,
        max_chars=300,
        overlap_chars=40,
    )

    second = chunk_text(
        text,
        max_chars=300,
        overlap_chars=40,
    )

    assert first == second
    assert len(first) > 1

    assert all(len(chunk) <= 300 for chunk in first)

# -------------------------------------------------------------------
# 2. PDF extraction must preserve page provenance.
# -------------------------------------------------------------------
def test_pdf_extraction_preserves_page_locator(
    tmp_path, monkeypatch
):
    path = make_pdf(tmp_path)

    patch_reader(
        monkeypatch,
        [
            FakePage("Nitrogen information."),
            FakePage("Potassium information."),
        ],
    )

    chunks = extract_pdf_chunks(path)

    assert len(chunks) == 2
    assert chunks[0].locator == "p. 1"
    assert chunks[1].locator == "p. 2"
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2

    # -------------------------------------------------------------------
# 3. Ingestion must register provenance, chunks, and embeddings.
# -------------------------------------------------------------------
def test_pdf_ingestion_registers_embedded_chunks(
    db_session, tmp_path, monkeypatch,
):
    path = make_pdf(tmp_path)

    patch_reader(
        monkeypatch,
        [
            FakePage("Durian nitrogen guidance."),
            FakePage("Durian potassium guidance."),
        ],
    )

    result = ingest_pdf_document(
        db_session,

        pdf_path=path,

        source=EvidenceSourceCreate(
            source_type=EvidenceSourceType.EXTENSION_GUIDE,
            title="Fixture Durian Guide",
            publisher="Fixture Publisher",
            published_year=2026,
            language="en",
        ),

        embedder=FakeEmbedder(),

        crop="durian",
    )

    assert result.chunk_count == 2
    assert result.page_count_with_text == 2

    source = db_session.get(EvidenceSource, result.source_id)

    assert source is not None
    assert source.source_metadata["filename"] == "fixture.pdf"
    assert len(source.source_metadata["sha256"]) == 64

    chunks = list(
        db_session.scalars(
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.source_id == result.source_id
            )
            .order_by(
                KnowledgeChunk.chunk_index
            )
        )
    )

    assert len(chunks) == 2
    assert chunks[0].locator == "p. 1"
    assert chunks[1].locator == "p. 2"
    assert chunks[0].embedding_model == "fixture-embedder"
    assert chunks[0].embedding is not None

# -------------------------------------------------------------------
# 4. A scanned/non-text PDF must fail explicitly.
# -------------------------------------------------------------------
def test_pdf_without_extractable_text_is_rejected(
    tmp_path, monkeypatch
):
    path = make_pdf(tmp_path)

    patch_reader(
        monkeypatch,
        [
            FakePage(None),
            FakePage(""),
        ],
    )

    with pytest.raises(
        DocumentIngestionError,
        match="no extractable text",
    ):
        extract_pdf_chunks(path)

# -------------------------------------------------------------------
# 5. Failed embedding must not leave partial document records.
# -------------------------------------------------------------------
def test_failed_embedding_rolls_back_document(
    db_session, tmp_path, monkeypatch
):
    path = make_pdf(tmp_path)

    patch_reader(
        monkeypatch,
        [
            FakePage("Page one content."),
            FakePage("Page two content."),
        ],
    )

    with pytest.raises(
        RuntimeError, match="Synthetic embedding failure"
    ):
        ingest_pdf_document(
            db_session,
            pdf_path=path,

            source=EvidenceSourceCreate(
                source_type=EvidenceSourceType.LITERATURE,
                title="Rollback Fixture",
            ),

            embedder=FailingEmbedder(),
            crop="durian",
        )

    remaining_source = (
        db_session.scalar(
            select(EvidenceSource).where(EvidenceSource.title == "Rollback Fixture")
        )
    )

    assert remaining_source is None