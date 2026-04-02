import pytest
from unittest.mock import patch
from apps.settings.models import DatabaseBackup
from apps.settings.backup_serializers import DatabaseBackupSerializer

pytestmark = pytest.mark.django_db


class TestDatabaseBackupModel:
    def test_create_backup_record(self, superuser_client):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()
        backup = DatabaseBackup.objects.create(
            filename="devtrack_20260403_120000.dump",
            status="running",
            created_by=user,
        )
        assert backup.filename == "devtrack_20260403_120000.dump"
        assert backup.status == "running"
        assert backup.file_size is None
        assert backup.error_message == ""

    def test_ordering_newest_first(self):
        b1 = DatabaseBackup.objects.create(filename="a.dump", status="success")
        b2 = DatabaseBackup.objects.create(filename="b.dump", status="success")
        ids = list(DatabaseBackup.objects.values_list("id", flat=True))
        assert ids == [b2.id, b1.id]

    def test_str_representation(self):
        backup = DatabaseBackup.objects.create(filename="test.dump", status="success")
        assert "test.dump" in str(backup)


class TestDatabaseBackupSerializer:
    def test_serializes_backup_record(self, superuser_client):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()
        backup = DatabaseBackup.objects.create(
            filename="devtrack_20260403_120000.dump",
            file_size=15728640,
            status="success",
            created_by=user,
        )
        data = DatabaseBackupSerializer(backup).data
        assert data["filename"] == "devtrack_20260403_120000.dump"
        assert data["file_size"] == 15728640
        assert data["status"] == "success"
        assert data["created_by_name"] == user.name
        assert "id" in data
        assert "created_at" in data

    def test_created_by_name_null_user(self):
        backup = DatabaseBackup.objects.create(
            filename="test.dump", status="success", created_by=None
        )
        data = DatabaseBackupSerializer(backup).data
        assert data["created_by_name"] is None


class TestBackupListAPI:
    def test_list_as_superuser(self, superuser_client):
        DatabaseBackup.objects.create(filename="a.dump", status="success")
        DatabaseBackup.objects.create(filename="b.dump", status="success")
        resp = superuser_client.get("/api/settings/backups/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_list_as_regular_user_forbidden(self, regular_client):
        resp = regular_client.get("/api/settings/backups/")
        assert resp.status_code == 403

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get("/api/settings/backups/")
        assert resp.status_code == 401


class TestBackupCreateAPI:
    @patch("apps.settings.backup_views.run_pg_dump")
    def test_trigger_backup_success(self, mock_dump, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        mock_dump.return_value = (True, 1024, "")

        resp = superuser_client.post("/api/settings/backups/create/")
        assert resp.status_code == 201
        assert resp.data["status"] == "success"
        assert resp.data["file_size"] == 1024

    @patch("apps.settings.backup_views.run_pg_dump")
    def test_trigger_backup_failure(self, mock_dump, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        mock_dump.return_value = (False, 0, "pg_dump: connection refused")
        resp = superuser_client.post("/api/settings/backups/create/")
        assert resp.status_code == 201
        assert resp.data["status"] == "failed"
        assert "connection refused" in resp.data["error_message"]

    def test_trigger_forbidden_non_staff(self, regular_client):
        resp = regular_client.post("/api/settings/backups/create/")
        assert resp.status_code == 403

    @patch("apps.settings.backup_views.run_pg_dump")
    def test_concurrent_backup_blocked(self, mock_dump, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        DatabaseBackup.objects.create(filename="running.dump", status="running")
        resp = superuser_client.post("/api/settings/backups/create/")
        assert resp.status_code == 409


class TestBackupDownloadAPI:
    def test_download_backup(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        (tmp_path / "test.dump").write_bytes(b"fake dump content")
        backup = DatabaseBackup.objects.create(
            filename="test.dump", file_size=17, status="success"
        )
        resp = superuser_client.get(f"/api/settings/backups/{backup.id}/download/")
        assert resp.status_code == 200
        assert b"fake dump content" in b"".join(resp.streaming_content)

    def test_download_missing_file_404(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        backup = DatabaseBackup.objects.create(
            filename="gone.dump", status="success"
        )
        resp = superuser_client.get(f"/api/settings/backups/{backup.id}/download/")
        assert resp.status_code == 404

    def test_download_nonexistent_record_404(self, superuser_client):
        resp = superuser_client.get("/api/settings/backups/99999/download/")
        assert resp.status_code == 404


class TestBackupDeleteAPI:
    def test_delete_backup_and_file(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        dump_file = tmp_path / "deleteme.dump"
        dump_file.write_bytes(b"data")
        backup = DatabaseBackup.objects.create(
            filename="deleteme.dump", status="success"
        )
        resp = superuser_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 204
        assert not dump_file.exists()
        assert not DatabaseBackup.objects.filter(id=backup.id).exists()

    def test_delete_file_already_gone(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        backup = DatabaseBackup.objects.create(
            filename="already_gone.dump", status="failed"
        )
        resp = superuser_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 204

    def test_delete_forbidden_non_staff(self, regular_client):
        backup = DatabaseBackup.objects.create(filename="t.dump", status="success")
        resp = regular_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 403
