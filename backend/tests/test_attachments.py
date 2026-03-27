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
    def test_create_issue_links_matching_attachments(self, auth_client, site_settings, settings):
        from apps.tools.models import Attachment
        from tests.factories import ProjectFactory, AttachmentFactory
        from django.contrib.auth import get_user_model
        settings.MINIO_PUBLIC_URL = "http://minio:9000"
        User = get_user_model()
        # auth_client fixture creates a user last — grab it
        user = User.objects.order_by("-date_joined").first()
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

    def test_update_issue_links_new_attachments(self, auth_client, site_settings, settings):
        from apps.tools.models import Attachment
        from tests.factories import IssueFactory, AttachmentFactory
        from django.contrib.auth import get_user_model
        settings.MINIO_PUBLIC_URL = "http://minio:9000"
        User = get_user_model()
        user = User.objects.order_by("-date_joined").first()
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
