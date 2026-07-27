from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.documents import load_issue_document
from planhub.layout import ensure_layout


def test_pull_without_plan_layout_exits(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["pull"])

    assert result.exit_code == 1
    assert "Run 'planhub init' first" in result.output


def test_push_without_plan_layout_exits(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push"])

    assert result.exit_code == 1
    assert "Run 'planhub init' first" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
def test_pull_without_auth_still_runs_local_reconcile(
    mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = None
    ensure_layout(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["pull"])

    assert result.exit_code == 0
    assert "Pull completed" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_pull_imports_issue_and_never_writes_to_github(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = []
    client_instance.list_issues.return_value = [
        {
            "number": 1,
            "title": "Remote issue",
            "body": "Body",
            "state": "open",
            "created_at": "2026-01-27T08:00:00Z",
            "labels": [],
            "assignees": [],
        }
    ]

    layout = ensure_layout(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["pull"])

    assert result.exit_code == 0
    assert (layout.issues_dir / "20260127-remote-issue.md").exists()
    client_instance.create_issue.assert_not_called()
    client_instance.update_issue.assert_not_called()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_pull_force_rewrites_existing_issue_preserving_local_only_key(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = []
    client_instance.list_issues.return_value = [
        {
            "number": 4,
            "title": "Fresh title",
            "body": "Fresh body",
            "state": "open",
            "created_at": "2026-01-27T10:00:00Z",
            "labels": [],
            "assignees": [],
        }
    ]

    layout = ensure_layout(tmp_path)
    layout.issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Stale title"\nid: "local-only"\nnumber: 4\n---\n\nStale body.\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["pull", "--force"])

    assert result.exit_code == 0
    issue = load_issue_document(issue_path)
    assert issue.title == "Fresh title"
    assert issue.body == "Fresh body"
    assert issue.issue_id == "local-only"


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_pull_force_dry_run_reports_without_writing(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = []
    client_instance.list_issues.return_value = [
        {
            "number": 4,
            "title": "Fresh title",
            "body": "Fresh body",
            "state": "open",
            "created_at": "2026-01-27T10:00:00Z",
            "labels": [],
            "assignees": [],
        }
    ]

    layout = ensure_layout(tmp_path)
    layout.issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Stale title"\nnumber: 4\n---\n\nStale body.\n',
        encoding="utf-8",
    )
    original = issue_path.read_text(encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["pull", "--force", "--dry-run"])

    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "overwrite 1" in result.output
    assert issue_path.read_text(encoding="utf-8") == original


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_push_creates_issue_and_writes_number_back(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.create_issue.return_value = {"number": 9}

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text('---\ntitle: "New issue"\n---\n\nBody\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push"])

    assert result.exit_code == 0
    assert "Push completed" in result.output
    assert load_issue_document(issue_path).number == 9


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_push_never_imports_from_github(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.create_issue.return_value = {"number": 9}

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text('---\ntitle: "New issue"\n---\n\nBody\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push"])

    assert result.exit_code == 0
    client_instance.list_issues.assert_not_called()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_push_dry_run_reports_plan_without_writing(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text('---\ntitle: "New issue"\n---\n\nBody\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push", "--dry-run"])

    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "would create 1" in result.output
    assert load_issue_document(issue_path).number is None
    mock_client.return_value.create_issue.assert_not_called()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_push_archives_closed_root_issue(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "closed", "state_reason": "completed"}

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Root"\nnumber: 55\n---\n\nBody\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push"])

    assert result.exit_code == 0
    assert not issue_path.exists()
    archived_path = tmp_path / ".plan" / "archive" / "issues" / "issue.md"
    assert archived_path.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
def test_push_with_pending_writes_and_no_auth_exits(
    mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = None

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text('---\ntitle: "New issue"\n---\n\nBody\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push"])

    assert result.exit_code == 1
    assert "Missing GitHub credentials" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
def test_push_without_pending_writes_and_no_auth_still_succeeds(
    mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = None
    ensure_layout(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["push"])

    assert result.exit_code == 0
    assert "Push completed" in result.output
