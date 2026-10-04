import json

import pytest
from pydantic import ValidationError

from agriworldmodel.compiled_evidence.io import load_compiled_study
from agriworldmodel.compiled_evidence.schemas import CompiledStudy, Provenance, ProvenanceType


def minimal_study() -> dict:
    return {
        "study_id": "fixture-study",

        "source": {
            "source_key": "fixture-source",
            "title": "Synthetic Fixture Study",
            "year": 2026,
        },

        "design": {
            "design_type": "synthetic randomized trial",
            "provenance": {
                "provenance_type": "author_result",
                "locator": "p. 1",
            },
        },

        "population": {
            "crop": "durian",
            "cultivar": "Ri6",
            "provenance": {
                "provenance_type": "author_result",
                "locator": "p. 1",
            },
        },

        "interventions": [
            {
                "intervention_id": "int-om",
                "name": "Organic manure",
                "intervention_type": "soil amendment",
                "provenance": {
                    "provenance_type": "author_result",
                    "locator": "p. 4",
                },
            }
        ],

        "arms": [
            {
                "arm_id": "arm-control",
                "label": "Control",
                "is_control": True,
                "provenance": {
                    "provenance_type": "author_result",
                    "locator": "p. 4",
                },
            },
            {
                "arm_id": "arm-om",
                "label": "OM",
                "intervention_ids": [
                    "int-om"
                ],
                "provenance": {
                    "provenance_type": "author_result",
                    "locator": "p. 4",
                },
            },
        ],

        "outcomes": [
            {
                "outcome_id": "outcome-pd",
                "name": "Physiological disorder rate",
                "unit": "%",
                "provenance": {
                    "provenance_type": "author_result",
                    "locator": "p. 5",
                },
            }
        ],

        "arm_results": [
            {
                "record_id": "result-control-pd",
                "arm_id": "arm-control",
                "outcome_id": "outcome-pd",
                "value": 12.0,
                "unit": "%",
                "provenance": {
                    "provenance_type": "author_result",
                    "locator": "Table X, p. 5",
                },
            },
            {
                "record_id": "result-om-pd",
                "arm_id": "arm-om",
                "outcome_id": "outcome-pd",
                "value": 5.0,
                "unit": "%",
                "provenance": {
                    "provenance_type": "author_result",
                    "locator": "Table X, p. 5",
                },
            },
        ],

        "contrasts": [
            {
                "record_id": "contrast-om-pd",
                "intervention_arm_id": "arm-om",
                "comparator_arm_id": "arm-control",
                "outcome_id": "outcome-pd",
                "effect_type": "absolute_mean_difference",
                "effect_value": -7.0,
                "unit": "%",
                "evidential_basis": "randomized_within_block_arm_mean_comparison",
                "estimand_text": "Difference in published arm means within the fixture stratum.",
                "uncertainty_status": "not_reconstructible_from_published_summaries",
                "provenance": {
                    "provenance_type": "our_derived",
                    "source_record_ids": [
                        "result-om-pd",
                        "result-control-pd",
                    ],
                    "derivation": (
                        "result-om-pd.value - "
                        "result-control-pd.value"
                    ),
                },
            }
        ],
    }


def test_minimal_compiled_study_is_valid():
    study = CompiledStudy.model_validate(minimal_study())

    assert study.study_id == "fixture-study"
    assert len(study.arms) == 2
    assert len(study.contrasts) == 1

def test_author_result_requires_locator():
    with pytest.raises(ValidationError):
        Provenance(
            provenance_type=(ProvenanceType.AUTHOR_RESULT)
        )

def test_derived_record_requires_inputs():
    with pytest.raises(ValidationError):
        Provenance(
            provenance_type=(ProvenanceType.OUR_DERIVED),
            derivation="a - b",
        )

def test_unknown_arm_reference_is_rejected():
    payload = minimal_study()

    payload["arm_results"][0]["arm_id"] = (
        "missing-arm"
    )

    with pytest.raises(ValidationError):
        CompiledStudy.model_validate(payload)


def test_unknown_derived_input_is_rejected():
    payload = minimal_study()
    payload["contrasts"][0]["provenance"]["source_record_ids"] = ["nonexistent-result"]

    with pytest.raises(ValidationError):
        CompiledStudy.model_validate(payload)

def test_json_round_trip(tmp_path):
    payload = minimal_study()

    path = tmp_path / "compiled.json"
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    study = load_compiled_study(path)

    assert study.source.title == "Synthetic Fixture Study"
    assert study.contrasts[0].provenance.provenance_type == ProvenanceType.OUR_DERIVED

def test_derived_contrast_must_recompute_from_sources():
    payload = minimal_study()
    payload["contrasts"][0]["effect_value"] = -6.5
    with pytest.raises(
        ValidationError,
        match="does not recompute",
    ):
        CompiledStudy.model_validate(payload)


def test_derived_contrast_cannot_mix_source_arms():
    payload = minimal_study()

    payload["contrasts"][0]["provenance"]["source_record_ids"] = ["result-om-pd", "result-om-pd",]

    with pytest.raises(
        ValidationError,
        match="source arms",
    ):
        CompiledStudy.model_validate(payload)

def add_valid_comparison_family(payload: dict) -> None:
    # Comparison-family tests are intentionally
    # isolated from derived-contrast validation.
    payload["contrasts"] = []

    for result in payload["arm_results"]:
        result["context"] = {
            "table": "Table X",
            "site": "D1",
            "season": "2026",
        }

    payload["comparison_families"] = [
        {
            "record_id": "family-d1-2026-pd",
            "outcome_id": "outcome-pd",
            "member_arm_result_ids": [
                "result-control-pd",
                "result-om-pd",
            ],
            "reported_family_significance_marker": "*",
            "overall_test_method": None,
            "overall_test_method_status": "not_reported",
            "post_hoc_method": "Duncan post hoc test",
            "post_hoc_alpha": 0.05,
            "group_letters_by_arm": {
                "arm-control": "a",
                "arm-om": "b",
            },
            "group_letter_semantics": "Different letters indicate significant differences.",
            "context": {
                "table": "Table X",
                "site": "D1",
                "season": "2026",
            },
            "result_provenance": {
                "provenance_type": "author_result",
                "locator": "Table X",
            },
            "method_provenance": {
                "provenance_type": "author_method",
                "locator": "Methods: Data Analysis",
            },
        }
    ]

def test_valid_comparison_family():
    payload = minimal_study()

    add_valid_comparison_family(
        payload
    )

    study = CompiledStudy.model_validate(
        payload
    )

    assert (
        len(study.comparison_families)
        == 1
    )


def test_comparison_family_cannot_mix_strata():
    payload = minimal_study()

    add_valid_comparison_family(
        payload
    )

    payload["arm_results"][1][
        "context"
    ]["season"] = "2027"

    with pytest.raises(
        ValidationError,
        match="mixes season strata",
    ):
        CompiledStudy.model_validate(
            payload
        )


def test_comparison_family_letters_must_match_arms():
    payload = minimal_study()

    add_valid_comparison_family(payload)

    payload["comparison_families"][0]["group_letters_by_arm"] = {
        "arm-control": "a",
    }

    with pytest.raises(
        ValidationError,
        match="group letters",
    ):
        CompiledStudy.model_validate(payload)