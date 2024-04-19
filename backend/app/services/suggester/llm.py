"""An optional LLM-backed suggester behind the same interface.

Switched on with ``SUGGESTER_BACKEND=openai`` and an API key. Anything
that goes wrong -- no key, timeout, rate limit, unparsable answer -- falls
back to the local matcher rather than failing the request, so turning the
model on can only add to what the app already does.

The model is asked for a mapping, never for code: its answer is validated
against the real column names before it reaches a response.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import Settings
from app.domain.schemas import ColumnProfile, ColumnSuggestion, MappingCandidate
from app.services import transforms
from app.services.suggester.base import MappingSuggester

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You map the columns of a source CSV onto a target schema. "
    "Answer with JSON only, shaped as "
    '{"mappings": [{"target_column": str, "source_column": str|null, '
    '"confidence": number between 0 and 1, "rationale": str, "transform": str}]}. '
    "Use exactly the column names you were given. Choose `transform` from the "
    'allowed list, or "identity" when the values already match. '
    "Use null for a target column with no reasonable source."
)

MAX_SAMPLES_IN_PROMPT = 5


def describe_columns(profiles: list[ColumnProfile]) -> list[dict[str, object]]:
    """Compact, token-cheap description of a table's columns."""
    return [
        {
            "name": profile.name,
            "type": profile.inferred_type,
            "samples": profile.sample_values[:MAX_SAMPLES_IN_PROMPT],
        }
        for profile in profiles
    ]


class OpenAIMappingSuggester:
    """Calls an OpenAI-compatible chat endpoint, with a local fallback."""

    name = "openai"

    def __init__(
        self,
        settings: Settings,
        fallback: MappingSuggester,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._fallback = fallback
        self._client = client

    def _post(self, payload: dict[str, object]) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}
        url = f"{self._settings.openai_base_url}/chat/completions"
        if self._client is not None:
            response = self._client.post(url, json=payload, headers=headers)
        else:
            with httpx.Client(timeout=self._settings.openai_timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _ask(
        self, source: list[ColumnProfile], target: list[ColumnProfile]
    ) -> list[dict[str, object]]:
        user_prompt = json.dumps(
            {
                "source_columns": describe_columns(source),
                "target_columns": describe_columns(target),
                "allowed_transforms": list(transforms.REGISTRY),
            }
        )
        body = self._post(
            {
                "model": self._settings.openai_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            }
        )
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        mappings = parsed.get("mappings", [])
        if not isinstance(mappings, list):
            raise ValueError("Model returned 'mappings' that is not a list.")
        return mappings

    def suggest(
        self,
        source: list[ColumnProfile],
        target: list[ColumnProfile],
    ) -> list[ColumnSuggestion]:
        """Ask the model, validate its answer, fall back on any problem."""
        if not self._settings.openai_api_key:
            logger.warning("No OPENAI_API_KEY set; using the local suggester.")
            return self._fallback.suggest(source, target)
        try:
            raw = self._ask(source, target)
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("LLM suggester failed (%s); using the local suggester.", exc)
            return self._fallback.suggest(source, target)
        return self._validate(raw, source, target)

    def _validate(
        self,
        raw: list[dict[str, object]],
        source: list[ColumnProfile],
        target: list[ColumnProfile],
    ) -> list[ColumnSuggestion]:
        """Keep only rows that name real columns and a known transform."""
        source_names = {profile.name for profile in source}
        by_target = {str(row.get("target_column")): row for row in raw}

        suggestions: list[ColumnSuggestion] = []
        for column in target:
            row = by_target.get(column.name)
            candidate: MappingCandidate | None = None
            source_column = row.get("source_column") if row else None
            if row is not None and source_column in source_names:
                transform = str(row.get("transform") or "identity")
                if transform not in transforms.REGISTRY:
                    transform = "identity"
                confidence = row.get("confidence", 0.5)
                candidate = MappingCandidate(
                    source_column=str(source_column),
                    confidence=_clamp(confidence),
                    rationale=str(row.get("rationale") or "suggested by the model"),
                    transform=transform,
                    signals={"model": 1.0},
                )
            suggestions.append(ColumnSuggestion(target_column=column.name, best=candidate))
        return suggestions


def _clamp(value: object) -> float:
    """Coerce a model-supplied confidence into ``0.0 - 1.0``."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, number))
