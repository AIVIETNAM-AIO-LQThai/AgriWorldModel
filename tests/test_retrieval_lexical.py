import uuid

import pytest

from agriworldmodel.evidence.schemas import EvidenceSourceCreate, EvidenceSourceType
from agriworldmodel.evidence.service import register_evidence_source
from agriworldmodel.retrieval.ingestion import RetrievalIngestionError, register_knowledge_chunk
from agriworldmodel.retrieval.lexical import search_lexical_chunks
from agriworldmodel.retrieval.schemas import KnowledgeChunkCreate


def make_source(
    db_session, *, title="Synthetic Retrieval Source",
):
    return register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title=title,
            publisher="Fixture Publisher",
            published_year=2026,
            language="en",
        ),
    )

# -------------------------------------------------------------------
# 1. A chunk cannot reference a nonexistent evidence source.
# -------------------------------------------------------------------
def test_chunk_requires_existing_source(
    db_session,
):
    with pytest.raises(RetrievalIngestionError):
        register_knowledge_chunk(
            db_session,
            KnowledgeChunkCreate(
                source_id=uuid.uuid4(),
                chunk_index=0,
                content="Synthetic fixture content.",
                locator="p. 1",
            ),
        )

# -------------------------------------------------------------------
# 2. A source chunk can be registered.
# -------------------------------------------------------------------
def test_register_knowledge_chunk(db_session):
    source = make_source(db_session)

    chunk = register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=0,
            content="Synthetic nitrogen uptake fixture.",
            locator="p. 12",
            crop="durian",
        ),
    )

    assert chunk.id is not None
    assert chunk.source_id == source.id
    assert chunk.chunk_index == 0
    assert chunk.locator == "p. 12"

# -------------------------------------------------------------------
# 3. Lexical retrieval returns the matching source chunk.
# -------------------------------------------------------------------
def test_lexical_retrieval_finds_relevant_chunk(db_session):
    source = make_source(db_session)

    relevant = register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=0,
            content="Nitrogen uptake increases in this synthetic fixture condition.",
            locator="p. 10",
        ),
    )

    register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=1,
            content="Synthetic irrigation scheduling fixture with unrelated terminology.",
            locator="p. 11",
        ),
    )

    results = search_lexical_chunks(db_session, query_text="nitrogen uptake")

    assert len(results) >= 1
    assert results[0].chunk_id == relevant.id
    assert results[0].score > 0

# -------------------------------------------------------------------
# 4. Crop-scoped retrieval cannot leak another crop's chunks.
# -------------------------------------------------------------------
def test_lexical_retrieval_respects_crop_scope(db_session):
    source = make_source(db_session)

    durian_chunk = register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=0,
            content="Synthetic potassium timing fixture.",
            locator="p. 20",
            crop="durian",
        ),
    )

    register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=1,
            content="Synthetic potassium timing fixture.",
            locator="p. 21",
            crop="rice",
        ),
    )

    results = search_lexical_chunks(
        db_session, query_text="potassium timing", crop="durian",
    )

    assert len(results) == 1
    assert results[0].chunk_id == durian_chunk.id

# -------------------------------------------------------------------
# 5. Retrieval keeps exact source provenance.
# -------------------------------------------------------------------
def test_retrieval_returns_source_provenance(db_session):
    source = make_source(db_session, title="Fixture Provenance Source")

    register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=3,
            content="Synthetic magnesium deficiency retrieval fixture.",
            locator="Section 4.2",
        ),
    )

    results = search_lexical_chunks(db_session, query_text="magnesium deficiency",)

    assert len(results) == 1

    result = results[0]

    assert result.source_id == source.id
    assert result.source_title == "Fixture Provenance Source"
    assert result.locator == "Section 4.2"