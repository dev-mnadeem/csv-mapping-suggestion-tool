"""Shared fixtures: an isolated database and a configured test client."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings, get_settings  # noqa: E402
from app.db import session as db_session  # noqa: E402

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointed at a throwaway SQLite file."""
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """A TestClient whose app uses the throwaway database."""
    get_settings.cache_clear()
    db_session.reset_engine()
    original = Settings.model_config.get("env_file")
    Settings.model_config["env_file"] = None

    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    previous_url = db_session.get_settings
    db_session.get_settings = lambda: settings  # type: ignore[assignment]
    db_session.reset_engine()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        db_session.get_settings = previous_url  # type: ignore[assignment]
        db_session.reset_engine()
        Settings.model_config["env_file"] = original
        get_settings.cache_clear()


@pytest.fixture
def sample_files() -> tuple[bytes, bytes]:
    """The committed demo CSVs, as raw bytes."""
    return (
        (SAMPLE_DIR / "employee_policies.csv").read_bytes(),
        (SAMPLE_DIR / "target_schema.csv").read_bytes(),
    )
