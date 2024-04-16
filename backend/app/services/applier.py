"""Execute an approved mapping plan against an uploaded table.

A plan names a source column and a transform from the registry for each
target column, so running one is a dictionary lookup and a function call
per cell -- no compilation, no evaluation, no dynamic attribute access.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass

from app.domain.schemas import MappingPlan
from app.services import transforms
from app.services.csv_reader import Table
from app.services.errors import MappingPlanError


@dataclass(slots=True)
class Compiled:
    """A validated plan: per target column, a source index and transform."""

    columns: list[str]
    steps: list[tuple[int | None, transforms.Transform, dict[str, str]]]
    warnings: list[str]


def compile_plan(plan: MappingPlan, table: Table) -> Compiled:
    """Check a plan against the uploaded table and resolve its lookups."""
    if not plan.mappings:
        raise MappingPlanError("The mapping plan is empty.")

    positions = {name: index for index, name in enumerate(table.columns)}
    columns: list[str] = []
    steps: list[tuple[int | None, transforms.Transform, dict[str, str]]] = []
    warnings: list[str] = []

    for mapping in plan.mappings:
        if mapping.target_column in columns:
            raise MappingPlanError(
                f"Target column '{mapping.target_column}' appears twice in the plan."
            )
        if mapping.transform not in transforms.REGISTRY:
            raise MappingPlanError(f"Unknown transform '{mapping.transform}'.")

        if mapping.source_column is None:
            warnings.append(
                f"'{mapping.target_column}' has no source column and will be blank."
            )
            index = None
        elif mapping.source_column not in positions:
            raise MappingPlanError(
                f"Source column '{mapping.source_column}' is not in the uploaded file."
            )
        else:
            index = positions[mapping.source_column]

        columns.append(mapping.target_column)
        steps.append((index, transforms.get(mapping.transform), mapping.options))

    return Compiled(columns=columns, steps=steps, warnings=warnings)


def iter_rows(compiled: Compiled, table: Table) -> Iterator[list[str]]:
    """Yield output rows one at a time, so a download never buffers."""
    for row in table.rows:
        yield [
            "" if index is None else transform(row[index] if index < len(row) else "", options)
            for index, transform, options in compiled.steps
        ]


def apply_plan(
    plan: MappingPlan, table: Table, limit: int | None = None, offset: int = 0
) -> tuple[Compiled, list[list[str]]]:
    """Run a plan and return one page of the result."""
    compiled = compile_plan(plan, table)
    rows: list[list[str]] = []
    for position, row in enumerate(iter_rows(compiled, table)):
        if position < offset:
            continue
        if limit is not None and len(rows) >= limit:
            break
        rows.append(row)
    return compiled, rows


def to_csv(compiled: Compiled, table: Table) -> Iterator[str]:
    """Stream the full result as CSV text chunks."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(compiled.columns)
    yield _drain(buffer)
    for row in iter_rows(compiled, table):
        writer.writerow(row)
        yield _drain(buffer)


def _drain(buffer: io.StringIO) -> str:
    text = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    return text
