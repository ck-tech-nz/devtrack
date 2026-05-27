from rest_framework import serializers

from .models import (
    AITestingModelSettings,
    BrowserArtifact,
    ProjectEnvironment,
    TestFlow,
    TestRun,
    TestStepRun,
)


class AITestingModelSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITestingModelSettings
        fields = [
            "id",
            "llm_config",
            "planner_model",
            "critic_model",
            "temperature",
            "tool_call_timeout_secs",
            "max_agent_turns",
            "enable_critic_review",
            "is_global_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProjectEnvironmentSerializer(serializers.ModelSerializer):
    login_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_login_password = serializers.BooleanField(read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = ProjectEnvironment
        fields = [
            "id",
            "project",
            "project_name",
            "name",
            "base_url",
            "login_type",
            "login_config",
            "login_username",
            "login_password",
            "has_login_password",
            "credential_ref",
            "model_settings",
            "allowed_url_patterns",
            "allow_write_actions",
            "allow_dangerous_actions",
            "artifact_retention_policy",
            "max_concurrent_runs",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "has_login_password"]

    def validate_base_url(self, value):
        if not (value.startswith("http://") or value.startswith("https://")):
            raise serializers.ValidationError("base_url 必须以 http:// 或 https:// 开头")
        return value

    def create(self, validated_data):
        password = validated_data.pop("login_password", None)
        instance = super().create(validated_data)
        if password is not None:
            instance.set_login_password(password)
            instance.save(update_fields=["login_password_encrypted", "updated_at"])
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("login_password", None)
        instance = super().update(instance, validated_data)
        if password is not None:
            instance.set_login_password(password)
            instance.save(update_fields=["login_password_encrypted", "updated_at"])
        return instance


class TestFlowSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    environment_name = serializers.CharField(source="environment.name", read_only=True, default="")

    class Meta:
        model = TestFlow
        fields = [
            "id",
            "project",
            "project_name",
            "environment",
            "environment_name",
            "name",
            "description",
            "target_url",
            "success_criteria",
            "max_steps",
            "timeout_secs",
            "cleanup_policy",
            "cleanup_enabled",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class TestRunSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    environment_name = serializers.CharField(source="environment.name", read_only=True)
    flow_name = serializers.CharField(source="flow.name", read_only=True, default="")

    class Meta:
        model = TestRun
        fields = [
            "id",
            "flow",
            "flow_name",
            "project",
            "project_name",
            "environment",
            "environment_name",
            "name",
            "target_url",
            "input_snapshot",
            "status",
            "started_at",
            "finished_at",
            "final_summary",
            "failure_reason",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "started_at",
            "finished_at",
            "final_summary",
            "failure_reason",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project")
        environment = attrs.get("environment")
        flow = attrs.get("flow")

        if environment:
            if project and environment.project_id != project.id:
                raise serializers.ValidationError({"environment": "环境与项目不匹配"})
            if not environment.is_active:
                raise serializers.ValidationError({"environment": "环境未启用，无法执行"})

        if flow:
            if project and flow.project_id != project.id:
                raise serializers.ValidationError({"flow": "流程与项目不匹配"})
            if flow.status != TestFlow.STATUS_ACTIVE:
                raise serializers.ValidationError({"flow": "仅允许执行已启用（active）的流程"})
            if environment and flow.environment_id and flow.environment_id != environment.id:
                raise serializers.ValidationError({"environment": "执行环境必须与流程默认环境一致"})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        validated_data["created_by"] = user
        validated_data.setdefault("status", TestRun.STATUS_PENDING)
        return super().create(validated_data)


class TestStepRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStepRun
        fields = [
            "id",
            "run",
            "step_index",
            "skill_name",
            "thought_summary",
            "tool_name",
            "tool_input",
            "tool_result",
            "page_url",
            "status",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class BrowserArtifactSerializer(serializers.ModelSerializer):
    attachment_url = serializers.CharField(source="attachment.file_url", read_only=True, default="")
    attachment_name = serializers.CharField(source="attachment.file_name", read_only=True, default="")

    class Meta:
        model = BrowserArtifact
        fields = [
            "id",
            "run",
            "step",
            "artifact_type",
            "attachment",
            "attachment_url",
            "attachment_name",
            "content",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
