# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Planhub is a Python CLI (`planhub`) that syncs local planning artifacts — plans, issues, and
milestones stored as Markdown files with YAML front matter under `.plan/` — to GitHub Issues and
Milestones via the REST API. The core idea: planning data lives in git, next to the code it
describes, and is reviewable like any other file.

## Commands

```bash
uv sync --dev                                          # install deps (dev group)
uv run pytest                                          # run all tests
uv run pytest tests/test_milestone_sync.py              # run a single test file
uv run pytest tests/test_milestone_sync.py::test_name    # run a single test
uv run pytest --cov=planhub --cov-report=term-missing   # coverage
uv run ruff check .                                     # lint
uv run ruff format .                                    # format
uv run ruff format --check .                            # format check (CI)
uv run pre-commit run --all-files                       # all pre-commit hooks
./grow.py                                               # bump version, changelog commit, tag
```

`make help` lists the same via Makefile targets (`install`, `test`, `test-cov`, `lint`, `format`,
`format-check`, `pre-commit`, `build`, `clean`).

CI (`.github/workflows/test.yml`) runs ruff lint + format-check, then pytest with coverage across
Python 3.9–3.14. Match that before considering work done.

## Architecture

### Data model: `.plan/` directory

Each target repo (this one included) gets a `.plan/` tree, managed by `layout.py`
(`PlanLayout`, `ensure_layout`, `discover_milestones`, `discover_root_issues`):

```
.plan/
  config.yaml
  issues/                  # backlog issues, not tied to a milestone
  milestones/<slug>/
    milestone.md
    issues/*.md
    assets/
  archive/
    issues/                # closed root issues (if policy: archive)
    milestones/<slug>/      # closed milestones, moved as whole directories
```

Format contracts: `docs/ISSUE_FORMAT.md`, `docs/MILESTONE_FORMAT.md`, `docs/REPO_LAYOUT.md`.

### Three-layer pipeline (parse → plan → apply)

This is the shape nearly every sync operation follows (see ADR-0005):

1. **Parse** (`documents.py`) — reads Markdown + YAML front matter into typed, frozen dataclasses
   (`IssueDocument`, `MilestoneDocument`). Validates required fields; raises `DocumentError`.
2. **Plan** (`cli/sync_plan.py`, `build_sync_plan`) — diffs local documents against GitHub state
   and produces a `SyncPlan` (creates/updates for issues and milestones) without touching the
   filesystem or the network for writes.
3. **Apply** (`cli/sync_plan.py`, `apply_sync_plan`) — executes the plan against the GitHub API
   via `GitHubClient` (concurrently, `MAX_WORKERS = 5`), then writes GitHub-assigned fields
   (`number`, reconciled `state`) back into the local files via `update_front_matter`.

`pull` and `push` (`cli/commands/sync/pull.py`, `push.py`) are directional halves of this pipeline;
`sync` runs both. Key invariant (ADR-0002, ADR-0006): **GitHub is the source of truth for `state`**.
Local `state`/`state_reason` are never sent on push — they're reconciled from GitHub's response.
`pull` only imports/reconciles and never writes to GitHub; `push` only writes to GitHub and never
imports.

### Module map

- `layout.py` — `.plan/` directory discovery and structure.
- `documents.py` — Markdown/YAML front-matter parse and render for issues/milestones.
- `config.py` — layered config: built-in defaults < `~/.planhub/config.yaml` < `.plan/config.yaml`
  (ADR-0003). Validates against a schema, rejects unknown keys.
- `github.py` — `GitHubClient`, thin wrapper over the REST API (retries, rate-limit handling,
  pagination via `Link` headers).
- `repository.py` — resolves `owner/repo` from the local git remote (`remote.origin.url`).
- `importer.py` — `pull`-side logic: creates/updates local files from GitHub issues.
- `milestone_sync.py` — milestone-specific reconcile logic (state from GitHub, archive/active
  directory placement).
- `cli/sync_plan.py` — the plan/apply core described above; also owns closed-issue archiving
  (`archive_closed_issues_in_filesystem`) and milestone archive-location reconciliation.
- `cli/app.py` + `cli/commands/**` — Typer command wiring; each command module stays thin and
  delegates to the modules above.
- `skills/` — bundled Claude/Cursor skill template (`planhub-plan-artifacts`) installed by
  `planhub init --skills` into a target repo's `.claude/skills/` and `.cursor/skills/`.

### Credentials

`auth.py` resolves a GitHub token by reusing the `gh` CLI session or `$GITHUB_TOKEN`. Commands that
only read local state (most of `pull`, all of `--dry-run`) work without credentials; anything that
writes to GitHub requires them plus a resolvable `remote.origin.url`.

## Documentation workflow (adrlane)

This repo's own `docs/` tree is managed by the adrlane convention: `docs/ideas/` → `docs/specs/`
→ `docs/plans/` → `docs/adr/`, with Gherkin acceptance scenarios in `docs/specs/features/`. Rules
for when to create/update each are in `docs/llm/DECISION_RULES.md`; the full agent contract is in
`docs/llm/AGENT_PROTOCOL.md`. Only touch `docs/**` when doing documentation work, and prefer
updating an existing artifact over creating a new one. Note: this convention governs *this*
project's own docs — it's a different concern from the `.plan/` issue/milestone data model that
`planhub` the tool operates on.

## Conventions

- Prefer Domain-Driven Design shape: small, explicit, typed dataclasses at boundaries
  (`IssueDocument`, `MilestoneDocument`, `PlanLayout`, `SyncPlan`) rather than passing raw dicts
  around.
- Tests are function-style (no test classes), live under `tests/`, use `@patch` for mocking.
- `tests/conftest.py` sets `HOME` to a tmp path for every test (autouse) so no test reads a real
  `~/.planhub/config.yaml`.
- Update `README.md` when user-facing CLI behavior changes.
