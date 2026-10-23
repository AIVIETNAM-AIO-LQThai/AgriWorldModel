from __future__ import annotations

import logging
from pathlib import Path
from statistics import median
from typing import Any

from pypdf import PdfReader

from agriworldmodel.corpus.manifest import ManifestRow
from agriworldmodel.corpus.pdf_preflight import legacy_encoding_score

# Pages with fewer extracted characters than this are "low text". This is a
# coverage heuristic only: covers, dividers and figure pages are legitimately
# short, so it is not a failure definition.
LOW_TEXT_CHARS = 100


def sample_pages(page_count: int) -> list[int]:
    """Deterministic 1-based sample: first, middle (n // 2 + 1) and last."""
    if page_count < 1:
        return []
    return sorted({1, page_count // 2 + 1, page_count})


def page_texts(path: Path) -> tuple[list[str] | None, int]:
    """Per-page stripped text and the number of pages that raised.

    Returns (None, 0) when the file cannot be opened by this parser.
    """
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        reader = PdfReader(path)
        pages = list(reader.pages)
    except Exception:  # noqa: BLE001 - pypdf raises many types
        return None, 0
    texts, errors = [], 0
    for page in pages:
        try:
            texts.append((page.extract_text() or "").strip())
        except Exception:  # noqa: BLE001 - counted, not hidden
            texts.append("")
            errors += 1
    return texts, errors


def _document_record(root: Path, row: ManifestRow) -> dict[str, Any]:
    texts, errors = page_texts(root / row.new_path)
    record: dict[str, Any] = {
        "path": row.new_path, "sha256": row.sha256,
        "primary_topic": row.primary_topic,
    }
    if texts is None:
        return {**record, "open_status": "unreadable_by_pypdf", "pages": None}
    sample = sample_pages(len(texts))
    return {
        **record, "open_status": "ok", "pages": len(texts),
        "pages_low_text": sum(len(t) < LOW_TEXT_CHARS for t in texts),
        "pages_extraction_error": errors,
        "median_chars_per_page": median(len(t) for t in texts),
        "sample_pages": sample,
        "sample_chars": [len(texts[p - 1]) for p in sample],
        # Detector signal on the page, not a fidelity judgment. The token
        # count is kept because a fraction over a handful of tokens (a short
        # figure page) is not meaningful.
        "sample_tokens": [len(texts[p - 1].split()) for p in sample],
        "sample_legacy_token_fraction": [
            round(legacy_encoding_score(texts[p - 1])[1], 4) for p in sample],
    }


def summarize_pages(root: Path, rows: list[ManifestRow]) -> dict[str, Any]:
    """Page-level extraction metrics per document and per document type.

    Rates use readable documents only; unreadable ones are counted apart so
    an open failure is never mixed into a page-level low-text rate.
    """
    documents = [_document_record(root, row) for row in
                 sorted(rows, key=lambda r: r.new_path)]
    by_topic: dict[str, dict[str, Any]] = {}
    for doc in documents:
        agg = by_topic.setdefault(doc["primary_topic"], {
            "documents": 0, "documents_unreadable": 0,
            "pages": 0, "pages_low_text": 0})
        agg["documents"] += 1
        if doc["open_status"] != "ok":
            agg["documents_unreadable"] += 1
            continue
        agg["pages"] += doc["pages"]
        agg["pages_low_text"] += doc["pages_low_text"]
    for agg in by_topic.values():
        agg["low_text_fraction"] = (
            round(agg["pages_low_text"] / agg["pages"], 4)
            if agg["pages"] else None)
    return {
        "definitions": {
            "parser": "pypdf (project environment)",
            "low_text_chars": LOW_TEXT_CHARS,
            "sample_rule": "pages 1, n // 2 + 1 and n (1-based, deduplicated)",
            "note": "low-text is not a failure; unreadable documents are "
                    "excluded from page rates",
        },
        "by_topic": dict(sorted(by_topic.items())),
        "documents": documents,
    }
