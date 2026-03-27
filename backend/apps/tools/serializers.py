from rest_framework import serializers
from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "file_name", "file_url", "file_size", "mime_type", "created_at"]
        read_only_fields = fields
