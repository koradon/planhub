# Issue and milestone documents

## Status

accepted

## Summary

Planning artifacts are Markdown files with YAML front matter. Issue and
milestone documents define the local contract that sync maps to GitHub's REST
API.

## User stories

- As a developer, I want stable Markdown + YAML issue files, so that I can edit
  planning content in any editor and review diffs in git.
- As a developer, I want milestone folders with a `milestone.md` file, so that
  scope, due dates, and related issues stay grouped.

## Requirements

### Issue documents

- Location: `.plan/issues/` or `.plan/milestones/<slug>/issues/`.
- Required front matter: `title` (string).
- Optional front matter: `id`, `number`, `labels`, `milestone` (title string or
  number), `assignees`, `type`, `state` (`open` | `closed`), `state_reason`
  (`completed` | `not_planned`, only meaningful with `state: closed`).
- Body after front matter is the GitHub issue description.
- Invalid `state` / `state_reason` values must fail document parsing.
- `labels: []` and `assignees: []` mean clear on GitHub when those keys are set.
- `milestone: null` clears the GitHub milestone when the key is set.
- After creation, `number` is the canonical remote identity.

### Milestone documents

- Location: `.plan/milestones/<slug>/milestone.md` or the archived equivalent
  under `.plan/archive/milestones/<slug>/milestone.md`.
- Required front matter: `title` (string).
- Optional front matter: `id`, `number`, `description`, `due_on` (ISO 8601),
  `state` (`open` | `closed`).
- If `description` is omitted, the Markdown body may be used as description.
- After creation, `number` is the canonical remote identity.

## Behavior

Parsers reject unknown state values instead of coercing them. Sync uses the
parsed documents to build create/update plans and to rewrite front matter after
GitHub responses (for example writing `number`, reconciled `state`, and
milestone placement metadata).

## Acceptance scenarios (BDD)

See `docs/specs/features/20260719-issue-and-milestone-documents.feature`.

## Related

- Reference: [ISSUE_FORMAT.md](../ISSUE_FORMAT.md)
- Reference: [MILESTONE_FORMAT.md](../MILESTONE_FORMAT.md)
- Spec: [GitHub sync](20260719-github-sync.md)
- Spec: [plan layout and init](20260719-plan-layout-and-init.md)
- Acceptance: `docs/specs/features/20260719-issue-and-milestone-documents.feature`

## Open Questions

- None for the shipped document contract.
