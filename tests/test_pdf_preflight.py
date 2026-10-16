from pathlib import Path

from pypdf import PdfWriter

from agriworldmodel.corpus.pdf_preflight import (
    DocumentPreflight,
    classify_open_error,
    legacy_encoding_score,
    preflight_pdf,
    shared_front_matter,
)

# A visible title fragment from a legacy-encoded Vietnamese article
# ("Nông nghiệp và MÔI TRƯỜNG" as it extracts).
GARBLED = "N«ng nghiÖp vµ M¤I TR¦êNG Tr8Gng h0c nghi:p " * 12
CLEAN_VI = "Nông nghiệp và môi trường: nghiên cứu về sầu riêng " * 12
CLEAN_EN = (
    "Applied 2.5 kg K2O per tree (±0.4, 25 °C); 3 µg/L; Ca×Mg factorial; "
    "p<0.05; Ca2+ uptake; ¿qué? "
) * 12


def make_text_pdf(path: Path, text: str, pages: int = 1) -> None:
    """Write a minimal valid PDF whose pages each show `text` (Helvetica)."""
    body = f"BT /F1 9 Tf 20 700 Td ({text}) Tj ET".encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(pages))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
    for i in range(pages):
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {4 + 2 * i} 0 R /Resources << /Font << /F1 << "
            f"/Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>"
            .encode())
        objs.append(
            b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref))
    path.write_bytes(bytes(out))


def test_legacy_signature_detected_in_garbled_text():
    tokens, fraction = legacy_encoding_score(GARBLED)
    assert tokens >= 20 and fraction >= 0.02


def test_clean_vietnamese_and_scientific_text_not_flagged():
    for text in (CLEAN_VI, CLEAN_EN):
        _, fraction = legacy_encoding_score(text)
        assert fraction < 0.02, text[:40]


def test_empty_text_has_zero_score():
    assert legacy_encoding_score("") == (0, 0.0)


def test_readable_pdf_has_no_flags(tmp_path):
    pdf = tmp_path / "ok.pdf"
    make_text_pdf(pdf, "Durian trial report. " * 30, pages=2)
    result = preflight_pdf(pdf)
    assert result.pages == 2
    assert result.flags == []
    assert result.front_matter_sha256


def test_blank_pdf_flagged_near_empty_and_low_density(tmp_path):
    pdf = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    with pdf.open("wb") as handle:
        writer.write(handle)
    result = preflight_pdf(pdf)
    assert {"near_empty_pages", "low_text_density"} <= set(result.flags)
    assert result.front_matter_sha256 is None


def test_garbled_pdf_flagged_as_suspected_legacy_encoding(tmp_path):
    pdf = tmp_path / "garbled.pdf"
    make_text_pdf(pdf, GARBLED)
    assert "legacy_vietnamese_encoding_suspected" in preflight_pdf(pdf).flags


def test_unreadable_file_is_reported_not_raised(tmp_path):
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"this is not a pdf")
    result = preflight_pdf(pdf)
    assert result.flags == ["open_failed"] and result.open_error


def test_missing_crypto_backend_is_classified_separately():
    error = RuntimeError("cryptography>=3.1 is required for AES algorithm")
    assert classify_open_error(error) == "encrypted_unreadable"
    assert classify_open_error(ValueError("EOF marker not found")) == "open_failed"


def test_preflight_is_deterministic(tmp_path):
    pdf = tmp_path / "a.pdf"
    make_text_pdf(pdf, "Same text every run. " * 20)
    assert preflight_pdf(pdf) == preflight_pdf(pdf)


def test_shared_front_matter_links_only_matching_documents():
    same = DocumentPreflight(front_matter_sha256="h1")
    results = {
        "a": same, "b": same, "c": DocumentPreflight(front_matter_sha256="h2"),
        "d": DocumentPreflight(front_matter_sha256=None),
    }
    assert shared_front_matter(results) == {"a": ["b"], "b": ["a"]}
