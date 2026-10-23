import hashlib
import json
from pathlib import Path

import pytest

from agriworldmodel.corpus.manifest import ManifestRow, load_manifest
from agriworldmodel.corpus.sources import (
    SourceRow,
    load_sources,
    reconcile_db_sources,
    resolve_pdf_by_sha256,
    validate_sources,
)

REPO = Path(__file__).resolve().parents[1]
PATH = "data/techniques_research/fertilization/a__b__c__d__2025.pdf"


def source(**overrides) -> SourceRow:
    base = {
        "source_id": "test-2025", "title": "T", "container_title": "",
        "source_kind": "journal_article", "study_design": "field_trial",
        "study_design_status": "reported_by_source", "issuing_body": "",
        "other_bodies": "", "issuing_jurisdiction": "", "study_region": "",
        "year": "2025", "edition_statement": "", "doi": "10.1000/abc",
        "isbn": "", "url": "", "identifier_locator": "p. 1", "license": "",
        "license_locator": "", "unverified_fields": "", "concerns": ""}
    return SourceRow(**{**base, **overrides})


def manifest_row(path=PATH, sha="a" * 64, **overrides) -> ManifestRow:
    base = {
        "original_path": "old.pdf", "new_path": path, "primary_topic": "x",
        "subcategory": "y", "secondary_themes": "", "region": "", "crop": "",
        "document_role": "", "year": "2025", "language": "en", "sha256": sha,
        "ambiguity_or_warning": "", "source_id": "test-2025", "source_part": ""}
    return ManifestRow(**{**base, **overrides})


def codes(sources, rows):
    return {issue.code for issue in validate_sources(sources, rows)}


def test_consistent_registry_has_no_issues():
    assert validate_sources([source()], [manifest_row()]) == []


@pytest.mark.parametrize("overrides, code", [
    ({"source_id": "Bad_ID"}, "bad_source_id"),
    ({"source_kind": "blog"}, "bad_source_kind"),
    ({"study_design": "rct"}, "bad_study_design"),
    ({"study_design_status": "sure"}, "bad_study_design_status"),
    ({"year": "25"}, "bad_year"),
    ({"doi": "not-a-doi"}, "bad_doi"),
    ({"identifier_locator": ""}, "identifier_without_locator"),
    ({"doi": "", "isbn": "1 2 3", "identifier_locator": ""},
     "identifier_without_locator"),
    ({"license": "CC BY"}, "license_without_locator"),
    ({"url": "https://doi.org/10.1000/other"}, "doi_url_mismatch"),
    ({"unverified_fields": "title;colour"}, "unknown_unverified_field"),
    ({"other_bodies": "host Ministry"}, "bad_other_bodies"),
    ({"other_bodies": "host: Ministry; : Nobody"}, "bad_other_bodies"),
    ({"other_bodies": "Host Body: Ministry"}, "bad_other_bodies"),
    ({"other_bodies": "host:"}, "bad_other_bodies"),
])
def test_field_rules_fire(overrides, code):
    rows = [manifest_row(source_id=overrides.get("source_id", "test-2025"))]
    assert code in codes([source(**overrides)], rows)


def test_blank_identifiers_are_allowed_without_locator():
    assert validate_sources(
        [source(doi="", identifier_locator="")], [manifest_row()]) == []


def test_well_formed_other_bodies_and_new_unverified_fields_pass():
    ok = source(
        other_bodies="host: A - B; implementer: C; printed and published by: D",
        unverified_fields="container_title;edition_statement")
    assert validate_sources([ok], [manifest_row()]) == []


def test_duplicate_source_id():
    assert "duplicate_source_id" in codes([source(), source()], [manifest_row()])


def test_manifest_row_must_name_a_known_source():
    assert "manifest_unknown_source" in codes(
        [source()], [manifest_row(), manifest_row(source_id="ghost")])


def test_source_without_files():
    assert "source_without_files" in codes(
        [source(), source(source_id="orphan")], [manifest_row()])


def test_manifest_and_source_years_must_agree():
    assert "source_year_mismatch" in codes([source(year="2024")], [manifest_row()])


def test_multi_file_source_needs_distinct_parts():
    a, b = manifest_row(PATH, "a" * 64), manifest_row(PATH + "2", "b" * 64)
    assert "multi_file_source_needs_parts" in codes([source()], [a, b])
    a, b = (r.model_copy(update={"source_part": "same"}) for r in (a, b))
    assert "duplicate_source_part" in codes([source()], [a, b])
    a = a.model_copy(update={"source_part": "one"})
    assert codes([source()], [a, b]) == set()


def make_pdf(tmp_path, name="x.pdf", blob=b"%PDF-content"):
    root = tmp_path
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / name).write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    return root, manifest_row(f"data/{name}", sha)


def test_resolve_by_hash_survives_a_rename(tmp_path):
    root, row = make_pdf(tmp_path, "renamed.pdf")
    path, found = resolve_pdf_by_sha256(root, row.sha256, [row])
    assert path.name == "renamed.pdf" and found.source_id == "test-2025"


def test_resolve_rejects_unknown_ambiguous_missing_and_changed(tmp_path):
    root, row = make_pdf(tmp_path)
    with pytest.raises(LookupError):
        resolve_pdf_by_sha256(root, "f" * 64, [row])
    twin = row.model_copy(update={"new_path": "data/twin.pdf"})
    with pytest.raises(ValueError, match="several"):
        resolve_pdf_by_sha256(root, row.sha256, [row, twin])
    with pytest.raises(ValueError, match="missing"):
        resolve_pdf_by_sha256(root, twin.sha256, [twin])
    (root / "data" / "x.pdf").write_bytes(b"edited")
    with pytest.raises(ValueError, match="changed"):
        resolve_pdf_by_sha256(root, row.sha256, [row])


def db(meta, ident="id-1"):
    return {"id": ident, "source_metadata": meta}


def test_reconcile_flags_stale_filename_and_missing_source_id():
    row = manifest_row(PATH, "a" * 64)
    meta = {"sha256": "a" * 64, "filename": "old-name.pdf", "doi": "10.1000/abc"}
    report = reconcile_db_sources([db(meta)], [row], [source()])
    assert report[0]["matched_source_id"] == "test-2025"
    assert set(report[0]["flags"]) == {"stale_filename", "no_source_id"}


def test_reconcile_clean_match_has_no_flags():
    row = manifest_row(PATH, "a" * 64)
    meta = {"sha256": "a" * 64, "filename": PATH.split("/")[-1],
            "doi": "10.1000/abc", "source_id": "test-2025"}
    assert reconcile_db_sources([db(meta)], [row], [source()])[0]["flags"] == []


def test_reconcile_flags_unknown_hash_missing_hash_and_doi_conflict():
    row = manifest_row(PATH, "a" * 64)
    report = reconcile_db_sources(
        [db({"sha256": "b" * 64}, "1"), db({}, "2"),
         db({"sha256": "a" * 64, "filename": PATH.split("/")[-1],
             "doi": "10.9999/other", "source_id": "x"}, "3")],
        [row], [source()])
    assert [r["flags"] for r in report] == [
        ["unknown_hash"], ["no_sha256"], ["doi_differs"]]


# Real tracked files (CSVs are tracked even though the PDFs are not).
def test_tracked_registry_is_consistent_with_tracked_manifest():
    rows = load_manifest(REPO / "data" / "MANIFEST.csv")
    sources = load_sources(REPO / "data" / "SOURCES.csv")
    assert validate_sources(sources, rows) == []
    assert len(sources) == 12 and len(rows) == 14


def test_compiled_dang_study_is_registered_with_matching_doi():
    study = json.loads(
        (REPO / "research/evidence/dang_2025_durian.json").read_text("utf-8"))
    registry = {s.source_id: s for s in
                load_sources(REPO / "data" / "SOURCES.csv")}
    entry = registry[study["source"]["source_key"]]
    assert entry.doi == study["source"]["doi"]
    assert entry.title == study["source"]["title"]


# Pins the identifiers verified against page text or Crossref records so
# an accidental edit of SOURCES.csv shows up as a test failure.
def test_verified_identifiers_are_pinned():
    registry = {s.source_id: s for s in
                load_sources(REPO / "data" / "SOURCES.csv")}
    assert registry["khcn-nnmt-2025-07-musang-king-npk"].doi == (
        "10.71254/nn5cqx48")
    assert registry["jad-24-3-cai-lay-durian-soil"].doi == (
        "10.52997/jad.2.03.2025")
    assert registry["tswj-2026-1153166"].doi == "10.1155/tswj/1153166"
    assert registry["doa-my-durian-package-2012"].isbn == "978-983-047-170-9"
    assert registry["doa-my-durian-package-2024"].isbn == "978-983-047-329-1"
    assert registry["id-moa-arabica-gap-postharvest-2019"].isbn == (
        "978-602-9292-40-4")
    assert registry["fao-lao-arabica-coffee-manual-2005"].isbn == (
        "974-7946-78-5")
    assert registry["ph-da-rfo12-coffee-guide-undated"].year == "undated"
    # Unresolved identity relations must stay flagged, not silently merged.
    assert "unresolved" in registry["doa-my-durian-package-2024"].concerns
