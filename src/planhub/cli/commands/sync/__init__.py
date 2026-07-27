from __future__ import annotations

from pathlib import Path

import typer

from planhub.auth import get_auth_token
from planhub.cli.commands.sync.pull import PullStats, echo_pull_summary, run_pull
from planhub.cli.commands.sync.push import (
    PushStats,
    echo_push_summary,
    echo_verbose_plan,
    run_push,
)
from planhub.cli.sync_plan import build_sync_plan
from planhub.config import PlanHubConfig, load_config
from planhub.github import GitHubClient
from planhub.layout import PlanLayout, load_layout
from planhub.repository import get_github_repo_from_git


def pull_command(*, dry_run: bool, force: bool, verbosity_override: str | None = None) -> None:
    del verbosity_override  # accepted for CLI symmetry with sync/push; no verbose output yet.
    repo_root = Path.cwd()
    layout, _config = _load_layout_and_config(repo_root)
    errors: list[str] = []

    client, owner_repo = _resolve_client(repo_root)
    stats = run_pull(
        layout,
        client=client,
        owner_repo=owner_repo,
        errors=errors,
        dry_run=dry_run,
        force=force,
    )
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)

    if dry_run:
        typer.echo("🧪 [dry-run] No changes written.")
        echo_pull_summary(stats, dry_run=True)
        return

    typer.echo("✅ Pull completed.")
    echo_pull_summary(stats, dry_run=False)


def push_command(*, dry_run: bool, verbosity_override: str | None = None) -> None:
    repo_root = Path.cwd()
    layout, config = _load_layout_and_config(repo_root)
    verbose_output = (verbosity_override or config.sync.behavior.verbosity) == "verbose"
    errors: list[str] = []

    client, owner_repo = _resolve_client(repo_root)
    plan, parsed_milestones, parsed_issues, parse_errors = build_sync_plan(layout)
    errors.extend(parse_errors)
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)

    stats = run_push(
        plan,
        parsed_milestones,
        parsed_issues,
        layout,
        config,
        client=client,
        owner_repo=owner_repo,
        errors=errors,
        dry_run=dry_run,
    )

    if dry_run:
        typer.echo("🧪 [dry-run] No changes written.")
        echo_push_summary(stats, dry_run=True)
        if verbose_output:
            echo_verbose_plan(plan)
        return

    if errors:
        for error in errors:
            typer.echo(f"❌ {error}")
        raise typer.Exit(code=1)

    typer.echo("✅ Push completed.")
    echo_push_summary(stats, dry_run=False)
    if verbose_output:
        echo_verbose_plan(plan)


def sync_command(*, dry_run: bool, verbosity_override: str | None = None) -> None:
    repo_root = Path.cwd()
    layout, config = _load_layout_and_config(repo_root)
    verbose_output = (verbosity_override or config.sync.behavior.verbosity) == "verbose"
    errors: list[str] = []

    client, owner_repo = _resolve_client(repo_root)

    pull_stats = run_pull(
        layout,
        client=client,
        owner_repo=owner_repo,
        errors=errors,
        dry_run=dry_run,
        force=False,
    )
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)

    plan, parsed_milestones, parsed_issues, parse_errors = build_sync_plan(layout)
    errors.extend(parse_errors)
    if _report_parse_errors(errors):
        raise typer.Exit(code=1)

    push_stats = run_push(
        plan,
        parsed_milestones,
        parsed_issues,
        layout,
        config,
        client=client,
        owner_repo=owner_repo,
        errors=errors,
        dry_run=dry_run,
    )

    if dry_run:
        typer.echo("🧪 [dry-run] No changes written.")
        echo_pull_summary(pull_stats, dry_run=True)
        echo_push_summary(push_stats, dry_run=True)
        if verbose_output:
            echo_verbose_plan(plan)
        return

    if errors:
        for error in errors:
            typer.echo(f"❌ {error}")
        raise typer.Exit(code=1)

    typer.echo("✅ Sync completed.")
    echo_pull_summary(pull_stats, dry_run=False)
    echo_push_summary(push_stats, dry_run=False)
    if verbose_output:
        echo_verbose_plan(plan)


def _load_layout_and_config(repo_root: Path) -> tuple[PlanLayout, PlanHubConfig]:
    try:
        layout = load_layout(repo_root)
    except FileNotFoundError as exc:
        typer.echo(f"{exc}. Run 'planhub init' first.")
        raise typer.Exit(code=1) from exc
    config = load_config(repo_root)
    return layout, config


def _resolve_client(
    repo_root: Path,
) -> tuple[GitHubClient | None, tuple[str, str] | None]:
    auth = _get_github_client(repo_root)
    if auth is None:
        return None, None
    client, owner, repo = auth
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


__all__ = [
    "PullStats",
    "PushStats",
    "pull_command",
    "push_command",
    "sync_command",
]
