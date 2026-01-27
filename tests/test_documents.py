from pathlib import Path

import pytest

from planhub.documents import DocumentError, load_issue_document, load_milestone_document
from planhub.github import IssueState, IssueStateReason


def test_load_issue_document_parses_fields(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "labels: [p1, backend]",
                "assignees: [alice]",
                'state: "closed"',
                'state_reason: "not_planned"',
                'number: "12"',
                "---",
                "",
                "Details here.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    issue = load_issue_document(issue_path)

    assert issue.title == "Ship it"
    assert issue.labels == ("p1", "backend")
    assert issue.assignees == ("alice",)
    assert issue.state == IssueState.CLOSED
    assert issue.state_reason == IssueStateReason.NOT_PLANNED
    assert issue.number == 12
    assert "Details here." in issue.body


def test_load_milestone_document_uses_body_for_description(tmp_path) -> None:
    milestone_path = tmp_path / "milestone.md"
    milestone_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Stage 1"',
                "---",
                "",
                "Scope notes.",
            ]
        ),
        encoding="utf-8",
    )

    milestone = load_milestone_document(milestone_path)

    assert milestone.title == "Stage 1"
    assert milestone.description == "Scope notes."


def test_load_issue_document_requires_title(tmp_path) -> None:
    issue_path = tmp_path / "issue.md"
    issue_path.write_text("---\nlabels: [p1]\n---\n", encoding="utf-8")

    with pytest.raises(DocumentError):
        load_issue_document(issue_path)
