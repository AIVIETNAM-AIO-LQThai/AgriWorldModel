"""Page-level extraction metrics (pypdf only, read-only).

    python research/scripts/page_extraction_metrics.py \
        --root . --out research/corpus/page_extraction_metrics.json

Output is sorted and timestamp-free so reruns are byte-identical.
"""
import argparse
import json
import sys
from pathlib import Path

from agriworldmodel.corpus.manifest import load_manifest
from agriworldmodel.corpus.page_metrics import summarize_pages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    report = summarize_pages(root, load_manifest(root / "data/MANIFEST.csv"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"{len(report['documents'])} documents -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
