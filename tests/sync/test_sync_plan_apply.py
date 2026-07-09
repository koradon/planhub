from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from planhub.cli.sync_plan import (
    SyncPlan,
    _github_milestone_info_from_issue_payload,
    _move_issue_to_dir,
    _state_updates_from_github_issue,
    apply_sync_plan,
    build_sync_plan,
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


def _config(archive_dir: Path | None = None) -> PlanHubConfig:
    return PlanHubConfig(
        sync=SyncConfig(
            closed_issues=SyncClosedIssuesConfig(
                policy="archive",
                archive_dir=archive_dir or Path("/tmp/archive"),
            ),
            github=SyncGithubConfig(default_assignees=(), default_labels=()),
            behavior=SyncBehaviorConfig(dry_run=False, verbosity="compact"),
        )
    )


def test_build_sync_plan_reports_missing_milestone_file(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir()

    _, _, _, errors = build_sync_plan(layout)

    assert any("missing milestone.md" in error for error in errors)


def test_build_sync_plan_reports_invalid_issue_state_reason(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text('---\ntitle: "S1"\n---\n', encoding="utf-8")
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir()
    (issues_dir / "issue.md").write_text(
        '---\ntitle: "Bad"\nstate_reason: "completed"\n---\n',
        encoding="utf-8",
    )

    _, _, _, errors = build_sync_plan(layout)

    assert any("state_reason requires state='closed'" in error for error in errors)


def test_build_sync_plan_queues_create_for_unnumbered_milestone(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text('---\ntitle: "S1"\n---\n', encoding="utf-8")

    plan, _, _, errors = build_sync_plan(layout)

    assert errors == []
    assert len(plan.milestones_to_create) == 1
    assert plan.milestones_to_create[0][1].title == "S1"


def test_apply_sync_plan_requires_owner_repo(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    errors: list[str] = []

    stats = apply_sync_plan(MagicMock(), None, SyncPlan(), errors, _config(), layout)

    assert stats.milestones_created == 0
    assert errors == ["Missing repository information for sync."]


def test_apply_sync_plan_reports_missing_milestone_number_on_update(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    milestone_path = milestone_dir / "milestone.md"
    milestone_path.write_text('---\ntitle: "S1"\n---\n', encoding="utf-8")

    plan = SyncPlan()
    from planhub.documents import load_milestone_document

    plan.milestones_to_update.append((milestone_path, load_milestone_document(milestone_path)))
    errors: list[str] = []
    client = MagicMock()

    apply_sync_plan(client, ("acme", "roadmap"), plan, errors, _config(), layout)

    assert any("missing milestone number" in error for error in errors)


def test_apply_sync_plan_create_issue_reports_missing_github_number(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text('---\ntitle: "New"\n---\n\nBody\n', encoding="utf-8")

    plan, _, _, _ = build_sync_plan(layout)
    errors: list[str] = []
    client = MagicMock()
    client.create_issue.return_value = {"state": "open"}

    apply_sync_plan(client, ("acme", "roadmap"), plan, errors, _config(), layout)

    assert any("GitHub did not return a number" in error for error in errors)


def test_move_issue_to_dir_adds_suffix_on_collision(tmp_path) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    source = source_dir / "issue.md"
    target = target_dir / "issue.md"
    source.write_text("source", encoding="utf-8")
    target.write_text("target", encoding="utf-8")

    moved = _move_issue_to_dir(source, target_dir=target_dir)

    assert moved.name == "issue-1.md"
    assert moved.read_text(encoding="utf-8") == "source"
    assert target.read_text(encoding="utf-8") == "target"


def test_move_issue_to_dir_returns_same_path_when_already_in_target(tmp_path) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    issue = target_dir / "issue.md"
    issue.write_text("body", encoding="utf-8")

    moved = _move_issue_to_dir(issue, target_dir=target_dir)

    assert moved == issue


def test_github_milestone_info_treats_missing_field_as_unknown() -> None:
    present, payload, title, number = _github_milestone_info_from_issue_payload({"state": "open"})

    assert present is False
    assert payload is None
    assert title is None
    assert number is None


def test_github_milestone_info_reads_null_milestone_as_cleared() -> None:
    present, payload, title, number = _github_milestone_info_from_issue_payload({"milestone": None})

    assert present is True
    assert payload is None
    assert title is None
    assert number is None


def test_state_updates_from_github_issue_open_clears_reason() -> None:
    assert _state_updates_from_github_issue({"state": "open", "state_reason": "completed"}) == {
        "state": "open",
        "state_reason": None,
    }


def test_apply_sync_plan_create_milestone_reports_missing_github_number(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text('---\ntitle: "S1"\n---\n', encoding="utf-8")

    plan, _, _, _ = build_sync_plan(layout)
    errors: list[str] = []
    client = MagicMock()
    client.create_milestone.return_value = {}

    apply_sync_plan(client, ("acme", "roadmap"), plan, errors, _config(), layout)

    assert any("GitHub did not return a number" in error for error in errors)


def test_apply_sync_plan_create_issue_uses_milestone_number_after_milestone_create(
    tmp_path,
) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text('---\ntitle: "S1"\n---\n', encoding="utf-8")
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir()
    issue_path = issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Needs milestone"\nmilestone: "S1"\n---\n\nBody\n',
        encoding="utf-8",
    )

    plan, _, _, errors = build_sync_plan(layout)
    assert errors == []
    client = MagicMock()
    client.create_milestone.return_value = {"number": 7}
    client.create_issue.return_value = {"number": 42, "state": "open"}

    stats = apply_sync_plan(client, ("acme", "roadmap"), plan, errors, _config(), layout)

    assert stats.milestones_created == 1
    assert stats.issues_created == 1
    client.create_issue.assert_called_once()
    assert client.create_issue.call_args.kwargs["milestone"] == 7


def test_apply_sync_plan_create_issue_reports_missing_milestone_mapping(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Orphan"\nmilestone: "Missing"\n---\n\nBody\n',
        encoding="utf-8",
    )

    plan, _, _, errors = build_sync_plan(layout)
    assert errors == []
    client = MagicMock()

    stats = apply_sync_plan(client, ("acme", "roadmap"), plan, errors, _config(), layout)

    assert stats.issues_created == 0
    client.create_issue.assert_not_called()
    assert any("has no number" in error for error in errors)


def test_reconcile_reports_invalid_milestone_document(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text("---\nlabels: [x]\n---\n", encoding="utf-8")
    errors: list[str] = []

    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=False,
        move_open_to_active=False,
        move_closed_to_archive=True,
    )

    assert any("Missing or invalid 'title'" in error for error in errors)


def test_reconcile_closed_milestone_dry_run_leaves_directories_in_place(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "S1"\nnumber: 1\nstate: "closed"\n---\n',
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

    assert milestone_dir.exists()
    assert errors == []
