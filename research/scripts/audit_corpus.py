"""Read-only corpus audit: manifest consistency + PDF extraction preflight.

    python research/scripts/audit_corpus.py \
        --root . --out research/corpus/extraction_preflight.json

Output is sorted and timestamp-free so reruns are byte-identical.
"""
import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

from agriworldmodel.corpus.manifest import load_manifest, validate_corpus
from agriworldmodel.corpus.pdf_preflight import (
    preflight_pdf,
    shared_front_matter,
)
from agriworldmodel.corpus.sources import load_sources, validate_sources


def build_report(root: Path) -> dict:
    rows = load_manifest(root / "data/MANIFEST.csv")
    manifest = {row.new_path: row for row in rows}
    sources = load_sources(root / "data/SOURCES.csv")
    issues = sorted(validate_corpus(root) + validate_sources(sources, rows))

    # Preflight every manifest PDF that exists; missing files are
    # already reported as manifest issues.
    results = {
        path: preflight_pdf(root / path)
        for path in sorted(manifest) if (root / path).is_file()
    }
    shared = shared_front_matter(results)
    documents = []
    for path, result in results.items():
        row = manifest[path]
        documents.append({
            "path": path,
            "sha256": row.sha256,
            "source_id": row.source_id,
            "source_part": row.source_part,
            "primary_topic": row.primary_topic,
            "document_role": row.document_role,
            "shared_front_matter_with": shared.get(path, []),
            **result.model_dump(),
        })
    return {
        "tool": {"pypdf": version("pypdf")},
        "manifest_issues": [vars(issue) for issue in issues],
        "documents": documents,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{len(report['documents'])} documents, "
          f"{len(report['manifest_issues'])} manifest issues -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
