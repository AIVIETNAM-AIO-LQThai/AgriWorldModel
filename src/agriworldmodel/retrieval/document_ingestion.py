import hashlib
import re
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from agriworldmodel.evidence.schemas import EvidenceSourceCreate
from agriworldmodel.evidence.service import register_evidence_source
from agriworldmodel.retrieval.dense import embed_chunk
from agriworldmodel.retrieval.embedding import DenseEmbedder
from agriworldmodel.retrieval.ingestion import register_knowledge_chunk
from agriworldmodel.retrieval.schemas import (
    DocumentIngestionResult, ExtractedDocumentChunk, KnowledgeChunkCreate
)

CHUNKING_VERSION = "pdf-char"
DEFAULT_MAX_CHARS = 1800
DEFAULT_OVERLAP_CHARS = 200

class DocumentIngestionError(ValueError):
    pass

def _normalize_text(text: str) -> str:
    """
    Produce stable whitespace normalization while preserving
    the original wording.
    """
    return re.sub(r"\s+", " ", text).strip()

def chunk_text(
    text: str, *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS
) -> list[str]:
    """
    Deterministically split normalized text.

    Uses character-bounded chunks with overlap.
    Where possible, chunk boundaries are moved backward
    to a whitespace boundary.
    """
    if max_chars < 200:
        raise DocumentIngestionError("max_chars must be >= 200.")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise DocumentIngestionError(
            "overlap_chars must be bounded in [0, max_chars)."
        )

    normalized = _normalize_text(text)
    if not normalized:
        return []

    chunks: list[str] = []

    start = 0
    text_length = len(normalized)

    while start < text_length:
        tentative_end = min(start + max_chars, text_length)
        end = tentative_end

        # Avoid cutting in the middle of a word when
        # a reasonable whitespace boundary exists.
        if tentative_end < text_length:
            boundary = normalized.rfind(
                " ",
                start + (max_chars // 2),
                tentative_end
            )
            if boundary > start:
                end = boundary

        content = normalized[start:end].strip()
        if content:
            chunks.append(content)

        if end >= text_length:
            break

        next_start = max(start + 1, end - overlap_chars)

        while (
            next_start < text_length
            and normalized[next_start].isspace()
        ):
            next_start += 1

        start = next_start

    return chunks

def extract_pdf_chunks(
    pdf_path: str | Path, *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS
) -> list[ExtractedDocumentChunk]:
    """
    Extract text from a text-based PDF while preserving
    page-level provenance.

    OCR is deliberately outside V1.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise DocumentIngestionError(f"Document does not exist: {path}")
    if not path.is_file():
        raise DocumentIngestionError(f"Document path is not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise DocumentIngestionError("Document ingestion supports PDF files only.")

    try:
        reader = PdfReader(str(path))
    except (OSError, PdfReadError) as exc:
        raise DocumentIngestionError("Unable to read PDF document.") from exc

    extracted: list[ExtractedDocumentChunk] = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""

        page_chunks = chunk_text(raw_text, max_chars=max_chars, overlap_chars=overlap_chars)

        for page_chunk_index, content in enumerate(page_chunks):
            extracted.append(
                ExtractedDocumentChunk(
                    page_number=page_number,
                    page_chunk_index=page_chunk_index,
                    content=content,
                    locator=f"p. {page_number}"
                )
            )

    if not extracted:
        raise DocumentIngestionError("PDF contains no extractable text. OCR is not supported in ingestion.")
    return extracted

def _sha256_file(path: Path,) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def ingest_pdf_document(
    session: Session, *,
    pdf_path: str | Path, source: EvidenceSourceCreate,
    embedder: DenseEmbedder, crop: str | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS
) -> DocumentIngestionResult:
    """
    Ingest one PDF into the RAG corpus.

    Pipeline:
        PDF
        -> extraction
        -> deterministic chunks
        -> EvidenceSource
        -> KnowledgeChunk
        -> dense embedding

    The operation uses a database savepoint so a failed
    embedding does not leave a partially ingested document.
    """
    path = Path(pdf_path)

    extracted = extract_pdf_chunks(path, max_chars=max_chars, overlap_chars=overlap_chars)

    file_sha256 = _sha256_file(path)

    source_metadata = {
        **source.source_metadata,

        "filename": path.name,
        "sha256": file_sha256,
        "document_format": "pdf",
        "chunking_version": CHUNKING_VERSION,

        "chunk_max_chars": max_chars,
        "chunk_overlap_chars": overlap_chars,
    }

    source_input = source.model_copy(
        update={
            "source_metadata": source_metadata
        }
    )

    chunk_ids = []

    # Atomic ingestion boundary.
    with session.begin_nested():
        db_source = register_evidence_source(session, source_input)

        for chunk_index, item in enumerate(extracted):
            db_chunk = (
                register_knowledge_chunk(
                    session,
                    KnowledgeChunkCreate(
                        source_id=db_source.id,
                        chunk_index=chunk_index,

                        content=item.content,
                        locator=item.locator,
                        language=source.language,
                        crop=crop,

                        chunk_metadata={
                            "page_number": item.page_number,
                            "page_chunk_index": item.page_chunk_index,
                            "chunking_version": CHUNKING_VERSION,
                        },
                    ),
                )
            )

            embed_chunk(
                session,
                chunk_id=db_chunk.id,
                embedder=embedder,
            )

            chunk_ids.append(db_chunk.id)

    return DocumentIngestionResult(
        source_id=db_source.id,
        chunk_ids=chunk_ids,
        chunk_count=len(chunk_ids),

        page_count_with_text=len(
            {
                item.page_number
                for item in extracted
            }
        ),
    )