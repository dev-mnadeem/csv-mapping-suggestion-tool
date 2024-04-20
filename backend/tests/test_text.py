"""Name normalisation is where most of the matching signal comes from."""

from __future__ import annotations

import pytest

from app.services.suggester.text import (
    canonical_tokens,
    levenshtein,
    name_similarity,
    synonym_hits,
    token_overlap,
    value_shape,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Policy_No", ("policy", "number")),
        ("PolicyNumber", ("policy", "number")),
        ("policy no.", ("policy", "number")),
        ("EmpID", ("person", "identifier")),
        ("employee_id", ("person", "identifier")),
        ("Date_of_Policy", ("date", "policy")),
        ("PostalCode", ("postcode",)),
        ("zip_code", ("postcode",)),
        ("FullName", ("name",)),
        ("qty", ("quantity",)),
        ("Total Amount", ("amount", "amount")),
        ("address_line_1", ("address", "line", "1")),
    ],
)
def test_canonical_tokens(name: str, expected: tuple[str, ...]) -> None:
    assert canonical_tokens(name) == expected


def test_levenshtein() -> None:
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("same", "same") == 0
    assert levenshtein("", "abc") == 3


def test_identical_meaning_names_score_one() -> None:
    assert name_similarity("Policy_No", "PolicyNumber") == 1.0
    assert token_overlap("Policy_No", "PolicyNumber") == 1.0


def test_qualified_name_still_matches_its_base() -> None:
    assert name_similarity("Premium", "Monthly_Premium") > 0.6
    assert token_overlap("Date", "Date_of_Policy") == 0.75


def test_unrelated_names_score_low() -> None:
    assert name_similarity("Department", "PolicyNumber") < 0.35


def test_synonym_hits_report_the_matching_words() -> None:
    assert synonym_hits("Policy_No", "PolicyNumber") == [("no", "number")]
    assert synonym_hits("City", "City") == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("AB-12345", "A-9"),
        ("ZZ99999", "A9"),
        ("John Doe", "A A"),
        ("05/08/2023", "9/9/9"),
    ],
)
def test_value_shape(value: str, expected: str) -> None:
    assert value_shape(value) == expected
