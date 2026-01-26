# Planhub

Planhub is a CLI app that syncs local planning artifacts (plans, issues,
milestones written as `.md` files) to GitHub Issues via the API.

## Goals
- Keep planning artifacts in git and reviewable.
- Generate/update GitHub issues and milestones from local files.
- Make planning conversational: we can edit `.md` files and sync later.

## Proposed Architecture
We split the system into two parts:
1. **CLI app (this repo)**: handles GitHub API communication and syncing.
2. **Data repo**: contains the `plans/`, `issues/`, and `milestones/` files.

The CLI will scaffold the data repo and then sync it on demand.

## Commands
- `planhub init`
  - Creates the standard folder structure in the current git repo:
    `plans/`, `issues/`, `milestones/`, and `docs/`.
- `planhub sync`
  - Reads the `.md` files and creates/updates GitHub issues/milestones.

## Suggested Data Repo Layout
```
plans/
issues/
milestones/
docs/
```

## Next Steps
- Finalize the file formats (see `docs/`).
- Implement `init` and `sync` commands.
- Add CI to validate the file format.
