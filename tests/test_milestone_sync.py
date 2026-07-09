from __future__ import annotations

from planhub.documents import load_milestone_document
from planhub.layout import ensure_layout
from planhub.milestone_sync import (
    ensure_milestone_from_github,
    milestone_updates_from_github_payload,
    reconcile_milestone_states_from_github,
)


class DummyMilestoneClient:
    def __init__(self, milestones):
        self._milestones = milestones

    def list_milestones(self, owner, repo, state="all"):
        return self._milestones


def test_milestone_updates_from_github_payload_includes_state() -> None:
    updates = milestone_updates_from_github_payload(
        {
            "title": "Stage 1",
            "number": 5,
            "state": "open",
            "description": "Scope",
        }
    )

    assert updates == {
        "title": "Stage 1",
        "number": 5,
        "description": "Scope",
        "state": "open",
    }


def test_reconcile_milestone_states_from_github_updates_archived_milestone(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    archived_dir = layout.root / "archive" / "milestones" / "stage-1"
    archived_dir.mkdir(parents=True, exist_ok=True)
    milestone_path = archived_dir / "milestone.md"
    milestone_path.write_text(
        '---\ntitle: "Stage 1"\nnumber: 5\nstate: "closed"\n---\n',
        encoding="utf-8",
    )

    client = DummyMilestoneClient(
        [
            {
                "title": "Stage 1",
                "number": 5,
                "state": "open",
                "description": "Scope",
            }
        ]
    )
    errors: list[str] = []

    updated = reconcile_milestone_states_from_github(
        client,
        "acme",
        "roadmap",
        layout,
        errors=errors,
        dry_run=False,
    )

    assert errors == []
    assert updated == 1
    milestone = load_milestone_document(milestone_path)
    assert milestone.state is not None
    assert milestone.state.value == "open"
    assert milestone.description == "Scope"


def test_ensure_milestone_from_github_updates_existing_archived_milestone(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    archived_dir = layout.root / "archive" / "milestones" / "stage-1"
    archived_dir.mkdir(parents=True, exist_ok=True)
    milestone_path = archived_dir / "milestone.md"
    milestone_path.write_text(
        '---\ntitle: "Stage 1"\nnumber: 5\nstate: "closed"\n---\n',
        encoding="utf-8",
    )

    ensured = ensure_milestone_from_github(
        layout,
        {
            "title": "Stage 1",
            "number": 5,
            "state": "open",
            "description": "Scope",
        },
        dry_run=False,
    )

    assert ensured is not None
    issues_dir, created = ensured
    assert created is False
    assert issues_dir == archived_dir / "issues"
    assert issues_dir.exists()
    milestone = load_milestone_document(milestone_path)
    assert milestone.state is not None
    assert milestone.state.value == "open"
