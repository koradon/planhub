from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from planhub.auth import get_auth_token
from planhub.github import GitHubClient
from planhub.importer import import_existing_issues
from planhub.documents import (
    DocumentError,
    IssueDocument,
    MilestoneDocument,
    load_issue_document,
    load_milestone_document,
    update_front_matter,
)
from planhub.layout import (
    PlanLayout,
    discover_milestones,
    discover_root_issues,
    ensure_layout,
    load_layout,
)
from planhub.repository import get_github_repo_from_git


class _SyncPlan:
    def __init__(self) -> None:
        self.milestones_to_create: list[tuple[Path, MilestoneDocument]] = []
        self.milestones_to_update: list[tuple[Path, MilestoneDocument]] = []
        self.issues_to_create: list[tuple[Path, IssueDocument, str | None]] = []
        self.issues_to_update: list[tuple[Path, IssueDocument, str | None]] = []
        self.milestone_numbers: dict[str, int] = {}
        self.milestone_titles_by_dir: dict[Path, str] = {}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planhub")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init", help="Initialize the .plan layout in a repo."
    )
    init_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing."
    )

    sync_parser = subparsers.add_parser("sync", help="Sync .plan files with GitHub.")
    sync_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing."
    )
    sync_parser.add_argument(
        "--import-existing",
        action="store_true",
        help="Import existing GitHub issues into .plan files.",
    )

    args = parser.parse_args(argv)
    if args.command == "init":
        return _run_init(Path.cwd(), dry_run=args.dry_run)
    if args.command == "sync":
        return _run_sync(
            Path.cwd(),
            dry_run=args.dry_run,
            import_existing=args.import_existing,
        )

    parser.print_help()
    return 1


def _run_init(repo_root: Path, dry_run: bool) -> int:
    if dry_run:
        plan_root = repo_root / ".plan"
        milestones_dir = plan_root / "milestones"
        issues_dir = plan_root / "issues"
        print("Dry run: would create plan layout:")
        print(f"- {plan_root}")
        print(f"- {milestones_dir}")
        print(f"- {issues_dir}")
        return 0

    layout = ensure_layout(repo_root)
    print(f"Initialized plan layout at {layout.root}")
    return 0


def _run_sync(repo_root: Path, dry_run: bool, import_existing: bool) -> int:
    try:
        layout = load_layout(repo_root)
    except FileNotFoundError as exc:
        print(f"{exc}. Run 'planhub init' first.")
        return 1

    client: GitHubClient | None = None
    owner_repo = _import_existing_issues_if_requested(
        layout,
        repo_root,
        dry_run=dry_run,
        import_existing=import_existing,
    )
    if import_existing and owner_repo is None:
        return 1
    if owner_repo is not None:
        client, owner_repo = owner_repo

    plan, parsed_milestones, parsed_issues, errors = _build_sync_plan(layout)
    if _report_parse_errors(errors):
        return 1

    if dry_run:
        print("Dry run: no changes will be written.")
        print(
            "Dry run: would create"
            f" {len(plan.milestones_to_create)} milestones and"
            f" {len(plan.issues_to_create)} issues."
        )
        print(
            "Dry run: would update"
            f" {len(plan.milestones_to_update)} milestones and"
            f" {len(plan.issues_to_update)} issues."
        )
        print(f"Found {parsed_milestones} milestones and {parsed_issues} issues.")
        return 0

    if (
        plan.milestones_to_create
        or plan.issues_to_create
        or plan.milestones_to_update
        or plan.issues_to_update
    ):
        if client is None:
            auth = _get_github_client(repo_root)
            if auth is None:
                return 1
            client, owner, repo = auth
            owner_repo = (owner, repo)
        _apply_sync_plan(client, owner_repo, plan, errors)

    if errors:
        for error in errors:
            print(f"Error: {error}")
        return 1
    print(f"Found {parsed_milestones} milestones and {parsed_issues} issues.")
    return 0


def _import_existing_issues_if_requested(
    layout: PlanLayout,
    repo_root: Path,
    *,
    dry_run: bool,
    import_existing: bool,
) -> tuple[GitHubClient, tuple[str, str]] | None:
    if not import_existing:
        return None
    auth = _get_github_client(repo_root)
    if auth is None:
        return None
    client, owner, repo = auth
    result = import_existing_issues(
        layout,
        owner,
        repo,
        client=client,
        dry_run=dry_run,
    )
    print(
        "Imported issues:"
        f" {result.issues_created} created,"
        f" {result.issues_skipped} skipped,"
        f" {result.milestones_created} milestones created."
    )
    return client, (owner, repo)


def _build_sync_plan(
    layout: PlanLayout,
) -> tuple[_SyncPlan, int, int, list[str]]:
    plan = _SyncPlan()
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


def _collect_issues_for_entry(entry, plan: _SyncPlan, errors: list[str]) -> int:
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


def _collect_root_issues(
    layout: PlanLayout, plan: _SyncPlan, errors: list[str]
) -> int:
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


def _report_parse_errors(errors: list[str]) -> bool:
    if not errors:
        return False
    for error in errors:
        print(f"Error: {error}")
    return True


def _apply_sync_plan(
    client: GitHubClient,
    owner_repo: tuple[str, str] | None,
    plan: _SyncPlan,
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


def _create_missing_milestones(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: _SyncPlan,
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
    plan: _SyncPlan,
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
    plan: _SyncPlan,
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
    plan: _SyncPlan,
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
    plan: _SyncPlan,
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


def _get_github_client(
    repo_root: Path,
) -> tuple[GitHubClient, str, str] | None:
    token = get_auth_token()
    if not token:
        print(
            "Missing GitHub credentials. "
            "Set GITHUB_TOKEN/GH_TOKEN or run 'gh auth login'."
        )
        return None
    try:
        owner, repo = get_github_repo_from_git(repo_root)
    except ValueError as exc:
        print(f"{exc} Cannot sync issues.")
        return None
    return GitHubClient(token), owner, repo


if __name__ == "__main__":
    raise SystemExit(main())
