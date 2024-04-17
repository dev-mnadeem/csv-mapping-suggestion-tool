"""Turn an uploaded byte stream into a header plus rows, defensively.

Real CSV exports are messy: a spreadsheet writes a UTF-8 BOM, a European
system writes semicolons and cp1252 bytes, an address field contains a
newline inside quotes, two columns are both called "Notes", and someone
exports a 400 MB file. Each of those is handled here, once, so that the
rest of the codebase only ever sees a clean :class:`Table`.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from app.config import Settings
from app.services.errors import CsvDecodeError, CsvEmptyError, CsvTooLargeError

# Tried in order. utf-8-sig strips a byte order mark if one is present and
# behaves exactly like utf-8 when it is not.
ENCODING_CANDIDATES: tuple[str, ...] = ("utf-8-sig", "cp1252", "latin-1")

# Delimiters we let csv.Sniffer choose between. Restricting the alphabet
# stops the sniffer from picking a letter that happens to be frequent.
DELIMITER_CANDIDATES = ",;\t|"
DEFAULT_DELIMITER = ","

# csv has a 128 KiB default field limit; a quoted free-text column can
# legitimately exceed it, and the upload cap already bounds total size.
_FIELD_SIZE_LIMIT = 10 * 1024 * 1024


@dataclass(slots=True)
class Table:
    """A parsed CSV: column names plus rows of raw string cells."""

    columns: list[str]
    rows: list[list[str]]
    encoding: str = "utf-8"
    delimiter: str = DEFAULT_DELIMITER
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def column_values(self, column: str) -> list[str]:
        """All values of one column, in row order."""
        index = self.columns.index(column)
        return [row[index] for row in self.rows]


def read_upload_bytes(stream: io.BufferedIOBase, settings: Settings) -> bytes:
    """Read at most ``max_upload_bytes`` and reject anything larger.

    The read is chunked and stops one byte past the limit, so an oversized
    upload never gets fully materialised in memory.
    """
    limit = settings.max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise CsvTooLargeError(f"File exceeds the {limit} byte upload limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def decode(payload: bytes) -> tuple[str, str]:
    """Decode bytes, returning ``(text, encoding_name)``.

    latin-1 decodes any byte sequence, so it is the terminal fallback and
    the loop cannot fall through in practice -- the raise guards against a
    future edit that removes it.
    """
    for encoding in ENCODING_CANDIDATES:
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise CsvDecodeError("Could not decode the file as UTF-8, cp1252 or latin-1.")


def sniff_delimiter(text: str, settings: Settings) -> tuple[str, bool]:
    """Guess the delimiter, returning ``(delimiter, was_sniffed)``."""
    sample = text[: settings.sniff_sample_bytes]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=DELIMITER_CANDIDATES)
    except csv.Error:
        return DEFAULT_DELIMITER, False
    return dialect.delimiter, True


def _looks_numeric(value: str) -> bool:
    candidate = value.strip().replace(",", "").replace(" ", "")
    if not candidate:
        return False
    try:
        float(candidate)
    except ValueError:
        return False
    return True


def normalise_header(raw: list[str], warnings: list[str]) -> list[str]:
    """Produce unique, non-empty column names.

    Blank headers become ``column_<n>`` and duplicates get a numeric
    suffix, because downstream code addresses columns by name and a
    duplicate silently shadows data otherwise.
    """
    names: list[str] = []
    seen: dict[str, int] = {}
    blanks = 0
    duplicates = 0
    for position, cell in enumerate(raw, start=1):
        name = cell.strip()
        if not name:
            name = f"column_{position}"
            blanks += 1
        if name in seen:
            seen[name] += 1
            duplicates += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        names.append(name)
    if blanks:
        warnings.append(f"{blanks} header cell(s) were empty and were auto-named.")
    if duplicates:
        warnings.append(
            f"{duplicates} duplicate header name(s) were suffixed to keep them unique."
        )
    return names


def parse_table(text: str, delimiter: str, settings: Settings) -> Table:
    """Parse decoded text into a :class:`Table`."""
    warnings: list[str] = []
    previous_limit = csv.field_size_limit(_FIELD_SIZE_LIMIT)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CsvEmptyError("The file is empty.") from exc

        if len(header) > settings.max_columns:
            raise CsvEmptyError(
                f"The file has {len(header)} columns, above the "
                f"{settings.max_columns} column limit."
            )

        data_rows: list[list[str]] = []
        header_is_data = bool(header) and all(_looks_numeric(cell) for cell in header)
        if header_is_data:
            warnings.append("The first row looks like data, so generic column names were used.")
            columns = [f"column_{i}" for i in range(1, len(header) + 1)]
            data_rows.append(header)
        else:
            columns = normalise_header(header, warnings)

        width = len(columns)
        ragged = 0
        truncated = False
        for row in reader:
            if len(data_rows) >= settings.max_rows:
                truncated = True
                break
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != width:
                ragged += 1
                row = (row + [""] * width)[:width]
            data_rows.append(row)
    finally:
        csv.field_size_limit(previous_limit)

    if ragged:
        warnings.append(
            f"{ragged} row(s) did not have {width} fields and were padded or trimmed."
        )
    if truncated:
        warnings.append(f"Only the first {settings.max_rows} rows were read.")
    if not data_rows:
        raise CsvEmptyError("The file has a header but no data rows.")

    return Table(
        columns=columns,
        rows=data_rows,
        delimiter=delimiter,
        truncated=truncated,
        warnings=warnings,
    )


def read_csv(payload: bytes, settings: Settings) -> Table:
    """Decode, sniff and parse an uploaded CSV payload."""
    text, encoding = decode(payload)
    delimiter, sniffed = sniff_delimiter(text, settings)
    table = parse_table(text, delimiter, settings)
    table.encoding = encoding
    if encoding != "utf-8-sig":
        table.warnings.insert(0, f"File was decoded as {encoding}, not UTF-8.")
    if not sniffed:
        table.warnings.insert(0, "Delimiter could not be detected; assumed a comma.")
    return table
