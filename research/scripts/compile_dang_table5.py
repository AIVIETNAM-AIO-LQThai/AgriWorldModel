import json
from pathlib import Path

from agriworldmodel.compiled_evidence.schemas import (
    CompiledStudy,
)


PATH = Path(
    "research/evidence/dang_2025_durian.json"
)


VARIABLES = {
    "soil_ph": "outcome-soil-ph",
    "soc": "outcome-soc",
    "available_p": "outcome-available-p",
    "exchangeable_k": "outcome-soil-exchangeable-k",
    "exchangeable_ca": "outcome-soil-exchangeable-ca",
    "leaf_k": "outcome-leaf-k",
    "leaf_ca": "outcome-leaf-ca",
    "fruit_yield": "outcome-fruit-yield",
    "pd_rate": "outcome-pd-rate",
}


# Each row:
#   x_key, y_key, Pearson r, significance marker
#
# Table 5 reports Pearson's r with n = 72.
TABLE_5 = [
    # SOC
    ("soc", "soil_ph", 0.74, "**"),

    # Available P
    ("available_p", "soil_ph", 0.87, "**"),
    ("available_p", "soc", 0.77, "**"),

    # Exchangeable K
    ("exchangeable_k", "soil_ph", 0.51, "*"),
    ("exchangeable_k", "soc", 0.72, "**"),
    ("exchangeable_k", "available_p", 0.42, None),

    # Exchangeable Ca
    ("exchangeable_ca", "soil_ph", 0.77, "**"),
    ("exchangeable_ca", "soc", 0.76, "**"),
    ("exchangeable_ca", "available_p", 0.79, "**"),
    ("exchangeable_ca", "exchangeable_k", 0.75, "**"),

    # Leaf K
    ("leaf_k", "soil_ph", 0.55, "*"),
    ("leaf_k", "soc", 0.66, "*"),
    ("leaf_k", "available_p", 0.51, "*"),
    ("leaf_k", "exchangeable_k", 0.63, "**"),
    ("leaf_k", "exchangeable_ca", 0.58, "*"),

    # Leaf Ca
    ("leaf_ca", "soil_ph", 0.38, None),
    ("leaf_ca", "soc", 0.60, "*"),
    ("leaf_ca", "available_p", 0.39, None),
    ("leaf_ca", "exchangeable_k", 0.38, None),
    ("leaf_ca", "exchangeable_ca", 0.25, None),
    ("leaf_ca", "leaf_k", 0.77, "**"),

    # Fruit yield
    ("fruit_yield", "soil_ph", 0.37, None),
    ("fruit_yield", "soc", 0.17, None),
    ("fruit_yield", "available_p", 0.16, None),
    ("fruit_yield", "exchangeable_k", 0.18, None),
    ("fruit_yield", "exchangeable_ca", 0.17, None),
    ("fruit_yield", "leaf_k", 0.31, None),
    ("fruit_yield", "leaf_ca", 0.17, None),

    # Physiological-disorder rate
    ("pd_rate", "soil_ph", -0.54, "*"),
    ("pd_rate", "soc", -0.71, "**"),
    ("pd_rate", "available_p", -0.52, "*"),
    ("pd_rate", "exchangeable_k", -0.54, "*"),
    ("pd_rate", "exchangeable_ca", -0.46, "*"),
    ("pd_rate", "leaf_k", -0.88, "**"),
    ("pd_rate", "leaf_ca", -0.91, "**"),
    ("pd_rate", "fruit_yield", -0.22, None),
]


SIGNIFICANCE = {
    "*": "p < 0.05",
    "**": "p < 0.01",
    None: None,
}


def make_record(
    index: int,
    x_key: str,
    y_key: str,
    value: float,
    marker: str | None,
) -> dict:
    return {
        "record_id": (
            f"t5-corr-{index:02d}-"
            f"{x_key}-{y_key}"
        ),
        "x": VARIABLES[x_key],
        "y": VARIABLES[y_key],
        "statistic": "pearson_r",
        "value": value,
        "sample_size": 72,
        "significance_text": (
            SIGNIFICANCE[marker]
        ),
        "context": {
            "table": "Table 5",
            "scope": (
                "pooled study observations"
            ),
            "significance_marker": (
                marker or "none"
            ),
        },
        "provenance": {
            "provenance_type": (
                "author_result"
            ),
            "locator": (
                f"Table 5, "
                f"{x_key} vs {y_key}"
            ),
        },
    }


def main() -> None:
    payload = json.loads(
        PATH.read_text(
            encoding="utf-8"
        )
    )

    existing = [
        item
        for item in payload[
            "associations"
        ]
        if item["record_id"].startswith(
            "t5-"
        )
    ]

    if existing:
        raise RuntimeError(
            "Table 5 associations "
            "already exist."
        )

    records = [
        make_record(
            index,
            x_key,
            y_key,
            value,
            marker,
        )
        for index, (
            x_key,
            y_key,
            value,
            marker,
        ) in enumerate(
            TABLE_5,
            start=1,
        )
    ]

    assert len(records) == 36

    payload["associations"].extend(
        records
    )

    compiled_tables = set(
        payload["metadata"].get(
            "compiled_tables",
            []
        )
    )

    compiled_tables.add("Table 5")

    payload["metadata"][
        "compiled_tables"
    ] = sorted(compiled_tables)

    payload["metadata"][
        "compilation_scope"
    ] = (
        "study design, sites, population, "
        "interventions, arms, outcome "
        "definitions, Table 1 soil chemistry, "
        "Table 2 leaf nutrients, Table 4 "
        "fruit yield and quality, and Table 5 "
        "Pearson associations"
    )

    study = CompiledStudy.model_validate(
        payload
    )

    PATH.write_text(
        json.dumps(
            study.model_dump(
                mode="json"
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Compiled {len(records)} "
        "Table 5 associations."
    )


if __name__ == "__main__":
    main()