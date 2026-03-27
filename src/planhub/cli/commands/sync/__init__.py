from __future__ import annotations

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
from planhub.importer import import_existing_issues
from planhub.layout import PlanLayout, load_layout
from planhub.repository import get_github_repo_from_git


def sync_command(*, dry_run: bool) -> None:
    repo_root = Path.cwd()
    try:
        layout = load_layout(repo_root)
    except FileNotFoundError as exc:
        typer.echo(f"{exc}. Run 'planhub init' first.")
        raise typer.Exit(code=1) from exc

    # Load layered config once per command invocation.
    config = load_config(repo_root)
    errors: list[str] = []

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
    owner_repo = _import_existing_issues_if_possible(
        layout,
        repo_root,
        dry_run=dry_run,
    )
    if owner_repo is not None:
        client, owner_repo = owner_repo

    plan, parsed_milestones, parsed_issues, errors = build_sync_plan(layout)
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)

    if dry_run:
        typer.echo("Dry run: no changes will be written.")
        typer.echo(
            "Dry run: would create"
            f" {len(plan.milestones_to_create)} milestones and"
            f" {len(plan.issues_to_create)} issues."
        )
        typer.echo(
            "Dry run: would update"
            f" {len(plan.milestones_to_update)} milestones and"
            f" {len(plan.issues_to_update)} issues."
        )
        typer.echo(f"Found {parsed_milestones} milestones and {parsed_issues} issues.")
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
        apply_sync_plan(client, owner_repo, plan, errors, config, layout)

    if not errors:
        archive_closed_issues_in_filesystem(layout, config, errors=errors, dry_run=dry_run)
        reconcile_milestone_archive_locations(
            layout,
            errors=errors,
            dry_run=dry_run,
            move_open_to_active=False,
            move_closed_to_archive=True,
        )

    if errors:
        for error in errors:
            typer.echo(f"Error: {error}")
        raise typer.Exit(code=1)
    typer.echo(f"Found {parsed_milestones} milestones and {parsed_issues} issues.")


def _import_existing_issues_if_possible(
    layout: PlanLayout,
    repo_root: Path,
    *,
    dry_run: bool,
) -> tuple[GitHubClient, tuple[str, str]] | None:
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
    typer.echo(
        "Imported issues:"
        f" {result.issues_created} created,"
        f" {result.issues_moved} moved,"
        f" {result.issues_skipped} skipped,"
        f" {result.milestones_created} milestones created."
    )
    return client, (owner, repo)


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
        typer.echo("Missing GitHub credentials. Set GITHUB_TOKEN/GH_TOKEN or run 'gh auth login'.")
        return None
    try:
        owner, repo = get_github_repo_from_git(repo_root)
    except ValueError as exc:
        typer.echo(f"{exc} Cannot sync issues.")
        return None
    return GitHubClient(token), owner, repo
