from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class GitHubAPIError(RuntimeError):
    status_code: int
    message: str
    response_body: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        return f"GitHub API error {self.status_code}: {self.message}"


class IssueState(Enum):
    OPEN = "open"
    CLOSED = "closed"


class IssueStateReason(Enum):
    COMPLETED = "completed"
    NOT_PLANNED = "not_planned"
    REOPENED = "reopened"


def _create_session(max_retries: int = 3) -> requests.Session:
    """Create a requests session with connection pooling and retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class GitHubClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://api.github.com",
        session: requests.Session | None = None,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._session = session or _create_session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "planhub",
            }
        )

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
        issue_type: str | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if body is not None:
            payload["body"] = body
        if labels is not None:
            payload["labels"] = labels
        if assignees is not None:
            payload["assignees"] = assignees
        if milestone is not None:
            payload["milestone"] = milestone
        if issue_type is not None:
            payload["type"] = issue_type
        return self._request("POST", f"/repos/{owner}/{repo}/issues", payload)

    def get_issue(self, owner: str, repo: str, number: int) -> Mapping[str, Any]:
        return self._request("GET", f"/repos/{owner}/{repo}/issues/{number}")

    def update_issue_state(
        self,
        owner: str,
        repo: str,
        number: int,
        state: IssueState,
        state_reason: IssueStateReason | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {"state": state.value}
        if state_reason is not None:
            payload["state_reason"] = state_reason.value
        return self._request("PATCH", f"/repos/{owner}/{repo}/issues/{number}", payload)

    def update_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        *,
        title: str | None = None,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
        clear_milestone: bool = False,
        issue_type: str | None = None,
        state: IssueState | None = None,
        state_reason: IssueStateReason | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if labels is not None:
            payload["labels"] = labels
        if assignees is not None:
            payload["assignees"] = assignees
        if milestone is not None or clear_milestone:
            payload["milestone"] = milestone
        if issue_type is not None:
            payload["type"] = issue_type
        if state is not None:
            payload["state"] = state.value
        if state_reason is not None and state == IssueState.CLOSED:
            payload["state_reason"] = state_reason.value
        return self._request("PATCH", f"/repos/{owner}/{repo}/issues/{number}", payload)

    def list_issues(self, owner: str, repo: str, state: str = "open") -> list[Mapping[str, Any]]:
        issues: list[Mapping[str, Any]] = []
        page = 1
        while True:
            path = f"/repos/{owner}/{repo}/issues?state={state}&per_page=100&page={page}"
            data, headers = self._request_with_headers("GET", path)
            if not isinstance(data, list):
                raise GitHubAPIError(
                    status_code=500,
                    message="Unexpected issues response.",
                    response_body={"data": data},
                )
            issues.extend(data)
            if not _has_next_link(headers.get("Link")):
                break
            page += 1
        return issues

    def close_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        state_reason: IssueStateReason | None = None,
    ) -> Mapping[str, Any]:
        return self.update_issue_state(
            owner, repo, number, IssueState.CLOSED, state_reason=state_reason
        )

    def reopen_issue(self, owner: str, repo: str, number: int) -> Mapping[str, Any]:
        return self.update_issue_state(owner, repo, number, IssueState.OPEN)

    def create_milestone(
        self,
        owner: str,
        repo: str,
        title: str,
        description: str | None = None,
        due_on: str | None = None,
        state: str | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if description is not None:
            payload["description"] = description
        if due_on is not None:
            payload["due_on"] = due_on
        if state is not None:
            payload["state"] = state
        return self._request("POST", f"/repos/{owner}/{repo}/milestones", payload)

    def update_milestone(
        self,
        owner: str,
        repo: str,
        number: int,
        *,
        title: str | None = None,
        description: str | None = None,
        due_on: str | None = None,
        state: str | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if due_on is not None:
            payload["due_on"] = due_on
        if state is not None:
            payload["state"] = state
        return self._request("PATCH", f"/repos/{owner}/{repo}/milestones/{number}", payload)

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        data, _headers = self._request_with_headers(method, path, payload)
        return data

    def _request_with_headers(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> tuple[Any, Mapping[str, str]]:
        url = f"{self._base_url}{path}"
        response = self._request_once(method, url, payload)
        wait_seconds = self._handle_rate_limit(response)
        if wait_seconds is not None:
            time.sleep(wait_seconds)
            response = self._request_once(method, url, payload)
        if not response.ok:
            body = self._parse_body(response.content)
            message = "unknown error"
            if isinstance(body, dict) and body.get("message"):
                message = str(body["message"])
            raise GitHubAPIError(
                status_code=response.status_code, message=message, response_body=body
            )
        headers = dict(response.headers)
        return self._parse_body(response.content), headers

    def _request_once(
        self, method: str, url: str, payload: Mapping[str, Any] | None
    ) -> requests.Response:
        return self._session.request(
            method=method,
            url=url,
            json=payload,
            timeout=30,
        )

    def _handle_rate_limit(self, response: requests.Response) -> int | None:
        """Return wait time in seconds when rate limited, otherwise None."""
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining == "0":
                reset_time = response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    wait_seconds = int(reset_time) - int(time.time()) + 1
                    if 0 < wait_seconds <= 60:
                        return wait_seconds
                raise GitHubAPIError(
                    status_code=403,
                    message="Rate limit exceeded. Try again later.",
                    response_body=None,
                )
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            wait_seconds = min(int(retry_after), 60)
            return wait_seconds
        return None

    @staticmethod
    def _parse_body(raw_body: bytes) -> Any:
        if not raw_body:
            return {}
        import json

        return json.loads(raw_body.decode("utf-8"))


def _has_next_link(link_header: str | None) -> bool:
    if not link_header:
        return False
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return True
    return False
