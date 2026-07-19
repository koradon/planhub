# CLI foundation (init, sync, issue)

## Status

completed

## Related

- Spec: [plan layout and init](../specs/20260719-plan-layout-and-init.md)
- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- Spec: [create issue command](../specs/20260719-create-issue-command.md)
- ADR: [0001 local markdown planning synced to GitHub](../adr/0001-local-markdown-planning-synced-to-github.md)

## Scope

Deliver the first usable Planhub CLI: initialize `.plan/`, sync Markdown to
GitHub Issues/Milestones, and create issues ad hoc. Includes CI and packaging
needed to ship the tool.

Out of scope for this plan: layered config UX, archive policies, verbosity
controls, and pull/push command split (later plans/ideas).

## Steps

1. Implement Typer CLI entrypoint with `init` and `sync`.
2. Define `.plan/` layout discovery and Markdown front-matter parsers.
3. Implement GitHub client + auth (`GITHUB_TOKEN` / `gh`).
4. Import existing GitHub issues and create/update from local files.
5. Add `planhub issue <title>` for immediate create + local file write.
6. Add CI (pytest) and pre-commit tooling.
7. Publish via PyPI / release automation (`grow.py`, workflows).

## Risks

- Bidirectional sync drift without clear source-of-truth rules (addressed later
  in ADR-0002).
- GitHub rate limits during large imports (mitigated with bounded workers).

## Open Questions

- None remaining for this completed foundation plan.
