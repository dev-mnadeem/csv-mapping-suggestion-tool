"""Mapping suggester implementations and the registry that picks one."""

from __future__ import annotations

from app.config import Settings
from app.services.suggester.base import MappingSuggester
from app.services.suggester.llm import OpenAIMappingSuggester
from app.services.suggester.local import LocalMappingSuggester

BUILDERS = {
    "local": lambda settings: LocalMappingSuggester(settings),
    "openai": lambda settings: OpenAIMappingSuggester(
        settings, fallback=LocalMappingSuggester(settings)
    ),
}


def get_suggester(settings: Settings) -> MappingSuggester:
    """Build the suggester named by ``settings.suggester_backend``.

    The OpenAI backend is only handed out when a key is actually present;
    without one it would fail on the first request, and a reviewer who
    cloned the repo would see an error instead of the app working.
    """
    name = settings.suggester_backend
    if name == "openai" and not settings.openai_api_key:
        name = "local"
    return BUILDERS[name](settings)


__all__ = [
    "BUILDERS",
    "LocalMappingSuggester",
    "MappingSuggester",
    "OpenAIMappingSuggester",
    "get_suggester",
]
