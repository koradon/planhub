from __future__ import annotations

from unittest.mock import patch

import pytest

from planhub.repository import get_github_repo_from_git, parse_github_remote


def test_parse_github_remote_strips_git_suffix() -> None:
    assert parse_github_remote("https://github.com/acme/roadmap.git") == ("acme", "roadmap")


def test_parse_github_remote_rejects_extra_path_segments() -> None:
    assert parse_github_remote("https://github.com/acme/roadmap/extra") is None


@patch("planhub.repository.subprocess.run")
def test_get_github_repo_from_git_errors_on_nonzero_git_exit(mock_run, tmp_path) -> None:
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""

    with pytest.raises(ValueError, match="Missing git remote origin URL"):
        get_github_repo_from_git(tmp_path)


@patch("planhub.repository.subprocess.run")
def test_get_github_repo_from_git_errors_on_unsupported_remote(mock_run, tmp_path) -> None:
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "git@gitlab.com:acme/roadmap.git\n"

    with pytest.raises(ValueError, match="Unsupported git remote URL"):
        get_github_repo_from_git(tmp_path)
