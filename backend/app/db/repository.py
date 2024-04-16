"""Data access for suggestion runs. No SQL escapes this module."""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import SuggestionRun
from app.domain.schemas import RunDetail, RunSummary, SuggestionResponse


class RunRepository:
    """Reads and writes :class:`SuggestionRun` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, response: SuggestionResponse) -> SuggestionRun:
        """Persist a completed suggestion run and return it."""
        matched = sum(1 for item in response.suggestions if item.best is not None)
        run = SuggestionRun(
            suggester=response.suggester,
            source_filename=response.source.filename,
            target_filename=response.target.filename,
            source_columns=len(response.source.columns),
            target_columns=len(response.target.columns),
            matched_columns=matched,
            duration_ms=response.duration_ms,
            payload=response.model_dump_json(),
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    def count(self) -> int:
        """Total number of stored runs."""
        return self._session.scalar(select(func.count()).select_from(SuggestionRun)) or 0

    def list(self, limit: int, offset: int) -> list[SuggestionRun]:
        """One page of runs, newest first."""
        statement = (
            select(SuggestionRun)
            .order_by(SuggestionRun.created_at.desc(), SuggestionRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(statement))

    def get(self, run_id: int) -> SuggestionRun | None:
        """A single run by id, or ``None``."""
        return self._session.get(SuggestionRun, run_id)


def to_summary(run: SuggestionRun) -> RunSummary:
    """Map a row onto the list DTO."""
    return RunSummary(
        id=run.id,
        created_at=run.created_at,
        suggester=run.suggester,
        source_filename=run.source_filename,
        target_filename=run.target_filename,
        duration_ms=run.duration_ms,
        matched_columns=run.matched_columns,
        target_columns=run.target_columns,
    )


def to_detail(run: SuggestionRun) -> RunDetail:
    """Map a row onto the detail DTO, re-inflating the stored payload."""
    return RunDetail(
        **to_summary(run).model_dump(),
        payload=json.loads(run.payload),
    )
