from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.documents import load_milestone_document
from planhub.layout import ensure_layout


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_reopens_archived_milestone_from_github_state(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = [
        {
            "title": "Stage 1",
            "number": 1,
            "state": "open",
            "description": "Scope",
        }
    ]
    client_instance.list_issues.return_value = []
    client_instance.update_issue.return_value = {"state": "open"}
    client_instance.update_milestone.return_value = {"state": "open"}

    layout = ensure_layout(tmp_path)
    archived_milestone_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    archived_milestone_dir.mkdir(parents=True, exist_ok=True)
    (archived_milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n\nMilestone body\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    active_milestone_dir = layout.milestones_dir / "stage-1"
    assert active_milestone_dir.exists()
    milestone = load_milestone_document(active_milestone_dir / "milestone.md")
    assert milestone.state is not None
    assert milestone.state.value == "open"
    assert not archived_milestone_dir.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_imports_new_issue_into_reopened_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = [
        {
            "title": "Stage 1",
            "number": 1,
            "state": "open",
            "description": "Scope",
        }
    ]
    client_instance.list_issues.return_value = [
        {
            "number": 101,
            "title": "New feature",
            "body": "Implement it",
            "state": "open",
            "created_at": "2026-07-09T18:00:00Z",
            "milestone": {
                "title": "Stage 1",
                "number": 1,
                "state": "open",
                "description": "Scope",
            },
            "labels": [],
            "assignees": [],
        }
    ]
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1", "number": 1, "state": "open"},
    }
    client_instance.update_milestone.return_value = {"state": "open"}

    layout = ensure_layout(tmp_path)
    archived_milestone_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    archived_milestone_dir.mkdir(parents=True, exist_ok=True)
    (archived_milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    active_milestone_dir = layout.milestones_dir / "stage-1"
    imported_issue = active_milestone_dir / "issues" / "20260709-new-feature.md"
    assert active_milestone_dir.exists()
    assert imported_issue.exists()
    assert not archived_milestone_dir.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_keeps_closed_issue_inside_open_milestone_directory(
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

    # Milestone issues stay in the milestone directory while milestone is open.
    assert issue_path.exists()
    archived = tmp_path / ".plan" / "archive" / "issues" / "issue.md"
    assert not archived.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_moves_closed_milestone_directory_to_archive(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "open"}
    client_instance.update_milestone.return_value = {"state": "closed"}

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n\nMilestone body\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 99\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert not milestone_dir.exists()
    archived_milestone_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    assert archived_milestone_dir.exists()
    assert (archived_milestone_dir / "issues" / "issue.md").exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_moves_reopened_milestone_directory_back_to_active(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "open"}
    client_instance.update_milestone.return_value = {"state": "open"}

    layout = ensure_layout(tmp_path)
    archived_milestone_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    archived_milestone_dir.mkdir(parents=True, exist_ok=True)
    (archived_milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "open"\n---\n\nMilestone body\n',
        encoding="utf-8",
    )
    issues_dir = archived_milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    (issues_dir / "issue.md").write_text(
        '---\ntitle: "Issue"\nnumber: 99\nstate: "open"\n---\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    active_milestone_dir = layout.milestones_dir / "stage-1"
    assert active_milestone_dir.exists()
    assert (active_milestone_dir / "issues" / "issue.md").exists()
    assert not archived_milestone_dir.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_moves_closed_milestone_when_archive_target_already_exists(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "open"}
    client_instance.update_milestone.return_value = {"state": "closed"}

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "m1-cli-and-documentation-bootstrap"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "M1"\nnumber: 1\nstate: "closed"\n---\n\nCurrent body\n',
        encoding="utf-8",
    )

    archived_dir = (
        tmp_path / ".plan" / "archive" / "milestones" / "m1-cli-and-documentation-bootstrap"
    )
    archived_dir.mkdir(parents=True, exist_ok=True)
    (archived_dir / "milestone.md").write_text(
        '---\ntitle: "M1"\nnumber: 1\nstate: "closed"\n---\n\nArchive body\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert not milestone_dir.exists()
    assert archived_dir.exists()
    assert "Archive body" in (archived_dir / "milestone.md").read_text(encoding="utf-8")


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
