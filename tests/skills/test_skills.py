from __future__ import annotations

from planhub.skills import (
    SKILL_NAMES,
    SKILL_TARGET_DIRS,
    install_skills,
    skill_install_paths,
)

EXPECTED_FILE_COUNT = len(SKILL_TARGET_DIRS) * len(SKILL_NAMES)


def test_skill_install_paths_covers_claude_cursor_codex_and_antigravity(tmp_path) -> None:
    paths = skill_install_paths(tmp_path)

    assert len(paths) == EXPECTED_FILE_COUNT
    assert tmp_path / ".claude" / "skills" / "planhub-plan-artifacts" / "SKILL.md" in paths
    assert tmp_path / ".cursor" / "skills" / "planhub-plan-artifacts" / "SKILL.md" in paths
    assert tmp_path / ".codex" / "skills" / "planhub-plan-artifacts" / "SKILL.md" in paths
    assert tmp_path / ".agents" / "skills" / "planhub-plan-artifacts" / "SKILL.md" in paths


def test_install_skills_creates_every_file_with_matching_content(tmp_path) -> None:
    result = install_skills(tmp_path)

    assert len(result.created) == EXPECTED_FILE_COUNT
    assert not result.updated
    assert not result.unchanged
    contents = {path.read_text(encoding="utf-8") for path in result.created}
    assert len(contents) == 1
    assert "planhub-plan-artifacts" in contents.pop()


# Codex CLI only scans `.codex/skills`; installing anywhere else leaves Codex agents
# without the skill, which is the gap this target dir closes.
def test_install_skills_writes_codex_skill_into_dot_codex(tmp_path) -> None:
    install_skills(tmp_path)

    codex_skill = tmp_path / ".codex" / "skills" / "planhub-plan-artifacts" / "SKILL.md"

    assert codex_skill.is_file()
    assert "planhub-plan-artifacts" in codex_skill.read_text(encoding="utf-8")


# Antigravity CLI (`agy`) only scans `.agents/skills`; installing anywhere else leaves
# Antigravity agents without the skill, which is the gap this target dir closes.
def test_install_skills_writes_antigravity_skill_into_dot_agents(tmp_path) -> None:
    install_skills(tmp_path)

    antigravity_skill = tmp_path / ".agents" / "skills" / "planhub-plan-artifacts" / "SKILL.md"

    assert antigravity_skill.is_file()
    assert "planhub-plan-artifacts" in antigravity_skill.read_text(encoding="utf-8")


def test_install_skills_dry_run_writes_nothing(tmp_path) -> None:
    result = install_skills(tmp_path, dry_run=True)

    assert len(result.created) == EXPECTED_FILE_COUNT
    for path in skill_install_paths(tmp_path):
        assert not path.exists()


def test_install_skills_second_run_is_unchanged_when_content_matches(tmp_path) -> None:
    install_skills(tmp_path)

    result = install_skills(tmp_path)

    assert not result.created
    assert not result.updated
    assert len(result.unchanged) == EXPECTED_FILE_COUNT


def test_install_skills_overwrites_stale_content(tmp_path) -> None:
    install_skills(tmp_path)
    for path in skill_install_paths(tmp_path):
        path.write_text("stale local edit", encoding="utf-8")

    result = install_skills(tmp_path)

    assert not result.created
    assert not result.unchanged
    assert len(result.updated) == EXPECTED_FILE_COUNT
    for path in skill_install_paths(tmp_path):
        assert path.read_text(encoding="utf-8") != "stale local edit"


def test_install_skills_dry_run_does_not_overwrite_stale_content(tmp_path) -> None:
    install_skills(tmp_path)
    for path in skill_install_paths(tmp_path):
        path.write_text("stale local edit", encoding="utf-8")

    result = install_skills(tmp_path, dry_run=True)

    assert len(result.updated) == EXPECTED_FILE_COUNT
    for path in skill_install_paths(tmp_path):
        assert path.read_text(encoding="utf-8") == "stale local edit"
