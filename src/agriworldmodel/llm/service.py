from pydantic import ValidationError

from agriworldmodel.decisions.reasoning_packet import DecisionReasoningPacket, DecisionReasoningStatus
from agriworldmodel.llm.provider import LLMProvider
from agriworldmodel.llm.schemas import DecisionRecommendation, StructuredDecisionResult

DECISION_PROMPT_VERSION = "n1-v1"

DECISION_SYSTEM_PROMPT = """
You are the reasoning layer of an agricultural decision system.

Use only the information supplied in the reasoning packet.

Rules:
1. Do not invent farm facts.
2. Do not invent evidence.
3. Do not perform or replace deterministic calculations.
4. Numeric calculated facts should come from calculated_facts.
5. Evidence references must use chunk_id values supplied in evidence.
6. If important uncertainty remains, state it explicitly.
7. Do not claim that retrieved evidence proves more than its text supports.

Return a structured agricultural recommendation matching the required schema.
""".strip()

class LLMReasoningError(ValueError):
    pass

def build_llm_payload(packet: DecisionReasoningPacket) -> dict:
    """
    Convert the deterministic reasoning packet into the only
    payload exposed to the model.
    """
    if (
        packet.status != DecisionReasoningStatus.READY
        or not packet.ready_for_llm
    ):
        raise LLMReasoningError("Only a READY reasoning packet may be sent to an LLM.")

    return packet.model_dump(mode="json")

def _validate_model_references(
    packet: DecisionReasoningPacket,
    recommendation: DecisionRecommendation,
) -> None:
    """
    Ensure the model can reference only evidence and calculated
    facts that actually exist in the deterministic packet.
    """
    valid_chunk_ids = {
        chunk.chunk_id
        for chunk in packet.decision_evidence.evidence
    }

    unknown_chunk_ids = [
        chunk_id
        for chunk_id in recommendation.evidence_chunk_ids
        if chunk_id not in valid_chunk_ids
    ]

    if unknown_chunk_ids:
        raise LLMReasoningError(
            "Model referenced evidence chunks that are not present in the reasoning packet."
        )

    valid_fact_names = {
        fact.name
        for fact in packet.tool_execution.calculated_facts
    }

    unknown_fact_names = [
        fact_name
        for fact_name in recommendation.calculated_fact_names
        if fact_name not in valid_fact_names
    ]

    if unknown_fact_names:
        raise LLMReasoningError(
            "Model referenced calculated facts that are not present in the reasoning packet."
        )


def generate_structured_decision(
    packet: DecisionReasoningPacket, *, provider: LLMProvider,
) -> StructuredDecisionResult:
    """
    Run structured model reasoning over an already validated
    deterministic reasoning packet.
    """
    payload = build_llm_payload(packet)

    raw_response = provider.generate_json(
        system_prompt=DECISION_SYSTEM_PROMPT,
        payload=payload,
    )

    try:
        recommendation = DecisionRecommendation.model_validate(raw_response)

    except ValidationError as exc:
        raise LLMReasoningError("Model returned an invalid decision schema.") from exc

    _validate_model_references(packet, recommendation)

    return StructuredDecisionResult(
        model_name=provider.model_name,
        prompt_version=DECISION_PROMPT_VERSION,
        recommendation=recommendation,
    )