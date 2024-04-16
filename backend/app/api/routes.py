"""HTTP surface. Routes parse, delegate and serialise -- nothing else."""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app import __version__
from app.api.deps import RepositoryDep, SettingsDep, SuggesterDep, load_table
from app.db.repository import to_detail, to_summary
from app.domain.schemas import (
    ApplyResponse,
    HealthResponse,
    MappingPlan,
    RunDetail,
    RunPage,
    SuggestionResponse,
    TableSummary,
    TransformInfo,
)
from app.services import transforms
from app.services.applier import compile_plan, iter_rows, to_csv
from app.services.csv_reader import Table
from app.services.errors import MappingPlanError, RunNotFoundError
from app.services.profiler import profile_table

router = APIRouter(prefix="/api")

PREVIEW_DEFAULT_LIMIT = 50
PREVIEW_MAX_LIMIT = 500
RESULT_FILENAME = "mapped.csv"


def summarise(filename: str, table: Table, settings: SettingsDep) -> TableSummary:
    """Describe a parsed upload for the client."""
    return TableSummary(
        filename=filename,
        encoding=table.encoding,
        delimiter=table.delimiter,
        row_count=table.row_count,
        truncated=table.truncated,
        columns=profile_table(table, settings),
    )


@router.get("/health", response_model=HealthResponse, tags=["service"])
def health(settings: SettingsDep) -> HealthResponse:
    """Liveness plus the configuration a caller needs to know about."""
    return HealthResponse(
        status="ok",
        version=__version__,
        suggester=settings.suggester_backend,
        llm_configured=bool(settings.openai_api_key),
        max_upload_bytes=settings.max_upload_bytes,
        max_rows=settings.max_rows,
    )


@router.get("/transforms", response_model=list[TransformInfo], tags=["mappings"])
def list_transforms() -> list[TransformInfo]:
    """Every transform a mapping plan may name."""
    return transforms.catalogue()


@router.post("/mappings/suggest", response_model=SuggestionResponse, tags=["mappings"])
async def suggest_mapping(
    settings: SettingsDep,
    suggester: SuggesterDep,
    repository: RepositoryDep,
    input_table: UploadFile = File(..., description="The CSV being mapped"),
    target_table: UploadFile = File(..., description="The schema to map onto"),
) -> SuggestionResponse:
    """Profile both files and propose a source column for each target column."""
    source_name, source_table = await load_table(input_table, settings)
    target_name, target_file = await load_table(target_table, settings)

    source_summary = summarise(source_name, source_table, settings)
    target_summary = summarise(target_name, target_file, settings)

    started = time.perf_counter()
    suggestions = suggester.suggest(source_summary.columns, target_summary.columns)
    duration_ms = int((time.perf_counter() - started) * 1000)

    response = SuggestionResponse(
        suggester=suggester.name,
        duration_ms=duration_ms,
        source=source_summary,
        target=target_summary,
        suggestions=suggestions,
        warnings=source_table.warnings + target_file.warnings,
    )
    response.run_id = repository.record(response).id
    return response


@router.post("/mappings/apply", tags=["mappings"], response_model=None)
async def apply_mapping(
    settings: SettingsDep,
    input_table: UploadFile = File(..., description="The CSV being mapped"),
    plan: str = Form(..., description="JSON mapping plan"),
    limit: int = Query(PREVIEW_DEFAULT_LIMIT, ge=1, le=PREVIEW_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    download: bool = Query(False, description="Stream the whole result as CSV"),
) -> ApplyResponse | StreamingResponse:
    """Run an approved plan and return a preview page, or the whole CSV."""
    _, table = await load_table(input_table, settings)
    mapping_plan = parse_plan(plan)
    compiled = compile_plan(mapping_plan, table)

    if download:
        return StreamingResponse(
            to_csv(compiled, table),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{RESULT_FILENAME}"'},
        )

    page = [
        dict(zip(compiled.columns, row, strict=True))
        for index, row in enumerate(iter_rows(compiled, table))
        if offset <= index < offset + limit
    ]
    return ApplyResponse(
        columns=compiled.columns,
        rows=page,
        total_rows=table.row_count,
        limit=limit,
        offset=offset,
        warnings=table.warnings + compiled.warnings,
    )


def parse_plan(raw: str) -> MappingPlan:
    """Decode the plan form field, reporting bad JSON as a plan error."""
    try:
        return MappingPlan.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise MappingPlanError(f"The mapping plan is not valid: {exc}") from exc


@router.get("/runs", response_model=RunPage, tags=["runs"])
def list_runs(
    settings: SettingsDep,
    repository: RepositoryDep,
    limit: int | None = Query(None, ge=1),
    offset: int = Query(0, ge=0),
) -> RunPage:
    """Stored suggestion runs, newest first."""
    page_size = min(limit or settings.runs_page_size, settings.runs_max_page_size)
    return RunPage(
        total=repository.count(),
        limit=page_size,
        offset=offset,
        items=[to_summary(run) for run in repository.list(page_size, offset)],
    )


@router.get("/runs/{run_id}", response_model=RunDetail, tags=["runs"])
def get_run(run_id: int, repository: RepositoryDep) -> RunDetail:
    """One stored run, including the suggestions it produced."""
    run = repository.get(run_id)
    if run is None:
        raise RunNotFoundError(run_id)
    return to_detail(run)
