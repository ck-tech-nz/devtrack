import pytest
from unittest.mock import patch, MagicMock
from apps.repos.models import Commit, GitAuthorAlias
from apps.repos.services import RepoCloneService
from tests.factories import RepoFactory, UserFactory

pytestmark = pytest.mark.django_db

_H1 = "abc1234567890abcdef1234567890abcdef12345"
_H2 = "def7890abcdef1234567890abcdef12345678901"
_H3 = "1111111111111111111111111111111111111111"

GIT_LOG_OUTPUT = (
    f"{_H1}\x00dev@example.com\x00Dev One\x002026-03-30T10:00:00+08:00\x00feat(ui): add dashboard\n"
    " src/ui/dashboard.vue | 80 ++++++\n"
    " src/ui/sidebar.vue   | 30 +++\n"
    " src/api/routes.py    | 40 ++--\n"
    " 3 files changed, 120 insertions(+), 30 deletions(-)\n"
    "\n"
    f"{_H2}\x00dev@example.com\x00Dev One\x002026-03-29T09:00:00+08:00\x00fix(api): resolve 500 error\n"
    " src/api/views.py | 7 +++--\n"
    " 1 file changed, 5 insertions(+), 2 deletions(-)\n"
    "\n"
    f"{_H3}\x00other@test.com\x00Other Dev\x002026-03-28T08:00:00+08:00\x00chore: update deps\n"
    " requirements.txt | 10 ++++----\n"
    " package.json     | 8 +++---\n"
    " 2 files changed, 10 insertions(+), 8 deletions(-)\n"
    "\n"
)


class TestSyncCommits:
    def test_creates_commits_and_aliases(self):
        repo = RepoFactory(clone_status="cloned", full_name="org/my-repo")

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            if any(str(c).startswith("--format") for c in cmd):
                mock.stdout = GIT_LOG_OUTPUT
            else:
                mock.stdout = ""
            return mock

        with patch("apps.repos.services.subprocess.run", side_effect=fake_run):
            with patch("apps.repos.services.os.path.exists", return_value=True):
                RepoCloneService().sync_commits(repo)

        assert Commit.objects.filter(repo=repo).count() == 3
        assert GitAuthorAlias.objects.filter(repo=repo).count() == 2

        c1 = Commit.objects.get(repo=repo, hash=_H1)
        assert c1.author_email == "dev@example.com"
        assert c1.message == "feat(ui): add dashboard"
        assert c1.additions == 120
        assert c1.deletions == 30

    def test_skips_existing_commits(self):
        repo = RepoFactory(clone_status="cloned", full_name="org/my-repo-2")
        Commit.objects.create(
            repo=repo, hash=_H1,
            author_name="Dev One", author_email="dev@example.com",
            date="2026-03-30T10:00:00+08:00", message="feat(ui): add dashboard",
        )

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = GIT_LOG_OUTPUT
            return mock

        with patch("apps.repos.services.subprocess.run", side_effect=fake_run):
            with patch("apps.repos.services.os.path.exists", return_value=True):
                RepoCloneService().sync_commits(repo)

        assert Commit.objects.filter(repo=repo).count() == 3

    def test_auto_matches_user_by_email(self):
        user = UserFactory(email="dev@example.com")
        repo = RepoFactory(clone_status="cloned", full_name="org/my-repo-3")

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = GIT_LOG_OUTPUT
            return mock

        with patch("apps.repos.services.subprocess.run", side_effect=fake_run):
            with patch("apps.repos.services.os.path.exists", return_value=True):
                RepoCloneService().sync_commits(repo)

        alias = GitAuthorAlias.objects.get(repo=repo, author_email="dev@example.com")
        assert alias.user == user
