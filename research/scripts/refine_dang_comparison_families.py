import json
from collections import defaultdict
from pathlib import Path

from agriworldmodel.compiled_evidence.schemas import CompiledStudy

PATH = Path("research/evidence/dang_2025_durian.json")

SUPPORTED_TABLES = {
    "Table 1",
    "Table 2",
    "Table 4",
}

ARM_ORDER = {
    "arm-control": 0,
    "arm-om": 1,
    "arm-ff": 2,
    "arm-om-ff": 3,
}

def safe_token(value: str) -> str:
    return (
        value
        .lower()
        .replace(" ", "-")
        .replace("+", "-")
        .replace("/", "-")
    )


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))

    # Idempotent behavior.
    existing = payload.get(
        "comparison_families",
        []
    )

    if existing:
        study = CompiledStudy.model_validate(payload)

        print(
            "Comparison families already "
            f"compiled: "
            f"{len(study.comparison_families)}"
        )
        return

    grouped = defaultdict(list)

    for result in payload["arm_results"]:
        table = result["context"].get("table")

        if table not in SUPPORTED_TABLES:
            continue

        key = (
            table,
            result["context"].get("site"),
            result["context"].get("season"),
            result["outcome_id"],
        )

        grouped[key].append(result)

    families = []

    for (table, site, season, outcome_id,), results in sorted(grouped.items()):
        results = sorted(
            results,
            key=lambda item: ARM_ORDER[item["arm_id"]],
        )

        if len(results) != 4:
            raise RuntimeError(
                "Expected four study arms for "
                f"{table}, {site}, {season}, "
                f"{outcome_id}; got "
                f"{len(results)}."
            )

        markers = {
            result.get("comparison_significance")
            for result in results
        }

        if len(markers) != 1:
            raise RuntimeError(
                "Inconsistent family significance "
                f"markers for {table}, {site}, "
                f"{season}, {outcome_id}: "
                f"{markers}"
            )

        marker = next(iter(markers))

        letters = {}

        for result in results:
            letter = result.get("significance_group")

            if not letter:
                raise RuntimeError(f"Missing Duncan group letter for {result['record_id']}.")

            letters[result["arm_id"]] = letter

        record_id = (
            "comparison-family-"
            f"{safe_token(table)}-"
            f"{safe_token(site)}-"
            f"{safe_token(season)}-"
            f"{safe_token(outcome_id)}"
        )

        families.append(
            {
                "record_id": record_id,

                "outcome_id": outcome_id,

                "member_arm_result_ids": [result["record_id"] for result in results],

                "reported_family_"
                "significance_marker": marker,

                # The paper reports the p-value
                # marker but does not identify
                # the overall/omnibus test.
                "overall_test_method": None,

                "overall_test_method_status": "not_reported",

                "post_hoc_method": "Duncan post hoc test",

                "post_hoc_alpha": 0.05,

                "group_letters_by_arm": letters,

                "group_letter_semantics": (
                    "Different letters indicate "
                    "significant differences among "
                    "treatment means under the "
                    "reported Duncan post hoc "
                    "procedure at p < 0.05."
                ),

                "context": {
                    "table": table,
                    "site": site,
                    "season": season,
                },

                "result_provenance": {
                    "provenance_type": "author_result",
                    "locator": (
                        f"{table}, {site}, "
                        f"{season}, "
                        f"{outcome_id}; treatment "
                        "letters and p-value row"
                    ),
                },

                "method_provenance": {
                    "provenance_type": "author_method",
                    "locator": "Section 4.6 Data Analysis",
                },
            }
        )

    assert len(families) == 66

    payload["comparison_families"] = families

    # Remove duplicated inferential semantics
    # from individual arm results.
    for result in payload["arm_results"]:
        if result["context"].get("table") in SUPPORTED_TABLES:
            result["significance_group"] = None

            result["comparison_significance"] = None

    payload["metadata"]["comparison_families_compiled"] = True

    payload["metadata"]["comparison_family_count"] = len(families)

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

    print(f"Compiled {len(families)} comparison families.")


if __name__ == "__main__":
    main()