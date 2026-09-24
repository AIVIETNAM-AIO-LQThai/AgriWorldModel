from sqlalchemy.orm import Session

from agriworldmodel.db.models.agronomic_assertion import AgronomicAssertion
from agriworldmodel.db.models.assertion_evidence import AssertionEvidence
from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.evidence.schemas import (
    AgronomicAssertionCreate, EvidenceSourceCreate, EvidenceSupportCreate,
)
from agriworldmodel.evidence.validation import validate_evidence_support

def register_evidence_source(
    session: Session, source: EvidenceSourceCreate,
) -> EvidenceSource:
    db_source = EvidenceSource(
        source_type=source.source_type.value,
        title=source.title,
        publisher=source.publisher,
        published_year=source.published_year,
        url=source.url,
        language=source.language,
        jurisdiction=source.jurisdiction,
        source_metadata=source.source_metadata,
    )

    session.add(db_source)
    session.flush()

    return db_source

def register_supported_assertion(
    session: Session, *,
    assertion: AgronomicAssertionCreate,
    supports: list[EvidenceSupportCreate],
) -> AgronomicAssertion:
    """
    Register one atomic agronomic assertion together with
    at least one provenance link.
    """
    validate_evidence_support(session, supports)

    db_assertion = AgronomicAssertion(
        assertion_type=assertion.assertion_type.value,
        subject=assertion.subject,
        predicate=assertion.predicate,
        object_text=assertion.object_text,
        direction=(
            assertion.direction.value
            if assertion.direction is not None
            else None
        ),
        condition_text=assertion.condition_text,
        crop=assertion.crop,
    )

    session.add(db_assertion)
    session.flush()

    for support in supports:
        link = AssertionEvidence(
            assertion_id=db_assertion.id,
            source_id=support.source_id,
            locator=support.locator,
            support_note=support.support_note,
        )
        session.add(link)

    session.flush()

    return db_assertion