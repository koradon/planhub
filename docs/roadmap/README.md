# Roadmap (Now / Next / Later)

The roadmap holds future initiatives without committing to exact dates.

- **Now**: active work or work starting soon (high confidence)
- **Next**: upcoming work with high confidence, but not started yet
- **Later**: speculative bets or ideas pending further validation

### Update semantics

- Add items when there is enough clarity to evaluate them.
- Link roadmap items to the related **Idea**, **Spec**, and/or **Plan** documents.
- Move items between horizons when confidence changes.

## Now

- Fix closed-milestone archive move collisions (`.plan` issue #37).
- Clarify sync summary counters when issue content changes (`.plan` issue #34).

## Next

- [Init welcome templates](../ideas/20260719-init-welcome-templates.md) (`.plan` issue #2).

## Later

(none currently)

## Shipped (documented)

Core CLI, sync, archive policies, state reconciliation, the `planhub init`
agent skills install/update flow, the `pull`/`push`/`sync` command split, and
[interactive config prompts](../specs/20260728-interactive-config-prompts.md)
(`.plan` issue #26, which also removed the global config layer — see
[ADR-0007](../adr/0007-repository-only-configuration.md)) are documented
under `docs/specs/` and `docs/adr/`. See [docs/README.md](../README.md).

If the project needs more detailed horizon pages, add them under `docs/roadmap/`
using `docs/llm/templates/roadmap.md`.
