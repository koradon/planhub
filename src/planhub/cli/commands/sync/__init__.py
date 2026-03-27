from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from planhub.auth import get_auth_token
from planhub.cli.sync_plan import (
    apply_sync_plan,
    archive_closed_issues_in_filesystem,
    build_sync_plan,
    reconcile_milestone_archive_locations,
)
from planhub.config import load_config
from planhub.documents import DocumentError  # noqa: F401
from planhub.github import GitHubClient
from planhub.importer import ImportResult, import_existing_issues
from planhub.layout import PlanLayout, load_layout
from planhub.repository import get_github_repo_from_git


@dataclass(frozen=True)
class SyncOutputStats:
    imported_created: int = 0
    imported_moved: int = 0
    imported_skipped: int = 0
    imported_milestones_created: int = 0
    plan_milestones_create: int = 0
    plan_milestones_update: int = 0
    plan_issues_create: int = 0
    plan_issues_update: int = 0
    archived_issues: int = 0
    deleted_issues: int = 0


def sync_command(*, dry_run: bool, verbosity_override: str | None = None) -> None:
    repo_root = Path.cwd()
    try:
        layout = load_layout(repo_root)
    except FileNotFoundError as exc:
        typer.echo(f"{exc}. Run 'planhub init' first.")
        raise typer.Exit(code=1) from exc

    # Load layered config once per command invocation.
    config = load_config(repo_root)
    verbosity = verbosity_override or config.sync.behavior.verbosity
    verbose_output = verbosity == "verbose"
    errors: list[str] = []
    stats = SyncOutputStats()

    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=dry_run,
        move_open_to_active=True,
        move_closed_to_archive=False,
    )
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)

    client: GitHubClient | None = None
    owner_repo, import_stats = _import_existing_issues_if_possible(
        layout,
        repo_root,
        dry_run=dry_run,
    )
    stats = SyncOutputStats(
        imported_created=import_stats.issues_created,
        imported_moved=import_stats.issues_moved,
        imported_skipped=import_stats.issues_skipped,
        imported_milestones_created=import_stats.milestones_created,
    )
    if owner_repo is not None:
        client, owner_repo = owner_repo

    plan, parsed_milestones, parsed_issues, errors = build_sync_plan(layout)
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)
    stats = SyncOutputStats(
        imported_created=stats.imported_created,
        imported_moved=stats.imported_moved,
        imported_skipped=stats.imported_skipped,
        imported_milestones_created=stats.imported_milestones_created,
        plan_milestones_create=len(plan.milestones_to_create),
        plan_milestones_update=len(plan.milestones_to_update),
        plan_issues_create=len(plan.issues_to_create),
        plan_issues_update=len(plan.issues_to_update),
    )

    if dry_run:
        typer.echo("🧪 [dry-run] No changes written.")
        _echo_sync_summary(stats, parsed_milestones, parsed_issues, dry_run=True)
        if verbose_output:
            _echo_verbose_plan(plan)
        return

    if (
        plan.milestones_to_create
        or plan.issues_to_create
        or plan.milestones_to_update
        or plan.issues_to_update
    ):
        if client is None:
            auth = _get_github_client(repo_root)
            if auth is None:
                raise typer.Exit(code=1)
            client, owner, repo = auth
            owner_repo = (owner, repo)
        apply_stats = apply_sync_plan(client, owner_repo, plan, errors, config, layout)
        stats = SyncOutputStats(
            imported_created=stats.imported_created,
            imported_moved=stats.imported_moved,
            imported_skipped=stats.imported_skipped,
            imported_milestones_created=stats.imported_milestones_created,
            plan_milestones_create=apply_stats.milestones_created,
            plan_milestones_update=apply_stats.milestones_updated,
            plan_issues_create=apply_stats.issues_created,
            plan_issues_update=apply_stats.issues_updated,
            archived_issues=stats.archived_issues,
            deleted_issues=stats.deleted_issues,
        )
    else:
        stats = SyncOutputStats(
            imported_created=stats.imported_created,
            imported_moved=stats.imported_moved,
            imported_skipped=stats.imported_skipped,
            imported_milestones_created=stats.imported_milestones_created,
            plan_milestones_create=0,
            plan_milestones_update=0,
            plan_issues_create=0,
            plan_issues_update=0,
            archived_issues=stats.archived_issues,
            deleted_issues=stats.deleted_issues,
        )

    if not errors:
        archive_stats = archive_closed_issues_in_filesystem(
            layout, config, errors=errors, dry_run=dry_run
        )
        stats = SyncOutputStats(
            imported_created=stats.imported_created,
            imported_moved=stats.imported_moved,
            imported_skipped=stats.imported_skipped,
            imported_milestones_created=stats.imported_milestones_created,
            plan_milestones_create=stats.plan_milestones_create,
            plan_milestones_update=stats.plan_milestones_update,
            plan_issues_create=stats.plan_issues_create,
            plan_issues_update=stats.plan_issues_update,
            archived_issues=archive_stats.archived_count,
            deleted_issues=archive_stats.deleted_count,
        )
        reconcile_milestone_archive_locations(
            layout,
            errors=errors,
            dry_run=dry_run,
            move_open_to_active=False,
            move_closed_to_archive=True,
        )

    if errors:
        for error in errors:
            typer.echo(f"❌ {error}")
        raise typer.Exit(code=1)
    typer.echo("✅ Sync completed.")
    _echo_sync_summary(stats, parsed_milestones, parsed_issues, dry_run=False)
    if verbose_output:
        _echo_verbose_plan(plan)


def _import_existing_issues_if_possible(
    layout: PlanLayout,
    repo_root: Path,
    *,
    dry_run: bool,
) -> tuple[tuple[GitHubClient, tuple[str, str]] | None, ImportResult]:
    empty_result = ImportResult(
        issues_created=0,
        issues_moved=0,
        milestones_created=0,
        issues_skipped=0,
    )
    auth = _get_github_client(repo_root)
    if auth is None:
        return None, empty_result
    client, owner, repo = auth
    result = import_existing_issues(
        layout,
        owner,
        repo,
        client=client,
        dry_run=dry_run,
    )
    return (client, (owner, repo)), result


def _report_parse_errors(errors: list[str]) -> bool:
    if not errors:
        return False
    for error in errors:
        typer.echo(f"Error: {error}")
    return True


def _get_github_client(
    repo_root: Path,
) -> tuple[GitHubClient, str, str] | None:
    token = get_auth_token()
    if not token:
        typer.echo(
            "⚠️ Missing GitHub credentials. Set GITHUB_TOKEN/GH_TOKEN or run 'gh auth login'."
        )
        return None
    try:
        owner, repo = get_github_repo_from_git(repo_root)
    except ValueError as exc:
        typer.echo(f"⚠️ {exc} Cannot sync issues.")
        return None
    return GitHubClient(token), owner, repo


def _echo_sync_summary(
    stats: SyncOutputStats, parsed_milestones: int, parsed_issues: int, *, dry_run: bool
) -> None:
    mode = "would " if dry_run else ""
    typer.echo(
        "📥 Import:"
        f" {mode}create {stats.imported_created} issues,"
        f" {mode}move {stats.imported_moved} issues,"
        f" skip {stats.imported_skipped},"
        f" {mode}create {stats.imported_milestones_created} milestones."
    )
    typer.echo(
        "📝 Issues:"
        f" {mode}create {stats.plan_issues_create},"
        f" {mode}update {stats.plan_issues_update},"
        f" {mode}delete {stats.deleted_issues},"
        f" {mode}archive {stats.archived_issues}."
    )
    typer.echo(
        "🏁 Milestones:"
        f" {mode}create {stats.plan_milestones_create},"
        f" {mode}update {stats.plan_milestones_update}."
    )
    typer.echo(f"📂 Parsed: {parsed_milestones} milestones, {parsed_issues} issues.")


def _echo_verbose_plan(plan) -> None:
    typer.echo("🔎 [verbose] Planned changes:")
    for milestone_path, _ in plan.milestones_to_create:
        typer.echo(f"  + milestone create: {milestone_path}")
    for milestone_path, _ in plan.milestones_to_update:
        typer.echo(f"  ~ milestone update: {milestone_path}")
    for issue_path, _, _ in plan.issues_to_create:
        typer.echo(f"  + issue create: {issue_path}")
    for issue_path, _, _ in plan.issues_to_update:
        typer.echo(f"  ~ issue update: {issue_path}")
