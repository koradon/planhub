from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from planhub.config import _deep_merge, default_config_data, read_config_file

_MISSING = object()


@dataclass(frozen=True)
class ConfigQuestion:
    dotted_path: str
    prompt: str
    kind: str  # "csv" | "enum"
    choices: tuple[str, ...] = ()


CONFIG_QUESTIONS: tuple[ConfigQuestion, ...] = (
    ConfigQuestion(
        "sync.github.default_assignees",
        "Default GitHub assignees for new issues (comma-separated)",
        "csv",
    ),
    ConfigQuestion(
        "sync.github.default_labels",
        "Default GitHub labels for new issues (comma-separated)",
        "csv",
    ),
    ConfigQuestion(
        "sync.closed_issues.policy", "Policy for closed issues", "enum", ("archive", "delete")
    ),
    ConfigQuestion(
        "sync.behavior.verbosity", "Sync output verbosity", "enum", ("compact", "verbose")
    ),
)


@dataclass(frozen=True)
class ConfigPromptOutcome:
    target_path: Path
    answers: dict[str, Any]  # every question, dotted path -> parsed value
    updates: dict[str, Any]  # the subset destined for the file
    prompted: bool
    skip_reason: str | None  # "accepted-defaults" | "non-interactive" | None


def parse_csv_list(raw: str) -> list[str]:
    """Trim, drop empty entries, and dedupe (preserving order)."""

    seen: set[str] = set()
    result: list[str] = []
    for item in raw.split(","):
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _value_at(data: Mapping[str, Any], dotted_path: str, *, sentinel: Any = None) -> Any:
    cursor: Any = data
    for part in dotted_path.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return sentinel
        cursor = cursor[part]
    return cursor


def _format_default(question: ConfigQuestion, value: Any) -> str:
    if question.kind == "csv":
        return ", ".join(value or [])
    return str(value)


def _prompt_for_question(question: ConfigQuestion, *, default: Any) -> Any:
    if question.kind == "csv":
        raw = typer.prompt(question.prompt, default=_format_default(question, default))
        return parse_csv_list(raw)

    label = f"{question.prompt} ({'/'.join(question.choices)})"
    while True:
        answer = typer.prompt(label, default=str(default)).strip()
        if answer in question.choices:
            return answer
        typer.echo(f"Please choose one of: {', '.join(question.choices)}.")


def config_updates_from_answers(
    answers: Mapping[str, Any], *, file_data: Mapping[str, Any]
) -> dict[str, Any]:
    """Which answers should actually be written to the file.

    Writing every answer would turn a fresh stub back into a full dump the
    first time someone accepts all defaults. Include an answer only if the
    file already sets that key (so it's genuinely being changed or
    reaffirmed), or if it differs from the built-in default (a real
    project-level override).
    """

    defaults_data = default_config_data()
    updates: dict[str, Any] = {}
    for question in CONFIG_QUESTIONS:
        dotted = question.dotted_path
        answer = answers[dotted]
        already_set = _value_at(file_data, dotted, sentinel=_MISSING) is not _MISSING
        built_in_default = _value_at(defaults_data, dotted)
        if already_set or answer != built_in_default:
            updates[dotted] = answer
    return updates


def run_config_prompts(
    *, target_path: Path, interactive: bool, skip_reason: str | None = None
) -> ConfigPromptOutcome:
    """Ask (or skip) the four onboarding questions for `target_path`.

    Never touches `sys.stdin` itself — callers decide `interactive` (TTY
    check, `--yes`, etc.) so the TTY seam stays in the command module where
    tests already patch it.
    """

    file_data = read_config_file(target_path)
    effective = _deep_merge(default_config_data(), file_data)

    answers: dict[str, Any] = {}
    for question in CONFIG_QUESTIONS:
        current = _value_at(effective, question.dotted_path)
        if interactive:
            answers[question.dotted_path] = _prompt_for_question(question, default=current)
        else:
            answers[question.dotted_path] = current

    updates = config_updates_from_answers(answers, file_data=file_data)

    return ConfigPromptOutcome(
        target_path=target_path,
        answers=answers,
        updates=updates,
        prompted=interactive,
        skip_reason=None if interactive else (skip_reason or "non-interactive"),
    )


def describe_prompts_dry_run(*, target_path: Path) -> tuple[str, ...]:
    """One line per question, showing what would be asked and its current default."""

    file_data = read_config_file(target_path)
    effective = _deep_merge(default_config_data(), file_data)
    lines = []
    for question in CONFIG_QUESTIONS:
        current = _value_at(effective, question.dotted_path)
        lines.append(f"- {question.prompt} [{_format_default(question, current)}]")
    return tuple(lines)
