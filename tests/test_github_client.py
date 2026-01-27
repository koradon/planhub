import io
import json
from urllib.error import HTTPError

import pytest
from planhub.github import (
    GitHubAPIError,
    GitHubClient,
    IssueState,
    IssueStateReason,
)
from unittest.mock import patch


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _get_header(request, name: str) -> str:
    for header_name, header_value in request.header_items():
        if header_name.lower() == name.lower():
            return header_value
    raise AssertionError(f"missing header {name}")


@patch("planhub.github.urlopen")
def test_create_issue_builds_request(mock_urlopen) -> None:
    mock_urlopen.return_value = DummyResponse({"id": 123})
    client = GitHubClient(token="token-123")

    payload = client.create_issue(
        "acme", "roadmap", "Ship it", body="Details", labels=["p1"]
    )

    assert payload["id"] == 123
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.github.com/repos/acme/roadmap/issues"
    assert request.get_method() == "POST"
    assert _get_header(request, "Authorization") == "Bearer token-123"
    assert _get_header(request, "Accept") == "application/vnd.github+json"
    assert _get_header(request, "User-Agent") == "planhub"
    assert json.loads(request.data.decode("utf-8")) == {
        "title": "Ship it",
        "body": "Details",
        "labels": ["p1"],
    }


@patch("planhub.github.urlopen")
def test_request_surfaces_github_error(mock_urlopen) -> None:
    error = HTTPError(
        url="https://api.github.com/repos/acme/roadmap/issues",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b'{"message": "Bad credentials"}'),
    )
    mock_urlopen.side_effect = error
    client = GitHubClient(token="bad-token")

    with pytest.raises(GitHubAPIError) as excinfo:
        client.create_issue("acme", "roadmap", "Ship it")

    assert excinfo.value.status_code == 401
    assert "Bad credentials" in str(excinfo.value)


@patch("planhub.github.urlopen")
def test_update_issue_state_sends_patch(mock_urlopen) -> None:
    mock_urlopen.return_value = DummyResponse({"state": "closed"})
    client = GitHubClient(token="token-123")

    payload = client.update_issue_state(
        "acme", "roadmap", 42, IssueState.CLOSED, IssueStateReason.COMPLETED
    )

    assert payload["state"] == "closed"
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.github.com/repos/acme/roadmap/issues/42"
    assert request.get_method() == "PATCH"
    assert json.loads(request.data.decode("utf-8")) == {
        "state": "closed",
        "state_reason": "completed",
    }


@patch("planhub.github.urlopen")
def test_close_issue_uses_state_reason(mock_urlopen) -> None:
    mock_urlopen.return_value = DummyResponse({"state": "closed"})
    client = GitHubClient(token="token-123")

    payload = client.close_issue(
        "acme", "roadmap", 42, state_reason=IssueStateReason.NOT_PLANNED
    )

    assert payload["state"] == "closed"
    request = mock_urlopen.call_args[0][0]
    assert json.loads(request.data.decode("utf-8")) == {
        "state": "closed",
        "state_reason": "not_planned",
    }


@patch("planhub.github.urlopen")
def test_reopen_issue_clears_state_reason(mock_urlopen) -> None:
    mock_urlopen.return_value = DummyResponse({"state": "open"})
    client = GitHubClient(token="token-123")

    payload = client.reopen_issue("acme", "roadmap", 42)

    assert payload["state"] == "open"
    request = mock_urlopen.call_args[0][0]
    assert json.loads(request.data.decode("utf-8")) == {"state": "open"}
