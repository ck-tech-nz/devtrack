import os

from celery import shared_task

from .models import TestRun
from .services import execute_ai_test_run

# Playwright sync runtime may create an event loop in worker threads. For this
# controlled background task we allow sync ORM access during execution.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

@shared_task
def run_ai_test(test_run_id: int):
    run = TestRun.objects.select_related("flow", "environment").filter(pk=test_run_id).first()
    if not run:
        return {"test_run_id": test_run_id, "status": "not_found"}
    run = execute_ai_test_run(run)
    run.refresh_from_db(fields=["status"])
    return {"test_run_id": test_run_id, "status": run.status}
