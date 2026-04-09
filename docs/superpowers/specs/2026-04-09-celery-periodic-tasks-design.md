# Add Celery with Periodic Tasks via Django Admin

**Date:** 2026-04-09
**Status:** Approved

## Problem

The AI insights page (`/app/ai-insights`) runs analysis synchronously during the HTTP request, making users wait ~30 seconds. Repo pull and GitHub issue sync are manual-only. All three should run automatically on a schedule.

## Solution

Add Celery (with Redis broker) for background task execution and periodic scheduling. Schedules are managed via Django admin using `django-celery-beat`. Task results are stored in the database and visible in Django admin via `django-celery-results`.

## Dependencies

Add to `backend/pyproject.toml`:
- `celery[redis]` — task queue with Redis broker
- `django-celery-results` — store task results in DB, auto-registers in admin
- `django-celery-beat` — DB-backed periodic task scheduler, admin-managed

## New Files

### `backend/config/celery.py`
Celery app configuration:
- Set `DJANGO_SETTINGS_MODULE`
- Create Celery app with namespace `CELERY`
- `autodiscover_tasks()` to find `tasks.py` in all apps

### `backend/config/__init__.py`
Import celery app so it's loaded on Django startup:
```python
from .celery import app as celery_app
__all__ = ["celery_app"]
```

### `backend/apps/ai/tasks.py`
```python
@shared_task
def run_team_insights():
    """Hourly team insights analysis. Skips if latest result is still fresh."""
    AIAnalysisService().get_or_run("team_insights", triggered_by="auto")

@shared_task
def refresh_team_insights(user_id=None):
    """Manual refresh triggered from UI."""
    user = User.objects.get(pk=user_id) if user_id else None
    AIAnalysisService()._run("team_insights", triggered_by="manual", user=user)
```

### `backend/apps/repos/tasks.py`
```python
@shared_task
def pull_all_repos():
    """Pull latest code for all cloned repos."""
    for repo in Repo.objects.filter(clone_status="cloned"):
        try:
            RepoCloneService().clone_or_pull(repo)
        except Exception as e:
            logger.error("Failed to pull repo %s: %s", repo.full_name, e)

@shared_task
def sync_all_repos():
    """Sync GitHub issues for all repos with tokens."""
    for repo in Repo.objects.exclude(github_token=""):
        try:
            GitHubSyncService().sync_repo(repo)
        except Exception as e:
            logger.error("Failed to sync repo %s: %s", repo.full_name, e)
```

## Settings Changes (`backend/config/settings.py`)

Add to `INSTALLED_APPS`:
- `"django_celery_results"`
- `"django_celery_beat"`

Add Celery config:
```python
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
```

## View Changes (`backend/apps/ai/views.py`)

### `InsightsView` (GET)
- Return latest `DONE` analysis from DB instantly
- If no analysis exists, dispatch `run_team_insights.delay()` and return 202 with status "pending"
- No more blocking synchronous LLM calls during requests

### `InsightsRefreshView` (POST)
- Dispatch `refresh_team_insights.delay(user_id=request.user.id)` 
- Return 202 immediately (non-blocking)

## Docker Changes

Add to both `docker-compose.yml` (local) and `servers/prod/docker-compose.yml`:

```yaml
celery-worker:
  image: <same backend image>
  env_file: <same as backend>
  volumes: <same as backend>
  command: celery -A config worker -l info
  depends_on:
    - backend

celery-beat:
  image: <same backend image>
  env_file: <same as backend>
  command: celery -A config beat -l info --scheduler django_celery_beat.schedulers.DatabaseScheduler
  depends_on:
    - backend
```

No new Redis container — existing Redis instances used in both environments.

## Django Admin

Automatically registered by packages:

**Celery Beat (schedule management):**
- Periodic Tasks — create/edit/disable scheduled tasks
- Intervals — e.g., "every 1 hour"
- Crontabs — e.g., "0 * * * *"
- Solar events, Clocked tasks

**Celery Results (task history):**
- TaskResult — task name, status (SUCCESS/FAILURE), result data, traceback, timestamps

## Default Schedule Seeding

A data migration seeds 3 default periodic tasks (all hourly, all enabled):
1. `apps.ai.tasks.run_team_insights` — AI team insights analysis
2. `apps.repos.tasks.pull_all_repos` — Git pull all cloned repos
3. `apps.repos.tasks.sync_all_repos` — Sync GitHub issues for all repos

These are editable/disableable in Django admin after creation.

## Frontend Changes (`frontend/app/pages/app/ai-insights.vue`)

Minimal:
- Handle 202 response from GET: show existing "AI 正在分析数据" loading state, with note that first analysis is being generated
- Handle 202 from POST refresh: show brief toast/message "已提交刷新请求" instead of blocking spinner
- If a cached result exists, display it immediately (main happy path after Celery runs)

## Environment Variables

Add to `.env` files:
```
CELERY_BROKER_URL=redis://<redis-host>:6379/0
```

## Not Included

- No Flower (Celery monitoring UI) — Django admin provides sufficient visibility
- No retry policies — tasks are idempotent and run hourly, a missed run self-corrects
- No separate queues — single default queue is sufficient for 3 tasks
