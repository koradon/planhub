# GitHub is source of truth for issue and milestone state

## Status

accepted

## Context and Problem Statement

Local files can drift from GitHub when users close/reopen issues or milestones
in the GitHub UI, or when local `state` values are invalid/non-GitHub statuses.
Early sync behavior risked pushing stale local state and reopening finished
work.

## Considered Options

- Local files are authoritative for `state` / `state_reason` on every sync.
- GitHub is authoritative for issue `state` / `state_reason` and milestone
  `state`; local files are reconciled from GitHub responses.
- Require explicit `pull` before any state reconciliation.

## Decision Outcome

Chosen option: "GitHub is authoritative for issue and milestone state during
`sync`", because GitHub boards and API consumers already treat remote state as
operational truth, and invalid local statuses caused real reopen bugs.

For existing issues, sync reconciles local `state` and `state_reason` from
GitHub and does not treat local state as an override to push. Milestone `state`
is likewise reconciled before archive moves.

### Consequences

- Good, because finished GitHub work cannot be reopened by stale local files.
- Good, because only GitHub-valid states (`open`/`closed`) are accepted locally.
- Bad, because users cannot close an issue purely by editing local front matter
  and expecting sync to push that state today.
- Bad, because intentional local-only state edits require a future explicit
  push model (see pull/push idea).

## Related

- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- Spec: [issue and milestone documents](../specs/20260719-issue-and-milestone-documents.md)
- Idea: [pull and push commands](../ideas/20260719-pull-and-push-commands.md)
