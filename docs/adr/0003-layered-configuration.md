# Layered configuration (global + repository)

## Status

accepted

## Context and Problem Statement

Sync behavior (closed-issue policy, verbosity, default labels/assignees) needs
defaults that work across repositories while allowing per-repo overrides without
CLI flag sprawl.

## Considered Options

- CLI flags only, no config files.
- Repository-only `.plan/config.yaml`.
- Layered config: built-in defaults < `~/.planhub/config.yaml` <
  `.plan/config.yaml`, with deep-merge for mappings and replace for scalars/lists.

## Decision Outcome

Chosen option: "Layered config with global and repository overlays", because
cross-repo defaults and per-repo exceptions are both common, and a schema-validated
YAML file keeps behavior reviewable in git for repo overrides.

`planhub setup` creates the global file; `planhub init` ensures both global and
repo files exist without overwriting.

### Consequences

- Good, because users can set personal defaults once.
- Good, because repositories can override policy in-tree.
- Bad, because debugging effective config requires understanding merge order.
- Bad, because interactive onboarding prompts are still missing.

## Related

- Spec: [layered configuration](../specs/20260719-layered-configuration.md)
- Idea: [interactive config prompts](../ideas/20260719-interactive-config-prompts.md)
