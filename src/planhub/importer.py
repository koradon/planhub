from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Any, Mapping, Optional

from planhub.documents import IssueDocument, MilestoneDocument, render_markdown
from planhub.layout import PlanLayout


@dataclass(frozen=True)
class ImportResult:
    issues_created: int
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
    milestones_created = 0
    issues_skipped = 0

    for issue in issues:
        if issue.get("pull_request"):
            continue

        milestone = issue.get("milestone")
        milestone_title = None
        milestone_dir = None
        if milestone:
            milestone_title = milestone.get("title")
            if milestone_title:
                milestone_dir = _ensure_milestone_dir(
                    layout, milestone, dry_run=dry_run
                )
                if milestone_dir and milestone_dir[1]:
                    milestones_created += 1

        number = issue.get("number")
        if not number:
            issues_skipped += 1
            continue
        target_dir = milestone_dir[0] if milestone_dir else layout.issues_dir
        issue_path = _issue_path_for_import(target_dir, issue)
        if issue_path.exists():
            issues_skipped += 1
            continue

        issue_doc = _issue_document_from_api(
            issue, issue_path, milestone_title=milestone_title
        )
        if not dry_run:
            _write_issue(issue_doc)
        issues_created += 1

    return ImportResult(
        issues_created=issues_created,
        milestones_created=milestones_created,
        issues_skipped=issues_skipped,
    )


def _ensure_milestone_dir(
    layout: PlanLayout, milestone: Mapping[str, Any], *, dry_run: bool
) -> Optional[tuple[Path, bool]]:
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


def _issue_document_from_api(
    issue: Mapping[str, Any], path: Path, *, milestone_title: Optional[str]
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


def _milestone_document_from_api(
    milestone: Mapping[str, Any], path: Path
) -> MilestoneDocument:
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
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
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


def _format_date(value: Optional[str]) -> str:
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
