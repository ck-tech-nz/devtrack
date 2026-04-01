import pytest
from datetime import timedelta
from django.utils import timezone
from apps.repos.insights import DeveloperInsightsService
from apps.repos.models import Commit, GitAuthorAlias
from tests.factories import RepoFactory, UserFactory

pytestmark = pytest.mark.django_db


def _create_commits(repo, author_email, author_name, messages, base_date=None):
    """Helper to create commits for a given author."""
    if base_date is None:
        base_date = timezone.now()
    commits = []
    for i, msg in enumerate(messages):
        commits.append(Commit(
            repo=repo,
            hash=f"{author_email[:4]}{i:036d}",
            author_email=author_email,
            author_name=author_name,
            date=base_date - timedelta(days=i),
            message=msg,
            additions=50 + i * 10,
            deletions=10 + i * 5,
            files_changed=[f"src/module{i % 3}/file{i}.py"],
        ))
    Commit.objects.bulk_create(commits)


class TestDeveloperInsightsService:
    def test_team_overview_returns_all_authors(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", ["feat: add login", "fix: typo"])
        _create_commits(repo, "b@test.com", "Bob", ["feat: add dashboard"])
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")
        GitAuthorAlias.objects.create(repo=repo, author_email="b@test.com", author_name="Bob")

        result = DeveloperInsightsService().team_overview(repo, days=90)
        assert len(result) == 2
        emails = [r["author_email"] for r in result]
        assert "a@test.com" in emails
        assert "b@test.com" in emails

    def test_scores_are_0_to_100(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", [
            "feat: one", "fix: two", "refactor: three", "chore: four", "docs: five"
        ])
        _create_commits(repo, "b@test.com", "Bob", ["feat: only one"])
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")
        GitAuthorAlias.objects.create(repo=repo, author_email="b@test.com", author_name="Bob")

        result = DeveloperInsightsService().team_overview(repo, days=90)
        for dev in result:
            for dim in ["contribution", "efficiency", "capability", "quality"]:
                score = dev["scores"][dim]
                assert 0 <= score <= 100, f"{dev['author_name']}.{dim} = {score}"

    def test_single_developer_gets_50(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "solo@test.com", "Solo", ["feat: init", "fix: bug"])
        GitAuthorAlias.objects.create(repo=repo, author_email="solo@test.com", author_name="Solo")

        result = DeveloperInsightsService().team_overview(repo, days=90)
        assert len(result) == 1
        for dim in ["contribution", "efficiency", "capability", "quality"]:
            assert result[0]["scores"][dim] == 50

    def test_individual_detail(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", [
            "feat(ui): login page", "fix(api): auth error", "refactor: cleanup"
        ])
        alias = GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")

        result = DeveloperInsightsService().individual_detail(repo, alias.id, days=90)
        assert result["author_name"] == "Alice"
        assert "scores" in result
        assert "details" in result
        assert "commit_types" in result["details"]

    def test_days_filter(self):
        repo = RepoFactory(clone_status="cloned")
        now = timezone.now()
        Commit.objects.create(
            repo=repo, hash="a" * 40, author_email="a@test.com", author_name="Alice",
            date=now - timedelta(days=5), message="feat: recent", additions=10, deletions=5,
        )
        Commit.objects.create(
            repo=repo, hash="b" * 40, author_email="a@test.com", author_name="Alice",
            date=now - timedelta(days=100), message="feat: old", additions=10, deletions=5,
        )
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")

        result = DeveloperInsightsService().team_overview(repo, days=30)
        assert result[0]["stats"]["commit_count"] == 1

    def test_unlinked_authors_returned(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", ["feat: one"])
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")
        user = UserFactory(email="b@test.com")
        _create_commits(repo, "b@test.com", "Bob", ["feat: two"])
        GitAuthorAlias.objects.create(repo=repo, author_email="b@test.com", author_name="Bob", user=user)

        service = DeveloperInsightsService()
        unlinked = service.unlinked_authors(repo)
        assert len(unlinked) == 1
        assert unlinked[0]["author_email"] == "a@test.com"
