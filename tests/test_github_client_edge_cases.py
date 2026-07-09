from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from planhub.github import GitHubAPIError, GitHubClient, IssueState


def _create_mock_response(
    payload: dict | list,
    status_code: int = 200,
    headers: dict | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.content = json.dumps(payload).encode("utf-8")
    response.headers = headers or {}
    return response


def test_create_milestone_builds_request() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"number": 3})

    client = GitHubClient(token="token-123", session=mock_session)
    payload = client.create_milestone(
        "acme",
        "roadmap",
        "Stage 1",
        description="Scope",
        due_on="2026-12-31T00:00:00Z",
        state="open",
    )

    assert payload["number"] == 3
    assert mock_session.request.call_args.kwargs["json"] == {
        "title": "Stage 1",
        "description": "Scope",
        "due_on": "2026-12-31T00:00:00Z",
        "state": "open",
    }


def test_update_milestone_builds_patch_payload() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"number": 3})

    client = GitHubClient(token="token-123", session=mock_session)
    client.update_milestone(
        "acme",
        "roadmap",
        3,
        title="Renamed",
        description="Updated",
        due_on="2026-12-31T00:00:00Z",
        state="closed",
    )

    assert mock_session.request.call_args.kwargs["json"] == {
        "title": "Renamed",
        "description": "Updated",
        "due_on": "2026-12-31T00:00:00Z",
        "state": "closed",
    }


def test_get_issue_returns_payload() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"number": 9, "state": "open"})

    client = GitHubClient(token="token-123", session=mock_session)
    issue = client.get_issue("acme", "roadmap", 9)

    assert issue["number"] == 9
    assert mock_session.request.call_args.kwargs["url"].endswith("/issues/9")


def test_list_issues_raises_on_unexpected_response_shape() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"not": "a list"})

    client = GitHubClient(token="token-123", session=mock_session)

    with pytest.raises(GitHubAPIError, match="Unexpected issues response"):
        client.list_issues("acme", "roadmap")


def test_list_milestones_raises_on_unexpected_response_shape() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"not": "a list"})

    client = GitHubClient(token="token-123", session=mock_session)

    with pytest.raises(GitHubAPIError, match="Unexpected milestones response"):
        client.list_milestones("acme", "roadmap")


def test_update_issue_includes_optional_fields() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response({"id": 1})

    client = GitHubClient(token="token-123", session=mock_session)
    client.update_issue(
        "acme",
        "roadmap",
        42,
        title="Ship it",
        body="Details",
        labels=["p1"],
        assignees=["alice"],
        milestone=7,
        issue_type="feature",
        state=IssueState.OPEN,
    )

    assert mock_session.request.call_args.kwargs["json"] == {
        "title": "Ship it",
        "body": "Details",
        "labels": ["p1"],
        "assignees": ["alice"],
        "milestone": 7,
        "type": "feature",
        "state": "open",
    }


def test_rate_limit_raises_when_reset_header_missing() -> None:
    mock_session = MagicMock()
    mock_session.request.return_value = _create_mock_response(
        {"message": "Rate limit exceeded"},
        status_code=403,
        headers={"X-RateLimit-Remaining": "0"},
    )

    client = GitHubClient(token="token-123", session=mock_session)

    with pytest.raises(GitHubAPIError, match="Rate limit exceeded"):
        client.create_issue("acme", "roadmap", "Ship it")


def test_rate_limit_429_retries_once_then_raises() -> None:
    mock_session = MagicMock()
    mock_session.request.side_effect = [
        _create_mock_response(
            {"message": "Too many requests"},
            status_code=429,
        ),
        _create_mock_response(
            {"message": "Too many requests"},
            status_code=429,
        ),
    ]

    client = GitHubClient(token="token-123", session=mock_session)

    with patch("planhub.github.time.sleep"):
        with pytest.raises(GitHubAPIError, match="Too many requests"):
            client.create_issue("acme", "roadmap", "Ship it")

    assert mock_session.request.call_count == 2
