"""Deterministic build of the Dang et al. (2025) compiled study.

Everything is derived from version-controlled inputs in one directory:

* ``study.yaml``   - design, interventions, outcomes, hand-authored flags and
                     the wording of derived records (human-reviewed);
* ``cells.csv``    - one printed table cell per row, verbatim from the paper;
* ``markers.csv``  - printed p-value marker of each comparison family;
* ``table5.csv``   - printed Pearson r (with significance stars) per pair.

The build reads no Git state, clock or network. Output is canonical JSON
(sorted by construction, LF line endings), so identical inputs give
identical bytes on any platform.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from scipy import stats

from agriworldmodel.compiled_evidence.schemas import CompiledStudy

INPUT_FILES = ("study.yaml", "cells.csv", "markers.csv", "table5.csv")

# "13.9 b ± 0.35", "8.80 ± 0.69", "65.9 ab ± 1.18" (letters optional).
_CELL = re.compile(
    r"^(-?\d+(?:\.\d+)?)(?: ([a-z]{1,3}))? ± (\d+(?:\.\d+)?)$")
_CORR = re.compile(r"^([−-]?)(\d+\.\d+)(?: (\*{1,2}))?$")
_DECIMAL = re.compile(r"^\d+\.\d+$")
ARM_ORDER = ("control", "om", "ff", "om-ff")


@dataclass(frozen=True)
class ParsedCell:
    value: float
    letter: str | None
    sd: float | None   # None when the printed SD is not a clean decimal


def parse_cell(printed: str) -> ParsedCell:
    """Parse one printed table cell.

    An SD without a decimal point (the paper prints '035') is ambiguous, so
    it is returned as None rather than guessed; the caller must then find a
    flag that documents it.
    """
    match = _CELL.match(printed)
    if match is None:
        raise ValueError(f"unparseable printed cell: {printed!r}")
    value, letter, sd = match.groups()
    return ParsedCell(
        float(value), letter, float(sd) if _DECIMAL.match(sd) else None)


def parse_correlation(printed: str) -> tuple[float, str | None]:
    match = _CORR.match(printed)
    if match is None:
        raise ValueError(f"unparseable printed correlation: {printed!r}")
    sign, magnitude, stars = match.groups()
    return (-float(magnitude) if sign else float(magnitude)), stars


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _token(value: str) -> str:
    return (value.lower().replace(" ", "-").replace("+", "-")
            .replace("/", "-"))


def _arm_token(treatment: str) -> str:
    return treatment.lower().replace("+", "-")


# Two-sided critical |r| for a Pearson test with n pairs, if all n pairs
# were independent. Used only to *check* printed stars, never to alter them.
def critical_r(n: int, alpha: float) -> float:
    t = stats.t.ppf(1 - alpha / 2, n - 2)
    return float(t / (t * t + n - 2) ** 0.5)


def check_table5_stars(
    correlations: list[dict[str, Any]], n: int,
) -> list[dict[str, Any]]:
    """Compare printed stars with those implied by n independent pairs.

    Stars are read as exclusive bands: none = p >= 0.05, '*' = 0.01 <= p <
    0.05, '**' = p < 0.01. Under an inclusive reading of '*' (p < 0.05 even
    when p < 0.01) only unmarked cells can disagree; both counts are kept.
    """
    c05, c01 = critical_r(n, 0.05), critical_r(n, 0.01)
    findings = []
    for item in correlations:
        r, stars = abs(item["value"]), item["stars"]
        implied = "**" if r >= c01 else "*" if r >= c05 else None
        if implied != stars:
            findings.append({
                "record_id": item["record_id"], "printed": stars,
                "implied": implied,
                "missing_star": stars is None,
            })
    return findings


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _group_cells(
    rows: list[dict[str, str]], spec: dict[str, Any],
) -> dict[tuple[str, str, str, str], dict[str, ParsedCell]]:
    """Index parsed cells by (table, site, season, variable) -> arm label."""
    groups: dict[tuple[str, str, str, str], dict[str, ParsedCell]] = {}
    for row in rows:
        if row["table"] not in spec:
            raise ValueError(f"table {row['table']!r} has no build rule")
        key = (row["table"], row["site"], row["season"], row["variable"])
        cells = groups.setdefault(key, {})
        if row["treatment"] in cells:
            raise ValueError(f"duplicate cell {key} {row['treatment']}")
        cells[row["treatment"]] = parse_cell(row["printed"])
    return groups


def build_study(input_dir: Path) -> CompiledStudy:
    """Build and validate the compiled study from the input directory."""
    for name in INPUT_FILES:
        if not (input_dir / name).is_file():
            raise FileNotFoundError(f"missing build input: {input_dir / name}")
    cfg = yaml.safe_load((input_dir / "study.yaml").read_text("utf-8"))
    cells = _read_csv(input_dir / "cells.csv")
    marker_rows = _read_csv(input_dir / "markers.csv")
    corr_rows = _read_csv(input_dir / "table5.csv")

    tables, treatments = cfg["tables"], cfg["treatments"]
    outcome_unit = {o["outcome_id"]: o["unit"] for o in cfg["outcomes"]}
    groups = _group_cells(cells, tables)
    markers: dict[tuple[str, str, str, str], str] = {}
    for m in marker_rows:
        key = (m["table"], m["site"], m["season"], m["variable"])
        if key in markers:
            raise ValueError(f"duplicate family marker {key}")
        markers[key] = m["marker"]

    # Stage 1: arm results, in the order of cells.csv.
    arm_results, unparsed_sd = [], []
    for row in cells:
        spec = tables[row["table"]]
        var, parsed = row["variable"], groups[
            (row["table"], row["site"], row["season"], row["variable"])
        ][row["treatment"]]
        outcome_id = spec["variables"][var]
        record_id = (f"{spec['prefix']}-{row['site'].lower()}-"
                     f"{row['season']}-{_arm_token(row['treatment'])}-"
                     f"{var.lower()}")
        if parsed.sd is None:
            unparsed_sd.append(record_id)
        arm_results.append({
            "record_id": record_id,
            "arm_id": treatments[row["treatment"]],
            "outcome_id": outcome_id,
            "value": parsed.value,
            "unit": outcome_unit[outcome_id],
            "dispersion_type":
                "standard_deviation" if parsed.sd is not None else None,
            "dispersion_value": parsed.sd,
            "sample_size": spec["sample_size"],
            "significance_group": None,
            "comparison_significance": None,
            "context": {"site": row["site"], "season": row["season"],
                        "table": row["table"], **spec["context_extra"]},
            "provenance": {
                "provenance_type": "author_result",
                "locator": (f"{row['table']}, {row['site']}, "
                            f"{row['season']}, {row['treatment']}, {var}"),
            },
        })
    flagged = {rid for flag in cfg["flags"]
               for rid in flag["related_record_ids"]}
    for record_id in unparsed_sd:
        if record_id not in flagged:
            raise ValueError(f"unparsed SD in {record_id} has no flag")
    result_by_id = {r["record_id"]: r for r in arm_results}

    # Stage 2: one comparison family per (table, site, season, outcome).
    fam_rules = cfg["family_rules"]
    families, family_keys = [], []
    for (table, site, season, var), arm_cells in groups.items():
        spec = tables[table]
        if set(arm_cells) != set(treatments):
            raise ValueError(f"expected four arms for {table} {site} {season} {var}")
        outcome_id = spec["variables"][var]
        marker = markers.get((table, site, season, var))
        if marker is None:
            raise ValueError(f"no family marker for {table} {site} {season} {var}")
        ordered = sorted(arm_cells, key=lambda t: ARM_ORDER.index(_arm_token(t)))
        letters = {treatments[t]: arm_cells[t].letter for t in ordered}
        have = [v is not None for v in letters.values()]
        if all(have):
            semantics = fam_rules["group_letter_semantics"]
        elif not any(have) and marker == "ns":
            letters, semantics = {}, fam_rules["no_letters_semantics"]
        else:
            raise ValueError(f"inconsistent letters for {table} {site} {season} {var}")
        members = [
            f"{spec['prefix']}-{site.lower()}-{season}-{_arm_token(t)}-{var.lower()}"
            for t in ordered
        ]
        family_keys.append((table, site, season, outcome_id))
        families.append({
            "record_id": ("comparison-family-"
                          f"{_token(table)}-{_token(site)}-{_token(season)}-"
                          f"{_token(outcome_id)}"),
            "outcome_id": outcome_id,
            "member_arm_result_ids": members,
            "reported_family_significance_marker": marker,
            "overall_test_method": None,
            "overall_test_method_status": fam_rules["overall_test_method_status"],
            "post_hoc_method": fam_rules["post_hoc_method"],
            "post_hoc_alpha": fam_rules["post_hoc_alpha"],
            "group_letters_by_arm": letters,
            "group_letter_semantics": semantics,
            "context": {"table": table, "site": site, "season": season},
            "result_provenance": {
                "provenance_type": "author_result",
                "locator": (f"{table}, {site}, {season}, {outcome_id}; "
                            f"{fam_rules['result_locator_suffix']}"),
            },
            "method_provenance": {
                "provenance_type": "author_method",
                "locator": fam_rules["method_locator"],
            },
        })
    # A marker with no matching cells is a transcription slip, not noise.
    unused = set(markers) - set(groups)
    if unused:
        raise ValueError(f"family markers without cells: {sorted(unused)}")
    order = sorted(range(len(families)), key=lambda i: family_keys[i])
    families = [families[i] for i in order]
    family_keys = [family_keys[i] for i in order]

    # Stage 3: derived treatment-minus-control contrasts.
    rules = cfg["contrast_rules"]
    control_arm = cfg["control_arm"]
    outcome_selected = {o["outcome_id"]: o.get("post_treatment_selection")
                        for o in cfg["outcomes"]}
    contrasts = []
    for (table, site, season, outcome_id), family in zip(family_keys, families):
        spec = tables[table]
        by_arm = {result_by_id[m]["arm_id"]: result_by_id[m]
                  for m in family["member_arm_result_ids"]}
        control = by_arm[control_arm]
        for arm_id in (a for a in treatments.values() if a != control_arm):
            treated = by_arm[arm_id]
            if treated["unit"] != control["unit"]:
                raise ValueError("cannot subtract results with different units")
            unit = rules["difference_units"].get(treated["unit"], treated["unit"])
            record_id = ("derived-vs-control-"
                         f"{_token(table)}-{_token(site)}-{_token(season)}-"
                         f"{_token(arm_id)}-{_token(outcome_id)}")
            assumptions = list(rules["assumptions"])
            if outcome_selected.get(outcome_id):
                assumptions.append(rules["selected_fruit_assumption"])
            contrasts.append({
                "record_id": record_id,
                "intervention_arm_id": arm_id,
                "comparator_arm_id": control_arm,
                "outcome_id": outcome_id,
                "effect_type": rules["effect_type"],
                "effect_value": round(treated["value"] - control["value"], 10),
                "unit": unit,
                "evidential_basis": rules["evidential_basis"],
                "estimand_text": rules["estimand_text"],
                "uncertainty_status": rules["uncertainty_status"],
                "uncertainty_text": rules["uncertainty_text"],
                "significance_text": rules["significance_text"],
                "assumptions": assumptions,
                "context": {"table": table, "site": site, "season": season,
                            "comparison": f"{arm_id} minus {control_arm}"},
                "provenance": {
                    "provenance_type": "our_derived",
                    "source_record_ids": [treated["record_id"],
                                          control["record_id"]],
                    "derivation": (f"{treated['record_id']}.value - "
                                   f"{control['record_id']}.value"),
                    "notes": rules["provenance_notes"],
                },
            })

    # Stage 4: Table 5 associations, exactly as printed.
    arules = cfg["association_rules"]
    associations, parsed_corr, pairs = [], [], set()
    for index, row in enumerate(corr_rows, start=1):
        if (row["x"], row["y"]) in pairs:
            raise ValueError(f"duplicate Table 5 pair {row['x']} vs {row['y']}")
        pairs.add((row["x"], row["y"]))
        value, stars = parse_correlation(row["printed"])
        record_id = f"t5-corr-{index:02d}-{row['x']}-{row['y']}"
        parsed_corr.append({"record_id": record_id, "value": value,
                            "stars": stars})
        associations.append({
            "record_id": record_id,
            "x": arules["variables"][row["x"]],
            "y": arules["variables"][row["y"]],
            "statistic": arules["statistic"],
            "value": value,
            "sample_size": arules["sample_size"],
            "significance_text": arules["significance_text"].get(stars),
            "context": {"table": "Table 5", "scope": arules["scope"],
                        "significance_marker": stars or "none"},
            "provenance": {"provenance_type": "author_result",
                           "locator": f"Table 5, {row['x']} vs {row['y']}"},
        })

    # Stage 5: flags: hand-authored ones plus computed, evidence-linked ones.
    flags = [dict(flag) for flag in cfg["flags"]]
    generated = cfg.get("generated_flags", {})
    context = {
        "all_contrast_ids": [c["record_id"] for c in contrasts],
        "all_family_ids": [f["record_id"] for f in families],
    }
    if "table5_consistency" in generated:
        flags.append(_table5_flag(
            generated["table5_consistency"], parsed_corr,
            arules["sample_size"]))
    for name in ("table5_pooling", "letter_semantics"):
        if name in generated:
            flags.append(_context_flag(generated[name], name, context,
                                       associations))
    flags = _apply_flag_updates(flags, cfg.get("flag_updates", {}), context)

    # Stage 6: assemble, keep metadata honest, validate.
    metadata = dict(cfg["metadata"])
    tables_used = sorted({r["table"] for r in cells})
    if metadata["compiled_tables"] != sorted({*tables_used, "Table 5"}):
        raise ValueError("metadata.compiled_tables disagrees with the inputs")
    metadata["derived_contrasts"] = {
        **metadata["derived_contrasts"], "count": len(contrasts),
        "tables": tables_used,
    }
    metadata["comparison_family_count"] = len(families)
    payload = {
        "study_id": cfg["study_id"], "source": cfg["source"],
        "design": cfg["design"], "sites": cfg["sites"],
        "population": cfg["population"],
        "interventions": cfg["interventions"], "arms": cfg["arms"],
        "outcomes": cfg["outcomes"], "arm_results": arm_results,
        "comparison_families": families, "contrasts": contrasts,
        "associations": associations, "interpretations": [],
        "recommendations": [], "flags": flags, "metadata": metadata,
    }
    if "schema_version" in cfg:
        payload["schema_version"] = cfg["schema_version"]
    return CompiledStudy.model_validate(payload)


def _table5_flag(spec, parsed_corr, n):
    findings = check_table5_stars(parsed_corr, n)
    missing = [f for f in findings if f["missing_star"]]
    single_strong = [f for f in findings
                     if f["printed"] == "*" and f["implied"] == "**"]
    if len(missing) + len(single_strong) != len(findings):
        raise ValueError("unexpected kind of Table 5 star disagreement")
    c05, c01 = critical_r(n, 0.05), critical_r(n, 0.01)
    detail = spec["detail_template"].format(
        n=n, n_total=len(parsed_corr), n_inconsistent=len(findings),
        n_missing=len(missing), n_single_star=len(single_strong),
        c05=_fmt(c05), c01=_fmt(c01))
    return {
        "record_id": spec["record_id"], "flag_type": spec["flag_type"],
        "detail": detail,
        "related_record_ids": [f["record_id"] for f in findings],
        "locator": spec["locator"],
    }


def _context_flag(spec, name, context, associations):
    related = {
        "table5_pooling": [a["record_id"] for a in associations],
        "letter_semantics": context["all_family_ids"],
    }[name]
    return {
        "record_id": spec["record_id"], "flag_type": spec["flag_type"],
        "detail": spec["detail"], "related_record_ids": related,
        "locator": spec["locator"],
    }


# Lets study.yaml extend the related records of an existing hand-authored
# flag with computed id groups, without duplicating long id lists.
def _apply_flag_updates(flags, updates, context):
    by_id = {flag["record_id"]: flag for flag in flags}
    for flag_id, spec in updates.items():
        flag = by_id[flag_id]
        if "related_extra" in spec:
            flag["related_record_ids"] = (
                list(flag["related_record_ids"])
                + context[spec["related_extra"]])
    return flags


def render_json(study: CompiledStudy) -> str:
    """Canonical text: 2-space indent, UTF-8 characters, LF, final newline."""
    return json.dumps(
        study.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"


def write_canonical(study: CompiledStudy, path: Path) -> bytes:
    data = render_json(study).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data
