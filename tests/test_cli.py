from pathlib import Path

from planhub.cli import main


def test_init_creates_layout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init"])

    assert exit_code == 0
    assert (tmp_path / ".plan" / "milestones").is_dir()
    captured = capsys.readouterr()
    assert "Initialized plan layout" in captured.out


def test_init_dry_run_does_not_create_layout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init", "--dry-run"])

    assert exit_code == 0
    assert not (tmp_path / ".plan").exists()
    captured = capsys.readouterr()
    assert "Dry run" in captured.out


def test_sync_requires_layout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["sync"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Run 'planhub init' first." in captured.out


def test_sync_reports_counts(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    _create_milestone(
        tmp_path / ".plan" / "milestones" / "stage-1",
        milestone_title="Stage 1",
        issue_names=("issue-001.md",),
    )
    _create_milestone(
        tmp_path / ".plan" / "milestones" / "stage-2",
        milestone_title="Stage 2",
    )

    exit_code = main(["sync"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Found 2 milestones and 1 issues." in captured.out


def test_sync_dry_run_reports_counts(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    _create_milestone(
        tmp_path / ".plan" / "milestones" / "stage-1",
        milestone_title="Stage 1",
    )

    exit_code = main(["sync", "--dry-run"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Dry run: no changes will be written." in captured.out
    assert "Found 1 milestones and 0 issues." in captured.out


def _create_milestone(
    directory: Path,
    milestone_title: str,
    issue_names: tuple[str, ...] = (),
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "milestone.md").write_text(
        f"---\ntitle: \"{milestone_title}\"\n---\n\n# Milestone\n",
        encoding="utf-8",
    )
    if issue_names:
        issues_dir = directory / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        for index, name in enumerate(issue_names, start=1):
            (issues_dir / name).write_text(
                f"---\ntitle: \"Issue {index}\"\n---\n\n# Issue\n",
                encoding="utf-8",
            )
