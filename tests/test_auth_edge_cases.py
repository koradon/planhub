from __future__ import annotations

from unittest.mock import patch

from planhub.auth import get_auth_token


def test_get_auth_token_prefers_github_token_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    monkeypatch.delenv("GH_TOKEN", raising=False)

    assert get_auth_token() == "env-token"


def test_get_auth_token_falls_back_to_gh_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "gh-token")

    assert get_auth_token() == "gh-token"


@patch("planhub.auth.subprocess.run")
def test_get_auth_token_uses_gh_cli_when_env_missing(mock_run, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "gh-cli-token\n"

    assert get_auth_token() == "gh-cli-token"


@patch("planhub.auth.subprocess.run")
def test_get_auth_token_returns_none_when_gh_cli_fails(mock_run, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""

    assert get_auth_token() is None
