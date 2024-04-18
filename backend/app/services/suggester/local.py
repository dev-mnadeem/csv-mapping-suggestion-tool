"""The deterministic matcher: string similarity plus a synonym table.

No network, no API key, no model. Every score here is reproducible from
the two CSVs alone, which is what makes the accuracy fixtures in
``tests/fixtures/mapping_cases`` meaningful and what lets the app run on
a fresh clone.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.config import Settings
from app.domain.schemas import ColumnProfile, ColumnSuggestion, MappingCandidate
from app.services import transforms
from app.services.profiler import detect_date_format
from app.services.suggester.text import (
    canonical_form,
    jaccard,
    name_similarity,
    shape_set,
    synonym_hits,
    token_overlap,
    value_set,
)

# How much each name-derived signal contributes to a candidate's score.
# They sum to 1.0, so two columns whose names mean the same thing and
# hold the same kind of value score exactly 1.0. Synonyms are not a
# separate weight: names are compared after the synonym table has already
# folded "Policy_No" and "PolicyNumber" onto the same canonical form.
WEIGHTS: dict[str, float] = {
    "name_similarity": 0.50,
    "token_overlap": 0.40,
    "type_match": 0.10,
}

# Value overlap is added on top instead of being averaged in. Two columns
# that hold the same vocabulary ("Gold", "Silver", "Bronze") are good
# evidence for a pairing, but two columns holding different people's
# names are not evidence against one -- a template file is usually filled
# with unrelated example rows.
VALUE_BONUS = 0.15

NUMERIC_TYPES = frozenset({"integer", "decimal", "currency"})

# A transform is only proposed when it lifts exact-value overlap by this
# much, so formatting noise does not produce spurious conversions.
TRANSFORM_MIN_GAIN = 0.10

# Transforms tried by the overlap search, cheapest and least destructive
# first so that a tie keeps the simpler option.
OVERLAP_TRANSFORMS: tuple[str, ...] = (
    "trim",
    "strip_separators",
    "first_token",
    "last_token",
    "digits_only",
    "upper",
    "lower",
    "title_case",
)


@dataclass(frozen=True, slots=True)
class ScoredPair:
    """A scored (target, source) pairing before assignment happens."""

    target: str
    source: str
    confidence: float
    signals: dict[str, float]
    rationale: str
    transform: str
    options: dict[str, str]


def exact_values(profile: ColumnProfile) -> set[str]:
    """Distinct sample values with only surrounding whitespace removed."""
    return {value.strip() for value in profile.sample_values if value.strip()}


def type_affinity(source: ColumnProfile, target: ColumnProfile) -> float:
    """How compatible two inferred types are, from 0.0 to 1.0."""
    if source.inferred_type == target.inferred_type:
        return 1.0
    if "empty" in (source.inferred_type, target.inferred_type):
        return 0.5
    if {source.inferred_type, target.inferred_type} <= NUMERIC_TYPES:
        return 0.7
    if "text" in (source.inferred_type, target.inferred_type):
        return 0.3
    return 0.0


def infer_transform(source: ColumnProfile, target: ColumnProfile) -> tuple[str, dict[str, str]]:
    """Guess the conversion that makes source values look like target ones."""
    if source.inferred_type == "date" and target.inferred_type == "date":
        source_format = detect_date_format(source.sample_values)
        target_format = detect_date_format(target.sample_values)
        if target_format and source_format != target_format:
            return "to_date", {"format": target_format}
        return "identity", {}

    if target.inferred_type == "integer" and source.inferred_type in {
        "decimal",
        "currency",
    }:
        return "to_integer", {}
    if target.inferred_type == "decimal" and source.inferred_type == "currency":
        return "to_decimal", {}

    source_values = exact_values(source)
    target_values = exact_values(target)
    if not source_values or not target_values:
        return "identity", {}

    chosen = _best_transform(source_values, target_values, lambda values: values)
    if chosen == "identity":
        # Literal values rarely coincide across two different exports, so
        # fall back to comparing their shapes.
        chosen = _best_transform(source_values, target_values, shape_set_of)
    return chosen, {}


def shape_set_of(values: set[str]) -> set[str]:
    """Shapes of a set of values, e.g. ``{"AB-12345"}`` -> ``{"A-9"}``."""
    return shape_set(list(values))


def _best_transform(
    source_values: set[str],
    target_values: set[str],
    project: Callable[[set[str]], set[str]],
) -> str:
    """Pick the transform that best aligns source with target values."""
    targets = project(target_values)
    best_name = "identity"
    best_score = jaccard(project(source_values), targets)
    for name in OVERLAP_TRANSFORMS:
        converted = {transforms.apply(name, value) for value in source_values}
        score = jaccard(project(converted - {""}), targets)
        if score > best_score + TRANSFORM_MIN_GAIN:
            best_name, best_score = name, score
    return best_name


def describe(
    source: ColumnProfile,
    target: ColumnProfile,
    signals: dict[str, float],
    transform: str,
) -> str:
    """A short, human-checkable reason for the pairing."""
    hits = synonym_hits(source.name, target.name)
    if canonical_form(source.name) == canonical_form(target.name):
        reason = "same name once abbreviations are expanded"
    elif hits:
        pairs = ", ".join(f"{left} = {right}" for left, right in hits[:2])
        reason = f"synonyms match ({pairs})"
    elif signals["token_overlap"] >= 0.5:
        reason = "column names share most of their words"
    elif signals["value_overlap"] >= 0.5:
        reason = "the two columns hold the same set of values"
    elif signals["name_similarity"] >= 0.6:
        reason = f"names are {signals['name_similarity']:.0%} similar"
    else:
        reason = f"weak match on name and type ({signals['name_similarity']:.0%} similar)"
    if transform != "identity":
        reason = f"{reason}, values need '{transform}'"
    return reason


class LocalMappingSuggester:
    """Scores every target/source pair, then assigns greedily."""

    name = "local"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def score(self, source: ColumnProfile, target: ColumnProfile) -> ScoredPair:
        """Score one candidate pairing."""
        signals = {
            "name_similarity": name_similarity(source.name, target.name),
            "token_overlap": token_overlap(source.name, target.name),
            "type_match": type_affinity(source, target),
            "value_overlap": jaccard(
                value_set(source.sample_values), value_set(target.sample_values)
            ),
        }

        confidence = sum(signals[key] * weight for key, weight in WEIGHTS.items())
        confidence += VALUE_BONUS * signals["value_overlap"]

        transform, options = infer_transform(source, target)
        return ScoredPair(
            target=target.name,
            source=source.name,
            confidence=round(min(1.0, confidence), 4),
            signals={key: round(value, 4) for key, value in signals.items()},
            rationale=describe(source, target, signals, transform),
            transform=transform,
            options=options,
        )

    def suggest(
        self,
        source: list[ColumnProfile],
        target: list[ColumnProfile],
    ) -> list[ColumnSuggestion]:
        """Return one suggestion per target column, in target order."""
        pairs = [
            self.score(source_column, target_column)
            for target_column in target
            for source_column in source
        ]
        pairs.sort(key=lambda pair: (-pair.confidence, pair.target, pair.source))

        # Greedy one-to-one assignment: a schema column takes one source
        # column, and a source column feeds at most one schema column.
        # Rejected pairings stay visible as alternatives.
        assigned: dict[str, ScoredPair] = {}
        used_sources: set[str] = set()
        for pair in pairs:
            if pair.confidence < self._settings.min_confidence:
                break
            if pair.target in assigned or pair.source in used_sources:
                continue
            assigned[pair.target] = pair
            used_sources.add(pair.source)

        by_target: dict[str, list[ScoredPair]] = {column.name: [] for column in target}
        for pair in pairs:
            by_target[pair.target].append(pair)

        suggestions: list[ColumnSuggestion] = []
        for column in target:
            best = assigned.get(column.name)
            alternatives = [
                pair
                for pair in by_target[column.name]
                if best is None or pair.source != best.source
            ][: self._settings.max_alternatives]
            suggestions.append(
                ColumnSuggestion(
                    target_column=column.name,
                    best=to_candidate(best) if best else None,
                    alternatives=[to_candidate(pair) for pair in alternatives],
                )
            )
        return suggestions


def to_candidate(pair: ScoredPair) -> MappingCandidate:
    """Convert an internal scored pair into the API's candidate shape."""
    return MappingCandidate(
        source_column=pair.source,
        confidence=pair.confidence,
        rationale=pair.rationale,
        transform=pair.transform,
        transform_options=pair.options,
        signals=pair.signals,
    )
