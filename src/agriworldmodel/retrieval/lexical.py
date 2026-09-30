from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.models.knowledge_chunk import KnowledgeChunk
from agriworldmodel.retrieval.schemas import RetrievedChunk

import re


_ENGLISH_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def _build_lexical_query(
    query_text: str,
) -> str:
    """
    Convert a natural-language question into a
    deterministic high-recall lexical query.

    The lexical branch is intended to provide recall.
    Dense retrieval and reranking provide semantic precision.
    """

    raw_terms = re.findall(
        r"[^\W_]+",
        query_text.lower(),
        flags=re.UNICODE,
    )

    terms: list[str] = []
    seen: set[str] = set()

    for term in raw_terms:
        if len(term) < 2:
            continue

        if term in _ENGLISH_QUERY_STOPWORDS:
            continue

        if term in seen:
            continue

        seen.add(term)
        terms.append(term)

    return " OR ".join(terms)

def search_lexical_chunks(
    session: Session, *,
    query_text: str,
    crop: str | None = None,
    limit: int = 10,
) -> list[RetrievedChunk]:
    """
    Retrieve source chunks using PostgreSQL full-text search.

    Crop scoping:
        crop-specific query includes
        - globally scoped chunks (crop=None)
        - chunks for the requested crop

    but excludes chunks belonging to other crops.
    """
    if not query_text.strip():
        return []

    lexical_query = _build_lexical_query(query_text)

    if not lexical_query:
        return []

    ts_query = func.websearch_to_tsquery(
        "simple", lexical_query,
    )

    rank = func.ts_rank_cd(
        KnowledgeChunk.search_vector, ts_query,
    ).label("score")

    stmt = (
        select(KnowledgeChunk, EvidenceSource, rank)
        .join(
            EvidenceSource,
            KnowledgeChunk.source_id == EvidenceSource.id,
        )
        .where(KnowledgeChunk.search_vector.op("@@")(ts_query))
    )

    if crop is not None:
        stmt = stmt.where(
            or_(
                KnowledgeChunk.crop.is_(None),
                func.lower(KnowledgeChunk.crop) == crop.lower(),
            )
        )

    stmt = (
        stmt
        .order_by(
            rank.desc(), KnowledgeChunk.id.asc(),
        ).limit(limit)
    )

    rows = session.execute(stmt).all()

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            source_id=source.id,
            source_type=source.source_type,
            source_title=source.title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            locator=chunk.locator,
            crop=chunk.crop,
            score=float(score),
        )
        for chunk, source, score in rows
    ]