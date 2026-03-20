import pytest
from tests.factories import UserFactory, ProjectFactory, ProjectMemberFactory

pytestmark = pytest.mark.django_db


class TestProjectList:
    def test_list_projects(self, auth_client):
        ProjectFactory.create_batch(3)
        response = auth_client.get("/api/projects/")
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_list_includes_member_count(self, auth_client):
        project = ProjectFactory()
        ProjectMemberFactory.create_batch(2, project=project)
        response = auth_client.get("/api/projects/")
        result = response.data["results"][0]
        assert result["member_count"] == 2


class TestProjectDetail:
    def test_get_project_detail(self, auth_client):
        project = ProjectFactory(name="测试项目")
        response = auth_client.get(f"/api/projects/{project.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "测试项目"

    def test_project_detail_includes_members(self, auth_client):
        project = ProjectFactory()
        member = ProjectMemberFactory(project=project, role="owner")
        response = auth_client.get(f"/api/projects/{project.id}/")
        assert len(response.data["members"]) == 1
        assert response.data["members"][0]["role"] == "owner"


class TestProjectCreate:
    def test_create_project(self, auth_client):
        response = auth_client.post("/api/projects/", {
            "name": "新项目",
            "description": "描述",
            "status": "进行中",
        })
        assert response.status_code == 201
        assert response.data["name"] == "新项目"


class TestProjectUpdate:
    def test_update_project(self, auth_client):
        project = ProjectFactory()
        response = auth_client.patch(f"/api/projects/{project.id}/", {
            "name": "改名了",
        })
        assert response.status_code == 200
        assert response.data["name"] == "改名了"


class TestProjectDelete:
    def test_delete_project(self, auth_client):
        project = ProjectFactory()
        response = auth_client.delete(f"/api/projects/{project.id}/")
        assert response.status_code == 204


class TestProjectMembers:
    def test_list_members(self, auth_client):
        project = ProjectFactory()
        ProjectMemberFactory(project=project, role="owner")
        response = auth_client.get(f"/api/projects/{project.id}/members/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_add_member(self, auth_client):
        project = ProjectFactory()
        user = UserFactory()
        response = auth_client.post(f"/api/projects/{project.id}/members/", {
            "user_id": str(user.id),
            "role": "member",
        })
        assert response.status_code == 201

    def test_remove_member(self, auth_client):
        project = ProjectFactory()
        member = ProjectMemberFactory(project=project)
        response = auth_client.delete(
            f"/api/projects/{project.id}/members/{member.user.id}/"
        )
        assert response.status_code == 204
