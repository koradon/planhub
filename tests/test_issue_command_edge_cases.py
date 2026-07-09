from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.github import GitHubAPIError


@patch("planhub.cli.commands.issue.get_github_repo_from_git", return_value=("acme", "roadmap"))
@patch("planhub.cli.commands.issue.get_auth_token", return_value="token")
@patch("planhub.cli.commands.issue.GitHubClient")
def test_issue_command_reports_github_api_error(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_client.return_value.create_issue.side_effect = GitHubAPIError(
        status_code=401,
        message="Bad credentials",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["issue", "Broken auth"])

    assert result.exit_code == 1
    assert "Error creating issue" in result.output
    assert "Bad credentials" in result.output
