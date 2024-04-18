"""The closed set of value transforms a mapping plan may ask for.

A plan arrives from the browser and may have been influenced by a model,
so it is treated as untrusted input: it can only name a transform from
this registry, and the worst a bad plan can do is produce wrong strings.
Nothing in a request is ever compiled or executed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.domain.schemas import TransformInfo
from app.services.profiler import parse_date

Options = dict[str, str]
TransformFn = Callable[[str, Options], str]

_SEPARATORS_RE = re.compile(r"[\s\-_/.,]+")
_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-z]+")
_NUMERIC_RE = re.compile(r"[+-]?\d[\d,]*(\.\d+)?")

DEFAULT_DATE_OUTPUT = "%Y-%m-%d"


@dataclass(frozen=True, slots=True)
class Transform:
    """A named, pure ``str -> str`` conversion."""

    name: str
    description: str
    fn: TransformFn
    options: tuple[str, ...] = field(default=())

    def __call__(self, value: str, options: Options | None = None) -> str:
        return self.fn(value, options or {})


def _identity(value: str, _options: Options) -> str:
    return value


def _trim(value: str, _options: Options) -> str:
    return value.strip()


def _upper(value: str, _options: Options) -> str:
    return value.strip().upper()


def _lower(value: str, _options: Options) -> str:
    return value.strip().lower()


def _title_case(value: str, _options: Options) -> str:
    return value.strip().title()


def _strip_separators(value: str, _options: Options) -> str:
    """``"CD-67890"`` -> ``"CD67890"``."""
    return _NON_ALNUM_RE.sub("", value.strip())


def _first_token(value: str, _options: Options) -> str:
    """``"Gold Plan"`` -> ``"Gold"``."""
    parts = [part for part in _SEPARATORS_RE.split(value.strip()) if part]
    return parts[0] if parts else ""


def _last_token(value: str, _options: Options) -> str:
    parts = [part for part in _SEPARATORS_RE.split(value.strip()) if part]
    return parts[-1] if parts else ""


def _digits_only(value: str, _options: Options) -> str:
    return re.sub(r"\D+", "", value)


def _to_integer(value: str, _options: Options) -> str:
    """Drop currency symbols and decimals: ``"$1,250.00"`` -> ``"1250"``."""
    match = _NUMERIC_RE.search(value.replace(" ", ""))
    if match is None:
        return ""
    try:
        return str(int(Decimal(match.group(0).replace(",", ""))))
    except (InvalidOperation, ValueError):
        return ""


def _to_decimal(value: str, options: Options) -> str:
    match = _NUMERIC_RE.search(value.replace(" ", ""))
    if match is None:
        return ""
    try:
        number = Decimal(match.group(0).replace(",", ""))
    except InvalidOperation:
        return ""
    places = options.get("places")
    if places is None:
        return str(number)
    try:
        quantum = Decimal(1).scaleb(-int(places))
    except (ValueError, InvalidOperation):
        return str(number)
    return str(number.quantize(quantum))


def _to_date(value: str, options: Options) -> str:
    """Re-format a date. ``format`` defaults to ISO ``%Y-%m-%d``."""
    parsed = parse_date(value)
    if parsed is None:
        return ""
    return parsed.strftime(options.get("format", DEFAULT_DATE_OUTPUT))


def _constant(_value: str, options: Options) -> str:
    return options.get("value", "")


REGISTRY: dict[str, Transform] = {
    transform.name: transform
    for transform in (
        Transform("identity", "Copy the value unchanged", _identity),
        Transform("trim", "Strip surrounding whitespace", _trim),
        Transform("upper", "Upper-case the value", _upper),
        Transform("lower", "Lower-case the value", _lower),
        Transform("title_case", "Title-case the value", _title_case),
        Transform(
            "strip_separators", "Remove spaces, dashes and punctuation", _strip_separators
        ),
        Transform("first_token", "Keep the first word", _first_token),
        Transform("last_token", "Keep the last word", _last_token),
        Transform("digits_only", "Keep digits only", _digits_only),
        Transform("to_integer", "Parse a number and drop the decimals", _to_integer),
        Transform("to_decimal", "Parse a number", _to_decimal, ("places",)),
        Transform("to_date", "Re-format a recognised date", _to_date, ("format",)),
        Transform(
            "constant", "Ignore the source and emit a fixed value", _constant, ("value",)
        ),
    )
}

# Transforms the suggester is allowed to propose on its own. "constant"
# needs a human decision, so it is never auto-selected.
INFERABLE: tuple[str, ...] = (
    "trim",
    "strip_separators",
    "first_token",
    "last_token",
    "to_integer",
    "to_date",
    "upper",
    "lower",
    "title_case",
)


def get(name: str) -> Transform:
    """Look up a transform, raising ``KeyError`` for unknown names."""
    return REGISTRY[name]


def apply(name: str, value: str, options: Options | None = None) -> str:
    """Run a named transform over a single value."""
    return get(name)(value, options)


def catalogue() -> list[TransformInfo]:
    """Describe the registry for the client's transform picker."""
    return [
        TransformInfo(
            name=transform.name,
            description=transform.description,
            options=list(transform.options),
        )
        for transform in REGISTRY.values()
    ]
