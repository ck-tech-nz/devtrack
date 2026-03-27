import pytest
from unittest.mock import patch, MagicMock
from apps.repos.services import RepoCloneService
from tests.factories import RepoFactory

MOCK_CLONE_DIR = "/tmp/test_repos"


@pytest.fixture(autouse=True)
def set_clone_dir(settings):
    settings.REPO_CLONE_DIR = MOCK_CLONE_DIR


@pytest.mark.django_db
class TestRepoCloneService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.svc = RepoCloneService()
        self.repo = RepoFactory(full_name="myorg/myrepo", github_token="ghp_test123")

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=False)
    @patch("apps.repos.services.os.makedirs")
    def test_clone_new_repo(self, mock_makedirs, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.svc.clone_or_pull(self.repo)
        self.repo.refresh_from_db()
        assert self.repo.clone_status == "cloned"
        assert self.repo.cloned_at is not None
        assert self.repo.clone_error == ""

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_pull_existing_repo(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.repo.clone_status = "cloned"
        self.repo.save()
        self.svc.clone_or_pull(self.repo)
        self.repo.refresh_from_db()
        assert self.repo.clone_status == "cloned"

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=False)
    @patch("apps.repos.services.os.makedirs")
    def test_clone_failure_sets_failed_status(self, mock_makedirs, mock_exists, mock_subprocess):
        mock_subprocess.run.side_effect = Exception("fatal: auth failed")
        self.svc.clone_or_pull(self.repo)
        self.repo.refresh_from_db()
        assert self.repo.clone_status == "failed"
        assert "fatal: auth failed" in self.repo.clone_error

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_switch_branch(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.repo.clone_status = "cloned"
        self.repo.save()
        self.svc.clone_or_pull(self.repo, branch="develop")
        self.repo.refresh_from_db()
        assert self.repo.current_branch == "develop"

    def test_local_path_validation_rejects_traversal(self):
        repo = RepoFactory(full_name="../etc/passwd")
        with pytest.raises(ValueError):
            _ = repo.local_path

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_get_log(self, mock_exists, mock_subprocess):
        log_output = (
            "abc123\x00Alice\x002026-03-25T10:00:00+08:00\x00fix bug\n"
            "abc456\x00Bob\x002026-03-24T09:00:00+08:00\x00add feature"
        )
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=log_output, stderr=""
        )
        result = self.svc.get_log(self.repo, limit=2)
        assert len(result) == 2
        assert result[0]["hash"] == "abc123"
        assert result[0]["author"] == "Alice"
        assert result[0]["message"] == "fix bug"

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_get_branches(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="origin/main\norigin/develop\norigin/feature/x",
            stderr="",
        )
        result = self.svc.get_branches(self.repo)
        assert "origin/main" in result
        assert len(result) == 3
