from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from planhub.documents import (
    DocumentError,
    MilestoneDocument,
    load_milestone_document,
    milestone_document_to_metadata,
    render_markdown,
    update_front_matter,
)
from planhub.github import GitHubClient, IssueState
from planhub.layout import (
    PlanLayout,
    discover_all_milestones,
    find_existing_milestone_dir,
    milestone_dir_for_slug,
)
from planhub.slug import slugify


def milestone_updates_from_github_payload(milestone: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    number = milestone.get("number")
    title = milestone.get("title")
    if isinstance(title, str) and title.strip():
        updates["title"] = title.strip()
    elif isinstance(number, int):
        updates["title"] = str(number)
    if isinstance(number, int):
        updates["number"] = number
    if "description" in milestone:
        description = milestone.get("description")
        updates["description"] = description if isinstance(description, str) else None
    if "due_on" in milestone:
        due_on = milestone.get("due_on")
        updates["due_on"] = due_on if isinstance(due_on, str) else None
    state = milestone.get("state")
    if state == IssueState.OPEN.value:
        updates["state"] = IssueState.OPEN.value
    elif state == IssueState.CLOSED.value:
        updates["state"] = IssueState.CLOSED.value
    return updates


def find_milestone_dir_by_number(layout: PlanLayout, number: int) -> Path | None:
    for entry in discover_all_milestones(layout):
        if not entry.milestone_file.exists():
            continue
        try:
            milestone_doc = load_milestone_document(entry.milestone_file)
        except DocumentError:
            continue
        if milestone_doc.number == number:
            return entry.directory
    return None


def ensure_milestone_from_github(
    layout: PlanLayout,
    milestone: Mapping[str, Any],
    *,
    dry_run: bool,
) -> tuple[Path, bool] | None:
    """Ensure milestone structure exists and reflects the GitHub milestone payload."""
    title = milestone.get("title")
    number = milestone.get("number")
    if (not title or not str(title).strip()) and not isinstance(number, int):
        return None

    slug_source = str(title).strip() if title and str(title).strip() else str(number)
    slug = slugify(slug_source, fallback="milestone")
    milestone_state = milestone.get("state")
    closed = milestone_state == IssueState.CLOSED.value

    milestone_dir: Path | None = None
    if isinstance(number, int):
        milestone_dir = find_milestone_dir_by_number(layout, number)
    if milestone_dir is None:
        milestone_dir = find_existing_milestone_dir(layout, slug)
    if milestone_dir is None:
        milestone_dir = milestone_dir_for_slug(layout, slug, closed=closed)

    created = False
    if not milestone_dir.exists():
        if not dry_run:
            milestone_dir.mkdir(parents=True, exist_ok=True)
        created = True

    milestone_path = milestone_dir / "milestone.md"
    if not milestone_path.exists():
        if not dry_run:
            milestone_doc = _milestone_document_from_github(milestone, milestone_path)
            milestone_path.write_text(
                render_markdown(milestone_document_to_metadata(milestone_doc), ""),
                encoding="utf-8",
            )
        created = True
    else:
        updates = milestone_updates_from_github_payload(milestone)
        if updates and not dry_run:
            update_front_matter(milestone_path, updates)

    issues_dir = milestone_dir / "issues"
    if not issues_dir.exists() and not dry_run:
        issues_dir.mkdir(parents=True, exist_ok=True)
    return issues_dir, created


def reconcile_milestone_states_from_github(
    client: GitHubClient,
    owner: str,
    repo: str,
    layout: PlanLayout,
    *,
    errors: list[str],
    dry_run: bool,
) -> int:
    """Reconcile local milestone.md fields from GitHub milestone state.

    Creates missing local milestone directories for every GitHub milestone
    (including open milestones with only closed issues, empty milestones, and
    closed milestones). Existing local files are updated in place.
    """
    updated_count = 0
    try:
        milestones = client.list_milestones(owner, repo, state="all")
    except Exception as exc:
        errors.append(f"Failed to list GitHub milestones: {exc}")
        return 0

    for milestone in milestones:
        if not isinstance(milestone, Mapping):
            continue
        number = milestone.get("number")
        if not isinstance(number, int):
            continue
        milestone_dir = find_milestone_dir_by_number(layout, number)
        if milestone_dir is None:
            ensured = ensure_milestone_from_github(layout, milestone, dry_run=dry_run)
            if ensured is not None:
                updated_count += 1
            continue
        milestone_path = milestone_dir / "milestone.md"
        if not milestone_path.exists():
            continue
        updates = milestone_updates_from_github_payload(milestone)
        if not updates:
            continue
        if dry_run:
            updated_count += 1
            continue
        if update_front_matter(milestone_path, updates):
            updated_count += 1
    return updated_count


def _milestone_document_from_github(milestone: Mapping[str, Any], path: Path) -> MilestoneDocument:
    state = None
    state_raw = milestone.get("state")
    if isinstance(state_raw, str):
        try:
            state = IssueState(state_raw)
        except ValueError:
            state = None
    description = milestone.get("description")
    due_on = milestone.get("due_on")
    number = milestone.get("number")
    title_raw = milestone.get("title")
    if isinstance(title_raw, str) and title_raw.strip():
        title = title_raw.strip()
    elif isinstance(number, int):
        title = str(number)
    else:
        title = path.parent.name
    return MilestoneDocument(
        path=path,
        title=title,
        description=description if isinstance(description, str) else None,
        due_on=due_on if isinstance(due_on, str) else None,
        state=state,
        milestone_id=None,
        number=number if isinstance(number, int) else None,
        body="",
    )
