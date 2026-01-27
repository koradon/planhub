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
            "state": "closed",
            "state_reason": "completed",
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
    root_issue = load_issue_document(
        layout.issues_dir / "20260127-root-issue.md"
    )
    assert root_issue.title == "Root issue"
    milestone_issue = load_issue_document(
        layout.milestones_dir
        / "stage-1"
        / "issues"
        / "20260127-milestone-issue.md"
    )
    assert milestone_issue.milestone == "Stage 1"
    milestone = load_milestone_document(
        layout.milestones_dir / "stage-1" / "milestone.md"
    )
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
