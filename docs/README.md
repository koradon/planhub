# Documentation Map

This repository uses a docs-as-code layout bootstrapped by [adrlane](https://github.com/koradon/adrlane).

## Structure

| Path | Purpose |
| --- | --- |
| `docs/specs/` | Feature specifications, behavior, and contracts |
| `docs/specs/features/` | Gherkin acceptance scenarios for specs |
| `docs/plans/` | Implementation plans derived from specs |
| `docs/adr/` | Architecture and design decision records |
| `docs/ideas/` | Early concepts that may be promoted to specs |
| `docs/roadmap/` | Now / Next / Later horizons for future initiatives |
| `docs/reference/` | CLI and related reference material |
| `docs/llm/` | Agent-facing documentation contract and templates |

## Shipped feature docs

| Spec | ADR / plan anchors |
| --- | --- |
| [Plan layout and init](specs/20260719-plan-layout-and-init.md) | [ADR-0001](adr/0001-local-markdown-planning-synced-to-github.md) |
| [GitHub sync](specs/20260719-github-sync.md) | [ADR-0002](adr/0002-github-source-of-truth-for-state.md), [ADR-0004](adr/0004-archive-closed-artifacts-by-policy.md), [ADR-0005](adr/0005-three-phase-sync-pipeline.md) |
| [Issue and milestone documents](specs/20260719-issue-and-milestone-documents.md) | [ISSUE_FORMAT](ISSUE_FORMAT.md), [MILESTONE_FORMAT](MILESTONE_FORMAT.md) |
| [Layered configuration](specs/20260719-layered-configuration.md) | [ADR-0003](adr/0003-layered-configuration.md) |
| [Create issue command](specs/20260719-create-issue-command.md) | [CLI foundation plan](plans/20260127-cli-foundation.completed.md) |
| [Plan artifact agent skills](specs/20260727-plan-artifact-agent-skills.md) | [Plan artifact agent skills plan](plans/20260727-plan-artifact-agent-skills.completed.md) |

Format/layout contracts also live as long-form reference:

- [REPO_LAYOUT.md](REPO_LAYOUT.md)
- [ISSUE_FORMAT.md](ISSUE_FORMAT.md)
- [MILESTONE_FORMAT.md](MILESTONE_FORMAT.md)
- [CLI reference](reference/cli.md)

Completed implementation plans:

- [CLI foundation](plans/20260127-cli-foundation.completed.md)
- [Config and sync hardening](plans/20260327-config-sync-hardening.completed.md)
- [Plan artifact agent skills](plans/20260727-plan-artifact-agent-skills.completed.md)

## How this documentation grows

`adrlane init` creates a minimal core and does not predict future project shape.

When the project gains a new, recurring documentation need (for example runbooks
or additional reference pages), the agent should:

1. Add a new top-level folder under `docs/` when the content does not fit
   `specs/`, `plans/`, `adr/`, `ideas/`, `roadmap/`, or `reference/`.
2. Copy a starter template from `docs/llm/templates/` and adapt it.
3. Update this file to document the new section.

Do not create empty folders "for later". Grow the tree only when there is real
content to place there.

Release history lives in Git and release tooling, not in `docs/`.

For the full growth model, see the [adrlane documentation model](https://github.com/koradon/adrlane#documentation-model).

## For agents

Read `docs/llm/AGENT_PROTOCOL.md` first. It defines the doc workflow
(`idea -> spec -> plan`) and how to extend the documentation consistently.
