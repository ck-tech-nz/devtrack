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
        f = SimpleUploadedFile("malware.exe", b"MZ", content_type="application/x-msdownload")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "类型" in response.data["detail"]

    def test_oversized_file_returns_400(self, auth_client):
        f = SimpleUploadedFile("big.png", b"x" * (21 * 1024 * 1024), content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "大小" in response.data["detail"]

    @patch("apps.tools.storage.upload_image")
    def test_valid_upload_returns_id_url_filename(self, mock_upload, auth_client):
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
        assert "id" in response.data
        assert Attachment.objects.filter(file_url=response.data["url"]).exists()

    @patch("apps.tools.storage.upload_image")
    def test_pdf_upload_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.pdf",
            "2026/04/29/abc.pdf",
        )
        f = SimpleUploadedFile("report.pdf", b"%PDF-1.4\n%test", content_type="application/pdf")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
        assert response.data["filename"] == "report.pdf"

    @patch("apps.tools.storage.upload_image")
    def test_docx_upload_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.docx",
            "2026/04/29/abc.docx",
        )
        f = SimpleUploadedFile(
            "spec.docx",
            b"PK\x03\x04",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200

    @patch("apps.tools.storage.upload_image")
    def test_zip_upload_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.zip",
            "2026/04/29/abc.zip",
        )
        f = SimpleUploadedFile("bundle.zip", b"PK\x03\x04", content_type="application/zip")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200

    @patch("apps.tools.storage.upload_image")
    def test_markdown_with_textplain_succeeds(self, mock_upload, auth_client):
        """Some browsers report .md files as text/plain — allow if extension matches."""
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.md",
            "2026/04/29/abc.md",
        )
        f = SimpleUploadedFile("notes.md", b"# Hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200

    @patch("apps.tools.storage.upload_image")
    def test_plain_txt_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.txt",
            "2026/04/29/abc.txt",
        )
        f = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
