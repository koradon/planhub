from __future__ import annotations

from planhub.skills import SKILL_NAMES, install_skills, skill_install_paths


def test_skill_install_paths_covers_claude_and_cursor(tmp_path) -> None:
    paths = skill_install_paths(tmp_path)

    assert len(paths) == 2 * len(SKILL_NAMES)
    assert tmp_path / ".claude" / "skills" / "planhub-plan-artifacts" / "SKILL.md" in paths
    assert tmp_path / ".cursor" / "skills" / "planhub-plan-artifacts" / "SKILL.md" in paths


def test_install_skills_creates_both_files_with_matching_content(tmp_path) -> None:
    result = install_skills(tmp_path)

    assert len(result.created) == 2
    assert not result.updated
    assert not result.unchanged
    claude_path, cursor_path = sorted(result.created)
    assert claude_path.read_text(encoding="utf-8") == cursor_path.read_text(encoding="utf-8")
    assert "planhub-plan-artifacts" in claude_path.read_text(encoding="utf-8")


def test_install_skills_dry_run_writes_nothing(tmp_path) -> None:
    result = install_skills(tmp_path, dry_run=True)

    assert len(result.created) == 2
    for path in skill_install_paths(tmp_path):
        assert not path.exists()


def test_install_skills_second_run_is_unchanged_when_content_matches(tmp_path) -> None:
    install_skills(tmp_path)

    result = install_skills(tmp_path)

    assert not result.created
    assert not result.updated
    assert len(result.unchanged) == 2


def test_install_skills_overwrites_stale_content(tmp_path) -> None:
    install_skills(tmp_path)
    for path in skill_install_paths(tmp_path):
        path.write_text("stale local edit", encoding="utf-8")

    result = install_skills(tmp_path)

    assert not result.created
    assert not result.unchanged
    assert len(result.updated) == 2
    for path in skill_install_paths(tmp_path):
        assert path.read_text(encoding="utf-8") != "stale local edit"


def test_install_skills_dry_run_does_not_overwrite_stale_content(tmp_path) -> None:
    install_skills(tmp_path)
    for path in skill_install_paths(tmp_path):
        path.write_text("stale local edit", encoding="utf-8")

    result = install_skills(tmp_path, dry_run=True)

    assert len(result.updated) == 2
    for path in skill_install_paths(tmp_path):
        assert path.read_text(encoding="utf-8") == "stale local edit"
