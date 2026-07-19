# Plan layout and init

## Status

accepted

## Summary

Planhub stores planning artifacts as Markdown files under a `.plan/` directory in
each target repository. `planhub init` creates that layout (and default config
files) so sync and other commands have a predictable place to read and write.

## User stories

- As a developer, I want a standard `.plan/` tree in my repo, so that planning
  files stay next to the code they describe and can be reviewed in git.
- As a developer, I want `planhub init --dry-run` to preview changes, so that I
  can confirm paths before writing anything.

## Requirements

- `.plan/` must contain `issues/` (root backlog) and `milestones/` directories.
- Each milestone lives in `.plan/milestones/<slug>/` with `milestone.md`,
  optional `issues/`, and optional `assets/`.
- Closed root issues may live under `.plan/archive/issues/` (see sync/archiving).
- Closed milestones may live under `.plan/archive/milestones/<slug>/`.
- `planhub init` creates missing layout directories and ensures global
  (`~/.planhub/config.yaml`) and repo (`.plan/config.yaml`) config files exist
  without overwriting existing files.
- `planhub init --dry-run` prints intended paths and does not write files.
- Sync and other commands that require a layout must fail with a clear hint to
  run `planhub init` when `.plan/` is missing or incomplete.

## Behavior

### Layout contract

```
.plan/
  config.yaml
  issues/
  milestones/
    <slug>/
      milestone.md
      issues/
      assets/
  archive/
    issues/
    milestones/
      <slug>/
```

Imported and CLI-created root issues use `YYYYMMDD-<slug>.md` filenames.

### Init command

1. Resolve the current working directory as the repository root.
2. In dry-run mode, echo the layout and config paths that would be created, then
   exit successfully.
3. Otherwise call `ensure_layout`, `ensure_global_config`, and
   `ensure_repo_config`, and report whether each config was created or already
   existed.

## Acceptance scenarios (BDD)

See `docs/specs/features/20260719-plan-layout-and-init.feature`.

## Related

- Reference: [REPO_LAYOUT.md](../REPO_LAYOUT.md)
- Spec: [layered configuration](20260719-layered-configuration.md)
- Spec: [GitHub sync](20260719-github-sync.md)
- ADR: [0001 local markdown planning synced to GitHub](../adr/0001-local-markdown-planning-synced-to-github.md)
- Active plan: (none — shipped)
- Acceptance: `docs/specs/features/20260719-plan-layout-and-init.feature`

## Open Questions

- None for the shipped layout. Welcome template content for `init` is tracked
  separately as an idea.
