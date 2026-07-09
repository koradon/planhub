from __future__ import annotations

from planhub.importer import import_existing_issues
from planhub.layout import ensure_layout


class DummyClient:
    def __init__(self, issues):
        self._issues = issues

    def list_issues(self, owner, repo, state="all"):
        return self._issues


def test_import_skips_issue_without_number(tmp_path) -> None:
    layout = ensure_layout(tmp_path)

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient([{"title": "No number", "state": "open"}]),
        dry_run=False,
    )

    assert result.issues_skipped == 1
    assert result.issues_created == 0


def test_import_skips_when_issue_number_already_tracked(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    existing = layout.issues_dir / "issue.md"
    existing.write_text('---\ntitle: "Root issue"\nnumber: 1\n---\n', encoding="utf-8")

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(
            [
                {
                    "number": 1,
                    "title": "Root issue",
                    "body": "Body",
                    "state": "open",
                    "created_at": "2026-01-27T08:00:00Z",
                    "labels": [],
                    "assignees": [],
                }
            ]
        ),
        dry_run=False,
    )

    assert result.issues_created == 0
    assert result.issues_skipped == 1


def test_import_dry_run_counts_without_writing(tmp_path) -> None:
    layout = ensure_layout(tmp_path)

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(
            [
                {
                    "number": 2,
                    "title": "New issue",
                    "body": "Body",
                    "state": "open",
                    "created_at": "2026-01-27T09:00:00Z",
                    "labels": [],
                    "assignees": [],
                }
            ]
        ),
        dry_run=True,
    )

    assert result.issues_created == 1
    assert not list(layout.issues_dir.glob("*.md"))


def test_import_skips_existing_issue_when_move_target_already_exists(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 5\nstate: "open"\n---\n',
        encoding="utf-8",
    )
    (issues_dir / "issue.md").write_text(
        '---\ntitle: "Existing"\nnumber: 4\n---\n', encoding="utf-8"
    )
    root_issue = layout.issues_dir / "issue.md"
    root_issue.write_text('---\ntitle: "Existing"\nnumber: 4\n---\n', encoding="utf-8")

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(
            [
                {
                    "number": 4,
                    "title": "Existing",
                    "created_at": "2026-01-27T10:00:00Z",
                    "milestone": {
                        "title": "Stage 1",
                        "number": 5,
                        "state": "open",
                    },
                    "labels": [],
                    "assignees": [],
                }
            ]
        ),
        dry_run=False,
    )

    assert result.issues_moved == 0
    assert result.issues_skipped == 1
    assert root_issue.exists()


def test_import_uses_suffix_when_generated_filename_collides(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    (layout.issues_dir / "20260127-new-issue.md").write_text("existing", encoding="utf-8")

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(
            [
                {
                    "number": 8,
                    "title": "New issue",
                    "body": "Body",
                    "state": "open",
                    "created_at": "2026-01-27T08:00:00Z",
                    "labels": [],
                    "assignees": [],
                }
            ]
        ),
        dry_run=False,
    )

    assert result.issues_created == 1
    assert (layout.issues_dir / "20260127-new-issue-8.md").exists()
