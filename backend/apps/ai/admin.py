from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import LLMConfig, Prompt, Analysis


@admin.register(LLMConfig)
class LLMConfigAdmin(ModelAdmin):
    list_display = ("name", "base_url", "supports_json_mode", "is_default", "is_active")
    readonly_fields = ("created_at", "updated_at")
    # api_key absent from list_display to avoid plaintext exposure in list view


@admin.register(Prompt)
class PromptAdmin(ModelAdmin):
    list_display = ("slug", "name", "llm_model", "llm_config", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Analysis)
class AnalysisAdmin(ModelAdmin):
    list_display = ("analysis_type", "triggered_by", "status", "created_at")
    readonly_fields = (
        "input_context", "prompt_snapshot", "raw_response", "parsed_result",
        "data_hash", "created_at", "updated_at",
    )
    list_filter = ("status", "analysis_type", "triggered_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
