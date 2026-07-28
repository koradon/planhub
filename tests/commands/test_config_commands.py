from __future__ import annotations

from unittest.mock import patch

from planhub.cli.commands.init import init_command
from planhub.cli.config_prompts import ConfigPromptOutcome
from planhub.config import ConfigError


def _no_op_outcome(
    target_path, *, skip_reason: str | None = "accepted-defaults"
) -> ConfigPromptOutcome:
    return ConfigPromptOutcome(
        target_path=target_path, answers={}, updates={}, prompted=False, skip_reason=skip_reason
    )


@patch("planhub.cli.commands.init.typer.echo")
def test_init_command_dry_run_prints_config_path_and_questions(
    mock_echo, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=True)

    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert str(tmp_path / ".plan" / "config.yaml") in printed
    assert "Default GitHub assignees" in printed
    assert "Sync output verbosity" in printed


@patch("planhub.cli.commands.init.typer.echo")
@patch("planhub.cli.commands.init.write_repo_config_values")
@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.ensure_repo_config")
def test_init_command_non_dry_run_calls_config_initializers(
    mock_ensure_repo, mock_run_prompts, mock_write, mock_echo, tmp_path, monkeypatch
) -> None:
    mock_ensure_repo.return_value = False
    mock_run_prompts.return_value = _no_op_outcome(tmp_path / ".plan" / "config.yaml")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False, accept_defaults=True)

    mock_ensure_repo.assert_called_once_with(tmp_path)
    mock_write.assert_not_called()
    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert "Plan layout ready" in printed
    assert "Repository config: already exists" in printed


@patch("planhub.cli.commands.init.write_repo_config_values")
@patch("planhub.cli.commands.init.run_config_prompts")
def test_init_command_writes_repo_config_from_answers(
    mock_run_prompts, mock_write, tmp_path, monkeypatch
) -> None:
    config_path = tmp_path / ".plan" / "config.yaml"
    mock_run_prompts.return_value = ConfigPromptOutcome(
        target_path=config_path,
        answers={"sync.behavior.verbosity": "verbose"},
        updates={"sync.behavior.verbosity": "verbose"},
        prompted=True,
        skip_reason=None,
    )
    mock_write.return_value = True
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False, accept_defaults=True)

    mock_write.assert_called_once_with(tmp_path, {"sync.behavior.verbosity": "verbose"})


@patch("planhub.cli.commands.init.typer.echo")
@patch("planhub.cli.commands.init.write_repo_config_values")
@patch("planhub.cli.commands.init.run_config_prompts")
def test_init_command_reports_unchanged_when_writer_returns_false(
    mock_run_prompts, mock_write, mock_echo, tmp_path, monkeypatch
) -> None:
    mock_run_prompts.return_value = _no_op_outcome(tmp_path / ".plan" / "config.yaml")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False, accept_defaults=True)

    mock_write.assert_not_called()
    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert "Repository config unchanged." in printed


@patch("planhub.cli.commands.init.typer.echo")
@patch("planhub.cli.commands.init.run_config_prompts")
def test_init_command_pre_existing_invalid_config_is_skipped_with_warning(
    mock_run_prompts, mock_echo, tmp_path, monkeypatch
) -> None:
    mock_run_prompts.side_effect = ConfigError(tmp_path / ".plan" / "config.yaml", "bad config")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False, accept_defaults=True)

    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert "Skipped config prompts" in printed
    assert "Plan layout ready" in printed


@patch("planhub.cli.commands.init.run_config_prompts")
def test_init_command_yes_flag_skips_prompts(mock_run_prompts, tmp_path, monkeypatch) -> None:
    mock_run_prompts.return_value = _no_op_outcome(tmp_path / ".plan" / "config.yaml")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False, accept_defaults=True)

    mock_run_prompts.assert_called_once_with(
        target_path=tmp_path / ".plan" / "config.yaml",
        interactive=False,
        skip_reason="accepted-defaults",
    )


@patch("planhub.cli.commands.init.sys.stdin")
@patch("planhub.cli.commands.init.run_config_prompts")
def test_init_command_non_tty_skips_prompts(
    mock_run_prompts, mock_stdin, tmp_path, monkeypatch
) -> None:
    mock_stdin.isatty.return_value = False
    mock_run_prompts.return_value = _no_op_outcome(
        tmp_path / ".plan" / "config.yaml", skip_reason="non-interactive"
    )
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False)

    mock_run_prompts.assert_called_once_with(
        target_path=tmp_path / ".plan" / "config.yaml", interactive=False, skip_reason=None
    )


@patch("planhub.cli.commands.init.typer.echo")
def test_init_command_dry_run_lists_skill_paths(mock_echo, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=True)

    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert str(tmp_path / ".claude" / "skills" / "planhub-plan-artifacts" / "SKILL.md") in printed
    assert str(tmp_path / ".cursor" / "skills" / "planhub-plan-artifacts" / "SKILL.md") in printed


@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.typer.confirm")
@patch("planhub.cli.commands.init.install_skills")
def test_init_command_skills_flag_installs_without_prompting(
    mock_install, mock_confirm, mock_run_prompts, tmp_path, monkeypatch
) -> None:
    from planhub.skills import SkillInstallResult

    mock_install.return_value = SkillInstallResult(created=(), updated=(), unchanged=())
    mock_run_prompts.return_value = _no_op_outcome(tmp_path / ".plan" / "config.yaml")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=True)

    mock_install.assert_called_once_with(tmp_path)
    mock_confirm.assert_not_called()


@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.typer.confirm")
@patch("planhub.cli.commands.init.install_skills")
def test_init_command_no_skills_flag_skips_without_prompting(
    mock_install, mock_confirm, mock_run_prompts, tmp_path, monkeypatch
) -> None:
    mock_run_prompts.return_value = _no_op_outcome(tmp_path / ".plan" / "config.yaml")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False)

    mock_install.assert_not_called()
    mock_confirm.assert_not_called()


@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.sys.stdin")
@patch("planhub.cli.commands.init.typer.confirm")
@patch("planhub.cli.commands.init.install_skills")
def test_init_command_omitted_flag_non_tty_skips_without_prompting(
    mock_install, mock_confirm, mock_stdin, mock_run_prompts, tmp_path, monkeypatch
) -> None:
    mock_stdin.isatty.return_value = False
    mock_run_prompts.return_value = _no_op_outcome(
        tmp_path / ".plan" / "config.yaml", skip_reason="non-interactive"
    )
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=None)

    mock_install.assert_not_called()
    mock_confirm.assert_not_called()


@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.sys.stdin")
@patch("planhub.cli.commands.init.typer.confirm")
@patch("planhub.cli.commands.init.install_skills")
def test_init_command_omitted_flag_tty_confirmed_installs(
    mock_install, mock_confirm, mock_stdin, mock_run_prompts, tmp_path, monkeypatch
) -> None:
    from planhub.skills import SkillInstallResult

    mock_stdin.isatty.return_value = True
    mock_confirm.return_value = True
    mock_install.return_value = SkillInstallResult(created=(), updated=(), unchanged=())
    mock_run_prompts.return_value = _no_op_outcome(
        tmp_path / ".plan" / "config.yaml", skip_reason=None
    )
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=None)

    mock_confirm.assert_called_once()
    mock_install.assert_called_once_with(tmp_path)


@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.sys.stdin")
@patch("planhub.cli.commands.init.typer.confirm")
@patch("planhub.cli.commands.init.install_skills")
def test_init_command_omitted_flag_tty_declined_skips(
    mock_install, mock_confirm, mock_stdin, mock_run_prompts, tmp_path, monkeypatch
) -> None:
    mock_stdin.isatty.return_value = True
    mock_confirm.return_value = False
    mock_run_prompts.return_value = _no_op_outcome(
        tmp_path / ".plan" / "config.yaml", skip_reason=None
    )
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=None)

    mock_confirm.assert_called_once()
    mock_install.assert_not_called()


@patch("planhub.cli.commands.init.run_config_prompts")
@patch("planhub.cli.commands.init.install_skills")
def test_init_command_yes_flag_installs_skills_without_prompting(
    mock_install, mock_run_prompts, tmp_path, monkeypatch
) -> None:
    from planhub.skills import SkillInstallResult

    mock_install.return_value = SkillInstallResult(created=(), updated=(), unchanged=())
    mock_run_prompts.return_value = _no_op_outcome(tmp_path / ".plan" / "config.yaml")
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=None, accept_defaults=True)

    mock_install.assert_called_once_with(tmp_path)


@patch("planhub.cli.commands.init.sys.stdin")
@patch("planhub.cli.config_prompts.typer.prompt")
def test_init_command_interactive_writes_answers_to_repo_config(
    mock_prompt, mock_stdin, tmp_path, monkeypatch
) -> None:
    import yaml

    mock_stdin.isatty.return_value = True
    mock_prompt.side_effect = ["alice", "bug", "delete", "verbose"]
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False, skills=False)

    data = yaml.safe_load((tmp_path / ".plan" / "config.yaml").read_text(encoding="utf-8"))
    assert data["sync"]["github"]["default_assignees"] == ["alice"]
    assert data["sync"]["github"]["default_labels"] == ["bug"]
    assert data["sync"]["closed_issues"]["policy"] == "delete"
    assert data["sync"]["behavior"]["verbosity"] == "verbose"
