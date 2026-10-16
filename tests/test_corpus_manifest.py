import csv
import hashlib

import pytest

from agriworldmodel.corpus.manifest import validate_corpus

COLUMNS = [
    "original_path", "new_path", "primary_topic", "subcategory",
    "secondary_themes", "region", "crop", "document_role", "year",
    "language", "sha256", "ambiguity_or_warning",
]
GOOD = (
    "data/techniques_research/fertilization/"
    "vietnam-test__durian__npk-trial__field-trial__2025.pdf"
)


def build_corpus(root, rows=None, duplicates=None, files=None):
    """Create a one-document corpus; `rows`/`files` override the defaults."""
    data = root / "data"
    data.mkdir()
    content = b"%PDF-fake"
    if files is None:
        files = {GOOD: content}
    for rel, blob in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    if rows is None:
        rows = [row(GOOD, content)]
    write_csv(data / "MANIFEST.csv", COLUMNS, rows)
    write_csv(data / "DUPLICATES.csv",
              ["duplicate_original", "same_as", "reason"], duplicates or [])


def row(path, content, **overrides):
    parts = path.split("/")
    base = {
        "original_path": f"old/{parts[-1]}", "new_path": path,
        "primary_topic": parts[1], "subcategory": parts[2],
        "secondary_themes": "", "region": "x", "crop": "durian",
        "document_role": "field trial", "year": "2025", "language": "en",
        "sha256": hashlib.sha256(content).hexdigest(),
        "ambiguity_or_warning": "",
    }
    return {**base, **overrides}


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def codes(root):
    return {issue.code for issue in validate_corpus(root)}


def test_consistent_corpus_has_no_issues(tmp_path):
    build_corpus(tmp_path)
    assert validate_corpus(tmp_path) == []


def test_hash_mismatch_is_reported(tmp_path):
    build_corpus(tmp_path, rows=[row(GOOD, b"different bytes")])
    assert codes(tmp_path) == {"sha_mismatch"}


def test_row_without_file_and_pdf_without_row(tmp_path):
    other = GOOD.replace("npk-trial", "other-trial")
    build_corpus(tmp_path, files={other: b"x"})
    assert codes(tmp_path) == {"row_without_file", "pdf_without_row"}


@pytest.mark.parametrize("bad_name", [
    "Vietnam-Test__durian__npk-trial__field-trial__2025.pdf",
    "vietnam-test__durian__npk-trial__2025.pdf",
    "vietnam-test__durian__npk-trial__field-trial__25.pdf",
    "vietnam test__durian__npk-trial__field-trial__2025.pdf",
])
def test_filename_convention_violations(tmp_path, bad_name):
    path = f"data/techniques_research/fertilization/{bad_name}"
    build_corpus(tmp_path, rows=[row(path, b"%PDF-fake")], files={path: b"%PDF-fake"})
    assert "filename_convention" in codes(tmp_path)


def test_folder_must_match_manifest_topic(tmp_path):
    build_corpus(tmp_path, rows=[row(GOOD, b"%PDF-fake", primary_topic="diseases")])
    assert codes(tmp_path) == {"folder_topic_mismatch"}


def test_year_must_match_filename(tmp_path):
    build_corpus(tmp_path, rows=[row(GOOD, b"%PDF-fake", year="2024")])
    assert codes(tmp_path) == {"year_mismatch"}


def test_duplicate_hash_and_duplicate_row(tmp_path):
    second = GOOD.replace("npk-trial", "copy-trial")
    content = b"%PDF-fake"
    build_corpus(
        tmp_path,
        rows=[row(GOOD, content), row(second, content), row(GOOD, content)],
        files={GOOD: content, second: content},
    )
    assert {"duplicate_hash", "duplicate_row"} <= codes(tmp_path)


def test_duplicate_record_must_name_known_canonical_original(tmp_path):
    build_corpus(tmp_path, duplicates=[{
        "duplicate_original": "old/copy.pdf", "same_as": "old/unknown.pdf",
        "reason": "SHA-256 identical",
    }])
    assert codes(tmp_path) == {"duplicate_unknown_canonical"}


def test_duplicate_record_must_not_still_be_listed(tmp_path):
    build_corpus(tmp_path, duplicates=[{
        "duplicate_original": f"old/{GOOD.split('/')[-1]}",
        "same_as": f"old/{GOOD.split('/')[-1]}", "reason": "SHA-256 identical",
    }])
    assert codes(tmp_path) == {"duplicate_still_listed"}
