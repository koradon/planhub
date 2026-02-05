from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.documents import load_issue_document, load_milestone_document
from planhub.layout import ensure_layout


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_creates_missing_issue_and_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.create_milestone.return_value = {"number": 7}
    client_instance.create_issue.return_value = {"number": 21}

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\n---\n\nMilestone body\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = issues_dir / "issue-001.md"
    issue_path.write_text(
        '---\ntitle: "Ship it"\nstate: "closed"\n---\n\nIssue body\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    milestone = load_milestone_document(milestone_dir / "milestone.md")
    issue = load_issue_document(issue_path)
    assert milestone.number == 7
    assert issue.number == 21
    client_instance.update_issue_state.assert_called_once()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_updates_existing_issue(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Ship it"\nnumber: 99\nassignees: [alice]\n---\n\nBody\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    client_instance.update_issue.assert_called_once()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_clears_labels_assignees_and_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "labels: []",
                "assignees: []",
                "milestone: null",
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
    kwargs = client_instance.update_issue.call_args.kwargs
    assert kwargs["labels"] == []
    assert kwargs["assignees"] == []
    assert kwargs["clear_milestone"] is True


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_uses_numeric_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: 7",
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
    kwargs = client_instance.update_issue.call_args.kwargs
    assert kwargs["milestone"] == 7
