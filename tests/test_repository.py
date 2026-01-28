from unittest.mock import patch

import pytest

from planhub.repository import get_github_repo_from_git, parse_github_remote


def test_parse_github_remote_supports_https_and_ssh() -> None:
    assert parse_github_remote("https://github.com/acme/roadmap") == ("acme", "roadmap")
    assert parse_github_remote("https://www.github.com/acme/roadmap") == (
        "acme",
        "roadmap",
    )
    assert parse_github_remote("git@github.com:acme/roadmap.git") == ("acme", "roadmap")


def test_parse_github_remote_rejects_invalid() -> None:
    assert parse_github_remote("git@example.com:acme/roadmap.git") is None
    assert parse_github_remote("https://github.com/acme") is None


@patch("planhub.repository.subprocess.run")
def test_get_github_repo_from_git_reads_remote(mock_run, tmp_path) -> None:
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "https://github.com/acme/roadmap\n"

    assert get_github_repo_from_git(tmp_path) == ("acme", "roadmap")


@patch("planhub.repository.subprocess.run")
def test_get_github_repo_from_git_errors_on_missing_remote(mock_run, tmp_path) -> None:
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = ""

    with pytest.raises(ValueError, match="Missing git remote origin URL"):
        get_github_repo_from_git(tmp_path)
