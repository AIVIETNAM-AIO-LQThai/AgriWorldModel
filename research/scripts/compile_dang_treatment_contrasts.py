import json
from collections import defaultdict
from pathlib import Path

from agriworldmodel.compiled_evidence.schemas import CompiledStudy

PATH = Path("research/evidence/dang_2025_durian.json")

CONTROL_ARM = "arm-control"

INTERVENTION_ARMS = [
    "arm-om",
    "arm-ff",
    "arm-om-ff",
]

SUPPORTED_TABLES = {
    "Table 1",
    "Table 2",
    "Table 4",
}


def safe_token(value: str) -> str:
    return (
        value.lower().replace(" ", "-").replace("+", "-").replace("/", "-")
    )

def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))

    existing = [
        item
        for item in payload["contrasts"]
        if item["record_id"].startswith("derived-vs-control-")
    ]

    if existing:
        raise RuntimeError("Treatment-vs-control contrasts already exist.")

    # ---------------------------------------------------------------
    # Index raw results by:
    #
    # table / site / season / outcome / arm
    # ---------------------------------------------------------------
    groups = defaultdict(dict)

    for result in payload["arm_results"]:
        context = result["context"]

        table = context.get("table")

        if table not in SUPPORTED_TABLES:
            continue

        site = context.get("site")
        season = context.get("season")
        outcome_id = result["outcome_id"]
        arm_id = result["arm_id"]

        key = (
            table, site, season, outcome_id,
        )

        if arm_id in groups[key]:
            raise RuntimeError(
                "Duplicate raw result for "
                f"{key} / {arm_id}"
            )

        groups[key][arm_id] = result

    contrasts = []

    for (table, site, season, outcome_id), arm_map in sorted(groups.items()):

        control = arm_map.get(CONTROL_ARM)

        if control is None:
            raise RuntimeError(
                "Missing control result for "
                f"{table}, {site}, {season}, "
                f"{outcome_id}"
            )

        if control["value"] is None:
            raise RuntimeError(
                "Control value is missing for "
                f"{control['record_id']}"
            )

        for intervention_arm in (INTERVENTION_ARMS):
            intervention = arm_map.get(intervention_arm)

            if intervention is None:
                raise RuntimeError(
                    "Missing intervention result for "
                    f"{table}, {site}, {season}, "
                    f"{outcome_id}, "
                    f"{intervention_arm}"
                )

            if intervention["value"] is None:
                raise RuntimeError(
                    "Intervention value is missing for "
                    f"{intervention['record_id']}"
                )

            if intervention.get("unit") != control.get("unit"):
                raise RuntimeError(
                    "Cannot subtract results with "
                    "different units: "
                    f"{intervention['record_id']} vs "
                    f"{control['record_id']}"
                )

            effect_value = intervention["value"] - control["value"]

            record_id = (
                "derived-vs-control-"
                f"{safe_token(table)}-"
                f"{safe_token(site)}-"
                f"{safe_token(season)}-"
                f"{safe_token(intervention_arm)}-"
                f"{safe_token(outcome_id)}"
            )

            contrasts.append(
                {
                    "record_id": record_id,

                    "intervention_arm_id": intervention_arm,

                    "comparator_arm_id": CONTROL_ARM,

                    "outcome_id": outcome_id,

                    "effect_type": "absolute_mean_difference",

                    "effect_value": round(effect_value, 10,),

                    "unit": intervention.get("unit"),

                    # We deliberately do not derive
                    # SE/CI/p-values from SD values alone.
                    "uncertainty_text": None,
                    "significance_text": None,

                    "context": {
                        "table": table,
                        "site": site,
                        "season": season,
                        "comparison": f"{intervention_arm} minus arm-control",
                    },

                    "provenance": {
                        "provenance_type": "our_derived",

                        "source_record_ids": [
                            intervention["record_id"],
                            control["record_id"],
                        ],

                        "derivation": (
                            f"{intervention['record_id']}.value - "
                            f"{control['record_id']}.value"
                        ),

                        "notes": (
                            "Deterministic difference "
                            "between published treatment "
                            "and control arm means. "
                            "No uncertainty or p-value "
                            "is inferred."
                        ),
                    },
                }
            )

    assert len(contrasts) == 198

    payload["contrasts"].extend(contrasts)

    payload["metadata"]["derived_contrasts"] = {
        "comparison": "each experimental arm minus control",
        "effect_type": "absolute_mean_difference",
        "count": len(contrasts),
        "tables": [
            "Table 1",
            "Table 2",
            "Table 4",
        ],
    }

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

    print(f"Compiled {len(contrasts)} treatment-vs-control contrasts.")


if __name__ == "__main__":
    main()