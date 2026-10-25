import csv
import shutil
from pathlib import Path

import pytest
import yaml

from agriworldmodel.compiled_evidence.dang_2025_build import (
    build_study,
    check_table5_stars,
    critical_r,
    parse_cell,
    parse_correlation,
    render_json,
)
from agriworldmodel.compiled_evidence.dang_2025_verify import (
    compare_inputs,
    printed_digest,
    read_inputs,
)
from agriworldmodel.compiled_evidence.io import load_compiled_study

REPO = Path(__file__).resolve().parents[1]
INPUTS = REPO / "research" / "evidence" / "dang_2025"
ARTIFACT = REPO / "research" / "evidence" / "dang_2025_durian.json"
BASELINE = REPO / "tests" / "data" / "dang_2025_pre_phase_b_baseline.csv"
SELECTED = {"outcome-pd-rate", "outcome-peel-proportion",
            "outcome-seed-proportion", "outcome-aril-proportion",
            "outcome-aril-b-star", "outcome-tss"}


@pytest.fixture(scope="module")
def built():
    return build_study(INPUTS)


@pytest.fixture
def inputs_copy(tmp_path):
    """Editable copy of the inputs, outside the repository (no .git)."""
    target = tmp_path / "dang_2025"
    shutil.copytree(INPUTS, target)
    return target


def edit_csv(path, column, old, new):
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        header = list(rows[0])
    hit = [r for r in rows if r[column] == old]
    assert hit, (column, old)
    hit[0][column] = new
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# ---- reproducibility --------------------------------------------------------
def test_build_is_deterministic(built):
    assert render_json(built) == render_json(build_study(INPUTS))


def test_committed_artifact_equals_a_fresh_build(built):
    committed = ARTIFACT.read_bytes().replace(b"\r\n", b"\n")
    assert render_json(built).encode("utf-8") == committed


def test_build_needs_no_git_state_or_working_directory(
        inputs_copy, tmp_path, monkeypatch, built):
    assert not (tmp_path / ".git").exists()
    monkeypatch.chdir(tmp_path)
    assert render_json(build_study(inputs_copy)) == render_json(built)


def test_artifact_loads_through_the_public_loader():
    study = load_compiled_study(ARTIFACT)
    assert study.schema_version == "compiled-study-2"


# ---- preserved content ---------------------------------------------------------
def baseline_rows():
    with BASELINE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_every_pre_phase_b_record_id_is_preserved(built):
    ids = {
        "arm_result": {r.record_id: r for r in built.arm_results},
        "family": {r.record_id: r for r in built.comparison_families},
        "contrast": {r.record_id: r for r in built.contrasts},
        "association": {r.record_id: r for r in built.associations},
    }
    rows = baseline_rows()
    assert len(rows) == 564
    missing = [r["record_id"] for r in rows if r["record_id"] not in ids[r["kind"]]]
    assert missing == []


def test_published_numbers_and_derived_values_are_unchanged(built):
    arm = {r.record_id: r for r in built.arm_results}
    con = {r.record_id: r for r in built.contrasts}
    ass = {r.record_id: r for r in built.associations}
    for row in baseline_rows():
        rid = row["record_id"]
        if row["kind"] == "arm_result":
            assert repr(arm[rid].value) == row["value"], rid
            assert repr(arm[rid].dispersion_value) == row["dispersion_value"], rid
        elif row["kind"] == "contrast":
            assert repr(con[rid].effect_value) == row["value"], rid
        elif row["kind"] == "association":
            assert repr(ass[rid].value) == row["value"], rid


def test_record_counts(built):
    assert (len(built.arm_results), len(built.comparison_families),
            len(built.contrasts), len(built.associations)) == (336, 84, 252, 36)


# ---- scientific semantics ------------------------------------------------------
def test_contrasts_are_labelled_published_mean_differences(built):
    for c in built.contrasts:
        assert c.evidential_basis.value == "published_arm_mean_difference"
        text = " ".join([c.estimand_text, c.uncertainty_text or "", *c.assumptions])
        assert "randomized_within" not in text
        assert "not a block-adjusted" in text and "randomization unit" in text
        assert c.significance_text is None
        assert c.uncertainty_status.value == (
            "not_reconstructible_from_published_summaries")


def test_percent_differences_are_percentage_points_and_others_unchanged(built):
    arm = {r.record_id: r for r in built.arm_results}
    for c in built.contrasts:
        unit = arm[c.provenance.source_record_ids[0]].unit
        assert c.unit == ("percentage points" if unit == "%" else unit), c.record_id
    assert sum(c.unit == "percentage points" for c in built.contrasts) == 90


def test_selected_fruit_outcomes_are_audited(built):
    flags = {o.outcome_id: o.post_treatment_selection for o in built.outcomes}
    assert {k for k, v in flags.items() if v} == SELECTED
    assert flags["outcome-fruit-yield"] is False
    assert all(flags[k] is False for k in flags if k.startswith(
        ("outcome-soil", "outcome-soc", "outcome-available", "outcome-leaf")))
    for c in built.contrasts:
        selected = c.outcome_id in SELECTED
        assert any("selected fruit" in a for a in c.assumptions) == selected


def test_table5_values_and_stars_are_preserved_and_inconsistencies_documented(built):
    flag = next(f for f in built.flags
                if f.record_id == "flag-table5-markers-inconsistent-with-n72")
    assert len(built.associations) == 36
    parsed = [{"record_id": a.record_id, "value": a.value,
               "stars": a.context["significance_marker"].replace("none", "") or None}
              for a in built.associations]
    expected = check_table5_stars(parsed, 72)
    assert sorted(flag.related_record_ids) == sorted(f["record_id"] for f in expected)
    assert len(flag.related_record_ids) == 17
    assert "7 correlations carry no star" in flag.detail
    assert "10 carry a single star" in flag.detail
    assert "does not show that the authors' tests were wrong" in flag.detail


def test_randomization_flag_covers_every_contrast(built):
    flag = next(f for f in built.flags
                if f.record_id == "flag-randomization-unit-unclear")
    contrast_ids = {c.record_id for c in built.contrasts}
    assert contrast_ids <= set(flag.related_record_ids)
    assert built.design.randomization_unit is None


def test_ns_families_carry_no_letters_and_others_do(built):
    for fam in built.comparison_families:
        if fam.reported_family_significance_marker == "ns":
            assert fam.group_letters_by_arm == {}
        else:
            assert len(fam.group_letters_by_arm) == 4
    assert sum(f.reported_family_significance_marker == "ns"
               for f in built.comparison_families) == 6


# ---- parsing and statistics helpers ------------------------------------------
def test_parse_cell_variants():
    assert parse_cell("13.9 b ± 0.35").letter == "b"
    assert parse_cell("8.80 ± 0.69").letter is None
    assert parse_cell("65.9 ab ± 1.18").letter == "ab"
    ambiguous = parse_cell("13.9 b ± 035")
    assert ambiguous.value == 13.9 and ambiguous.sd is None


@pytest.mark.parametrize("bad", ["", "abc", "1.2 ± ", "1,2 b ± 0.3", "1.2 b 0.3"])
def test_parse_cell_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_cell(bad)


def test_parse_correlation_handles_the_printed_minus_sign():
    assert parse_correlation("−0.54 *") == (-0.54, "*")
    assert parse_correlation("0.42") == (0.42, None)


def test_critical_r_matches_the_textbook_value():
    assert critical_r(72, 0.05) == pytest.approx(0.2319, abs=5e-4)
    assert critical_r(72, 0.01) == pytest.approx(0.3017, abs=5e-4)


# ---- tamper detection ---------------------------------------------------------
def test_changed_cell_changes_the_build_and_fails_the_artifact_check(
        inputs_copy, built):
    edit_csv(inputs_copy / "cells.csv", "printed", "65.1 c ± 1.35", "65.2 c ± 1.35")
    assert render_json(build_study(inputs_copy)) != render_json(built)


def test_changed_contrast_follows_changed_arm_mean(inputs_copy, built):
    edit_csv(inputs_copy / "cells.csv", "printed", "65.1 c ± 1.35", "65.2 c ± 1.35")
    rebuilt = build_study(inputs_copy)
    old = {c.record_id: c.effect_value for c in built.contrasts}
    changed = [c for c in rebuilt.contrasts if c.effect_value != old[c.record_id]]
    assert len(changed) == 3
    assert all("t4-d1-2022-2023-control-yield" in c.provenance.source_record_ids
               for c in changed)


def test_pdf_comparison_reports_a_tampered_cell_marker_and_correlation(inputs_copy):
    def rows(name):
        with (inputs_copy / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    truth = {
        "cells": {(r["table"], r["site"], r["season"], r["treatment"], r["variable"]):
                  r["printed"] for r in rows("cells.csv")},
        "markers": {(r["table"], r["site"], r["season"], r["variable"]): r["marker"]
                    for r in rows("markers.csv")},
        "corr": {(r["x"], r["y"]): r["printed"] for r in rows("table5.csv")},
    }
    assert compare_inputs(inputs_copy, truth)["mismatches"] == []
    edit_csv(inputs_copy / "cells.csv", "printed", "65.1 c ± 1.35", "65.1 c ± 1.53")
    edit_csv(inputs_copy / "markers.csv", "marker", "ns", "*")
    edit_csv(inputs_copy / "table5.csv", "printed", "0.74 **", "0.47 **")
    report = compare_inputs(inputs_copy, truth)
    kinds = {m.split()[0] for m in report["mismatches"]}
    assert kinds == {"cell", "marker", "correlation"}


def test_unparseable_sd_needs_a_flag(inputs_copy):
    path = inputs_copy / "study.yaml"
    cfg = yaml.safe_load(path.read_text("utf-8"))
    cfg["flags"] = [f for f in cfg["flags"]
                    if f["record_id"] != "flag-table2-d1-om-k-sd"]
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), "utf-8")
    with pytest.raises(ValueError, match="has no flag"):
        build_study(inputs_copy)


def test_missing_family_marker_is_rejected(inputs_copy):
    path = inputs_copy / "markers.csv"
    lines = path.read_text("utf-8").splitlines()
    path.write_text("\n".join(lines[:1] + lines[2:]) + "\n", "utf-8")
    with pytest.raises(ValueError, match="no family marker"):
        build_study(inputs_copy)


def test_letters_without_an_ns_marker_are_rejected(inputs_copy):
    with (inputs_copy / "cells.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    target = next(r for r in rows if r["table"] == "Table 1")
    target["printed"] = target["printed"].replace(" b ", " ", 1)
    with (inputs_copy / "cells.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ValueError, match="inconsistent letters"):
        build_study(inputs_copy)


def test_missing_input_file_is_reported(inputs_copy):
    (inputs_copy / "markers.csv").unlink()
    with pytest.raises(FileNotFoundError):
        build_study(inputs_copy)


def test_artifact_lines_in_inputs_are_lf_in_the_repository_blobs():
    attrs = (REPO / ".gitattributes").read_text("utf-8")
    assert "research/evidence/** text eol=lf" in attrs


# ---- independent transcription anchor -------------------------------------
def committed_digest():
    lines = (INPUTS / "pdf_extraction.sha256").read_text("utf-8").splitlines()
    return dict(line.split(" ", 1) for line in lines if not line.startswith("#"))


def test_inputs_match_the_recorded_pdf_extraction_digest():
    # The digest was written from a pypdf re-parse of the source PDF with
    # 0 mismatches; any later edit of a printed string breaks this test.
    assert printed_digest(read_inputs(INPUTS)) == committed_digest()


def test_digest_detects_a_consistent_marker_edit(inputs_copy):
    edit_csv(inputs_copy / "markers.csv", "marker", "ns", "*")
    assert printed_digest(read_inputs(inputs_copy)) != committed_digest()


def test_duplicate_or_orphan_markers_are_rejected(inputs_copy):
    path = inputs_copy / "markers.csv"
    lines = path.read_text("utf-8").splitlines()
    path.write_text("\n".join(lines + [lines[1]]) + "\n", "utf-8")
    with pytest.raises(ValueError, match="duplicate family marker"):
        build_study(inputs_copy)
    path.write_text("\n".join(lines + ["Table 9,D1,2022-2023,x,**"]) + "\n", "utf-8")
    with pytest.raises(ValueError, match="without cells"):
        build_study(inputs_copy)


def test_duplicate_table5_pair_is_rejected(inputs_copy):
    path = inputs_copy / "table5.csv"
    lines = path.read_text("utf-8").splitlines()
    path.write_text("\n".join(lines + [lines[1]]) + "\n", "utf-8")
    with pytest.raises(ValueError, match="duplicate Table 5 pair"):
        build_study(inputs_copy)
