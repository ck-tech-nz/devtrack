import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.repos.models import Commit, GitAuthorAlias
from tests.factories import RepoFactory, UserFactory

pytestmark = pytest.mark.django_db


def _seed(repo, email="dev@test.com", name="Dev", count=3):
    for i in range(count):
        Commit.objects.create(
            repo=repo,
            hash=f"{email[:3]}{i:037d}",
            author_email=email,
            author_name=name,
            date=timezone.now() - timedelta(days=i),
            message=f"feat: commit {i}",
            additions=10 * (i + 1),
            deletions=5 * (i + 1),
            files_changed=[f"src/mod{i}/file.py"],
        )
    GitAuthorAlias.objects.get_or_create(
        repo=repo, author_email=email, defaults={"author_name": name}
    )


class TestDeveloperInsightsListAPI:
    def test_returns_developer_list(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo, "a@test.com", "Alice", 5)
        _seed(repo, "b@test.com", "Bob", 3)
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/")
        assert response.status_code == 200
        assert len(response.data["developers"]) == 2
        assert "scores" in response.data["developers"][0]

    def test_days_filter(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/?days=30")
        assert response.status_code == 200

    def test_includes_unlinked_authors(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/")
        assert "unlinked_count" in response.data

    def test_unauthenticated(self, api_client):
        repo = RepoFactory()
        response = api_client.get(f"/api/repos/{repo.id}/developer-insights/")
        assert response.status_code == 401


class TestDeveloperInsightsDetailAPI:
    def test_returns_individual_detail(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        alias = GitAuthorAlias.objects.first()
        response = auth_client.get(
            f"/api/repos/{repo.id}/developer-insights/{alias.id}/"
        )
        assert response.status_code == 200
        assert "scores" in response.data
        assert "details" in response.data

    def test_404_for_wrong_alias(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/99999/")
        assert response.status_code == 404


class TestSyncCommitsAPI:
    def test_sync_commits_endpoint(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        with patch("apps.repos.views.RepoCloneService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            response = auth_client.post(f"/api/repos/{repo.id}/sync-commits/")
        assert response.status_code == 200
        mock_instance.sync_commits.assert_called_once()

    def test_sync_404_not_cloned(self, auth_client):
        repo = RepoFactory(clone_status="not_cloned")
        response = auth_client.post(f"/api/repos/{repo.id}/sync-commits/")
        assert response.status_code == 400


class TestGitAuthorAliasPatchAPI:
    def test_link_user(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        alias = GitAuthorAlias.objects.first()
        user = UserFactory()
        response = auth_client.patch(
            f"/api/repos/{repo.id}/git-author-aliases/{alias.id}/",
            {"user": user.id},
            format="json",
        )
        assert response.status_code == 200
        alias.refresh_from_db()
        assert alias.user == user

    def test_unlink_user(self, auth_client):
        user = UserFactory()
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        alias = GitAuthorAlias.objects.first()
        alias.user = user
        alias.save()
        response = auth_client.patch(
            f"/api/repos/{repo.id}/git-author-aliases/{alias.id}/",
            {"user": None},
            format="json",
        )
        assert response.status_code == 200
        alias.refresh_from_db()
        assert alias.user is None
