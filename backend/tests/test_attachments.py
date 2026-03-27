import pytest
from tests.factories import UserFactory, IssueFactory


@pytest.mark.django_db
class TestAttachmentModel:
    def test_attachment_str(self):
        from apps.tools.models import Attachment
        from tests.factories import AttachmentFactory
        a = AttachmentFactory(file_name="screenshot.png")
        assert str(a) == "screenshot.png"

    def test_is_image_true(self):
        from apps.tools.models import Attachment
        from tests.factories import AttachmentFactory
        a = AttachmentFactory(mime_type="image/png")
        assert a.is_image is True

    def test_is_image_false(self):
        from apps.tools.models import Attachment
        from tests.factories import AttachmentFactory
        a = AttachmentFactory(mime_type="application/pdf")
        assert a.is_image is False
