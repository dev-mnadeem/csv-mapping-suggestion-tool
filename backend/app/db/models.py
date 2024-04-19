"""The one persisted table: a log of suggestion runs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for the application's tables."""


def utcnow() -> datetime:
    return datetime.now(UTC)


class SuggestionRun(Base):
    """One call to the suggester, kept so results can be reviewed later.

    The full response is stored as JSON text rather than as a second
    table of rows: nothing queries inside it, and keeping it whole means
    a run can be replayed exactly as it was returned.
    """

    __tablename__ = "suggestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    suggester: Mapped[str] = mapped_column(String(32), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    target_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_columns: Mapped[int] = mapped_column(Integer, nullable=False)
    target_columns: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_columns: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


# The list endpoint always sorts newest first; without this index SQLite
# sorts the whole table on every page request.
Index("ix_suggestion_runs_created_at", SuggestionRun.created_at.desc())
