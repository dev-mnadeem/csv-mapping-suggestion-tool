"""The transform registry is the only code a mapping plan can run."""

from __future__ import annotations

import pytest

from app.services import transforms


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("identity", " Gold ", " Gold "),
        ("trim", "  Gold  ", "Gold"),
        ("upper", "gold", "GOLD"),
        ("lower", "GOLD", "gold"),
        ("title_case", "gold plan", "Gold Plan"),
        ("strip_separators", "CD-67890", "CD67890"),
        ("strip_separators", "GB 12 34 56", "GB123456"),
        ("first_token", "Gold Plan", "Gold"),
        ("last_token", "Gold Plan", "Plan"),
        ("digits_only", "+44 7700 900111", "447700900111"),
        ("to_integer", "100.0", "100"),
        ("to_integer", "$1,250.75", "1250"),
        ("to_integer", "not a number", ""),
        ("to_decimal", "£19.99", "19.99"),
    ],
)
def test_transform_values(name: str, value: str, expected: str) -> None:
    assert transforms.apply(name, value) == expected


def test_to_decimal_honours_places() -> None:
    assert transforms.apply("to_decimal", "19.999", {"places": "2"}) == "20.00"


def test_to_date_reformats() -> None:
    assert transforms.apply("to_date", "05/08/2023", {"format": "%Y-%m-%d"}) == "2023-05-08"


def test_to_date_on_an_unparsable_value_is_blank() -> None:
    assert transforms.apply("to_date", "sometime", {}) == ""


def test_constant_ignores_the_source_value() -> None:
    assert transforms.apply("constant", "anything", {"value": "GBP"}) == "GBP"


def test_unknown_transform_raises() -> None:
    with pytest.raises(KeyError):
        transforms.apply("exec", "1")


def test_catalogue_lists_every_transform() -> None:
    names = {item.name for item in transforms.catalogue()}
    assert names == set(transforms.REGISTRY)
    assert "to_date" in names
