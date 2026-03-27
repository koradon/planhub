from __future__ import annotations

import typer

from planhub.config import _global_config_path as global_config_path, ensure_global_config


def setup_command(*, dry_run: bool) -> None:
    if dry_run:
        typer.echo("🧪 [dry-run] Would create global config:")
        typer.echo(f"- {global_config_path()}")
        return

    created = ensure_global_config()
    if created:
        typer.echo(f"✅ Created global config at {global_config_path()}")
    else:
        typer.echo(f"ℹ️ Global config already exists at {global_config_path()}")
