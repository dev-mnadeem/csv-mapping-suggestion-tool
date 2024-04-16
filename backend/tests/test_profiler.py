"""Column profiling: type inference and sampling."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.csv_reader import read_csv
from app.services.profiler import detect_date_format, infer_type, profile_table


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["1", "2", "30"], "integer"),
        (["1.5", "2.0"], "decimal"),
        (["1,250", "980"], "integer"),
        (["$12.00", "$9.99"], "currency"),
        (["2023-01-02", "2024-12-31"], "date"),
        (["05/08/2023", "05/09/2023"], "date"),
        (["true", "false"], "boolean"),
        (["yes", "no"], "boolean"),
        (["Gold", "Silver"], "text"),
        (["", "  "], "empty"),
        (["AB-12345", "CD-67890"], "text"),
    ],
)
def test_infer_type(values: list[str], expected: str) -> None:
    assert infer_type(values) == expected


def test_detect_date_format() -> None:
    assert detect_date_format(["2023-01-02", "2024-12-31"]) == "%Y-%m-%d"
    assert detect_date_format(["not a date"]) is None


def test_profile_reports_counts_and_samples() -> None:
    settings = Settings(profile_sample_size=2)
    table = read_csv(b"plan,note\nGold,\nGold,x\nSilver,y\n", settings)
    plan, note = profile_table(table, settings)

    assert plan.name == "plan"
    assert plan.row_count == 3
    assert plan.non_empty_count == 3
    assert plan.distinct_count == 2
    assert plan.sample_values == ["Gold", "Silver"]
    assert note.non_empty_count == 2
