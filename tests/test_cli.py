from pathlib import Path

from typer.testing import CliRunner
from unittest.mock import patch

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


def _create_milestone(
    directory: Path,
    milestone_title: str,
    milestone_number: int | None = None,
    issue_names: tuple[str, ...] = (),
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    milestone_lines = ["---", f"title: \"{milestone_title}\""]
    if milestone_number is not None:
        milestone_lines.append(f"number: {milestone_number}")
    milestone_lines.append("---")
    milestone_lines.append("")
    milestone_lines.append("# Milestone")
    (directory / "milestone.md").write_text(
        "\n".join(milestone_lines), encoding="utf-8"
    )
    if issue_names:
        issues_dir = directory / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        for index, name in enumerate(issue_names, start=1):
            (issues_dir / name).write_text(
                f"---\ntitle: \"Issue {index}\"\nnumber: {index}\n---\n\n# Issue\n",
                encoding="utf-8",
            )


def _create_root_issue(path: Path, number: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'title: "Root Issue"']
    if number is not None:
        lines.append(f"number: {number}")
    lines.append("---")
    lines.append("")
    lines.append("# Issue")
    path.write_text("\n".join(lines), encoding="utf-8")
