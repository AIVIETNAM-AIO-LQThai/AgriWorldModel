import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from agriworldmodel.db.models.agronomic_assertion import AgronomicAssertion
from agriworldmodel.db.models.assertion_evidence import AssertionEvidence
from agriworldmodel.db.models.evidence_source import EvidenceSource

class EvidenceLookupError(ValueError):
    pass

class EvidenceCitation(BaseModel):
    source_id: uuid.UUID
    source_type: str
    title: str

    publisher: str | None = None
    published_year: int | None = None
    url: str | None = None

    locator: str
    support_note: str | None = None

class AssertionProvenance(BaseModel):
    assertion_id: uuid.UUID
    assertion_type: str

    subject: str
    predicate: str
    object_text: str

    citations: list[EvidenceCitation]

def get_assertion_provenance(
    session: Session, assertion_id: uuid.UUID
) -> AssertionProvenance:
    assertion = session.get(AgronomicAssertion, assertion_id)

    if assertion is None:
        raise EvidenceLookupError("Agronomic assertion does not exist.")

    stmt = (
        select(
            AssertionEvidence, EvidenceSource
        )
        .join(
            EvidenceSource,
            AssertionEvidence.source_id == EvidenceSource.id,
        )
        .where(
            AssertionEvidence.assertion_id == assertion.id
        )
        .order_by(
            EvidenceSource.title.asc(),
            AssertionEvidence.locator.asc(),
        )
    )

    rows = session.execute(stmt).all()

    if not rows:
        raise EvidenceLookupError("Agronomic assertion has no provenance.")

    citations = [
        EvidenceCitation(
            source_id=source.id,
            source_type=source.source_type,
            title=source.title,
            publisher=source.publisher,
            published_year=source.published_year,
            url=source.url,
            locator=link.locator,
            support_note=link.support_note,
        )
        for link, source in rows
    ]

    return AssertionProvenance(
        assertion_id=assertion.id,
        assertion_type=assertion.assertion_type,
        subject=assertion.subject,
        predicate=assertion.predicate,
        object_text=assertion.object_text,
        citations=citations,
    )