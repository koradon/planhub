from __future__ import annotations

from pathlib import Path

from planhub.cli.sync_plan import (
    _state_updates_from_github_issue,
    archive_closed_issues_in_filesystem,
    reconcile_milestone_archive_locations,
)
from planhub.config import (
    PlanHubConfig,
    SyncBehaviorConfig,
    SyncClosedIssuesConfig,
    SyncConfig,
    SyncGithubConfig,
)
from planhub.layout import ensure_layout


def _config(*, policy: str, archive_dir: Path) -> PlanHubConfig:
    return PlanHubConfig(
        sync=SyncConfig(
            closed_issues=SyncClosedIssuesConfig(policy=policy, archive_dir=archive_dir),
            github=SyncGithubConfig(default_assignees=(), default_labels=()),
            behavior=SyncBehaviorConfig(dry_run=False, verbosity="compact"),
        )
    )


def test_archive_closed_issues_dry_run_does_not_move(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 1\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )
    cfg = _config(policy="archive", archive_dir=tmp_path / ".plan" / "archive" / "issues")
    errors: list[str] = []

    stats = archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=True)

    assert issue_path.exists()
    assert errors == []
    assert stats.archived_count == 1
    assert stats.deleted_count == 0


def test_archive_closed_issues_skips_unsynced_issue(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )
    cfg = _config(policy="archive", archive_dir=tmp_path / ".plan" / "archive" / "issues")
    errors: list[str] = []

    stats = archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=False)

    assert issue_path.exists()
    assert not (tmp_path / ".plan" / "archive" / "issues" / "issue.md").exists()
    assert errors == []
    assert stats.archived_count == 0
    assert stats.deleted_count == 0


def test_archive_closed_issues_skips_milestone_issues(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "open"\n---\n',
        encoding="utf-8",
    )
    issue_path = milestone_dir / "issues" / "issue.md"
    issue_path.parent.mkdir(parents=True, exist_ok=True)
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 1\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )
    cfg = _config(policy="archive", archive_dir=tmp_path / ".plan" / "archive" / "issues")
    errors: list[str] = []

    archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=False)

    assert issue_path.exists()
    assert not (tmp_path / ".plan" / "archive" / "issues" / "issue.md").exists()
    assert errors == []


def test_archive_closed_issues_unsupported_policy_reports_error(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 1\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )
    cfg = _config(policy="invalid", archive_dir=tmp_path / ".plan" / "archive" / "issues")
    errors: list[str] = []

    stats = archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=False)

    assert issue_path.exists()
    assert len(errors) == 1
    assert "Unsupported closed issue policy" in errors[0]
    assert stats.archived_count == 0
    assert stats.deleted_count == 0


def test_archive_closed_issues_duplicate_target_gets_suffix(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 1\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )
    archive_dir = tmp_path / ".plan" / "archive" / "issues"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "issue.md").write_text("existing", encoding="utf-8")
    cfg = _config(policy="archive", archive_dir=archive_dir)
    errors: list[str] = []

    stats = archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=False)

    assert not issue_path.exists()
    assert (archive_dir / "issue.md").read_text(encoding="utf-8") == "existing"
    assert (archive_dir / "issue-1.md").exists()
    assert errors == []
    assert stats.archived_count == 1
    assert stats.deleted_count == 0


def test_archive_closed_issues_exhausts_suffixes_reports_error(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 1\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )

    archive_dir = tmp_path / ".plan" / "archive" / "issues"
    archive_dir.mkdir(parents=True, exist_ok=True)

    (archive_dir / "issue.md").write_text("existing-0", encoding="utf-8")
    for index in range(1, 1000):
        (archive_dir / f"issue-{index}.md").write_text(
            f"existing-{index}",
            encoding="utf-8",
        )

    cfg = _config(policy="archive", archive_dir=archive_dir)
    errors: list[str] = []

    stats = archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=False)

    # Must not overwrite existing archive files when all suffixes are taken.
    assert issue_path.exists()
    assert errors and len(errors) == 1
    assert "all suffixes 1..999 are taken" in errors[0]
    assert (archive_dir / "issue.md").read_text(encoding="utf-8") == "existing-0"
    assert stats.archived_count == 0
    assert stats.deleted_count == 0


def test_archive_closed_issues_delete_policy_counts_deletions(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Issue"\nnumber: 1\nstate: "closed"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )
    cfg = _config(policy="delete", archive_dir=tmp_path / ".plan" / "archive" / "issues")
    errors: list[str] = []

    stats = archive_closed_issues_in_filesystem(layout, cfg, errors=errors, dry_run=False)

    assert not issue_path.exists()
    assert errors == []
    assert stats.deleted_count == 1
    assert stats.archived_count == 0


def test_reconcile_closed_milestone_discards_active_duplicate_when_archive_exists(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n\nDuplicate body\n',
        encoding="utf-8",
    )

    archived_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    archived_dir.mkdir(parents=True, exist_ok=True)
    (archived_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n\nArchive body\n',
        encoding="utf-8",
    )

    errors: list[str] = []
    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=False,
        move_open_to_active=False,
        move_closed_to_archive=True,
    )

    assert errors == []
    assert not milestone_dir.exists()
    assert archived_dir.exists()
    assert "Archive body" in (archived_dir / "milestone.md").read_text(encoding="utf-8")


def test_reconcile_reopened_milestone_replaces_stale_active_duplicate(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    active_dir = layout.milestones_dir / "stage-1"
    active_dir.mkdir(parents=True, exist_ok=True)
    (active_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n\nStale body\n',
        encoding="utf-8",
    )

    archived_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    archived_dir.mkdir(parents=True, exist_ok=True)
    (archived_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "open"\n---\n\nCurrent body\n',
        encoding="utf-8",
    )

    errors: list[str] = []
    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=False,
        move_open_to_active=True,
        move_closed_to_archive=False,
    )

    assert errors == []
    assert active_dir.exists()
    assert not archived_dir.exists()
    assert "Current body" in (active_dir / "milestone.md").read_text(encoding="utf-8")


def test_reconcile_closed_milestone_collision_dry_run_reports_no_error(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n',
        encoding="utf-8",
    )

    archived_dir = tmp_path / ".plan" / "archive" / "milestones" / "stage-1"
    archived_dir.mkdir(parents=True, exist_ok=True)
    (archived_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n',
        encoding="utf-8",
    )

    errors: list[str] = []
    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=True,
        move_open_to_active=False,
        move_closed_to_archive=True,
    )

    assert errors == []
    assert milestone_dir.exists()
    assert archived_dir.exists()


def test_state_updates_from_github_issue_handles_open_and_closed_reason() -> None:
    assert _state_updates_from_github_issue({"state": "open"}) == {
        "state": "open",
        "state_reason": None,
    }
    assert _state_updates_from_github_issue({"state": "closed", "state_reason": "completed"}) == {
        "state": "closed",
        "state_reason": "completed",
    }


def test_state_updates_from_github_issue_invalid_payload_returns_empty() -> None:
    assert _state_updates_from_github_issue(object()) == {}
    assert _state_updates_from_github_issue({"state": "something"}) == {}
