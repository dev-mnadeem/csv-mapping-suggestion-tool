"""Typed payloads exchanged between the API, the services and the client."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

InferredType = Literal["integer", "decimal", "currency", "date", "boolean", "text", "empty"]


class ColumnProfile(BaseModel):
    """What the service knows about one column of an uploaded table."""

    name: str
    index: int
    inferred_type: InferredType
    row_count: int
    non_empty_count: int
    distinct_count: int
    sample_values: list[str] = Field(default_factory=list)


class MappingCandidate(BaseModel):
    """One possible source column for a target column, with its score."""

    source_column: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    transform: str = "identity"
    transform_options: dict[str, str] = Field(default_factory=dict)
    signals: dict[str, float] = Field(default_factory=dict)


class ColumnSuggestion(BaseModel):
    """The chosen candidate for a target column plus the runners up."""

    target_column: str
    best: MappingCandidate | None = None
    alternatives: list[MappingCandidate] = Field(default_factory=list)


class TableSummary(BaseModel):
    """Everything the UI needs to describe an uploaded file."""

    filename: str
    encoding: str
    delimiter: str
    row_count: int
    truncated: bool
    columns: list[ColumnProfile]


class SuggestionResponse(BaseModel):
    """Result of ``POST /api/mappings/suggest``."""

    run_id: int | None = None
    suggester: str
    duration_ms: int
    source: TableSummary
    target: TableSummary
    suggestions: list[ColumnSuggestion]
    warnings: list[str] = Field(default_factory=list)


class ColumnMapping(BaseModel):
    """One line of a mapping plan: where a target column gets its value."""

    target_column: str
    source_column: str | None = None
    transform: str = "identity"
    options: dict[str, str] = Field(default_factory=dict)


class MappingPlan(BaseModel):
    """The full, user-approved mapping submitted back for execution."""

    mappings: list[ColumnMapping]


class ApplyResponse(BaseModel):
    """Result of ``POST /api/mappings/apply`` -- one page of output rows."""

    columns: list[str]
    rows: list[dict[str, str]]
    total_rows: int
    limit: int
    offset: int
    warnings: list[str] = Field(default_factory=list)


class TransformInfo(BaseModel):
    """A transform the client may put in a mapping plan."""

    name: str
    description: str
    options: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    """A stored suggestion run, as listed by ``GET /api/runs``."""

    id: int
    created_at: datetime
    suggester: str
    source_filename: str
    target_filename: str
    duration_ms: int
    matched_columns: int
    target_columns: int


class RunDetail(RunSummary):
    """A stored run including the suggestions it produced."""

    payload: dict[str, Any]


class Page(BaseModel):
    """A slice of a list endpoint."""

    total: int
    limit: int
    offset: int


class RunPage(Page):
    items: list[RunSummary]


class HealthResponse(BaseModel):
    """Liveness plus the facts a reviewer usually wants to see first."""

    status: Literal["ok"]
    version: str
    suggester: str
    llm_configured: bool
    max_upload_bytes: int
    max_rows: int
