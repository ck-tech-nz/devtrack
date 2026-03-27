from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Issue


@receiver(post_save, sender=Issue)
def trigger_ai_analysis(sender, instance, created, update_fields, **kwargs):
    if created:
        _maybe_analyze(instance, triggered_by="auto")
    elif update_fields and "description" in update_fields:
        _maybe_analyze(instance, triggered_by="auto")


def _maybe_analyze(issue, triggered_by):
    if not issue.repo_id:
        return
    from apps.repos.models import Repo
    try:
        repo = Repo.objects.get(pk=issue.repo_id)
    except Repo.DoesNotExist:
        return
    if repo.clone_status != "cloned":
        return

    from apps.ai.services import IssueAnalysisService
    svc = IssueAnalysisService()
    if svc.get_running_analysis(issue):
        return
    svc.analyze_async(issue, triggered_by=triggered_by)
