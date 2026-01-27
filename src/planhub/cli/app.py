from __future__ import annotations

import typer

from planhub.cli.commands import init_command, sync_command

app = typer.Typer(help="Planhub CLI.")


@app.command("init")
def init_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
) -> None:
    init_command(dry_run=dry_run)


@app.command("sync")
def sync_entry(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing."
    ),
    import_existing: bool = typer.Option(
        False,
        "--import-existing",
        help="Import existing GitHub issues into .plan files.",
    ),
) -> None:
    sync_command(dry_run=dry_run, import_existing=import_existing)


def main() -> None:
    app()
