from __future__ import annotations

from planhub.slug import slugify


def test_slugify_normalizes_spaces_and_case() -> None:
    assert slugify("Stage 1 / Q2", fallback="milestone") == "stage-1-q2"


def test_slugify_collapses_repeated_separators() -> None:
    assert slugify("a---b__c", fallback="milestone") == "a-b-c"


def test_slugify_uses_fallback_for_empty_result() -> None:
    assert slugify("!!!", fallback="milestone") == "milestone"
    assert slugify("", fallback="issue") == "issue"


def test_slugify_strips_leading_and_trailing_dashes() -> None:
    assert slugify(" -hello- ", fallback="milestone") == "hello"
