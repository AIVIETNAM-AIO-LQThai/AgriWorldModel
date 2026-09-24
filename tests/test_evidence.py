import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from agriworldmodel.db.models.agronomic_assertion import (
    AgronomicAssertion,
)
from agriworldmodel.db.models.assertion_evidence import (
    AssertionEvidence,
)
from agriworldmodel.evidence.schemas import (
    AgronomicAssertionCreate,
    AssertionType,
    EffectDirection,
    EvidenceSourceCreate,
    EvidenceSourceType,
    EvidenceSupportCreate,
)
from agriworldmodel.evidence.service import (
    register_evidence_source,
    register_supported_assertion,
)
from agriworldmodel.evidence.validation import (
    EvidenceValidationError,
)


def make_fixture_source(db_session):
    return register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Synthetic Fixture Agronomy Document",
            publisher="Fixture Publisher",
            published_year=2026,
            language="en",
        ),
    )


# -------------------------------------------------------------------
# 1. An evidence source can be registered and persisted.
# -------------------------------------------------------------------
def test_register_evidence_source(db_session):
    source = make_fixture_source(db_session)

    assert source.id is not None
    assert source.source_type == "literature"
    assert (
        source.title
        == "Synthetic Fixture Agronomy Document"
    )


# -------------------------------------------------------------------
# 2. A directional-effect assertion must declare its direction.
# -------------------------------------------------------------------
def test_directional_assertion_requires_direction():
    with pytest.raises(ValidationError):
        AgronomicAssertionCreate(
            assertion_type=(
                AssertionType.DIRECTIONAL_EFFECT
            ),
            subject="fixture factor",
            predicate="affects",
            object_text="fixture outcome",
        )


# -------------------------------------------------------------------
# 3. An assertion cannot be registered without provenance.
# -------------------------------------------------------------------
def test_assertion_without_evidence_is_rejected(
    db_session,
):
    assertion = AgronomicAssertionCreate(
        assertion_type=AssertionType.RELATION,
        subject="fixture subject",
        predicate="relates_to",
        object_text="fixture object",
    )

    with pytest.raises(EvidenceValidationError):
        register_supported_assertion(
            db_session,
            assertion=assertion,
            supports=[],
        )


# -------------------------------------------------------------------
# 4. Evidence links cannot reference nonexistent sources.
# -------------------------------------------------------------------
def test_nonexistent_evidence_source_is_rejected(
    db_session,
):
    assertion = AgronomicAssertionCreate(
        assertion_type=AssertionType.RELATION,
        subject="fixture subject",
        predicate="relates_to",
        object_text="fixture object",
    )

    supports = [
        EvidenceSupportCreate(
            source_id=uuid.uuid4(),
            locator="p. 12",
        )
    ]

    with pytest.raises(EvidenceValidationError):
        register_supported_assertion(
            db_session,
            assertion=assertion,
            supports=supports,
        )


# -------------------------------------------------------------------
# 5. A supported assertion persists with an exact provenance link.
# -------------------------------------------------------------------
def test_supported_assertion_persists_with_provenance(
    db_session,
):
    source = make_fixture_source(db_session)

    assertion = AgronomicAssertionCreate(
        assertion_type=(
            AssertionType.DIRECTIONAL_EFFECT
        ),
        subject="fixture factor",
        predicate="affects",
        object_text="fixture outcome",
        direction=EffectDirection.INCREASE,
        condition_text="synthetic test condition",
    )

    saved = register_supported_assertion(
        db_session,
        assertion=assertion,
        supports=[
            EvidenceSupportCreate(
                source_id=source.id,
                locator="p. 12",
                support_note=(
                    "Synthetic provenance fixture only."
                ),
            )
        ],
    )

    assert saved.id is not None
    assert saved.direction == "increase"

    links = list(
        db_session.scalars(
            select(AssertionEvidence).where(
                AssertionEvidence.assertion_id
                == saved.id
            )
        )
    )

    assert len(links) == 1
    assert links[0].source_id == source.id
    assert links[0].locator == "p. 12"

    assertions = list(
        db_session.scalars(
            select(AgronomicAssertion)
        )
    )

    assert len(assertions) == 1