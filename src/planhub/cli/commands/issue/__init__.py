from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from planhub.auth import get_auth_token
from planhub.documents import render_markdown
from planhub.github import GitHubClient
from planhub.layout import ensure_layout
from planhub.repository import get_github_repo_from_git


def issue_command(title: str) -> None:
    """Create a new GitHub issue with the given title."""
    repo_root = Path.cwd()

    # Get authentication token
    token = get_auth_token()
    if not token:
        typer.echo("Error: No GitHub token found. Set GITHUB_TOKEN or run 'gh auth login'.")
        raise typer.Exit(code=1)

    # Get repository information
    try:
        owner, repo = get_github_repo_from_git(repo_root)
    except ValueError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc

    # Ensure .plan directory exists
    layout = ensure_layout(repo_root)

    # Create GitHub client and issue
    client = GitHubClient(token=token)
    try:
        issue = client.create_issue(owner=owner, repo=repo, title=title)
        issue_number = issue.get("number")
        issue_url = issue.get("html_url")
        issue_state = issue.get("state", "open")
        assignees = issue.get("assignees", [])
        assignee_logins = [
            assignee.get("login")
            for assignee in assignees
            if isinstance(assignee, dict) and assignee.get("login")
        ]

        # Generate filename: YYYYMMDD-title-slug.md
        date_str = datetime.now().strftime("%Y%m%d")
        title_slug = _slugify(title) or "issue"
        base_name = f"{date_str}-{title_slug}"
        issue_path = layout.issues_dir / f"{base_name}.md"

        # Handle filename conflicts
        if issue_path.exists():
            issue_path = layout.issues_dir / f"{base_name}-{issue_number}.md"

        # Create issue file with front matter
        front_matter: dict[str, Any] = {
            "title": title,
            "number": issue_number,
            "state": issue_state,
            "assignees": assignee_logins,
        }
        content = render_markdown(front_matter, "")
        issue_path.write_text(content, encoding="utf-8")

        typer.echo(f"Created issue #{issue_number}: {title}")
        typer.echo(f"View at: {issue_url}")
        typer.echo(f"Saved to: {issue_path}")
    except Exception as exc:
        typer.echo(f"Error creating issue: {exc}")
        raise typer.Exit(code=1) from exc


def _slugify(value: str) -> str:
    """Convert a string to a URL-friendly slug."""
    slug: list[str] = []
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
        elif char in {" ", "-", "_"}:
            slug.append("-")
    normalized = "".join(slug).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or "issue"
