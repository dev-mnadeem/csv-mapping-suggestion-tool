"""Accuracy of the local matcher on the committed fixture cases.

The cases in ``tests/fixtures/mapping_cases`` are hand-written pairs of a
messy export and the schema it should land on, each with the mapping a
person would pick. They are a regression suite, not an independent
benchmark: the synonym and phrase tables were extended until these cases
passed. What the suite protects is that a change to scoring cannot
quietly break a mapping that used to work.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.schemas import ColumnProfile
from app.services.profiler import infer_type
from app.services.suggester.local import LocalMappingSuggester

CASE_DIR = Path(__file__).parent / "fixtures" / "mapping_cases"
CASE_FILES = sorted(CASE_DIR.glob("*.json"))
MIN_ACCURACY = 0.90

SETTINGS = Settings()


def to_profiles(columns: list[dict[str, list[str]]]) -> list[ColumnProfile]:
    """Build profiles straight from a fixture's column definitions."""
    return [
        ColumnProfile(
            name=str(column["name"]),
            index=index,
            inferred_type=infer_type(list(column["values"])),
            row_count=len(column["values"]),
            non_empty_count=len([value for value in column["values"] if value.strip()]),
            distinct_count=len(set(column["values"])),
            sample_values=list(column["values"]),
        )
        for index, column in enumerate(columns)
    ]


def run_case(case: dict) -> list[tuple[str, str | None, str | None]]:
    """Return ``(target, expected, predicted)`` for every target column."""
    suggestions = LocalMappingSuggester(SETTINGS).suggest(
        to_profiles(case["source"]), to_profiles(case["target"])
    )
    return [
        (
            item.target_column,
            case["expected"].get(item.target_column),
            item.best.source_column if item.best else None,
        )
        for item in suggestions
    ]


def test_fixture_cases_are_present() -> None:
    assert len(CASE_FILES) >= 5


@pytest.mark.parametrize("path", CASE_FILES, ids=lambda path: path.stem)
def test_every_expected_mapping_is_the_top_choice(path: Path) -> None:
    case = json.loads(path.read_text())
    misses = [
        (target, expected, predicted)
        for target, expected, predicted in run_case(case)
        if expected != predicted
    ]
    assert not misses, f"{path.stem}: {misses}"


def test_overall_top_one_accuracy(capsys: pytest.CaptureFixture[str]) -> None:
    total = 0
    correct = 0
    for path in CASE_FILES:
        case = json.loads(path.read_text())
        for _, expected, predicted in run_case(case):
            total += 1
            correct += expected == predicted

    with capsys.disabled():
        print(f"\nlocal matcher top-1: {correct}/{total} = {correct / total:.1%}")
    assert correct / total >= MIN_ACCURACY
