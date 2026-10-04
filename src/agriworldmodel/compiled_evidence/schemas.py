from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# -------------------------------------------------------------------
# Epistemic provenance
# -------------------------------------------------------------------
class ProvenanceType(str, enum.Enum):
    AUTHOR_METHOD = "author_method"
    AUTHOR_RESULT = "author_result"
    AUTHOR_INTERPRETATION = "author_interpretation"
    AUTHOR_RECOMMENDATION = "author_recommendation"
    EXTERNAL_CITED_CLAIM = "external_cited_claim"
    OUR_DERIVED = "our_derived"
    UNKNOWN = "unknown"

class EvidenceFlagType(str, enum.Enum):
    REPORTED_INCONSISTENCY = "reported_inconsistency"
    ABSTRACT_TABLE_MISMATCH = "abstract_table_mismatch"
    UNVERIFIED_CITED_CLAIM = "unverified_cited_claim"
    MISSING_DOSE_INFORMATION = "missing_dose_information"
    MISSING_UNCERTAINTY = "missing_uncertainty"
    NOT_CAUSALLY_IDENTIFIED = "not_causally_identified"
    ECONOMIC_CLAIM_UNSUPPORTED = "economic_claim_unsupported"
    OTHER = "other"


class Provenance(BaseModel):
    provenance_type: ProvenanceType

    # Exact location in the source document.
    # Examples:
    #   "p. 6"
    #   "Table 4, p. 6"
    #   "Section 3.2, p. 8"
    locator: str | None = None

    # Required for OUR_DERIVED records.
    source_record_ids: list[str] = Field(default_factory=list)

    # Human-readable deterministic derivation.
    # Example:
    #   "control_pd - omff_pd"
    derivation: str | None = None

    # Used when the paper itself cites another source for the claim.
    cited_reference: str | None = None

    notes: str | None = None

    @model_validator(mode="after")
    def validate_provenance(self):
        source_bound = {
            ProvenanceType.AUTHOR_METHOD,
            ProvenanceType.AUTHOR_RESULT,
            ProvenanceType.AUTHOR_INTERPRETATION,
            ProvenanceType.AUTHOR_RECOMMENDATION,
            ProvenanceType.EXTERNAL_CITED_CLAIM,
        }

        if (
            self.provenance_type in source_bound
            and not self.locator
        ):
            raise ValueError(
                "Source-derived evidence requires an exact locator."
            )

        if self.provenance_type == ProvenanceType.OUR_DERIVED:
            if not self.derivation:
                raise ValueError(
                    "OUR_DERIVED evidence requires a derivation."
                )

            if not self.source_record_ids:
                raise ValueError(
                    "OUR_DERIVED evidence requires source_record_ids."
                )

        if (
            self.provenance_type == ProvenanceType.EXTERNAL_CITED_CLAIM
            and not self.cited_reference
        ):
            raise ValueError(
                "External cited claims require cited_reference."
            )

        return self


# -------------------------------------------------------------------
# Bibliographic source
# -------------------------------------------------------------------
class CompiledSource(BaseModel):
    source_key: str = Field(min_length=1)

    title: str = Field(min_length=1)
    year: int | None = None

    doi: str | None = None
    citation: str | None = None

    provenance_note: str | None = None


# -------------------------------------------------------------------
# Study structure
# -------------------------------------------------------------------
class StudyDesign(BaseModel):
    design_type: str = Field(min_length=1)

    randomization_unit: str | None = None
    blocking: str | None = None
    seasons: list[str] = Field(default_factory=list)

    notes: str | None = None

    provenance: Provenance


class StudySite(BaseModel):
    site_id: str = Field(min_length=1)
    name: str | None = None
    region: str | None = None
    country: str | None = None
    notes: str | None = None
    provenance: Provenance
    latitude: float | None = None
    longitude: float | None = None


class StudyPopulation(BaseModel):
    crop: str = Field(min_length=1)

    cultivar: str | None = None

    tree_age_years_min: float | None = None
    tree_age_years_max: float | None = None

    spacing: str | None = None

    notes: str | None = None

    provenance: Provenance


# -------------------------------------------------------------------
# Intervention structure
# -------------------------------------------------------------------
class InterventionProtocol(BaseModel):
    intervention_id: str = Field(min_length=1)

    name: str = Field(min_length=1)
    intervention_type: str = Field(min_length=1)

    product_name: str | None = None
    composition_text: str | None = None

    dose_text: str | None = None
    dose_value: float | None = None
    dose_unit: str | None = None
    dose_basis: str | None = None

    application_mode: str | None = None
    timing_text: str | None = None
    frequency_text: str | None = None

    notes: str | None = None

    provenance: Provenance


class StudyArm(BaseModel):
    arm_id: str = Field(min_length=1)
    label: str = Field(min_length=1)

    intervention_ids: list[str] = Field(default_factory=list)

    is_control: bool = False

    notes: str | None = None

    provenance: Provenance


# -------------------------------------------------------------------
# Outcomes
# -------------------------------------------------------------------
class OutcomeDefinition(BaseModel):
    outcome_id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    unit: str | None = None
    measurement_method: str | None = None
    measurement_time: str | None = None

    notes: str | None = None

    provenance: Provenance


class ArmResult(BaseModel):
    record_id: str = Field(min_length=1)

    arm_id: str = Field(min_length=1)
    outcome_id: str = Field(min_length=1)

    value: float | None = None
    unit: str | None = None

    dispersion_type: str | None = None
    dispersion_value: float | None = None

    sample_size: int | None = Field(default=None, ge=1)
    significance_group: str | None = None

    # Statistical comparison reported for the site/season/outcome.
    # Examples: "*", "**", "***", "ns"
    comparison_significance: str | None = None

    # Example:
    # {
    #   "site": "D1",
    #   "season": "2024"
    # }
    context: dict[str, str] = Field(default_factory=dict)

    provenance: Provenance


# -------------------------------------------------------------------
# Comparisons / effects
# -------------------------------------------------------------------
class Contrast(BaseModel):
    record_id: str = Field(min_length=1)

    intervention_arm_id: str = Field(min_length=1)
    comparator_arm_id: str = Field(min_length=1)

    outcome_id: str = Field(min_length=1)

    effect_type: str = Field(min_length=1)

    effect_value: float | None = None
    unit: str | None = None

    uncertainty_text: str | None = None
    significance_text: str | None = None

    context: dict[str, str] = Field(default_factory=dict)

    provenance: Provenance


class Association(BaseModel):
    record_id: str = Field(min_length=1)

    x: str = Field(min_length=1)
    y: str = Field(min_length=1)

    statistic: str = Field(min_length=1)
    value: float | None = None

    sample_size: int | None = Field(
        default=None,
        ge=1,
    )

    context: dict[str, str] = Field(default_factory=dict)

    provenance: Provenance


# -------------------------------------------------------------------
# Narrative scientific objects
# -------------------------------------------------------------------
class Interpretation(BaseModel):
    record_id: str = Field(min_length=1)

    statement: str = Field(min_length=1)

    related_record_ids: list[str] = Field(default_factory=list)

    provenance: Provenance


class Recommendation(BaseModel):
    record_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    scope: str | None = None
    related_record_ids: list[str] = Field(default_factory=list)
    provenance: Provenance


class EvidenceFlag(BaseModel):
    record_id: str = Field(min_length=1)
    flag_type: EvidenceFlagType
    detail: str = Field(min_length=1)
    related_record_ids: list[str] = Field(default_factory=list)
    locator: str | None = None


# -------------------------------------------------------------------
# Complete compiled study
# -------------------------------------------------------------------
class CompiledStudy(BaseModel):
    schema_version: str = "compiled-study-1"

    study_id: str = Field(min_length=1)

    source: CompiledSource
    design: StudyDesign

    sites: list[StudySite] = Field(default_factory=list)

    population: StudyPopulation

    interventions: list[InterventionProtocol] = Field(default_factory=list)

    arms: list[StudyArm] = Field(default_factory=list)

    outcomes: list[OutcomeDefinition] = Field(default_factory=list)

    arm_results: list[ArmResult] = Field(default_factory=list)

    contrasts: list[Contrast] = Field(default_factory=list)

    associations: list[Association] = Field(default_factory=list)

    interpretations: list[Interpretation] = Field(default_factory=list)

    recommendations: list[Recommendation] = Field(default_factory=list)

    flags: list[EvidenceFlag] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self):
        intervention_ids = {
            item.intervention_id for item in self.interventions
        }

        arm_ids = {
            item.arm_id for item in self.arms
        }

        outcome_ids = {
            item.outcome_id for item in self.outcomes
        }

        record_ids = (
            {
                item.record_id for item in self.arm_results
            }
            | {
                item.record_id for item in self.contrasts
            }
            | {
                item.record_id for item in self.associations
            }
            | {
                item.record_id for item in self.interpretations
            }
            | {
                item.record_id for item in self.recommendations
            }
            | {
                item.record_id for item in self.flags
            }
        )

        all_ids = (
            intervention_ids
            | arm_ids
            | outcome_ids
            | record_ids
        )

        expected_count = (
            len(self.interventions)
            + len(self.arms)
            + len(self.outcomes)
            + len(self.arm_results)
            + len(self.contrasts)
            + len(self.associations)
            + len(self.interpretations)
            + len(self.recommendations)
            + len(self.flags)
        )

        if len(all_ids) != expected_count:
            raise ValueError(
                "Compiled-study identifiers must be globally unique."
            )

        for arm in self.arms:
            unknown = (
                set(arm.intervention_ids) - intervention_ids
            )

            if unknown:
                raise ValueError(
                    f"Arm {arm.arm_id} references unknown interventions: {sorted(unknown)}"
                )

        for result in self.arm_results:
            if result.arm_id not in arm_ids:
                raise ValueError(
                    f"Result {result.record_id} references unknown arm {result.arm_id}."
                )

            if result.outcome_id not in outcome_ids:
                raise ValueError(
                    f"Result {result.record_id} references unknown outcome {result.outcome_id}."
                )

        for contrast in self.contrasts:
            if contrast.intervention_arm_id not in arm_ids:
                raise ValueError(
                    f"Contrast {contrast.record_id} references "
                    "an unknown intervention arm."
                )

            if contrast.comparator_arm_id not in arm_ids:
                raise ValueError(
                    f"Contrast {contrast.record_id} references "
                    "an unknown comparator arm."
                )

            if contrast.outcome_id not in outcome_ids:
                raise ValueError(
                    f"Contrast {contrast.record_id} references an unknown outcome."
                )

        for collection in [
            self.interpretations,
            self.recommendations,
            self.flags,
        ]:
            for item in collection:
                unknown = set(item.related_record_ids) - all_ids

                if unknown:
                    raise ValueError(
                        f"{item.record_id} references unknown records: {sorted(unknown)}"
                    )

        # OUR_DERIVED records must also point to real records.
        provenance_holders = [
            *self.arm_results,
            *self.contrasts,
            *self.associations,
            *self.interpretations,
            *self.recommendations,
        ]

        for item in provenance_holders:
            provenance = item.provenance

            if provenance.provenance_type == ProvenanceType.OUR_DERIVED:
                unknown = set(provenance.source_record_ids) - all_ids

                if unknown:
                    raise ValueError(
                        f"{item.record_id} derives from unknown records: {sorted(unknown)}"
                    )

        return self