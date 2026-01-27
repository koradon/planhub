from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from planhub.layout import discover_milestones, ensure_layout, load_layout


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planhub")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize the .plan layout in a repo.")
    subparsers.add_parser("sync", help="Sync .plan files with GitHub.")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _run_init(Path.cwd())
    if args.command == "sync":
        return _run_sync(Path.cwd())

    parser.print_help()
    return 1


def _run_init(repo_root: Path) -> int:
    layout = ensure_layout(repo_root)
    print(f"Initialized plan layout at {layout.root}")
    return 0


def _run_sync(repo_root: Path) -> int:
    try:
        layout = load_layout(repo_root)
    except FileNotFoundError as exc:
        print(f"{exc}. Run 'planhub init' first.")
        return 1

    milestones = discover_milestones(layout)
    issue_count = sum(len(entry.issue_files) for entry in milestones)
    print(f"Found {len(milestones)} milestones and {issue_count} issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
