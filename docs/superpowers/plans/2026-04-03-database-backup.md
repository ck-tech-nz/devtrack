# Database Backup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-click PostgreSQL backup to DevTrack's web UI — trigger backups, view history, download/delete backup files.

**Architecture:** Django view runs `pg_dump` via `asyncio.create_subprocess_exec` (wrapped in `asyncio.run()` for WSGI compat), writes dump files to `/data/backups/` (Docker volume mount). A `DatabaseBackup` model tracks records. Frontend page at `/app/settings/backups` with superuser-only access via page-perms.

**Tech Stack:** Django 6, `pg_dump` (postgresql-client), uvicorn (ASGI), Nuxt 4 + @nuxt/ui 3

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `backend/apps/settings/backup_views.py` | Views: list, create, download, delete backups |
| `backend/apps/settings/backup_serializers.py` | `DatabaseBackupSerializer` |
| `backend/tests/test_backups.py` | All backup API tests |

### Backend — Modified Files

| File | Change |
|------|--------|
| `backend/apps/settings/models.py` | Add `DatabaseBackup` model |
| `backend/apps/settings/urls.py` | Mount `/backups/` endpoints |
| `backend/apps/settings/admin.py` | Register `DatabaseBackup` in unfold admin |
| `backend/config/settings.py` | Add `BACKUP_DIR` setting + backup route to `PAGE_PERMS.SEED_ROUTES` |
| `backend/pyproject.toml` | Add `uvicorn` dependency |
| `backend/Dockerfile` | Install `postgresql-client` |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `frontend/app/pages/app/settings/backups.vue` | Backup management page |

### Deployment — Modified Files

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `backups` volume mount |
| `servers/prod/docker-compose.yml` | Add `backups` volume, switch to uvicorn CMD |

---

## Task 1: DatabaseBackup Model + Migration

**Files:**
- Modify: `backend/apps/settings/models.py`
- Create: `backend/tests/test_backups.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_backups.py`:

```python
import pytest
from apps.settings.models import DatabaseBackup

pytestmark = pytest.mark.django_db


class TestDatabaseBackupModel:
    def test_create_backup_record(self, superuser_client):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()
        backup = DatabaseBackup.objects.create(
            filename="devtrack_20260403_120000.dump",
            status="running",
            created_by=user,
        )
        assert backup.filename == "devtrack_20260403_120000.dump"
        assert backup.status == "running"
        assert backup.file_size is None
        assert backup.error_message == ""

    def test_ordering_newest_first(self):
        b1 = DatabaseBackup.objects.create(filename="a.dump", status="success")
        b2 = DatabaseBackup.objects.create(filename="b.dump", status="success")
        ids = list(DatabaseBackup.objects.values_list("id", flat=True))
        assert ids == [b2.id, b1.id]

    def test_str_representation(self):
        backup = DatabaseBackup.objects.create(filename="test.dump", status="success")
        assert "test.dump" in str(backup)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_backups.py -v`
Expected: FAIL — `ImportError: cannot import name 'DatabaseBackup'`

- [ ] **Step 3: Implement the model**

In `backend/apps/settings/models.py`, first check existing imports. The file already has `from django.db import models`. Add `from django.conf import settings as django_settings` if not present (the file uses `settings_module` or `django_settings` — check and match the existing alias). Then append:

```python
class DatabaseBackup(models.Model):
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "备份中"),
            ("success", "成功"),
            ("failed", "失败"),
        ],
    )
    error_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "数据库备份"
        verbose_name_plural = "数据库备份"

    def __str__(self):
        return self.filename
```

Use whatever alias is already used in the file for `django.conf.settings` (e.g. `settings_module` or `django_settings`). If `AUTH_USER_MODEL` reference doesn't work with the existing alias, use the string `"users.User"` directly.

- [ ] **Step 4: Generate and apply migration**

```bash
cd backend && uv run python manage.py makemigrations settings && uv run python manage.py migrate
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_backups.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/settings/models.py backend/apps/settings/migrations/ backend/tests/test_backups.py
git commit -m "feat(backups): add DatabaseBackup model"
```

---

## Task 2: Backup Serializer

**Files:**
- Create: `backend/apps/settings/backup_serializers.py`
- Modify: `backend/tests/test_backups.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_backups.py`:

```python
from apps.settings.backup_serializers import DatabaseBackupSerializer


class TestDatabaseBackupSerializer:
    def test_serializes_backup_record(self, superuser_client):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()
        backup = DatabaseBackup.objects.create(
            filename="devtrack_20260403_120000.dump",
            file_size=15728640,
            status="success",
            created_by=user,
        )
        data = DatabaseBackupSerializer(backup).data
        assert data["filename"] == "devtrack_20260403_120000.dump"
        assert data["file_size"] == 15728640
        assert data["status"] == "success"
        assert data["created_by_name"] == user.name
        assert "id" in data
        assert "created_at" in data

    def test_created_by_name_null_user(self):
        backup = DatabaseBackup.objects.create(
            filename="test.dump", status="success", created_by=None
        )
        data = DatabaseBackupSerializer(backup).data
        assert data["created_by_name"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_backups.py::TestDatabaseBackupSerializer -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement the serializer**

Create `backend/apps/settings/backup_serializers.py`:

```python
from rest_framework import serializers
from .models import DatabaseBackup


class DatabaseBackupSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.name", read_only=True, default=None
    )

    class Meta:
        model = DatabaseBackup
        fields = [
            "id", "filename", "file_size", "status",
            "error_message", "created_by_name", "created_at",
        ]
        read_only_fields = fields
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_backups.py::TestDatabaseBackupSerializer -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/settings/backup_serializers.py backend/tests/test_backups.py
git commit -m "feat(backups): add DatabaseBackup serializer"
```

---

## Task 3: Backup API Views + URL Routing

**Files:**
- Create: `backend/apps/settings/backup_views.py`
- Modify: `backend/apps/settings/urls.py`
- Modify: `backend/tests/test_backups.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_backups.py`:

```python
from unittest.mock import patch, AsyncMock


class TestBackupListAPI:
    def test_list_as_superuser(self, superuser_client):
        DatabaseBackup.objects.create(filename="a.dump", status="success")
        DatabaseBackup.objects.create(filename="b.dump", status="success")
        resp = superuser_client.get("/api/settings/backups/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_list_as_regular_user_forbidden(self, regular_client):
        resp = regular_client.get("/api/settings/backups/")
        assert resp.status_code == 403

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get("/api/settings/backups/")
        assert resp.status_code == 401


class TestBackupCreateAPI:
    @patch("apps.settings.backup_views.run_pg_dump")
    def test_trigger_backup_success(self, mock_dump, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)

        async def fake_dump(filepath):
            # Create a fake dump file
            with open(filepath, "wb") as f:
                f.write(b"x" * 1024)
            return True, 1024, ""

        mock_dump.side_effect = lambda fp: __import__("asyncio").get_event_loop().run_until_complete(fake_dump(fp)) if False else (True, 1024, "")
        # Simpler: just return the tuple directly since asyncio.run wraps the coroutine
        mock_dump.return_value = (True, 1024, "")

        # We need the file to exist for file_size check
        import os
        os.makedirs(str(tmp_path), exist_ok=True)

        resp = superuser_client.post("/api/settings/backups/")
        assert resp.status_code == 201
        assert resp.data["status"] == "success"
        assert resp.data["file_size"] == 1024

    @patch("apps.settings.backup_views.run_pg_dump")
    def test_trigger_backup_failure(self, mock_dump, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        mock_dump.return_value = (False, 0, "pg_dump: connection refused")
        resp = superuser_client.post("/api/settings/backups/")
        assert resp.status_code == 201
        assert resp.data["status"] == "failed"
        assert "connection refused" in resp.data["error_message"]

    def test_trigger_forbidden_non_staff(self, regular_client):
        resp = regular_client.post("/api/settings/backups/")
        assert resp.status_code == 403

    @patch("apps.settings.backup_views.run_pg_dump")
    def test_concurrent_backup_blocked(self, mock_dump, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        DatabaseBackup.objects.create(filename="running.dump", status="running")
        resp = superuser_client.post("/api/settings/backups/")
        assert resp.status_code == 409


class TestBackupDownloadAPI:
    def test_download_backup(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        (tmp_path / "test.dump").write_bytes(b"fake dump content")
        backup = DatabaseBackup.objects.create(
            filename="test.dump", file_size=17, status="success"
        )
        resp = superuser_client.get(f"/api/settings/backups/{backup.id}/download/")
        assert resp.status_code == 200
        assert b"fake dump content" in b"".join(resp.streaming_content)

    def test_download_missing_file_404(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        backup = DatabaseBackup.objects.create(
            filename="gone.dump", status="success"
        )
        resp = superuser_client.get(f"/api/settings/backups/{backup.id}/download/")
        assert resp.status_code == 404

    def test_download_nonexistent_record_404(self, superuser_client):
        resp = superuser_client.get("/api/settings/backups/99999/download/")
        assert resp.status_code == 404


class TestBackupDeleteAPI:
    def test_delete_backup_and_file(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        dump_file = tmp_path / "deleteme.dump"
        dump_file.write_bytes(b"data")
        backup = DatabaseBackup.objects.create(
            filename="deleteme.dump", status="success"
        )
        resp = superuser_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 204
        assert not dump_file.exists()
        assert not DatabaseBackup.objects.filter(id=backup.id).exists()

    def test_delete_file_already_gone(self, superuser_client, tmp_path, settings):
        settings.BACKUP_DIR = str(tmp_path)
        backup = DatabaseBackup.objects.create(
            filename="already_gone.dump", status="failed"
        )
        resp = superuser_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 204

    def test_delete_forbidden_non_staff(self, regular_client):
        backup = DatabaseBackup.objects.create(filename="t.dump", status="success")
        resp = regular_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_backups.py::TestBackupListAPI tests/test_backups.py::TestBackupCreateAPI tests/test_backups.py::TestBackupDownloadAPI tests/test_backups.py::TestBackupDeleteAPI -v`
Expected: FAIL — 404 or ImportError

- [ ] **Step 3: Implement backup views**

Create `backend/apps/settings/backup_views.py`:

```python
import asyncio
import os
from datetime import datetime

from django.conf import settings as django_settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.generics import ListAPIView, DestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .backup_serializers import DatabaseBackupSerializer
from .models import DatabaseBackup


def get_backup_dir():
    d = getattr(django_settings, "BACKUP_DIR", "/data/backups")
    os.makedirs(d, exist_ok=True)
    return d


async def run_pg_dump(filepath):
    """Run pg_dump. Returns (success, file_size, error_message)."""
    db = django_settings.DATABASES["default"]
    env = os.environ.copy()
    env["PGPASSWORD"] = db.get("PASSWORD", "")

    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h", db.get("HOST", "127.0.0.1"),
        "-p", str(db.get("PORT", "5432")),
        "-U", db.get("USER", "postgres"),
        "-Fc", db.get("NAME", "devtrack"),
        "-f", filepath,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode == 0:
        return True, os.path.getsize(filepath), ""
    return False, 0, stderr.decode().strip()


class BackupListView(ListAPIView):
    queryset = DatabaseBackup.objects.all()
    serializer_class = DatabaseBackupSerializer
    permission_classes = [IsAdminUser]


class BackupCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        if DatabaseBackup.objects.filter(status="running").exists():
            return Response(
                {"detail": "已有备份任务正在运行"},
                status=status.HTTP_409_CONFLICT,
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = django_settings.DATABASES["default"].get("NAME", "devtrack")
        filename = f"{db_name}_{timestamp}.dump"
        filepath = os.path.join(get_backup_dir(), filename)

        backup = DatabaseBackup.objects.create(
            filename=filename,
            status="running",
            created_by=request.user,
        )

        try:
            success, file_size, error_msg = asyncio.run(run_pg_dump(filepath))
            if success:
                backup.status = "success"
                backup.file_size = file_size
            else:
                backup.status = "failed"
                backup.error_message = error_msg
                if os.path.exists(filepath):
                    os.remove(filepath)
        except Exception as e:
            backup.status = "failed"
            backup.error_message = str(e)

        backup.save()
        return Response(
            DatabaseBackupSerializer(backup).data,
            status=status.HTTP_201_CREATED,
        )


class BackupDownloadView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            backup = DatabaseBackup.objects.get(pk=pk)
        except DatabaseBackup.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        filepath = os.path.join(get_backup_dir(), backup.filename)
        if not os.path.exists(filepath):
            return Response(
                {"detail": "备份文件不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(filepath, "rb"),
            content_type="application/octet-stream",
            as_attachment=True,
            filename=backup.filename,
        )


class BackupDeleteView(DestroyAPIView):
    queryset = DatabaseBackup.objects.all()
    serializer_class = DatabaseBackupSerializer
    permission_classes = [IsAdminUser]

    def perform_destroy(self, instance):
        filepath = os.path.join(get_backup_dir(), instance.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        instance.delete()
```

- [ ] **Step 4: Mount URL routes**

In `backend/apps/settings/urls.py`, add imports and paths. The file currently has:

```python
from django.urls import path
from .views import SiteSettingsView, LabelSettingsView

urlpatterns = [
    path("", SiteSettingsView.as_view(), name="site-settings"),
    path("labels/", LabelSettingsView.as_view(), name="label-settings"),
]
```

Add the backup imports and routes:

```python
from django.urls import path
from .views import SiteSettingsView, LabelSettingsView
from .backup_views import (
    BackupListView, BackupCreateView, BackupDownloadView, BackupDeleteView,
)

urlpatterns = [
    path("", SiteSettingsView.as_view(), name="site-settings"),
    path("labels/", LabelSettingsView.as_view(), name="label-settings"),
    path("backups/", BackupListView.as_view(), name="backup-list"),
    path("backups/create/", BackupCreateView.as_view(), name="backup-create"),
    path("backups/<int:pk>/download/", BackupDownloadView.as_view(), name="backup-download"),
    path("backups/<int:pk>/", BackupDeleteView.as_view(), name="backup-delete"),
]
```

Note: List (GET `/backups/`) and create (POST `/backups/create/`) are separate paths because `ListAPIView` only handles GET and the create logic is custom. Download must come before the delete route so `<int:pk>/download/` matches first.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_backups.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/settings/backup_views.py backend/apps/settings/urls.py backend/tests/test_backups.py
git commit -m "feat(backups): add backup API views and URL routing"
```

---

## Task 4: Settings, Admin, and Page-Perms Config

**Files:**
- Modify: `backend/config/settings.py`
- Modify: `backend/apps/settings/admin.py`

- [ ] **Step 1: Add BACKUP_DIR setting**

In `backend/config/settings.py`, after the `REPO_CLONE_DIR` line (line 143), add:

```python
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/data/backups")
```

- [ ] **Step 2: Add backup route to PAGE_PERMS SEED_ROUTES**

In `backend/config/settings.py`, in the `SEED_ROUTES` list (around line 148-158), add before the permissions route (sort_order 99):

```python
{"path": "/app/settings/backups", "label": "数据库备份", "icon": "i-heroicons-circle-stack", "permission": None, "sort_order": 8, "meta": {"superuserOnly": True}},
```

- [ ] **Step 3: Register DatabaseBackup in admin**

In `backend/apps/settings/admin.py`, add the import and registration. The file already uses `@admin.register` and imports `ModelAdmin` from `unfold.admin`. Add:

```python
from .models import SiteSettings, DatabaseBackup  # update existing import
```

Then add at the bottom:

```python
@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(ModelAdmin):
    list_display = ("filename", "status", "file_size", "created_by", "created_at")
    list_filter = ("status",)
    readonly_fields = ("filename", "file_size", "status", "error_message", "created_by", "created_at")
```

- [ ] **Step 4: Sync page-perms**

```bash
cd backend && uv run python manage.py sync_page_perms
```

- [ ] **Step 5: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/config/settings.py backend/apps/settings/admin.py
git commit -m "feat(backups): add BACKUP_DIR setting, page-perms route, admin registration"
```

---

## Task 5: Docker Infrastructure

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `backend/pyproject.toml`
- Modify: `docker-compose.yml`
- Modify: `servers/prod/docker-compose.yml`

- [ ] **Step 1: Install postgresql-client in Dockerfile**

In `backend/Dockerfile` line 3, change:

```dockerfile
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
```

to:

```dockerfile
RUN apt-get update && apt-get install -y git curl postgresql-client && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 2: Add uvicorn dependency**

```bash
cd backend && uv add uvicorn
```

- [ ] **Step 3: Update Dockerfile CMD to uvicorn**

In `backend/Dockerfile`, change the CMD line (line 20):

```dockerfile
CMD ["uv", "run", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Add backups volume to docker-compose.yml (dev)**

In `docker-compose.yml`, add to backend `volumes`:

```yaml
    volumes:
      - repo_data:/data/repos
      - backups:/data/backups
```

And add to root `volumes`:

```yaml
volumes:
  pgdata:
  repo_data:
  backups:
```

- [ ] **Step 5: Update servers/prod/docker-compose.yml**

Add `backups:/data/backups` to backend volumes:

```yaml
    volumes:
      - ./.gitconfig-proxy:/root/.gitconfig:ro
      - repo_data:/data/repos
      - backups:/data/backups
```

Switch command to uvicorn:

```yaml
    command: >
      sh -c "uv run python manage.py migrate --noinput &&
             uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000"
```

Add to root volumes:

```yaml
volumes:
  repo_data:
  backups:
```

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile backend/pyproject.toml backend/uv.lock docker-compose.yml servers/prod/docker-compose.yml
git commit -m "infra(backups): add postgresql-client, uvicorn, and backup volumes"
```

---

## Task 6: Frontend — Backup Management Page

**Files:**
- Create: `frontend/app/pages/app/settings/backups.vue`

- [ ] **Step 1: Create the backup page**

Create `frontend/app/pages/app/settings/backups.vue`. The project uses Nuxt 4 with @nuxt/ui 3. Existing pages use `definePageMeta({ layout: 'default' })`. UTable in @nuxt/ui 3 uses `data` prop (not `rows`) and `accessorKey` in column defs. Slot names follow `#<columnKey>-cell` pattern.

```vue
<script setup lang="ts">
definePageMeta({ layout: 'default' })

interface BackupRecord {
  id: number
  filename: string
  file_size: number | null
  status: 'running' | 'success' | 'failed'
  error_message: string
  created_by_name: string | null
  created_at: string
}

const { api } = useApi()
const toast = useToast()

const loading = ref(false)
const creating = ref(false)
const backups = ref<BackupRecord[]>([])
const total = ref(0)
const page = ref(1)

const columns = [
  { accessorKey: 'filename', header: '文件名' },
  { accessorKey: 'file_size', header: '大小' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'created_by_name', header: '操作人' },
  { accessorKey: 'created_at', header: '时间' },
  { accessorKey: 'actions', header: '操作' },
]

function formatSize(bytes: number | null): string {
  if (bytes == null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

const statusMap: Record<string, { label: string; color: 'success' | 'warning' | 'error' }> = {
  running: { label: '备份中', color: 'warning' },
  success: { label: '成功', color: 'success' },
  failed: { label: '失败', color: 'error' },
}

async function fetchBackups() {
  loading.value = true
  try {
    const res = await api<any>(`/api/settings/backups/?page=${page.value}`)
    backups.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

async function triggerBackup() {
  creating.value = true
  try {
    await api<BackupRecord>('/api/settings/backups/create/', { method: 'POST' })
    toast.add({ title: '备份完成', color: 'success' })
    await fetchBackups()
  } catch (e: any) {
    const msg = e?.data?.detail || '备份失败'
    toast.add({ title: msg, color: 'error' })
  } finally {
    creating.value = false
  }
}

async function downloadBackup(row: BackupRecord) {
  const token = localStorage.getItem('access_token')
  try {
    const response = await fetch(`/api/settings/backups/${row.id}/download/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new Error()
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ title: '下载失败', color: 'error' })
  }
}

async function deleteBackup(row: BackupRecord) {
  if (!confirm(`确定要删除备份 ${row.filename}？`)) return
  try {
    await api(`/api/settings/backups/${row.id}/`, { method: 'DELETE' })
    toast.add({ title: '已删除', color: 'success' })
    await fetchBackups()
  } catch {
    toast.add({ title: '删除失败', color: 'error' })
  }
}

watch(page, fetchBackups)
onMounted(fetchBackups)
</script>

<template>
  <div class="p-6 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold">数据库备份</h1>
      <UButton
        icon="i-heroicons-arrow-down-tray"
        :loading="creating"
        @click="triggerBackup"
      >
        立即备份
      </UButton>
    </div>

    <UTable
      :data="backups"
      :columns="columns"
      :loading="loading"
      :ui="{ th: 'text-xs', td: 'text-sm' }"
    >
      <template #file_size-cell="{ row }">
        {{ formatSize(row.original.file_size) }}
      </template>
      <template #status-cell="{ row }">
        <UBadge
          :color="statusMap[row.original.status]?.color"
          variant="subtle"
        >
          {{ statusMap[row.original.status]?.label }}
        </UBadge>
      </template>
      <template #created_by_name-cell="{ row }">
        {{ row.original.created_by_name || '-' }}
      </template>
      <template #created_at-cell="{ row }">
        {{ formatTime(row.original.created_at) }}
      </template>
      <template #actions-cell="{ row }">
        <div class="flex gap-2">
          <UButton
            v-if="row.original.status === 'success'"
            size="xs"
            variant="ghost"
            icon="i-heroicons-arrow-down-tray"
            @click="downloadBackup(row.original)"
          />
          <UButton
            size="xs"
            variant="ghost"
            color="error"
            icon="i-heroicons-trash"
            @click="deleteBackup(row.original)"
          />
        </div>
      </template>
    </UTable>

    <div v-if="total > 20" class="flex justify-center">
      <UPagination
        v-model="page"
        :total="total"
        :items-per-page="20"
        @update:model-value="fetchBackups"
      />
    </div>
  </div>
</template>
```

- [ ] **Step 2: Verify the page loads**

Start dev servers and navigate to `/app/settings/backups` as superuser. Verify:
- Page renders with "数据库备份" title and "立即备份" button
- Table shows correct columns
- Non-superuser cannot see the page in nav

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/settings/backups.vue
git commit -m "feat(backups): add backup management frontend page"
```

---

## Task 7: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest -v
```

Expected: All tests PASS

- [ ] **Step 2: Run frontend typecheck**

```bash
cd frontend && npx nuxi typecheck
```

Expected: No type errors

- [ ] **Step 3: Manual integration test**

1. Start backend: `cd backend && uv run python manage.py runserver`
2. Start frontend: `cd frontend && npm run dev`
3. Log in as superuser
4. Navigate to `/app/settings/backups`
5. Click "立即备份" — verify new row with status "成功" appears
6. Click download icon — verify .dump file downloads
7. Click delete icon — verify row is removed
8. Log in as regular user — verify page is not visible in nav and route redirects to forbidden

- [ ] **Step 4: Fix any issues found and commit**

Only if manual testing reveals issues:

```bash
git add -u
git commit -m "fix(backups): address integration test findings"
```
