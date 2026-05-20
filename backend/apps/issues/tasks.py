"""Celery tasks for issue-side AI work that the submitter doesn't need to wait for.

Auto-assign is the canonical example: picking who handles an Issue has no
bearing on whether the submitter's draft matches their intent, so it runs
off the critical path. The wizard POST returns the Issue immediately
(status=待分配); the worker picks an assignee and flips status to 待确认
shortly after.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, autoretry_for=(Exception,),
             retry_backoff=True, retry_kwargs={"max_retries": 2})
def auto_assign_issue_task(issue_id):
    """LLM-pick + assign the developer for a freshly created Issue.

    Idempotency: skips silently if the Issue already has an assignee or has
    moved past 待分配 (someone claimed/transferred it before the worker ran).
    """
    from apps.issues.models import Issue, IssueStatus
    from apps.issues.services import auto_assign_issue

    issue = Issue.objects.filter(pk=issue_id).first()
    if issue is None:
        logger.info("auto_assign_task: issue %s no longer exists; skipping", issue_id)
        return
    if issue.assignee_id is not None or issue.status != IssueStatus.UNASSIGNED.value:
        logger.info(
            "auto_assign_task: issue %s already has assignee=%s status=%s; skipping",
            issue_id, issue.assignee_id, issue.status,
        )
        return
    auto_assign_issue(issue)
