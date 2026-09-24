import datetime
import enum
import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from agriworldmodel.decisions.readiness import DecisionReadinessPacket, prepare_decision_readiness
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.retrieval.embedding import DenseEmbedder
from agriworldmodel.retrieval.rerank import search_reranked_chunks
from agriworldmodel.retrieval.reranker import Reranker
from agriworldmodel.retrieval.schemas import RerankedChunk

class DecisionEvidenceError(ValueError):
    pass

class DecisionEvidenceStatus(str, enum.Enum):
    BLOCKED_MISSING_DATA = "blocked_missing_data"
    NO_EVIDENCE = "no_evidence"
    READY = "ready"

class DecisionEvidencePacket(BaseModel):
    """
    Deterministic input boundary immediately before reasoning.

    It combines:
    - farm/decision readiness
    - the user's decision question
    - final reranked evidence
    - an explicit reasoning gate
    """
    status: DecisionEvidenceStatus
    question: str

    # None when retrieval was deliberately skipped because
    # required farm data was missing.
    retrieval_query: str | None = None

    readiness: DecisionReadinessPacket

    evidence: list[RerankedChunk]

    ready_for_reasoning: bool

def prepare_decision_evidence(
    session: Session, *, decision_type: DecisionType,
    management_unit_id: uuid.UUID, crop_cycle_id: uuid.UUID,
    effective_at: datetime.datetime,knowledge_cutoff: datetime.datetime,
    question: str,
    embedder: DenseEmbedder, reranker: Reranker,
    limit: int = 10, candidate_limit: int = 20,
) -> DecisionEvidencePacket:
    """
    Assemble the complete deterministic pre-reasoning packet.

    Retrieval is deliberately skipped when required farm data
    is missing.

    For V1, the original decision question is used directly as
    the retrieval query. Crop is applied as a structured filter
    instead of being appended to the query text.
    """
    normalized_question = question.strip()
    if not normalized_question:
        raise DecisionEvidenceError("Decision question must not be blank.")
    if limit < 1:
        raise DecisionEvidenceError("limit must be >= 1.")
    if candidate_limit < limit:
        raise DecisionEvidenceError("candidate_limit must be >= limit.")

    readiness = prepare_decision_readiness(
        session, decision_type=decision_type,
        management_unit_id=management_unit_id, crop_cycle_id=crop_cycle_id,
        effective_at=effective_at, knowledge_cutoff=knowledge_cutoff
    )

    # Hard gate:
    # do not retrieve decision evidence when required
    # farm-state information is missing.
    if not readiness.missing_data.ready:
        return DecisionEvidencePacket(
            status=DecisionEvidenceStatus.BLOCKED_MISSING_DATA,
            question=normalized_question,
            retrieval_query=None,
            readiness=readiness,
            evidence=[],
            ready_for_reasoning=False
        )

    evidence = search_reranked_chunks(
        session, query_text=normalized_question,
        embedder=embedder, reranker=reranker,
        crop=readiness.context.crop,
        limit=limit, candidate_limit=candidate_limit
    )

    if not evidence:
        return DecisionEvidencePacket(
            status=DecisionEvidenceStatus.NO_EVIDENCE,
            question=normalized_question,
            retrieval_query=normalized_question,
            readiness=readiness,
            evidence=[],
            ready_for_reasoning=False
        )

    return DecisionEvidencePacket(
        status=DecisionEvidenceStatus.READY,
        question=normalized_question,
        retrieval_query=normalized_question,
        readiness=readiness,
        evidence=evidence,
        ready_for_reasoning=True,
    )