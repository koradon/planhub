from __future__ import annotations

import typer

from planhub.cli.commands import init_command, issue_command, setup_command, sync_command

app = typer.Typer(help="Planhub CLI.")


@app.command("init")
def init_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
) -> None:
    init_command(dry_run=dry_run)


@app.command("setup")
def setup_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
) -> None:
    setup_command(dry_run=dry_run)


@app.command("sync")
def sync_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed sync output."),
    compact: bool = typer.Option(False, "--compact", help="Force compact sync output."),
) -> None:
    verbosity_override: str | None = None
    if verbose and compact:
        raise typer.BadParameter("Use either --verbose or --compact, not both.")
    if verbose:
        verbosity_override = "verbose"
    if compact:
        verbosity_override = "compact"
    sync_command(dry_run=dry_run, verbosity_override=verbosity_override)


@app.command("issue")
def issue_entry(title: str = typer.Argument(..., help="Title of the issue to create.")) -> None:
    issue_command(title=title)


def main() -> None:
    app()
