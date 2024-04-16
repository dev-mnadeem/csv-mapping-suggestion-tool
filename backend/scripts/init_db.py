"""Create the database schema, and optionally load a demo run.

    python scripts/init_db.py             # schema only
    python scripts/init_db.py --demo      # schema plus one run from sample_data/

Replaces the SQLite file that used to be committed to the repository.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes import summarise
from app.config import get_settings
from app.db.repository import RunRepository
from app.db.session import get_session_factory, init_db
from app.domain.schemas import SuggestionResponse
from app.services.csv_reader import read_csv
from app.services.suggester import get_suggester

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def load_demo_run() -> int:
    """Run the sample files through the suggester and store the result."""
    settings = get_settings()
    source_path = SAMPLE_DIR / "employee_policies.csv"
    target_path = SAMPLE_DIR / "target_schema.csv"
    source = read_csv(source_path.read_bytes(), settings)
    target = read_csv(target_path.read_bytes(), settings)

    source_summary = summarise(source_path.name, source, settings)
    target_summary = summarise(target_path.name, target, settings)

    suggester = get_suggester(settings)
    started = time.perf_counter()
    suggestions = suggester.suggest(source_summary.columns, target_summary.columns)
    duration_ms = int((time.perf_counter() - started) * 1000)

    response = SuggestionResponse(
        suggester=suggester.name,
        duration_ms=duration_ms,
        source=source_summary,
        target=target_summary,
        suggestions=suggestions,
    )
    session = get_session_factory()()
    try:
        return RunRepository(session).record(response).id
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo", action="store_true", help="also store one run over sample_data/"
    )
    args = parser.parse_args()

    init_db()
    print(f"Schema ready at {get_settings().database_url}")
    if args.demo:
        run_id = load_demo_run()
        print(f"Stored demo run #{run_id}")


if __name__ == "__main__":
    main()
