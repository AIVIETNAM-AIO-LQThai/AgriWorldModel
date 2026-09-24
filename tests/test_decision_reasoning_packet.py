import datetime
import uuid

import pytest

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.event import Event
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.reasoning_packet import (
    DecisionReasoningError, DecisionReasoningStatus,
    prepare_decision_reasoning,
)
from agriworldmodel.decisions.registry import DecisionRequirementCreate, register_decision_requirement
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.evidence.schemas import (
    AgronomicAssertionCreate,
    AssertionType,
    EvidenceSourceCreate, EvidenceSourceType, EvidenceSupportCreate,
)
from agriworldmodel.evidence.service import register_evidence_source, register_supported_assertion
from agriworldmodel.retrieval.dense import embed_chunk
from agriworldmodel.retrieval.embedding import EMBEDDING_DIMENSION
from agriworldmodel.retrieval.ingestion import register_knowledge_chunk
from agriworldmodel.retrieval.schemas import KnowledgeChunkCreate
from agriworldmodel.tools.schemas import ToolExecutionStatus

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC)

def vector_at(index: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[index] = 1.0
    return vector

class FakeEmbedder:
    model_name = "fixture-embedder"
    dimension = EMBEDDING_DIMENSION

    def embed_documents(
        self, texts: list[str],
    ) -> list[list[float]]:
        return [vector_at(0) for _ in texts]

    def embed_query(
        self, text: str,
    ) -> list[float]:
        return vector_at(0)


class FakeReranker:
    model_name = "fixture-reranker"

    def score(
        self, *, query: str, passages: list[str],
    ) -> list[float]:
        return [0.9 for _ in passages]

class ExplodingEmbedder:
    model_name = "must-not-run"
    dimension = EMBEDDING_DIMENSION

    def embed_documents(self, texts):
        raise AssertionError("Retrieval must not run.")

    def embed_query(self, text):
        raise AssertionError("Retrieval must not run.")

class ExplodingReranker:
    model_name = "must-not-run"
    def score(self, *, query, passages):
        raise AssertionError("Reranking must not run.")

def make_farm_context(
    db_session,
    *,
    cultivar="Ri6",
    fertilizer_unit="kg",
):
    farm = Farm(
        name="Reasoning Fixture Farm",
        province="Dong Nai",
    )

    unit = ManagementUnit(
        farm=farm,
        name="Block R1",
        area_m2=20_000,
    )

    db_session.add(farm)
    db_session.flush()

    cycle = CropCycle(
        management_unit_id=unit.id,
        crop="durian",
        cultivar=cultivar,
        tree_count=100,
    )

    db_session.add(cycle)
    db_session.flush()

    event = Event(
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        recorded_at=dt(10),
        source="farm_record",
        payload={
            "product_name": "NPK Fixture",
            "amount": 2.0,
            "amount_unit": fertilizer_unit,
            "basis": "per_tree",
            "n_pct": 20.0,
            "p2o5_pct": 10.0,
            "k2o_pct": 5.0,
        },
    )

    db_session.add(event)
    db_session.flush()

    return unit, cycle

def add_retrievable_evidence(
    db_session,
    *,
    embedder,
):
    source = register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=(
                EvidenceSourceType.LITERATURE
            ),
            title="Reasoning Fixture Source",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

    chunk = register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=0,
            content="Synthetic nitrogen recommendation fixture evidence.",
            locator="p. 30",
            crop="durian",
        ),
    )

    embed_chunk(
        db_session,
        chunk_id=chunk.id,
        embedder=embedder,
    )

    return chunk

def add_cultivar_requirement(db_session):
    source = register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Reasoning Requirement Fixture",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

    assertion = register_supported_assertion(
        db_session,
        assertion=AgronomicAssertionCreate(
            assertion_type=AssertionType.REQUIREMENT,
            subject="fixture N1 decision",
            predicate="requires",
            object_text="cultivar",
            crop="durian",
        ),
        supports=[
            EvidenceSupportCreate(
                source_id=source.id,
                locator="p. 4",
            )
        ],
    )

    register_decision_requirement(
        db_session,
        DecisionRequirementCreate(
            assertion_id=assertion.id,
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Cultivar is required.",
        ),
    )

# -------------------------------------------------------------------
# 1. Missing farm data must block the packet before retrieval/tools.
# -------------------------------------------------------------------
def test_missing_data_blocks_reasoning_packet(db_session):
    unit, cycle = make_farm_context(db_session, cultivar=None)

    add_cultivar_requirement(db_session)

    packet = prepare_decision_reasoning(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen recommendation",
        embedder=ExplodingEmbedder(),
        reranker=ExplodingReranker(),
    )

    assert packet.status == DecisionReasoningStatus.BLOCKED_MISSING_DATA
    assert packet.ready_for_llm is False
    assert packet.tool_execution.executions == []

# -------------------------------------------------------------------
# 2. Missing retrieved evidence must prevent model reasoning.
# -------------------------------------------------------------------
def test_no_evidence_blocks_reasoning_packet(db_session):
    unit, cycle = make_farm_context(db_session)

    packet = prepare_decision_reasoning(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen recommendation",
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
    )

    assert packet.status == DecisionReasoningStatus.BLOCKED_NO_EVIDENCE
    assert packet.ready_for_llm is False
    assert packet.tool_execution.executions == []

# -------------------------------------------------------------------
# 3. A blocked deterministic tool must prevent model reasoning.
# -------------------------------------------------------------------
def test_blocked_tool_prevents_reasoning(db_session):
    unit, cycle = make_farm_context(db_session, fertilizer_unit="L")

    embedder = FakeEmbedder()

    add_retrievable_evidence(db_session, embedder=embedder)

    packet = prepare_decision_reasoning(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen recommendation",
        embedder=embedder,
        reranker=FakeReranker(),
    )

    assert packet.status == DecisionReasoningStatus.BLOCKED_TOOL_EXECUTION
    assert packet.ready_for_llm is False
    assert packet.tool_execution.executions[0].status == ToolExecutionStatus.BLOCKED

# -------------------------------------------------------------------
# 4. A valid N1 request should produce the complete pre-LLM packet.
# -------------------------------------------------------------------
def test_ready_reasoning_packet_contains_evidence_and_facts(db_session):
    unit, cycle = make_farm_context(db_session)

    embedder = FakeEmbedder()

    add_retrievable_evidence(
        db_session, embedder=embedder,
    )

    packet = prepare_decision_reasoning(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen recommendation",
        embedder=embedder,
        reranker=FakeReranker(),
    )

    assert packet.status == DecisionReasoningStatus.READY
    assert packet.ready_for_llm is True
    assert len(packet.decision_evidence.evidence) == 1

    facts = {
        fact.name: fact.value
        for fact in packet.tool_execution.calculated_facts
    }

    assert facts["product_kg_total"] == pytest.approx(200.0)
    assert facts["n_kg_total"] == pytest.approx(40.0)
    assert packet.blocking_reasons == []

# -------------------------------------------------------------------
# 5. P1 must remain blocked until its deterministic pipeline exists.
# -------------------------------------------------------------------
def test_reasoning_packet_v1_rejects_p1(
    db_session,
):
    with pytest.raises(DecisionReasoningError):
        prepare_decision_reasoning(
            db_session,
            decision_type=DecisionType.CROP_PROTECTION,
            management_unit_id=uuid.uuid4(),
            crop_cycle_id=uuid.uuid4(),
            effective_at=dt(15),
            knowledge_cutoff=dt(15),
            question="fungicide recommendation",
            embedder=FakeEmbedder(),
            reranker=FakeReranker(),
        )