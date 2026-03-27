from __future__ import annotations

import os
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


@dataclass(frozen=True)
class SyncConfig:
    closed_issues: SyncClosedIssuesConfig
    github: SyncGithubConfig
    behavior: SyncBehaviorConfig


@dataclass(frozen=True)
class PlanHubConfig:
    sync: SyncConfig


_CLOSED_ISSUES_POLICIES = {"archive", "delete"}


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
            },
        }
    }


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
        },
    }
}


def render_default_config_yaml() -> str:
    """Render default config YAML for users to copy/create."""

    # `sort_keys=False` keeps dict insertion order for stable diffs.
    return yaml.safe_dump(_default_config_data(), sort_keys=False).strip() + "\n"


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_global_config() -> bool:
    """Ensure `~/.planhub/config.yaml` exists (creates defaults if missing)."""

    return _write_if_missing(_global_config_path(), render_default_config_yaml())


def ensure_repo_config(repo_root: Path) -> bool:
    """Ensure `<repo>/.plan/config.yaml` exists (creates defaults if missing)."""

    repo_root = repo_root.resolve()
    path = repo_root / ".plan" / "config.yaml"
    return _write_if_missing(path, render_default_config_yaml())


def load_config(repo_root: Path) -> PlanHubConfig:
    """Load configuration from ~/.planhub/config.yaml and .plan/config.yaml.

    Precedence:
      built-in defaults < global config < repository config
    """

    repo_root = repo_root.resolve()
    merged = _default_config_data()

    global_path = _global_config_path()
    merged = _deep_merge(merged, _load_and_validate_yaml(global_path))

    repo_path = repo_root / ".plan" / "config.yaml"
    merged = _deep_merge(merged, _load_and_validate_yaml(repo_path))

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
            behavior=SyncBehaviorConfig(dry_run=bool(sync_data["behavior"]["dry_run"])),
        )
    )


def _global_config_path() -> Path:
    # Use expanduser so callers/tests can control via HOME.
    config_home = Path(os.path.expanduser("~")) / ".planhub"
    return config_home / "config.yaml"


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
    """

    result: dict[str, Any] = dict(base)
    for key, override_value in override.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = _deep_merge(base_value, override_value)
        else:
            result[key] = override_value
    return result
