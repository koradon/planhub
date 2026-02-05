from __future__ import annotations

import subprocess
from pathlib import Path


def get_github_repo_from_git(repo_root: Path) -> tuple[str, str]:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    url = result.stdout.strip()
    if result.returncode != 0 or not url:
        raise ValueError("Missing git remote origin URL.")

    parsed = parse_github_remote(url)
    if parsed is None:
        raise ValueError(f"Unsupported git remote URL: {url}")
    return parsed


def parse_github_remote(url: str) -> tuple[str, str] | None:
    if url.startswith("git@github.com:"):
        path = url.replace("git@github.com:", "", 1)
    elif url.startswith("https://github.com/"):
        path = url.replace("https://github.com/", "", 1)
    elif url.startswith("https://www.github.com/"):
        path = url.replace("https://www.github.com/", "", 1)
    else:
        return None

    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = [part for part in path.split("/") if part]
    if len(parts) != 2:
        return None
    return parts[0], parts[1]
