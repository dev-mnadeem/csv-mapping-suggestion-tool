"""Domain level errors that the API layer turns into HTTP responses."""

from __future__ import annotations


class CsvError(Exception):
    """Base class for anything wrong with an uploaded table."""


class CsvTooLargeError(CsvError):
    """The upload exceeded ``Settings.max_upload_bytes``."""


class CsvEmptyError(CsvError):
    """The upload contained no parsable rows."""


class CsvDecodeError(CsvError):
    """None of the supported encodings could decode the upload."""


class MappingPlanError(Exception):
    """A submitted mapping plan does not fit the uploaded table."""


class RunNotFoundError(Exception):
    """A suggestion run id that is not in the database."""

    def __init__(self, run_id: int) -> None:
        super().__init__(f"Run {run_id} was not found.")
        self.run_id = run_id
