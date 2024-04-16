"""String helpers shared by the matching code.

Deliberately dependency free: the whole point of the local suggester is
that a fresh clone can run it with nothing installed but the web stack.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.services.suggester.synonyms import (
    CANONICAL,
    MAX_PHRASE_LENGTH,
    NON_PLURAL,
    PHRASES,
    STOPWORDS,
)

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SPLIT_CHARS = re.compile(r"[^0-9A-Za-z]+")
_DIGIT_BOUNDARY = re.compile(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])")


def singular(token: str) -> str:
    """Strip a plural "s" when it is safe to do so."""
    if len(token) > 3 and token.endswith("s") and token not in NON_PLURAL:
        return token[:-1]
    return token


@lru_cache(maxsize=2048)
def tokenize(name: str) -> tuple[str, ...]:
    """Split a column name into lower-case words.

    ``"PolicyNumber"``, ``"policy_no"`` and ``"Policy No."`` all become
    ``("policy", "number")`` once :func:`canonical_tokens` has run.
    """
    spaced = _CAMEL_BOUNDARY.sub(" ", name)
    spaced = _DIGIT_BOUNDARY.sub(" ", spaced)
    parts = (part.lower() for part in _SPLIT_CHARS.split(spaced))
    return tuple(part for part in parts if part)


def collapse_phrases(tokens: list[str]) -> list[str]:
    """Replace known compound sequences with their single canonical word."""
    collapsed: list[str] = []
    position = 0
    while position < len(tokens):
        for width in range(MAX_PHRASE_LENGTH, 1, -1):
            phrase = tuple(tokens[position : position + width])
            replacement = PHRASES.get(phrase)
            if replacement is not None:
                collapsed.append(replacement)
                position += width
                break
        else:
            collapsed.append(tokens[position])
            position += 1
    return collapsed


@lru_cache(maxsize=2048)
def canonical_tokens(name: str) -> tuple[str, ...]:
    """Tokenize, drop stopwords, fold synonyms and collapse compounds."""
    tokens = []
    for token in tokenize(name):
        if token in STOPWORDS:
            continue
        root = singular(token)
        tokens.append(CANONICAL.get(root, CANONICAL.get(token, root)))
    return tuple(collapse_phrases(tokens))


def canonical_form(name: str) -> str:
    """The canonical tokens joined into one comparable string."""
    return "".join(canonical_tokens(name))


def levenshtein(left: str, right: str) -> int:
    """Edit distance between two strings (iterative, two rows)."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def ratio(left: str, right: str) -> float:
    """Edit distance normalised to ``0.0 - 1.0``."""
    if not left or not right:
        return 0.0
    return 1.0 - levenshtein(left, right) / max(len(left), len(right))


def token_set_ratio(left: str, right: str) -> float:
    """Similarity that ignores extra words on either side.

    ``"Premium"`` against ``"Monthly_Premium"`` scores 1.0 here and 0.42
    on a plain edit distance, because one name being a qualified version
    of the other is the most common way two schemas disagree.
    """
    left_tokens = set(canonical_tokens(left))
    right_tokens = set(canonical_tokens(right))
    shared = "".join(sorted(left_tokens & right_tokens))
    if not shared:
        return ratio("".join(sorted(left_tokens)), "".join(sorted(right_tokens)))
    left_full = "".join(sorted(left_tokens))
    right_full = "".join(sorted(right_tokens))
    return max(
        ratio(shared, left_full),
        ratio(shared, right_full),
        ratio(left_full, right_full),
    )


def name_similarity(left: str, right: str) -> float:
    """Blend of whole-name and token-set similarity over canonical forms."""
    whole = ratio(canonical_form(left), canonical_form(right))
    return 0.5 * whole + 0.5 * token_set_ratio(left, right)


def jaccard(left: set[str], right: set[str]) -> float:
    """Overlap of two sets, ``0.0`` when either is empty."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def containment(left: set[str], right: set[str]) -> float:
    """Share of the smaller set that the larger one contains."""
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def token_overlap(left: str, right: str) -> float:
    """Token agreement between two column names.

    Half Jaccard, half containment: a qualified name such as
    ``Date_of_Policy`` still counts as agreeing with ``Date`` without
    scoring as highly as an exact token match.
    """
    left_tokens = set(canonical_tokens(left))
    right_tokens = set(canonical_tokens(right))
    return 0.5 * jaccard(left_tokens, right_tokens) + 0.5 * containment(
        left_tokens, right_tokens
    )


def synonym_hits(left: str, right: str) -> list[tuple[str, str]]:
    """Pairs of differently spelled tokens that share a canonical word."""
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    hits: list[tuple[str, str]] = []
    for lhs in left_tokens:
        lhs_root = CANONICAL.get(singular(lhs), singular(lhs))
        for rhs in right_tokens:
            rhs_root = CANONICAL.get(singular(rhs), singular(rhs))
            if lhs_root == rhs_root and lhs.lower() != rhs.lower():
                hits.append((lhs, rhs))
    return hits


def normalise_value(value: str) -> str:
    """Fold a cell value for comparison: case, spacing and punctuation."""
    return re.sub(r"[^0-9a-z]+", "", value.strip().lower())


_DIGIT_RUN = re.compile(r"\d+")
_LETTER_RUN = re.compile(r"[A-Za-z]+")


def value_shape(value: str) -> str:
    """Collapse a value to its pattern: ``"AB-12345"`` -> ``"A-9"``.

    Two columns rarely share literal values -- a template file holds
    example rows, not the same rows -- but a policy number looks like a
    policy number in both files, and that is enough to tell which
    reformatting is needed.
    """
    collapsed = _DIGIT_RUN.sub("9", value.strip())
    return _LETTER_RUN.sub("A", collapsed)


def shape_set(values: list[str]) -> set[str]:
    """Distinct value shapes of a column sample."""
    return {value_shape(value) for value in values if value.strip()} - {""}


def value_set(values: list[str]) -> set[str]:
    """Normalised, non-empty distinct values of a column sample."""
    return {normalise_value(value) for value in values if value.strip()} - {""}
