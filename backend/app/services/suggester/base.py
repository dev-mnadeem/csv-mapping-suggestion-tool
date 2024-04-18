"""The seam every mapping strategy implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.schemas import ColumnProfile, ColumnSuggestion


@runtime_checkable
class MappingSuggester(Protocol):
    """Proposes, for each target column, which source column feeds it.

    Implementations must be side-effect free and must return one
    :class:`ColumnSuggestion` per target column, in target order, so the
    client can render the table without reordering anything.
    """

    name: str

    def suggest(
        self,
        source: list[ColumnProfile],
        target: list[ColumnProfile],
    ) -> list[ColumnSuggestion]:
        """Return one suggestion per target column."""
        ...
