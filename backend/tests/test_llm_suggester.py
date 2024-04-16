"""The optional LLM backend, exercised against a stubbed transport."""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.domain.schemas import ColumnProfile
from app.services.suggester import get_suggester
from app.services.suggester.llm import OpenAIMappingSuggester
from app.services.suggester.local import LocalMappingSuggester

SETTINGS = Settings(suggester_backend="openai", openai_api_key="test-key")


def profile(name: str) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        index=0,
        inferred_type="text",
        row_count=1,
        non_empty_count=1,
        distinct_count=1,
        sample_values=["x"],
    )


SOURCE = [profile("Policy_No"), profile("Department")]
TARGET = [profile("PolicyNumber"), profile("Team")]


def stub_client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def reply(payload: dict) -> httpx.MockTransport:
    def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(payload)}}]},
        )

    return httpx.MockTransport(handle)


def build(transport: httpx.MockTransport) -> OpenAIMappingSuggester:
    return OpenAIMappingSuggester(
        SETTINGS, fallback=LocalMappingSuggester(SETTINGS), client=stub_client(transport)
    )


def test_model_answer_is_used() -> None:
    suggester = build(
        reply(
            {
                "mappings": [
                    {
                        "target_column": "PolicyNumber",
                        "source_column": "Policy_No",
                        "confidence": 0.91,
                        "rationale": "same identifier",
                        "transform": "strip_separators",
                    },
                    {"target_column": "Team", "source_column": None},
                ]
            }
        )
    )
    first, second = suggester.suggest(SOURCE, TARGET)
    assert first.best is not None
    assert first.best.source_column == "Policy_No"
    assert first.best.transform == "strip_separators"
    assert second.best is None


def test_hallucinated_column_is_dropped() -> None:
    suggester = build(
        reply(
            {
                "mappings": [
                    {"target_column": "PolicyNumber", "source_column": "does_not_exist"}
                ]
            }
        )
    )
    results = suggester.suggest(SOURCE, TARGET)
    assert all(item.best is None for item in results)


def test_unknown_transform_falls_back_to_identity() -> None:
    suggester = build(
        reply(
            {
                "mappings": [
                    {
                        "target_column": "PolicyNumber",
                        "source_column": "Policy_No",
                        "transform": "__import__('os').system",
                    }
                ]
            }
        )
    )
    [first, _] = suggester.suggest(SOURCE, TARGET)
    assert first.best is not None
    assert first.best.transform == "identity"


def test_transport_error_falls_back_to_the_local_matcher() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("no route")

    suggester = build(httpx.MockTransport(fail))
    [first, _] = suggester.suggest(SOURCE, TARGET)
    assert first.best is not None
    assert first.best.source_column == "Policy_No"


def test_unparsable_answer_falls_back_to_the_local_matcher() -> None:
    def garbage(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "{{{"}}]})

    suggester = build(httpx.MockTransport(garbage))
    [first, _] = suggester.suggest(SOURCE, TARGET)
    assert first.best is not None
    assert first.best.source_column == "Policy_No"


def test_missing_key_falls_back_to_the_local_matcher() -> None:
    suggester = OpenAIMappingSuggester(
        Settings(suggester_backend="openai", openai_api_key=None),
        fallback=LocalMappingSuggester(SETTINGS),
    )
    [first, _] = suggester.suggest(SOURCE, TARGET)
    assert first.best is not None
    assert first.best.source_column == "Policy_No"


@pytest.mark.parametrize(
    ("backend", "key", "expected"),
    [
        ("local", None, "local"),
        ("openai", None, "local"),
        ("openai", "test-key", "openai"),
    ],
)
def test_registry_picks_the_right_backend(
    backend: str, key: str | None, expected: str
) -> None:
    settings = Settings(suggester_backend=backend, openai_api_key=key)
    assert get_suggester(settings).name == expected
