from django.db import models


class Repo(models.Model):
    name = models.CharField(max_length=100, verbose_name="仓库名")
    full_name = models.CharField(max_length=200, verbose_name="完整名称")
    url = models.CharField(max_length=500, verbose_name="GitHub URL")
    description = models.TextField(blank=True, verbose_name="描述")
    default_branch = models.CharField(max_length=50, default="main", verbose_name="默认分支")
    language = models.CharField(max_length=50, blank=True, verbose_name="主要语言")
    stars = models.PositiveIntegerField(default=0, verbose_name="Star 数")
    status = models.CharField(max_length=20, default="在线", verbose_name="状态")
    connected_at = models.DateTimeField(auto_now_add=True, verbose_name="绑定时间")
    github_token = models.CharField(max_length=200, blank=True, verbose_name="GitHub Token")
    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name="最近同步时间")

    class Meta:
        verbose_name = "GitHub 仓库"
        verbose_name_plural = "GitHub 仓库"
        ordering = ["-connected_at"]

    def __str__(self):
        return self.full_name


class GitHubIssue(models.Model):
    STATE_OPEN = "open"
    STATE_CLOSED = "closed"
    STATE_CHOICES = [(STATE_OPEN, "开放"), (STATE_CLOSED, "已关闭")]

    repo = models.ForeignKey(Repo, on_delete=models.CASCADE, related_name="github_issues")
    github_id = models.PositiveIntegerField(verbose_name="GitHub Issue 编号")
    title = models.CharField(max_length=500, verbose_name="标题")
    body = models.TextField(blank=True, verbose_name="内容")
    state = models.CharField(max_length=20, choices=STATE_CHOICES, verbose_name="状态")
    labels = models.JSONField(default=list, verbose_name="标签")
    assignees = models.JSONField(default=list, verbose_name="负责人")
    github_created_at = models.DateTimeField(verbose_name="GitHub 创建时间")
    github_updated_at = models.DateTimeField(verbose_name="GitHub 更新时间")
    github_closed_at = models.DateTimeField(null=True, blank=True, verbose_name="GitHub 关闭时间")
    synced_at = models.DateTimeField(verbose_name="同步时间")

    class Meta:
        verbose_name = "GitHub Issue"
        verbose_name_plural = "GitHub Issues"
        unique_together = ("repo", "github_id")
        ordering = ["-github_created_at"]

    def __str__(self):
        return f"#{self.github_id} {self.title}"
