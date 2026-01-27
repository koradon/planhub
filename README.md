# Planhub

Planhub is a CLI app that syncs local planning artifacts (plans, issues,
milestones written as `.md` files) to GitHub Issues via the API.

## Goals
- Keep planning artifacts in git and reviewable.
- Generate/update GitHub issues and milestones from local files.
- Make planning conversational: we can edit `.md` files and sync later.

## How It Works
Planhub stores planning artifacts inside each target repository under `.plan/`.
The CLI initializes the layout and then syncs the local files with GitHub.

## Installation
Global install from PyPI (recommended for CLI usage). `pipx` keeps CLI tools in
isolated environments while still putting `planhub` on your PATH, so your
global site-packages stay clean:

```
pipx install planhub
```

Project-local install with uv (inside your repo):

```
uv venv
uv pip install planhub
```

## Commands
- `planhub init`
  - Creates the standard `.plan/` structure in the current repo.
- `planhub sync`
  - Reads the `.md` files and creates/updates GitHub issues/milestones.

## Suggested Data Repo Layout
```
.plan/
  milestones/
    stage-1/
      milestone.md
      issues/
        issue-001.md
      assets/
        diagram.png
```

## Next Steps
- Implement the parsing + GitHub sync logic.
- Add CI to validate file formats.
