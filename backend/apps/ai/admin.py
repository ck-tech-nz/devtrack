import openai
from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from .forms import PromptAdminForm
from .models import LLMConfig, Prompt, Analysis


@admin.action(description="从提供商获取可用模型(/v1/models)")
def fetch_models_from_provider(modeladmin, request, queryset):
    """调用 OpenAI 兼容的 GET /v1/models,把返回的模型 ID 写入 available_models。

    一次失败不影响其它行;每行单独提示成功/失败,方便一键刷新多个配置。
    """
    for cfg in queryset:
        try:
            client = openai.OpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url or None,
                timeout=15,
            )
            ids = sorted({m.id for m in client.models.list().data})
            cfg.available_models = ids
            cfg.save(update_fields=["available_models", "updated_at"])
            messages.success(request, f"{cfg.name}: 获取到 {len(ids)} 个模型")
        except Exception as e:
            messages.error(request, f"{cfg.name}: 获取失败 — {e}")


@admin.register(LLMConfig)
class LLMConfigAdmin(ModelAdmin):
    list_display = (
        "name", "base_url", "model_count", "supports_json_mode",
        "is_default", "is_active",
    )
    readonly_fields = ("created_at", "updated_at")
    actions = (fetch_models_from_provider,)
    # api_key absent from list_display to avoid plaintext exposure in list view

    @admin.display(description="可用模型数")
    def model_count(self, obj):
        return len(obj.available_models or [])


@admin.register(Prompt)
class PromptAdmin(ModelAdmin):
    form = PromptAdminForm
    list_display = ("slug", "name", "llm_config", "llm_model", "is_active")
    readonly_fields = ("created_at", "updated_at")
    # 字段顺序:LLM 配置 在前,模型 紧随其后,UI 提示"模型由所选配置过滤"
    fieldsets = (
        (None, {
            "fields": (
                "slug", "name",
                "system_prompt", "user_prompt_template",
                ("llm_config", "llm_model"),
                "temperature",
                "is_active",
            ),
        }),
        ("时间", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )


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
