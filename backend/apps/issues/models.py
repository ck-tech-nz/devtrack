from django.conf import settings
from django.db import models


class Issue(models.Model):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="issues"
    )
    title = models.CharField(max_length=200, verbose_name="标题")
    description = models.TextField(blank=True, verbose_name="描述")
    github_issues = models.ManyToManyField(
        "repos.GitHubIssue", blank=True, related_name="devtrack_issues",
        verbose_name="关联 GitHub Issues",
    )
    attachments = models.ManyToManyField(
        "tools.Attachment", blank=True,
        related_name="issues", verbose_name="附件",
    )
    repo = models.ForeignKey(
        "repos.Repo", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="issues",
        verbose_name="关联仓库",
    )
    priority = models.CharField(max_length=10, verbose_name="优先级")
    status = models.CharField(max_length=20, verbose_name="状态")
    labels = models.JSONField(default=list, verbose_name="标签", blank=True)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="reported_issues", verbose_name="提出人",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_issues", verbose_name="负责人",
    )
    helpers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="helped_issues",
        verbose_name="协助人",
    )
    remark = models.TextField(blank=True, verbose_name="备注")
    estimated_completion = models.DateField(null=True, blank=True, verbose_name="预计完成")
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="实际工时")
    cause = models.TextField(blank=True, verbose_name="原因分析")
    solution = models.TextField(blank=True, verbose_name="解决办法")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="解决时间")

    class Meta:
        verbose_name = "问题"
        verbose_name_plural = "问题"
        ordering = ["-created_at"]
        permissions = [
            ("batch_update_issue", "Can batch update issues"),
            ("view_dashboard", "Can view dashboard"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.title}"


class Activity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="activities")
    action = models.CharField(max_length=20, verbose_name="动作")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="activities")
    detail = models.CharField(max_length=200, blank=True, verbose_name="详情")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "活动记录"
        verbose_name_plural = "活动记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.action} {self.issue}"
