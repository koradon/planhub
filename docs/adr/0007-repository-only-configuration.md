# Repository-only configuration (drop the global config layer)

## Status

accepted

## Context and Problem Statement

ADR-0003 introduced a layered config (`built-in defaults < ~/.planhub/config.yaml
< .plan/config.yaml`) so users could set personal defaults once and let
repositories override them. Implementing issue #26 (interactive prompts during
onboarding) required deciding what the global layer is actually *for*, since
prompting for six settings across two files, with a merge order between them,
only makes sense if the global layer earns its keep.

`sync.github.default_assignees` was the strongest case for a global default —
a GitHub username that repeats across every repo. But a developer with
separate work and personal GitHub accounts cannot have one correct global
value for it: they would override it per repo anyway, making the "default" an
actively wrong value for however many repos don't match today's active
account. The one remaining candidate for a genuinely personal setting,
`sync.behavior.verbosity`, already has `--verbose`/`--compact` CLI flags, so it
doesn't justify a config file, a `planhub setup` command, and a merge-order
layer on its own — ADR-0003 already lists "debugging effective config requires
understanding merge order" as a cost of that layer.

Planhub is pre-1.0 (`0.4.0`), single-user, with no installed base to protect
(2 GitHub stars, 0 forks at the time of this decision), so there is no
compatibility reason to keep the layer around while its justification erodes.

## Considered Options

- **Keep layering as designed.** Preserve `~/.planhub/config.yaml` and
  `planhub setup`, and just make the interactive prompts write both files.
  Keeps a file whose only unbroken use case (`verbosity`) already has CLI
  flags, and keeps the merge-order tax for no real gain.
- **Split by ownership.** Keep the global file, but restrict it to genuinely
  personal keys (`default_assignees`, `verbosity`) and put project keys
  (`default_labels`, `closed_issues.*`) only in the repo file. Rejected once
  the multi-account scenario showed `default_assignees` isn't safely personal
  either — leaving only `verbosity` in the personal bucket, not enough to
  justify a scope-aware schema and a second file.
- **Drop the global layer entirely.** One config file (`.plan/config.yaml`),
  one command that prompts (`planhub init`), no merge order to reason about.

## Decision Outcome

Chosen option: "Drop the global layer entirely", because the key that most
justified a global file breaks under a common real-world scenario (multiple
GitHub accounts), and the one key that survives that scenario already has a
CLI-flag alternative. Removing the layer trades a small, real convenience
(set assignees/verbosity once, everywhere) for a strictly simpler mental
model, and pre-1.0 status means this trade can be made without a deprecation
cycle.

`planhub setup` and `~/.planhub/config.yaml` support are removed outright:
no warning, no compatibility stub. `planhub init` remains the single
onboarding entry point and now prompts interactively for the four repo-level
settings (see [interactive config prompts](../specs/20260728-interactive-config-prompts.md)).

### Consequences

- Good, because there's exactly one config file and no merge order to debug —
  directly resolves the "Bad" consequence ADR-0003 recorded for that reason.
- Good, because a value shown as a prompt default is always the value that
  will actually take effect; there's no second layer that could silently
  override it later.
- Good, because onboarding is one command (`planhub init`) instead of two.
- Bad, because a developer who genuinely wants "the same assignee everywhere"
  now has to accept per-repo prompts (or `-y`) in every repo — the small
  convenience layering provided is gone.
- Bad, because this is a breaking change for anyone else who had already set
  a non-default value in `~/.planhub/config.yaml`. Accepted given planhub's
  pre-1.0, single-user status at the time of this decision.

## Related

- Supersedes: [ADR-0003 layered configuration](0003-layered-configuration.md)
- Spec: [interactive config prompts](../specs/20260728-interactive-config-prompts.md)
- Spec (superseded): [layered configuration](../specs/20260719-layered-configuration.md)
- Idea: [interactive config prompts](../ideas/20260719-interactive-config-prompts.md)
