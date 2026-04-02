from rest_framework import serializers
from .models import DatabaseBackup


class DatabaseBackupSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.name", read_only=True, default=None
    )

    class Meta:
        model = DatabaseBackup
        fields = [
            "id", "filename", "file_size", "status",
            "error_message", "created_by_name", "created_at",
        ]
        read_only_fields = fields
