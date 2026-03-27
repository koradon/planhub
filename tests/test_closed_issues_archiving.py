from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.layout import ensure_layout


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_archives_closed_issue_under_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "closed", "state_reason": "completed"}

    # Use default archive policy (archive).
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\n---\n\nMilestone body\n',
        encoding="utf-8",
    )

    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Root issue"',
                "number: 99",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0

    # Default archive_dir is `.plan/archive/issues`.
    archived = tmp_path / ".plan" / "archive" / "issues" / "stage-1" / "issue.md"
    assert archived.exists()
    assert not issue_path.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_deletes_closed_issue_when_policy_delete(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "closed", "state_reason": "completed"}

    # Override policy at repository level.
    (tmp_path / ".plan").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".plan" / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  closed_issues:",
                "    policy: delete",
            ]
        ),
        encoding="utf-8",
    )

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue-root.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Root"',
                "number: 55",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert not issue_path.exists()
