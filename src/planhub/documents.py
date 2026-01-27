from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

from planhub.github import IssueState, IssueStateReason


class DocumentError(ValueError):
    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


@dataclass(frozen=True)
class IssueDocument:
    path: Path
    title: str
    body: str
    issue_id: Optional[str]
    number: Optional[int]
    labels: tuple[str, ...]
    milestone: Optional[str]
    assignees: tuple[str, ...]
    issue_type: Optional[str]
    state: Optional[IssueState]
    state_reason: Optional[IssueStateReason]


@dataclass(frozen=True)
class MilestoneDocument:
    path: Path
    title: str
    description: Optional[str]
    due_on: Optional[str]
    state: Optional[IssueState]
    milestone_id: Optional[str]
    number: Optional[int]
    body: str


def load_issue_document(path: Path) -> IssueDocument:
    metadata, body = _parse_front_matter(path, path.read_text(encoding="utf-8"))
    title = _require_str(metadata, "title", path)
    issue_id = _optional_str(metadata, "id", path)
    number = _optional_int(metadata, "number", path)
    labels = _optional_str_list(metadata, "labels", path)
    milestone = _optional_str(metadata, "milestone", path)
    assignees = _optional_str_list(metadata, "assignees", path)
    issue_type = _optional_str(metadata, "type", path)
    state = _parse_issue_state(metadata.get("state"), path)
    state_reason = _parse_state_reason(metadata.get("state_reason"), path)
    return IssueDocument(
        path=path,
        title=title,
        body=body,
        issue_id=issue_id,
        number=number,
        labels=labels,
        milestone=milestone,
        assignees=assignees,
        issue_type=issue_type,
        state=state,
        state_reason=state_reason,
    )


def load_milestone_document(path: Path) -> MilestoneDocument:
    metadata, body = _parse_front_matter(path, path.read_text(encoding="utf-8"))
    title = _require_str(metadata, "title", path)
    milestone_id = _optional_str(metadata, "id", path)
    number = _optional_int(metadata, "number", path)
    description = _optional_str(metadata, "description", path) or body or None
    due_on = _optional_str(metadata, "due_on", path)
    state = _parse_issue_state(metadata.get("state"), path)
    return MilestoneDocument(
        path=path,
        title=title,
        description=description,
        due_on=due_on,
        state=state,
        milestone_id=milestone_id,
        number=number,
        body=body,
    )


def update_front_matter(path: Path, updates: Mapping[str, Any]) -> None:
    metadata, body = _parse_front_matter(path, path.read_text(encoding="utf-8"))
    merged = dict(metadata)
    merged.update(updates)
    path.write_text(render_markdown(merged, body), encoding="utf-8")


def render_markdown(front_matter: Mapping[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(front_matter, sort_keys=False).strip()
    sections = ["---", yaml_text, "---", ""]
    if body:
        sections.append(body)
    return "\n".join(sections) + "\n"


def _parse_front_matter(path: Path, text: str) -> tuple[Mapping[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise DocumentError(path, "Missing closing front matter delimiter '---'.")
    yaml_text = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    if body.startswith("\n"):
        body = body[1:]
    metadata = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise DocumentError(path, "Front matter must be a mapping.")
    return metadata, body


def _require_str(metadata: Mapping[str, Any], key: str, path: Path) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DocumentError(path, f"Missing or invalid '{key}'.")
    return value


def _optional_str(metadata: Mapping[str, Any], key: str, path: Path) -> Optional[str]:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise DocumentError(path, f"Expected '{key}' to be a string.")
    return value


def _optional_int(metadata: Mapping[str, Any], key: str, path: Path) -> Optional[int]:
    value = metadata.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise DocumentError(path, f"Expected '{key}' to be an integer.")


def _optional_str_list(
    metadata: Mapping[str, Any], key: str, path: Path
) -> tuple[str, ...]:
    value = metadata.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DocumentError(path, f"Expected '{key}' to be a list of strings.")
    return tuple(value)


def _parse_issue_state(value: Any, path: Path) -> Optional[IssueState]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DocumentError(path, "Expected 'state' to be a string.")
    try:
        return IssueState(value)
    except ValueError as exc:
        raise DocumentError(path, f"Unknown state '{value}'.") from exc


def _parse_state_reason(value: Any, path: Path) -> Optional[IssueStateReason]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DocumentError(path, "Expected 'state_reason' to be a string.")
    try:
        return IssueStateReason(value)
    except ValueError as exc:
        raise DocumentError(path, f"Unknown state_reason '{value}'.") from exc
