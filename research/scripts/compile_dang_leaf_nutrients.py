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

OUTCOME_IDS = {
    "K": "outcome-leaf-k",
    "Ca": "outcome-leaf-ca",
}

# site, season, treatment, nutrient,
# mean, SD, significance group
TABLE_2 = [
    # ---------------------------------------------------------------
    # D1
    # ---------------------------------------------------------------
    ("D1", "2022-2023", "Control", "K", 11.2, 0.30, "c"),
    ("D1", "2022-2023", "Control", "Ca", 15.9, 0.35, "c"),
    ("D1", "2023-2024", "Control", "K", 11.9, 0.35, "c"),
    ("D1", "2023-2024", "Control", "Ca", 16.1, 0.56, "c"),

    # The source prints the K SD as "035".
    # Leave it unresolved instead of silently assuming 0.35.
    ("D1", "2022-2023", "OM", "K", 13.9, None, "b"),
    ("D1", "2022-2023", "OM", "Ca", 17.8, 0.95, "b"),
    ("D1", "2023-2024", "OM", "K", 14.1, 0.46, "b"),
    ("D1", "2023-2024", "OM", "Ca", 18.4, 0.42, "b"),

    ("D1", "2022-2023", "FF", "K", 13.6, 0.21, "b"),
    ("D1", "2022-2023", "FF", "Ca", 18.4, 0.62, "b"),
    ("D1", "2023-2024", "FF", "K", 14.6, 0.49, "b"),
    ("D1", "2023-2024", "FF", "Ca", 18.9, 0.25, "b"),

    ("D1", "2022-2023", "OM+FF", "K", 15.8, 0.36, "a"),
    ("D1", "2022-2023", "OM+FF", "Ca", 20.5, 0.87, "a"),
    ("D1", "2023-2024", "OM+FF", "K", 16.9, 0.67, "a"),
    ("D1", "2023-2024", "OM+FF", "Ca", 20.4, 0.70, "a"),

    # ---------------------------------------------------------------
    # D2
    # ---------------------------------------------------------------
    ("D2", "2022-2023", "Control", "K", 12.2, 0.30, "c"),
    ("D2", "2022-2023", "Control", "Ca", 15.5, 0.60, "c"),
    ("D2", "2023-2024", "Control", "K", 12.1, 0.57, "c"),
    ("D2", "2023-2024", "Control", "Ca", 14.9, 0.35, "c"),

    ("D2", "2022-2023", "OM", "K", 15.5, 0.31, "b"),
    ("D2", "2022-2023", "OM", "Ca", 18.0, 0.44, "b"),
    ("D2", "2023-2024", "OM", "K", 14.8, 0.42, "b"),
    ("D2", "2023-2024", "OM", "Ca", 17.2, 0.50, "b"),

    ("D2", "2022-2023", "FF", "K", 15.8, 0.31, "b"),
    ("D2", "2022-2023", "FF", "Ca", 18.2, 0.80, "b"),
    ("D2", "2023-2024", "FF", "K", 15.0, 0.21, "b"),
    ("D2", "2023-2024", "FF", "Ca", 17.4, 0.61, "b"),

    ("D2", "2022-2023", "OM+FF", "K", 16.9, 0.75, "a"),
    ("D2", "2022-2023", "OM+FF", "Ca", 20.9, 0.36, "a"),
    ("D2", "2023-2024", "OM+FF", "K", 17.9, 0.20, "a"),
    ("D2", "2023-2024", "OM+FF", "Ca", 19.9, 0.35, "a"),

    # ---------------------------------------------------------------
    # D3
    # ---------------------------------------------------------------
    ("D3", "2022-2023", "Control", "K", 11.5, 0.55, "c"),
    ("D3", "2022-2023", "Control", "Ca", 14.9, 0.30, "c"),
    ("D3", "2023-2024", "Control", "K", 11.6, 0.56, "c"),
    ("D3", "2023-2024", "Control", "Ca", 14.2, 0.31, "c"),

    ("D3", "2022-2023", "OM", "K", 15.0, 0.62, "b"),
    ("D3", "2022-2023", "OM", "Ca", 16.7, 0.46, "b"),
    ("D3", "2023-2024", "OM", "K", 15.2, 0.30, "b"),
    ("D3", "2023-2024", "OM", "Ca", 16.1, 0.46, "b"),

    ("D3", "2022-2023", "FF", "K", 15.4, 0.60, "b"),
    ("D3", "2022-2023", "FF", "Ca", 16.3, 0.55, "b"),
    ("D3", "2023-2024", "FF", "K", 15.6, 0.61, "b"),
    ("D3", "2023-2024", "FF", "Ca", 16.1, 0.20, "b"),

    ("D3", "2022-2023", "OM+FF", "K", 17.6, 0.40, "a"),
    ("D3", "2022-2023", "OM+FF", "Ca", 19.7, 0.47, "a"),
    ("D3", "2023-2024", "OM+FF", "K", 17.8, 0.42, "a"),
    ("D3", "2023-2024", "OM+FF", "Ca", 19.9, 0.67, "a"),
]


def make_record(
    site: str, season: str,
    treatment: str, nutrient: str,
    value: float, sd: float | None,
    group: str,
) -> dict:
    treatment_key = treatment.lower().replace("+", "-")

    record_id = f"t2-{site.lower()}-{season}-{treatment_key}-{nutrient.lower()}"

    return {
        "record_id": record_id,
        "arm_id": ARM_IDS[treatment],
        "outcome_id": OUTCOME_IDS[nutrient],
        "value": value,
        "unit": "g kg^-1",
        "dispersion_type": "standard_deviation" if sd is not None else None,
        "dispersion_value": sd,
        "sample_size": 3,
        "significance_group": group,
        "comparison_significance": "***",
        "context": {
            "site": site,
            "season": season,
            "table": "Table 2",
        },
        "provenance": {
            "provenance_type": "author_result",
            "locator": f"Table 2, {site}, {season}, {treatment}, {nutrient}",
        },
    }


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))

    # This script should not silently append duplicates.
    existing_table2 = [
        item for item in payload["arm_results"]
        if item["record_id"].startswith("t2-")
    ]

    if existing_table2:
        raise RuntimeError("Table 2 records already exist.")

    records = [make_record(*row) for row in TABLE_2]

    assert len(records) == 48

    payload["arm_results"].extend(records)

    payload["flags"].append(
        {
            "record_id": "flag-table2-d1-om-k-sd",
            "flag_type": "reported_inconsistency",
            "detail": (
                "Table 2 reports the D1, 2022-2023, "
                "OM leaf-K cell as '13.9 b ± 035'. "
                "The decimal point in the reported SD is "
                "ambiguous, so dispersion_value is left "
                "unresolved rather than silently corrected."
            ),
            "related_record_ids": ["t2-d1-2022-2023-om-k"],
            "locator": "Table 2, D1, 2022-2023, OM, K",
        }
    )

    payload["metadata"]["compiled_tables"] = ["Table 2"]

    payload["metadata"]["compilation_scope"] = (
        "study design, sites, population, "
        "interventions, arms, outcome definitions, "
        "and Table 2 leaf K/Ca results"
    )

    # Validate before modifying the canonical artifact.
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

    print(f"Compiled {len(records)} Table 2 records.")


if __name__ == "__main__":
    main()