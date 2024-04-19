"""FastAPI dependencies: settings, suggester, repository, upload parsing."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated

from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.repository import RunRepository
from app.db.session import session_scope
from app.services.csv_reader import Table, read_csv, read_upload_bytes
from app.services.errors import CsvError
from app.services.suggester import MappingSuggester, get_suggester

ACCEPTED_SUFFIXES = frozenset({".csv", ".tsv", ".txt"})
FALLBACK_FILENAME = "upload.csv"


def safe_filename(raw: str | None) -> str:
    """Reduce a client-supplied filename to a bare, displayable name.

    Nothing here is ever used as a path -- uploads are parsed in memory --
    but the name is echoed back in responses and written to the run log,
    and ``../../etc/passwd`` or a Windows path should not survive that.
    """
    if not raw:
        return FALLBACK_FILENAME
    name = PureWindowsPath(PurePosixPath(raw).name).name.strip().lstrip(".")
    return name or FALLBACK_FILENAME


def has_accepted_suffix(filename: str) -> bool:
    """True when the filename ends in an extension we will parse."""
    return PurePosixPath(filename.lower()).suffix in ACCEPTED_SUFFIXES


async def load_table(upload: UploadFile, settings: Settings) -> tuple[str, Table]:
    """Validate and parse one uploaded file into a :class:`Table`."""
    filename = safe_filename(upload.filename)
    if not has_accepted_suffix(filename):
        raise CsvError(
            f"'{filename}' is not a CSV. Accepted extensions: "
            f"{', '.join(sorted(ACCEPTED_SUFFIXES))}."
        )
    payload = read_upload_bytes(upload.file, settings)
    return filename, read_csv(payload, settings)


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(session_scope)]


def get_repository(session: SessionDep) -> RunRepository:
    """Repository bound to the request's session."""
    return RunRepository(session)


def get_active_suggester(settings: SettingsDep) -> MappingSuggester:
    """The suggester configured for this deployment."""
    return get_suggester(settings)


RepositoryDep = Annotated[RunRepository, Depends(get_repository)]
SuggesterDep = Annotated[MappingSuggester, Depends(get_active_suggester)]
