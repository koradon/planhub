Feature: Layered configuration and setup
  Load global and repository config overlays and create defaults on demand.

  # Related spec: docs/specs/20260719-layered-configuration.md (superseded by
  # docs/specs/20260728-interactive-config-prompts.md — see ADR-0007). The
  # global config layer and `planhub setup` no longer exist; the three
  # scenarios below are kept as history, not current behavior. "Unknown
  # config keys are rejected" is unrelated to layering and still current.

  Scenario: Repository config overrides global closed-issue policy
    Given a global config with `sync.closed_issues.policy: archive`
    And a repository config with `sync.closed_issues.policy: delete`
    When Planhub loads config for that repository
    Then the effective policy is `delete`

  Scenario: Setup creates missing global config
    Given `~/.planhub/config.yaml` does not exist
    When the user runs `planhub setup`
    Then the global config file is created with defaults

  Scenario: Setup dry-run does not create files
    Given `~/.planhub/config.yaml` does not exist
    When the user runs `planhub setup --dry-run`
    Then the CLI reports the path that would be created
    And the file is not written

  Scenario: Unknown config keys are rejected
    Given a repository config containing an unknown top-level key
    When Planhub loads config
    Then loading fails with a ConfigError that names the unknown key
