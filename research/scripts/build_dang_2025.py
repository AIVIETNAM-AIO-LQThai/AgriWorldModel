"""Build the Dang 2025 compiled study from version-controlled inputs.

    python research/scripts/build_dang_2025.py --out <path>
    python research/scripts/build_dang_2025.py --check

--check rebuilds in memory and fails (exit 1) if the committed artifact
differs by even one byte (line endings are compared as LF).
"""
import argparse
import hashlib
import sys
from pathlib import Path

from agriworldmodel.compiled_evidence.dang_2025_build import (
    build_study,
    render_json,
    write_canonical,
)

DEFAULT_INPUTS = Path("research/evidence/dang_2025")
DEFAULT_ARTIFACT = Path("research/evidence/dang_2025_durian.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path, help="write the built JSON here")
    group.add_argument("--check", action="store_true",
                       help="compare a fresh build with --artifact")
    args = parser.parse_args()

    study = build_study(args.inputs)
    if args.out:
        data = write_canonical(study, args.out)
        print(f"built {args.out} sha256={hashlib.sha256(data).hexdigest()}")
        return 0

    built = render_json(study).encode("utf-8")
    committed = args.artifact.read_bytes().replace(b"\r\n", b"\n")
    same = built == committed
    print(f"build sha256={hashlib.sha256(built).hexdigest()[:16]} "
          f"artifact sha256={hashlib.sha256(committed).hexdigest()[:16]} "
          f"-> {'identical' if same else 'DIFFERENT'}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
