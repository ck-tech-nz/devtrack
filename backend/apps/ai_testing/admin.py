from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    AITestingModelSettings,
    BrowserArtifact,
    ProjectEnvironment,
    TestFlow,
    TestRun,
    TestStepRun,
)


@admin.register(AITestingModelSettings)
class AITestingModelSettingsAdmin(ModelAdmin):
    list_display = (
        "id",
        "llm_config",
        "planner_model",
        "critic_model",
        "temperature",
        "max_agent_turns",
        "is_global_default",
    )
    list_filter = ("is_global_default", "enable_critic_review")


@admin.register(ProjectEnvironment)
class ProjectEnvironmentAdmin(ModelAdmin):
    list_display = (
        "id",
        "project",
        "name",
        "base_url",
        "login_type",
        "login_username",
        "has_login_password",
        "allow_write_actions",
        "allow_dangerous_actions",
        "is_active",
    )
    list_filter = ("is_active", "login_type", "allow_write_actions", "allow_dangerous_actions")
    search_fields = ("project__name", "name", "base_url", "login_username")
    readonly_fields = ("created_at", "updated_at")
    exclude = ("login_password_encrypted",)


@admin.register(TestFlow)
class TestFlowAdmin(ModelAdmin):
    list_display = (
        "id",
        "project",
        "name",
        "environment",
        "status",
        "cleanup_policy",
        "cleanup_enabled",
        "updated_at",
    )
    list_filter = ("status", "cleanup_policy", "cleanup_enabled")
    search_fields = ("project__name", "name")
    readonly_fields = ("created_at", "updated_at", "created_by")


class TestStepRunInline(admin.TabularInline):
    model = TestStepRun
    extra = 0
    can_delete = False
    fields = ("step_index", "skill_name", "tool_name", "status", "created_at")
    readonly_fields = fields
    show_change_link = True


@admin.register(TestRun)
class TestRunAdmin(ModelAdmin):
    list_display = ("id", "project", "name", "status", "environment", "created_by", "created_at")
    list_filter = ("status", "project")
    search_fields = ("name", "project__name")
    readonly_fields = ("created_at", "updated_at", "started_at", "finished_at")
    inlines = [TestStepRunInline]


@admin.register(TestStepRun)
class TestStepRunAdmin(ModelAdmin):
    list_display = ("id", "run", "step_index", "skill_name", "tool_name", "status", "created_at")
    list_filter = ("status", "tool_name")
    readonly_fields = (
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
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BrowserArtifact)
class BrowserArtifactAdmin(ModelAdmin):
    list_display = ("id", "run", "artifact_type", "step", "created_at")
    list_filter = ("artifact_type",)
    readonly_fields = ("run", "step", "artifact_type", "attachment", "content", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
