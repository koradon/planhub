Feature: Plan artifact agent skills
  Install a Claude/Cursor skill during `planhub init` that teaches agents the .plan/ format.

  # Related spec: docs/specs/20260727-plan-artifact-agent-skills.md

  Scenario: Dry-run lists skill paths without writing or prompting
    Given a repository without `.plan/` yet
    When the user runs `planhub init --dry-run`
    Then the output lists the `.claude/skills/planhub-plan-artifacts/SKILL.md` and `.cursor/skills/planhub-plan-artifacts/SKILL.md` paths
    And no files are written
    And the user is not prompted

  Scenario: Explicit --skills installs without prompting
    Given a repository with no skill files installed
    When the user runs `planhub init --skills`
    Then `.claude/skills/planhub-plan-artifacts/SKILL.md` and `.cursor/skills/planhub-plan-artifacts/SKILL.md` are created
    And the user is not prompted

  Scenario: Explicit --no-skills skips without touching existing files
    Given a repository with a previously installed skill file
    When the user runs `planhub init --no-skills`
    Then the existing skill file is left unchanged
    And the user is not prompted

  Scenario: Omitted flag in an interactive shell prompts for confirmation
    Given a TTY-attached shell and no `--skills`/`--no-skills` flag
    When the user runs `planhub init` and confirms the prompt
    Then the skill files are installed

  Scenario: Omitted flag in a non-interactive shell skips silently
    Given stdin is not a TTY and no `--skills`/`--no-skills` flag
    When the user runs `planhub init`
    Then no skill files are written
    And no prompt is shown

  Scenario: Re-running with --skills refreshes changed content
    Given an installed skill file whose content differs from the current bundled template
    When the user runs `planhub init --skills`
    Then the file is overwritten with the bundled template content

  Scenario: Re-running with --skills leaves up-to-date files untouched
    Given an installed skill file whose content already matches the current bundled template
    When the user runs `planhub init --skills`
    Then the file is not rewritten
