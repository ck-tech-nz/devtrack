import pytest
from tests.factories import RepoFactory

pytestmark = pytest.mark.django_db


class TestRepoList:
    def test_list_repos(self, auth_client):
        RepoFactory.create_batch(3)
        response = auth_client.get("/api/repos/")
        assert response.status_code == 200
        assert len(response.data) == 3

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/repos/")
        assert response.status_code == 401


class TestRepoDetail:
    def test_get_repo_detail(self, auth_client):
        repo = RepoFactory(name="my-repo", full_name="org/my-repo")
        response = auth_client.get(f"/api/repos/{repo.id}/")
        assert response.status_code == 200
        assert response.data["full_name"] == "org/my-repo"


class TestRepoCreate:
    def test_create_repo(self, auth_client):
        response = auth_client.post("/api/repos/", {
            "name": "new-repo",
            "full_name": "org/new-repo",
            "url": "https://github.com/org/new-repo",
            "description": "A new repo",
            "default_branch": "main",
            "language": "Python",
            "stars": 0,
        })
        assert response.status_code == 201
        assert response.data["name"] == "new-repo"


class TestRepoDelete:
    def test_delete_repo(self, auth_client):
        repo = RepoFactory()
        response = auth_client.delete(f"/api/repos/{repo.id}/")
        assert response.status_code == 204
