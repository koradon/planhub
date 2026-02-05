from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    issue_id: str | None
    number: int | None
    labels: tuple[str, ...]
    labels_set: bool
    milestone: str | None
    milestone_number: int | None
    milestone_set: bool
    assignees: tuple[str, ...]
    assignees_set: bool
    issue_type: str | None
    state: IssueState | None
    state_reason: IssueStateReason | None


@dataclass(frozen=True)
class MilestoneDocument:
    path: Path
    title: str
    description: str | None
    due_on: str | None
    state: IssueState | None
    milestone_id: str | None
    number: int | None
    body: str


def load_issue_document(path: Path) -> IssueDocument:
    metadata, body = _parse_front_matter(path, path.read_text(encoding="utf-8"))
    title = _require_str(metadata, "title", path)
    issue_id = _optional_str(metadata, "id", path)
    number = _optional_int(metadata, "number", path)
    labels = _optional_str_list(metadata, "labels", path)
    labels_set = _has_key(metadata, "labels")
    milestone, milestone_number, milestone_set = _optional_milestone(metadata, path)
    assignees = _optional_str_list(metadata, "assignees", path)
    assignees_set = _has_key(metadata, "assignees")
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
        labels_set=labels_set,
        milestone=milestone,
        milestone_number=milestone_number,
        milestone_set=milestone_set,
        assignees=assignees,
        assignees_set=assignees_set,
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


def update_front_matter(
    path: Path,
    updates: Mapping[str, Any],
    *,
    cached_metadata: Mapping[str, Any] | None = None,
    cached_body: str | None = None,
) -> None:
    """Update front matter in a markdown file.

    Args:
        path: Path to the file to update.
        updates: Dictionary of key-value pairs to update in the front matter.
        cached_metadata: Optional pre-parsed metadata to avoid re-reading the file.
        cached_body: Optional pre-parsed body to avoid re-reading the file.
    """
    if cached_metadata is not None and cached_body is not None:
        metadata = cached_metadata
        body = cached_body
    else:
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


def issue_document_to_metadata(doc: IssueDocument) -> dict[str, Any]:
    """Convert an IssueDocument back to front matter metadata dict."""
    metadata: dict[str, Any] = {"title": doc.title}
    if doc.issue_id is not None:
        metadata["id"] = doc.issue_id
    if doc.number is not None:
        metadata["number"] = doc.number
    if doc.labels_set:
        metadata["labels"] = list(doc.labels)
    if doc.milestone_set:
        if doc.milestone_number is not None:
            metadata["milestone"] = doc.milestone_number
        else:
            metadata["milestone"] = doc.milestone
    if doc.assignees_set:
        metadata["assignees"] = list(doc.assignees)
    if doc.issue_type is not None:
        metadata["type"] = doc.issue_type
    if doc.state is not None:
        metadata["state"] = doc.state.value
    if doc.state_reason is not None:
        metadata["state_reason"] = doc.state_reason.value
    return metadata


def milestone_document_to_metadata(doc: MilestoneDocument) -> dict[str, Any]:
    """Convert a MilestoneDocument back to front matter metadata dict."""
    metadata: dict[str, Any] = {"title": doc.title}
    if doc.milestone_id is not None:
        metadata["id"] = doc.milestone_id
    if doc.number is not None:
        metadata["number"] = doc.number
    if doc.description is not None:
        metadata["description"] = doc.description
    if doc.due_on is not None:
        metadata["due_on"] = doc.due_on
    if doc.state is not None:
        metadata["state"] = doc.state.value
    return metadata


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


def _optional_str(metadata: Mapping[str, Any], key: str, path: Path) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise DocumentError(path, f"Expected '{key}' to be a string.")
    return value


def _optional_int(metadata: Mapping[str, Any], key: str, path: Path) -> int | None:
    value = metadata.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise DocumentError(path, f"Expected '{key}' to be an integer.")


def _optional_str_list(metadata: Mapping[str, Any], key: str, path: Path) -> tuple[str, ...]:
    value = metadata.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DocumentError(path, f"Expected '{key}' to be a list of strings.")
    return tuple(value)


def _optional_milestone(
    metadata: Mapping[str, Any], path: Path
) -> tuple[str | None, int | None, bool]:
    if "milestone" not in metadata:
        return None, None, False
    value = metadata.get("milestone")
    if value is None:
        return None, None, True
    if isinstance(value, int):
        return None, value, True
    if isinstance(value, str):
        return value, None, True
    raise DocumentError(path, "Expected 'milestone' to be a string, int, or null.")


def _has_key(metadata: Mapping[str, Any], key: str) -> bool:
    return key in metadata


def _parse_issue_state(value: Any, path: Path) -> IssueState | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DocumentError(path, "Expected 'state' to be a string.")
    try:
        return IssueState(value)
    except ValueError as exc:
        raise DocumentError(path, f"Unknown state '{value}'.") from exc


def _parse_state_reason(value: Any, path: Path) -> IssueStateReason | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DocumentError(path, "Expected 'state_reason' to be a string.")
    try:
        return IssueStateReason(value)
    except ValueError as exc:
        raise DocumentError(path, f"Unknown state_reason '{value}'.") from exc
