from __future__ import annotations

import pytest

from planhub.config import ConfigError, load_config


def test_load_config_uses_defaults(tmp_path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.sync.closed_issues.policy == "archive"
    assert cfg.sync.closed_issues.archive_dir == tmp_path / ".plan" / "archive" / "issues"


def test_load_config_global_only(tmp_path) -> None:
    global_config_dir = tmp_path / ".planhub"
    global_config_dir.mkdir(parents=True, exist_ok=True)
    (global_config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  closed_issues:",
                "    policy: delete",
                "    archive_dir: custom-archive/issues",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    assert cfg.sync.closed_issues.policy == "delete"
    assert cfg.sync.closed_issues.archive_dir == tmp_path / "custom-archive" / "issues"


def test_load_config_repository_only(tmp_path) -> None:
    repo_plan_dir = tmp_path / ".plan"
    repo_plan_dir.mkdir(parents=True, exist_ok=True)
    (repo_plan_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  closed_issues:",
                "    policy: delete",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    assert cfg.sync.closed_issues.policy == "delete"
    assert cfg.sync.closed_issues.archive_dir == tmp_path / ".plan" / "archive" / "issues"


def test_load_config_repo_overrides_global(tmp_path) -> None:
    global_config_dir = tmp_path / ".planhub"
    global_config_dir.mkdir(parents=True, exist_ok=True)
    (global_config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  closed_issues:",
                "    policy: delete",
                "    archive_dir: global-archive/issues",
            ]
        ),
        encoding="utf-8",
    )

    repo_plan_dir = tmp_path / ".plan"
    repo_plan_dir.mkdir(parents=True, exist_ok=True)
    (repo_plan_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  closed_issues:",
                "    policy: archive",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    assert cfg.sync.closed_issues.policy == "archive"
    # archive_dir came from global because repository config didn't override it.
    assert cfg.sync.closed_issues.archive_dir == tmp_path / "global-archive" / "issues"


def test_load_config_deep_merge_lists_replace(tmp_path) -> None:
    global_config_dir = tmp_path / ".planhub"
    global_config_dir.mkdir(parents=True, exist_ok=True)
    (global_config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  github:",
                "    default_labels: [a]",
            ]
        ),
        encoding="utf-8",
    )

    repo_plan_dir = tmp_path / ".plan"
    repo_plan_dir.mkdir(parents=True, exist_ok=True)
    (repo_plan_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  github:",
                "    default_labels: [b]",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    assert cfg.sync.github.default_labels == ("b",)


def test_load_config_unknown_key_fails_with_location(tmp_path) -> None:
    global_config_dir = tmp_path / ".planhub"
    global_config_dir.mkdir(parents=True, exist_ok=True)
    (global_config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  no_such_section:",
                "    value: 1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path)

    assert "config.yaml" in str(exc.value)
    assert "Unknown config key" in str(exc.value)


def test_load_config_invalid_policy_fails(tmp_path) -> None:
    global_config_dir = tmp_path / ".planhub"
    global_config_dir.mkdir(parents=True, exist_ok=True)
    (global_config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  closed_issues:",
                "    policy: keep",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path)

    assert "closed_issues.policy" in str(exc.value)
