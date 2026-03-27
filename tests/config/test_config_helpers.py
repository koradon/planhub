from __future__ import annotations

import pytest
import yaml

from planhub.config import (
    ConfigError,
    _deep_merge,
    _load_and_validate_yaml,
    _validate_config_dict,
    _write_if_missing,
    ensure_global_config,
    ensure_repo_config,
    render_default_config_yaml,
)


def test_render_default_config_yaml_has_expected_structure() -> None:
    rendered = render_default_config_yaml()
    data = yaml.safe_load(rendered)
    assert isinstance(data, dict)
    assert data["sync"]["closed_issues"]["policy"] == "archive"
    assert data["sync"]["closed_issues"]["archive_dir"] == ".plan/archive/issues"
    assert data["sync"]["behavior"]["verbosity"] == "compact"


def test_write_if_missing_creates_file_then_skips_overwrite(tmp_path) -> None:
    path = tmp_path / "a" / "config.yaml"
    created = _write_if_missing(path, "first")
    assert created is True
    assert path.read_text(encoding="utf-8") == "first"

    created = _write_if_missing(path, "second")
    assert created is False
    assert path.read_text(encoding="utf-8") == "first"


def test_ensure_global_config_creates_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    created = ensure_global_config()
    assert created is True
    cfg = tmp_path / ".planhub" / "config.yaml"
    assert cfg.exists()

    created_again = ensure_global_config()
    assert created_again is False
    assert cfg.exists()


def test_ensure_repo_config_creates_once(tmp_path) -> None:
    created = ensure_repo_config(tmp_path)
    assert created is True
    cfg = tmp_path / ".plan" / "config.yaml"
    assert cfg.exists()

    created_again = ensure_repo_config(tmp_path)
    assert created_again is False
    assert cfg.exists()


def test_load_and_validate_yaml_non_mapping_top_level_raises(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        _load_and_validate_yaml(path)


def test_load_and_validate_yaml_empty_file_returns_empty_dict(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("", encoding="utf-8")
    assert _load_and_validate_yaml(path) == {}


def test_validate_config_dict_expected_mapping_raises(tmp_path) -> None:
    schema = {"sync": {"closed_issues": {"policy": ("enum", {"archive", "delete"})}}}
    with pytest.raises(ConfigError) as exc:
        _validate_config_dict({"sync": True}, schema, tmp_path / "config.yaml")
    assert "Expected 'sync' to be a mapping." in str(exc.value)


def test_deep_merge_merges_dicts_and_replaces_scalars_and_lists() -> None:
    base = {"a": {"x": 1, "list": [1], "k": "base"}, "b": 1}
    override = {"a": {"y": 2, "list": [2]}, "b": 3}
    merged = _deep_merge(base, override)
    assert merged == {"a": {"x": 1, "y": 2, "list": [2], "k": "base"}, "b": 3}
