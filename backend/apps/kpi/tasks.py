import logging

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
