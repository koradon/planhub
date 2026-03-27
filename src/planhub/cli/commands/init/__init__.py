from __future__ import annotations

from pathlib import Path

import typer

from planhub.config import _global_config_path, ensure_global_config, ensure_repo_config
from planhub.layout import ensure_layout


def init_command(*, dry_run: bool) -> None:
    repo_root = Path.cwd()
    if dry_run:
        plan_root = repo_root / ".plan"
        milestones_dir = plan_root / "milestones"
        issues_dir = plan_root / "issues"
        typer.echo("Dry run: would create plan layout:")
        typer.echo(f"- {plan_root}")
        typer.echo(f"- {milestones_dir}")
        typer.echo(f"- {issues_dir}")
        typer.echo("Dry run: would create config files (if missing):")
        typer.echo(f"- {_global_config_path()}")
        typer.echo(f"- {plan_root / 'config.yaml'}")
        return

    layout = ensure_layout(repo_root)
    ensure_global_config()
    ensure_repo_config(repo_root)
    typer.echo(f"Initialized plan layout at {layout.root}")
