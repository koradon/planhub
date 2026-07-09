from __future__ import annotations

import pytest

from planhub.layout import (
    discover_all_milestones,
    discover_milestones,
    discover_root_issues,
    ensure_layout,
    find_existing_milestone_dir,
    load_layout,
    milestone_archive_root,
    milestone_dir_for_slug,
)


def test_load_layout_raises_when_plan_missing(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing .plan directory"):
        load_layout(tmp_path)


def test_load_layout_raises_when_milestones_missing(tmp_path) -> None:
    (tmp_path / ".plan").mkdir()
    (tmp_path / ".plan" / "issues").mkdir()

    with pytest.raises(FileNotFoundError, match="Missing milestones directory"):
        load_layout(tmp_path)


def test_load_layout_raises_when_issues_missing(tmp_path) -> None:
    (tmp_path / ".plan").mkdir()
    (tmp_path / ".plan" / "milestones").mkdir()

    with pytest.raises(FileNotFoundError, match="Missing issues directory"):
        load_layout(tmp_path)


def test_milestone_dir_for_slug_uses_archive_when_closed(tmp_path) -> None:
    layout = ensure_layout(tmp_path)

    active = milestone_dir_for_slug(layout, "stage-1", closed=False)
    archived = milestone_dir_for_slug(layout, "stage-1", closed=True)

    assert active == layout.milestones_dir / "stage-1"
    assert archived == milestone_archive_root(layout) / "stage-1"


def test_find_existing_milestone_dir_prefers_active_over_archive(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    active = layout.milestones_dir / "stage-1"
    archived = milestone_archive_root(layout) / "stage-1"
    active.mkdir(parents=True)
    archived.mkdir(parents=True)

    assert find_existing_milestone_dir(layout, "stage-1") == active


def test_find_existing_milestone_dir_finds_archive_when_active_missing(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    archived = milestone_archive_root(layout) / "stage-1"
    archived.mkdir(parents=True)

    assert find_existing_milestone_dir(layout, "stage-1") == archived


def test_discover_milestones_skips_missing_issues_dir(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir()
    (milestone_dir / "milestone.md").write_text('---\ntitle: "S1"\n---\n', encoding="utf-8")

    entries = discover_milestones(layout)

    assert len(entries) == 1
    assert entries[0].issue_files == ()


def test_discover_all_milestones_includes_active_and_archived(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    active = layout.milestones_dir / "active"
    archived = milestone_archive_root(layout) / "archived"
    for directory, title in ((active, "Active"), (archived, "Archived")):
        directory.mkdir(parents=True)
        (directory / "milestone.md").write_text(f'---\ntitle: "{title}"\n---\n', encoding="utf-8")
        issues = directory / "issues"
        issues.mkdir()
        (issues / "issue.md").write_text(f'---\ntitle: "{title} issue"\n---\n', encoding="utf-8")

    entries = discover_all_milestones(layout)

    assert {entry.directory.name for entry in entries} == {"active", "archived"}
    assert all(entry.issue_files for entry in entries)


def test_discover_root_issues_returns_sorted_paths(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    (layout.issues_dir / "b-issue.md").write_text('---\ntitle: "B"\n---\n', encoding="utf-8")
    (layout.issues_dir / "a-issue.md").write_text('---\ntitle: "A"\n---\n', encoding="utf-8")

    issues = discover_root_issues(layout)

    assert [path.name for path in issues] == ["a-issue.md", "b-issue.md"]
