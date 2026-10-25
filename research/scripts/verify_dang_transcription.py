"""Check the Dang build inputs against the local source PDF (pypdf).

    python research/scripts/verify_dang_transcription.py [--write-digest]

Needs the third-party PDF, which is not tracked in Git; it is located by
SHA-256 through data/MANIFEST.csv. Exit code 1 on any mismatch.
"""
import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from agriworldmodel.compiled_evidence.dang_2025_verify import (
    compare_inputs,
    extract_printed,
    printed_digest,
)
from agriworldmodel.corpus.sources import resolve_pdf_by_sha256

DANG_SHA256 = (
    "5e8a648d3694d60fa1143a14246a0385cb93c4ce9e91ff315ffd6d5ec058eb0e")
INPUTS = Path("research/evidence/dang_2025")
DIGEST = INPUTS / "pdf_extraction.sha256"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-digest", action="store_true",
                        help="record the extraction digest (0 mismatches only)")
    args = parser.parse_args()

    pdf, _ = resolve_pdf_by_sha256(Path("."), DANG_SHA256)
    extracted = extract_printed(pdf)
    report = compare_inputs(INPUTS, extracted)
    print(f"cells={report['cells']} markers={report['markers']} "
          f"correlations={report['correlations']} "
          f"mismatches={len(report['mismatches'])}")
    for line in report["mismatches"]:
        print("  ", line)
    if args.write_digest and not report["mismatches"]:
        digest = printed_digest(extracted)
        header = (f"# pypdf {version('pypdf')} extraction of PDF sha256 "
                  f"{DANG_SHA256}\n")
        body = "".join(f"{k} {v}\n" for k, v in digest.items())
        DIGEST.write_text(header + body, encoding="utf-8", newline="\n")
        print(f"wrote {DIGEST}")
    return 1 if report["mismatches"] else 0


if __name__ == "__main__":
    sys.exit(main())
