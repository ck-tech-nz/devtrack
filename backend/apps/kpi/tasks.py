import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def refresh_all_kpi():
    """定时保存月度 KPI 快照（用于趋势历史）。视图层按需计算任意周期。"""
    from apps.kpi.services import KPIService

    today = timezone.now().date()
    month_start = today.replace(day=1)
    try:
        result = KPIService().refresh(period_start=month_start, period_end=today)
        logger.info("KPI snapshot saved: %s ~ %s, %d users", month_start, today, result["user_count"])
    except Exception:
        logger.exception("KPI refresh failed")


@shared_task(ignore_result=False)
def generate_monthly_plans():
    """每月 1 号自动生成提升计划草案。"""
    from django.contrib.auth import get_user_model
    from apps.kpi.models import ImprovementPlan, ActionItem
    from apps.kpi.plan_generator import generate_action_items
    from apps.kpi.services import KPIService

    User = get_user_model()
    today = timezone.now().date()
    current_period = today.strftime("%Y-%m")
    prev_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    month_start = today.replace(day=1)

    # 1) 刷新上月 KPI 快照
    svc = KPIService()
    try:
        svc.refresh(period_start=prev_month_start, period_end=month_start - timedelta(days=1))
    except Exception:
        logger.exception("Failed to refresh previous month KPI")

    # 2) 归档上月 published 计划
    prev_period = prev_month_start.strftime("%Y-%m")
    archived = ImprovementPlan.objects.filter(
        period=prev_period, status=ImprovementPlan.Status.PUBLISHED,
    ).update(status=ImprovementPlan.Status.ARCHIVED, archived_at=timezone.now())
    logger.info("Archived %d plans for %s", archived, prev_period)

    # 3) 为每个活跃用户生成草案
    users = svc._get_target_users()
    team_scores = [svc.compute_for_user(u, month_start, today)["scores"] for u in users]
    dims = ("efficiency", "output", "quality", "capability")
    team_avgs = {}
    if team_scores:
        for d in dims:
            vals = [s.get(d, 0) for s in team_scores]
            team_avgs[d] = round(sum(vals) / len(vals), 1)

    created = 0
    for user in users:
        if ImprovementPlan.objects.filter(user=user, period=current_period).exists():
            continue

        kpi_data = svc.compute_for_user(user, month_start, today)
        items_data = generate_action_items(
            kpi_data["scores"], kpi_data["issue_metrics"],
            kpi_data["commit_metrics"], team_avgs,
        )

        plan = ImprovementPlan.objects.create(
            user=user, period=current_period,
            status=ImprovementPlan.Status.DRAFT,
            source_kpi_scores=kpi_data["scores"],
        )
        for i, item_data in enumerate(items_data):
            ActionItem.objects.create(plan=plan, sort_order=i, **item_data)
        created += 1

    logger.info("Generated %d plans for %s", created, current_period)
