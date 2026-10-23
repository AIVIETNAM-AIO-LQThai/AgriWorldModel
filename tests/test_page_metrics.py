import csv
import json
from pathlib import Path

import pytest

from agriworldmodel.corpus.manifest import ManifestRow, load_manifest
from agriworldmodel.corpus.page_metrics import (
    LOW_TEXT_CHARS,
    page_texts,
    sample_pages,
    summarize_pages,
)
from tests.test_pdf_preflight import make_text_pdf

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "research" / "corpus"
FINDINGS = {
    "corrupt_confirmed", "corrupt_reported_external", "signal_only",
    "anomalous_parser_output", "page_attribution_error", "layout_risk",
    "no_issue_reported", "not_assessed",
}


@pytest.mark.parametrize("n, expected", [
    (0, []), (1, [1]), (2, [1, 2]), (3, [1, 2, 3]), (10, [1, 6, 10]),
    (11, [1, 6, 11]), (101, [1, 51, 101]), (370, [1, 186, 370]),
])
def test_sample_rule(n, expected):
    assert sample_pages(n) == expected


def row(path, topic="x", sha="a" * 64) -> ManifestRow:
    return ManifestRow(
        original_path="o.pdf", new_path=path, primary_topic=topic,
        subcategory="y", secondary_themes="", region="", crop="",
        document_role="", year="2025", language="en", sha256=sha,
        ambiguity_or_warning="", source_id="s", source_part="")


def test_unreadable_pdf_is_counted_apart_from_page_rates(tmp_path):
    good, bad = tmp_path / "good.pdf", tmp_path / "bad.pdf"
    make_text_pdf(good, "Plenty of readable durian text. " * 12, pages=3)
    bad.write_bytes(b"not a pdf")
    report = summarize_pages(
        tmp_path, [row("good.pdf", "t", "b" * 64), row("bad.pdf", "t")])
    agg = report["by_topic"]["t"]
    assert agg["documents"] == 2 and agg["documents_unreadable"] == 1
    assert agg["pages"] == 3 and agg["pages_low_text"] == 0
    assert agg["low_text_fraction"] == 0.0
    statuses = {d["path"]: d["open_status"] for d in report["documents"]}
    assert statuses["bad.pdf"] == "unreadable_by_pypdf"


def test_low_text_pages_are_counted(tmp_path):
    pdf = tmp_path / "short.pdf"
    make_text_pdf(pdf, "tiny", pages=2)
    texts, errors = page_texts(pdf)
    assert errors == 0 and all(len(t) < LOW_TEXT_CHARS for t in texts)
    assert summarize_pages(tmp_path, [row("short.pdf")])["by_topic"]["x"][
        "pages_low_text"] == 2


def test_summary_is_deterministic(tmp_path):
    make_text_pdf(tmp_path / "a.pdf", "Same text every run. " * 20, pages=4)
    rows = [row("a.pdf")]
    assert summarize_pages(tmp_path, rows) == summarize_pages(tmp_path, rows)


# Tracked evidence files: internally consistent and tied to the manifest.
def committed_metrics():
    return json.loads(
        (CORPUS / "page_extraction_metrics.json").read_text("utf-8"))


def test_committed_metrics_cover_every_manifest_document():
    manifest = load_manifest(REPO / "data" / "MANIFEST.csv")
    docs = {d["path"]: d for d in committed_metrics()["documents"]}
    assert set(docs) == {r.new_path for r in manifest}
    assert all(docs[r.new_path]["sha256"] == r.sha256 for r in manifest)


def test_committed_topic_totals_equal_document_sums():
    report = committed_metrics()
    for topic, agg in report["by_topic"].items():
        docs = [d for d in report["documents"] if d["primary_topic"] == topic]
        ok = [d for d in docs if d["open_status"] == "ok"]
        assert agg["documents"] == len(docs)
        assert agg["documents_unreadable"] == len(docs) - len(ok)
        assert agg["pages"] == sum(d["pages"] for d in ok)
        assert agg["pages_low_text"] == sum(d["pages_low_text"] for d in ok)


def test_judgments_cover_each_sampled_page_with_valid_labels():
    manifest = {r.sha256: r for r in
                load_manifest(REPO / "data" / "MANIFEST.csv")}
    with (CORPUS / "visual_sample_judgments.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 42 and {r["sha256"] for r in rows} <= set(manifest)
    assert {r["text_fidelity_finding"] for r in rows} <= FINDINGS
    assert {r["renders_ok"] for r in rows} <= {"yes", "no"}
    seen = {(r["sha256"], int(r["page"])) for r in rows}
    assert len(seen) == len(rows), "duplicate judgment rows"
    for doc in committed_metrics()["documents"]:
        if doc["open_status"] == "ok":
            for page in doc["sample_pages"]:
                assert (doc["sha256"], page) in seen, (doc["path"], page)


def test_external_spotcheck_hashes_match_manifest_and_skip_comments():
    manifest = {r.new_path: r.sha256 for r in
                load_manifest(REPO / "data" / "MANIFEST.csv")}
    lines = (CORPUS / "external_spotcheck_preflight.csv").read_text(
        "utf-8").splitlines()
    assert lines[0].startswith("# ")
    rows = list(csv.DictReader(l for l in lines if not l.startswith("#")))
    assert {r["path"]: r["sha256"] for r in rows} == manifest
