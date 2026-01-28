from __future__ import annotations

import os
import subprocess
from typing import Optional


def get_auth_token() -> Optional[str]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    return _get_token_from_gh()


def _get_token_from_gh() -> Optional[str]:
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
