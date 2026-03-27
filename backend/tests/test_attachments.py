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
