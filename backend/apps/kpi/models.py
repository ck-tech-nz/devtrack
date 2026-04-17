import uuid

from django.conf import settings
from django.db import models
from solo.models import SingletonModel


# ---------------------------------------------------------------------------
# 评分配置（单例）
# ---------------------------------------------------------------------------

def _default_dimension_weights():
    return {
        "efficiency": 0.25,
        "output": 0.25,
        "quality": 0.25,
        "capability": 0.15,
        "growth": 0.10,
    }


def _default_efficiency_formula():
    return {
        "daily_resolved": 0.4,
        "speed": 0.4,
        "p0p1_speed": 0.2,
    }


def _default_output_formula():
    return {
        "weighted_issue_value": 0.4,
        "resolved_count": 0.3,
        "commit_volume": 0.2,
        "repo_breadth": 0.1,
    }


def _default_quality_formula():
    return {
        "inv_bug_rate": 0.30,
        "inv_churn_rate": 0.25,
        "commit_size": 0.20,
        "conventional_ratio": 0.25,
    }


def _default_capability_formula():
    return {
        "file_type_breadth": 0.25,
        "repo_coverage": 0.25,
        "p0_handling_ratio": 0.25,
        "helper_participation": 0.25,
    }


def _default_ceilings():
    return {
        "daily_resolved": 3.0,
        "avg_hours": 168.0,
        "p0p1_hours": 48.0,
        "weighted_value": 200.0,
        "resolved_count": 30.0,
        "commit_volume": 100.0,
        "repo_breadth": 5.0,
        "file_type": 8.0,
        "helper_count": 10.0,
    }


class KPIScoringConfig(SingletonModel):
    """KPI 评分规则配置（全局单例）。"""

    dimension_weights = models.JSONField(
        default=_default_dimension_weights,
        verbose_name="综合分维度权重",
        help_text="5 个维度在综合分中的权重，总和应为 1.0",
    )
    efficiency_formula = models.JSONField(
        default=_default_efficiency_formula,
        verbose_name="效率评分公式",
        help_text="效率维度各子指标权重",
    )
    output_formula = models.JSONField(
        default=_default_output_formula,
        verbose_name="产出评分公式",
        help_text="产出维度各子指标权重",
    )
    quality_formula = models.JSONField(
        default=_default_quality_formula,
        verbose_name="质量评分公式",
        help_text="质量维度各子指标权重",
    )
    capability_formula = models.JSONField(
        default=_default_capability_formula,
        verbose_name="能力评分公式",
        help_text="能力维度各子指标权重",
    )
    ceilings = models.JSONField(
        default=_default_ceilings,
        verbose_name="饱和天花板值",
        help_text="各指标达到满分 100 的阈值",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "KPI 评分规则"
        verbose_name_plural = "KPI 评分规则"

    def __str__(self):
        return "KPI 评分规则"


# ---------------------------------------------------------------------------
# KPI 快照
# ---------------------------------------------------------------------------

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
