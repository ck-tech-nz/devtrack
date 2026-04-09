import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def run_team_insights():
    """Hourly team insights analysis. Skips if latest result is still fresh."""
    from .services import AIAnalysisService, AIConfigurationError
    try:
        AIAnalysisService().get_or_run("team_insights", triggered_by="auto")
    except AIConfigurationError as e:
        logger.warning("Skipping team insights: %s", e)


@shared_task(ignore_result=False)
def refresh_team_insights(user_id=None):
    """Manual refresh triggered from UI."""
    from django.contrib.auth import get_user_model
    from .services import AIAnalysisService
    User = get_user_model()
    user = User.objects.get(pk=user_id) if user_id else None
    AIAnalysisService()._run("team_insights", triggered_by="manual", user=user, data_hash="")
