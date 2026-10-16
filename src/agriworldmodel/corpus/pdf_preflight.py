from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from pydantic import BaseModel
from pypdf import PdfReader

# Thresholds were fixed before the first audit run. They are heuristic
# triage values, not validated detectors.
NEAR_EMPTY_CHARS = 40
LOW_DENSITY_MEAN_CHARS = 150
LEGACY_TOKEN_FRACTION = 0.02
LEGACY_MIN_TOKENS = 20
FRONT_MATTER_PAGES = 5
FRONT_MATTER_MIN_CHARS = 200
FRONT_MATTER_SLICE = 100

# Legacy Vietnamese font encodings (e.g. TCVN3) corrupt text in two ways.
# Titles show Latin-1 symbols wedged between ASCII letters ("N«ng", "vµ");
# excluded on purpose: soft hyphen and ¬ (hyphenation), degree/plus-minus/
# powers, and the multiplication sign (the "Ca x Mg" factorial notation).
# Body text shows digits/punctuation inside words ("Tr8Gng", "h0c").
# A digit counts only beside a lowercase letter, so all-caps chemical
# formulas (K2O, P2O5, N2O) are not mistaken for corruption; mixed-case
# ones such as "CO2e" still are. The second pattern was added after the
# first failed on the one known positive document, so its threshold is
# untested on other positives.
_LEGACY_TOKEN = re.compile(
    "[A-Za-z][¡-«®¯´-¶¸¿][A-Za-z]"
    r"|[A-Za-z][!#$&;:<=>?@\[\\\]^][A-Za-z]"
    r"|[a-z][0-9][A-Za-z]|[A-Z][0-9][a-z]"
)


class DocumentPreflight(BaseModel):
    pages: int = 0
    mean_chars_per_page: float = 0.0
    near_empty_pages: int = 0
    page_extraction_errors: int = 0
    legacy_token_fraction: float = 0.0
    front_matter_sha256: str | None = None
    flags: list[str] = []
    open_error: str | None = None


def legacy_encoding_score(text: str) -> tuple[int, float]:
    """Return (token count, fraction of tokens with a legacy signature)."""
    tokens = text.split()
    if not tokens:
        return 0, 0.0
    hits = sum(1 for token in tokens if _LEGACY_TOKEN.search(token))
    return len(tokens), hits / len(tokens)


# Maps an open failure onto a flag. A missing optional crypto backend is
# reported separately: the file may be fine, our toolchain cannot tell.
def classify_open_error(error: Exception) -> str:
    text = f"{type(error).__name__}: {error}"
    if "cryptography" in text or "DependencyError" in text:
        return "encrypted_unreadable"
    return "open_failed"


def _front_matter_hash(page_texts: list[str]) -> str | None:
    for text in page_texts[:FRONT_MATTER_PAGES]:
        normalized = " ".join(text.split())
        if len(normalized) >= FRONT_MATTER_MIN_CHARS:
            head = normalized[:FRONT_MATTER_SLICE].encode("utf-8")
            return hashlib.sha256(head).hexdigest()
    return None


def preflight_pdf(path: Path) -> DocumentPreflight:
    """Extraction-health metrics for one PDF. No OCR, no page rendering.

    Flags are triage hints ("suspected"), never reasons to drop a file.
    Only counts and a hash are kept, so no source text is reproduced.
    """
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        reader = PdfReader(path)
        page_count = len(reader.pages)
    except Exception as error:  # noqa: BLE001 - pypdf raises many types
        return DocumentPreflight(
            flags=[classify_open_error(error)],
            open_error=type(error).__name__,
        )

    # Stage 1: extract every page, tolerating per-page failures.
    texts, errors = [], 0
    for page in reader.pages:
        try:
            texts.append((page.extract_text() or "").strip())
        except Exception:  # noqa: BLE001 - counted, not hidden
            texts.append("")
            errors += 1

    # Stage 2: derive metrics and flags from the extracted text.
    total_chars = sum(len(t) for t in texts)
    near_empty = sum(1 for t in texts if len(t) < NEAR_EMPTY_CHARS)
    mean_chars = total_chars / page_count if page_count else 0.0
    tokens, fraction = legacy_encoding_score(" ".join(texts))
    flags = []
    if errors:
        flags.append("page_extraction_errors")
    if near_empty:
        flags.append("near_empty_pages")
    if mean_chars < LOW_DENSITY_MEAN_CHARS:
        flags.append("low_text_density")
    if tokens >= LEGACY_MIN_TOKENS and fraction >= LEGACY_TOKEN_FRACTION:
        flags.append("legacy_vietnamese_encoding_suspected")
    return DocumentPreflight(
        pages=page_count,
        mean_chars_per_page=round(mean_chars, 1),
        near_empty_pages=near_empty,
        page_extraction_errors=errors,
        legacy_token_fraction=round(fraction, 4),
        front_matter_sha256=_front_matter_hash(texts),
        flags=flags,
    )


# Documents whose opening text is identical are probably sections of one
# parent work. This is a hint to check bibliographic linkage, not proof.
def shared_front_matter(
    results: dict[str, DocumentPreflight],
) -> dict[str, list[str]]:
    by_hash: dict[str, list[str]] = {}
    for name, result in results.items():
        if result.front_matter_sha256:
            by_hash.setdefault(result.front_matter_sha256, []).append(name)
    return {
        name: sorted(set(group) - {name})
        for group in by_hash.values() if len(group) > 1
        for name in group
    }
