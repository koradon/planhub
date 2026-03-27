from __future__ import annotations

from unittest.mock import patch

from planhub.cli.commands.init import init_command
from planhub.cli.commands.setup import setup_command


@patch("planhub.cli.commands.init.typer.echo")
@patch("planhub.cli.commands.init._global_config_path")
def test_init_command_dry_run_prints_config_paths(
    mock_global_path, mock_echo, tmp_path, monkeypatch
) -> None:
    mock_global_path.return_value = tmp_path / ".planhub" / "config.yaml"
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=True)

    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert str(tmp_path / ".planhub" / "config.yaml") in printed
    assert str(tmp_path / ".plan" / "config.yaml") in printed


@patch("planhub.cli.commands.init.typer.echo")
@patch("planhub.cli.commands.init.ensure_repo_config")
@patch("planhub.cli.commands.init.ensure_global_config")
@patch("planhub.cli.commands.init._global_config_path")
def test_init_command_non_dry_run_calls_config_initializers(
    mock_global_path, mock_ensure_global, mock_ensure_repo, mock_echo, tmp_path, monkeypatch
) -> None:
    mock_global_path.return_value = tmp_path / ".planhub" / "config.yaml"
    mock_ensure_global.return_value = True
    mock_ensure_repo.return_value = False
    monkeypatch.chdir(tmp_path)

    init_command(dry_run=False)

    mock_ensure_global.assert_called_once_with()
    mock_ensure_repo.assert_called_once_with(tmp_path)
    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert "Plan layout ready" in printed
    assert "Global config: created" in printed
    assert "Repository config: already exists" in printed


@patch("planhub.cli.commands.setup.typer.echo")
@patch("planhub.cli.commands.setup.global_config_path")
def test_setup_command_dry_run_prints_target_path(mock_global_path, mock_echo, tmp_path) -> None:
    mock_global_path.return_value = tmp_path / ".planhub" / "config.yaml"

    setup_command(dry_run=True)

    printed = "\n".join(call.args[0] for call in mock_echo.call_args_list)
    assert str(tmp_path / ".planhub" / "config.yaml") in printed


@patch("planhub.cli.commands.setup.typer.echo")
@patch("planhub.cli.commands.setup.global_config_path")
@patch("planhub.cli.commands.setup.ensure_global_config")
def test_setup_command_non_dry_run_created_message(
    mock_ensure, mock_global_path, mock_echo, tmp_path
) -> None:
    mock_ensure.return_value = True
    mock_global_path.return_value = tmp_path / ".planhub" / "config.yaml"

    setup_command(dry_run=False)

    mock_ensure.assert_called_once_with()
    assert any("Created global config" in call.args[0] for call in mock_echo.call_args_list)


@patch("planhub.cli.commands.setup.typer.echo")
@patch("planhub.cli.commands.setup.global_config_path")
@patch("planhub.cli.commands.setup.ensure_global_config")
def test_setup_command_non_dry_run_existing_message(
    mock_ensure, mock_global_path, mock_echo, tmp_path
) -> None:
    mock_ensure.return_value = False
    mock_global_path.return_value = tmp_path / ".planhub" / "config.yaml"

    setup_command(dry_run=False)

    mock_ensure.assert_called_once_with()
    assert any("Global config already exists" in call.args[0] for call in mock_echo.call_args_list)
