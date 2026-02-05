from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app


def test_init_creates_layout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert (tmp_path / ".plan" / "milestones").is_dir()
    assert (tmp_path / ".plan" / "issues").is_dir()
    assert "Initialized plan layout" in result.output


def test_init_dry_run_does_not_create_layout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["init", "--dry-run"])

    assert result.exit_code == 0
    assert not (tmp_path / ".plan").exists()
    assert "Dry run" in result.output


def test_sync_requires_layout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Run 'planhub init' first." in result.output


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_reports_counts(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch, capsys
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    mock_client.return_value.update_issue.return_value = {}
    mock_client.return_value.update_milestone.return_value = {}
    monkeypatch.chdir(tmp_path)
    _create_milestone(
        tmp_path / ".plan" / "milestones" / "stage-1",
        milestone_title="Stage 1",
        milestone_number=1,
        issue_names=("issue-001.md",),
    )
    _create_milestone(
        tmp_path / ".plan" / "milestones" / "stage-2",
        milestone_title="Stage 2",
        milestone_number=2,
    )
    _create_root_issue(tmp_path / ".plan" / "issues" / "issue-root.md", number=10)

    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Found 2 milestones and 2 issues." in result.output


def test_sync_dry_run_reports_counts(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    _create_milestone(
        tmp_path / ".plan" / "milestones" / "stage-1",
        milestone_title="Stage 1",
    )
    _create_root_issue(tmp_path / ".plan" / "issues" / "issue-root.md")

    runner = CliRunner()
    result = runner.invoke(app, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run: no changes will be written." in result.output
    assert "Found 1 milestones and 1 issues." in result.output


def test_sync_rejects_state_reason_without_closed_state(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".plan" / "milestones").mkdir(parents=True, exist_ok=True)
    _create_root_issue(
        tmp_path / ".plan" / "issues" / "issue-root.md", number=10, state_reason=True
    )

    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "state_reason requires state='closed'" in result.output


@patch("planhub.cli.commands.issue.datetime")
@patch("planhub.cli.commands.issue.get_github_repo_from_git")
@patch("planhub.cli.commands.issue.get_auth_token")
@patch("planhub.cli.commands.issue.GitHubClient")
def test_issue_command_success(
    mock_client, mock_token, mock_repo, mock_datetime, tmp_path, monkeypatch
) -> None:
    mock_now = mock_datetime.now.return_value
    mock_now.strftime.return_value = "20240115"
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    mock_client.return_value.create_issue.return_value = {
        "number": 42,
        "html_url": "https://github.com/acme/roadmap/issues/42",
        "state": "open",
        "assignees": [],
    }
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["issue", "Test Issue Title"])

    assert result.exit_code == 0
    assert "Created issue #42: Test Issue Title" in result.output
    assert "View at: https://github.com/acme/roadmap/issues/42" in result.output
    assert "Saved to:" in result.output
    mock_client.return_value.create_issue.assert_called_once_with(
        owner="acme", repo="roadmap", title="Test Issue Title"
    )

    # Verify the file was created in .plan/issues/
    issue_files = list((tmp_path / ".plan" / "issues").glob("*.md"))
    assert len(issue_files) == 1
    issue_file = issue_files[0]
    assert issue_file.name == "20240115-test-issue-title.md"

    # Verify the file content
    content = issue_file.read_text(encoding="utf-8")
    assert "title: Test Issue Title" in content
    assert "number: 42" in content
    assert "state: open" in content
    assert "assignees: []" in content


@patch("planhub.cli.commands.issue.get_auth_token", return_value=None)
def test_issue_command_no_token(mock_token, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["issue", "Test Issue"])

    assert result.exit_code == 1
    assert "No GitHub token found" in result.output


@patch("planhub.cli.commands.issue.get_github_repo_from_git")
@patch("planhub.cli.commands.issue.get_auth_token", return_value="token")
def test_issue_command_no_git_remote(mock_token, mock_repo, tmp_path, monkeypatch) -> None:
    mock_repo.side_effect = ValueError("Missing git remote origin URL.")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["issue", "Test Issue"])

    assert result.exit_code == 1
    assert "Missing git remote origin URL" in result.output


@patch("planhub.cli.commands.issue.datetime")
@patch("planhub.cli.commands.issue.get_github_repo_from_git")
@patch("planhub.cli.commands.issue.get_auth_token")
@patch("planhub.cli.commands.issue.GitHubClient")
def test_issue_command_handles_filename_conflicts(
    mock_client, mock_token, mock_repo, mock_datetime, tmp_path, monkeypatch
) -> None:
    mock_now = mock_datetime.now.return_value
    mock_now.strftime.return_value = "20240115"
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")

    # First issue
    mock_client.return_value.create_issue.side_effect = [
        {
            "number": 42,
            "html_url": "https://github.com/acme/roadmap/issues/42",
            "state": "open",
            "assignees": [],
        },
        # Second issue with same title
        {
            "number": 43,
            "html_url": "https://github.com/acme/roadmap/issues/43",
            "state": "open",
            "assignees": [],
        },
    ]
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()

    # Create first issue
    result1 = runner.invoke(app, ["issue", "Test Issue"])
    assert result1.exit_code == 0
    assert "Created issue #42: Test Issue" in result1.output

    # Create second issue with same title
    result2 = runner.invoke(app, ["issue", "Test Issue"])
    assert result2.exit_code == 0
    assert "Created issue #43: Test Issue" in result2.output

    # Verify both files exist with correct names
    issue_files = sorted((tmp_path / ".plan" / "issues").glob("*.md"))
    assert len(issue_files) == 2
    assert issue_files[0].name == "20240115-test-issue-43.md"
    assert issue_files[1].name == "20240115-test-issue.md"

    # Verify first file content
    content1 = issue_files[0].read_text(encoding="utf-8")
    assert "title: Test Issue" in content1
    assert "number: 43" in content1

    # Verify second file content (with appended issue number)
    content2 = issue_files[1].read_text(encoding="utf-8")
    assert "title: Test Issue" in content2
    assert "number: 42" in content2


def _create_milestone(
    directory: Path,
    milestone_title: str,
    milestone_number: int | None = None,
    issue_names: tuple[str, ...] = (),
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    milestone_lines = ["---", f'title: "{milestone_title}"']
    if milestone_number is not None:
        milestone_lines.append(f"number: {milestone_number}")
    milestone_lines.append("---")
    milestone_lines.append("")
    milestone_lines.append("# Milestone")
    (directory / "milestone.md").write_text("\n".join(milestone_lines), encoding="utf-8")
    if issue_names:
        issues_dir = directory / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        for index, name in enumerate(issue_names, start=1):
            (issues_dir / name).write_text(
                f'---\ntitle: "Issue {index}"\nnumber: {index}\n---\n\n# Issue\n',
                encoding="utf-8",
            )


def _create_root_issue(path: Path, number: int | None = None, state_reason: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'title: "Root Issue"']
    if number is not None:
        lines.append(f"number: {number}")
    if state_reason:
        lines.append('state_reason: "completed"')
    lines.append("---")
    lines.append("")
    lines.append("# Issue")
    path.write_text("\n".join(lines), encoding="utf-8")
