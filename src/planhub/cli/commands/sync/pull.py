from __future__ import annotations

from dataclasses import dataclass

import typer

from planhub.cli.sync_plan import reconcile_milestone_archive_locations
from planhub.github import GitHubClient
from planhub.importer import import_existing_issues
from planhub.layout import PlanLayout
from planhub.milestone_sync import reconcile_milestone_states_from_github


@dataclass(frozen=True)
class PullStats:
    imported_created: int = 0
    imported_moved: int = 0
    imported_overwritten: int = 0
    imported_skipped: int = 0
    imported_milestones_created: int = 0


def run_pull(
    layout: PlanLayout,
    *,
    client: GitHubClient | None,
    owner_repo: tuple[str, str] | None,
    errors: list[str],
    dry_run: bool,
    force: bool,
) -> PullStats:
    """Reconcile milestone state from GitHub, then import new/updated remote issues.

    Never writes to GitHub. Runs the local archive-location reconcile even when
    no credentials are available, matching today's `sync` behavior.
    """
    if client is not None and owner_repo is not None:
        owner, repo = owner_repo
        reconcile_milestone_states_from_github(
            client,
            owner,
            repo,
            layout,
            errors=errors,
            dry_run=dry_run,
        )
        if errors:
            return PullStats()

    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=dry_run,
        move_open_to_active=True,
        move_closed_to_archive=False,
    )
    if errors:
        return PullStats()

    if client is None or owner_repo is None:
        return PullStats()

    owner, repo = owner_repo
    import_result = import_existing_issues(
        layout,
        owner,
        repo,
        client=client,
        dry_run=dry_run,
        force=force,
    )

    reconcile_milestone_archive_locations(
        layout,
        errors=errors,
        dry_run=dry_run,
        move_open_to_active=True,
        move_closed_to_archive=False,
    )

    return PullStats(
        imported_created=import_result.issues_created,
        imported_moved=import_result.issues_moved,
        imported_overwritten=import_result.issues_overwritten,
        imported_skipped=import_result.issues_skipped,
        imported_milestones_created=import_result.milestones_created,
    )


def echo_pull_summary(stats: PullStats, *, dry_run: bool) -> None:
    mode = "would " if dry_run else ""
    typer.echo(
        "📥 Import:"
        f" {mode}create {stats.imported_created} issues,"
        f" {mode}move {stats.imported_moved} issues,"
        f" {mode}overwrite {stats.imported_overwritten},"
        f" skip {stats.imported_skipped},"
        f" {mode}create {stats.imported_milestones_created} milestones."
    )
