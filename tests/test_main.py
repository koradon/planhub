from __future__ import annotations

import subprocess
import sys


def test_module_entry_point_shows_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "planhub", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "sync" in result.stdout
