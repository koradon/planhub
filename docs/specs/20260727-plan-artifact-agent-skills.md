# Plan artifact agent skills

## Status

accepted

## Summary

`planhub init` can install a bundled Claude Code / Cursor skill that teaches
AI agents how to author valid `.plan/` issues and milestones, and when (and
when not) to run `planhub sync`. Installation and updates happen only through
`init`, and only with the user's consent.

## User stories

- As a developer, I want Claude Code / Cursor to already know Planhub's issue
  and milestone front matter when I ask it to draft a plan, so that I don't
  have to paste format docs into the prompt myself.
- As a developer, I want to opt in or out of installing these skills during
  `planhub init`, so that a repo where I don't want AI-authored plans doesn't
  get files added automatically.
- As a developer, I want re-running `planhub init` after upgrading Planhub to
  refresh my installed skill content, so the agent's understanding of the
  format stays current with the version I have installed.
- As a scripted or CI caller of `planhub init`, I want a way to make the
  install decision explicit up front, so `init` never blocks on a prompt.

## Requirements

- Bundle exactly one skill, `planhub-plan-artifacts`, describing: the
  `.plan/` layout, issue front matter, milestone front matter, and an
  explicit rule against running `planhub sync` without the user's request.
- The bundled skill content must be self-contained: it must not link to
  files that only exist in the Planhub repository itself (for example
  `docs/ISSUE_FORMAT.md`), since the target repo does not have them.
- `planhub init` gains a tri-state `--skills`/`--no-skills` option:
  - `--skills` — install/update the skill files; never prompts.
  - `--no-skills` — skip entirely; never prompts.
  - omitted — if stdin is a TTY, prompt `Install Claude/Cursor skills for
    authoring .plan/ issues and milestones?` (default yes); if stdin is not a
    TTY, skip without prompting.
- Skill files are written identically to
  `.claude/skills/planhub-plan-artifacts/SKILL.md` and
  `.cursor/skills/planhub-plan-artifacts/SKILL.md`.
- Installing (via `--skills` or a confirmed prompt) creates missing files and
  overwrites existing files whose content differs from the current bundled
  template, so re-running `init` refreshes skills to the version bundled with
  the installed Planhub release. Files whose content already matches the
  bundled template are left untouched (no unnecessary writes).
- `--no-skills`, or the flag omitted in a non-interactive shell, must not
  touch any existing skill files.
- `planhub init --dry-run` prints the skill file paths `install_skills` would
  affect, and never writes files or prompts, regardless of
  `--skills`/`--no-skills`.
- No other command (`sync`, `setup`, `issue`) installs, updates, or removes
  skill files.

## Behavior

### Decision flow

1. `--dry-run`: print the layout/config paths (existing behavior) plus the
   `.claude`/`.cursor` skill paths `install_skills` would touch; exit before
   writing anything or prompting.
2. Otherwise, run the existing layout/config setup, then resolve the skills
   decision:
   - `--skills` passed → proceed to install/update.
   - `--no-skills` passed → skip; print a hint that `--skills` installs them
     later.
   - Neither passed, stdin is a TTY → prompt for confirmation; proceed to
     install/update only if confirmed.
   - Neither passed, stdin is not a TTY → skip silently (no prompt); same
     hint as `--no-skills`.
3. Install/update: for each of the two target paths, write the bundled
   template if the file is missing or its content differs from the template;
   leave it alone if content already matches. Report each file as installed,
   updated, or already up to date.

### Skill content

The `SKILL.md` body inlines (rather than links to) the front matter formats
from `ISSUE_FORMAT.md`/`MILESTONE_FORMAT.md` and the `.plan/` layout from
`REPO_LAYOUT.md`, condensed, plus the rule that creating or editing `.plan/`
files is safe but running `planhub sync` is not something the agent should do
without being asked.

## Acceptance scenarios (BDD)

See `docs/specs/features/20260727-plan-artifact-agent-skills.feature`.

## Related

- Idea: [AI rules for planning artifacts](../ideas/20260719-ai-rules-for-planning-artifacts.md)
- Spec: [plan layout and init](20260719-plan-layout-and-init.md)
- Reference: [ISSUE_FORMAT.md](../ISSUE_FORMAT.md), [MILESTONE_FORMAT.md](../MILESTONE_FORMAT.md), [REPO_LAYOUT.md](../REPO_LAYOUT.md)
- Active plan: [plan artifact agent skills](../plans/20260727-plan-artifact-agent-skills.md)
- Acceptance: `docs/specs/features/20260727-plan-artifact-agent-skills.feature`

## Open Questions

- Should a future `planhub update`/`upgrade` command (not yet implemented)
  also refresh installed skills? Out of scope until that command exists.
- Should skill granularity ever split into more than one file (for example
  separate sync-safety guidance)? Starting with one bundled skill per the
  idea doc's "keep rules thin" constraint.
