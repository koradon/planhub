from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PLAN_DIR_NAME = ".plan"
MILESTONES_DIR_NAME = "milestones"
ROOT_ISSUES_DIR_NAME = "issues"
ISSUES_DIR_NAME = "issues"
MILESTONE_FILENAME = "milestone.md"


@dataclass(frozen=True)
class PlanLayout:
    root: Path
    milestones_dir: Path
    issues_dir: Path


@dataclass(frozen=True)
class MilestoneEntry:
    directory: Path
    milestone_file: Path
    issue_files: tuple[Path, ...]


def ensure_layout(repo_root: Path) -> PlanLayout:
    plan_root = repo_root / PLAN_DIR_NAME
    milestones_dir = plan_root / MILESTONES_DIR_NAME
    issues_dir = plan_root / ROOT_ISSUES_DIR_NAME
    milestones_dir.mkdir(parents=True, exist_ok=True)
    issues_dir.mkdir(parents=True, exist_ok=True)
    return PlanLayout(
        root=plan_root, milestones_dir=milestones_dir, issues_dir=issues_dir
    )


def load_layout(repo_root: Path) -> PlanLayout:
    plan_root = repo_root / PLAN_DIR_NAME
    milestones_dir = plan_root / MILESTONES_DIR_NAME
    issues_dir = plan_root / ROOT_ISSUES_DIR_NAME
    if not plan_root.exists():
        raise FileNotFoundError(f"Missing {PLAN_DIR_NAME} directory")
    if not milestones_dir.exists():
        raise FileNotFoundError(f"Missing {MILESTONES_DIR_NAME} directory")
    if not issues_dir.exists():
        raise FileNotFoundError(f"Missing {ROOT_ISSUES_DIR_NAME} directory")
    return PlanLayout(
        root=plan_root, milestones_dir=milestones_dir, issues_dir=issues_dir
    )


def discover_milestones(layout: PlanLayout) -> tuple[MilestoneEntry, ...]:
    entries: list[MilestoneEntry] = []
    for milestone_dir in _sorted_dirs(layout.milestones_dir):
        milestone_file = milestone_dir / MILESTONE_FILENAME
        issue_files = _sorted_files(milestone_dir / ISSUES_DIR_NAME, "*.md")
        entries.append(
            MilestoneEntry(
                directory=milestone_dir,
                milestone_file=milestone_file,
                issue_files=issue_files,
            )
        )
    return tuple(entries)


def discover_root_issues(layout: PlanLayout) -> tuple[Path, ...]:
    return _sorted_files(layout.issues_dir, "*.md")


def _sorted_dirs(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return []
    return sorted([path for path in directory.iterdir() if path.is_dir()])


def _sorted_files(directory: Path, pattern: str) -> tuple[Path, ...]:
    if not directory.exists():
        return ()
    return tuple(sorted(directory.glob(pattern)))
