# Celery Periodic Tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Celery with Redis broker so AI insights run hourly in the background, repo pull/sync run hourly, and all schedules are managed via Django admin.

**Architecture:** Celery worker processes tasks dispatched via Redis. Celery Beat reads periodic schedules from the database (`django-celery-beat`) and dispatches tasks on schedule. Task results are stored in the database (`django-celery-results`) and visible in Django admin. The existing `AIAnalysisService`, `RepoCloneService`, and `GitHubSyncService` are reused as-is — Celery tasks are thin wrappers.

**Tech Stack:** Celery 5.x, Redis (existing), django-celery-results, django-celery-beat, Django Unfold admin

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `backend/config/celery.py` | Celery app configuration |
| Modify | `backend/config/__init__.py` | Import celery app on startup |
| Modify | `backend/config/settings.py` | Add installed apps + Celery config |
| Create | `backend/apps/ai/tasks.py` | AI insights Celery tasks |
| Modify | `backend/apps/ai/views.py` | Make GET/POST non-blocking via Celery |
| Create | `backend/apps/repos/tasks.py` | Repo pull/sync Celery tasks |
| Create | `backend/tests/test_celery_tasks.py` | Tests for all Celery tasks + views |
| Modify | `backend/pyproject.toml` | Add celery dependencies |
| Modify | `docker-compose.yml` | Add celery-worker + celery-beat |
| Modify | `servers/prod/docker-compose.yml` | Add celery-worker + celery-beat |
| Modify | `deploy/test/docker-compose.yml` | Add celery-worker + celery-beat |
| Modify | `frontend/app/pages/app/ai-insights.vue` | Handle 202 response + async refresh |

---

### Task 1: Add Celery Dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add celery packages to dependencies**

In `backend/pyproject.toml`, add to the `dependencies` list:

```toml
    "celery[redis]>=5.4,<6.0",
    "django-celery-results>=2.5,<3.0",
    "django-celery-beat>=2.7,<3.0",
```

- [ ] **Step 2: Install dependencies**

Run:
```bash
cd backend && uv sync
```

Expected: packages install successfully, no conflicts.

- [ ] **Step 3: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat(celery): add celery, django-celery-results, django-celery-beat dependencies"
```

---

### Task 2: Configure Celery App and Django Settings

**Files:**
- Create: `backend/config/celery.py`
- Modify: `backend/config/__init__.py`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Create `backend/config/celery.py`**

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("devtrack")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

- [ ] **Step 2: Update `backend/config/__init__.py`**

Replace the empty file with:

```python
from .celery import app as celery_app

__all__ = ["celery_app"]
```

- [ ] **Step 3: Add Celery settings to `backend/config/settings.py`**

Add `"django_celery_results"` and `"django_celery_beat"` to `INSTALLED_APPS`, after `"solo"`:

```python
    # Third party
    "rest_framework",
    "django_filters",
    "solo",
    "django_celery_results",
    "django_celery_beat",
```

Add Celery configuration block at the end of the file (after `BACKUP_DIR`):

```python
# Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
```

- [ ] **Step 4: Add Celery admin sections to Unfold sidebar**

In the `UNFOLD["SIDEBAR"]["navigation"]` list in `backend/config/settings.py`, add a new group after the "系统" section:

```python
            {
                "title": "定时任务",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "任务结果",
                        "icon": "task_alt",
                        "link": reverse_lazy("admin:django_celery_results_taskresult_changelist"),
                    },
                    {
                        "title": "定时任务",
                        "icon": "schedule",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                    {
                        "title": "执行间隔",
                        "icon": "timer",
                        "link": reverse_lazy("admin:django_celery_beat_intervalschedule_changelist"),
                    },
                    {
                        "title": "Cron 计划",
                        "icon": "event_repeat",
                        "link": reverse_lazy("admin:django_celery_beat_crontabschedule_changelist"),
                    },
                ],
            },
```

- [ ] **Step 5: Run migrations**

```bash
cd backend && uv run python manage.py migrate
```

Expected: migrations for `django_celery_results` and `django_celery_beat` apply successfully.

- [ ] **Step 6: Verify Celery app loads**

```bash
cd backend && uv run celery -A config inspect ping 2>&1 || echo "No worker running (expected)"
```

Expected: "Error: No running workers" (expected since no worker is running yet), but no import errors.

- [ ] **Step 7: Commit**

```bash
git add backend/config/celery.py backend/config/__init__.py backend/config/settings.py
git commit -m "feat(celery): configure celery app, django settings, and admin sidebar"
```

---

### Task 3: Create AI Insights Celery Tasks

**Files:**
- Create: `backend/apps/ai/tasks.py`
- Test: `backend/tests/test_celery_tasks.py`

- [ ] **Step 1: Write the failing tests for AI tasks**

Create `backend/tests/test_celery_tasks.py`:

```python
from unittest.mock import patch, MagicMock
import pytest
from tests.factories import LLMConfigFactory, PromptFactory, AnalysisFactory, UserFactory


@pytest.mark.django_db
class TestRunTeamInsights:
    def test_calls_get_or_run(self):
        LLMConfigFactory(is_default=True)
        PromptFactory(slug="team_insights")

        with patch("apps.ai.services.LLMClient") as mock_cls:
            mock_cls.return_value.complete.return_value = '{"trend_alerts": []}'
            from apps.ai.tasks import run_team_insights
            run_team_insights()

        from apps.ai.models import Analysis
        assert Analysis.objects.filter(
            analysis_type="team_insights", status="done"
        ).exists()

    def test_skips_when_fresh_result_exists(self):
        AnalysisFactory(
            analysis_type="team_insights", status="done",
            parsed_result={"trend_alerts": []}, data_hash="abc",
        )
        with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="abc"), \
             patch("apps.ai.services.AIAnalysisService._run") as mock_run:
            from apps.ai.tasks import run_team_insights
            run_team_insights()
        mock_run.assert_not_called()


@pytest.mark.django_db
class TestRefreshTeamInsights:
    def test_forces_new_analysis_with_user(self):
        LLMConfigFactory(is_default=True)
        PromptFactory(slug="team_insights")
        user = UserFactory()

        with patch("apps.ai.services.LLMClient") as mock_cls:
            mock_cls.return_value.complete.return_value = '{"recommendations": []}'
            from apps.ai.tasks import refresh_team_insights
            refresh_team_insights(user_id=user.id)

        from apps.ai.models import Analysis
        analysis = Analysis.objects.filter(
            analysis_type="team_insights", status="done"
        ).latest("created_at")
        assert analysis.triggered_by == "manual"
        assert analysis.triggered_by_user == user
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_celery_tasks.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.ai.tasks'`

- [ ] **Step 3: Create `backend/apps/ai/tasks.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_celery_tasks.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/ai/tasks.py backend/tests/test_celery_tasks.py
git commit -m "feat(celery): add AI insights celery tasks with tests"
```

---

### Task 4: Create Repo Pull/Sync Celery Tasks

**Files:**
- Create: `backend/apps/repos/tasks.py`
- Modify: `backend/tests/test_celery_tasks.py`

- [ ] **Step 1: Write the failing tests for repo tasks**

Append to `backend/tests/test_celery_tasks.py`:

```python
from tests.factories import RepoFactory


@pytest.mark.django_db
class TestPullAllRepos:
    def test_pulls_cloned_repos_only(self):
        cloned = RepoFactory(clone_status="cloned")
        not_cloned = RepoFactory(clone_status="not_cloned")

        with patch("apps.repos.tasks.RepoCloneService") as mock_cls:
            from apps.repos.tasks import pull_all_repos
            pull_all_repos()

        mock_cls.return_value.clone_or_pull.assert_called_once()
        call_args = mock_cls.return_value.clone_or_pull.call_args
        assert call_args[0][0].id == cloned.id

    def test_continues_on_error(self):
        RepoFactory(clone_status="cloned")
        RepoFactory(clone_status="cloned")

        with patch("apps.repos.tasks.RepoCloneService") as mock_cls:
            mock_cls.return_value.clone_or_pull.side_effect = [Exception("fail"), None]
            from apps.repos.tasks import pull_all_repos
            pull_all_repos()

        assert mock_cls.return_value.clone_or_pull.call_count == 2


@pytest.mark.django_db
class TestSyncAllRepos:
    def test_syncs_repos_with_token(self):
        with_token = RepoFactory(github_token="ghp_test123")
        without_token = RepoFactory(github_token="")

        with patch("apps.repos.tasks.GitHubSyncService") as mock_cls:
            from apps.repos.tasks import sync_all_repos
            sync_all_repos()

        mock_cls.return_value.sync_repo.assert_called_once()
        call_args = mock_cls.return_value.sync_repo.call_args
        assert call_args[0][0].id == with_token.id

    def test_continues_on_error(self):
        RepoFactory(github_token="ghp_1")
        RepoFactory(github_token="ghp_2")

        with patch("apps.repos.tasks.GitHubSyncService") as mock_cls:
            mock_cls.return_value.sync_repo.side_effect = [Exception("fail"), None]
            from apps.repos.tasks import sync_all_repos
            sync_all_repos()

        assert mock_cls.return_value.sync_repo.call_count == 2
```

- [ ] **Step 2: Run tests to verify new tests fail**

```bash
cd backend && uv run pytest tests/test_celery_tasks.py::TestPullAllRepos -v
```

Expected: `ModuleNotFoundError: No module named 'apps.repos.tasks'`

- [ ] **Step 3: Create `backend/apps/repos/tasks.py`**

```python
import logging

from celery import shared_task

from .models import Repo
from .services import RepoCloneService, GitHubSyncService

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def pull_all_repos():
    """Pull latest code for all cloned repos."""
    for repo in Repo.objects.filter(clone_status="cloned"):
        try:
            RepoCloneService().clone_or_pull(repo)
        except Exception as e:
            logger.error("Failed to pull repo %s: %s", repo.full_name, e)


@shared_task(ignore_result=False)
def sync_all_repos():
    """Sync GitHub issues for all repos with tokens."""
    for repo in Repo.objects.exclude(github_token=""):
        try:
            GitHubSyncService().sync_repo(repo)
        except Exception as e:
            logger.error("Failed to sync repo %s: %s", repo.full_name, e)
```

- [ ] **Step 4: Run all celery task tests**

```bash
cd backend && uv run pytest tests/test_celery_tasks.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/repos/tasks.py backend/tests/test_celery_tasks.py
git commit -m "feat(celery): add repo pull and sync celery tasks with tests"
```

---

### Task 5: Make AI Insights Views Non-Blocking

**Files:**
- Modify: `backend/apps/ai/views.py`
- Modify: `backend/tests/test_ai_views.py`

- [ ] **Step 1: Update tests for async behavior**

Replace `backend/tests/test_ai_views.py` with updated tests:

```python
from unittest.mock import patch
import pytest
from tests.factories import AnalysisFactory, LLMConfigFactory, PromptFactory


@pytest.mark.django_db
def test_get_insights_returns_cached_result(ai_client):
    AnalysisFactory(
        analysis_type="team_insights", status="done",
        parsed_result={"trend_alerts": []}, data_hash="abc",
    )
    with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="abc"), \
         patch("apps.ai.services.AIAnalysisService._is_stale", return_value=False):
        response = ai_client.get("/api/ai/insights/?type=team_insights")

    assert response.status_code == 200
    assert response.data["status"] == "done"
    assert response.data["result"] == {"trend_alerts": []}


@pytest.mark.django_db
def test_get_insights_returns_202_when_no_result(ai_client):
    """When no cached result exists, dispatch task and return 202."""
    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    with patch("apps.ai.tasks.run_team_insights.delay") as mock_delay:
        response = ai_client.get("/api/ai/insights/?type=team_insights")

    assert response.status_code == 202
    assert response.data["status"] == "pending"
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_get_insights_503_when_no_config(ai_client):
    """No LLMConfig and no Prompt → 503."""
    response = ai_client.get("/api/ai/insights/?type=team_insights")
    assert response.status_code == 503


@pytest.mark.django_db
def test_post_refresh_returns_202(ai_client):
    """Refresh dispatches task and returns 202."""
    with patch("apps.ai.tasks.refresh_team_insights.delay") as mock_delay:
        response = ai_client.post(
            "/api/ai/insights/refresh/", {"type": "team_insights"}, format="json"
        )

    assert response.status_code == 202
    assert response.data["status"] == "pending"
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_insights_requires_authentication(api_client):
    response = api_client.get("/api/ai/insights/?type=team_insights")
    assert response.status_code == 401


@pytest.mark.django_db
def test_sync_github_requires_staff(ai_client):
    response = ai_client.post("/api/ai/sync-github/")
    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to see failures**

```bash
cd backend && uv run pytest tests/test_ai_views.py -v
```

Expected: `test_get_insights_returns_202_when_no_result` and `test_post_refresh_returns_202` fail (views still synchronous).

- [ ] **Step 3: Update `backend/apps/ai/views.py`**

Replace `InsightsView` and `InsightsRefreshView`:

```python
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions
from .models import Analysis, LLMConfig, Prompt
from .client import LLMClient
from .services import AIConfigurationError


class InsightsView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Analysis.objects.none()

    def get(self, request):
        analysis_type = request.query_params.get("type", "team_insights")

        # Return latest cached result if available and fresh
        latest = (
            Analysis.objects.filter(analysis_type=analysis_type, status=Analysis.Status.DONE)
            .order_by("-created_at")
            .first()
        )
        if latest:
            from .services import AIAnalysisService
            if not AIAnalysisService()._is_stale(latest):
                return Response({
                    "status": latest.status,
                    "updated_at": latest.updated_at,
                    "is_fresh": True,
                    "result": latest.parsed_result,
                    "error_message": latest.error_message,
                })

        # Check configuration exists before dispatching
        has_prompt = Prompt.objects.filter(slug=analysis_type, is_active=True).exists()
        has_llm = LLMConfig.objects.filter(is_active=True).exists()
        if not has_prompt or not has_llm:
            return Response(
                {"detail": "AI 服务未配置"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Dispatch async task
        from .tasks import run_team_insights
        run_team_insights.delay()

        # Return stale result if available, otherwise pending
        if latest:
            return Response({
                "status": "running",
                "updated_at": latest.updated_at,
                "is_fresh": False,
                "result": latest.parsed_result,
                "error_message": None,
            }, status=status.HTTP_202_ACCEPTED)

        return Response({
            "status": "pending",
            "updated_at": None,
            "is_fresh": False,
            "result": None,
            "error_message": None,
        }, status=status.HTTP_202_ACCEPTED)


class InsightsRefreshView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Analysis.objects.none()

    def post(self, request):
        from .tasks import refresh_team_insights
        refresh_team_insights.delay(user_id=request.user.id)
        return Response({
            "status": "pending",
            "message": "已提交刷新请求",
        }, status=status.HTTP_202_ACCEPTED)
```

Keep `AnalysisStatusView`, `GenerateNicknameView`, and `SyncGitHubView` unchanged.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_ai_views.py -v
```

Expected: All 6 tests pass.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd backend && uv run pytest -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/ai/views.py backend/tests/test_ai_views.py
git commit -m "feat(celery): make AI insights views non-blocking via celery tasks"
```

---

### Task 6: Update Frontend to Handle Async Responses

**Files:**
- Modify: `frontend/app/pages/app/ai-insights.vue`

- [ ] **Step 1: Update `frontend/app/pages/app/ai-insights.vue` script section**

Replace the `<script setup>` block:

```typescript
<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { isOnline } = useServiceStatus()
const { api } = useApi()

const data = ref<any>(null)
const pending = ref(false)
const error = ref<any>(null)
const refreshing = ref(false)

let pollTimer: ReturnType<typeof setTimeout> | null = null

async function fetchInsights() {
  pending.value = true
  error.value = null
  try {
    const response = await api('/api/ai/insights/?type=team_insights', { raw: true })
    data.value = response._data

    // If 202, poll until result is ready
    if (response.status === 202 && !data.value?.result) {
      startPolling()
    }
  } catch (e) {
    error.value = e
  } finally {
    pending.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setTimeout(async () => {
    try {
      const response = await api('/api/ai/insights/?type=team_insights', { raw: true })
      data.value = response._data
      if (response.status === 202 && !data.value?.result) {
        startPolling()
      }
    } catch (e) {
      error.value = e
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

const insights = computed(() => data.value?.result ?? null)

async function handleRefresh() {
  refreshing.value = true
  try {
    await api('/api/ai/insights/refresh/', { method: 'POST', body: { type: 'team_insights' } })
    // Start polling for the new result
    startPolling()
  } finally {
    refreshing.value = false
  }
}

onMounted(fetchInsights)
onUnmounted(stopPolling)
</script>
```

- [ ] **Step 2: Update the loading message in the template**

Replace the loading section comment and div:

```html
    <!-- 加载中 -->
    <div v-if="pending" class="bg-white rounded-xl border border-gray-100 p-12 text-center">
      <UIcon name="i-heroicons-cpu-chip" class="w-10 h-10 text-crystal-400 mx-auto mb-3 animate-pulse" />
      <p class="text-gray-600 font-medium">AI 正在分析数据，请稍候...</p>
      <p class="text-sm text-gray-400 mt-1">首次分析可能需要 30 秒左右</p>
    </div>
```

Note: Remove `|| refreshing` from the `v-if` condition — the refresh button already shows its own loading spinner via `:loading="refreshing"`, and we want to keep showing existing data while a refresh is in progress.

- [ ] **Step 3: Verify the `useApi` composable supports raw responses**

Check if `useApi` supports a `raw: true` option. If not, use `$fetch` directly or adapt: the key behavior is detecting the 202 status code. If `useApi` always returns parsed JSON without status code, adjust by checking for `data.value?.status === 'pending'` instead:

```typescript
async function fetchInsights() {
  pending.value = true
  error.value = null
  try {
    data.value = await api('/api/ai/insights/?type=team_insights')
    // If analysis is pending/running, poll
    if (data.value?.status === 'pending' || data.value?.status === 'running') {
      startPolling()
    }
  } catch (e) {
    error.value = e
  } finally {
    pending.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setTimeout(async () => {
    try {
      data.value = await api('/api/ai/insights/?type=team_insights')
      if (data.value?.status === 'pending' || data.value?.status === 'running') {
        startPolling()
      }
    } catch (e) {
      error.value = e
    }
  }, 5000)
}
```

Use this simpler approach (check `status` field, not HTTP status code) since it works regardless of the `useApi` implementation.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/ai-insights.vue
git commit -m "feat(celery): update ai-insights page for async analysis with polling"
```

---

### Task 7: Add Docker Compose Services

**Files:**
- Modify: `docker-compose.yml`
- Modify: `servers/prod/docker-compose.yml`
- Modify: `deploy/test/docker-compose.yml`

- [ ] **Step 1: Add celery services to `docker-compose.yml` (local dev)**

Add after the `frontend` service:

```yaml
  celery-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file:
      - ./backend/.env
    environment:
      - REPO_CLONE_DIR=/data/repos
    volumes:
      - repo_data:/data/repos
    command: celery -A config worker -l info
    depends_on:
      - backend

  celery-beat:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file:
      - ./backend/.env
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers.DatabaseScheduler
    depends_on:
      - backend
```

Note: `celery-worker` needs `repo_data` volume because `pull_all_repos` task does git operations.

- [ ] **Step 2: Add celery services to `servers/prod/docker-compose.yml`**

Add after the `frontend` service:

```yaml
  celery-worker:
    image: registry.aimenu.tech/devtrack/backend-prod
    container_name: devtrack-celery-worker
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./.gitconfig-proxy:/root/.gitconfig:ro
      - repo_data:/data/repos
    networks:
      - db-network
    labels:
      - com.centurylinklabs.watchtower.enable=true
    command: celery -A config worker -l info

  celery-beat:
    image: registry.aimenu.tech/devtrack/backend-prod
    container_name: devtrack-celery-beat
    restart: unless-stopped
    env_file:
      - .env
    networks:
      - db-network
    labels:
      - com.centurylinklabs.watchtower.enable=true
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers.DatabaseScheduler
```

- [ ] **Step 3: Add celery services to `deploy/test/docker-compose.yml`**

Add after the `frontend` service:

```yaml
  celery-worker:
    image: registry.aimenu.tech/devtrack/backend-test
    container_name: devtrack-celery-worker-test
    env_file:
      - .env
    networks:
      - db-network
    command: celery -A config worker -l info

  celery-beat:
    image: registry.aimenu.tech/devtrack/backend-test
    container_name: devtrack-celery-beat-test
    env_file:
      - .env
    networks:
      - db-network
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers.DatabaseScheduler
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml servers/prod/docker-compose.yml deploy/test/docker-compose.yml
git commit -m "feat(celery): add celery worker and beat to all docker-compose files"
```

---

### Task 8: Seed Default Periodic Tasks via Data Migration

**Files:**
- Create: a new migration in `backend/apps/ai/migrations/`

- [ ] **Step 1: Create the data migration**

```bash
cd backend && uv run python manage.py makemigrations ai --empty -n seed_celery_periodic_tasks
```

- [ ] **Step 2: Write the migration code**

Edit the newly created migration file (e.g., `backend/apps/ai/migrations/XXXX_seed_celery_periodic_tasks.py`):

```python
from django.db import migrations


def seed_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Create "every 1 hour" interval
    hourly, _ = IntervalSchedule.objects.get_or_create(
        every=1, period="hours",
    )

    tasks = [
        {
            "name": "AI 团队洞察分析（每小时）",
            "task": "apps.ai.tasks.run_team_insights",
        },
        {
            "name": "拉取所有仓库代码（每小时）",
            "task": "apps.repos.tasks.pull_all_repos",
        },
        {
            "name": "同步所有 GitHub Issues（每小时）",
            "task": "apps.repos.tasks.sync_all_repos",
        },
    ]

    for task_def in tasks:
        PeriodicTask.objects.get_or_create(
            name=task_def["name"],
            defaults={
                "task": task_def["task"],
                "interval": hourly,
                "enabled": True,
            },
        )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task__in=[
            "apps.ai.tasks.run_team_insights",
            "apps.repos.tasks.pull_all_repos",
            "apps.repos.tasks.sync_all_repos",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "__latest__"),
        ("django_celery_beat", "__latest__"),
    ]

    operations = [
        migrations.RunPython(seed_periodic_tasks, remove_periodic_tasks),
    ]
```

Replace `"__latest__"` for the `"ai"` dependency with the actual latest migration name (check `backend/apps/ai/migrations/` for the last file).

- [ ] **Step 3: Run the migration**

```bash
cd backend && uv run python manage.py migrate
```

Expected: migration applies, 3 periodic tasks created.

- [ ] **Step 4: Verify in Django shell**

```bash
cd backend && uv run python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(list(PeriodicTask.objects.values_list('name', 'task', 'enabled')))"
```

Expected: 3 tasks listed, all enabled.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/ai/migrations/
git commit -m "feat(celery): seed default hourly periodic tasks via data migration"
```

---

### Task 9: Add Celery Test Configuration

**Files:**
- Modify: `backend/pytest.ini`

- [ ] **Step 1: Add Celery eager mode for tests**

The tests call tasks synchronously (not via `.delay()`), so they already work. But for view tests that mock `.delay()`, ensure `CELERY_TASK_ALWAYS_EAGER` is NOT set (we want to verify `.delay()` is called, not execute the task).

Verify existing tests pass with the full suite:

```bash
cd backend && uv run pytest -v
```

Expected: All tests pass (tasks are either called directly or mocked).

- [ ] **Step 2: Commit if any changes needed**

Only commit if changes were required. If all tests pass as-is, skip this commit.

---

### Task 10: Final Verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && uv run pytest -v
```

Expected: All tests pass.

- [ ] **Step 2: Start Celery worker locally and verify**

Terminal 1:
```bash
cd backend && uv run celery -A config worker -l info
```

Terminal 2:
```bash
cd backend && uv run celery -A config beat -l info --scheduler django_celery_beat.schedulers.DatabaseScheduler
```

Expected: Worker connects to Redis, Beat starts and loads 3 periodic tasks.

- [ ] **Step 3: Verify Django admin**

Navigate to `/admin/` and confirm:
- "定时任务" sidebar section exists with 4 links
- "任务结果" page loads (empty initially)
- "定时任务" page shows 3 seeded tasks
- Tasks are editable (can change interval, enable/disable)

- [ ] **Step 4: Test end-to-end**

Visit `/app/ai-insights` — should show cached result instantly or "pending" state, then poll until result appears. Click "刷新" — should return immediately, then poll for new result.

- [ ] **Step 5: Final commit if needed**

```bash
git add -A && git status
```

Only commit if there are uncommitted changes from fixes.
