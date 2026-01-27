from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from planhub.documents import DocumentError, load_issue_document, load_milestone_document
from planhub.layout import discover_milestones, ensure_layout, load_layout


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planhub")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init", help="Initialize the .plan layout in a repo."
    )
    init_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing."
    )

    sync_parser = subparsers.add_parser("sync", help="Sync .plan files with GitHub.")
    sync_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing."
    )

    args = parser.parse_args(argv)
    if args.command == "init":
        return _run_init(Path.cwd(), dry_run=args.dry_run)
    if args.command == "sync":
        return _run_sync(Path.cwd(), dry_run=args.dry_run)

    parser.print_help()
    return 1


def _run_init(repo_root: Path, dry_run: bool) -> int:
    if dry_run:
        plan_root = repo_root / ".plan"
        milestones_dir = plan_root / "milestones"
        print("Dry run: would create plan layout:")
        print(f"- {plan_root}")
        print(f"- {milestones_dir}")
        return 0

    layout = ensure_layout(repo_root)
    print(f"Initialized plan layout at {layout.root}")
    return 0


def _run_sync(repo_root: Path, dry_run: bool) -> int:
    try:
        layout = load_layout(repo_root)
    except FileNotFoundError as exc:
        print(f"{exc}. Run 'planhub init' first.")
        return 1

    milestones = discover_milestones(layout)
    parsed_milestones = 0
    parsed_issues = 0
    errors: list[str] = []
    for entry in milestones:
        if not entry.milestone_file.exists():
            errors.append(f"{entry.milestone_file}: missing milestone.md")
            continue
        try:
            load_milestone_document(entry.milestone_file)
            parsed_milestones += 1
        except DocumentError as exc:
            errors.append(str(exc))
            continue

        for issue_file in entry.issue_files:
            try:
                load_issue_document(issue_file)
                parsed_issues += 1
            except DocumentError as exc:
                errors.append(str(exc))

    for error in errors:
        print(f"Error: {error}")
    if dry_run:
        print("Dry run: no changes will be written.")
    print(f"Found {parsed_milestones} milestones and {parsed_issues} issues.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
