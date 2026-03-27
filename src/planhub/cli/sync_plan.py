from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from planhub.config import PlanHubConfig
from planhub.documents import (
    DocumentError,
    IssueDocument,
    MilestoneDocument,
    issue_document_to_metadata,
    load_issue_document,
    load_milestone_document,
    milestone_document_to_metadata,
    render_markdown,
    update_front_matter,
)
from planhub.github import GitHubClient, IssueState, IssueStateReason
from planhub.layout import PlanLayout, discover_milestones, discover_root_issues
from planhub.slug import slugify

MAX_WORKERS = 5  # Conservative limit to avoid GitHub rate limits


class SyncPlan:
    def __init__(self) -> None:
        self.milestones_to_create: list[tuple[Path, MilestoneDocument]] = []
        self.milestones_to_update: list[tuple[Path, MilestoneDocument]] = []
        self.issues_to_create: list[tuple[Path, IssueDocument, str | None]] = []
        self.issues_to_update: list[tuple[Path, IssueDocument, str | None]] = []
        self.milestone_numbers: dict[str, int] = {}
        self.milestone_titles_by_dir: dict[Path, str] = {}


def _github_milestone_info_from_issue_payload(
    issue_payload: Mapping[str, object] | object,
) -> tuple[bool, Mapping[str, object] | None, str | None, int | None]:
    if not isinstance(issue_payload, Mapping):
        return False, None, None, None
    sentinel_missing = object()
    milestone_payload = issue_payload.get("milestone", sentinel_missing)
    if milestone_payload is sentinel_missing:
        # Treat missing `milestone` as "unknown" instead of "milestone cleared".
        return False, None, None, None
    if milestone_payload is None:
        return True, None, None, None
    if not isinstance(milestone_payload, Mapping):
        return True, None, None, None
    raw_title = milestone_payload.get("title")
    milestone_title = raw_title if isinstance(raw_title, str) and raw_title.strip() else None
    raw_number = milestone_payload.get("number")
    milestone_number = raw_number if isinstance(raw_number, int) else None
    return True, milestone_payload, milestone_title, milestone_number


def _ensure_milestone_dir_and_doc(
    layout: PlanLayout,
    *,
    milestone_slug: str,
    milestone_payload: Mapping[str, object],
) -> Path:
    """Ensure milestone directory structure exists and milestone.md is present."""
    milestone_dir = layout.milestones_dir / milestone_slug
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    milestone_path = milestone_dir / "milestone.md"
    if milestone_path.exists():
        return issues_dir

    title_raw = milestone_payload.get("title")
    title = title_raw if isinstance(title_raw, str) and title_raw.strip() else milestone_slug
    number_raw = milestone_payload.get("number")
    number = number_raw if isinstance(number_raw, int) else None
    description = milestone_payload.get("description")
    description_str = description if isinstance(description, str) else None
    due_on = milestone_payload.get("due_on")
    due_on_str = due_on if isinstance(due_on, str) else None
    state_raw = milestone_payload.get("state")
    state = None
    if isinstance(state_raw, str):
        try:
            state = IssueState(state_raw)
        except ValueError:
            state = None

    milestone_doc = MilestoneDocument(
        path=milestone_path,
        title=title,
        description=description_str,
        due_on=due_on_str,
        state=state,
        milestone_id=None,
        number=number,
        body="",
    )
    content = render_markdown(milestone_document_to_metadata(milestone_doc), "")
    milestone_path.write_text(content, encoding="utf-8")
    return issues_dir


def _move_issue_to_dir(issue_path: Path, *, target_dir: Path) -> Path:
    """Move an issue markdown file to a new directory without overwriting."""
    if issue_path.parent == target_dir:
        return issue_path

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / issue_path.name
    if not target_path.exists():
        issue_path.rename(target_path)
        return target_path

    for index in range(1, 1000):
        candidate = target_path.with_name(f"{target_path.stem}-{index}{target_path.suffix}")
        if not candidate.exists():
            issue_path.rename(candidate)
            return candidate

    # If all candidates are taken, fall back to raising; collision is unexpected.
    raise FileExistsError(f"Unable to move {issue_path} into {target_dir} due to collisions.")


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
    config: PlanHubConfig,
    layout: PlanLayout,
) -> None:
    if owner_repo is None:
        errors.append("Missing repository information for sync.")
        return
    owner, repo = owner_repo
    _create_missing_milestones(client, owner, repo, plan, errors)
    _update_existing_milestones(client, owner, repo, plan, errors)
    _create_missing_issues(client, owner, repo, plan, errors, config)
    _update_existing_issues(client, layout, owner, repo, plan, errors, config)


def _collect_issues_for_entry(entry, plan: SyncPlan, errors: list[str]) -> int:
    parsed = 0
    for issue_file in entry.issue_files:
        try:
            issue_doc = load_issue_document(issue_file)
        except DocumentError as exc:
            errors.append(str(exc))
            continue
        if _validate_issue_state(issue_doc, issue_file, errors):
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
        if _validate_issue_state(issue_doc, issue_file, errors):
            continue
        if issue_doc.number is None:
            plan.issues_to_create.append((issue_file, issue_doc, None))
        else:
            plan.issues_to_update.append((issue_file, issue_doc, None))
        parsed += 1
    return parsed


def _validate_issue_state(issue_doc: IssueDocument, issue_path: Path, errors: list[str]) -> bool:
    if issue_doc.state_reason and issue_doc.state != IssueState.CLOSED:
        errors.append(f"{issue_path}: state_reason requires state='closed'.")
        return True
    return False


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
            cached_metadata = milestone_document_to_metadata(milestone_doc)
            update_front_matter(
                milestone_path,
                {"number": number},
                cached_metadata=cached_metadata,
                cached_body=milestone_doc.body,
            )
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
    errors_lock = Lock()

    def update_single_milestone(milestone_path: Path, milestone_doc: MilestoneDocument) -> None:
        if milestone_doc.number is None:
            with errors_lock:
                errors.append(f"{milestone_path}: missing milestone number.")
            return
        client.update_milestone(
            owner,
            repo,
            milestone_doc.number,
            title=milestone_doc.title,
            description=milestone_doc.description,
            due_on=milestone_doc.due_on,
            state=milestone_doc.state.value if milestone_doc.state else None,
        )

    _run_parallel(
        plan.milestones_to_update,
        lambda item: update_single_milestone(item[0], item[1]),
        errors,
        errors_lock,
    )


def _resolve_milestone_number(
    plan: SyncPlan,
    issue_path: Path,
    issue_doc: IssueDocument,
    milestone_title: str | None,
    errors: list[str],
) -> tuple[int | None, bool]:
    if issue_doc.milestone_number is not None:
        return issue_doc.milestone_number, False
    if issue_doc.milestone_set and issue_doc.milestone is None:
        return None, True
    milestone_number = None
    effective_title = issue_doc.milestone or milestone_title
    if effective_title:
        milestone_number = plan.milestone_numbers.get(effective_title)
        if milestone_number is None:
            errors.append(f"{issue_path}: milestone '{effective_title}' has no number.")
    return milestone_number, False


def _create_missing_issues(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: SyncPlan,
    errors: list[str],
    config: PlanHubConfig,
) -> None:
    errors_lock = Lock()

    def create_single_issue(
        issue_path: Path, issue_doc: IssueDocument, milestone_title: str | None
    ) -> None:
        local_errors: list[str] = []
        milestone_number, clear_milestone = _resolve_milestone_number(
            plan, issue_path, issue_doc, milestone_title, local_errors
        )
        if local_errors:
            with errors_lock:
                errors.extend(local_errors)
            return
        if clear_milestone:
            milestone_number = None
        if (issue_doc.milestone or milestone_title) and milestone_number is None:
            return
        labels = (
            list(issue_doc.labels)
            if issue_doc.labels_set
            else list(config.sync.github.default_labels)
        )
        assignees = (
            list(issue_doc.assignees)
            if issue_doc.assignees_set
            else list(config.sync.github.default_assignees)
        )
        created = client.create_issue(
            owner,
            repo,
            issue_doc.title,
            body=issue_doc.body or None,
            labels=labels,
            assignees=assignees,
            milestone=milestone_number,
            issue_type=issue_doc.issue_type,
        )
        issue_number = created.get("number")
        if isinstance(issue_number, int):
            cached_metadata = issue_document_to_metadata(issue_doc)
            state_updates = _state_updates_from_github_issue(created)
            update_front_matter(
                issue_path,
                {"number": issue_number, **state_updates},
                cached_metadata=cached_metadata,
                cached_body=issue_doc.body,
            )
        else:
            with errors_lock:
                errors.append(f"{issue_path}: GitHub did not return a number.")
            return

    _run_parallel(
        plan.issues_to_create,
        lambda item: create_single_issue(item[0], item[1], item[2]),
        errors,
        errors_lock,
    )


def _update_existing_issues(
    client: GitHubClient,
    layout: PlanLayout,
    owner: str,
    repo: str,
    plan: SyncPlan,
    errors: list[str],
    config: PlanHubConfig,
) -> None:
    errors_lock = Lock()
    milestone_creation_lock = Lock()
    move_locks_by_dir: dict[Path, Lock] = {}
    move_locks_registry_lock = Lock()

    def _move_lock_for_dir(target_dir: Path) -> Lock:
        with move_locks_registry_lock:
            lock = move_locks_by_dir.get(target_dir)
            if lock is None:
                lock = Lock()
                move_locks_by_dir[target_dir] = lock
            return lock

    def update_single_issue(
        issue_path: Path, issue_doc: IssueDocument, milestone_title: str | None
    ) -> None:
        del milestone_title  # Milestone placement is reconciled from GitHub.
        if issue_doc.number is None:
            with errors_lock:
                errors.append(f"{issue_path}: missing issue number.")
            return
        labels = (
            list(issue_doc.labels)
            if issue_doc.labels_set
            else list(config.sync.github.default_labels)
        )
        assignees = (
            list(issue_doc.assignees)
            if issue_doc.assignees_set
            else list(config.sync.github.default_assignees)
        )
        updated_issue = client.update_issue(
            owner,
            repo,
            issue_doc.number,
            title=issue_doc.title,
            body=issue_doc.body or None,
            labels=labels,
            assignees=assignees,
            issue_type=issue_doc.issue_type,
            # Keep issue state authoritative on GitHub during sync.
            state=None,
            state_reason=None,
        )
        state_updates = _state_updates_from_github_issue(updated_issue)

        (
            milestone_field_present,
            milestone_payload,
            milestone_title_github,
            milestone_number_github,
        ) = _github_milestone_info_from_issue_payload(updated_issue)

        milestone_updates: dict[str, object] = {}
        if milestone_field_present:
            if milestone_title_github is None and milestone_number_github is None:
                # GitHub indicates no milestone.
                target_parent_dir = layout.issues_dir
            else:
                milestone_slug = slugify(
                    milestone_title_github or str(milestone_number_github),
                    fallback="milestone",
                )
                # Ensure local milestone structure exists so the rename/move succeeds.
                if milestone_payload is not None:
                    with milestone_creation_lock:
                        target_parent_dir = _ensure_milestone_dir_and_doc(
                            layout,
                            milestone_slug=milestone_slug,
                            milestone_payload=milestone_payload,
                        )
                else:
                    # Fallback: ensure directory even if milestone payload is incomplete.
                    target_parent_dir = layout.milestones_dir / milestone_slug / "issues"
                    target_parent_dir.mkdir(parents=True, exist_ok=True)

            if issue_path.parent != target_parent_dir:
                # Serialize moves per target directory to avoid rename races.
                with _move_lock_for_dir(target_parent_dir):
                    issue_path = _move_issue_to_dir(issue_path, target_dir=target_parent_dir)

            if milestone_title_github is not None or milestone_number_github is not None:
                if milestone_number_github is not None:
                    milestone_updates["milestone"] = milestone_number_github
                else:
                    milestone_updates["milestone"] = milestone_title_github
            elif issue_doc.milestone_set:
                milestone_updates["milestone"] = None

        updates: dict[str, object] = {}
        updates.update(state_updates)
        updates.update(milestone_updates)
        if updates:
            cached_metadata = issue_document_to_metadata(issue_doc)
            update_front_matter(
                issue_path,
                updates,
                cached_metadata=cached_metadata,
                cached_body=issue_doc.body,
            )

    _run_parallel(
        plan.issues_to_update,
        lambda item: update_single_issue(item[0], item[1], item[2]),
        errors,
        errors_lock,
    )


def _run_parallel(
    items: list,
    func: Callable,
    errors: list[str],
    errors_lock: Lock,
) -> None:
    """Run a function in parallel over a list of items."""
    if not items:
        return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(func, item): item for item in items}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                with errors_lock:
                    errors.append(f"Parallel execution error: {exc}")


def _state_updates_from_github_issue(
    issue_payload: Mapping[str, object] | object,
) -> dict[str, str | None]:
    if not isinstance(issue_payload, Mapping):
        return {}
    raw_state = issue_payload.get("state")
    if raw_state not in (IssueState.OPEN.value, IssueState.CLOSED.value):
        return {}
    updates: dict[str, str | None] = {"state": raw_state}
    raw_reason = issue_payload.get("state_reason")
    if raw_state == IssueState.CLOSED.value and isinstance(raw_reason, str):
        valid_reasons = {reason.value for reason in IssueStateReason}
        updates["state_reason"] = raw_reason if raw_reason in valid_reasons else None
        return updates
    updates["state_reason"] = None
    return updates


def archive_closed_issues_in_filesystem(
    layout: PlanLayout,
    config: PlanHubConfig,
    *,
    errors: list[str],
    dry_run: bool,
) -> None:
    """Archive or delete locally-synced GitHub-closed issues.

    We scan the active plan layout (`.plan/issues` and `.plan/milestones/*/issues`)
    and move/delete issue documents whose `state` is `closed` and which have
    a known GitHub `number` (i.e., they are already synced).
    """

    policy = config.sync.closed_issues.policy
    archive_dir = config.sync.closed_issues.archive_dir

    def iter_issue_files() -> list[Path]:
        issue_files: list[Path] = []
        issue_files.extend(discover_root_issues(layout))
        for milestone_entry in discover_milestones(layout):
            issue_files.extend(milestone_entry.issue_files)
        return issue_files

    issue_files = iter_issue_files()
    for issue_path in issue_files:
        try:
            issue_doc = load_issue_document(issue_path)
        except DocumentError as exc:
            errors.append(str(exc))
            continue

        if issue_doc.number is None:
            continue
        if issue_doc.state != IssueState.CLOSED:
            continue

        if policy == "delete":
            if not dry_run:
                try:
                    issue_path.unlink()
                except FileNotFoundError:
                    # Best-effort cleanup.
                    pass
            continue

        if policy != "archive":
            errors.append(f"{issue_path}: Unsupported closed issue policy: {policy}.")
            continue

        milestone_slug: str | None = None
        try:
            rel = issue_path.relative_to(layout.milestones_dir)
            # Expected: <milestone-slug>/issues/<filename>.md
            if len(rel.parts) >= 3 and rel.parts[1] == "issues":
                milestone_slug = rel.parts[0]
        except ValueError:
            milestone_slug = None

        target_dir = archive_dir
        if milestone_slug:
            target_dir = archive_dir / milestone_slug
        target_path = target_dir / issue_path.name

        if target_path == issue_path:
            continue

        if target_path.exists():
            # Avoid overwriting; add numeric suffix.
            for index in range(1, 1000):
                candidate = target_path.with_name(f"{target_path.stem}-{index}{target_path.suffix}")
                if not candidate.exists():
                    target_path = candidate
                    break
            else:
                errors.append(
                    f"{issue_path}: archive target collision; all suffixes 1..999 are taken for "
                    f"{target_path}."
                )
                continue

        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            issue_path.rename(target_path)
