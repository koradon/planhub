import json
from unittest.mock import MagicMock, patch

import pytest

from planhub.github import (
    GitHubAPIError,
    GitHubClient,
    IssueState,
    IssueStateReason,
)


def _create_mock_response(
    payload: dict | list,
    status_code: int = 200,
    headers: dict | None = None,
) -> MagicMock:
    """Create a mock requests.Response object."""
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.content = json.dumps(payload).encode("utf-8")
    response.headers = headers or {}
    return response


def test_create_issue_builds_request() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"id": 123})

    client = GitHubClient(token="token-123", session=mock_session)
    payload = client.create_issue("acme", "roadmap", "Ship it", body="Details", labels=["p1"])

    assert payload["id"] == 123
    mock_session.request.assert_called_once()
    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["url"] == "https://api.github.com/repos/acme/roadmap/issues"
    assert call_kwargs["json"] == {
        "title": "Ship it",
        "body": "Details",
        "labels": ["p1"],
    }
    # Verify headers were set on session
    assert mock_session.headers.update.called


def test_request_surfaces_github_error() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response(
        {"message": "Bad credentials"}, status_code=401
    )

    client = GitHubClient(token="bad-token", session=mock_session)

    with pytest.raises(GitHubAPIError) as excinfo:
        client.create_issue("acme", "roadmap", "Ship it")

    assert excinfo.value.status_code == 401
    assert "Bad credentials" in str(excinfo.value)


def test_update_issue_state_sends_patch() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"state": "closed"})

    client = GitHubClient(token="token-123", session=mock_session)
    payload = client.update_issue_state(
        "acme", "roadmap", 42, IssueState.CLOSED, IssueStateReason.COMPLETED
    )

    assert payload["state"] == "closed"
    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["method"] == "PATCH"
    assert call_kwargs["url"] == "https://api.github.com/repos/acme/roadmap/issues/42"
    assert call_kwargs["json"] == {
        "state": "closed",
        "state_reason": "completed",
    }


def test_close_issue_uses_state_reason() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"state": "closed"})

    client = GitHubClient(token="token-123", session=mock_session)
    payload = client.close_issue("acme", "roadmap", 42, state_reason=IssueStateReason.NOT_PLANNED)

    assert payload["state"] == "closed"
    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["json"] == {
        "state": "closed",
        "state_reason": "not_planned",
    }


def test_reopen_issue_clears_state_reason() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"state": "open"})

    client = GitHubClient(token="token-123", session=mock_session)
    payload = client.reopen_issue("acme", "roadmap", 42)

    assert payload["state"] == "open"
    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["json"] == {"state": "open"}


def test_update_issue_includes_state_reason_when_closed() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"id": 1})

    client = GitHubClient(token="token-123", session=mock_session)
    client.update_issue(
        "acme",
        "roadmap",
        42,
        state=IssueState.CLOSED,
        state_reason=IssueStateReason.COMPLETED,
    )

    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["json"] == {
        "state": "closed",
        "state_reason": "completed",
    }


def test_list_issues_paginates() -> None:
    mock_session = MagicMock()
    mock_session.request.side_effect = [
        _create_mock_response([{"id": 1}], headers={"Link": '<x>; rel="next"'}),
        _create_mock_response([{"id": 2}], headers={}),
    ]

    client = GitHubClient(token="token-123", session=mock_session)
    issues = client.list_issues("acme", "roadmap", state="all")

    assert [issue["id"] for issue in issues] == [1, 2]
    assert mock_session.request.call_count == 2


def test_update_issue_clears_milestone_and_guards_state_reason() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"id": 1})

    client = GitHubClient(token="token-123", session=mock_session)
    client.update_issue(
        "acme",
        "roadmap",
        42,
        title="Ship it",
        labels=[],
        assignees=[],
        clear_milestone=True,
        state=None,
        state_reason=IssueStateReason.COMPLETED,
    )

    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["json"] == {
        "title": "Ship it",
        "labels": [],
        "assignees": [],
        "milestone": None,
    }


def test_rate_limit_handling() -> None:
    """Test that rate limit responses are handled gracefully."""
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response(
        {"message": "Rate limit exceeded"},
        status_code=403,
        headers={"X-RateLimit-Remaining": "100"},  # Not actually rate limited
    )

    client = GitHubClient(token="token-123", session=mock_session)

    with pytest.raises(GitHubAPIError) as excinfo:
        client.create_issue("acme", "roadmap", "Ship it")

    assert excinfo.value.status_code == 403


def test_rate_limit_retries_after_reset() -> None:
    mock_session = MagicMock()
    mock_session.request.side_effect = [
        _create_mock_response(
            {"message": "Rate limit exceeded"},
            status_code=403,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "100"},
        ),
        _create_mock_response({"id": 1}, status_code=200),
    ]

    client = GitHubClient(token="token-123", session=mock_session)

    with patch("planhub.github.time.time", return_value=99):
        payload = client.create_issue("acme", "roadmap", "Ship it")

    assert payload["id"] == 1
    assert mock_session.request.call_count == 2
