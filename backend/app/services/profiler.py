"""Describe a parsed table's columns without loading a dataframe library.

The suggester works from these profiles rather than from raw rows, which
keeps the matching code independent of how the table arrived.
"""

from __future__ import annotations

import re
from datetime import datetime

from app.config import Settings
from app.domain.schemas import ColumnProfile
from app.services.csv_reader import Table

BOOLEAN_TOKENS = frozenset({"true", "false", "yes", "no", "y", "n", "t", "f", "0", "1"})

# Ordered widest-first so that "05/08/2023" is not read as "%d/%m/%Y" by
# accident when a "%m/%d/%Y" reading also parses -- ambiguity is reported
# as a date either way, only the transform step needs the exact pattern.
DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d %b %Y",
    "%b %d, %Y",
)

_INTEGER_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})*$|^[+-]?\d+$")
_DECIMAL_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})*(\.\d+)?$|^[+-]?\d*\.\d+$")
_CURRENCY_SYMBOLS = r"[$\u20ac\u00a3\u00a5\u20b9]|USD|EUR|GBP|PKR|INR"
_CURRENCY_RE = re.compile(
    rf"^\s*(?:{_CURRENCY_SYMBOLS})\s*[+-]?[\d,]+(?:\.\d+)?\s*$"
    rf"|^\s*[+-]?[\d,]+(?:\.\d+)?\s*(?:{_CURRENCY_SYMBOLS})\s*$"
)


def parse_date(value: str) -> datetime | None:
    """Return the parsed date for the first matching known format."""
    candidate = value.strip()
    if not candidate:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def detect_date_format(values: list[str]) -> str | None:
    """Return the single format that parses every non-empty value."""
    populated = [value.strip() for value in values if value.strip()]
    if not populated:
        return None
    for fmt in DATE_FORMATS:
        try:
            for value in populated:
                datetime.strptime(value, fmt)
        except ValueError:
            continue
        return fmt
    return None


def infer_type(values: list[str]) -> str:
    """Classify a column from its values into a coarse type name."""
    populated = [value.strip() for value in values if value.strip()]
    if not populated:
        return "empty"
    lowered = {value.lower() for value in populated}
    if lowered <= BOOLEAN_TOKENS and not lowered <= {"0", "1"}:
        return "boolean"
    if all(_INTEGER_RE.match(value) for value in populated):
        return "integer"
    if all(_DECIMAL_RE.match(value) for value in populated):
        return "decimal"
    if all(parse_date(value) is not None for value in populated):
        return "date"
    if all(_CURRENCY_RE.match(value) for value in populated):
        return "currency"
    return "text"


def profile_column(table: Table, name: str, index: int, settings: Settings) -> ColumnProfile:
    """Build a :class:`ColumnProfile` for one column."""
    values = table.column_values(name)
    populated = [value for value in values if value.strip()]
    distinct = list(dict.fromkeys(populated))
    return ColumnProfile(
        name=name,
        index=index,
        inferred_type=infer_type(values),
        row_count=len(values),
        non_empty_count=len(populated),
        distinct_count=len(distinct),
        sample_values=distinct[: settings.profile_sample_size],
    )


def profile_table(table: Table, settings: Settings) -> list[ColumnProfile]:
    """Profile every column of a table, left to right."""
    return [
        profile_column(table, name, index, settings) for index, name in enumerate(table.columns)
    ]
