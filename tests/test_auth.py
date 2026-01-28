from unittest.mock import patch

from planhub.auth import get_auth_token


def test_get_auth_token_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")

    assert get_auth_token() == "env-token"


@patch("planhub.auth.subprocess.run")
def test_get_auth_token_uses_gh(mock_run, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "gh-token\n"

    assert get_auth_token() == "gh-token"
