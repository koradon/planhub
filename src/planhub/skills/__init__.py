from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

SKILL_NAMES: tuple[str, ...] = ("planhub-plan-artifacts",)
_TARGET_DIRS: tuple[str, ...] = (".claude/skills", ".cursor/skills")


@dataclass(frozen=True)
class SkillInstallResult:
    created: tuple[Path, ...]
    updated: tuple[Path, ...]
    unchanged: tuple[Path, ...]


def skill_install_paths(repo_root: Path) -> tuple[Path, ...]:
    """All .claude/.cursor SKILL.md paths install_skills() would touch."""

    return tuple(
        repo_root / target_dir / name / "SKILL.md"
        for name in SKILL_NAMES
        for target_dir in _TARGET_DIRS
    )


def _skill_content(name: str) -> str:
    templates = resources.files("planhub.skills")
    return templates.joinpath("templates", f"{name}.md").read_text(encoding="utf-8")


def install_skills(repo_root: Path, *, dry_run: bool = False) -> SkillInstallResult:
    """Write bundled SKILL.md files into .claude/ and .cursor/.

    Creates missing files, overwrites files whose content differs from the
    current bundled template, and leaves already-up-to-date files untouched.
    """

    created: list[Path] = []
    updated: list[Path] = []
    unchanged: list[Path] = []
    for name in SKILL_NAMES:
        content = _skill_content(name)
        for target_dir in _TARGET_DIRS:
            path = repo_root / target_dir / name / "SKILL.md"
            if path.exists():
                if path.read_text(encoding="utf-8") == content:
                    unchanged.append(path)
                    continue
                if not dry_run:
                    path.write_text(content, encoding="utf-8")
                updated.append(path)
                continue
            if not dry_run:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            created.append(path)
    return SkillInstallResult(
        created=tuple(created), updated=tuple(updated), unchanged=tuple(unchanged)
    )
