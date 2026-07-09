from __future__ import annotations

from planhub.layout import ensure_layout
from planhub.milestone_sync import (
    ensure_milestone_from_github,
    find_milestone_dir_by_number,
    milestone_updates_from_github_payload,
    reconcile_milestone_states_from_github,
)


class ExplodingClient:
    def list_milestones(self, owner, repo, state="all"):
        raise RuntimeError("network down")


def test_milestone_updates_from_github_payload_handles_null_description() -> None:
    updates = milestone_updates_from_github_payload(
        {"title": "Stage 1", "number": 1, "description": None, "state": "closed"}
    )

    assert updates["description"] is None
    assert updates["state"] == "closed"


def test_ensure_milestone_from_github_returns_none_without_title_or_number(tmp_path) -> None:
    layout = ensure_layout(tmp_path)

    assert ensure_milestone_from_github(layout, {"title": ""}, dry_run=False) is None


def test_ensure_milestone_from_github_dry_run_does_not_write(tmp_path) -> None:
    layout = ensure_layout(tmp_path)

    ensured = ensure_milestone_from_github(
        layout,
        {"title": "Stage 1", "number": 1, "state": "open"},
        dry_run=True,
    )

    assert ensured is not None
    assert ensured[1] is True
    assert not (layout.milestones_dir / "stage-1").exists()


def test_find_milestone_dir_by_number_skips_invalid_documents(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text("not yaml", encoding="utf-8")

    assert find_milestone_dir_by_number(layout, 1) is None


def test_reconcile_milestone_states_from_github_reports_list_failure(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n',
        encoding="utf-8",
    )
    errors: list[str] = []

    updated = reconcile_milestone_states_from_github(
        ExplodingClient(),
        "acme",
        "roadmap",
        layout,
        errors=errors,
        dry_run=False,
    )

    assert updated == 0
    assert errors and "Failed to list GitHub milestones" in errors[0]


def test_reconcile_milestone_states_from_github_skips_unknown_local_milestones(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    client = type(
        "Client",
        (),
        {
            "list_milestones": lambda self, owner, repo, state="all": [
                {"title": "GH only", "number": 99, "state": "open"}
            ]
        },
    )()
    errors: list[str] = []

    updated = reconcile_milestone_states_from_github(
        client,
        "acme",
        "roadmap",
        layout,
        errors=errors,
        dry_run=False,
    )

    assert updated == 0
    assert errors == []


def test_reconcile_milestone_states_from_github_dry_run_counts_without_writing(tmp_path) -> None:
    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True)
    milestone_path = milestone_dir / "milestone.md"
    milestone_path.write_text(
        '---\ntitle: "Stage 1"\nnumber: 1\nstate: "closed"\n---\n',
        encoding="utf-8",
    )
    client = type(
        "Client",
        (),
        {
            "list_milestones": lambda self, owner, repo, state="all": [
                {"title": "Stage 1", "number": 1, "state": "open"}
            ]
        },
    )()
    errors: list[str] = []

    updated = reconcile_milestone_states_from_github(
        client,
        "acme",
        "roadmap",
        layout,
        errors=errors,
        dry_run=True,
    )

    assert updated == 1
    assert 'state: "closed"' in milestone_path.read_text(encoding="utf-8")
