from unittest.mock import patch

from typer.testing import CliRunner

from planhub.cli.app import app
from planhub.documents import load_issue_document, load_milestone_document
from planhub.layout import ensure_layout


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_creates_missing_issue_and_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.create_milestone.return_value = {"number": 7}
    client_instance.create_issue.return_value = {"number": 21, "state": "open"}

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\n---\n\nMilestone body\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    issue_path = issues_dir / "issue-001.md"
    issue_path.write_text(
        '---\ntitle: "Ship it"\nstate: "closed"\n---\n\nIssue body\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    milestone = load_milestone_document(milestone_dir / "milestone.md")
    issue = load_issue_document(issue_path)
    assert milestone.number == 7
    assert issue.number == 21
    assert issue.state is not None
    assert issue.state.value == "open"
    client_instance.update_issue_state.assert_not_called()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_updates_existing_issue(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "closed", "state_reason": "completed"}

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Ship it"\nnumber: 99\nassignees: [alice]\n---\n\nBody\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    client_instance.update_issue.assert_called_once()
    kwargs = client_instance.update_issue.call_args.kwargs
    assert kwargs["state"] is None
    assert kwargs["state_reason"] is None
    archived_issue_path = tmp_path / ".plan" / "archive" / "issues" / issue_path.name
    issue = load_issue_document(archived_issue_path)
    assert issue.state is not None
    assert issue.state.value == "closed"
    assert issue.state_reason is not None
    assert issue.state_reason.value == "completed"


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_ignores_unknown_state_reason_from_github(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "closed", "state_reason": "foo"}

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        '---\ntitle: "Ship it"\nnumber: 99\n---\n\nBody\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    archived_issue_path = tmp_path / ".plan" / "archive" / "issues" / issue_path.name
    issue = load_issue_document(archived_issue_path)
    assert issue.state is not None
    assert issue.state.value == "closed"
    assert issue.state_reason is None


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_clears_labels_assignees_and_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "open"}

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "labels: []",
                "assignees: []",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    kwargs = client_instance.update_issue.call_args.kwargs
    assert kwargs["labels"] == []
    assert kwargs["assignees"] == []
    assert "milestone" not in kwargs
    assert "clear_milestone" not in kwargs


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_moves_root_issue_to_github_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1", "number": 7},
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 7\n---\n',
        encoding="utf-8",
    )
    (milestone_dir / "issues").mkdir(parents=True, exist_ok=True)

    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                # Simulate drift locally; placement will be reconciled from GitHub.
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    kwargs = client_instance.update_issue.call_args.kwargs
    assert "milestone" not in kwargs
    assert "clear_milestone" not in kwargs

    moved_issue_path = milestone_dir / "issues" / issue_path.name
    assert moved_issue_path.exists()
    assert not issue_path.exists()

    moved_issue = load_issue_document(moved_issue_path)
    assert moved_issue.milestone_set is True
    assert moved_issue.milestone_number == 7


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_moves_milestone_issue_back_to_root_if_github_removes_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": None,
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 7\n---\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    issue_path = issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: " + '"Stage 1"',
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    kwargs = client_instance.update_issue.call_args.kwargs
    assert "milestone" not in kwargs
    assert "clear_milestone" not in kwargs

    moved_issue_path = layout.issues_dir / issue_path.name
    assert moved_issue_path.exists()
    assert not issue_path.exists()

    moved_issue = load_issue_document(moved_issue_path)
    assert moved_issue.milestone_set is True
    assert moved_issue.milestone is None


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_create_uses_config_defaults_for_unset_labels_and_assignees(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.create_issue.return_value = {"number": 21, "state": "open"}

    (tmp_path / ".plan").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".plan" / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  github:",
                "    default_labels: [bug, backend]",
                "    default_assignees: [alice, bob]",
            ]
        ),
        encoding="utf-8",
    )

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue-001.md"
    issue_path.write_text('---\ntitle: "Ship it"\n---\n\nIssue body\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    kwargs = client_instance.create_issue.call_args.kwargs
    assert kwargs["labels"] == ["bug", "backend"]
    assert kwargs["assignees"] == ["alice", "bob"]


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_update_uses_config_defaults_for_unset_labels_and_assignees(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {"state": "open"}

    (tmp_path / ".plan").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".plan" / "config.yaml").write_text(
        "\n".join(
            [
                "sync:",
                "  github:",
                "    default_labels: [bug, backend]",
                "    default_assignees: [alice, bob]",
            ]
        ),
        encoding="utf-8",
    )

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue-001.md"
    issue_path.write_text(
        '---\ntitle: "Ship it"\nnumber: 99\n---\n\nIssue body\n', encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    kwargs = client_instance.update_issue.call_args.kwargs
    assert kwargs["labels"] == ["bug", "backend"]
    assert kwargs["assignees"] == ["alice", "bob"]


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_does_not_move_if_issue_already_in_target_milestone(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1", "number": 7},
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 7\n---\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    issue_path = issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: 7",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert issue_path.exists()
    assert not (layout.issues_dir / issue_path.name).exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_creates_missing_milestone_dir_from_github(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1", "number": 7},
    }

    layout = ensure_layout(tmp_path)
    # Ensure milestone dir is missing initially.
    assert not (layout.milestones_dir / "stage-1").exists()

    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0

    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_doc = load_milestone_document(milestone_dir / "milestone.md")
    assert milestone_doc.number == 7

    moved_issue_path = milestone_dir / "issues" / issue_path.name
    assert moved_issue_path.exists()
    assert not issue_path.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_creates_milestone_md_with_details_from_github(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {
            "title": "Stage 1",
            "number": 7,
            "description": "Milestone description",
            "due_on": "2026-03-27T12:00:00Z",
            "state": "open",
        },
    }

    layout = ensure_layout(tmp_path)
    assert not (layout.milestones_dir / "stage-1").exists()

    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0

    milestone_dir = layout.milestones_dir / "stage-1"
    moved_issue_path = milestone_dir / "issues" / issue_path.name
    assert moved_issue_path.exists()

    milestone_doc = load_milestone_document(milestone_dir / "milestone.md")
    assert milestone_doc.title == "Stage 1"
    assert milestone_doc.number == 7
    assert milestone_doc.description == "Milestone description"
    assert milestone_doc.due_on == "2026-03-27T12:00:00Z"


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_does_not_overwrite_existing_milestone_md(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {
            "title": "Stage 1",
            "number": 7,
            "description": "New description from GitHub",
        },
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "issues").mkdir(parents=True, exist_ok=True)
    milestone_md_path = milestone_dir / "milestone.md"
    milestone_md_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Stage 1"',
                "number: 999",
                'description: "Local description"',
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    original_text = milestone_md_path.read_text(encoding="utf-8")

    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0

    moved_issue_path = milestone_dir / "issues" / issue_path.name
    assert moved_issue_path.exists()
    assert not issue_path.exists()

    # Milestone doc should remain unchanged if it already exists locally.
    assert milestone_md_path.read_text(encoding="utf-8") == original_text


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_slugifies_milestone_title_for_folder_name(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1 / Q2", "number": 7},
    }

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    milestone_dir = layout.milestones_dir / "stage-1-q2"
    assert milestone_dir.exists()
    moved_issue_path = milestone_dir / "issues" / issue_path.name
    assert moved_issue_path.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_milestone_when_title_missing_uses_number_slug(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "", "number": 7},
    }

    layout = ensure_layout(tmp_path)
    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    milestone_dir = layout.milestones_dir / "7"
    assert milestone_dir.exists()
    moved_issue_path = milestone_dir / "issues" / issue_path.name
    assert moved_issue_path.exists()
    moved_issue = load_issue_document(moved_issue_path)
    assert moved_issue.milestone_set is True
    assert moved_issue.milestone_number == 7


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_milestone_number_as_string_uses_title_in_front_matter(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1", "number": "7"},
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 7\n---\n',
        encoding="utf-8",
    )
    (milestone_dir / "issues").mkdir(parents=True, exist_ok=True)

    issue_path = layout.issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    moved_issue_path = milestone_dir / "issues" / issue_path.name
    moved_issue = load_issue_document(moved_issue_path)
    assert moved_issue.milestone_set is True
    assert moved_issue.milestone == "Stage 1"
    assert moved_issue.milestone_number is None


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_moves_multiple_issues_to_distinct_milestones(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value

    def update_issue_side_effect(owner: str, repo: str, number: int, **_: object) -> dict:
        if number == 1:
            return {"state": "open", "milestone": {"title": "Stage 1", "number": 7}}
        if number == 2:
            return {"state": "open", "milestone": {"title": "Stage 2", "number": 8}}
        raise AssertionError(f"Unexpected issue number: {number}")

    client_instance.update_issue.side_effect = update_issue_side_effect

    layout = ensure_layout(tmp_path)
    for milestone_title, milestone_slug, milestone_number in [
        ("Stage 1", "stage-1", 7),
        ("Stage 2", "stage-2", 8),
    ]:
        milestone_dir = layout.milestones_dir / milestone_slug
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (milestone_dir / "milestone.md").write_text(
            f'---\ntitle: "{milestone_title}"\nnumber: {milestone_number}\n---\n',
            encoding="utf-8",
        )
        (milestone_dir / "issues").mkdir(parents=True, exist_ok=True)

    issue1_path = layout.issues_dir / "issue1.md"
    issue1_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Issue 1"',
                "number: 1",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )
    issue2_path = layout.issues_dir / "issue2.md"
    issue2_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Issue 2"',
                "number: 2",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0

    moved1 = layout.milestones_dir / "stage-1" / "issues" / issue1_path.name
    moved2 = layout.milestones_dir / "stage-2" / "issues" / issue2_path.name
    assert moved1.exists()
    assert moved2.exists()
    assert not issue1_path.exists()
    assert not issue2_path.exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_milestone_move_collision_adds_numeric_suffix(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": {"title": "Stage 1", "number": 7},
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 7\n---\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    # Collision target already exists in the milestone folder.
    existing_target = issues_dir / "issue.md"
    existing_target.write_text(
        '---\ntitle: "Existing"\nnumber: 50\nmilestone: 7\n---\n\nBody\n',
        encoding="utf-8",
    )

    # Source issue has the same filename.
    source_path = layout.issues_dir / "issue.md"
    source_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: null",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert not source_path.exists()
    assert existing_target.exists()
    # Moved file should get `-1` suffix.
    assert (issues_dir / "issue-1.md").exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_does_not_relocate_when_github_milestone_field_missing(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        # Note: no `milestone` key in GitHub response.
    }

    layout = ensure_layout(tmp_path)
    milestone_dir = layout.milestones_dir / "stage-1"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "milestone.md").write_text(
        '---\ntitle: "Stage 1"\nnumber: 7\n---\n',
        encoding="utf-8",
    )
    issues_dir = milestone_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    issue_path = issues_dir / "issue.md"
    issue_path.write_text(
        "\n".join(
            [
                "---",
                'title: "Ship it"',
                "number: 99",
                "milestone: 7",
                "---",
                "",
                "Body",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert issue_path.exists()
    assert not (layout.issues_dir / issue_path.name).exists()


@patch("planhub.cli.commands.sync.get_github_repo_from_git")
@patch("planhub.cli.commands.sync.get_auth_token")
@patch("planhub.cli.commands.sync.GitHubClient")
def test_sync_parallel_moves_same_filename_to_root_are_collision_safe(
    mock_client, mock_token, mock_repo, tmp_path, monkeypatch
) -> None:
    mock_token.return_value = "token"
    mock_repo.return_value = ("acme", "roadmap")
    client_instance = mock_client.return_value
    client_instance.update_issue.return_value = {
        "state": "open",
        "milestone": None,
    }

    layout = ensure_layout(tmp_path)
    for milestone_slug, number in [("stage-1", 7), ("stage-2", 8)]:
        milestone_dir = layout.milestones_dir / milestone_slug
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (milestone_dir / "milestone.md").write_text(
            f'---\ntitle: "{milestone_slug}"\nnumber: {number}\n---\n',
            encoding="utf-8",
        )
        issues_dir = milestone_dir / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        (issues_dir / "issue.md").write_text(
            "\n".join(
                [
                    "---",
                    f'title: "{milestone_slug} issue"',
                    f"number: {number}",
                    f"milestone: {number}",
                    "---",
                    "",
                    "Body",
                ]
            ),
            encoding="utf-8",
        )

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert (layout.issues_dir / "issue.md").exists()
    assert (layout.issues_dir / "issue-1.md").exists()
