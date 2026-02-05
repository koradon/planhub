from planhub.documents import load_issue_document, load_milestone_document
from planhub.importer import import_existing_issues
from planhub.layout import ensure_layout


class DummyClient:
    def __init__(self, issues):
        self._issues = issues

    def list_issues(self, owner, repo, state="open"):
        return self._issues


def test_import_existing_creates_root_and_milestone_issues(tmp_path) -> None:
    issues = [
        {
            "number": 1,
            "title": "Root issue",
            "body": "Body",
            "state": "open",
            "created_at": "2026-01-27T08:00:00Z",
            "labels": [{"name": "p1"}],
            "assignees": [{"login": "alice"}],
        },
        {
            "number": 2,
            "title": "Milestone issue",
            "state": "open",
            "created_at": "2026-01-27T09:00:00Z",
            "milestone": {
                "title": "Stage 1",
                "number": 5,
                "state": "open",
                "description": "Scope",
            },
            "labels": [],
            "assignees": [],
        },
    ]
    layout = ensure_layout(tmp_path)

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(issues),
        dry_run=False,
    )

    assert result.issues_created == 2
    assert result.issues_moved == 0
    root_issue = load_issue_document(layout.issues_dir / "20260127-root-issue.md")
    assert root_issue.title == "Root issue"
    milestone_issue = load_issue_document(
        layout.milestones_dir / "stage-1" / "issues" / "20260127-milestone-issue.md"
    )
    assert milestone_issue.milestone == "Stage 1"
    milestone = load_milestone_document(layout.milestones_dir / "stage-1" / "milestone.md")
    assert milestone.title == "Stage 1"


def test_import_skips_pull_requests(tmp_path) -> None:
    issues = [
        {
            "number": 3,
            "title": "PR",
            "pull_request": {"url": "https://api.github.com/pulls/1"},
        }
    ]
    layout = ensure_layout(tmp_path)

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(issues),
        dry_run=False,
    )

    assert result.issues_created == 0
    assert result.issues_moved == 0


def test_import_skips_existing_issue_number(tmp_path) -> None:
    issues = [
        {
            "number": 4,
            "title": "Existing issue",
            "created_at": "2026-01-27T10:00:00Z",
            "milestone": {
                "title": "Stage 1",
                "number": 5,
                "state": "open",
                "description": "Scope",
            },
            "labels": [],
            "assignees": [],
        }
    ]
    layout = ensure_layout(tmp_path)
    layout.issues_dir.mkdir(parents=True, exist_ok=True)
    (layout.issues_dir / "issue.md").write_text(
        '---\ntitle: "Existing"\nnumber: 4\n---\n\nBody\n',
        encoding="utf-8",
    )

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(issues),
        dry_run=False,
    )

    assert result.issues_created == 0
    assert result.issues_moved == 1
    assert result.issues_skipped == 0
    assert not (layout.issues_dir / "issue.md").exists()
    assert (layout.milestones_dir / "stage-1" / "issues" / "issue.md").exists()


def test_import_moves_existing_issue_by_content(tmp_path) -> None:
    issues = [
        {
            "number": 7,
            "title": "Doc update",
            "body": "Same body",
            "created_at": "2026-01-27T10:00:00Z",
            "milestone": {
                "title": "Stage 1",
                "number": 5,
                "state": "open",
                "description": "Scope",
            },
            "labels": [],
            "assignees": [],
        }
    ]
    layout = ensure_layout(tmp_path)
    layout.issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Doc update"\n---\n\nSame body\n',
        encoding="utf-8",
    )

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(issues),
        dry_run=False,
    )

    moved_path = layout.milestones_dir / "stage-1" / "issues" / "issue.md"
    assert result.issues_created == 0
    assert result.issues_moved == 1
    assert result.issues_skipped == 0
    assert not issue_path.exists()
    assert moved_path.exists()
    assert load_issue_document(moved_path).number == 7


def test_import_skips_closed_issues(tmp_path) -> None:
    issues = [
        {
            "number": 5,
            "title": "Closed issue",
            "body": "This is closed",
            "state": "closed",
            "state_reason": "completed",
            "created_at": "2026-01-27T10:00:00Z",
            "labels": [],
            "assignees": [],
        }
    ]
    layout = ensure_layout(tmp_path)

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(issues),
        dry_run=False,
    )

    assert result.issues_created == 0
    assert result.issues_skipped == 1
    assert not (layout.issues_dir / "20260127-closed-issue.md").exists()


def test_import_creates_reopened_issues(tmp_path) -> None:
    issues = [
        {
            "number": 6,
            "title": "Reopened issue",
            "body": "This was closed but is now open",
            "state": "open",
            "state_reason": "reopened",
            "created_at": "2026-01-27T10:00:00Z",
            "labels": [],
            "assignees": [],
        }
    ]
    layout = ensure_layout(tmp_path)

    result = import_existing_issues(
        layout,
        "acme",
        "roadmap",
        client=DummyClient(issues),
        dry_run=False,
    )

    assert result.issues_created == 1
    assert result.issues_skipped == 0
    reopened_issue = load_issue_document(layout.issues_dir / "20260127-reopened-issue.md")
    assert reopened_issue.title == "Reopened issue"
    assert reopened_issue.number == 6
