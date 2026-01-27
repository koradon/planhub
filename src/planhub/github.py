from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class GitHubAPIError(RuntimeError):
    status_code: int
    message: str
    response_body: Optional[Mapping[str, Any]] = None

    def __str__(self) -> str:
        return f"GitHub API error {self.status_code}: {self.message}"


class IssueState(Enum):
    OPEN = "open"
    CLOSED = "closed"


class IssueStateReason(Enum):
    COMPLETED = "completed"
    NOT_PLANNED = "not_planned"
    REOPENED = "reopened"


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None,
        milestone: Optional[int] = None,
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
        return self._request("POST", f"/repos/{owner}/{repo}/issues", payload)

    def get_issue(self, owner: str, repo: str, number: int) -> Mapping[str, Any]:
        return self._request("GET", f"/repos/{owner}/{repo}/issues/{number}")

    def update_issue_state(
        self,
        owner: str,
        repo: str,
        number: int,
        state: "IssueState",
        state_reason: Optional["IssueStateReason"] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {"state": state.value}
        if state_reason is not None:
            payload["state_reason"] = state_reason.value
        return self._request("PATCH", f"/repos/{owner}/{repo}/issues/{number}", payload)

    def list_issues(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[Mapping[str, Any]]:
        issues: list[Mapping[str, Any]] = []
        page = 1
        while True:
            path = (
                f"/repos/{owner}/{repo}/issues"
                f"?state={state}&per_page=100&page={page}"
            )
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
        state_reason: Optional["IssueStateReason"] = None,
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
        description: Optional[str] = None,
        due_on: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if description is not None:
            payload["description"] = description
        if due_on is not None:
            payload["due_on"] = due_on
        if state is not None:
            payload["state"] = state
        return self._request("POST", f"/repos/{owner}/{repo}/milestones", payload)

    def _request(
        self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None
    ) -> Any:
        data, _headers = self._request_with_headers(method, path, payload)
        return data

    def _request_with_headers(
        self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None
    ) -> tuple[Any, Mapping[str, str]]:
        url = f"{self._base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "planhub",
            },
        )
        try:
            with urlopen(request) as response:
                raw_body = response.read()
                headers = dict(response.headers.items())
        except HTTPError as error:
            body = self._parse_body(error.read())
            message = "unknown error"
            if isinstance(body, dict) and body.get("message"):
                message = str(body["message"])
            raise GitHubAPIError(
                status_code=error.code, message=message, response_body=body
            ) from error
        return self._parse_body(raw_body), headers

    @staticmethod
    def _parse_body(raw_body: bytes) -> Any:
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))


def _has_next_link(link_header: Optional[str]) -> bool:
    if not link_header:
        return False
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return True
    return False
