import datetime
import uuid

from agriworldmodel.decisions.evidence_packet import (
    DecisionEvidencePacket,
    DecisionEvidenceStatus,
)
from agriworldmodel.decisions.readiness import (
    DecisionReadinessPacket,
)
from agriworldmodel.decisions.reasoning_packet import (
    DecisionReasoningPacket,
    DecisionReasoningStatus,
)
from agriworldmodel.decisions.requirements import (
    MissingDataReport,
)
from agriworldmodel.decisions.schemas import (
    DecisionContext,
    DecisionType,
)
from agriworldmodel.llm.factory import (
    build_llm_provider,
)
from agriworldmodel.llm.service import (
    generate_structured_decision,
)
from agriworldmodel.retrieval.schemas import (
    RerankedChunk,
)
from agriworldmodel.state.derived import (
    FertilizerApplicationState,
    NutrientState,
)
from agriworldmodel.state.schemas import (
    FarmStateSnapshot,
)
from agriworldmodel.tools.schemas import (
    CalculatedFact,
    ToolExecutionPacket,
    ToolExecutionRecord,
    ToolExecutionStatus,
)


UTC = datetime.timezone.utc


def dt(day: int) -> datetime.datetime:
    return datetime.datetime(
        2026,
        9,
        day,
        8,
        0,
        tzinfo=UTC,
    )


# -------------------------------------------------------------------
# Stable fixture IDs make it easy to verify whether the LLM cites
# exactly the evidence and farm event that were supplied.
# -------------------------------------------------------------------

MANAGEMENT_UNIT_ID = uuid.UUID(
    "11111111-1111-1111-1111-111111111111"
)

CROP_CYCLE_ID = uuid.UUID(
    "22222222-2222-2222-2222-222222222222"
)

SOURCE_EVENT_ID = uuid.UUID(
    "33333333-3333-3333-3333-333333333333"
)

EVIDENCE_CHUNK_ID = uuid.UUID(
    "44444444-4444-4444-4444-444444444444"
)

EVIDENCE_SOURCE_ID = uuid.UUID(
    "55555555-5555-5555-5555-555555555555"
)


# -------------------------------------------------------------------
# 1. Deterministic farm state
# -------------------------------------------------------------------

farm_state = FarmStateSnapshot(
    management_unit_id=MANAGEMENT_UNIT_ID,
    crop_cycle_id=CROP_CYCLE_ID,

    effective_at=dt(15),
    knowledge_cutoff=dt(15),

    events=[],
)


last_application = FertilizerApplicationState(
    event_id=SOURCE_EVENT_ID,

    occurred_at=dt(10),
    days_since=5,

    product_name="Fixture NPK 20-10-5",

    amount=2.0,
    amount_unit="kg",
    basis="per_tree",

    n_pct=20.0,
    p2o5_pct=10.0,
    k2o_pct=5.0,
)


nutrient_state = NutrientState(
    application_count=1,
    last_application=last_application,
)


context = DecisionContext(
    decision_type=DecisionType.NUTRIENT,

    management_unit_id=MANAGEMENT_UNIT_ID,
    crop_cycle_id=CROP_CYCLE_ID,

    effective_at=dt(15),
    knowledge_cutoff=dt(15),

    farm_name="Controlled Fixture Farm",
    management_unit_name="Durian Block A",

    crop="durian",
    cultivar="Ri6",

    area_m2=20_000,
    tree_count=100,

    farm_state=farm_state,

    nutrient_state=nutrient_state,
    crop_protection_state=None,
)


# -------------------------------------------------------------------
# 2. Missing-data gate
# -------------------------------------------------------------------

missing_data = MissingDataReport(
    decision_type=DecisionType.NUTRIENT,

    ready=True,

    checked_requirements=[],

    missing_required=[],
    missing_optional=[],
)


readiness = DecisionReadinessPacket(
    context=context,

    requirements=[],

    missing_data=missing_data,

    requirement_provenance=[],
)


# -------------------------------------------------------------------
# 3. Controlled evidence
#
# This is deliberately synthetic test evidence.
# It must NOT later be treated as research/agronomic evidence.
# -------------------------------------------------------------------

evidence = RerankedChunk(
    chunk_id=EVIDENCE_CHUNK_ID,

    source_id=EVIDENCE_SOURCE_ID,

    source_type="fixture",

    source_title=(
        "Controlled N1 Integration Fixture"
    ),

    chunk_index=0,

    content=(
        "Before considering another nitrogen application, "
        "account for nitrogen supplied by the recent fertilizer "
        "application and evaluate the current crop condition. "
        "A recommendation should not ignore recent nitrogen input."
    ),

    locator="fixture:p1",

    crop="durian",

    lexical_rank=1,
    dense_rank=1,

    lexical_score=1.0,
    dense_score=1.0,

    rrf_score=1.0,

    hybrid_rank=1,
    rerank_score=1.0,
)


evidence_packet = DecisionEvidencePacket(
    status=DecisionEvidenceStatus.READY,

    question=(
        "What should be considered before another "
        "nitrogen application for this durian block?"
    ),

    retrieval_query=(
        "What should be considered before another "
        "nitrogen application for this durian block?"
    ),

    readiness=readiness,

    evidence=[evidence],

    ready_for_reasoning=True,
)


# -------------------------------------------------------------------
# 4. Trusted deterministic calculation
#
# 2 kg/tree × 100 trees = 200 kg product
# 200 kg × 20% N = 40 kg N
#
# The LLM is NOT asked to calculate these.
# -------------------------------------------------------------------

execution = ToolExecutionRecord(
    tool_name=(
        "fertilizer_application_normalizer"
    ),

    tool_version="1.0",

    status=ToolExecutionStatus.SUCCESS,

    inputs={
        "amount": 2.0,
        "amount_unit": "kg",
        "basis": "per_tree",
        "tree_count": 100,
        "area_m2": 20_000,
        "n_pct": 20.0,
        "p2o5_pct": 10.0,
        "k2o_pct": 5.0,
    },

    outputs={
        "product_kg_total": 200.0,
        "product_kg_per_tree": 2.0,
        "product_kg_per_ha": 100.0,

        "n_kg_total": 40.0,
        "p2o5_kg_total": 20.0,
        "k2o_kg_total": 10.0,
    },

    source_event_ids=[
        SOURCE_EVENT_ID
    ],
)


facts = [
    CalculatedFact(
        name="product_kg_total",
        value=200.0,
        unit="kg",
        source_tool=(
            "fertilizer_application_normalizer"
        ),
        source_event_ids=[
            SOURCE_EVENT_ID
        ],
    ),

    CalculatedFact(
        name="n_kg_total",
        value=40.0,
        unit="kg N",
        source_tool=(
            "fertilizer_application_normalizer"
        ),
        source_event_ids=[
            SOURCE_EVENT_ID
        ],
    ),
]


tool_packet = ToolExecutionPacket(
    executions=[execution],
    calculated_facts=facts,
)


# -------------------------------------------------------------------
# 5. Final deterministic pre-LLM boundary
# -------------------------------------------------------------------

reasoning_packet = DecisionReasoningPacket(
    status=DecisionReasoningStatus.READY,

    decision_evidence=evidence_packet,

    tool_execution=tool_packet,

    blocking_reasons=[],

    ready_for_llm=True,
)


# -------------------------------------------------------------------
# 6. Actual local Qwen inference through LM Studio
# -------------------------------------------------------------------

provider = build_llm_provider()


print()
print("==========================================")
print("AgriWorldModel live local reasoning test")
print("==========================================")

print()
print("Provider:")
print(type(provider).__name__)

print()
print("Model:")
print(provider.model_name)

print()
print("Allowed evidence chunk:")
print(EVIDENCE_CHUNK_ID)

print()
print(
    "Allowed calculated facts:",
    [
        fact.name
        for fact
        in tool_packet.calculated_facts
    ],
)


result = generate_structured_decision(
    reasoning_packet,
    provider=provider,
)


print()
print("==========================================")
print("VALIDATED RESULT")
print("==========================================")

print(
    result.model_dump_json(
        indent=2
    )
)