import uuid

from django.conf import settings
from django.db import models


class KPISnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kpi_snapshots",
        verbose_name="用户",
    )
    period_start = models.DateField(verbose_name="统计起始日期")
    period_end = models.DateField(verbose_name="统计截止日期")
    issue_metrics = models.JSONField(default=dict, verbose_name="问题指标")
    commit_metrics = models.JSONField(default=dict, verbose_name="Commit 指标")
    scores = models.JSONField(default=dict, verbose_name="评分")
    rankings = models.JSONField(default=dict, verbose_name="排名")
    suggestions = models.JSONField(default=dict, verbose_name="改进建议")
    computed_at = models.DateTimeField(verbose_name="计算时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "KPI 快照"
        verbose_name_plural = "KPI 快照"
        unique_together = ("user", "period_start", "period_end")
        ordering = ["-period_end", "-computed_at"]
        permissions = [
            ("view_own_kpi", "Can view own KPI"),
            ("refresh_kpi", "Can refresh KPI data"),
        ]

    def __str__(self):
        return f"{self.user} | {self.period_start} ~ {self.period_end}"
