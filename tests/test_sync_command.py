from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.layout import ensure_layout


def test_sync_without_plan_layout_exits(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Run 'planhub init' first" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
def test_sync_without_auth_still_runs_local_reconcile(
    mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = None
    ensure_layout(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Sync completed" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_dry_run_reports_plan_without_writing(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = []
    client_instance.list_issues.return_value = []

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text('---\ntitle: "Ship it"\nnumber: 1\n---\n\nBody\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert issue_path.exists()
    assert "would update 1" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_verbose_lists_planned_changes(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.list_milestones.return_value = []
    client_instance.list_issues.return_value = []

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text('---\ntitle: "Stage 1"\n---\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync", "--dry-run", "--verbose"])

    assert result.exit_code == 0
    assert "[verbose] Planned changes" in result.output
    assert "milestone create" in result.output


@patch("planhub.cli.commands.sync.pull.reconcile_milestone_states_from_github")
@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_reports_milestone_reconcile_errors(
    mock_client,
    mock_token,
    mock_repo,
    mock_reconcile_milestones,
    tmp_path,
    monkeypatch,
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    mock_client.return_value.list_milestones.return_value = []
    mock_client.return_value.list_issues.return_value = []

    def _fail_reconcile(*args, **kwargs):
        kwargs["errors"].append("Failed to list GitHub milestones: boom")

    mock_reconcile_milestones.side_effect = _fail_reconcile
    ensure_layout(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Failed to list GitHub milestones" in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_reports_parse_errors_before_apply(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    mock_client.return_value.list_milestones.return_value = []
    mock_client.return_value.list_issues.return_value = []

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "broken"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text("---\nlabels: [x]\n---\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Missing or invalid 'title'" in result.output
