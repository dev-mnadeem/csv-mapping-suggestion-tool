"""Running an approved plan over an uploaded table."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.domain.schemas import ColumnMapping, MappingPlan
from app.services.applier import apply_plan, compile_plan, to_csv
from app.services.csv_reader import read_csv
from app.services.errors import MappingPlanError

SETTINGS = Settings()
CSV = b"Policy_No,Monthly_Premium,Insurance_Plan\nAB-12345,100.0,Gold Plan\nCD-67890,50.0,Silver Plan\n"


def plan(*mappings: ColumnMapping) -> MappingPlan:
    return MappingPlan(mappings=list(mappings))


def test_applies_transforms_per_column() -> None:
    table = read_csv(CSV, SETTINGS)
    compiled, rows = apply_plan(
        plan(
            ColumnMapping(
                target_column="PolicyNumber",
                source_column="Policy_No",
                transform="strip_separators",
            ),
            ColumnMapping(
                target_column="Premium",
                source_column="Monthly_Premium",
                transform="to_integer",
            ),
            ColumnMapping(
                target_column="Plan",
                source_column="Insurance_Plan",
                transform="first_token",
            ),
        ),
        table,
    )
    assert compiled.columns == ["PolicyNumber", "Premium", "Plan"]
    assert rows == [["AB12345", "100", "Gold"], ["CD67890", "50", "Silver"]]


def test_unmapped_target_column_is_blank_and_warns() -> None:
    table = read_csv(CSV, SETTINGS)
    compiled, rows = apply_plan(
        plan(ColumnMapping(target_column="Notes", source_column=None)), table
    )
    assert rows == [[""], [""]]
    assert compiled.warnings == ["'Notes' has no source column and will be blank."]


def test_pagination_slices_the_result() -> None:
    table = read_csv(CSV, SETTINGS)
    _, rows = apply_plan(
        plan(ColumnMapping(target_column="P", source_column="Policy_No")),
        table,
        limit=1,
        offset=1,
    )
    assert rows == [["CD-67890"]]


def test_unknown_source_column_is_rejected() -> None:
    table = read_csv(CSV, SETTINGS)
    with pytest.raises(MappingPlanError, match="not in the uploaded file"):
        compile_plan(plan(ColumnMapping(target_column="X", source_column="nope")), table)


def test_unknown_transform_is_rejected() -> None:
    table = read_csv(CSV, SETTINGS)
    with pytest.raises(MappingPlanError, match="Unknown transform"):
        compile_plan(
            plan(
                ColumnMapping(
                    target_column="X", source_column="Policy_No", transform="os.system"
                )
            ),
            table,
        )


def test_duplicate_target_column_is_rejected() -> None:
    table = read_csv(CSV, SETTINGS)
    with pytest.raises(MappingPlanError, match="appears twice"):
        compile_plan(
            plan(
                ColumnMapping(target_column="X", source_column="Policy_No"),
                ColumnMapping(target_column="X", source_column="Monthly_Premium"),
            ),
            table,
        )


def test_empty_plan_is_rejected() -> None:
    table = read_csv(CSV, SETTINGS)
    with pytest.raises(MappingPlanError, match="empty"):
        compile_plan(plan(), table)


def test_csv_output_quotes_embedded_delimiters() -> None:
    table = read_csv(b'name\n"Doe, John"\n', SETTINGS)
    compiled = compile_plan(
        plan(ColumnMapping(target_column="EmployeeName", source_column="name")), table
    )
    output = "".join(to_csv(compiled, table))
    assert output == 'EmployeeName\r\n"Doe, John"\r\n'
