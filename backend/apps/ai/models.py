from django.conf import settings
from django.db import models


class LLMConfig(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="名称")
    api_key = models.CharField(max_length=500, verbose_name="API Key")
    base_url = models.CharField(max_length=500, blank=True, verbose_name="Base URL")
    # 该配置下可用的模型 ID 列表。提供商之间不互通,所以挂在配置上而不是全局
    # 表。可在 LLM 配置列表用"获取可用模型"动作自动调用 /v1/models 拉取
    available_models = models.JSONField(
        default=list, blank=True,
        verbose_name="可用模型",
        help_text="该配置可用的模型 ID 列表。留空时不校验;非空时提示词的「模型」字段必须在此列表内。",
    )
    supports_json_mode = models.BooleanField(default=True, verbose_name="支持 JSON 模式")
    is_default = models.BooleanField(default=False, verbose_name="默认配置")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LLM 配置"
        verbose_name_plural = "LLM 配置"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            from django.db import transaction
            with transaction.atomic():
                if self.pk:
                    LLMConfig.objects.exclude(pk=self.pk).update(is_default=False)
                else:
                    LLMConfig.objects.all().update(is_default=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class Prompt(models.Model):
    slug = models.CharField(max_length=100, unique=True, verbose_name="标识符")
    name = models.CharField(max_length=200, verbose_name="显示名")
    system_prompt = models.TextField(verbose_name="系统提示词")
    user_prompt_template = models.TextField(verbose_name="用户提示词模板")
    llm_model = models.CharField(max_length=100, verbose_name="模型")
    temperature = models.FloatField(default=0.3, verbose_name="Temperature")
    llm_config = models.ForeignKey(
        LLMConfig, on_delete=models.PROTECT,
        verbose_name="LLM 配置",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "提示词"
        verbose_name_plural = "提示词"

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def clean(self):
        """校验 llm_model 是否在所选 LLMConfig.available_models 内。"""
        super().clean()
        cfg = self.llm_config
        if cfg and cfg.available_models and self.llm_model and self.llm_model not in cfg.available_models:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                "llm_model": (
                    f"模型 {self.llm_model!r} 不在 LLM 配置「{cfg.name}」的可用模型列表中。"
                    f"可用: {cfg.available_models}"
                ),
            })


class Analysis(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        RUNNING = "running", "运行中"
        DONE = "done", "完成"
        FAILED = "failed", "失败"

    class TriggerType(models.TextChoices):
        PAGE_OPEN = "page_open", "页面打开"
        MANUAL = "manual", "手动刷新"
        AUTO = "auto", "自动触发"

    analysis_type = models.CharField(max_length=100, verbose_name="分析类型")
    prompt_template = models.ForeignKey(
        Prompt, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="提示词模板",
    )
    triggered_by = models.CharField(
        max_length=20, choices=TriggerType.choices, verbose_name="触发方式",
    )
    triggered_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="触发用户",
    )
    issue = models.ForeignKey(
        "issues.Issue", on_delete=models.CASCADE,
        null=True, blank=True, related_name="analyses",
        verbose_name="关联问题",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="状态",
    )
    data_hash = models.CharField(max_length=32, blank=True, verbose_name="数据哈希")
    input_context = models.JSONField(default=dict, verbose_name="输入上下文")
    prompt_snapshot = models.JSONField(default=dict, verbose_name="提示词快照")
    raw_response = models.TextField(null=True, blank=True, verbose_name="LLM 原始回包")
    parsed_result = models.JSONField(null=True, blank=True, verbose_name="解析结果")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 分析"
        verbose_name_plural = "AI 分析"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.analysis_type} [{self.status}] {self.created_at:%Y-%m-%d %H:%M}"
