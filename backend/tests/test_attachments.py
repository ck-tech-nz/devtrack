import pytest
from tests.factories import AttachmentFactory


@pytest.mark.django_db
class TestAttachmentModel:
    def test_attachment_str(self):
        a = AttachmentFactory(file_name="screenshot.png")
        assert str(a) == "screenshot.png"

    def test_is_image_true(self):
        a = AttachmentFactory(mime_type="image/png")
        assert a.is_image is True

    def test_is_image_false(self):
        a = AttachmentFactory(mime_type="application/pdf")
        assert a.is_image is False

    def test_attachment_survives_user_deletion(self):
        """uploaded_by SET_NULL: deleting user keeps attachment, nulls uploaded_by"""
        from tests.factories import UserFactory
        from apps.tools.models import Attachment
        user = UserFactory()
        a = AttachmentFactory(uploaded_by=user)
        user.delete()
        a.refresh_from_db()
        assert a.uploaded_by is None

    def test_attachment_deleted_with_issue(self):
        """issue CASCADE: deleting issue deletes all its attachments"""
        from tests.factories import IssueFactory
        from apps.tools.models import Attachment
        issue = IssueFactory()
        AttachmentFactory(issue=issue)
        AttachmentFactory(issue=issue)
        issue.delete()
        assert not Attachment.objects.filter(issue_id=issue.pk).exists()


@pytest.mark.django_db
class TestAttachmentSync:
    def test_create_issue_links_matching_attachments(self, auth_client, auth_user, site_settings, settings):
        from apps.tools.models import Attachment
        from tests.factories import ProjectFactory, AttachmentFactory
        settings.MINIO_PUBLIC_URL = "http://minio:9000"
        user = auth_user
        project = ProjectFactory()
        att = AttachmentFactory(
            issue=None,
            uploaded_by=user,
            file_url="http://minio:9000/devtrack-uploads/2026/03/27/abc.png",
        )
        description = "截图: ![img](http://minio:9000/devtrack-uploads/2026/03/27/abc.png)"
        response = auth_client.post("/api/issues/", {
            "project": project.id,
            "title": "测试问题",
            "description": description,
            "priority": "P1",
            "status": "待处理",
            "labels": [],
        }, format="json")
        assert response.status_code == 201
        att.refresh_from_db()
        assert att.issue_id == response.data["id"]

    def test_detail_response_includes_attachments(self, auth_client, site_settings):
        from tests.factories import IssueFactory, AttachmentFactory
        issue = IssueFactory()
        AttachmentFactory(issue=issue)
        AttachmentFactory(issue=issue)
        response = auth_client.get(f"/api/issues/{issue.id}/")
        assert response.status_code == 200
        assert len(response.data["attachments"]) == 2

    def test_update_issue_links_new_attachments(self, auth_client, auth_user, site_settings, settings):
        from apps.tools.models import Attachment
        from tests.factories import IssueFactory, AttachmentFactory
        settings.MINIO_PUBLIC_URL = "http://minio:9000"
        user = auth_user
        issue = IssueFactory()
        att = AttachmentFactory(
            issue=None,
            uploaded_by=user,
            file_url="http://minio:9000/devtrack-uploads/2026/03/27/xyz.png",
        )
        response = auth_client.patch(f"/api/issues/{issue.id}/", {
            "description": "更新: ![img](http://minio:9000/devtrack-uploads/2026/03/27/xyz.png)",
        }, format="json")
        assert response.status_code == 200
        att.refresh_from_db()
        assert att.issue_id == issue.id


@pytest.mark.django_db
class TestAttachmentDeleteAPI:
    def test_delete_attachment_removes_from_db_and_calls_minio(self, auth_client, auth_user):
        from unittest.mock import patch
        from tests.factories import AttachmentFactory
        from apps.tools.models import Attachment
        att = AttachmentFactory(uploaded_by=auth_user, file_key="2026/03/27/test.png")

        with patch("apps.tools.storage.delete_object") as mock_del:
            response = auth_client.delete(f"/api/tools/attachments/{att.id}/")
        assert response.status_code == 204
        mock_del.assert_called_once_with("2026/03/27/test.png")
        assert not Attachment.objects.filter(id=att.id).exists()

    def test_delete_forbidden_for_other_user(self, auth_client):
        from tests.factories import AttachmentFactory, UserFactory
        other_user = UserFactory()
        att = AttachmentFactory(uploaded_by=other_user)
        response = auth_client.delete(f"/api/tools/attachments/{att.id}/")
        assert response.status_code == 403

    def test_delete_nonexistent_returns_404(self, auth_client):
        import uuid
        response = auth_client.delete(f"/api/tools/attachments/{uuid.uuid4()}/")
        assert response.status_code == 404

    def test_staff_can_delete_others_attachment(self, superuser_client):
        from unittest.mock import patch
        from tests.factories import AttachmentFactory, UserFactory
        from apps.tools.models import Attachment
        owner = UserFactory()
        att = AttachmentFactory(uploaded_by=owner, file_key="2026/03/27/staff.png")

        with patch("apps.tools.storage.delete_object") as mock_del:
            response = superuser_client.delete(f"/api/tools/attachments/{att.id}/")
        assert response.status_code == 204
        mock_del.assert_called_once_with("2026/03/27/staff.png")
        assert not Attachment.objects.filter(id=att.id).exists()

    def test_unauthenticated_delete_rejected(self, api_client):
        from tests.factories import AttachmentFactory
        att = AttachmentFactory()
        response = api_client.delete(f"/api/tools/attachments/{att.id}/")
        assert response.status_code == 401
