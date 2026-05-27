from django.conf import settings
from django.db import models
from django.db.models import Q

from .crypto import decrypt_secret, encrypt_secret


class AITestingModelSettings(models.Model):
    llm_config = models.ForeignKey(
        "ai.LLMConfig",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_testing_settings",
        verbose_name="LLM 配置",
    )
    planner_model = models.CharField(max_length=100, blank=True, verbose_name="Planner 模型")
    critic_model = models.CharField(max_length=100, blank=True, verbose_name="Critic 模型")
    temperature = models.FloatField(default=0.1, verbose_name="Temperature")
    tool_call_timeout_secs = models.PositiveIntegerField(default=60, verbose_name="工具调用超时(秒)")
    max_agent_turns = models.PositiveIntegerField(default=30, verbose_name="最大 Agent 轮次")
    enable_critic_review = models.BooleanField(default=False, verbose_name="启用 Critic 复核")
    is_global_default = models.BooleanField(default=False, verbose_name="全局默认")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 测试模型设置"
        verbose_name_plural = "AI 测试模型设置"
        constraints = [
            models.UniqueConstraint(
                fields=["is_global_default"],
                condition=Q(is_global_default=True),
                name="unique_ai_testing_global_default",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.is_global_default:
            AITestingModelSettings.objects.exclude(pk=self.pk).filter(is_global_default=True).update(
                is_global_default=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        if self.planner_model:
            return self.planner_model
        if self.llm_config_id:
            return f"LLM#{self.llm_config_id}"
        return f"配置#{self.pk}"


class ProjectEnvironment(models.Model):
    LOGIN_USERNAME_PASSWORD = "username_password"
    LOGIN_SAVED_SESSION = "saved_session"
    LOGIN_NONE = "none"
    LOGIN_TYPE_CHOICES = [
        (LOGIN_USERNAME_PASSWORD, "账号密码"),
        (LOGIN_SAVED_SESSION, "已保存会话"),
        (LOGIN_NONE, "无登录"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ai_testing_environments",
        verbose_name="项目",
    )
    name = models.CharField(max_length=100, verbose_name="环境名称")
    base_url = models.URLField(max_length=500, verbose_name="基础 URL")
    login_type = models.CharField(
        max_length=50,
        choices=LOGIN_TYPE_CHOICES,
        default=LOGIN_USERNAME_PASSWORD,
        verbose_name="登录类型",
    )
    login_config = models.JSONField(default=dict, blank=True, verbose_name="登录配置")
    login_username = models.CharField(max_length=200, blank=True, verbose_name="测试账号")
    login_password_encrypted = models.TextField(blank=True, verbose_name="测试密码(加密)")
    credential_ref = models.CharField(max_length=200, blank=True, verbose_name="凭证引用")
    model_settings = models.ForeignKey(
        "ai_testing.AITestingModelSettings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="environments",
        verbose_name="模型设置覆盖",
    )
    allowed_url_patterns = models.JSONField(default=list, blank=True, verbose_name="URL 白名单")
    allow_write_actions = models.BooleanField(default=False, verbose_name="允许写操作")
    allow_dangerous_actions = models.BooleanField(default=False, verbose_name="允许危险操作")
    artifact_retention_policy = models.JSONField(default=dict, blank=True, verbose_name="产物保留策略")
    max_concurrent_runs = models.PositiveIntegerField(default=1, verbose_name="最大并发执行")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 测试环境"
        verbose_name_plural = "AI 测试环境"
        unique_together = ("project", "name")
        ordering = ["project_id", "name"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"

    def set_login_password(self, raw_password: str):
        self.login_password_encrypted = encrypt_secret(raw_password or "")

    def get_login_password(self) -> str:
        return decrypt_secret(self.login_password_encrypted or "")

    @property
    def has_login_password(self) -> bool:
        return bool(self.login_password_encrypted)


class TestFlow(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_ACTIVE, "启用"),
        (STATUS_ARCHIVED, "归档"),
    ]

    CLEANUP_NONE = "none"
    CLEANUP_DELETE = "delete"
    CLEANUP_CLOSE = "close"
    CLEANUP_CHOICES = [
        (CLEANUP_NONE, "不清理"),
        (CLEANUP_DELETE, "删除"),
        (CLEANUP_CLOSE, "关闭"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ai_testing_flows",
        verbose_name="项目",
    )
    environment = models.ForeignKey(
        ProjectEnvironment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_flows",
        verbose_name="默认环境",
    )
    name = models.CharField(max_length=200, verbose_name="流程名称")
    description = models.TextField(verbose_name="流程描述")
    target_url = models.URLField(max_length=500, blank=True, verbose_name="目标 URL")
    success_criteria = models.TextField(blank=True, verbose_name="成功标准")
    max_steps = models.PositiveIntegerField(default=30, verbose_name="最大步骤数")
    timeout_secs = models.PositiveIntegerField(default=300, verbose_name="超时(秒)")
    cleanup_policy = models.CharField(
        max_length=20,
        choices=CLEANUP_CHOICES,
        default=CLEANUP_NONE,
        verbose_name="清理策略",
    )
    cleanup_enabled = models.BooleanField(default=False, verbose_name="启用自动清理")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="状态")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_testing_flows",
        verbose_name="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 测试流程"
        verbose_name_plural = "AI 测试流程"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"


class TestRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_TIMEOUT = "timeout"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_TIMEOUT, "超时"),
        (STATUS_CANCELLED, "已取消"),
    ]

    flow = models.ForeignKey(
        TestFlow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
        verbose_name="流程",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ai_testing_runs",
        verbose_name="项目",
    )
    environment = models.ForeignKey(
        ProjectEnvironment,
        on_delete=models.PROTECT,
        related_name="runs",
        verbose_name="环境",
    )
    name = models.CharField(max_length=200, verbose_name="执行名称")
    target_url = models.URLField(max_length=500, blank=True, verbose_name="目标 URL")
    input_snapshot = models.JSONField(default=dict, blank=True, verbose_name="输入快照")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="状态")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    final_summary = models.TextField(blank=True, verbose_name="最终摘要")
    failure_reason = models.TextField(blank=True, verbose_name="失败原因")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_testing_runs",
        verbose_name="触发人",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 测试执行"
        verbose_name_plural = "AI 测试执行"
        ordering = ["-created_at"]
        permissions = [
            ("view_ai_testing", "Can view AI testing pages"),
            ("manage_ai_testing", "Can manage AI testing configuration"),
        ]

    def __str__(self):
        return f"{self.project.name} / Run#{self.id} / {self.name}"


class TestStepRun(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
    ]

    run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="执行",
    )
    step_index = models.PositiveIntegerField(verbose_name="步骤序号")
    skill_name = models.CharField(max_length=100, blank=True, verbose_name="技能")
    thought_summary = models.TextField(blank=True, verbose_name="决策摘要")
    tool_name = models.CharField(max_length=100, verbose_name="工具名")
    tool_input = models.JSONField(default=dict, blank=True, verbose_name="工具输入")
    tool_result = models.JSONField(default=dict, blank=True, verbose_name="工具输出")
    page_url = models.URLField(max_length=1000, blank=True, verbose_name="页面 URL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS, verbose_name="状态")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI 测试步骤"
        verbose_name_plural = "AI 测试步骤"
        ordering = ["step_index", "id"]
        unique_together = ("run", "step_index")

    def __str__(self):
        return f"Run#{self.run_id} Step#{self.step_index} {self.tool_name}"


class BrowserArtifact(models.Model):
    TYPE_SCREENSHOT = "screenshot"
    TYPE_TRACE = "trace"
    TYPE_CONSOLE = "console_log"
    TYPE_NETWORK = "network_log"
    TYPE_VIDEO = "video"
    TYPE_CHOICES = [
        (TYPE_SCREENSHOT, "截图"),
        (TYPE_TRACE, "Trace"),
        (TYPE_CONSOLE, "Console 日志"),
        (TYPE_NETWORK, "Network 日志"),
        (TYPE_VIDEO, "视频"),
    ]

    run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name="artifacts",
        verbose_name="执行",
    )
    step = models.ForeignKey(
        TestStepRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artifacts",
        verbose_name="步骤",
    )
    artifact_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="产物类型")
    attachment = models.ForeignKey(
        "tools.Attachment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_testing_artifacts",
        verbose_name="附件引用",
    )
    content = models.TextField(blank=True, verbose_name="文本内容")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="元数据")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "浏览器产物"
        verbose_name_plural = "浏览器产物"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Run#{self.run_id} {self.artifact_type}"
