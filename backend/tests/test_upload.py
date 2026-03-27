import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
class TestImageUpload:
    URL = "/api/tools/upload/image/"

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.post(self.URL)
        assert response.status_code == 401

    def test_no_file_returns_400(self, auth_client):
        response = auth_client.post(self.URL)
        assert response.status_code == 400

    def test_invalid_type_returns_400(self, auth_client):
        f = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "类型" in response.data["detail"]

    def test_oversized_file_returns_400(self, auth_client):
        f = SimpleUploadedFile("big.png", b"x" * (6 * 1024 * 1024), content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "大小" in response.data["detail"]

    @patch("apps.tools.storage.upload_image")
    def test_valid_upload_creates_attachment(self, mock_upload, auth_client):
        from apps.tools.models import Attachment
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/03/24/abc.png",
            "2026/03/24/abc.png",
        )
        f = SimpleUploadedFile("screenshot.png", b"\x89PNG" + b"\x00" * 100, content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
        assert response.data["url"] == "http://minio:9000/devtrack-uploads/2026/03/24/abc.png"
        assert response.data["filename"] == "screenshot.png"
        assert Attachment.objects.filter(file_url=response.data["url"]).exists()

    @patch("apps.tools.storage.upload_image")
    def test_upload_with_issue_links_attachment(self, mock_upload, auth_client):
        from apps.tools.models import Attachment
        from tests.factories import IssueFactory
        issue = IssueFactory()
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/03/24/def.png",
            "2026/03/24/def.png",
        )
        f = SimpleUploadedFile("photo.png", b"\x89PNG" + b"\x00" * 100, content_type="image/png")
        response = auth_client.post(
            self.URL, {"file": f, "issue_id": issue.id}, format="multipart"
        )
        assert response.status_code == 200
        assert Attachment.objects.filter(issue=issue).exists()
