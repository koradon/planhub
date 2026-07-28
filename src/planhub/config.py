from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when configuration is missing required structure or contains unknown keys."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


@dataclass(frozen=True)
class SyncClosedIssuesConfig:
    policy: str  # "archive" | "delete"
    archive_dir: Path  # resolved relative to repo root


@dataclass(frozen=True)
class SyncGithubConfig:
    default_assignees: tuple[str, ...]
    default_labels: tuple[str, ...]


@dataclass(frozen=True)
class SyncBehaviorConfig:
    dry_run: bool
    verbosity: str  # "compact" | "verbose"


@dataclass(frozen=True)
class SyncConfig:
    closed_issues: SyncClosedIssuesConfig
    github: SyncGithubConfig
    behavior: SyncBehaviorConfig


@dataclass(frozen=True)
class PlanHubConfig:
    sync: SyncConfig


_CLOSED_ISSUES_POLICIES = {"archive", "delete"}
_SYNC_VERBOSITY_LEVELS = {"compact", "verbose"}


def _default_config_data() -> dict[str, Any]:
    return {
        "sync": {
            "closed_issues": {
                "policy": "archive",
                "archive_dir": ".plan/archive/issues",
            },
            "github": {
                "default_assignees": [],
                "default_labels": [],
            },
            "behavior": {
                "dry_run": False,
                "verbosity": "compact",
            },
        }
    }


def default_config_data() -> dict[str, Any]:
    """Public alias for the built-in defaults layer."""

    return _default_config_data()


_CONFIG_SCHEMA: Mapping[str, Any] = {
    "sync": {
        "closed_issues": {
            "policy": ("enum", _CLOSED_ISSUES_POLICIES),
            "archive_dir": ("str", None),
        },
        "github": {
            "default_assignees": ("list_str", None),
            "default_labels": ("list_str", None),
        },
        "behavior": {
            "dry_run": ("bool", None),
            "verbosity": ("enum", _SYNC_VERBOSITY_LEVELS),
        },
    }
}


def _dump_config_yaml(data: Mapping[str, Any]) -> str:
    # `sort_keys=False` keeps dict insertion order for stable diffs;
    # `allow_unicode=True` keeps non-ASCII assignees/labels readable.
    return yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True).strip() + "\n"


def render_default_config_yaml() -> str:
    """Render default config YAML for users to copy/create."""

    return _dump_config_yaml(_default_config_data())


_REPO_CONFIG_STUB = """\
# Planhub configuration for this repository.
# Only keys set here differ from planhub's built-in defaults.
# Run `planhub init` to set them interactively.
"""


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_repo_config(repo_root: Path) -> bool:
    """Ensure `<repo>/.plan/config.yaml` exists (creates a minimal stub if missing).

    The stub sets no keys, so built-in defaults apply until the project
    deliberately overrides one.
    """

    repo_root = repo_root.resolve()
    path = repo_root / ".plan" / "config.yaml"
    return _write_if_missing(path, _REPO_CONFIG_STUB)


def read_config_file(path: Path) -> dict[str, Any]:
    """Validated raw contents of one config file ({} when absent/empty)."""

    return _load_and_validate_yaml(path)


def load_config(repo_root: Path) -> PlanHubConfig:
    """Load configuration from built-in defaults and `.plan/config.yaml`.

    Precedence: built-in defaults < repository config.
    """

    repo_root = repo_root.resolve()
    repo_path = repo_root / ".plan" / "config.yaml"
    merged = _deep_merge(_default_config_data(), read_config_file(repo_path))

    # Convert the validated dict into a typed config object.
    sync_data = merged["sync"]
    closed_issues_data = sync_data["closed_issues"]
    archive_dir_value = Path(closed_issues_data["archive_dir"])
    if not archive_dir_value.is_absolute():
        archive_dir_value = repo_root / archive_dir_value

    return PlanHubConfig(
        sync=SyncConfig(
            closed_issues=SyncClosedIssuesConfig(
                policy=str(closed_issues_data["policy"]),
                archive_dir=archive_dir_value,
            ),
            github=SyncGithubConfig(
                default_assignees=tuple(sync_data["github"]["default_assignees"]),
                default_labels=tuple(sync_data["github"]["default_labels"]),
            ),
            behavior=SyncBehaviorConfig(
                dry_run=bool(sync_data["behavior"]["dry_run"]),
                verbosity=str(sync_data["behavior"]["verbosity"]),
            ),
        )
    )


def _load_and_validate_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}

    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(path, "Top-level YAML value must be a mapping.")

    _validate_config_dict(data, _CONFIG_SCHEMA, path)
    return data


def _validate_config_dict(
    data: Mapping[str, Any],
    schema: Mapping[str, Any],
    file_path: Path,
    *,
    dot_path_prefix: str = "",
) -> None:
    for key, value in data.items():
        if key not in schema:
            dotted = f"{dot_path_prefix}.{key}" if dot_path_prefix else str(key)
            raise ConfigError(file_path, f"Unknown config key '{dotted}'.")

        expected = schema[key]
        dotted = f"{dot_path_prefix}.{key}" if dot_path_prefix else str(key)

        if isinstance(expected, Mapping):
            if not isinstance(value, Mapping):
                raise ConfigError(file_path, f"Expected '{dotted}' to be a mapping.")
            _validate_config_dict(value, expected, file_path, dot_path_prefix=dotted)
            continue

        # Leaf type descriptors:
        expected_kind = expected[0]
        if expected_kind == "enum":
            allowed = expected[1]
            if not isinstance(value, str) or value not in allowed:
                raise ConfigError(
                    file_path,
                    f"Expected '{dotted}' to be one of {sorted(allowed)}.",
                )
            continue

        if expected_kind == "str":
            if not isinstance(value, str):
                raise ConfigError(file_path, f"Expected '{dotted}' to be a string.")
            continue

        if expected_kind == "bool":
            if not isinstance(value, bool):
                raise ConfigError(file_path, f"Expected '{dotted}' to be a boolean.")
            continue

        if expected_kind == "list_str":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ConfigError(file_path, f"Expected '{dotted}' to be a list of strings.")
            continue

        raise ConfigError(file_path, f"Internal error: unknown schema kind for '{dotted}'.")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge dicts where:
    - mappings are merged recursively
    - scalars and lists are replaced

    Note: values copied from `base`/`override` are shared by reference in the
    result, not deep-copied. Safe as long as callers treat merge results as
    read-only, since nothing here mutates a merged value after the fact.
    """

    result: dict[str, Any] = dict(base)
    for key, override_value in override.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = _deep_merge(base_value, override_value)
        else:
            result[key] = override_value
    return result


def _nested_from_dotted(updates: Mapping[str, Any], *, path: Path) -> dict[str, Any]:
    """Expand `{"a.b.c": 1}`-style dotted keys into a nested dict.

    Raises ConfigError (not TypeError) when a dotted path tries to descend
    through a key that another update already set to a scalar, e.g. both
    "sync.github" and "sync.github.default_labels" in the same call.
    """

    nested: dict[str, Any] = {}
    for dotted_key, value in updates.items():
        parts = dotted_key.split(".")
        cursor = nested
        for part in parts[:-1]:
            existing = cursor.get(part)
            if existing is None:
                existing = {}
                cursor[part] = existing
            if not isinstance(existing, dict):
                raise ConfigError(
                    path, f"Conflicting update for '{dotted_key}': '{part}' is not a mapping."
                )
            cursor = existing
        cursor[parts[-1]] = value
    return nested


def _split_leading_comments(text: str) -> tuple[str, str]:
    """Split `text` into its leading `#`-comment/blank-line block and the rest."""

    lines = text.splitlines(keepends=True)
    split_index = 0
    for line in lines:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            split_index += 1
            continue
        break
    return "".join(lines[:split_index]), "".join(lines[split_index:])


def write_config_values(path: Path, updates: Mapping[str, Any]) -> bool:
    """Merge dotted-path `updates` into the YAML config at `path`.

    Reads the file's existing contents (validated), merges the update onto
    them (never onto built-in defaults, so unrelated keys and the file's own
    values are preserved), validates the merged result, and writes it back.

    Returns True when the file was written, False when nothing changed (the
    merged result equals what's already on disk; an absent file is not
    created just to write nothing new into it).

    Raises ConfigError (naming `path` + the offending dotted path) without
    writing when the existing file, the update, or the merged result is
    invalid.
    """

    existing = _load_and_validate_yaml(path)

    overlay = _nested_from_dotted(updates, path=path)
    _validate_config_dict(overlay, _CONFIG_SCHEMA, path)

    merged = _deep_merge(existing, overlay)
    _validate_config_dict(merged, _CONFIG_SCHEMA, path)

    if merged == existing:
        return False

    header = ""
    if path.exists():
        current_text = path.read_text(encoding="utf-8")
        header, remainder = _split_leading_comments(current_text)
        if "#" in remainder:
            print(f"⚠️ Comments in {path} were not preserved by this update.", file=sys.stderr)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + _dump_config_yaml(merged), encoding="utf-8")
    return True


def write_repo_config_values(repo_root: Path, updates: Mapping[str, Any]) -> bool:
    """Merge-safe write of `updates` into `<repo_root>/.plan/config.yaml`."""

    repo_root = repo_root.resolve()
    path = repo_root / ".plan" / "config.yaml"
    return write_config_values(path, updates)
