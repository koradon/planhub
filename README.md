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

## Commands
- `planhub init`
  - Creates the standard `.plan/` structure in the current repo.
  - Use `--dry-run` to preview the folders that would be created.
- `planhub sync`
  - Reads `.plan/` files and creates or updates GitHub issues and milestones.
  - Writes the GitHub `number` back into each file after creation.
  - Sync runs in three phases: parse files, build a sync plan, then apply it.
  - Use `--dry-run` to validate files without writing changes.
  - Use `--import-existing` to pull existing GitHub issues into `.plan/`.
    This requires credentials and a GitHub `remote.origin.url`.
  - Creating issues or milestones also requires credentials and a GitHub
    `remote.origin.url`.
  - Sync never deletes local files. If something can’t be identified, it
    reports an error and skips removal.

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

## Next Steps
- Implement the parsing + GitHub sync logic.
- Add CI to validate file formats.
