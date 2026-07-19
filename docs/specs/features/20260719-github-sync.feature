Feature: GitHub sync
  Keep local .plan Markdown artifacts and GitHub Issues/Milestones aligned.

  # Related spec: docs/specs/20260719-github-sync.md

  Scenario: Dry-run validates without writing planned creates
    Given an initialized `.plan` layout with a new local issue without a number
    And valid GitHub credentials
    When the user runs `planhub sync --dry-run`
    Then the CLI reports planned create counts
    And no GitHub issue is created
    And local files are not updated with a GitHub number from that plan apply

  Scenario: Sync creates a GitHub issue and writes back the number
    Given a local root issue file without `number`
    And valid GitHub credentials for the repository remote
    When the user runs `planhub sync`
    Then a GitHub issue is created from the local title and body
    And the local front matter gains the GitHub `number`

  Scenario: Sync reconciles issue state from GitHub
    Given a synced local issue file with `state: open`
    And the matching GitHub issue is closed
    When the user runs `planhub sync`
    Then the local front matter `state` becomes `closed`
    And sync does not reopen the GitHub issue based on the stale local state

  Scenario: Closed root issues are archived by default
    Given a synced root issue with `state: closed` and a GitHub `number`
    And `sync.closed_issues.policy` is `archive`
    When the user runs `planhub sync`
    Then the issue file is moved under `.plan/archive/issues`

  Scenario: Closed milestones move as whole directories
    Given a milestone directory under `.plan/milestones/<slug>`
    And its `milestone.md` has `state: closed` after GitHub reconciliation
    When the user runs `planhub sync`
    Then the directory is moved to `.plan/archive/milestones/<slug>`
    And milestone issues remain inside that directory
