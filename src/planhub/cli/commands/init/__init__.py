from __future__ import annotations

import sys
from pathlib import Path

import typer

from planhub.cli.config_prompts import describe_prompts_dry_run, run_config_prompts
from planhub.config import ConfigError, ensure_repo_config, write_repo_config_values
from planhub.layout import ensure_layout
from planhub.skills import install_skills, skill_install_paths


def init_command(
    *, dry_run: bool, skills: bool | None = None, accept_defaults: bool = False
) -> None:
    repo_root = Path.cwd()
    if dry_run:
        plan_root = repo_root / ".plan"
        milestones_dir = plan_root / "milestones"
        issues_dir = plan_root / "issues"
        typer.echo("🧪 [dry-run] Would prepare plan layout:")
        typer.echo(f"- {plan_root}")
        typer.echo(f"- {milestones_dir}")
        typer.echo(f"- {issues_dir}")
        typer.echo("🧪 [dry-run] Would create config file (if missing):")
        typer.echo(f"- {plan_root / 'config.yaml'}")
        typer.echo("🧪 [dry-run] Would ask:")
        for line in describe_prompts_dry_run(target_path=plan_root / "config.yaml"):
            typer.echo(line)
        typer.echo("🧪 [dry-run] Would offer to install Claude/Cursor skills:")
        for path in skill_install_paths(repo_root):
            typer.echo(f"- {path}")
        return

    layout = ensure_layout(repo_root)
    repo_created = ensure_repo_config(repo_root)
    typer.echo(f"✅ Plan layout ready at {layout.root}")
    typer.echo(
        "⚙️ Repository config:"
        f" {'created' if repo_created else 'already exists'} at {layout.root / 'config.yaml'}"
    )

    config_path = layout.root / "config.yaml"
    interactive = (not accept_defaults) and sys.stdin.isatty()
    try:
        outcome = run_config_prompts(
            target_path=config_path,
            interactive=interactive,
            skip_reason="accepted-defaults" if accept_defaults else None,
        )
        wrote = bool(outcome.updates) and write_repo_config_values(repo_root, outcome.updates)
        if wrote:
            typer.echo(f"⚙️ Updated repository config at {config_path}")
        else:
            typer.echo("⚙️ Repository config unchanged.")
        if outcome.skip_reason == "accepted-defaults":
            typer.echo("ℹ️ Skipped config prompts (--yes); kept current values.")
        elif outcome.skip_reason == "non-interactive":
            typer.echo("ℹ️ Non-interactive shell: skipped config prompts (current values kept).")
    except ConfigError as error:
        typer.echo(f"⚠️ Skipped config prompts: {error}")

    install = skills
    if install is None:
        if accept_defaults:
            install = True
        else:
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
