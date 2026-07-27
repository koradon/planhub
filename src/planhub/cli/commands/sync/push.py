from __future__ import annotations

from dataclasses import dataclass

import typer

from planhub.cli.sync_plan import (
    SyncPlan,
    apply_sync_plan,
    archive_closed_issues_in_filesystem,
    reconcile_milestone_archive_locations,
)
from planhub.config import PlanHubConfig
from planhub.github import GitHubClient
from planhub.layout import PlanLayout


@dataclass(frozen=True)
class PushStats:
    plan_milestones_create: int = 0
    plan_milestones_update: int = 0
    plan_issues_create: int = 0
    plan_issues_update: int = 0
    archived_issues: int = 0
    deleted_issues: int = 0
    parsed_milestones: int = 0
    parsed_issues: int = 0


def run_push(
    plan: SyncPlan,
    parsed_milestones: int,
    parsed_issues: int,
    layout: PlanLayout,
    config: PlanHubConfig,
    *,
    client: GitHubClient | None,
    owner_repo: tuple[str, str] | None,
    errors: list[str],
    dry_run: bool,
) -> PushStats:
    """Apply an already-parsed sync plan to GitHub, then settle the filesystem.

    Callers are expected to have parsed `plan` via `build_sync_plan` and
    handled any parse errors (with an immediate exit) before calling this.

    On `--dry-run`, reports the plan without applying it or running the
    archive step, matching today's `sync --dry-run` behavior (archive/delete
    counts stay at zero). Runtime errors (missing credentials, apply/archive
    failures) are appended to `errors` for the caller to report and exit on.
    """
    counts = {"parsed_milestones": parsed_milestones, "parsed_issues": parsed_issues}

    if dry_run:
        return PushStats(
            plan_milestones_create=len(plan.milestones_to_create),
            plan_milestones_update=len(plan.milestones_to_update),
            plan_issues_create=len(plan.issues_to_create),
            plan_issues_update=len(plan.issues_to_update),
            **counts,
        )

    has_pending_writes = bool(
        plan.milestones_to_create
        or plan.issues_to_create
        or plan.milestones_to_update
        or plan.issues_to_update
    )
    if has_pending_writes:
        if client is None or owner_repo is None:
            errors.append("Missing GitHub credentials. Cannot push issues/milestones.")
            return PushStats(**counts)
        apply_stats = apply_sync_plan(client, owner_repo, plan, errors, config, layout)
        milestones_create = apply_stats.milestones_created
        milestones_update = apply_stats.milestones_updated
        issues_create = apply_stats.issues_created
        issues_update = apply_stats.issues_updated
    else:
        milestones_create = milestones_update = issues_create = issues_update = 0

    archived_issues = 0
    deleted_issues = 0
    if not errors:
        archive_stats = archive_closed_issues_in_filesystem(
            layout, config, errors=errors, dry_run=dry_run
        )
        archived_issues = archive_stats.archived_count
        deleted_issues = archive_stats.deleted_count
        reconcile_milestone_archive_locations(
            layout,
            errors=errors,
            dry_run=dry_run,
            move_open_to_active=False,
            move_closed_to_archive=True,
        )

    return PushStats(
        plan_milestones_create=milestones_create,
        plan_milestones_update=milestones_update,
        plan_issues_create=issues_create,
        plan_issues_update=issues_update,
        archived_issues=archived_issues,
        deleted_issues=deleted_issues,
        **counts,
    )


def echo_push_summary(stats: PushStats, *, dry_run: bool) -> None:
    mode = "would " if dry_run else ""
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
    typer.echo(f"📂 Parsed: {stats.parsed_milestones} milestones, {stats.parsed_issues} issues.")


def echo_verbose_plan(plan: SyncPlan) -> None:
    typer.echo("🔎 [verbose] Planned changes:")
    for milestone_path, _ in plan.milestones_to_create:
        typer.echo(f"  + milestone create: {milestone_path}")
    for milestone_path, _ in plan.milestones_to_update:
        typer.echo(f"  ~ milestone update: {milestone_path}")
    for issue_path, _, _ in plan.issues_to_create:
        typer.echo(f"  + issue create: {issue_path}")
    for issue_path, _, _ in plan.issues_to_update:
        typer.echo(f"  ~ issue update: {issue_path}")
