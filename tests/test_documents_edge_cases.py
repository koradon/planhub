from __future__ import annotations

import pytest

from planhub.documents import (
    DocumentError,
    issue_document_to_metadata,
    load_issue_document,
    load_milestone_document,
    milestone_document_to_metadata,
    render_markdown,
    update_front_matter,
)
from planhub.github import IssueState


def test_load_issue_document_without_front_matter_treats_all_as_body(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text("No front matter here.", encoding="utf-8")

    with pytest.raises(DocumentError, match="Missing or invalid 'title'"):
        load_issue_document(issue_path)


def test_load_issue_document_rejects_unclosed_front_matter(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text("---\ntitle: Broken\nBody continues", encoding="utf-8")

    with pytest.raises(DocumentError, match="Missing closing front matter"):
        load_issue_document(issue_path)


def test_load_issue_document_rejects_non_mapping_front_matter(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text("---\n- not\n- mapping\n---\n", encoding="utf-8")

    with pytest.raises(DocumentError, match="Front matter must be a mapping"):
        load_issue_document(issue_path)


def test_load_issue_document_rejects_invalid_labels_type(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\nlabels: p1\n---\n', encoding="utf-8")

    with pytest.raises(DocumentError, match="Expected 'labels' to be a list of strings"):
        load_issue_document(issue_path)


def test_load_issue_document_rejects_invalid_milestone_type(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\nmilestone: {bad: true}\n---\n', encoding="utf-8")

    with pytest.raises(DocumentError, match="Expected 'milestone' to be a string, int, or null"):
        load_issue_document(issue_path)


def test_load_issue_document_rejects_unknown_state(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\nstate: "wip"\n---\n', encoding="utf-8")

    with pytest.raises(DocumentError, match="Unknown state 'wip'"):
        load_issue_document(issue_path)


def test_load_issue_document_rejects_unknown_state_reason(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\nstate_reason: "maybe"\n---\n', encoding="utf-8")

    with pytest.raises(DocumentError, match="Unknown state_reason 'maybe'"):
        load_issue_document(issue_path)


def test_load_issue_document_parses_null_milestone(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\nmilestone: null\n---\n', encoding="utf-8")

    issue = load_issue_document(issue_path)

    assert issue.milestone_set is True
    assert issue.milestone is None
    assert issue.milestone_number is None


def test_load_issue_document_parses_string_milestone(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\nmilestone: "Stage 1"\n---\n', encoding="utf-8")

    issue = load_issue_document(issue_path)

    assert issue.milestone == "Stage 1"
    assert issue.milestone_set is True


def test_load_milestone_document_parses_front_matter_description(tmp_path) -> None:
    milestone_path = tmp_path / "milestone.md"
    milestone_path.write_text(
        '---\ntitle: "Stage 1"\ndescription: "From front matter"\nstate: "open"\n---\n',
        encoding="utf-8",
    )

    milestone = load_milestone_document(milestone_path)

    assert milestone.description == "From front matter"
    assert milestone.state == IssueState.OPEN


def test_issue_document_to_metadata_includes_explicit_empty_lists(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text(
        '---\ntitle: "X"\nlabels: []\nassignees: []\nmilestone: null\n---\n',
        encoding="utf-8",
    )

    metadata = issue_document_to_metadata(load_issue_document(issue_path))

    assert metadata["labels"] == []
    assert metadata["assignees"] == []
    assert metadata["milestone"] is None


def test_milestone_document_to_metadata_includes_optional_fields(tmp_path) -> None:
    milestone_path = tmp_path / "milestone.md"
    milestone_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Stage 1"',
                "number: 3",
                'description: "Scope"',
                'due_on: "2026-12-31"',
                'state: "closed"',
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    metadata = milestone_document_to_metadata(load_milestone_document(milestone_path))

    assert metadata == {
        "title": "Stage 1",
        "number": 3,
        "description": "Scope",
        "due_on": "2026-12-31",
        "state": "closed",
    }


def test_render_markdown_omits_body_when_empty() -> None:
    rendered = render_markdown({"title": "X"}, "")

    assert rendered == "---\ntitle: X\n---\n\n"


def test_update_front_matter_with_cached_metadata_avoids_reread(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text('---\ntitle: "X"\n---\n\nBody\n', encoding="utf-8")

    changed = update_front_matter(
        issue_path,
        {"number": 1},
        cached_metadata={"title": "X"},
        cached_body="Body",
    )

    assert changed is True
    assert "number: 1" in issue_path.read_text(encoding="utf-8")
