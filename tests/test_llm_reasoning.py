import datetime
import uuid

import pytest

from agriworldmodel.decisions.evidence_packet import DecisionEvidencePacket, DecisionEvidenceStatus
from agriworldmodel.decisions.readiness import DecisionReadinessPacket
from agriworldmodel.decisions.reasoning_packet import DecisionReasoningPacket, DecisionReasoningStatus
from agriworldmodel.decisions.requirements import MissingDataReport
from agriworldmodel.decisions.schemas import DecisionContext, DecisionType
from agriworldmodel.llm.service import LLMReasoningError, generate_structured_decision
from agriworldmodel.llm.schemas import DecisionRecommendation
from agriworldmodel.retrieval.schemas import RerankedChunk
from agriworldmodel.state.derived import NutrientState
from agriworldmodel.state.schemas import FarmStateSnapshot
from agriworldmodel.tools.schemas import CalculatedFact, ToolExecutionPacket, ToolExecutionRecord, ToolExecutionStatus

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC,)

class FakeProvider:
    model_name = "fixture-model"

    def __init__(
        self, response: dict,
    ):
        self.response = response
        self.calls = 0
        self.last_system_prompt = None
        self.last_payload = None
        self.last_response_model = None

    def generate_json(
        self, *, system_prompt: str, payload: dict, response_model,
    ) -> dict:
        self.calls += 1
        self.last_system_prompt = system_prompt
        self.last_payload = payload
        self.last_response_model = response_model

        return self.response

class ExplodingProvider:
    model_name = "must-not-run"

    def generate_json(
        self, *, system_prompt: str, payload: dict, response_model
    ) -> dict:
        raise AssertionError("LLM must not run for a blocked packet.")

def make_ready_reasoning_packet():
    """
    Construct the smallest valid READY DecisionReasoningPacket
    using the actual current AgriWorldModel schemas.
    """
    management_unit_id = uuid.uuid4()
    crop_cycle_id = uuid.uuid4()
    source_event_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    # ---------------------------------------------------------------
    # 1. Farm state
    # ---------------------------------------------------------------
    farm_state = FarmStateSnapshot(
        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        events=[],
    )

    # ---------------------------------------------------------------
    # 2. Decision context
    # ---------------------------------------------------------------
    context = DecisionContext(
        decision_type=DecisionType.NUTRIENT,

        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,

        effective_at=dt(15),
        knowledge_cutoff=dt(15),

        farm_name="Fixture Farm",
        management_unit_name="Block LLM-1",

        crop="durian",
        cultivar="Ri6",

        area_m2=20_000,
        tree_count=100,

        farm_state=farm_state,

        nutrient_state=NutrientState(
            application_count=0, last_application=None,
        ),

        crop_protection_state=None,
    )

    # ---------------------------------------------------------------
    # 3. Missing-data report
    # ---------------------------------------------------------------
    missing_data = MissingDataReport(
        decision_type=DecisionType.NUTRIENT,
        ready=True,
        checked_requirements=[],
        missing_required=[],
        missing_optional=[],
    )

    # ---------------------------------------------------------------
    # 4. Decision readiness
    # ---------------------------------------------------------------
    readiness = DecisionReadinessPacket(
        context=context,
        requirements=[],
        missing_data=missing_data,
        requirement_provenance=[],
    )

    # ---------------------------------------------------------------
    # 5. Retrieved/reranked evidence
    # ---------------------------------------------------------------
    evidence = RerankedChunk(
        chunk_id=chunk_id,

        source_id=uuid.uuid4(),
        source_type="literature",
        source_title="Fixture Agronomy Source",

        chunk_index=0,

        content="Synthetic nitrogen evidence.",
        locator="p. 12",

        crop="durian",

        lexical_rank=1, dense_rank=1,
        lexical_score=0.4, dense_score=0.9, rrf_score=0.03, 
        hybrid_rank=1, rerank_score=0.95,
    )

    evidence_packet = DecisionEvidencePacket(
        status=DecisionEvidenceStatus.READY,

        question="What nitrogen action is appropriate?",
        retrieval_query="What nitrogen action is appropriate?",

        readiness=readiness,
        evidence=[evidence],
        ready_for_reasoning=True,
    )

    # ---------------------------------------------------------------
    # 6. Trusted deterministic calculation
    # ---------------------------------------------------------------
    execution = ToolExecutionRecord(
        tool_name="fertilizer_application_normalizer",
        tool_version="1.0",
        status=ToolExecutionStatus.SUCCESS,

        inputs={
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
            "tree_count": 100,
        },

        outputs={
            "product_kg_total": 200.0,
            "n_kg_total": 40.0,
        },

        source_event_ids=[source_event_id],
    )

    fact = CalculatedFact(
        name="n_kg_total",
        value=40.0,
        unit="kg N",
        source_tool="fertilizer_application_normalizer",
        source_event_ids=[source_event_id],
    )

    tool_packet = ToolExecutionPacket(
        executions=[execution], calculated_facts=[fact],
    )

    # ---------------------------------------------------------------
    # 7. Final READY reasoning packet
    # ---------------------------------------------------------------
    packet = DecisionReasoningPacket(
        status=DecisionReasoningStatus.READY,
        decision_evidence=evidence_packet,
        tool_execution=tool_packet,
        blocking_reasons=[],
        ready_for_llm=True,
    )

    return packet, chunk_id

def make_blocked_reasoning_packet():
    management_unit_id = uuid.uuid4()
    crop_cycle_id = uuid.uuid4()

    farm_state = FarmStateSnapshot(
        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        events=[],
    )

    context = DecisionContext(
        decision_type=DecisionType.NUTRIENT,

        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,

        effective_at=dt(15),
        knowledge_cutoff=dt(15),

        farm_name="Fixture Farm",
        management_unit_name="Block LLM-1",

        crop="durian",
        cultivar="Ri6",

        area_m2=20_000,
        tree_count=100,

        farm_state=farm_state,
        nutrient_state=NutrientState(
            application_count=0,
            last_application=None,
        ),

        crop_protection_state=None,
    )

    readiness = DecisionReadinessPacket(
        context=context,
        requirements=[],

        missing_data=MissingDataReport(
            decision_type=DecisionType.NUTRIENT,
            ready=True,
            checked_requirements=[],
            missing_required=[],
            missing_optional=[],
        ),

        requirement_provenance=[],
    )

    evidence_packet = DecisionEvidencePacket(
        status=DecisionEvidenceStatus.NO_EVIDENCE,
        question="What nitrogen action is appropriate?",
        retrieval_query="What nitrogen action is appropriate?",

        readiness=readiness,
        evidence=[],
        ready_for_reasoning=False,
    )

    return DecisionReasoningPacket(
        status=DecisionReasoningStatus.BLOCKED_NO_EVIDENCE,
        decision_evidence=evidence_packet,

        tool_execution=ToolExecutionPacket(
            executions=[], calculated_facts=[]
        ),

        blocking_reasons=["No supporting evidence was retrieved."],

        ready_for_llm=False,
    )

# -------------------------------------------------------------------
# 1. A blocked reasoning packet must never invoke the model.
# -------------------------------------------------------------------
def test_blocked_packet_never_calls_llm():
    packet = make_blocked_reasoning_packet()

    with pytest.raises(LLMReasoningError):
        generate_structured_decision(
            packet,
            provider=ExplodingProvider(),
        )


# -------------------------------------------------------------------
# 2. A READY packet should pass through the provider boundary.
# -------------------------------------------------------------------
def test_ready_packet_calls_provider():
    packet, chunk_id = make_ready_reasoning_packet()

    provider = FakeProvider(
        {
            "recommendation": "Use the verified farm and evidence context.",

            "rationale": ["The recommendation is grounded in the supplied evidence and calculated facts."],
            "action_steps": ["Review the verified nitrogen context."],
            "evidence_chunk_ids": [str(chunk_id)],
            "calculated_fact_names": ["n_kg_total"],
            "uncertainties": [],
        }
    )

    result = generate_structured_decision(packet, provider=provider)

    assert provider.calls == 1
    assert result.model_name == "fixture-model"
    assert result.prompt_version == "n1-v1"
    assert result.recommendation.evidence_chunk_ids == [chunk_id]
    assert result.recommendation.calculated_fact_names == ["n_kg_total"]
    assert provider.last_response_model is DecisionRecommendation

    # Verify deterministic data actually reaches
    # the provider boundary.
    assert provider.last_payload["status"] == "ready"
    assert provider.last_payload["tool_execution"]["calculated_facts"][0]["name"] == "n_kg_total"

# -------------------------------------------------------------------
# 3. The model must not cite evidence outside the reasoning packet.
# -------------------------------------------------------------------
def test_unknown_evidence_reference_is_rejected():
    packet, _ = make_ready_reasoning_packet()

    provider = FakeProvider(
        {
            "recommendation": "Fixture recommendation.",
            "rationale": ["Fixture rationale."],
            "action_steps": [],
            "evidence_chunk_ids": [str(uuid.uuid4())],
            "calculated_fact_names": [],
            "uncertainties": [],
        }
    )

    with pytest.raises(LLMReasoningError):
        generate_structured_decision(packet, provider=provider)

# -------------------------------------------------------------------
# 4. The model must not invent deterministic calculated facts.
# -------------------------------------------------------------------
def test_unknown_calculated_fact_is_rejected():
    packet, chunk_id = make_ready_reasoning_packet()
    provider = FakeProvider(
        {
            "recommendation": "Fixture recommendation.",
            "rationale": ["Fixture rationale."],
            "action_steps": [],
            "evidence_chunk_ids": [str(chunk_id)],
            "calculated_fact_names": ["invented_nitrogen_value"],
            "uncertainties": [],
        }
    )

    with pytest.raises(LLMReasoningError):
        generate_structured_decision(packet, provider=provider)


# -------------------------------------------------------------------
# 5. Malformed model output must fail schema validation.
# -------------------------------------------------------------------
def test_invalid_model_schema_is_rejected():
    packet, _ = make_ready_reasoning_packet()

    provider = FakeProvider(
        {
            # Invalid because recommendation must
            # contain at least one character.
            "recommendation": "",

            # Invalid because rationale requires
            # at least one entry.
            "rationale": [],

            # Invalid because at least one evidence
            # chunk must be referenced.
            "evidence_chunk_ids": [],
        }
    )

    with pytest.raises(LLMReasoningError):
        generate_structured_decision(packet, provider=provider)