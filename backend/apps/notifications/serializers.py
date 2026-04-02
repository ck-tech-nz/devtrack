from rest_framework import serializers
from .models import Notification, NotificationRecipient


class NotificationSerializer(serializers.ModelSerializer):
    """User-facing serializer: includes per-user read state."""
    is_read = serializers.BooleanField(source="recipient.is_read", read_only=True)
    read_at = serializers.DateTimeField(source="recipient.read_at", read_only=True)
    source_user_name = serializers.CharField(source="source_user.name", read_only=True, default=None)
    source_issue_title = serializers.CharField(source="source_issue.title", read_only=True, default=None)
    source_issue_id = serializers.UUIDField(read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "content",
            "source_user_name", "source_issue_id", "source_issue_title",
            "is_read", "read_at", "created_at",
        ]


class NotificationManageSerializer(serializers.ModelSerializer):
    """Admin-facing serializer: includes target info, draft state, recipient count."""
    source_user_name = serializers.CharField(source="source_user.name", read_only=True, default=None)
    target_group_id = serializers.IntegerField(source="target_group_id", required=False, allow_null=True)
    target_group_name = serializers.CharField(source="target_group.name", read_only=True, default=None)
    target_user_ids = serializers.PrimaryKeyRelatedField(
        source="target_users", many=True, read_only=True,
    )
    recipient_count = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "content",
            "source_user_name", "target_type", "target_group_id", "target_group_name",
            "target_user_ids", "is_draft", "recipient_count", "created_at",
        ]

    def get_recipient_count(self, obj):
        return obj.recipients.count()
