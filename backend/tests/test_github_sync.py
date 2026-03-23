import pytest
from unittest.mock import patch, MagicMock
from tests.factories import RepoFactory


@pytest.mark.django_db
def test_repo_has_new_fields():
    repo = RepoFactory(github_token="ghp_test", last_synced_at=None)
    assert repo.github_token == "ghp_test"
    assert repo.last_synced_at is None


@pytest.mark.django_db
def test_github_issue_creation(repo_with_token):
    from apps.repos.models import GitHubIssue
    from django.utils import timezone

    issue = GitHubIssue.objects.create(
        repo=repo_with_token,
        github_id=1,
        title="Fix bug",
        body="Description",
        state="open",
        labels=["bug"],
        assignees=["alice"],
        github_created_at=timezone.now(),
        github_updated_at=timezone.now(),
        synced_at=timezone.now(),
    )
    assert issue.github_id == 1
    assert issue.labels == ["bug"]


@pytest.mark.django_db
def test_github_issue_unique_together(repo_with_token):
    from apps.repos.models import GitHubIssue
    from django.utils import timezone
    from django.db import IntegrityError

    kwargs = dict(
        repo=repo_with_token, github_id=42, title="A",
        state="open", github_created_at=timezone.now(),
        github_updated_at=timezone.now(), synced_at=timezone.now(),
    )
    GitHubIssue.objects.create(**kwargs)
    with pytest.raises(IntegrityError):
        GitHubIssue.objects.create(**kwargs)


def make_api_issue(number=1, updated_at="2026-01-01T00:00:00Z"):
    return {
        "number": number,
        "title": f"Issue #{number}",
        "body": "Body",
        "state": "open",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "alice"}],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": updated_at,
        "closed_at": None,
    }


@pytest.mark.django_db
def test_sync_repo_creates_issues():
    from apps.repos.services import GitHubSyncService
    from apps.repos.models import GitHubIssue

    repo = RepoFactory(github_token="ghp_test")
    with patch("apps.repos.services.requests.get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: [make_api_issue(1)]),
            MagicMock(status_code=200, json=lambda: []),
        ]
        GitHubSyncService().sync_repo(repo)

    assert GitHubIssue.objects.filter(repo=repo).count() == 1
    issue = GitHubIssue.objects.get(repo=repo, github_id=1)
    assert issue.labels == ["bug"]
    assert issue.assignees == ["alice"]
    repo.refresh_from_db()
    assert repo.last_synced_at is not None


@pytest.mark.django_db
def test_sync_repo_skips_unchanged_issues():
    from apps.repos.services import GitHubSyncService
    from tests.factories import GitHubIssueFactory

    repo = RepoFactory(github_token="ghp_test")
    from datetime import datetime, timezone as dt_tz
    existing = GitHubIssueFactory(
        repo=repo, github_id=1, title="Old Title",
        github_updated_at=datetime(2026, 1, 1, tzinfo=dt_tz.utc),
    )
    with patch("apps.repos.services.requests.get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: [make_api_issue(1, "2026-01-01T00:00:00Z")]),
            MagicMock(status_code=200, json=lambda: []),
        ]
        GitHubSyncService().sync_repo(repo)

    existing.refresh_from_db()
    assert existing.title == "Old Title"


@pytest.mark.django_db
def test_sync_all_skips_repos_without_token():
    from apps.repos.services import GitHubSyncService

    RepoFactory(github_token="")
    repo_with_token = RepoFactory(github_token="ghp_test")

    with patch.object(GitHubSyncService, "sync_repo") as mock_sync:
        GitHubSyncService().sync_all()

    assert mock_sync.call_count == 1
    assert mock_sync.call_args[0][0] == repo_with_token
