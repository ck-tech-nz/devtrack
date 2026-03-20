from rest_framework import serializers
from django.utils import timezone
from apps.settings.models import SiteSettings
from .models import Issue, Activity


class ActivitySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    issue_title = serializers.CharField(source="issue.title", read_only=True)
    issue_id = serializers.UUIDField(source="issue.id", read_only=True)
    issue_display_id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ["id", "user_name", "action", "issue_title", "issue_id", "issue_display_id", "detail", "created_at"]

    def get_issue_display_id(self, obj):
        return f"ISS-{obj.issue.number:03d}" if obj.issue.number else None


class IssueListSerializer(serializers.ModelSerializer):
    display_id = serializers.SerializerMethodField()
    reporter_name = serializers.CharField(source="reporter.name", read_only=True, default=None)
    assignee_name = serializers.CharField(source="assignee.name", read_only=True, default=None)
    resolution_hours = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "number", "display_id", "project", "title", "priority",
            "status", "labels", "reporter", "reporter_name",
            "assignee", "assignee_name", "resolution_hours",
            "created_at", "updated_at",
        ]

    def get_display_id(self, obj):
        return f"ISS-{obj.number:03d}" if obj.number else None

    def get_resolution_hours(self, obj):
        if obj.resolved_at and obj.created_at:
            delta = obj.resolved_at - obj.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None


class IssueDetailSerializer(IssueListSerializer):
    class Meta(IssueListSerializer.Meta):
        fields = IssueListSerializer.Meta.fields + [
            "description", "remark", "estimated_completion",
            "actual_hours", "cause", "solution", "resolved_at",
        ]


class IssueCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = [
            "project", "title", "description", "priority", "status",
            "labels", "assignee", "remark", "estimated_completion",
            "actual_hours", "cause", "solution",
        ]

    def validate_labels(self, value):
        site_settings = SiteSettings.get_solo()
        valid = set(site_settings.labels)
        invalid = [l for l in value if l not in valid]
        if invalid:
            raise serializers.ValidationError(f"无效的标签: {invalid}")
        return value

    def validate_priority(self, value):
        site_settings = SiteSettings.get_solo()
        if value not in site_settings.priorities:
            raise serializers.ValidationError(f"无效的优先级: {value}")
        return value

    def validate_status(self, value):
        site_settings = SiteSettings.get_solo()
        if value not in site_settings.issue_statuses:
            raise serializers.ValidationError(f"无效的状态: {value}")
        return value

    def create(self, validated_data):
        validated_data["reporter"] = self.context["request"].user
        issue = super().create(validated_data)
        Activity.objects.create(
            user=self.context["request"].user,
            issue=issue,
            action="created",
        )
        return issue

    def update(self, instance, validated_data):
        user = self.context["request"].user
        old_status = instance.status
        old_assignee = instance.assignee_id
        issue = super().update(instance, validated_data)

        # Track status changes
        new_status = validated_data.get("status")
        if new_status and new_status != old_status:
            action = "resolved" if new_status == "已解决" else "closed" if new_status == "已关闭" else "updated"
            Activity.objects.create(
                user=user, issue=issue, action=action,
                detail=f"状态从 {old_status} 改为 {new_status}",
            )
            if new_status == "已解决" and not issue.resolved_at:
                issue.resolved_at = timezone.now()
                issue.save(update_fields=["resolved_at"])

        # Track assignee changes
        new_assignee = validated_data.get("assignee")
        if "assignee" in validated_data and str(getattr(new_assignee, "id", None)) != str(old_assignee):
            Activity.objects.create(
                user=user, issue=issue, action="assigned",
                detail=f"分配给 {new_assignee.name}" if new_assignee else "取消分配",
            )

        return issue


class BatchUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField())
    action = serializers.ChoiceField(choices=["assign", "set_priority"])
    value = serializers.CharField()
