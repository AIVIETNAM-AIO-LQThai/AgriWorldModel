from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pydantic import BaseModel

# <region>__<crop>__<subject>__<document-role>__<year>.pdf, where each
# field is lowercase words joined by single hyphens.
_FIELD = r"[a-z0-9]+(?:-[a-z0-9]+)*"
FILENAME_RE = re.compile(rf"^{_FIELD}(?:__{_FIELD}){{3}}__(\d{{4}}|undated)\.pdf$")


class ManifestRow(BaseModel):
    original_path: str
    new_path: str
    primary_topic: str
    subcategory: str
    secondary_themes: str
    region: str
    crop: str
    document_role: str
    year: str
    language: str
    sha256: str
    ambiguity_or_warning: str
    # Link to the bibliographic work in SOURCES.csv; source_part tells
    # apart several files (e.g. excerpts) of the same work.
    source_id: str
    source_part: str


@dataclass(frozen=True, order=True)
class CorpusIssue:
    code: str
    path: str
    detail: str


# utf-8-sig tolerates the BOM that the curated CSVs carry.
def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_manifest(path: Path) -> list[ManifestRow]:
    return [ManifestRow(**row) for row in _read_csv(path)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# Checks the naming convention and that the folder agrees with the
# row's topic/subcategory. A folder is a filing choice, not evidence of
# authority or study design, so no other meaning is read into it.
def _check_name_and_folder(row: ManifestRow) -> list[CorpusIssue]:
    issues = []
    parts = PurePosixPath(row.new_path).parts
    name = parts[-1]
    if not FILENAME_RE.match(name):
        issues.append(CorpusIssue(
            "filename_convention", row.new_path,
            "expected <region>__<crop>__<subject>__<role>__<year>.pdf"))
    elif name[:-4].rsplit("__", 1)[1] != row.year:
        issues.append(CorpusIssue(
            "year_mismatch", row.new_path,
            f"filename year differs from manifest year {row.year!r}"))
    if len(parts) != 4 or parts[1:3] != (row.primary_topic, row.subcategory):
        issues.append(CorpusIssue(
            "folder_topic_mismatch", row.new_path,
            f"expected data/{row.primary_topic}/{row.subcategory}/<file>"))
    return issues


# Duplicate records must name an original that the manifest knows as the
# canonical copy, and must not claim a copy that is still on disk.
def _check_duplicates(
    rows: list[ManifestRow], duplicates: list[dict[str, str]],
) -> list[CorpusIssue]:
    originals = {row.original_path for row in rows}
    on_disk = {row.new_path for row in rows}
    issues = []
    for record in duplicates:
        copy, canonical = record["duplicate_original"], record["same_as"]
        if canonical not in originals:
            issues.append(CorpusIssue(
                "duplicate_unknown_canonical", copy,
                f"same_as {canonical!r} is not a manifest original_path"))
        if copy in originals or copy in on_disk:
            issues.append(CorpusIssue(
                "duplicate_still_listed", copy,
                "listed as a duplicate but also present in the manifest"))
    return issues


def validate_corpus(
    repo_root: Path,
    manifest_path: Path | None = None,
    duplicates_path: Path | None = None,
) -> list[CorpusIssue]:
    """Return every identity problem; an empty list means consistent.

    Read-only: the PDFs are hashed but never modified. Hashes are the
    identity key, so paths are only checked for convention and presence.
    """
    data_dir = repo_root / "data"
    manifest_path = manifest_path or data_dir / "MANIFEST.csv"
    duplicates_path = duplicates_path or data_dir / "DUPLICATES.csv"
    rows = load_manifest(manifest_path)
    issues: list[CorpusIssue] = []

    # Stage 1: each manifest row against the file on disk.
    seen_paths: dict[str, int] = {}
    seen_hashes: dict[str, str] = {}
    for row in rows:
        seen_paths[row.new_path] = seen_paths.get(row.new_path, 0) + 1
        issues += _check_name_and_folder(row)
        if row.sha256 in seen_hashes:
            issues.append(CorpusIssue(
                "duplicate_hash", row.new_path,
                f"same sha256 as {seen_hashes[row.sha256]}"))
        seen_hashes.setdefault(row.sha256, row.new_path)
        pdf = repo_root / row.new_path
        if not pdf.is_file():
            issues.append(CorpusIssue(
                "row_without_file", row.new_path, "file not found"))
        elif sha256_file(pdf) != row.sha256:
            issues.append(CorpusIssue(
                "sha_mismatch", row.new_path, "disk hash differs from manifest"))
    issues += [
        CorpusIssue("duplicate_row", path, f"{count} manifest rows")
        for path, count in seen_paths.items() if count > 1
    ]

    # Stage 2: every PDF on disk must be accounted for by exactly one row.
    for pdf in sorted(data_dir.rglob("*.pdf")):
        rel = pdf.relative_to(repo_root).as_posix()
        if rel not in seen_paths:
            issues.append(CorpusIssue(
                "pdf_without_row", rel, "no manifest row"))

    issues += _check_duplicates(rows, _read_csv(duplicates_path))
    return sorted(issues)
