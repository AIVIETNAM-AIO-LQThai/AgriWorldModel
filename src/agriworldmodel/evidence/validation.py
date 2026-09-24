from sqlalchemy.orm import Session

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.evidence.schemas import EvidenceSupportCreate

class EvidenceValidationError(ValueError):
    pass

def validate_evidence_support(
    session: Session, supports: list[EvidenceSupportCreate],
) -> None:
    """
    Ensure an assertion has provenance and every referenced
    source actually exists.
    """
    if not supports:
        raise EvidenceValidationError("Agronomic assertions require at least one evidence source.")

    for support in supports:
        source = session.get(EvidenceSource, support.source_id)

        if source is None:
            raise EvidenceValidationError(
                f"Evidence source does not exist: {support.source_id}"
            )