"""The parser has to survive real exports, not just tidy ones."""

from __future__ import annotations

import io

import pytest

from app.config import Settings
from app.services.csv_reader import read_csv, read_upload_bytes
from app.services.errors import CsvEmptyError, CsvTooLargeError


@pytest.fixture
def settings() -> Settings:
    return Settings()


def test_plain_csv(settings: Settings) -> None:
    table = read_csv(b"a,b\n1,2\n3,4\n", settings)
    assert table.columns == ["a", "b"]
    assert table.rows == [["1", "2"], ["3", "4"]]
    assert table.delimiter == ","


def test_utf8_bom_is_stripped(settings: Settings) -> None:
    table = read_csv("﻿name,city\nAnna,Berlin\n".encode(), settings)
    assert table.columns == ["name", "city"]


def test_latin1_bytes_decode_and_warn(settings: Settings) -> None:
    payload = "name,city\nJosé,Málaga\n".encode("latin-1")
    table = read_csv(payload, settings)
    assert table.rows[0][0] == "José"
    assert any("not UTF-8" in warning for warning in table.warnings)


def test_semicolon_delimiter_is_detected(settings: Settings) -> None:
    table = read_csv(b"name;amount\nAnna;12,50\nBo;3,00\n", settings)
    assert table.delimiter == ";"
    assert table.columns == ["name", "amount"]
    assert table.rows[0] == ["Anna", "12,50"]


def test_tab_delimiter_is_detected(settings: Settings) -> None:
    table = read_csv(b"name\tamount\nAnna\t12\nBo\t3\n", settings)
    assert table.delimiter == "\t"


def test_quoted_field_containing_newline_stays_one_cell(settings: Settings) -> None:
    table = read_csv(b'id,note\n1,"line one\nline two"\n2,plain\n', settings)
    assert table.row_count == 2
    assert table.rows[0][1] == "line one\nline two"


def test_quoted_field_containing_delimiter(settings: Settings) -> None:
    table = read_csv(b'id,name\n1,"Doe, John"\n', settings)
    assert table.rows[0][1] == "Doe, John"


def test_duplicate_headers_are_made_unique(settings: Settings) -> None:
    table = read_csv(b"note,note,note\na,b,c\n", settings)
    assert table.columns == ["note", "note_2", "note_3"]
    assert any("duplicate header" in warning for warning in table.warnings)


def test_blank_headers_are_named(settings: Settings) -> None:
    table = read_csv(b"id,,name\n1,x,Anna\n", settings)
    assert table.columns == ["id", "column_2", "name"]
    assert any("empty" in warning for warning in table.warnings)


def test_header_row_that_is_actually_data(settings: Settings) -> None:
    table = read_csv(b"1,2,3\n4,5,6\n", settings)
    assert table.columns == ["column_1", "column_2", "column_3"]
    assert table.row_count == 2
    assert any("looks like data" in warning for warning in table.warnings)


def test_ragged_rows_are_padded(settings: Settings) -> None:
    table = read_csv(b"a,b,c\n1,2\n1,2,3,4\n", settings)
    assert table.rows[0] == ["1", "2", ""]
    assert table.rows[1] == ["1", "2", "3"]
    assert any("did not have 3 fields" in warning for warning in table.warnings)


def test_blank_lines_are_skipped(settings: Settings) -> None:
    table = read_csv(b"a,b\n1,2\n\n\n3,4\n", settings)
    assert table.row_count == 2


def test_row_cap_truncates_and_warns() -> None:
    settings = Settings(max_rows=5)
    payload = b"a\n" + b"".join(b"%d\n" % index for index in range(50))
    table = read_csv(payload, settings)
    assert table.row_count == 5
    assert table.truncated is True


def test_header_only_file_is_rejected(settings: Settings) -> None:
    with pytest.raises(CsvEmptyError):
        read_csv(b"a,b,c\n", settings)


def test_empty_file_is_rejected(settings: Settings) -> None:
    with pytest.raises(CsvEmptyError):
        read_csv(b"", settings)


def test_upload_larger_than_the_cap_is_refused() -> None:
    settings = Settings(max_upload_bytes=1024)
    stream = io.BytesIO(b"x" * 5000)
    with pytest.raises(CsvTooLargeError):
        read_upload_bytes(stream, settings)


def test_upload_at_the_cap_is_accepted() -> None:
    settings = Settings(max_upload_bytes=1024)
    payload = read_upload_bytes(io.BytesIO(b"x" * 1024), settings)
    assert len(payload) == 1024


def test_too_many_columns_is_rejected() -> None:
    settings = Settings(max_columns=3)
    with pytest.raises(CsvEmptyError):
        read_csv(b"a,b,c,d\n1,2,3,4\n", settings)
