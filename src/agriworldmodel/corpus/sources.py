from __future__ import annotations

import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel

from agriworldmodel.corpus.manifest import (
    CorpusIssue,
    ManifestRow,
    _read_csv,
    load_manifest,
    sha256_file,
)

SOURCE_KINDS = {"journal_article", "monograph", "technical_guide"}
STUDY_DESIGNS = {
    "field_trial", "observational_survey", "guideline_or_review", "unknown",
}
DESIGN_STATUSES = {"reported_by_source", "curator_assessed", "unverified"}
SOURCE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
YEAR_RE = re.compile(r"^(\d{4}|undated)$")
ROLE_RE = re.compile(r"^[a-z][a-z -]*$")


class SourceRow(BaseModel):
    """One bibliographic work. Blank means unknown, never "not applicable"."""

    source_id: str
    title: str
    # Journal or series the work appears in (blank for stand-alone books).
    container_title: str
    source_kind: str
    study_design: str
    study_design_status: str
    # Publisher or formally issuing institution, not the authors' unit.
    issuing_body: str
    # "role: name; role: name" for sponsors, hosts, implementers etc.
    other_bodies: str
    # Jurisdiction of the issuing institution, not the study location.
    issuing_jurisdiction: str
    # Where the study ran, or where a guide is meant to apply.
    study_region: str
    year: str
    # Verbatim edition/printing wording, for comparing editions.
    edition_statement: str
    doi: str
    isbn: str
    url: str
    identifier_locator: str
    license: str
    license_locator: str
    unverified_fields: str
    concerns: str


def load_sources(path: Path) -> list[SourceRow]:
    return [SourceRow(**row) for row in _read_csv(path)]


# Field-level rules for one registry row. Identifiers and licences must
# say where they were read, so a reviewer can check them in the PDF.
def _check_source_fields(source: SourceRow) -> list[CorpusIssue]:
    sid, issues = source.source_id, []

    def add(code: str, detail: str) -> None:
        issues.append(CorpusIssue(code, sid, detail))

    if not SOURCE_ID_RE.match(sid):
        add("bad_source_id", "expected lowercase words joined by hyphens")
    if source.source_kind not in SOURCE_KINDS:
        add("bad_source_kind", source.source_kind)
    if source.study_design not in STUDY_DESIGNS:
        add("bad_study_design", source.study_design)
    if source.study_design_status not in DESIGN_STATUSES:
        add("bad_study_design_status", source.study_design_status)
    if not YEAR_RE.match(source.year):
        add("bad_year", source.year)
    if source.doi and not DOI_RE.match(source.doi):
        add("bad_doi", source.doi)
    if (source.doi or source.isbn) and not source.identifier_locator:
        add("identifier_without_locator", "DOI/ISBN needs a page locator")
    if source.license and not source.license_locator:
        add("license_without_locator", "licence needs a page locator")
    doi_url = source.url.startswith("https://doi.org/")
    if doi_url and source.url != f"https://doi.org/{source.doi}":
        add("doi_url_mismatch", source.url)
    entries = (e.strip() for e in source.other_bodies.split(";"))
    for entry in filter(None, entries):
        role, _, name = entry.partition(":")
        if not ROLE_RE.match(role.strip()) or not name.strip():
            add("bad_other_bodies", f"expected 'role: name', got {entry!r}")
    known = set(SourceRow.model_fields)
    for name in filter(None, source.unverified_fields.split(";")):
        if name not in known:
            add("unknown_unverified_field", name)
    return issues


def validate_sources(
    sources: list[SourceRow], rows: list[ManifestRow],
) -> list[CorpusIssue]:
    """Cross-check the registry against itself and the file manifest."""
    issues = [i for source in sources for i in _check_source_fields(source)]
    ids = Counter(source.source_id for source in sources)
    issues += [
        CorpusIssue("duplicate_source_id", sid, f"{n} registry rows")
        for sid, n in ids.items() if n > 1
    ]
    by_id = {source.source_id: source for source in sources}

    # Each file points at one known work whose year agrees with the row.
    files: dict[str, list[ManifestRow]] = {}
    for row in rows:
        files.setdefault(row.source_id, []).append(row)
        source = by_id.get(row.source_id)
        if source is None:
            issues.append(CorpusIssue(
                "manifest_unknown_source", row.new_path,
                f"source_id {row.source_id!r} not in SOURCES.csv"))
        elif source.year != row.year:
            issues.append(CorpusIssue(
                "source_year_mismatch", row.new_path,
                f"manifest year {row.year!r} vs source {source.year!r}"))

    # Several files of one work (excerpts) must be told apart by part.
    for sid in sorted(by_id):
        group = files.get(sid, [])
        if not group:
            issues.append(CorpusIssue(
                "source_without_files", sid, "no manifest row uses it"))
        if len(group) > 1:
            parts = [row.source_part for row in group]
            if not all(parts):
                issues.append(CorpusIssue(
                    "multi_file_source_needs_parts", sid,
                    "every file of a multi-file source needs a source_part"))
            elif len(set(parts)) != len(parts):
                issues.append(CorpusIssue(
                    "duplicate_source_part", sid, "repeated source_part"))
    return sorted(issues)


def resolve_pdf_by_sha256(
    repo_root: Path, sha256: str, rows: list[ManifestRow] | None = None,
) -> tuple[Path, ManifestRow]:
    """Locate a PDF by content hash, so renames cannot break ingestion.

    Raises LookupError for an unknown hash, ValueError when the hash is
    ambiguous or the file on disk no longer matches the manifest.
    """
    rows = rows if rows is not None else load_manifest(
        repo_root / "data" / "MANIFEST.csv")
    matches = [row for row in rows if row.sha256 == sha256]
    if not matches:
        raise LookupError(f"sha256 {sha256[:12]}... is not in the manifest")
    if len(matches) > 1:
        raise ValueError(f"sha256 {sha256[:12]}... appears in several rows")
    path = repo_root / matches[0].new_path
    if not path.is_file():
        raise ValueError(f"manifest file is missing: {matches[0].new_path}")
    if sha256_file(path) != sha256:
        raise ValueError(f"file content changed: {matches[0].new_path}")
    return path, matches[0]


# Compares database source rows (plain dicts, so no DB is needed here)
# with the manifest. A row is identified by its content hash; a stale
# filename is reported, never treated as a different document.
def reconcile_db_sources(
    db_rows: list[dict[str, Any]], rows: list[ManifestRow],
    sources: list[SourceRow],
) -> list[dict[str, Any]]:
    by_sha = {row.sha256: row for row in rows}
    doi_by_id = {source.source_id: source.doi for source in sources}
    report = []
    for db_row in db_rows:
        meta = db_row.get("source_metadata") or {}
        sha = meta.get("sha256")
        flags, manifest_row = [], by_sha.get(sha)
        if not sha:
            flags.append("no_sha256")
        elif manifest_row is None:
            flags.append("unknown_hash")
        else:
            if meta.get("filename") != PurePosixPath(
                    manifest_row.new_path).name:
                flags.append("stale_filename")
            registry_doi = doi_by_id.get(manifest_row.source_id, "")
            db_doi = meta.get("doi", "")
            if registry_doi and db_doi and registry_doi != db_doi:
                flags.append("doi_differs")
            if not meta.get("source_id"):
                flags.append("no_source_id")
        report.append({
            "db_id": str(db_row.get("id")),
            "matched_source_id": manifest_row.source_id if manifest_row else None,
            "flags": flags,
        })
    return report
