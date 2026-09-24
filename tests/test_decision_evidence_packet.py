import datetime

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.evidence_packet import DecisionEvidenceStatus, prepare_decision_evidence
from agriworldmodel.decisions.registry import DecisionRequirementCreate, register_decision_requirement
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.evidence.schemas import (
    AgronomicAssertionCreate, AssertionType,
    EvidenceSourceCreate, EvidenceSourceType, EvidenceSupportCreate,
)
from agriworldmodel.evidence.service import register_evidence_source, register_supported_assertion
from agriworldmodel.retrieval.dense import embed_chunk
from agriworldmodel.retrieval.embedding import EMBEDDING_DIMENSION
from agriworldmodel.retrieval.ingestion import register_knowledge_chunk
from agriworldmodel.retrieval.schemas import KnowledgeChunkCreate


UTC = datetime.timezone.utc


def dt(day: int) -> datetime.datetime:
    return datetime.datetime(
        2026, 9, day, 8, 0, tzinfo=UTC,
    )

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
        return [
            (
                vector_at(0)
                if "nitrogen" in text.lower()
                else vector_at(1)
            )
            for text in texts
        ]

    def embed_query(
        self, text: str,
    ) -> list[float]:
        if "nitrogen" in text.lower():
            return vector_at(0)
        return vector_at(1)


class FakeReranker:
    model_name = "fixture-reranker"
    def score(
        self, *, query: str, passages: list[str],
    ) -> list[float]:
        return [
            (
                0.95
                if "preferred" in passage.lower()
                else 0.10
            )
            for passage in passages
        ]

class ExplodingEmbedder:
    model_name = "must-not-run"
    dimension = EMBEDDING_DIMENSION

    def embed_documents(self, texts):
        raise AssertionError("Embedding must not run when data is missing.")

    def embed_query(self, text):
        raise AssertionError("Embedding must not run when data is missing.")


class ExplodingReranker:
    model_name = "must-not-run"
    def score(self, *, query, passages):
        raise AssertionError("Reranking must not run when data is missing.")

def make_crop_cycle(db_session, *, crop="durian", cultivar="Ri6"):
    farm = Farm(name="Evidence Packet Fixture Farm", province="Dong Nai")

    unit = ManagementUnit(
        farm=farm,
        name="Block C1",
        area_m2=10_000,
    )

    db_session.add(farm)
    db_session.flush()

    cycle = CropCycle(
        management_unit_id=unit.id,
        crop=crop,
        cultivar=cultivar,
    )

    db_session.add(cycle)
    db_session.flush()

    return unit, cycle

def add_cultivar_requirement(db_session, *, crop="durian"):
    source = register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Synthetic Requirement Source",
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
            object_text="cultivar information",
            crop=crop,
        ),
        supports=[
            EvidenceSupportCreate(
                source_id=source.id,
                locator="p. 10",
            )
        ],
    )

    register_decision_requirement(
        db_session,
        DecisionRequirementCreate(
            assertion_id=assertion.id,
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Fixture cultivar requirement.",
        ),
    )

    return assertion

def make_retrieval_source(db_session):
    return register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Synthetic Decision Evidence Source",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

def make_chunk(
    db_session, source, *,
    index: int, content: str, crop: str | None = None,
):
    return register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=index,
            content=content,
            locator=f"p. {index + 20}",
            crop=crop,
        ),
    )

# -------------------------------------------------------------------
# 1. Missing required farm data must block retrieval and reasoning.
# -------------------------------------------------------------------
def test_missing_data_blocks_retrieval(db_session):
    unit, cycle = make_crop_cycle(
        db_session, cultivar=None,
    )

    add_cultivar_requirement(db_session)

    packet = prepare_decision_evidence(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen timing",
        embedder=ExplodingEmbedder(),
        reranker=ExplodingReranker(),
    )

    assert packet.status == DecisionEvidenceStatus.BLOCKED_MISSING_DATA
    assert packet.ready_for_reasoning is False
    assert packet.retrieval_query is None
    assert packet.evidence == []
    assert len(packet.readiness.missing_data.missing_required) == 1

# -------------------------------------------------------------------
# 2. A ready decision should retrieve and rerank supporting evidence.
# -------------------------------------------------------------------
def test_ready_decision_builds_evidence_packet(db_session):
    unit, cycle = make_crop_cycle(
        db_session, cultivar="Ri6",
    )

    add_cultivar_requirement(db_session)
    source = make_retrieval_source(db_session)

    ordinary = make_chunk(
        db_session, source, index=0,
        content="Synthetic nitrogen ordinary evidence.", crop="durian",
    )

    preferred = make_chunk(
        db_session, source, index=1,
        content="Synthetic nitrogen preferred evidence.", crop="durian",
    )

    embedder = FakeEmbedder()

    for chunk in [ordinary, preferred]:
        embed_chunk(
            db_session,
            chunk_id=chunk.id,
            embedder=embedder,
        )

    packet = prepare_decision_evidence(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen",
        embedder=embedder,
        reranker=FakeReranker(),
    )

    assert packet.status == DecisionEvidenceStatus.READY
    assert packet.ready_for_reasoning is True
    assert packet.retrieval_query == "nitrogen"
    assert len(packet.evidence) == 2
    assert packet.evidence[0].chunk_id == preferred.id
    assert packet.evidence[0].rerank_score == 0.95

# -------------------------------------------------------------------
# 3. Decision evidence retrieval must preserve crop isolation.
# -------------------------------------------------------------------
def test_decision_evidence_respects_crop_scope(db_session):
    unit, cycle = make_crop_cycle(
        db_session, crop="durian", cultivar="Ri6"
    )

    source = make_retrieval_source(db_session)

    durian = make_chunk(
        db_session, source, index=0,
        content="Synthetic nitrogen preferred evidence.", crop="durian",
    )

    rice = make_chunk(
        db_session, source, index=1,
        content="Synthetic nitrogen preferred evidence.", crop="rice",
    )

    embedder = FakeEmbedder()

    for chunk in [durian, rice]:
        embed_chunk(
            db_session,
            chunk_id=chunk.id,
            embedder=embedder,
        )

    packet = prepare_decision_evidence(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen",
        embedder=embedder,
        reranker=FakeReranker(),
    )

    assert packet.status == DecisionEvidenceStatus.READY
    assert len(packet.evidence) == 1
    assert packet.evidence[0].chunk_id == durian.id

# -------------------------------------------------------------------
# 4. Farm readiness alone must not permit evidence-free reasoning.
# -------------------------------------------------------------------
def test_no_retrieved_evidence_blocks_reasoning(db_session):
    unit, cycle = make_crop_cycle( db_session, cultivar="Ri6")

    packet = prepare_decision_evidence(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen",
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
    )

    assert packet.status == DecisionEvidenceStatus.NO_EVIDENCE
    assert packet.readiness.missing_data.ready is True
    assert packet.ready_for_reasoning is False
    assert packet.retrieval_query == "nitrogen"
    assert packet.evidence == []

# -------------------------------------------------------------------
# 5. Final decision evidence must retain retrieval provenance.
# -------------------------------------------------------------------
def test_decision_evidence_preserves_provenance(db_session):
    unit, cycle = make_crop_cycle(db_session)
    source = make_retrieval_source(db_session)
    chunk = make_chunk(
        db_session, source, index=0,
        content="Synthetic nitrogen preferred evidence.", crop="durian",
    )

    embedder = FakeEmbedder()

    embed_chunk(
        db_session,
        chunk_id=chunk.id,
        embedder=embedder,
    )

    packet = prepare_decision_evidence(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
        question="nitrogen",
        embedder=embedder,
        reranker=FakeReranker(),
    )

    result = packet.evidence[0]

    assert result.source_id == source.id
    assert result.source_title == "Synthetic Decision Evidence Source"
    assert result.locator == "p. 20"
    assert result.dense_rank is not None
    assert result.rerank_score == 0.95