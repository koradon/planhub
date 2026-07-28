from __future__ import annotations

import typer

from planhub.cli.commands import (
    init_command,
    issue_command,
    pull_command,
    push_command,
    sync_command,
)

app = typer.Typer(help="Planhub CLI.")


def _resolve_verbosity_override(*, verbose: bool, compact: bool) -> str | None:
    if verbose and compact:
        raise typer.BadParameter("Use either --verbose or --compact, not both.")
    if verbose:
        return "verbose"
    if compact:
        return "compact"
    return None


@app.command("init")
def init_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
    skills: bool | None = typer.Option(
        None,
        "--skills/--no-skills",
        help="Install Claude/Cursor skills for .plan/ authoring. Omitted: you'll be asked.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Accept current config values without prompting (also installs skills"
        " when --skills/--no-skills is omitted).",
    ),
) -> None:
    init_command(dry_run=dry_run, skills=skills, accept_defaults=yes)


@app.command("pull")
def pull_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing local issue files with their current GitHub content.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed pull output."),
    compact: bool = typer.Option(False, "--compact", help="Force compact pull output."),
) -> None:
    verbosity_override = _resolve_verbosity_override(verbose=verbose, compact=compact)
    pull_command(dry_run=dry_run, force=force, verbosity_override=verbosity_override)


@app.command("push")
def push_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed push output."),
    compact: bool = typer.Option(False, "--compact", help="Force compact push output."),
) -> None:
    verbosity_override = _resolve_verbosity_override(verbose=verbose, compact=compact)
    push_command(dry_run=dry_run, verbosity_override=verbosity_override)


@app.command("sync")
def sync_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed sync output."),
    compact: bool = typer.Option(False, "--compact", help="Force compact sync output."),
) -> None:
    verbosity_override = _resolve_verbosity_override(verbose=verbose, compact=compact)
    sync_command(dry_run=dry_run, verbosity_override=verbosity_override)


@app.command("issue")
def issue_entry(title: str = typer.Argument(..., help="Title of the issue to create.")) -> None:
    issue_command(title=title)


def main() -> None:
    app()
