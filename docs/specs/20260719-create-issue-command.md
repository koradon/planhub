# Create issue command

## Status

accepted

## Summary

`planhub issue <title>` creates a GitHub issue immediately and writes a matching
root backlog file under `.plan/issues/` with the returned GitHub number.

## User stories

- As a developer, I want a one-shot CLI to open a GitHub issue, so that I do not
  have to create a Markdown file first when I already know the title.

## Requirements

- Require a GitHub token (`GITHUB_TOKEN` / `GH_TOKEN` or `gh auth login`).
- Require a parseable GitHub `remote.origin.url`.
- Ensure `.plan/issues/` exists (create layout if needed).
- Create the GitHub issue with the given title.
- Write `.plan/issues/YYYYMMDD-<slug>.md` containing at least `title`, `number`,
  `state`, and `assignees` from the GitHub response.
- On filename collision, append `-<number>` before the extension.
- Print the issue number, URL, and saved path.
- Exit non-zero with an error message when auth, remote resolution, or API
  create fails.

## Behavior

Unlike sync, this command is create-only and always targets the root issues
directory. Milestone placement and richer metadata editing remain Markdown +
sync workflows.

## Acceptance scenarios (BDD)

See `docs/specs/features/20260719-create-issue-command.feature`.

## Related

- Spec: [plan layout and init](20260719-plan-layout-and-init.md)
- Spec: [issue and milestone documents](20260719-issue-and-milestone-documents.md)
- Spec: [GitHub sync](20260719-github-sync.md)
- Plan: [CLI foundation](../plans/20260127-cli-foundation.completed.md)
- Acceptance: `docs/specs/features/20260719-create-issue-command.feature`

## Open Questions

- Interactive milestone placement for new issues is still desired (original
  issue #7) but not shipped in the current command.
