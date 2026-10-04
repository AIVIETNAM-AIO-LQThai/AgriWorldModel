import json
from pathlib import Path

from agriworldmodel.compiled_evidence.schemas import CompiledStudy

PATH = Path("research/evidence/dang_2025_durian.json")

ARM_IDS = {
    "Control": "arm-control",
    "OM": "arm-om",
    "FF": "arm-ff",
    "OM+FF": "arm-om-ff",
}

OUTCOMES = {
    "yield": (
        "outcome-fruit-yield",
        "kg tree^-1",
    ),
    "bstar": (
        "outcome-aril-b-star",
        None,
    ),
    "tss": (
        "outcome-tss",
        "%",
    ),
    "pd": (
        "outcome-pd-rate",
        "%",
    ),
}


# Each cell:
#   (mean, standard deviation, significance group)
TABLE_4 = {
    # ===============================================================
    # D1
    # ===============================================================
    ("D1", "2022-2023"): {
        "Control": {
            "yield": (65.1, 1.35, "c"),
            "bstar": (38.8, 2.03, "c"),
            "tss": (27.3, 0.56, "c"),
            "pd": (12.6, 0.81, "a"),
        },
        "OM": {
            "yield": (70.6, 0.90, "b"),
            "bstar": (45.0, 1.46, "b"),
            "tss": (29.2, 0.30, "b"),
            "pd": (8.37, 0.42, "b"),
        },
        "FF": {
            "yield": (71.9, 2.31, "b"),
            "bstar": (47.2, 1.05, "b"),
            "tss": (29.2, 0.31, "b"),
            "pd": (8.53, 0.55, "b"),
        },
        "OM+FF": {
            "yield": (75.8, 1.07, "a"),
            "bstar": (63.2, 1.05, "a"),
            "tss": (31.3, 0.80, "a"),
            "pd": (1.83, 0.21, "c"),
        },
    },

    ("D1", "2023-2024"): {
        "Control": {
            "yield": (90.1, 1.39, "c"),
            "bstar": (42.3, 1.43, "c"),
            "tss": (26.9, 0.40, "c"),
            "pd": (12.9, 1.35, "a"),
        },
        "OM": {
            "yield": (94.2, 0.47, "b"),
            "bstar": (48.4, 0.75, "b"),
            "tss": (29.0, 0.46, "b"),
            "pd": (8.23, 0.31, "b"),
        },
        "FF": {
            "yield": (94.5, 0.55, "b"),
            "bstar": (49.5, 0.65, "b"),
            "tss": (29.2, 0.40, "b"),
            "pd": (8.77, 0.31, "b"),
        },
        "OM+FF": {
            "yield": (97.8, 0.25, "a"),
            "bstar": (59.8, 1.27, "a"),
            "tss": (30.6, 0.40, "a"),
            "pd": (1.93, 0.23, "c"),
        },
    },

    # ===============================================================
    # D2
    # ===============================================================
    ("D2", "2022-2023"): {
        "Control": {
            "yield": (67.3, 0.35, "c"),
            "bstar": (42.4, 0.82, "c"),
            "tss": (27.4, 0.56, "c"),
            "pd": (11.7, 0.86, "a"),
        },
        "OM": {
            "yield": (70.8, 0.46, "b"),
            "bstar": (49.2, 2.17, "b"),
            "tss": (29.1, 0.26, "b"),
            "pd": (8.40, 0.70, "b"),
        },
        "FF": {
            "yield": (70.3, 1.69, "b"),
            "bstar": (49.2, 1.23, "b"),
            "tss": (29.3, 0.67, "b"),
            "pd": (8.63, 0.70, "b"),
        },
        "OM+FF": {
            "yield": (76.1, 1.54, "a"),
            "bstar": (63.1, 0.85, "a"),
            "tss": (30.9, 0.35, "a"),
            "pd": (1.17, 0.83, "c"),
        },
    },

    ("D2", "2023-2024"): {
        "Control": {
            "yield": (89.5, 1.40, "c"),

            # The published table reports ±11.8.
            # Preserve it exactly for now.
            "bstar": (37.3, 11.8, "c"),

            "tss": (27.3, 0.32, "c"),
            "pd": (13.4, 1.20, "a"),
        },
        "OM": {
            "yield": (94.9, 0.31, "b"),
            "bstar": (50.8, 1.25, "b"),
            "tss": (28.8, 0.36, "b"),
            "pd": (8.60, 0.90, "b"),
        },
        "FF": {
            "yield": (95.3, 0.96, "b"),
            "bstar": (50.7, 1.22, "b"),
            "tss": (28.9, 0.47, "b"),
            "pd": (8.43, 0.61, "b"),
        },
        "OM+FF": {
            "yield": (98.1, 0.91, "a"),
            "bstar": (63.4, 0.95, "a"),
            "tss": (30.8, 0.25, "a"),
            "pd": (1.77, 0.21, "c"),
        },
    },

    # ===============================================================
    # D3
    # ===============================================================
    ("D3", "2022-2023"): {
        "Control": {
            "yield": (66.8, 1.72, "c"),
            "bstar": (42.1, 1.73, "c"),
            "tss": (26.9, 0.47, "c"),
            "pd": (14.2, 0.66, "a"),
        },
        "OM": {
            "yield": (71.0, 1.42, "b"),
            "bstar": (47.7, 1.16, "b"),
            "tss": (28.9, 0.30, "b"),
            "pd": (8.87, 0.35, "b"),
        },
        "FF": {
            "yield": (71.7, 1.65, "b"),
            "bstar": (50.2, 1.83, "b"),
            "tss": (28.8, 0.65, "b"),
            "pd": (8.57, 0.81, "b"),
        },
        "OM+FF": {
            "yield": (75.8, 1.24, "a"),
            "bstar": (59.0, 1.31, "a"),
            "tss": (30.6, 0.55, "a"),
            "pd": (2.20, 0.40, "c"),
        },
    },

    ("D3", "2023-2024"): {
        "Control": {
            "yield": (88.3, 1.56, "c"),
            "bstar": (43.4, 0.95, "c"),
            "tss": (27.8, 0.36, "c"),
            "pd": (14.4, 0.97, "a"),
        },
        "OM": {
            "yield": (93.3, 0.97, "b"),
            "bstar": (52.2, 1.15, "b"),
            "tss": (29.8, 0.31, "b"),
            "pd": (9.53, 0.72, "b"),
        },
        "FF": {
            "yield": (94.0, 0.79, "b"),
            "bstar": (52.9, 1.65, "b"),
            "tss": (30.2, 0.61, "b"),
            "pd": (9.53, 0.65, "b"),
        },
        "OM+FF": {
            "yield": (97.4, 1.43, "a"),
            "bstar": (63.9, 1.40, "a"),
            "tss": (31.9, 0.40, "a"),
            "pd": (2.23, 0.21, "c"),
        },
    },
}


P_VALUES = {
    ("D1", "2022-2023"): {
        "yield": "***",
        "bstar": "***",
        "tss": "***",
        "pd": "***",
    },
    ("D1", "2023-2024"): {
        "yield": "***",
        "bstar": "***",
        "tss": "***",
        "pd": "**",
    },

    ("D2", "2022-2023"): {
        "yield": "***",
        "bstar": "***",
        "tss": "***",
        "pd": "***",
    },
    ("D2", "2023-2024"): {
        "yield": "***",
        "bstar": "**",
        "tss": "***",
        "pd": "***",
    },

    ("D3", "2022-2023"): {
        "yield": "***",
        "bstar": "***",
        "tss": "**",
        "pd": "**",
    },
    ("D3", "2023-2024"): {
        "yield": "***",
        "bstar": "***",
        "tss": "**",
        "pd": "***",
    },
}


def make_record(
    *, site: str, season: str,
    treatment: str, outcome_key: str,
    value: float, sd: float, group: str,
) -> dict:
    outcome_id, unit = OUTCOMES[outcome_key]

    treatment_key = treatment.lower().replace("+", "-")

    record_id = (
        f"t4-{site.lower()}-{season}-{treatment_key}-{outcome_key}"
    )

    return {
        "record_id": record_id,
        "arm_id": ARM_IDS[treatment],
        "outcome_id": outcome_id,
        "value": value,
        "unit": unit,
        "dispersion_type": "standard_deviation",
        "dispersion_value": sd,
        "sample_size": 3,
        "significance_group": group,
        "comparison_significance": (
            P_VALUES[
                (site, season)
            ][outcome_key]
        ),
        "context": {
            "site": site,
            "season": season,
            "table": "Table 4",
        },
        "provenance": {
            "provenance_type": "author_result",
            "locator": (
                f"Table 4, {site}, {season}, {treatment}, {outcome_key}"
            ),
        },
    }


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))

    existing = [
        item
        for item in payload["arm_results"]
        if item["record_id"].startswith("t4-")
    ]

    if existing:
        raise RuntimeError("Table 4 records already exist.")

    records = []

    for (site, season), treatments in TABLE_4.items():

        for treatment, outcomes in treatments.items():

            for outcome_key, (value, sd, group) in outcomes.items():

                records.append(
                    make_record(
                        site=site,
                        season=season,
                        treatment=treatment,
                        outcome_key=outcome_key,
                        value=value,
                        sd=sd,
                        group=group,
                    )
                )

    assert len(records) == 96

    payload["arm_results"].extend(records)

    # Preserve the unusual value exactly as published.
    payload["flags"].append(
        {
            "record_id": (
                "flag-table4-d2-control-bstar-sd"
            ),
            "flag_type": "other",
            "detail": (
                "Table 4 reports the D2, "
                "2023-2024 Control b* value "
                "as 37.3 c ± 11.8. "
                "The SD is unusually large "
                "relative to neighboring cells. "
                "It is preserved exactly as "
                "published and not corrected."
            ),
            "related_record_ids": ["t4-d2-2023-2024-control-bstar"],
            "locator": "Table 4, D2, 2023-2024, Control, b*",
        }
    )

    compiled_tables = set(
        payload["metadata"].get(
            "compiled_tables",
            []
        )
    )

    compiled_tables.add("Table 4")

    payload["metadata"]["compiled_tables"] = sorted(compiled_tables)

    payload["metadata"]["compilation_scope"] = (
        "study design, sites, population, "
        "interventions, arms, outcome "
        "definitions, Table 1 soil chemistry, "
        "Table 2 leaf nutrients, and Table 4 "
        "fruit yield and quality results"
    )

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

    print(f"Compiled {len(records)} Table 4 records.")


if __name__ == "__main__":
    main()