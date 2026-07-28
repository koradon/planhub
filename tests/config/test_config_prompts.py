from __future__ import annotations

from unittest.mock import patch

from planhub.cli.config_prompts import (
    config_updates_from_answers,
    describe_prompts_dry_run,
    parse_csv_list,
    run_config_prompts,
)


def test_parse_csv_list_trims_and_drops_empty_entries() -> None:
    result = parse_csv_list(" a , , b ")

    assert result == ["a", "b"]


def test_parse_csv_list_returns_empty_list_for_blank_input() -> None:
    assert parse_csv_list("") == []


def test_parse_csv_list_dedupes_preserving_order() -> None:
    result = parse_csv_list("bug, chore, bug")

    assert result == ["bug", "chore"]


@patch("planhub.cli.config_prompts.typer.prompt")
def test_run_config_prompts_non_interactive_returns_current_values_without_prompting(
    mock_prompt, tmp_path
) -> None:
    target = tmp_path / "config.yaml"

    outcome = run_config_prompts(target_path=target, interactive=False)

    mock_prompt.assert_not_called()
    assert outcome.prompted is False
    assert outcome.skip_reason == "non-interactive"
    assert outcome.answers["sync.behavior.verbosity"] == "compact"


@patch("planhub.cli.config_prompts.typer.prompt")
def test_run_config_prompts_uses_accepted_defaults_skip_reason(mock_prompt, tmp_path) -> None:
    target = tmp_path / "config.yaml"

    outcome = run_config_prompts(
        target_path=target, interactive=False, skip_reason="accepted-defaults"
    )

    assert outcome.skip_reason == "accepted-defaults"


@patch("planhub.cli.config_prompts.typer.prompt")
def test_run_config_prompts_shows_existing_file_values_as_defaults(mock_prompt, tmp_path) -> None:
    target = tmp_path / "config.yaml"
    target.write_text("sync:\n  github:\n    default_labels: [bug]\n", encoding="utf-8")
    mock_prompt.side_effect = ["", "bug", "archive", "compact"]

    outcome = run_config_prompts(target_path=target, interactive=True)

    labels_call = mock_prompt.call_args_list[1]
    assert labels_call.kwargs["default"] == "bug"
    assert outcome.answers["sync.github.default_labels"] == ["bug"]


@patch("planhub.cli.config_prompts.typer.prompt")
def test_run_config_prompts_reasks_until_enum_answer_is_valid(mock_prompt, tmp_path) -> None:
    target = tmp_path / "config.yaml"
    mock_prompt.side_effect = ["", "", "bogus", "delete", "compact"]

    with patch("planhub.cli.config_prompts.typer.echo") as mock_echo:
        outcome = run_config_prompts(target_path=target, interactive=True)

    assert outcome.answers["sync.closed_issues.policy"] == "delete"
    assert any("choose one of" in call.args[0] for call in mock_echo.call_args_list)


def test_config_updates_include_keys_already_present_in_file() -> None:
    file_data = {"sync": {"behavior": {"verbosity": "compact"}}}
    answers = {
        "sync.github.default_assignees": [],
        "sync.github.default_labels": [],
        "sync.closed_issues.policy": "archive",
        "sync.behavior.verbosity": "compact",
    }

    updates = config_updates_from_answers(answers, file_data=file_data)

    assert updates == {"sync.behavior.verbosity": "compact"}


def test_config_updates_omit_keys_equal_to_built_in_default_when_unset() -> None:
    answers = {
        "sync.github.default_assignees": [],
        "sync.github.default_labels": [],
        "sync.closed_issues.policy": "archive",
        "sync.behavior.verbosity": "compact",
    }

    updates = config_updates_from_answers(answers, file_data={})

    assert updates == {}


def test_config_updates_include_answers_that_differ_from_built_in_default() -> None:
    answers = {
        "sync.github.default_assignees": [],
        "sync.github.default_labels": ["bug"],
        "sync.closed_issues.policy": "archive",
        "sync.behavior.verbosity": "compact",
    }

    updates = config_updates_from_answers(answers, file_data={})

    assert updates == {"sync.github.default_labels": ["bug"]}


def test_describe_prompts_dry_run_lists_all_questions_with_current_defaults(tmp_path) -> None:
    target = tmp_path / "config.yaml"
    target.write_text("sync:\n  behavior:\n    verbosity: verbose\n", encoding="utf-8")

    lines = describe_prompts_dry_run(target_path=target)

    assert len(lines) == 4
    assert any("verbose" in line for line in lines)
