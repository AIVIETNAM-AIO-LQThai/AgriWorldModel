import uuid
from typing import Any

from pydantic import BaseModel, Field

class KnowledgeChunkCreate(BaseModel):
    source_id: uuid.UUID
    chunk_index: int = Field(ge=0)

    content: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    language: str | None = None

    crop: str | None = None
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)

class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID

    source_id: uuid.UUID
    source_type: str
    source_title: str

    chunk_index: int

    content: str
    locator: str

    crop: str | None = None
    score: float

class HybridRetrievedChunk(BaseModel):
    chunk_id: uuid.UUID

    source_id: uuid.UUID
    source_type: str
    source_title: str

    chunk_index: int

    content: str
    locator: str

    crop: str | None = None

    lexical_rank: int | None = None
    dense_rank: int | None = None

    lexical_score: float | None = None
    dense_score: float | None = None

    rrf_score: float

class RerankedChunk(HybridRetrievedChunk):
    hybrid_rank: int
    rerank_score: float

class ExtractedDocumentChunk(BaseModel):
    """
    One deterministic chunk extracted from a source document
    before database persistence.
    """
    page_number: int = Field(ge=1)
    page_chunk_index: int = Field(ge=0)

    content: str = Field(min_length=1)
    locator: str = Field(min_length=1)

class DocumentIngestionResult(BaseModel):
    """
    Result of ingesting one document into the retrieval corpus.
    """
    source_id: uuid.UUID
    chunk_ids: list[uuid.UUID]

    chunk_count: int
    page_count_with_text: int