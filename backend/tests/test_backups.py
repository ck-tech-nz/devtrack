import pytest
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
