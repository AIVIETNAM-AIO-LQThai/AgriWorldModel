import json
from pathlib import Path

from agriworldmodel.compiled_evidence.schemas import CompiledStudy


PATH = Path("research/evidence/dang_2025_durian.json")


def upsert_flag(payload: dict, flag: dict) -> None:
    payload["flags"] = [
        existing for existing in payload["flags"]
        if existing["record_id"] != flag["record_id"]
    ]

    payload["flags"].append(flag)


def main() -> None:
    payload = json.loads(
        PATH.read_text(encoding="utf-8")
    )

    # ---------------------------------------------------------------
    # Study design
    # ---------------------------------------------------------------
    payload["design"]["randomization_unit_status"] = "not_reported"

    # Do not infer "tree", "plot", or "replicate".
    payload["design"]["randomization_unit"] = None

    # ---------------------------------------------------------------
    # Intervention missingness
    # ---------------------------------------------------------------
    for intervention in payload["interventions"]:
        intervention_id = intervention["intervention_id"]

        if intervention_id in {
            "int-background-npk",
            "int-om",
        }:
            intervention["dose_status"] = "reported"

        elif intervention_id == "int-ff":
            intervention["dose_status"] = "not_reported"

    # ---------------------------------------------------------------
    # Outcome semantics
    # ---------------------------------------------------------------
    for outcome in payload["outcomes"]:
        outcome_id = outcome["outcome_id"]

        if outcome_id in {
            "outcome-leaf-k",
            "outcome-leaf-ca"
        }:
            outcome["measurement_time"] = (
                "Fruit harvesting period; "
                "leaf samples were collected "
                "simultaneously with soil sampling."
            )

            outcome["sampling_rule"] = (
                "Leaves were collected at the "
                "5th and 6th positions of the bud; "
                "six leaves were picked from each "
                "durian tree, yielding 24 leaves "
                "per replication as reported."
            )

        if outcome_id == "outcome-pd-rate":
            outcome["name"] = (
                "Physiological disorder percentage "
                "among flesh components of selected "
                "durian fruit"
            )

            outcome["measurement_time"] = (
                "Fruit harvesting period"
            )

            outcome["sampling_rule"] = (
                "Three durian fruits were randomly "
                "selected in each replicate for "
                "fruit-quality evaluation."
            )

            outcome["selection_rule"] = (
                "Selected fruits weighed 2.2-2.8 kg "
                "and had no physical damage due to "
                "pest infestation."
            )

            outcome[
                "post_treatment_selection"
            ] = True

            outcome["notes"] = (
                "PD percentage was calculated as "
                "the number of flesh components "
                "showing physiological disorder "
                "divided by the total number of "
                "flesh components in the selected "
                "fruit. This should not be read as "
                "an orchard-wide fruit-level "
                "incidence estimate."
            )

    # ---------------------------------------------------------------
    # Derived contrast semantics
    # ---------------------------------------------------------------
    for contrast in payload["contrasts"]:
        contrast["evidential_basis"] = (
            "randomized_within_block_arm_mean_comparison"
        )

        contrast["estimand_text"] = (
            "Difference in published intervention and control arm means within one orchard, season, and outcome stratum."
        )

        contrast["uncertainty_status"] = (
            "not_reconstructible_from_published_summaries"
        )

        contrast["uncertainty_text"] = (
            "The paper reports arm means and standard deviations, but the "
            "covariance/block-level information required to reconstruct uncertainty "
            "for this derived pairwise contrast is unavailable."
        )

        contrast["significance_text"] = None

        contrast["assumptions"] = [
            (
                "Published arm means correspond to the randomized treatment "
                "groups in this site-season stratum."
            ),
            (
                "This value is a deterministic arm-mean difference, not a "
                "reconstructed model-adjusted treatment effect."
            ),
            (
                "No standard error, confidence interval, or pairwise p-value is inferred."
            ),
        ]

    # ---------------------------------------------------------------
    # Explicit study limitations
    # ---------------------------------------------------------------
    upsert_flag(
        payload,
        {
            "record_id": "flag-randomization-unit-unclear",
            "flag_type": "randomization_unit_unclear",
            "detail": (
                "The article reports a randomized "
                "complete block design with three "
                "replicates and 12 trees per "
                "treatment, but does not explicitly "
                "identify the physical randomization "
                "unit. The compiler therefore does "
                "not infer tree, plot, or replicate "
                "as the randomization unit."
            ),
            "related_record_ids": [],
            "locator": "Section 4.3 Experimental Design",
        },
    )

    upsert_flag(
        payload,
        {
            "record_id": "flag-pd-post-treatment-selection",
            "flag_type": "post_treatment_selection",
            "detail": (
                "Fruit-quality and PD measurements "
                "were made on three randomly "
                "selected fruits per replicate "
                "restricted to 2.2-2.8 kg and no "
                "physical pest damage. Because this "
                "selection occurs after treatment, "
                "the PD estimand is narrower than "
                "orchard-wide fruit-level PD."
            ),
            "related_record_ids": ["outcome-pd-rate"],
            "locator": "Section 4.5 Evaluation of Fruit Yield and Quality Characteristics",
        },
    )

    payload["metadata"]["results_compiled"] = True

    payload["metadata"]["inference_semantics_refined"] = True

    # ---------------------------------------------------------------
    # Full validation BEFORE writing
    # ---------------------------------------------------------------
    study = CompiledStudy.model_validate(payload)

    PATH.write_text(
        json.dumps(
            study.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Refined Dang inferential semantics.")


if __name__ == "__main__":
    main()