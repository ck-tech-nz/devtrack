# AI Code Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add code-aware AI analysis to Issues by cloning repos to the server, integrating opencode CLI for code understanding, and exposing git log + AI analysis on the frontend.

**Architecture:** Django backend extended with RepoCloneService (subprocess git), OpenCodeRunner (subprocess opencode), and IssueAnalysisService (async via ThreadPoolExecutor). Project.linked_repos JSONField migrated to M2M. Issue gets repo FK. Frontend adds clone/git-log to repo pages and AI analyze button to issue detail.

**Tech Stack:** Django REST Framework, subprocess (git + opencode), ThreadPoolExecutor, Nuxt 4 (Vue 3), Nuxt UI.

**Spec:** `docs/superpowers/specs/2026-03-25-ai-code-analysis-design.md`

---

## File Map

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `backend/apps/ai/opencode.py` | OpenCodeRunner: generate opencode config, run subprocess, parse output |
| `backend/apps/issues/signals.py` | post_save signal: auto-trigger AI analysis on Issue create/update |
| `backend/tests/test_repo_clone_service.py` | Tests for RepoCloneService |
| `backend/tests/test_opencode_runner.py` | Tests for OpenCodeRunner |
| `backend/tests/test_issue_analysis.py` | Tests for IssueAnalysisService + views + signals |

### Backend — Modified Files

| File | Changes |
|------|---------|
| `backend/apps/repos/models.py` | Repo: +clone_status, +clone_error, +current_branch, +cloned_at, +local_path property |
| `backend/apps/repos/services.py` | +RepoCloneService class |
| `backend/apps/repos/serializers.py` | RepoSerializer: +clone fields |
| `backend/apps/repos/views.py` | +RepoCloneView, +RepoGitLogView, +RepoBranchesView |
| `backend/apps/repos/urls.py` | +3 URL patterns |
| `backend/apps/projects/models.py` | Project: linked_repos JSONField → repos M2M |
| `backend/apps/projects/serializers.py` | Update all serializers for repos M2M |
| `backend/apps/issues/models.py` | Issue: +repo FK |
| `backend/apps/issues/serializers.py` | +repo field in list/detail/create serializers |
| `backend/apps/issues/views.py` | +IssueAIAnalyzeView |
| `backend/apps/issues/urls.py` | +1 URL pattern |
| `backend/apps/issues/apps.py` | Register signal in ready() |
| `backend/apps/ai/models.py` | Analysis: +issue FK, +TriggerType.AUTO |
| `backend/apps/ai/services.py` | +IssueAnalysisService, +_executor ThreadPoolExecutor |
| `backend/apps/ai/views.py` | +AnalysisStatusView |
| `backend/apps/ai/urls.py` | +1 URL pattern |
| `backend/apps/ai/apps.py` | +startup cleanup in ready() |
| `backend/config/settings.py` | +REPO_CLONE_DIR setting |
| `backend/tests/factories.py` | Update factories for new fields |
| `backend/tests/conftest.py` | +fixtures if needed |

### Frontend — Modified Files

| File | Changes |
|------|---------|
| `frontend/app/pages/app/repos/[id]/index.vue` | +clone button, +status badge, +git log tab, +branch switcher |
| `frontend/app/pages/app/issues/[id].vue` | +AI analyze button, +AI content rendering |
| `frontend/app/pages/app/issues/index.vue` | +repo field in create form (auto-populate logic) |

---

## Task 1: Repo Model — Add Clone Fields + Migration

**Files:**
- Modify: `backend/apps/repos/models.py:4-20`
- Create: `backend/apps/repos/migrations/0004_repo_clone_fields.py` (auto-generated)

- [ ] **Step 1: Add clone fields to Repo model**

In `backend/apps/repos/models.py`, add after line 15 (`last_synced_at`):

```python
import os
import re
from django.conf import settings as django_settings

class Repo(models.Model):
    CLONE_STATUS_CHOICES = [
        ("not_cloned", "未克隆"),
        ("cloning", "克隆中"),
        ("cloned", "已克隆"),
        ("failed", "失败"),
    ]

    # ... existing fields ...
    clone_status = models.CharField(
        max_length=20, choices=CLONE_STATUS_CHOICES,
        default="not_cloned", verbose_name="克隆状态",
    )
    clone_error = models.TextField(blank=True, verbose_name="克隆错误信息")
    current_branch = models.CharField(max_length=100, blank=True, verbose_name="当前分支")
    cloned_at = models.DateTimeField(null=True, blank=True, verbose_name="克隆时间")

    @property
    def local_path(self) -> str:
        if not re.match(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$', self.full_name):
            raise ValueError(f"Invalid repo full_name: {self.full_name}")
        return os.path.join(django_settings.REPO_CLONE_DIR, self.full_name)
```

- [ ] **Step 2: Add REPO_CLONE_DIR to settings**

In `backend/config/settings.py`, add near the bottom:

```python
REPO_CLONE_DIR = os.environ.get("REPO_CLONE_DIR", "/data/repos")
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend && uv run python manage.py makemigrations repos --name repo_clone_fields
cd backend && uv run python manage.py migrate
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/repos/models.py backend/apps/repos/migrations/ backend/config/settings.py
git commit -m "feat(repos): add clone_status, clone_error, current_branch, cloned_at fields"
```

---

## Task 2: Project Model — Migrate linked_repos JSONField to repos M2M

**Files:**
- Modify: `backend/apps/projects/models.py:14`
- Create: 3 migration files (auto-generated + manual data migration)

This is a 3-step migration: add M2M → data migration → remove JSONField.

- [ ] **Step 1: Add repos M2M field alongside existing linked_repos**

In `backend/apps/projects/models.py`, add after `linked_repos` (line 14):

```python
repos = models.ManyToManyField(
    "repos.Repo", blank=True, related_name="projects",
    verbose_name="关联仓库",
)
```

- [ ] **Step 2: Generate schema migration**

```bash
cd backend && uv run python manage.py makemigrations projects --name add_repos_m2m
```

- [ ] **Step 3: Create data migration**

```bash
cd backend && uv run python manage.py makemigrations projects --empty --name migrate_linked_repos_to_m2m
```

Edit the generated migration file:

```python
from django.db import migrations


def migrate_linked_repos(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Repo = apps.get_model("repos", "Repo")
    for project in Project.objects.all():
        if not project.linked_repos:
            continue
        for repo_id in project.linked_repos:
            try:
                repo = Repo.objects.get(pk=repo_id)
                project.repos.add(repo)
            except Repo.DoesNotExist:
                pass


def reverse_migrate(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    for project in Project.objects.all():
        project.linked_repos = list(project.repos.values_list("id", flat=True))
        project.save(update_fields=["linked_repos"])


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "XXXX_add_repos_m2m"),  # replace with actual name
    ]

    operations = [
        migrations.RunPython(migrate_linked_repos, reverse_migrate),
    ]
```

- [ ] **Step 4: Remove linked_repos JSONField**

In `backend/apps/projects/models.py`, remove line 14 (`linked_repos = models.JSONField(...)`).

```bash
cd backend && uv run python manage.py makemigrations projects --name remove_linked_repos_json
```

- [ ] **Step 5: Apply all migrations**

```bash
cd backend && uv run python manage.py migrate
```

- [ ] **Step 6: Update Project serializers**

In `backend/apps/projects/serializers.py`:

Replace `linked_repos` with `repos` in all serializer Meta.fields lists. In `ProjectListSerializer` and `ProjectDetailSerializer`, add a nested read field:

```python
from apps.repos.serializers import RepoSerializer as RepoNestedSerializer

class ProjectListSerializer(serializers.ModelSerializer):
    repos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # ... rest unchanged ...

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "repos",
            "member_count", "issue_count", "created_at", "updated_at",
        ]

class ProjectDetailSerializer(serializers.ModelSerializer):
    repos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # ...
    class Meta:
        fields = [
            "id", "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "repos",
            "members", "created_at", "updated_at",
        ]

class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        fields = [
            "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "repos",
        ]
```

- [ ] **Step 7: Run tests to verify nothing breaks**

```bash
cd backend && uv run pytest -x
```

- [ ] **Step 8: Commit**

```bash
git add backend/apps/projects/ backend/tests/
git commit -m "feat(projects): migrate linked_repos JSONField to repos M2M"
```

---

## Task 3: Issue Model — Add repo FK + Migration

**Files:**
- Modify: `backend/apps/issues/models.py:5-14`
- Modify: `backend/apps/issues/serializers.py`
- Create: migration (auto-generated)

- [ ] **Step 1: Add repo FK to Issue model**

In `backend/apps/issues/models.py`, add after `github_issues` M2M (line 14):

```python
repo = models.ForeignKey(
    "repos.Repo", on_delete=models.SET_NULL,
    null=True, blank=True, related_name="issues",
    verbose_name="关联仓库",
)
```

- [ ] **Step 2: Generate and apply migration**

```bash
cd backend && uv run python manage.py makemigrations issues --name issue_repo_fk
cd backend && uv run python manage.py migrate
```

- [ ] **Step 3: Add repo to Issue serializers**

In `backend/apps/issues/serializers.py`:

Add `"repo"` to `IssueListSerializer.Meta.fields` (after `"project"`).
Add `"repo"` to `IssueCreateUpdateSerializer.Meta.fields` (after `"project"`).

- [ ] **Step 4: Update IssueFactory**

In `backend/tests/factories.py`, add to `IssueFactory`:

```python
repo = None  # Optional, set in tests that need it
```

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest -x
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/issues/ backend/tests/factories.py
git commit -m "feat(issues): add repo FK for direct repo association"
```

---

## Task 4: Analysis Model — Add issue FK + TriggerType.AUTO

**Files:**
- Modify: `backend/apps/ai/models.py:58-100`
- Create: migration (auto-generated)

- [ ] **Step 1: Add issue FK and AUTO trigger type**

In `backend/apps/ai/models.py`, add to `Analysis`:

```python
# Add to TriggerType choices (after MANUAL line):
AUTO = "auto", "自动触发"

# Add new field (after triggered_by_user):
issue = models.ForeignKey(
    "issues.Issue", on_delete=models.CASCADE,
    null=True, blank=True, related_name="analyses",
    verbose_name="关联问题",
)
```

- [ ] **Step 2: Generate and apply migration**

```bash
cd backend && uv run python manage.py makemigrations ai --name analysis_issue_fk_auto_trigger
cd backend && uv run python manage.py migrate
```

- [ ] **Step 3: Update AnalysisFactory**

In `backend/tests/factories.py`, add to `AnalysisFactory`:

```python
issue = None
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest -x
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/ai/ backend/tests/factories.py
git commit -m "feat(ai): add issue FK and auto trigger type to Analysis"
```

---

## Task 5: RepoCloneService — Tests + Implementation

**Files:**
- Create: `backend/tests/test_repo_clone_service.py`
- Modify: `backend/apps/repos/services.py`

- [ ] **Step 1: Write tests for RepoCloneService**

Create `backend/tests/test_repo_clone_service.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from apps.repos.services import RepoCloneService
from tests.factories import RepoFactory


MOCK_CLONE_DIR = "/tmp/test_repos"


@override_settings(REPO_CLONE_DIR=MOCK_CLONE_DIR)
class TestRepoCloneService:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.svc = RepoCloneService()
        self.repo = RepoFactory(full_name="myorg/myrepo", github_token="ghp_test123")

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=False)
    @patch("apps.repos.services.os.makedirs")
    def test_clone_new_repo(self, mock_makedirs, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.svc.clone_or_pull(self.repo)
        self.repo.refresh_from_db()
        assert self.repo.clone_status == "cloned"
        assert self.repo.cloned_at is not None
        assert self.repo.clone_error == ""

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_pull_existing_repo(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.repo.clone_status = "cloned"
        self.repo.save()
        self.svc.clone_or_pull(self.repo)
        self.repo.refresh_from_db()
        assert self.repo.clone_status == "cloned"

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=False)
    @patch("apps.repos.services.os.makedirs")
    def test_clone_failure_sets_failed_status(self, mock_makedirs, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: auth failed")
        mock_subprocess.CalledProcessError = Exception
        self.svc.clone_or_pull(self.repo)
        self.repo.refresh_from_db()
        assert self.repo.clone_status == "failed"
        assert "fatal: auth failed" in self.repo.clone_error

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_switch_branch(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.repo.clone_status = "cloned"
        self.repo.save()
        self.svc.clone_or_pull(self.repo, branch="develop")
        self.repo.refresh_from_db()
        assert self.repo.current_branch == "develop"

    def test_local_path_validation_rejects_traversal(self, db):
        repo = RepoFactory(full_name="../etc/passwd")
        with pytest.raises(ValueError):
            _ = repo.local_path

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_get_log(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="abc123\x00Alice\x002026-03-25T10:00:00+08:00\x00fix bug\nabc456\x00Bob\x002026-03-24T09:00:00+08:00\x00add feature",
            stderr="",
        )
        result = self.svc.get_log(self.repo, limit=2)
        assert len(result) == 2
        assert result[0]["hash"] == "abc123"
        assert result[0]["author"] == "Alice"
        assert result[0]["message"] == "fix bug"

    @patch("apps.repos.services.subprocess")
    @patch("apps.repos.services.os.path.exists", return_value=True)
    def test_get_branches(self, mock_exists, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="origin/main\norigin/develop\norigin/feature/x",
            stderr="",
        )
        result = self.svc.get_branches(self.repo)
        assert "origin/main" in result
        assert len(result) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_repo_clone_service.py -v
```

Expected: ImportError or AttributeError (RepoCloneService doesn't exist yet).

- [ ] **Step 3: Implement RepoCloneService**

In `backend/apps/repos/services.py`, add at the top-level:

```python
import os
import stat
import subprocess
import tempfile

from django.conf import settings as django_settings
from django.utils import timezone


class RepoCloneService:
    def clone_or_pull(self, repo, branch=None):
        repo.clone_status = "cloning"
        repo.clone_error = ""
        repo.save(update_fields=["clone_status", "clone_error"])

        askpass_path = None
        try:
            local_path = repo.local_path
            env, askpass_path = self._make_askpass(repo.github_token)

            if not os.path.exists(local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                clone_url = repo.url if repo.url.endswith(".git") else f"{repo.url}.git"
                subprocess.run(
                    ["git", "clone", clone_url, local_path],
                    env=env, capture_output=True, text=True,
                    timeout=300, check=True,
                )
            else:
                subprocess.run(
                    ["git", "-C", local_path, "fetch", "--all"],
                    env=env, capture_output=True, text=True,
                    timeout=300, check=True,
                )
                target = branch or repo.default_branch or "main"
                subprocess.run(
                    ["git", "-C", local_path, "reset", "--hard", f"origin/{target}"],
                    capture_output=True, text=True, timeout=60, check=True,
                )

            if branch:
                subprocess.run(
                    ["git", "-C", local_path, "checkout", branch],
                    env=env, capture_output=True, text=True,
                    timeout=60, check=True,
                )
                repo.current_branch = branch
            else:
                repo.current_branch = branch or repo.default_branch or "main"

            repo.clone_status = "cloned"
            repo.cloned_at = timezone.now()
            repo.save(update_fields=["clone_status", "clone_error", "current_branch", "cloned_at"])
        except subprocess.CalledProcessError as e:
            repo.clone_status = "failed"
            repo.clone_error = e.stderr or str(e)
            repo.save(update_fields=["clone_status", "clone_error"])
        except Exception as e:
            repo.clone_status = "failed"
            repo.clone_error = str(e)
            repo.save(update_fields=["clone_status", "clone_error"])
        finally:
            self._cleanup_askpass(askpass_path)

    def get_log(self, repo, limit=50):
        local_path = repo.local_path
        if not os.path.exists(local_path):
            return []
        result = subprocess.run(
            ["git", "-C", local_path, "log",
             "--format=%H%x00%an%x00%aI%x00%s", f"-n{limit}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\x00")
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })
        return commits

    def get_branches(self, repo):
        local_path = repo.local_path
        if not os.path.exists(local_path):
            return []
        result = subprocess.run(
            ["git", "-C", local_path, "branch", "-r",
             "--format=%(refname:short)"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        return [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]

    @staticmethod
    def _make_askpass(token):
        """Create a temp GIT_ASKPASS script. Returns (env_dict, file_path)."""
        env = os.environ.copy()
        if not token:
            return env, None
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False)
        f.write(f"#!/bin/sh\necho {token}\n")
        f.close()
        os.chmod(f.name, stat.S_IRWXU)
        env["GIT_ASKPASS"] = f.name
        env["GIT_TERMINAL_PROMPT"] = "0"
        return env, f.name

    @staticmethod
    def _cleanup_askpass(askpass_path):
        if askpass_path:
            try:
                os.unlink(askpass_path)
            except OSError:
                pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_repo_clone_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/repos/services.py backend/tests/test_repo_clone_service.py
git commit -m "feat(repos): add RepoCloneService with secure git auth"
```

---

## Task 6: Repo API Endpoints — Clone, Git Log, Branches

**Files:**
- Modify: `backend/apps/repos/serializers.py:32-46`
- Modify: `backend/apps/repos/views.py`
- Modify: `backend/apps/repos/urls.py`

- [ ] **Step 1: Update RepoSerializer with clone fields**

In `backend/apps/repos/serializers.py`, add to `RepoSerializer.Meta.fields` list:

```python
fields = [
    "id", "name", "full_name", "url", "description",
    "default_branch", "language", "stars", "status",
    "connected_at", "last_synced_at",
    "clone_status", "clone_error", "current_branch", "cloned_at",
    "open_issues_count", "closed_issues_count",
]
read_only_fields = [
    "id", "connected_at", "last_synced_at",
    "clone_status", "clone_error", "current_branch", "cloned_at",
]
```

- [ ] **Step 2: Add views**

In `backend/apps/repos/views.py`, add:

```python
from concurrent.futures import ThreadPoolExecutor
from .services import RepoCloneService

_clone_executor = ThreadPoolExecutor(max_workers=2)


class RepoCloneView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def post(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)

        if repo.clone_status == "cloning":
            return Response(
                {"detail": "克隆任务进行中", "clone_status": "cloning"},
                status=status.HTTP_409_CONFLICT,
            )

        branch = request.data.get("branch")
        # clone_or_pull sets clone_status="cloning" itself; don't duplicate here
        _clone_executor.submit(RepoCloneService().clone_or_pull, repo, branch)
        return Response(
            {"detail": "克隆任务已启动", "clone_status": "cloning"},
            status=status.HTTP_202_ACCEPTED,
        )


class RepoGitLogView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def get(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)

        if repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)

        limit = min(int(request.query_params.get("limit", 50)), 200)
        commits = RepoCloneService().get_log(repo, limit=limit)
        return Response(commits)


class RepoBranchesView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def get(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)

        if repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)

        branches = RepoCloneService().get_branches(repo)
        return Response(branches)
```

- [ ] **Step 3: Add URL patterns**

In `backend/apps/repos/urls.py`, update imports and add patterns:

```python
from .views import (
    RepoListCreateView, RepoDetailView, GitHubIssueListView,
    RepoSyncView, GitHubIssueDetailView,
    RepoCloneView, RepoGitLogView, RepoBranchesView,
)

urlpatterns = [
    path("", RepoListCreateView.as_view(), name="repo-list"),
    path("github-issues/", GitHubIssueListView.as_view(), name="github-issue-list"),
    path("github-issues/<int:pk>/", GitHubIssueDetailView.as_view(), name="github-issue-detail"),
    path("<int:pk>/sync/", RepoSyncView.as_view(), name="repo-sync"),
    path("<int:pk>/clone/", RepoCloneView.as_view(), name="repo-clone"),
    path("<int:pk>/git-log/", RepoGitLogView.as_view(), name="repo-git-log"),
    path("<int:pk>/branches/", RepoBranchesView.as_view(), name="repo-branches"),
    path("<int:pk>/", RepoDetailView.as_view(), name="repo-detail"),
]
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && uv run pytest -x
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/repos/
git commit -m "feat(repos): add clone, git-log, branches API endpoints"
```

---

## Task 7: OpenCodeRunner — Tests + Implementation

**Files:**
- Create: `backend/apps/ai/opencode.py`
- Create: `backend/tests/test_opencode_runner.py`

- [ ] **Step 1: Write tests**

Create `backend/tests/test_opencode_runner.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from apps.ai.opencode import OpenCodeRunner
from tests.factories import LLMConfigFactory, PromptFactory


class TestOpenCodeRunner:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.config = LLMConfigFactory(
            api_key="sk-test123",
            base_url="https://api.deepseek.com/v1",
        )
        self.prompt = PromptFactory(llm_model="deepseek-chat")
        self.runner = OpenCodeRunner(self.config)

    def test_generate_config(self):
        config = self.runner.generate_config("deepseek-chat")
        assert "provider" in config
        provider = list(config["provider"].values())[0]
        assert provider["options"]["apiKey"] == "sk-test123"
        assert provider["options"]["baseURL"] == "https://api.deepseek.com/v1"

    @patch("apps.ai.opencode.subprocess")
    @patch("apps.ai.opencode.tempfile")
    def test_run_success(self, mock_tempfile, mock_subprocess):
        mock_tempfile.NamedTemporaryFile.return_value.__enter__ = MagicMock()
        mock_tempfile.NamedTemporaryFile.return_value.__exit__ = MagicMock()
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout='{"target_field": "cause", "content": "分析结果"}',
            stderr="",
        )
        result = self.runner.run(
            repo_path="/data/repos/org/repo",
            prompt="分析这个问题",
            model=self.prompt.llm_model,
        )
        assert "分析结果" in result

    @patch("apps.ai.opencode.subprocess")
    def test_run_timeout(self, mock_subprocess):
        import subprocess as sp
        mock_subprocess.TimeoutExpired = sp.TimeoutExpired
        mock_subprocess.run.side_effect = sp.TimeoutExpired(cmd="opencode", timeout=120)
        with pytest.raises(sp.TimeoutExpired):
            self.runner.run(
                repo_path="/data/repos/org/repo",
                prompt="分析",
                model=self.prompt.llm_model,
            )

    def test_check_health_missing_binary(self):
        with patch("apps.ai.opencode.shutil.which", return_value=None):
            assert self.runner.check_health() is False

    def test_check_health_present(self):
        with patch("apps.ai.opencode.shutil.which", return_value="/usr/local/bin/opencode"):
            assert self.runner.check_health() is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_opencode_runner.py -v
```

- [ ] **Step 3: Implement OpenCodeRunner**

Create `backend/apps/ai/opencode.py`:

```python
import json
import os
import shutil
import subprocess
import tempfile


class OpenCodeRunner:
    def __init__(self, llm_config):
        self.llm_config = llm_config

    def check_health(self) -> bool:
        return shutil.which("opencode") is not None

    def generate_config(self, model: str) -> dict:
        provider_id = self.llm_config.name.lower().replace(" ", "_")
        return {
            "provider": {
                provider_id: {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": self.llm_config.name,
                    "options": {
                        "baseURL": self.llm_config.base_url,
                        "apiKey": self.llm_config.api_key,
                    },
                    "models": {
                        model: {"name": model},
                    },
                }
            },
            "model": f"{provider_id}/{model}",
        }

    def run(self, repo_path: str, prompt: str, model: str,
            timeout: int = 120) -> str:
        config = self.generate_config(model)
        config_path = os.path.join(repo_path, "opencode.json")
        try:
            with open(config_path, "w") as f:
                json.dump(config, f)
            result = subprocess.run(
                ["opencode", "-p", prompt],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/test_opencode_runner.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/ai/opencode.py backend/tests/test_opencode_runner.py
git commit -m "feat(ai): add OpenCodeRunner for opencode CLI integration"
```

---

## Task 8: IssueAnalysisService — Tests + Implementation

**Files:**
- Create: `backend/tests/test_issue_analysis.py`
- Modify: `backend/apps/ai/services.py`

- [ ] **Step 1: Write tests**

Create `backend/tests/test_issue_analysis.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from apps.ai.services import IssueAnalysisService
from apps.ai.models import Analysis
from tests.factories import (
    IssueFactory, RepoFactory, PromptFactory, LLMConfigFactory, AnalysisFactory,
)


@override_settings(REPO_CLONE_DIR="/tmp/test_repos")
class TestIssueAnalysisService:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.config = LLMConfigFactory(is_default=True)
        self.prompt = PromptFactory(
            slug="issue_code_analysis",
            system_prompt="你是代码分析专家",
            user_prompt_template="分析问题: {title}\n描述: {description}",
        )
        self.repo = RepoFactory(clone_status="cloned")
        self.issue = IssueFactory(repo=self.repo)
        self.svc = IssueAnalysisService()

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analyze_appends_to_cause(self, MockRunner):
        mock_instance = MockRunner.return_value
        mock_instance.run.return_value = json.dumps({
            "target_field": "cause",
            "content": "根因是空指针"
        })
        mock_instance.check_health.return_value = True

        analysis = self.svc.analyze(self.issue, triggered_by="manual")
        self.issue.refresh_from_db()

        assert analysis.status == "done"
        assert "🤖 AI 分析" in self.issue.cause
        assert "根因是空指针" in self.issue.cause

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analyze_rejects_invalid_field(self, MockRunner):
        mock_instance = MockRunner.return_value
        mock_instance.run.return_value = json.dumps({
            "target_field": "status",
            "content": "恶意内容"
        })
        mock_instance.check_health.return_value = True

        analysis = self.svc.analyze(self.issue, triggered_by="manual")
        assert analysis.status == "failed"
        assert "Invalid target field" in analysis.error_message

    def test_analyze_requires_cloned_repo(self):
        self.repo.clone_status = "not_cloned"
        self.repo.save()
        with pytest.raises(ValueError, match="请先同步代码"):
            self.svc.analyze(self.issue, triggered_by="manual")

    def test_analyze_requires_repo(self):
        self.issue.repo = None
        self.issue.save()
        with pytest.raises(ValueError, match="请先关联仓库"):
            self.svc.analyze(self.issue, triggered_by="manual")

    def test_no_duplicate_running_analysis(self):
        AnalysisFactory(
            issue=self.issue,
            analysis_type="issue_code_analysis",
            status="running",
        )
        existing = self.svc.get_running_analysis(self.issue)
        assert existing is not None

    def test_cleanup_stale_analyses(self, db):
        from django.utils import timezone
        from datetime import timedelta
        stale = AnalysisFactory(
            status="running",
            analysis_type="issue_code_analysis",
        )
        # Manually backdate
        Analysis.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        IssueAnalysisService.cleanup_stale_analyses()
        stale.refresh_from_db()
        assert stale.status == "failed"
        assert "进程异常终止" in stale.error_message

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analyze_preserves_existing_content(self, MockRunner):
        self.issue.cause = "用户手动输入的原因"
        self.issue.save()

        mock_instance = MockRunner.return_value
        mock_instance.run.return_value = json.dumps({
            "target_field": "cause",
            "content": "AI补充分析"
        })
        mock_instance.check_health.return_value = True

        self.svc.analyze(self.issue, triggered_by="manual")
        self.issue.refresh_from_db()

        assert "用户手动输入的原因" in self.issue.cause
        assert "AI补充分析" in self.issue.cause
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_issue_analysis.py -v
```

- [ ] **Step 3: Implement IssueAnalysisService**

In `backend/apps/ai/services.py`, add imports and new class:

```python
import logging
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction, close_old_connections
from apps.issues.models import Issue
from .opencode import OpenCodeRunner

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


class IssueAnalysisService:
    ALLOWED_FIELDS = {"cause", "solution", "remark"}

    def analyze(self, issue, triggered_by="manual", user=None):
        """Synchronous analysis — creates Analysis, runs, returns it."""
        if not issue.repo:
            raise ValueError("请先关联仓库")
        if issue.repo.clone_status != "cloned":
            raise ValueError("请先同步代码")

        analysis = Analysis.objects.create(
            analysis_type="issue_code_analysis",
            issue=issue,
            triggered_by=triggered_by,
            triggered_by_user=user if triggered_by == "manual" else None,
            status=Analysis.Status.RUNNING,
        )
        self._execute_analysis(analysis, issue)
        return analysis

    def analyze_async(self, issue, triggered_by="auto", user=None):
        """Async analysis — creates Analysis, submits to thread pool."""
        analysis = Analysis.objects.create(
            analysis_type="issue_code_analysis",
            issue=issue,
            triggered_by=triggered_by,
            triggered_by_user=user if triggered_by == "manual" else None,
            status=Analysis.Status.RUNNING,
        )
        _executor.submit(self._run_in_thread, analysis.id, issue.id)
        return analysis

    def _run_in_thread(self, analysis_id, issue_id):
        """Thread entry point — handles DB connection lifecycle."""
        try:
            issue = Issue.objects.select_related("repo").get(pk=issue_id)
            analysis = Analysis.objects.get(pk=analysis_id)
            self._execute_analysis(analysis, issue)
        except Exception:
            logger.exception("AI analysis thread failed for analysis %s", analysis_id)
            Analysis.objects.filter(pk=analysis_id).update(
                status=Analysis.Status.FAILED,
                error_message="执行异常",
            )
        finally:
            close_old_connections()

    def _execute_analysis(self, analysis, issue):
        """Core analysis logic — shared by sync and async paths."""
        prompt_template = Prompt.objects.filter(
            slug="issue_code_analysis", is_active=True
        ).first()
        if not prompt_template:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = "No active Prompt for 'issue_code_analysis'"
            analysis.save(update_fields=["status", "error_message", "updated_at"])
            return

        llm_config = prompt_template.llm_config or LLMConfig.objects.filter(
            is_default=True, is_active=True
        ).first()
        if not llm_config:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = "No default LLMConfig configured"
            analysis.save(update_fields=["status", "error_message", "updated_at"])
            return

        try:
            context = {
                "title": issue.title,
                "description": issue.description,
                "priority": issue.priority,
                "status": issue.status,
                "labels": ", ".join(issue.labels) if issue.labels else "",
                "cause": issue.cause or "",
                "solution": issue.solution or "",
                "remark": issue.remark or "",
            }
            user_prompt = prompt_template.user_prompt_template.format(**context)
            runner = OpenCodeRunner(llm_config)
            full_prompt = f"{prompt_template.system_prompt}\n\n{user_prompt}"
            raw = runner.run(
                repo_path=issue.repo.local_path,
                prompt=full_prompt,
                model=prompt_template.llm_model,
            )

            parsed = parse_json_response(raw)
            target_field = parsed.get("target_field", "")
            content = parsed.get("content", "")

            if target_field not in self.ALLOWED_FIELDS:
                raise ValueError(f"Invalid target field: {target_field}")

            self._append_ai_content(issue, target_field, content)

            analysis.raw_response = raw
            analysis.parsed_result = parsed
            analysis.prompt_template = prompt_template
            analysis.status = Analysis.Status.DONE
            analysis.save(update_fields=[
                "raw_response", "parsed_result", "prompt_template",
                "status", "updated_at",
            ])
        except Exception as e:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = str(e)
            analysis.save(update_fields=["status", "error_message", "updated_at"])

    def _append_ai_content(self, issue, field, content):
        if field not in self.ALLOWED_FIELDS:
            raise ValueError(f"Invalid target field: {field}")
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        block = f"\n\n---\n🤖 AI 分析 | {timestamp}\n{content}"
        with transaction.atomic():
            issue = Issue.objects.select_for_update().get(pk=issue.pk)
            current = getattr(issue, field) or ""  # Guard against None
            setattr(issue, field, current + block)
            issue.save(update_fields=[field, "updated_at"])

    def get_running_analysis(self, issue):
        return Analysis.objects.filter(
            issue=issue,
            analysis_type="issue_code_analysis",
            status=Analysis.Status.RUNNING,
        ).first()

    @classmethod
    def cleanup_stale_analyses(cls):
        cutoff = timezone.now() - timedelta(minutes=10)
        Analysis.objects.filter(
            status=Analysis.Status.RUNNING,
            created_at__lt=cutoff,
        ).update(status=Analysis.Status.FAILED, error_message="进程异常终止")
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/test_issue_analysis.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/ai/services.py backend/tests/test_issue_analysis.py
git commit -m "feat(ai): add IssueAnalysisService with field allowlist and async support"
```

---

## Task 9: Issue AI Analyze + Analysis Status API Endpoints

**Files:**
- Modify: `backend/apps/issues/views.py`
- Modify: `backend/apps/issues/urls.py`
- Modify: `backend/apps/ai/views.py`
- Modify: `backend/apps/ai/urls.py`

- [ ] **Step 1: Add IssueAIAnalyzeView**

In `backend/apps/issues/views.py`, add:

```python
from apps.ai.services import IssueAnalysisService


class IssueAIAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        issue = Issue.objects.select_related("repo").filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)

        if not issue.repo:
            return Response({"detail": "请先关联仓库"}, status=status.HTTP_400_BAD_REQUEST)

        if issue.repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)

        svc = IssueAnalysisService()
        existing = svc.get_running_analysis(issue)
        if existing:
            return Response(
                {"analysis_id": existing.id, "status": "running"},
                status=status.HTTP_409_CONFLICT,
            )

        analysis = svc.analyze_async(issue, triggered_by="manual", user=request.user)
        return Response(
            {"analysis_id": analysis.id, "status": "running"},
            status=status.HTTP_202_ACCEPTED,
        )
```

- [ ] **Step 2: Add URL pattern for issue AI analyze**

In `backend/apps/issues/urls.py`, add import and pattern:

```python
from .views import (
    IssueListCreateView, IssueDetailView, BatchUpdateView,
    IssueGitHubCreateView, IssueGitHubLinkView, IssueCloseWithGitHubView,
    IssueAIAnalyzeView,
)

# Add to urlpatterns:
path("<int:pk>/ai-analyze/", IssueAIAnalyzeView.as_view(), name="issue-ai-analyze"),
```

- [ ] **Step 3: Add AnalysisStatusView**

In `backend/apps/ai/views.py`, add:

```python
class AnalysisStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .models import Analysis
        try:
            analysis = Analysis.objects.get(pk=pk)
        except Analysis.DoesNotExist:
            return Response({"detail": "分析记录不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "id": analysis.id,
            "status": analysis.status,
            "error_message": analysis.error_message,
        })
```

- [ ] **Step 4: Add URL pattern for analysis status**

In `backend/apps/ai/urls.py`:

```python
from .views import InsightsView, InsightsRefreshView, SyncGitHubView, AnalysisStatusView

urlpatterns = [
    path("insights/", InsightsView.as_view(), name="ai-insights"),
    path("insights/refresh/", InsightsRefreshView.as_view(), name="ai-insights-refresh"),
    path("sync-github/", SyncGitHubView.as_view(), name="ai-sync-github"),
    path("analysis/<int:pk>/status/", AnalysisStatusView.as_view(), name="analysis-status"),
]
```

- [ ] **Step 5: Run all tests**

```bash
cd backend && uv run pytest -x
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/issues/views.py backend/apps/issues/urls.py backend/apps/ai/views.py backend/apps/ai/urls.py
git commit -m "feat(api): add issue AI analyze and analysis status endpoints"
```

---

## Task 10: Auto-Trigger Signal + AppConfig Startup Cleanup

**Files:**
- Create: `backend/apps/issues/signals.py`
- Modify: `backend/apps/issues/apps.py`
- Modify: `backend/apps/ai/apps.py`

- [ ] **Step 1: Create signal**

Create `backend/apps/issues/signals.py`:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Issue


@receiver(post_save, sender=Issue)
def trigger_ai_analysis(sender, instance, created, update_fields, **kwargs):
    if created:
        _maybe_analyze(instance, triggered_by="auto")
    elif update_fields and "description" in update_fields:
        # Only trigger on explicit description updates (update_fields specified)
        # Skip full saves (update_fields=None) to avoid unnecessary re-analysis
        # Skip AI-appended fields to prevent loops
        if not (set(update_fields) & {"cause", "solution", "remark"}):
            _maybe_analyze(instance, triggered_by="auto")


def _maybe_analyze(issue, triggered_by):
    if not issue.repo_id:
        return
    # Lazy import to avoid circular dependency
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
```

- [ ] **Step 2: Register signal in IssuesConfig**

Check/create `backend/apps/issues/apps.py`:

```python
from django.apps import AppConfig


class IssuesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.issues"
    verbose_name = "问题跟踪"

    def ready(self):
        import apps.issues.signals  # noqa: F401
```

- [ ] **Step 3: Add startup cleanup to AiConfig**

In `backend/apps/ai/apps.py`:

```python
from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI 分析"

    def ready(self):
        from .services import IssueAnalysisService
        try:
            IssueAnalysisService.cleanup_stale_analyses()
        except Exception:
            pass  # DB may not be ready during initial migration
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && uv run pytest -x
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/issues/signals.py backend/apps/issues/apps.py backend/apps/ai/apps.py
git commit -m "feat(issues): add auto-trigger signal and startup cleanup"
```

---

## Task 11: Frontend — Repo Detail Page (Clone, Git Log, Branches)

**Files:**
- Modify: `frontend/app/pages/app/repos/[id]/index.vue`

- [ ] **Step 1: Add clone button, status badge, branch switcher, and git log tab**

Read the current file first, then add:

1. **Clone status badge** next to repo name (显示 clone_status)
2. **"同步代码" button** that POSTs to `/api/repos/{id}/clone/`
3. **Branch switcher dropdown** — fetches from `/api/repos/{id}/branches/`, calls clone with `{branch}` to switch
4. **"提交记录" tab** — fetches from `/api/repos/{id}/git-log/`, displays commit list with hash (short), author, date, message
5. **Clone error display** — when clone_status is "failed", show clone_error in an alert

Key implementation details:
- Poll repo status every 3 seconds while `clone_status === "cloning"`
- Git log table columns: 提交哈希 (short hash), 作者, 日期, 提交信息
- Branch dropdown only visible when clone_status is "cloned"
- Disable "同步代码" button when clone_status is "cloning"

```vue
<!-- Clone button example -->
<UButton
  :loading="repo.clone_status === 'cloning'"
  :disabled="repo.clone_status === 'cloning'"
  @click="cloneRepo"
  icon="i-heroicons-arrow-down-tray"
>
  {{ repo.clone_status === 'cloned' ? '拉取更新' : '同步代码' }}
</UButton>

<!-- Status badge -->
<UBadge :color="cloneStatusColor">{{ cloneStatusLabel }}</UBadge>
```

- [ ] **Step 2: Test manually in browser**

- Visit a repo detail page
- Verify clone button appears
- Verify git log tab appears after clone
- Verify branch switcher works

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/repos/
git commit -m "feat(frontend): add clone, git log, branch switcher to repo detail"
```

---

## Task 12: Frontend — Issue Create Form (Repo Auto-Populate)

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

- [ ] **Step 1: Add repo field to issue create form**

In the create issue modal in `index.vue`:

1. When user selects a Project, fetch that project's `repos` list
2. If project has exactly 1 repo → auto-set `newIssue.repo` to that repo's id
3. If project has multiple repos → show a `<USelect>` dropdown to pick one
4. If project has 0 repos → hide repo field
5. Add `repo` to the POST body when creating issue

```javascript
// In the project selection watcher
watch(() => newIssue.value.project, async (projectId) => {
  if (!projectId) {
    projectRepos.value = []
    newIssue.value.repo = null
    return
  }
  const project = projects.value.find(p => p.id === projectId)
  if (project?.repos?.length === 1) {
    newIssue.value.repo = project.repos[0]
  } else {
    newIssue.value.repo = null
  }
  projectRepos.value = project?.repos || []
})
```

- [ ] **Step 2: Test manually**

- Create a new issue
- Select a project with 1 repo → repo auto-fills
- Select a project with multiple repos → dropdown appears
- Select a project with 0 repos → no repo field

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/issues/index.vue
git commit -m "feat(frontend): auto-populate repo field on issue create"
```

---

## Task 13: Frontend — Issue Detail Page (AI Analyze + Content Rendering)

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Add AI analyze button and content rendering**

1. **AI 分析 button** in the toolbar area:
   - Disabled if `!issue.repo` or repo.clone_status !== "cloned"
   - Shows loading spinner while analysis is running
   - Calls `POST /api/issues/{id}/ai-analyze/`
   - Polls `GET /api/ai/analysis/{analysis_id}/status/` every 3 seconds until done/failed
   - On done: refresh issue data to show new content

2. **AI content rendering** in cause/solution/remark fields:
   - Parse field content, split on `\n---\n🤖 AI 分析` separator
   - Render user content normally
   - Render AI blocks in a distinct style (light blue/gray background card with robot icon and timestamp)

```vue
<!-- AI analyze button -->
<UButton
  v-if="issue.repo"
  :loading="aiAnalyzing"
  :disabled="aiAnalyzing"
  @click="triggerAIAnalysis"
  icon="i-heroicons-cpu-chip"
  color="primary"
  variant="soft"
>
  AI 分析
</UButton>

<!-- AI content rendering helper -->
<template #ai-field="{ content }">
  <div v-for="(block, i) in parseAIContent(content)" :key="i">
    <div v-if="block.isAI" class="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
      <div class="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 mb-1">
        <UIcon name="i-heroicons-cpu-chip" class="w-3 h-3" />
        <span>AI 分析 | {{ block.timestamp }}</span>
      </div>
      <div class="text-sm">{{ block.content }}</div>
    </div>
    <div v-else class="text-sm">{{ block.content }}</div>
  </div>
</template>
```

```javascript
function parseAIContent(text) {
  if (!text) return []
  const blocks = []
  const parts = text.split(/\n---\n🤖 AI 分析 \| /)
  if (parts[0]) {
    blocks.push({ isAI: false, content: parts[0].trim() })
  }
  for (let i = 1; i < parts.length; i++) {
    const newlineIdx = parts[i].indexOf('\n')
    const timestamp = parts[i].substring(0, newlineIdx)
    const content = parts[i].substring(newlineIdx + 1)
    blocks.push({ isAI: true, timestamp, content: content.trim() })
  }
  return blocks
}

const aiAnalyzing = ref(false)
let pollTimer = null

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function triggerAIAnalysis() {
  aiAnalyzing.value = true
  try {
    const { analysis_id } = await api(`/api/issues/${route.params.id}/ai-analyze/`, {
      method: 'POST',
    })
    pollAnalysisStatus(analysis_id)
  } catch (e) {
    if (e.status === 409) {
      // Already running, poll existing
      pollAnalysisStatus(e.data.analysis_id)
    } else {
      aiAnalyzing.value = false
    }
  }
}

function pollAnalysisStatus(analysisId) {
  let failCount = 0
  pollTimer = setInterval(async () => {
    try {
      const res = await api(`/api/ai/analysis/${analysisId}/status/`)
      failCount = 0
      if (res.status === 'done' || res.status === 'failed') {
        clearInterval(pollTimer)
        aiAnalyzing.value = false
        await fetchIssue() // refresh issue data
      }
    } catch {
      failCount++
      if (failCount >= 3) {
        clearInterval(pollTimer)
        aiAnalyzing.value = false
      }
    }
  }, 3000)
}
```

- [ ] **Step 2: Test manually**

- Open an issue with a linked cloned repo
- Click "AI 分析" button
- Verify loading state shows
- Verify result appears in cause/solution/remark field with AI attribution styling

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/issues/
git commit -m "feat(frontend): add AI analyze button and AI content rendering"
```

---

## Task 14: Integration Test — Full Flow

**Files:**
- Modify: `backend/tests/test_issue_analysis.py`

- [ ] **Step 1: Add API-level integration tests**

Append to `backend/tests/test_issue_analysis.py`:

```python
@pytest.mark.django_db
class TestIssueAIAnalyzeView:
    def test_trigger_returns_202(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        issue = IssueFactory(repo=repo)
        with patch("apps.issues.views.IssueAnalysisService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_running_analysis.return_value = None
            mock_svc.analyze_async.return_value = AnalysisFactory(
                issue=issue, status="running"
            )
            resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
            assert resp.status_code == 202
            assert "analysis_id" in resp.data

    def test_no_repo_returns_400(self, auth_client):
        issue = IssueFactory(repo=None)
        resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
        assert resp.status_code == 400
        assert "关联仓库" in resp.data["detail"]

    def test_not_cloned_returns_400(self, auth_client):
        repo = RepoFactory(clone_status="not_cloned")
        issue = IssueFactory(repo=repo)
        resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
        assert resp.status_code == 400
        assert "同步代码" in resp.data["detail"]

    def test_already_running_returns_409(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        issue = IssueFactory(repo=repo)
        with patch("apps.issues.views.IssueAnalysisService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_running_analysis.return_value = AnalysisFactory(
                issue=issue, status="running"
            )
            resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
            assert resp.status_code == 409


@pytest.mark.django_db
class TestAnalysisStatusView:
    def test_returns_status(self, auth_client):
        analysis = AnalysisFactory(status="done")
        resp = auth_client.get(f"/api/ai/analysis/{analysis.pk}/status/")
        assert resp.status_code == 200
        assert resp.data["status"] == "done"

    def test_not_found(self, auth_client):
        resp = auth_client.get("/api/ai/analysis/99999/status/")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run all tests**

```bash
cd backend && uv run pytest -x -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_issue_analysis.py
git commit -m "test: add API integration tests for AI analyze endpoints"
```

---

## Task 15: Docker + Final Cleanup

**Files:**
- Modify: `backend/Dockerfile` (if exists) or `docker-compose.yml`

- [ ] **Step 1: Add git to backend Docker image**

In the backend Dockerfile, add:

```dockerfile
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://opencode.ai/install | bash
```

- [ ] **Step 2: Add REPO_CLONE_DIR volume to docker-compose.yml**

```yaml
backend:
  volumes:
    - repo_data:/data/repos
  environment:
    - REPO_CLONE_DIR=/data/repos

volumes:
  repo_data:
```

- [ ] **Step 3: Run full test suite one final time**

```bash
cd backend && uv run pytest -x -v
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml backend/Dockerfile
git commit -m "chore: add git to Docker image and repo clone volume"
```

---

## Summary of All Commits

| # | Message | Scope |
|---|---------|-------|
| 1 | `feat(repos): add clone_status, clone_error, current_branch, cloned_at fields` | Model |
| 2 | `feat(projects): migrate linked_repos JSONField to repos M2M` | Model + Migration |
| 3 | `feat(issues): add repo FK for direct repo association` | Model |
| 4 | `feat(ai): add issue FK and auto trigger type to Analysis` | Model |
| 5 | `feat(repos): add RepoCloneService with secure git auth` | Service + Tests |
| 6 | `feat(repos): add clone, git-log, branches API endpoints` | Views + URLs |
| 7 | `feat(ai): add OpenCodeRunner for opencode CLI integration` | Service + Tests |
| 8 | `feat(ai): add IssueAnalysisService with field allowlist and async support` | Service + Tests |
| 9 | `feat(api): add issue AI analyze and analysis status endpoints` | Views + URLs |
| 10 | `feat(issues): add auto-trigger signal and startup cleanup` | Signal + AppConfig |
| 11 | `feat(frontend): add clone, git log, branch switcher to repo detail` | Frontend |
| 12 | `feat(frontend): auto-populate repo field on issue create` | Frontend |
| 13 | `feat(frontend): add AI analyze button and AI content rendering` | Frontend |
| 14 | `test: add API integration tests for AI analyze endpoints` | Tests |
| 15 | `chore: add git to Docker image and repo clone volume` | Infra |
