"""Behaviour of the deterministic matcher."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.domain.schemas import ColumnProfile
from app.services.profiler import infer_type
from app.services.suggester.local import LocalMappingSuggester

SETTINGS = Settings()


def profile(name: str, values: list[str], index: int = 0) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        index=index,
        inferred_type=infer_type(values),
        row_count=len(values),
        non_empty_count=len([value for value in values if value.strip()]),
        distinct_count=len(set(values)),
        sample_values=values,
    )


def suggest(source: list[ColumnProfile], target: list[ColumnProfile]):
    return LocalMappingSuggester(SETTINGS).suggest(source, target)


def test_exact_name_match_is_certain() -> None:
    [result] = suggest([profile("city", ["Leeds"])], [profile("city", ["York"])])
    assert result.best is not None
    assert result.best.source_column == "city"
    assert result.best.confidence == 1.0


def test_abbreviation_is_resolved_through_the_synonym_table() -> None:
    [result] = suggest(
        [profile("Policy_No", ["AB-12345"]), profile("Department", ["Sales"])],
        [profile("PolicyNumber", ["ZZ99999"])],
    )
    assert result.best is not None
    assert result.best.source_column == "Policy_No"
    assert "synonym" in result.best.rationale or "same name" in result.best.rationale


def test_unrelated_target_gets_no_match() -> None:
    [result] = suggest(
        [profile("Department", ["Sales"])],
        [profile("ShippingWeightKg", ["1.2"])],
    )
    assert result.best is None


def test_a_source_column_is_used_at_most_once() -> None:
    source = [profile("name", ["Ann Lee"])]
    target = [profile("first_name", ["Ann"]), profile("last_name", ["Lee"])]
    results = suggest(source, target)
    used = [item.best.source_column for item in results if item.best]
    assert len(used) == len(set(used))


def test_alternatives_are_offered_for_an_ambiguous_column() -> None:
    source = [
        profile("Insurance_Plan", ["Gold Plan", "Silver Plan"]),
        profile("Insurance_Type", ["Gold", "Silver"]),
    ]
    [result] = suggest(source, [profile("Plan", ["Gold", "Silver"])])
    assert result.best is not None
    assert result.best.source_column == "Insurance_Plan"
    assert [item.source_column for item in result.alternatives] == ["Insurance_Type"]


def test_suggestions_keep_target_order() -> None:
    target = [profile("b", ["1"]), profile("a", ["2"])]
    results = suggest([profile("a", ["2"]), profile("b", ["1"])], target)
    assert [item.target_column for item in results] == ["b", "a"]


@pytest.mark.parametrize(
    ("source_values", "target_values", "expected"),
    [
        (["AB-12345"], ["ZZ99999"], "strip_separators"),
        (["Gold Plan"], ["Gold"], "first_token"),
        (["100.0"], ["100"], "to_integer"),
    ],
)
def test_transform_is_inferred(
    source_values: list[str], target_values: list[str], expected: str
) -> None:
    [result] = suggest(
        [profile("value", source_values)], [profile("value", target_values)]
    )
    assert result.best is not None
    assert result.best.transform == expected


def test_date_transform_carries_the_target_format() -> None:
    [result] = suggest(
        [profile("Date_of_Policy", ["05/08/2023", "05/09/2023"])],
        [profile("Date", ["2023-04-03", "2023-04-04"])],
    )
    assert result.best is not None
    assert result.best.transform == "to_date"
    assert result.best.transform_options == {"format": "%Y-%m-%d"}


def test_header_only_target_still_matches_on_names() -> None:
    [result] = suggest([profile("cust_email", ["a@b.test"])], [profile("CustomerEmail", [])])
    assert result.best is not None
    assert result.best.source_column == "cust_email"
