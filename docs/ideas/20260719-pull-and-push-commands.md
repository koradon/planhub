# Pull and push commands

## Status

draft

## Summary

Split today's combined `planhub sync` into explicit `pull` and `push` actions,
similar to git, so users can choose direction and conflict handling.

## Problem

`sync` both imports from GitHub and pushes local creates/updates. That is a good
default, but users eventually need aware, directional operations—especially when
local and remote both changed.

## Audience / value

Developers who treat `.plan/` as a working tree and want intentional remote
updates without surprise overwrites.

## Options

- Keep only `sync` and add flags (`--pull-only`, `--push-only`).
- Add `planhub pull` / `planhub push` and keep `sync` as a convenience wrapper.
- Replace `sync` entirely (breaking).

## Constraints

- Must preserve current source-of-truth rules unless an ADR supersedes them.
- Non-interactive CI usage must remain possible.
- Conflict cases (both sides changed) need a defined strategy—possibly defer to
  git for file conflicts after pull.

## Explicit no-gos

- Silent overwrite of local files without a force/opt-in path on pull.
- Removing `sync` before pull/push are feature-complete.

## Related

- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0002 GitHub source of truth for state](../adr/0002-github-source-of-truth-for-state.md)
- Roadmap: [Now / Next / Later](../roadmap/README.md)
- `.plan` issue: #9
