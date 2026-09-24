import datetime
import enum
import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from agriworldmodel.decisions.evidence_packet import (
    DecisionEvidencePacket, DecisionEvidenceStatus,
    prepare_decision_evidence,
)
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.retrieval.embedding import DenseEmbedder
from agriworldmodel.retrieval.reranker import Reranker
from agriworldmodel.tools.execution import execute_nutrient_context_tools
from agriworldmodel.tools.schemas import ToolExecutionPacket, ToolExecutionStatus

class DecisionReasoningError(ValueError):
    pass

class DecisionReasoningStatus(str, enum.Enum):
    BLOCKED_MISSING_DATA = "blocked_missing_data"
    BLOCKED_NO_EVIDENCE = "blocked_no_evidence"
    BLOCKED_TOOL_EXECUTION = "blocked_tool_execution"
    READY = "ready"

class DecisionReasoningPacket(BaseModel):
    """
    Complete deterministic boundary immediately before
    model reasoning.

    No model should need to recalculate deterministic values
    or independently retrieve evidence from inside this packet.
    """
    status: DecisionReasoningStatus
    decision_evidence: DecisionEvidencePacket
    tool_execution: ToolExecutionPacket
    blocking_reasons: list[str]
    ready_for_llm: bool

def _empty_tool_packet() -> ToolExecutionPacket:
    return ToolExecutionPacket(executions=[], calculated_facts=[],)

def prepare_decision_reasoning(
    session: Session, *,
    decision_type: DecisionType,
    management_unit_id: uuid.UUID, crop_cycle_id: uuid.UUID,
    effective_at: datetime.datetime, knowledge_cutoff: datetime.datetime,
    question: str,
    embedder: DenseEmbedder, reranker: Reranker,
    limit: int = 10, candidate_limit: int = 20,
) -> DecisionReasoningPacket:
    """
    Assemble the complete deterministic N1 input packet
    that may later be given to an LLM.

    V1 deliberately supports N1 only. P1 must not enter
    model reasoning until its deterministic compliance
    tools are implemented.
    """
    if decision_type != DecisionType.NUTRIENT:
        raise DecisionReasoningError("Decision reasoning V1 currently supports N1 only.")

    evidence_packet = prepare_decision_evidence(
        session,
        decision_type=decision_type,
        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,
        effective_at=effective_at,
        knowledge_cutoff=knowledge_cutoff,
        question=question,
        embedder=embedder,
        reranker=reranker,
        limit=limit,
        candidate_limit=candidate_limit,
    )

    if evidence_packet.status == DecisionEvidenceStatus.BLOCKED_MISSING_DATA:
        return DecisionReasoningPacket(
            status=DecisionReasoningStatus.BLOCKED_MISSING_DATA,
            decision_evidence=evidence_packet,
            tool_execution=_empty_tool_packet(),
            blocking_reasons=["Required farm data is missing."],
            ready_for_llm=False,
        )

    if evidence_packet.status == DecisionEvidenceStatus.NO_EVIDENCE:
        return DecisionReasoningPacket(
            status=DecisionReasoningStatus.BLOCKED_NO_EVIDENCE,
            decision_evidence=evidence_packet,
            tool_execution=_empty_tool_packet(),
            blocking_reasons=["No supporting evidence was retrieved."],
            ready_for_llm=False,
        )

    tool_packet = execute_nutrient_context_tools(
        evidence_packet.readiness.context
    )

    blocked_executions = [
        execution
        for execution in tool_packet.executions
        if execution.status == ToolExecutionStatus.BLOCKED
    ]

    if blocked_executions:
        reasons = [
            (
                execution.message
                or f"Tool {execution.tool_name} was blocked."
            )
            for execution in blocked_executions
        ]

        return DecisionReasoningPacket(
            status=DecisionReasoningStatus.BLOCKED_TOOL_EXECUTION,
            decision_evidence=evidence_packet,
            tool_execution=tool_packet,
            blocking_reasons=reasons,
            ready_for_llm=False,
        )

    return DecisionReasoningPacket(
        status=DecisionReasoningStatus.READY,
        decision_evidence=evidence_packet,
        tool_execution=tool_packet,
        blocking_reasons=[],
        ready_for_llm=True,
    )