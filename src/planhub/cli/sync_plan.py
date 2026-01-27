from __future__ import annotations

from pathlib import Path

from planhub.documents import (
    DocumentError,
    IssueDocument,
    MilestoneDocument,
    load_issue_document,
    load_milestone_document,
    update_front_matter,
)
from planhub.github import GitHubClient
from planhub.layout import PlanLayout, discover_milestones, discover_root_issues


class SyncPlan:
    def __init__(self) -> None:
        self.milestones_to_create: list[tuple[Path, MilestoneDocument]] = []
        self.milestones_to_update: list[tuple[Path, MilestoneDocument]] = []
        self.issues_to_create: list[tuple[Path, IssueDocument, str | None]] = []
        self.issues_to_update: list[tuple[Path, IssueDocument, str | None]] = []
        self.milestone_numbers: dict[str, int] = {}
        self.milestone_titles_by_dir: dict[Path, str] = {}


def build_sync_plan(
    layout: PlanLayout,
) -> tuple[SyncPlan, int, int, list[str]]:
    plan = SyncPlan()
    errors: list[str] = []
    parsed_milestones = 0
    parsed_issues = 0
    for entry in discover_milestones(layout):
        if not entry.milestone_file.exists():
            errors.append(f"{entry.milestone_file}: missing milestone.md")
            continue
        try:
            milestone_doc = load_milestone_document(entry.milestone_file)
        except DocumentError as exc:
            errors.append(str(exc))
            continue
        plan.milestone_titles_by_dir[entry.directory] = milestone_doc.title
        if milestone_doc.number is not None:
            plan.milestone_numbers[milestone_doc.title] = milestone_doc.number
            plan.milestones_to_update.append((entry.milestone_file, milestone_doc))
        else:
            plan.milestones_to_create.append((entry.milestone_file, milestone_doc))
        parsed_milestones += 1
        parsed_issues += _collect_issues_for_entry(entry, plan, errors)

    parsed_issues += _collect_root_issues(layout, plan, errors)
    return plan, parsed_milestones, parsed_issues, errors


def apply_sync_plan(
    client: GitHubClient,
    owner_repo: tuple[str, str] | None,
    plan: SyncPlan,
    errors: list[str],
) -> None:
    if owner_repo is None:
        errors.append("Missing repository information for sync.")
        return
    owner, repo = owner_repo
    _create_missing_milestones(client, owner, repo, plan, errors)
    _update_existing_milestones(client, owner, repo, plan, errors)
    _create_missing_issues(client, owner, repo, plan, errors)
    _update_existing_issues(client, owner, repo, plan, errors)


def _collect_issues_for_entry(entry, plan: SyncPlan, errors: list[str]) -> int:
    parsed = 0
    for issue_file in entry.issue_files:
        try:
            issue_doc = load_issue_document(issue_file)
        except DocumentError as exc:
            errors.append(str(exc))
            continue
        if issue_doc.number is None:
            plan.issues_to_create.append(
                (
                    issue_file,
                    issue_doc,
                    plan.milestone_titles_by_dir.get(entry.directory),
                )
            )
        else:
            plan.issues_to_update.append(
                (
                    issue_file,
                    issue_doc,
                    plan.milestone_titles_by_dir.get(entry.directory),
                )
            )
        parsed += 1
    return parsed


def _collect_root_issues(layout: PlanLayout, plan: SyncPlan, errors: list[str]) -> int:
    parsed = 0
    for issue_file in discover_root_issues(layout):
        try:
            issue_doc = load_issue_document(issue_file)
        except DocumentError as exc:
            errors.append(str(exc))
            continue
        if issue_doc.number is None:
            plan.issues_to_create.append((issue_file, issue_doc, None))
        else:
            plan.issues_to_update.append((issue_file, issue_doc, None))
        parsed += 1
    return parsed


def _create_missing_milestones(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: SyncPlan,
    errors: list[str],
) -> None:
    for milestone_path, milestone_doc in plan.milestones_to_create:
        created = client.create_milestone(
            owner,
            repo,
            milestone_doc.title,
            description=milestone_doc.description,
            due_on=milestone_doc.due_on,
            state=milestone_doc.state.value if milestone_doc.state else None,
        )
        number = created.get("number")
        if isinstance(number, int):
            update_front_matter(milestone_path, {"number": number})
            plan.milestone_numbers[milestone_doc.title] = number
        else:
            errors.append(f"{milestone_path}: GitHub did not return a number.")


def _update_existing_milestones(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: SyncPlan,
    errors: list[str],
) -> None:
    for milestone_path, milestone_doc in plan.milestones_to_update:
        if milestone_doc.number is None:
            errors.append(f"{milestone_path}: missing milestone number.")
            continue
        client.update_milestone(
            owner,
            repo,
            milestone_doc.number,
            title=milestone_doc.title,
            description=milestone_doc.description,
            due_on=milestone_doc.due_on,
            state=milestone_doc.state.value if milestone_doc.state else None,
        )


def _resolve_milestone_number(
    plan: SyncPlan,
    issue_path: Path,
    issue_doc: IssueDocument,
    milestone_title: str | None,
    errors: list[str],
) -> int | None:
    milestone_number = None
    effective_title = issue_doc.milestone or milestone_title
    if effective_title:
        milestone_number = plan.milestone_numbers.get(effective_title)
        if milestone_number is None:
            errors.append(f"{issue_path}: milestone '{effective_title}' has no number.")
    return milestone_number


def _create_missing_issues(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: SyncPlan,
    errors: list[str],
) -> None:
    for issue_path, issue_doc, milestone_title in plan.issues_to_create:
        milestone_number = _resolve_milestone_number(
            plan, issue_path, issue_doc, milestone_title, errors
        )
        if (issue_doc.milestone or milestone_title) and milestone_number is None:
            continue
        created = client.create_issue(
            owner,
            repo,
            issue_doc.title,
            body=issue_doc.body or None,
            labels=list(issue_doc.labels) if issue_doc.labels else None,
            assignees=list(issue_doc.assignees) if issue_doc.assignees else None,
            milestone=milestone_number,
            issue_type=issue_doc.issue_type,
        )
        issue_number = created.get("number")
        if isinstance(issue_number, int):
            update_front_matter(issue_path, {"number": issue_number})
        else:
            errors.append(f"{issue_path}: GitHub did not return a number.")
            continue
        if issue_doc.state and issue_doc.state.value == "closed":
            client.update_issue_state(
                owner,
                repo,
                issue_number,
                issue_doc.state,
                state_reason=issue_doc.state_reason,
            )


def _update_existing_issues(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: SyncPlan,
    errors: list[str],
) -> None:
    for issue_path, issue_doc, milestone_title in plan.issues_to_update:
        if issue_doc.number is None:
            errors.append(f"{issue_path}: missing issue number.")
            continue
        milestone_number = _resolve_milestone_number(
            plan, issue_path, issue_doc, milestone_title, errors
        )
        if (issue_doc.milestone or milestone_title) and milestone_number is None:
            continue
        client.update_issue(
            owner,
            repo,
            issue_doc.number,
            title=issue_doc.title,
            body=issue_doc.body or None,
            labels=list(issue_doc.labels) if issue_doc.labels else None,
            assignees=list(issue_doc.assignees) if issue_doc.assignees else None,
            milestone=milestone_number,
            issue_type=issue_doc.issue_type,
            state=issue_doc.state,
            state_reason=issue_doc.state_reason,
        )
