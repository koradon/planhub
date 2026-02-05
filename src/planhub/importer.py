from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from planhub.documents import (
    DocumentError,
    IssueDocument,
    MilestoneDocument,
    load_issue_document,
    render_markdown,
    update_front_matter,
)
from planhub.layout import PlanLayout, discover_milestones, discover_root_issues


@dataclass(frozen=True)
class ImportResult:
    issues_created: int
    issues_moved: int
    milestones_created: int
    issues_skipped: int


def import_existing_issues(
    layout: PlanLayout,
    owner: str,
    repo: str,
    *,
    client: Any,
    dry_run: bool,
) -> ImportResult:
    issues = client.list_issues(owner, repo, state="all")
    issues_created = 0
    issues_moved = 0
    milestones_created = 0
    issues_skipped = 0
    existing_issues = _collect_existing_issues(layout)
    existing_by_content = _collect_existing_by_content(layout)

    for issue in issues:
        if issue.get("pull_request"):
            continue

        number = issue.get("number")
        if not number:
            issues_skipped += 1
            continue

        milestone = issue.get("milestone")
        milestone_title = None
        milestone_dir = None
        if milestone:
            milestone_title = milestone.get("title")
            if milestone_title:
                milestone_dir = _ensure_milestone_dir(layout, milestone, dry_run=dry_run)
                if milestone_dir and milestone_dir[1]:
                    milestones_created += 1

        if number in existing_issues:
            existing_path = existing_issues[number]
            if _maybe_move_issue(existing_path, milestone_dir, dry_run=dry_run):
                issues_moved += 1
            else:
                issues_skipped += 1
            continue
        if (issue.get("title") or "") and issue.get("body") is not None:
            content_key = _content_key(issue.get("title", ""), issue.get("body"))
            if content_key in existing_by_content:
                existing_path = existing_by_content[content_key]
                if not dry_run:
                    update_front_matter(existing_path, {"number": number})
                if _maybe_move_issue(existing_path, milestone_dir, dry_run=dry_run):
                    issues_moved += 1
                else:
                    issues_skipped += 1
                continue

        target_dir = milestone_dir[0] if milestone_dir else layout.issues_dir
        issue_path = _issue_path_for_import(target_dir, issue)
        if issue_path.exists():
            issues_skipped += 1
            continue

        issue_doc = _issue_document_from_api(issue, issue_path, milestone_title=milestone_title)
        if not dry_run:
            _write_issue(issue_doc)
        issues_created += 1

    return ImportResult(
        issues_created=issues_created,
        issues_moved=issues_moved,
        milestones_created=milestones_created,
        issues_skipped=issues_skipped,
    )


def _ensure_milestone_dir(
    layout: PlanLayout, milestone: Mapping[str, Any], *, dry_run: bool
) -> tuple[Path, bool] | None:
    title = milestone.get("title")
    if not title:
        return None
    slug = _slugify(title)
    milestone_dir = layout.milestones_dir / slug
    milestone_path = milestone_dir / "milestone.md"
    created = False
    if not milestone_dir.exists():
        if not dry_run:
            milestone_dir.mkdir(parents=True, exist_ok=True)
        created = True
    if not milestone_path.exists():
        milestone_doc = _milestone_document_from_api(milestone, milestone_path)
        if not dry_run:
            _write_milestone(milestone_doc)
        created = True
    issues_dir = milestone_dir / "issues"
    if not issues_dir.exists() and not dry_run:
        issues_dir.mkdir(parents=True, exist_ok=True)
    return issues_dir, created


def _maybe_move_issue(
    existing_path: Path,
    milestone_dir: tuple[Path, bool] | None,
    *,
    dry_run: bool,
) -> bool:
    if milestone_dir is None:
        return False
    target_dir = milestone_dir[0]
    target_path = target_dir / existing_path.name
    if existing_path == target_path or target_path.exists():
        return False
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        existing_path.rename(target_path)
    return True


def _collect_existing_issues(layout: PlanLayout) -> dict[int, Path]:
    numbers: dict[int, Path] = {}
    for issue_path in discover_root_issues(layout):
        _try_add_issue_number(issue_path, numbers)
    for entry in discover_milestones(layout):
        for issue_path in entry.issue_files:
            _try_add_issue_number(issue_path, numbers)
    return numbers


def _collect_existing_by_content(layout: PlanLayout) -> dict[tuple[str, str], Path]:
    entries: dict[tuple[str, str], Path] = {}
    for issue_path in discover_root_issues(layout):
        _try_add_issue_content(issue_path, entries)
    for entry in discover_milestones(layout):
        for issue_path in entry.issue_files:
            _try_add_issue_content(issue_path, entries)
    return entries


def _try_add_issue_number(issue_path: Path, numbers: dict[int, Path]) -> None:
    try:
        issue_doc = load_issue_document(issue_path)
    except DocumentError:
        return
    if issue_doc.number is not None:
        numbers.setdefault(issue_doc.number, issue_path)


def _try_add_issue_content(issue_path: Path, entries: dict[tuple[str, str], Path]) -> None:
    try:
        issue_doc = load_issue_document(issue_path)
    except DocumentError:
        return
    if issue_doc.number is not None:
        return
    key = _content_key(issue_doc.title, issue_doc.body)
    entries.setdefault(key, issue_path)


def _content_key(title: str, body: str | None) -> tuple[str, str]:
    return title.strip(), (body or "").strip()


def _issue_document_from_api(
    issue: Mapping[str, Any], path: Path, *, milestone_title: str | None
) -> IssueDocument:
    labels = tuple(label["name"] for label in issue.get("labels", []))
    assignees = tuple(assignee["login"] for assignee in issue.get("assignees", []))
    state = issue.get("state")
    state_reason = issue.get("state_reason")
    return IssueDocument(
        path=path,
        title=str(issue.get("title", "")).strip(),
        body=(issue.get("body") or "").strip(),
        issue_id=None,
        number=issue.get("number"),
        labels=labels,
        labels_set=True,
        milestone=milestone_title,
        milestone_number=None,
        milestone_set=milestone_title is not None,
        assignees=assignees,
        assignees_set=True,
        issue_type=None,
        state=None if not state else _parse_state(state),
        state_reason=None if not state_reason else _parse_state_reason(state_reason),
    )


def _milestone_document_from_api(milestone: Mapping[str, Any], path: Path) -> MilestoneDocument:
    return MilestoneDocument(
        path=path,
        title=str(milestone.get("title", "")).strip(),
        description=milestone.get("description"),
        due_on=milestone.get("due_on"),
        state=None if not milestone.get("state") else _parse_state(milestone["state"]),
        milestone_id=None,
        number=milestone.get("number"),
        body="",
    )


def _write_issue(issue: IssueDocument) -> None:
    front_matter: dict[str, Any] = {"title": issue.title, "number": issue.number}
    if issue.labels:
        front_matter["labels"] = list(issue.labels)
    if issue.assignees:
        front_matter["assignees"] = list(issue.assignees)
    if issue.milestone is not None:
        front_matter["milestone"] = issue.milestone
    if issue.milestone_number is not None:
        front_matter["milestone"] = issue.milestone_number
    if issue.state:
        front_matter["state"] = issue.state.value
    if issue.state_reason:
        front_matter["state_reason"] = issue.state_reason.value
    content = render_markdown(front_matter, issue.body)
    issue.path.parent.mkdir(parents=True, exist_ok=True)
    issue.path.write_text(content, encoding="utf-8")


def _write_milestone(milestone: MilestoneDocument) -> None:
    front_matter: dict[str, Any] = {"title": milestone.title, "number": milestone.number}
    if milestone.description:
        front_matter["description"] = milestone.description
    if milestone.due_on:
        front_matter["due_on"] = milestone.due_on
    if milestone.state:
        front_matter["state"] = milestone.state.value
    content = render_markdown(front_matter, "")
    milestone.path.parent.mkdir(parents=True, exist_ok=True)
    milestone.path.write_text(content, encoding="utf-8")


def _slugify(value: str) -> str:
    slug = []
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
        elif char in {" ", "-", "_"}:
            slug.append("-")
    normalized = "".join(slug).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or "milestone"


def _issue_path_for_import(directory: Path, issue: Mapping[str, Any]) -> Path:
    created_at = issue.get("created_at")
    created_at_str = _format_date(created_at)
    title = _slugify(str(issue.get("title", "")).strip()) or "issue"
    base_name = f"{created_at_str}-{title}"
    path = directory / f"{base_name}.md"
    if not path.exists():
        return path
    number = issue.get("number")
    if number:
        with_number = directory / f"{base_name}-{number}.md"
        if not with_number.exists():
            return with_number
    index = 2
    while True:
        candidate = directory / f"{base_name}-{index}.md"
        if not candidate.exists():
            return candidate
        index += 1


def _format_date(value: str | None) -> str:
    if not value:
        return "00000000"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "00000000"
    return parsed.strftime("%Y%m%d")


def _parse_state(value: str):
    from planhub.github import IssueState

    return IssueState(value)


def _parse_state_reason(value: str):
    from planhub.github import IssueStateReason

    return IssueStateReason(value)
