from __future__ import annotations

import sys
from pathlib import Path

import typer

from planhub.config import _global_config_path, ensure_global_config, ensure_repo_config
from planhub.layout import ensure_layout
from planhub.skills import install_skills, skill_install_paths


def init_command(*, dry_run: bool, skills: bool | None = None) -> None:
    repo_root = Path.cwd()
    if dry_run:
        plan_root = repo_root / ".plan"
        milestones_dir = plan_root / "milestones"
        issues_dir = plan_root / "issues"
        typer.echo("🧪 [dry-run] Would prepare plan layout:")
        typer.echo(f"- {plan_root}")
        typer.echo(f"- {milestones_dir}")
        typer.echo(f"- {issues_dir}")
        typer.echo("🧪 [dry-run] Would create config files (if missing):")
        typer.echo(f"- {_global_config_path()}")
        typer.echo(f"- {plan_root / 'config.yaml'}")
        typer.echo("🧪 [dry-run] Would offer to install Claude/Cursor skills:")
        for path in skill_install_paths(repo_root):
            typer.echo(f"- {path}")
        return

    layout = ensure_layout(repo_root)
    global_created = ensure_global_config()
    repo_created = ensure_repo_config(repo_root)
    typer.echo(f"✅ Plan layout ready at {layout.root}")
    typer.echo(
        "⚙️ Global config:"
        f" {'created' if global_created else 'already exists'} at {_global_config_path()}"
    )
    typer.echo(
        "⚙️ Repository config:"
        f" {'created' if repo_created else 'already exists'} at {layout.root / 'config.yaml'}"
    )

    install = skills
    if install is None:
        install = sys.stdin.isatty() and typer.confirm(
            "Install Claude/Cursor skills for authoring .plan/ issues and milestones?",
            default=True,
        )
    if install:
        result = install_skills(repo_root)
        for path in result.created:
            typer.echo(f"🧩 Skill installed: {path}")
        for path in result.updated:
            typer.echo(f"🧩 Skill updated: {path}")
        for path in result.unchanged:
            typer.echo(f"🧩 Skill already up to date: {path}")
    else:
        typer.echo(
            "🧩 Skipped Claude/Cursor skills (run `planhub init --skills` later to add them)."
        )
