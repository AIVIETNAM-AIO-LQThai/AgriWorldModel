"""Read-only report: do database source rows resolve to the manifest?

    python research/scripts/check_db_source_identity.py

Only SELECTs are issued; nothing is written. A 5 s connect timeout turns
the localhost -> ::1 stall into a quick, explained failure.
"""
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from agriworldmodel.config import settings
from agriworldmodel.corpus.manifest import load_manifest
from agriworldmodel.corpus.sources import load_sources, reconcile_db_sources


def fetch_db_sources() -> list[dict]:
    engine = create_engine(
        settings.database_url, connect_args={"connect_timeout": 5})
    query = text(
        "select id, title, url, source_metadata from evidence_source "
        "order by id")
    with engine.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(query)]


def main() -> int:
    root = Path(".")
    rows = load_manifest(root / "data/MANIFEST.csv")
    sources = load_sources(root / "data/SOURCES.csv")
    try:
        db_rows = fetch_db_sources()
    except Exception as error:  # noqa: BLE001 - report, don't traceback
        print(f"database unreachable: {type(error).__name__}. If the host in "
              "DATABASE_URL is 'localhost', try 127.0.0.1.")
        return 2
    report = reconcile_db_sources(db_rows, rows, sources)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
