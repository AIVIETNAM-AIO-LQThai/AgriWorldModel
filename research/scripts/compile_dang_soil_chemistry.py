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
    "ph": (
        "outcome-soil-ph",
        "pH",
    ),
    "soc": (
        "outcome-soc",
        "g C kg^-1",
    ),
    "ap": (
        "outcome-available-p",
        "mg P kg^-1",
    ),
    "k": (
        "outcome-soil-exchangeable-k",
        "cmolc 100 g^-1",
    ),
    "ca": (
        "outcome-soil-exchangeable-ca",
        "cmolc 100 g^-1",
    ),
}

# Each cell is:
#   (mean, SD, significance_group)
#
# Significance for the treatment comparison is stored separately
# in P_VALUES below.
TABLE_1 = {
    ("D1", "2022-2023"): {
        "Control": {
            "ph": (4.75, 0.08, "b"),
            "soc": (20.3, 0.85, "b"),
            "ap": (22.5, 0.62, "b"),
            "k": (0.50, 0.02, "b"),
            "ca": (4.79, 0.06, "b"),
        },
        "OM": {
            "ph": (5.04, 0.11, "a"),
            "soc": (23.9, 0.70, "a"),
            "ap": (26.7, 0.46, "a"),
            "k": (0.60, 0.02, "a"),
            "ca": (5.19, 0.04, "a"),
        },
        "FF": {
            "ph": (4.77, 0.08, "b"),
            "soc": (20.2, 0.35, "b"),
            "ap": (22.3, 0.40, "b"),
            "k": (0.52, 0.03, "b"),
            "ca": (4.76, 0.07, "b"),
        },
        "OM+FF": {
            "ph": (5.06, 0.06, "a"),
            "soc": (24.3, 0.42, "a"),
            "ap": (26.3, 0.56, "a"),
            "k": (0.62, 0.03, "a"),
            "ca": (5.26, 0.06, "a"),
        },
    },

    ("D1", "2023-2024"): {
        "Control": {
            "ph": (4.95, 0.07, "b"),
            "soc": (19.2, 0.32, "b"),
            "ap": (22.7, 0.38, "b"),
            "k": (0.52, 0.02, "b"),
            "ca": (4.75, 0.09, "b"),
        },
        "OM": {
            "ph": (5.13, 0.10, "a"),
            "soc": (23.9, 0.65, "a"),
            "ap": (26.4, 0.42, "a"),
            "k": (0.62, 0.03, "a"),
            "ca": (5.22, 0.09, "a"),
        },
        "FF": {
            "ph": (4.88, 0.09, "b"),
            "soc": (19.7, 0.32, "b"),
            "ap": (22.6, 0.55, "b"),
            "k": (0.54, 0.04, "b"),
            "ca": (4.78, 0.09, "b"),
        },
        "OM+FF": {
            "ph": (5.17, 0.03, "a"),
            "soc": (24.8, 0.74, "a"),
            "ap": (26.0, 0.47, "a"),
            "k": (0.63, 0.04, "a"),
            "ca": (5.25, 0.06, "a"),
        },
    },

    ("D2", "2022-2023"): {
        "Control": {
            "ph": (4.69, 0.08, "b"),
            "soc": (20.3, 0.46, "b"),
            "ap": (19.5, 1.05, "b"),
            "k": (0.64, 0.02, "b"),
            "ca": (4.91, 0.05, "b"),
        },
        "OM": {
            "ph": (5.03, 0.08, "a"),
            "soc": (23.9, 0.65, "a"),
            "ap": (24.6, 0.67, "a"),
            "k": (0.70, 0.02, "a"),
            "ca": (5.37, 0.04, "a"),
        },
        "FF": {
            "ph": (4.74, 0.08, "b"),
            "soc": (20.1, 0.65, "b"),
            "ap": (19.9, 0.65, "b"),
            "k": (0.65, 0.02, "b"),
            "ca": (4.95, 0.08, "b"),
        },
        "OM+FF": {
            "ph": (5.07, 0.05, "a"),
            "soc": (24.1, 0.47, "a"),
            "ap": (24.8, 0.42, "a"),
            "k": (0.72, 0.02, "a"),
            "ca": (5.45, 0.07, "a"),
        },
    },

    ("D2", "2023-2024"): {
        "Control": {
            "ph": (4.81, 0.07, "b"),
            "soc": (20.6, 0.53, "b"),
            "ap": (20.6, 0.46, "b"),
            "k": (0.62, 0.02, "b"),
            "ca": (4.98, 0.06, "b"),
        },
        "OM": {
            "ph": (5.12, 0.05, "a"),
            "soc": (24.9, 0.35, "a"),
            "ap": (25.8, 0.61, "a"),
            "k": (0.71, 0.03, "a"),
            "ca": (5.47, 0.13, "a"),
        },
        "FF": {
            "ph": (4.87, 0.05, "b"),
            "soc": (20.7, 0.60, "b"),
            "ap": (20.8, 0.32, "b"),
            "k": (0.62, 0.03, "b"),
            "ca": (4.94, 0.07, "b"),
        },
        "OM+FF": {
            "ph": (5.16, 0.06, "a"),
            "soc": (25.0, 0.56, "a"),
            "ap": (26.1, 0.35, "a"),
            "k": (0.73, 0.02, "a"),
            "ca": (5.44, 0.07, "a"),
        },
    },

    ("D3", "2022-2023"): {
        "Control": {
            "ph": (5.00, 0.05, "b"),
            "soc": (20.3, 0.57, "b"),
            "ap": (24.4, 0.60, "b"),
            "k": (0.58, 0.03, "b"),
            "ca": (5.21, 0.11, "b"),
        },
        "OM": {
            "ph": (5.19, 0.03, "a"),
            "soc": (24.7, 0.80, "a"),
            "ap": (27.8, 0.31, "a"),
            "k": (0.68, 0.03, "a"),
            "ca": (5.62, 0.03, "a"),
        },
        "FF": {
            "ph": (5.00, 0.06, "b"),
            "soc": (20.6, 0.36, "b"),
            "ap": (24.7, 0.36, "b"),
            "k": (0.59, 0.01, "b"),
            "ca": (5.23, 0.07, "b"),
        },
        "OM+FF": {
            "ph": (5.18, 0.05, "a"),
            "soc": (25.2, 0.78, "a"),
            "ap": (28.6, 0.40, "a"),
            "k": (0.68, 0.03, "a"),
            "ca": (5.63, 0.05, "a"),
        },
    },

    ("D3", "2023-2024"): {
        "Control": {
            "ph": (4.97, 0.04, "b"),
            "soc": (19.5, 0.56, "b"),
            "ap": (23.9, 0.64, "b"),
            "k": (0.59, 0.03, "b"),
            "ca": (5.30, 0.09, "b"),
        },
        "OM": {
            "ph": (5.15, 0.03, "a"),
            "soc": (24.3, 0.40, "a"),
            "ap": (27.2, 0.30, "a"),
            "k": (0.68, 0.03, "a"),
            "ca": (5.66, 0.05, "a"),
        },
        "FF": {
            "ph": (5.00, 0.04, "b"),
            "soc": (19.9, 0.47, "b"),
            "ap": (23.7, 0.40, "b"),
            "k": (0.58, 0.03, "b"),
            "ca": (5.27, 0.05, "b"),
        },
        "OM+FF": {
            "ph": (5.17, 0.03, "a"),
            "soc": (24.7, 0.60, "a"),
            "ap": (27.5, 0.85, "a"),
            "k": (0.71, 0.02, "a"),
            "ca": (5.60, 0.13, "a"),
        },
    },
}


P_VALUES = {
    ("D1", "2022-2023"): {
        "ph": "**",
        "soc": "***",
        "ap": "***",
        "k": "**",
        "ca": "***",
    },
    ("D1", "2023-2024"): {
        "ph": "***",
        "soc": "***",
        "ap": "***",
        "k": "*",
        "ca": "***",
    },
    ("D2", "2022-2023"): {
        "ph": "***",
        "soc": "***",
        "ap": "***",
        "k": "***",
        "ca": "***",
    },
    ("D2", "2023-2024"): {
        "ph": "**",
        "soc": "***",
        "ap": "***",
        "k": "**",
        "ca": "***",
    },
    ("D3", "2022-2023"): {
        "ph": "**",
        "soc": "***",
        "ap": "***",
        "k": "**",
        "ca": "***",
    },
    ("D3", "2023-2024"): {
        "ph": "***",
        "soc": "***",
        "ap": "***",
        "k": "**",
        "ca": "***",
    },
}


def make_record(
    *, site: str, season: str,
    treatment: str, outcome_key: str,
    value: float, sd: float, group: str,
) -> dict:
    outcome_id, unit = OUTCOMES[outcome_key]

    treatment_key = treatment.lower().replace("+", "-")

    record_id = f"t1-{site.lower()}-{season}-{treatment_key}-{outcome_key}"

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
        "comparison_significance": P_VALUES[(site, season)][outcome_key],
        "context": {
            "site": site,
            "season": season,
            "table": "Table 1",
            "soil_depth": "0-20 cm",
        },
        "provenance": {
            "provenance_type": "author_result",
            "locator": (
                f"Table 1, {site}, {season}, {treatment}, {outcome_key}"
            ),
        },
    }


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))

    existing = [
        item
        for item in payload["arm_results"]
        if item["record_id"].startswith("t1-")
    ]

    if existing:
        raise RuntimeError("Table 1 records already exist.")

    records = []

    for (site, season), treatments in TABLE_1.items():
        for treatment, outcomes in treatments.items():
            for outcome_key, (
                value,
                sd,
                group,
            ) in outcomes.items():
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

    assert len(records) == 120

    payload["arm_results"].extend(records)

    compiled_tables = set(
        payload["metadata"].get(
            "compiled_tables",
            []
        )
    )

    compiled_tables.add("Table 1")

    payload["metadata"]["compiled_tables"] = sorted(compiled_tables)

    payload["metadata"]["compilation_scope"] = (
        "study design, sites, population, "
        "interventions, arms, outcome definitions, "
        "Table 1 soil chemistry results, "
        "and Table 2 leaf K/Ca results"
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

    print(f"Compiled {len(records)} Table 1 records.")


if __name__ == "__main__":
    main()