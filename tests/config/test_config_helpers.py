from __future__ import annotations

import pytest
import yaml

from planhub.config import (
    ConfigError,
    _deep_merge,
    _load_and_validate_yaml,
    _nested_from_dotted,
    _split_leading_comments,
    _validate_config_dict,
    _write_if_missing,
    ensure_repo_config,
    read_config_file,
    render_default_config_yaml,
    write_config_values,
    write_repo_config_values,
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


def test_ensure_repo_config_creates_once(tmp_path) -> None:
    created = ensure_repo_config(tmp_path)
    assert created is True
    cfg = tmp_path / ".plan" / "config.yaml"
    assert cfg.exists()

    created_again = ensure_repo_config(tmp_path)
    assert created_again is False
    assert cfg.exists()


def test_ensure_repo_config_writes_a_comment_only_stub(tmp_path) -> None:
    ensure_repo_config(tmp_path)

    cfg = tmp_path / ".plan" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    assert all(line.strip() == "" or line.strip().startswith("#") for line in text.splitlines())
    assert yaml.safe_load(text) is None


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


def test_read_config_file_returns_empty_dict_when_absent(tmp_path) -> None:
    assert read_config_file(tmp_path / "missing.yaml") == {}


def test_nested_from_dotted_expands_dotted_paths(tmp_path) -> None:
    nested = _nested_from_dotted(
        {"sync.github.default_labels": ["bug"], "sync.behavior.verbosity": "verbose"},
        path=tmp_path / "config.yaml",
    )
    assert nested == {
        "sync": {"github": {"default_labels": ["bug"]}, "behavior": {"verbosity": "verbose"}}
    }


def test_nested_from_dotted_raises_on_prefix_collision(tmp_path) -> None:
    with pytest.raises(ConfigError):
        _nested_from_dotted(
            {"sync.github": "oops", "sync.github.default_labels": ["bug"]},
            path=tmp_path / "config.yaml",
        )


def test_split_leading_comments_separates_header_from_body() -> None:
    text = "# a comment\n\nsync:\n  behavior:\n    verbosity: verbose\n"
    header, remainder = _split_leading_comments(text)
    assert header == "# a comment\n\n"
    assert remainder == "sync:\n  behavior:\n    verbosity: verbose\n"


def test_split_leading_comments_with_no_comments_returns_empty_header() -> None:
    text = "sync:\n  behavior:\n    verbosity: verbose\n"
    header, remainder = _split_leading_comments(text)
    assert header == ""
    assert remainder == text


def test_write_config_values_creates_file_with_only_given_keys(tmp_path) -> None:
    path = tmp_path / "config.yaml"

    written = write_config_values(path, {"sync.github.default_labels": ["bug"]})

    assert written is True
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data == {"sync": {"github": {"default_labels": ["bug"]}}}


def test_write_config_values_preserves_unrelated_keys(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "sync:\n  closed_issues:\n    archive_dir: custom/dir\n  behavior:\n    dry_run: true\n",
        encoding="utf-8",
    )

    write_config_values(path, {"sync.github.default_labels": ["bug"]})

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["sync"]["closed_issues"]["archive_dir"] == "custom/dir"
    assert data["sync"]["behavior"]["dry_run"] is True
    assert data["sync"]["github"]["default_labels"] == ["bug"]


def test_write_config_values_preserves_existing_key_order(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "sync:\n  closed_issues:\n    policy: archive\n  github:\n    default_labels: []\n",
        encoding="utf-8",
    )

    write_config_values(path, {"sync.behavior.verbosity": "verbose"})

    text = path.read_text(encoding="utf-8")
    assert text.index("closed_issues") < text.index("github") < text.index("behavior")


def test_write_config_values_returns_false_when_nothing_changes(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    write_config_values(path, {"sync.github.default_labels": ["bug"]})
    before = path.read_text(encoding="utf-8")

    written_again = write_config_values(path, {"sync.github.default_labels": ["bug"]})

    assert written_again is False
    assert path.read_text(encoding="utf-8") == before


def test_write_config_values_with_empty_updates_does_not_create_file(tmp_path) -> None:
    path = tmp_path / "config.yaml"

    written = write_config_values(path, {})

    assert written is False
    assert not path.exists()


def test_write_config_values_rejects_invalid_enum_without_writing(tmp_path) -> None:
    path = tmp_path / "config.yaml"

    with pytest.raises(ConfigError) as exc:
        write_config_values(path, {"sync.closed_issues.policy": "nope"})

    assert "sync.closed_issues.policy" in str(exc.value)
    assert not path.exists()


def test_write_config_values_rejects_unknown_dotted_path(tmp_path) -> None:
    path = tmp_path / "config.yaml"

    with pytest.raises(ConfigError):
        write_config_values(path, {"sync.no_such_key": "value"})

    assert not path.exists()


def test_write_config_values_refuses_when_existing_file_is_invalid(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("sync:\n  no_such_section:\n    value: 1\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        write_config_values(path, {"sync.behavior.verbosity": "verbose"})


def test_write_config_values_preserves_leading_comments(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("# a header comment\n\n", encoding="utf-8")

    write_config_values(path, {"sync.behavior.verbosity": "verbose"})

    text = path.read_text(encoding="utf-8")
    assert text.startswith("# a header comment\n\n")


def test_write_config_values_warns_when_comments_are_stripped(tmp_path, capsys) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "sync:\n  behavior:\n    # inline note, not preserved\n    dry_run: false\n",
        encoding="utf-8",
    )

    write_config_values(path, {"sync.behavior.verbosity": "verbose"})

    assert f"Comments in {path} were not preserved" in capsys.readouterr().err


def test_write_repo_config_values_targets_plan_config(tmp_path) -> None:
    written = write_repo_config_values(tmp_path, {"sync.behavior.verbosity": "verbose"})

    assert written is True
    data = yaml.safe_load((tmp_path / ".plan" / "config.yaml").read_text(encoding="utf-8"))
    assert data == {"sync": {"behavior": {"verbosity": "verbose"}}}
