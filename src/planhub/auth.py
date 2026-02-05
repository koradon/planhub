from __future__ import annotations

import os
import subprocess


def get_auth_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    return _get_token_from_gh()


def _get_token_from_gh() -> str | None:
    result = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    token = result.stdout.strip()
    return token or None
