from __future__ import annotations

import enum
import math
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

class ReportStatus(str, enum.Enum):
    REPORTED = "reported"
    NOT_REPORTED = "not_reported"
    NOT_COMPILED = "not_compiled"
    NOT_APPLICABLE = "not_applicable"
    INFERRED = "inferred"

class ContrastEvidentialBasis(str, enum.Enum):
    RANDOMIZED_WITHIN_BLOCK_ARM_MEAN_COMPARISON = "randomized_within_block_arm_mean_comparison"

class UncertaintyStatus(str, enum.Enum):
    AUTHOR_REPORTED = "author_reported"
    NOT_RECONSTRUCTIBLE_FROM_PUBLISHED_SUMMARIES = "not_reconstructible_from_published_summaries"
    NOT_APPLICABLE = "not_applicable"

class EvidenceFlagType(str, enum.Enum):
    REPORTED_INCONSISTENCY = "reported_inconsistency"
    ABSTRACT_TABLE_MISMATCH = "abstract_table_mismatch"
    UNVERIFIED_CITED_CLAIM = "unverified_cited_claim"
    MISSING_DOSE_INFORMATION = "missing_dose_information"
    MISSING_UNCERTAINTY = "missing_uncertainty"
    NOT_CAUSALLY_IDENTIFIED = "not_causally_identified"
    ECONOMIC_CLAIM_UNSUPPORTED = "economic_claim_unsupported"
    OTHER = "other"
    POST_TREATMENT_SELECTION = "post_treatment_selection"
    RANDOMIZATION_UNIT_UNCLEAR = "randomization_unit_unclear"


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
    randomization_unit_status: ReportStatus = ReportStatus.NOT_COMPILED

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

    dose_status: ReportStatus = ReportStatus.NOT_COMPILED
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

    sampling_rule: str | None = None
    selection_rule: str | None = None

    post_treatment_selection: bool | None = None

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

    evidential_basis: ContrastEvidentialBasis

    estimand_text: str = Field(min_length=1)

    uncertainty_status: UncertaintyStatus

    uncertainty_text: str | None = None
    significance_text: str | None = None

    assumptions: list[str] = Field(
        default_factory=list
    )

    context: dict[str, str] = Field(
        default_factory=dict
    )

    provenance: Provenance


class Association(BaseModel):
    record_id: str = Field(min_length=1)

    x: str = Field(min_length=1)
    y: str = Field(min_length=1)

    statistic: str = Field(min_length=1)
    value: float | None = None

    sample_size: int | None = Field(
        default=None, ge=1,
    )

    significance_text: str | None = None

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
            raise ValueError("Compiled-study identifiers must be globally unique.")

        for arm in self.arms:
            unknown = (
                set(arm.intervention_ids) - intervention_ids
            )

            if unknown:
                raise ValueError(f"Arm {arm.arm_id} references unknown interventions: {sorted(unknown)}")

        for result in self.arm_results:
            if result.arm_id not in arm_ids:
                raise ValueError(f"Result {result.record_id} references unknown arm {result.arm_id}.")

            if result.outcome_id not in outcome_ids:
                raise ValueError(f"Result {result.record_id} references unknown outcome {result.outcome_id}.")

        for contrast in self.contrasts:
            if contrast.intervention_arm_id not in arm_ids:
                raise ValueError(f"Contrast {contrast.record_id} references an unknown intervention arm.")

            if contrast.comparator_arm_id not in arm_ids:
                raise ValueError(f"Contrast {contrast.record_id} references an unknown comparator arm.")

            if contrast.outcome_id not in outcome_ids:
                raise ValueError(f"Contrast {contrast.record_id} references an unknown outcome.")

        result_by_id = {
            result.record_id: result
            for result in self.arm_results
        }

        for contrast in self.contrasts:
            if contrast.provenance.provenance_type != ProvenanceType.OUR_DERIVED:
                continue

            source_ids = contrast.provenance.source_record_ids

            if len(source_ids) != 2:
                raise ValueError(
                    f"Derived contrast "
                    f"{contrast.record_id} must have "
                    "exactly two source arm results."
                )

            try:
                source_results = [result_by_id[source_id] for source_id in source_ids]
            except KeyError as exc:
                raise ValueError(
                    f"Derived contrast "
                    f"{contrast.record_id} must derive "
                    "only from ArmResult records."
                ) from exc

            intervention_matches = [
                result for result in source_results
                if result.arm_id == contrast.intervention_arm_id
            ]

            comparator_matches = [
                result for result in source_results
                if result.arm_id == contrast.comparator_arm_id
            ]

            if (
                len(intervention_matches) != 1
                or len(comparator_matches) != 1
            ):
                raise ValueError(
                    f"Derived contrast "
                    f"{contrast.record_id} source arms "
                    "do not match the declared comparison."
                )

            intervention_result = intervention_matches[0]
            comparator_result = comparator_matches[0]

            if (
                intervention_result.outcome_id != contrast.outcome_id
                or comparator_result.outcome_id
                != contrast.outcome_id
            ):
                raise ValueError(f"Derived contrast {contrast.record_id} mixes outcomes.")

            if (
                intervention_result.unit != comparator_result.unit
                or contrast.unit != intervention_result.unit
            ):
                raise ValueError(
                    f"Derived contrast {contrast.record_id} mixes units."
                )

            for key in ("table", "site", "season"):
                intervention_value = intervention_result.context.get(key)
                comparator_value = comparator_result.context.get(key)
                contrast_value = contrast.context.get(key)

                if (
                    intervention_value != comparator_value
                    or intervention_value != contrast_value
                ):
                    raise ValueError(
                        f"Derived contrast "
                        f"{contrast.record_id} mixes "
                        f"context for {key}."
                    )

            if (
                contrast.effect_type == "absolute_mean_difference"
                and intervention_result.value is not None
                and comparator_result.value is not None
            ):
                expected = intervention_result.value - comparator_result.value

                if contrast.effect_value is None:
                    raise ValueError(
                        f"Derived contrast "
                        f"{contrast.record_id} has "
                        "no effect value."
                    )

                if not math.isclose(
                    contrast.effect_value,
                    expected,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                ):
                    raise ValueError(
                        f"Derived contrast "
                        f"{contrast.record_id} does not "
                        "recompute from its source records."
                    )

        for collection in [
            self.interpretations,
            self.recommendations,
            self.flags,
        ]:
            for item in collection:
                unknown = set(item.related_record_ids) - all_ids

                if unknown:
                    raise ValueError(f"{item.record_id} references unknown records: {sorted(unknown)}")

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
                    raise ValueError(f"{item.record_id} derives from unknown records: {sorted(unknown)}")

        return self