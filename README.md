# Planhub

Planhub is a CLI app that syncs local planning artifacts (plans, issues,
milestones written as `.md` files) to GitHub Issues via the API.

## Goals
- Keep planning artifacts in git and reviewable.
- Generate/update GitHub issues and milestones from local files.
- Make planning conversational: we can edit `.md` files and sync later.

## How It Works
Planhub keeps planning data next to the code it describes. Each repository gets
a `.plan/` folder containing milestones and issues as Markdown files with YAML
front matter. You edit these files like normal docs, then `planhub sync` maps
them to GitHub issues and milestones.

## Installation
Global install from PyPI (recommended for CLI usage). `pipx` gives you a clean
CLI install without polluting your system Python, and puts `planhub` on your
PATH:

```
pipx install planhub
```

Project-local install with uv (inside your repo). This keeps the tool in a
virtual environment for that repo:

```
uv venv
uv pip install planhub
```

## First Run (Required)
Run `planhub setup` immediately after installation to create the global config
at `~/.planhub/config.yaml` (created only if missing):

```
planhub setup
```

Without this setup step, sync defaults and other CLI behavior may be missing.

## Commands
- `planhub init`
  - Creates the standard `.plan/` structure in the current repo.
  - Use `--dry-run` to preview the folders that would be created.
  - Offers to install a `planhub-plan-artifacts` skill for Claude Code and
    Cursor (`.claude/skills/` and `.cursor/skills/`) that teaches the agent
    `.plan/` layout, front matter, and to never run `planhub sync` unasked.
  - Use `--skills` to install/update without prompting, or `--no-skills` to
    skip without prompting. Omit both to be asked (interactive shells only —
    non-interactive runs skip by default).
  - Re-running `planhub init --skills` refreshes any installed skill file
    whose content is out of date with the bundled template.
- `planhub setup`
  - Creates the global config file at `~/.planhub/config.yaml` (if missing).
  - Use `--dry-run` to preview what would be created.
- `planhub issue <title>`
  - Creates a new GitHub issue with the given title.
  - Requires credentials and a GitHub `remote.origin.url`.
- `planhub pull`
  - Imports GitHub issues and milestones into `.plan/`. Never writes to GitHub.
  - Imports all GitHub milestones into `.plan/` (including open milestones with
    only closed issues, empty milestones, and closed milestones under
    `.plan/archive/milestones`). Closed milestone issues are imported into the
    milestone folder; closed backlog/root issues are not imported as files.
  - GitHub is also the source of truth for milestone `state`; local milestone
    files are reconciled from GitHub before archive moves run.
  - Use `--force` to overwrite an already-imported local issue file's
    title/body/labels/assignees/milestone/state from its current GitHub
    content. Local-only front matter keys (e.g. `id`) are preserved. Without
    `--force`, an already-imported issue's content is left untouched.
  - Use `--dry-run` to preview imports/overwrites without writing changes.
  - Requires credentials and a GitHub `remote.origin.url` to import; without
    them, pull still runs local reconcile and exits 0.
- `planhub push`
  - Reads `.plan/` files and creates or updates GitHub issues and milestones.
    Never imports from GitHub.
  - Prints explicit operation counts for create/update/archive/delete.
  - Writes the GitHub `number` back into each file after creation.
  - GitHub is the source of truth for issue state during push; push does not
    send local `state` or `state_reason` to GitHub, it reconciles those
    fields from the GitHub response.
  - Push runs in three phases: parse files, build a sync plan, then apply it.
  - Use `--dry-run` to validate files without writing changes.
  - Use `--verbose` for path-level planned changes, or `--compact` for concise
    output. CLI flags override config.
  - Requires credentials and a GitHub `remote.origin.url` only when there are
    pending creates/updates; exits non-zero in that case if missing.
  - Closed synced root issues are archived under `.plan/archive/issues` by
    default (or deleted when `sync.closed_issues.policy: delete` is configured).
  - Milestone issues remain inside their milestone folder. When
    `milestone.md` has `state: "closed"`, push moves the whole milestone
    directory to `.plan/archive/milestones`. If set back to `state: "open"`,
    push moves that directory back under `.plan/milestones`.
- `planhub sync`
  - Runs `planhub pull` then `planhub push` — the same combined behavior as
    before `pull`/`push` existed as separate commands.
  - Use `--dry-run`, `--verbose`, or `--compact` as with `push`.

## Credentials
Planhub can reuse your GitHub CLI session or a token stored in the environment.
The simplest path is to authenticate once with `gh`, and the CLI will fetch a
token automatically.

```
gh auth login
```

Alternatively, create a personal access token and export it:

1. GitHub → Settings → Developer settings → Personal access tokens.
2. Create a fine-grained token for the target repo(s).
3. Grant Issues: Read (and Write if you will push updates later).

```
export GITHUB_TOKEN=ghp_your_token_here
```

## Suggested Data Repo Layout
```
.plan/
  issues/
    20260127-backlog-issue.md
  milestones/
    stage-1/
      milestone.md
      issues/
        issue-001.md
      assets/
        diagram.png
```

## Front Matter Tips
- `milestone` can be a title or a number; use `milestone: null` to clear it.
- Use `labels: []` or `assignees: []` to remove them on GitHub.
- `state_reason` requires `state: "closed"`.

## Config
- `~/.planhub/config.yaml` and `.plan/config.yaml` are layered (repo overrides global).
- Set `sync.behavior.verbosity` to `compact` (default) or `verbose`.

## Development

### Setup

Install development dependencies:

```
uv sync --dev
```

### Pre-commit Hooks

This project uses pre-commit to run code quality checks before commits. Install
the hooks:

```
uv run pre-commit install
```

The hooks will automatically run on `git commit`. They check for:
- Code formatting and linting (ruff)
- Trailing whitespace and end-of-file fixes
- YAML, JSON, and TOML syntax
- Merge conflicts and other common issues

To run hooks manually:

```
uv run pre-commit run --all-files
```

### Version Bumping

This project includes a `grow.py` script for bumping versions and creating releases:

```
./grow.py
```

The script will:
1. Read the current version from `pyproject.toml`
2. Show commits since the last tag
3. Prompt for the new version
4. Update the version in `pyproject.toml`
5. Create a commit with a changelog of commits since the last release
6. Create an annotated tag with the new version
7. Optionally push commits and tags to the remote repository

The changelog commit includes all commit messages since the last tag, making it easy to see what changed in each release on GitHub.

## License

Planhub is licensed under the [GNU Affero General Public License v3.0](LICENSE)
(AGPL-3.0). See `LICENSE` for the full text.

## Next Steps
- Implement the parsing + GitHub sync logic.
- Add CI to validate file formats.
