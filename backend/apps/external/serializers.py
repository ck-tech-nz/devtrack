from rest_framework import serializers

TYPE_TO_LABEL = {
    "bug": "Bug",
    "BUG": "Bug",
    "feature": "需求",
    "功能建议": "需求",
    "improvement": "优化",
    "体验改进": "优化",
}


class ExternalIssueCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    type = serializers.CharField(required=False, default="")
    priority = serializers.CharField(required=False, default="P2")
    description = serializers.CharField(required=False, default="")
    module = serializers.CharField(required=False, default="")
    source_feedback_id = serializers.CharField(required=False, default="")
    reporter = serializers.DictField(required=False, default=dict)
    context = serializers.DictField(required=False, default=dict)
    attachments = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )

    def validate_priority(self, value):
        if value not in ("P0", "P1", "P2", "P3"):
            return "P2"
        return value

    def validate(self, data):
        labels = []
        type_val = data.pop("type", "")
        if type_val:
            mapped = TYPE_TO_LABEL.get(type_val, type_val)
            labels.append(mapped)
        module = data.pop("module", "")
        if module:
            labels.append(module)
        data["_labels"] = labels
        return data


class ExternalIssueResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    issue_number = serializers.SerializerMethodField()
    title = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    assignee = serializers.SerializerMethodField()
    labels = serializers.JSONField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField()
    source_feedback_id = serializers.SerializerMethodField()

    def get_issue_number(self, obj):
        return f"ISS-{obj.id:03d}"

    def get_assignee(self, obj):
        if obj.assignee:
            return obj.assignee.name or obj.assignee.username
        return None

    def get_source_feedback_id(self, obj):
        if obj.source_meta and isinstance(obj.source_meta, dict):
            return obj.source_meta.get("feedback_id")
        return None
