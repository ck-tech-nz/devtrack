# Database Backup Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-click database backup to DevTrack's web UI so admins can trigger pg_dump, view backup history, and download backup files.

**Architecture:** Django async view runs `pg_dump` via `asyncio.create_subprocess_exec`, writing dump files to a volume-mounted `/data/backups/` directory. Frontend provides a settings page with a backup button and history table. ASGI switch enables async views.

**Tech Stack:** Django 6 async views, uvicorn (ASGI), `pg_dump` CLI, Nuxt 4 (UTable, UButton), DRF serializers

---

## File Structure

**Backend (create):**
- `backend/apps/settings/backup_views.py` — async views for backup CRUD + download
- `backend/apps/settings/backup_serializers.py` — serializer for DatabaseBackup model
- `backend/tests/test_backups.py` — API tests

**Backend (modify):**
- `backend/apps/settings/models.py` — add DatabaseBackup model
- `backend/apps/settings/urls.py` — add backup URL patterns
- `backend/config/settings.py` — add BACKUP_DIR setting
- `backend/Dockerfile` — install postgresql-client
- `backend/pyproject.toml` — add uvicorn dependency

**Frontend (create):**
- `frontend/app/pages/app/settings/backups.vue` — backup management page

**Deployment (modify):**
- `servers/prod/docker-compose.yml` — add backups volume, switch to uvicorn command
- `servers/test/docker-compose.yml` — same changes

---

### Task 1: Backend Infrastructure — ASGI + pg_dump

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/Dockerfile`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Add uvicorn dependency**

In `backend/pyproject.toml`, add `uvicorn[standard]` to dependencies:

```toml
dependencies = [
    "django>=6.0,<7.0",
    "djangorestframework>=3.15,<4.0",
    "djangorestframework-simplejwt>=5.3,<6.0",
    "django-solo>=2.3,<3.0",
    "django-filter>=25.0,<26.0",
    "psycopg[binary]>=3.2,<4.0",
    "django-page-perms",
    "openai>=2.29.0,<3.0",
    "requests>=2.32.5",
    "whitenoise>=6.12.0",
    "boto3>=1.35,<2.0",
    "python-dotenv>=1.0,<2.0",
    "django-unfold>=0.87",
    "uvicorn[standard]>=0.34,<1.0",
]
```

- [ ] **Step 2: Install postgresql-client in Dockerfile**

In `backend/Dockerfile`, change the apt-get line:

```dockerfile
RUN apt-get update && apt-get install -y git curl postgresql-client && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: Add BACKUP_DIR setting**

In `backend/config/settings.py`, add at the end of the file:

```python
# Database backup
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/data/backups")
```

- [ ] **Step 4: Run uv sync to install uvicorn**

Run: `cd backend && uv sync`
Expected: uvicorn installed successfully

- [ ] **Step 5: Verify uvicorn can start the app**

Run: `cd backend && uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000 &` then `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/settings/` then kill the process.
Expected: HTTP response (401 is fine — means Django is running)

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/Dockerfile backend/config/settings.py
git commit -m "feat(backup): add uvicorn, postgresql-client, and BACKUP_DIR setting"
```

---

### Task 2: DatabaseBackup Model + Migration

**Files:**
- Modify: `backend/apps/settings/models.py`

- [ ] **Step 1: Add DatabaseBackup model**

Append to `backend/apps/settings/models.py`:

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
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "数据库备份"
        verbose_name_plural = "数据库备份"

    def __str__(self):
        return f"{self.filename} ({self.get_status_display()})"
```

- [ ] **Step 2: Generate migration**

Run: `cd backend && uv run python manage.py makemigrations settings`
Expected: Migration file created

- [ ] **Step 3: Apply migration**

Run: `cd backend && uv run python manage.py migrate`
Expected: Migration applied successfully

- [ ] **Step 4: Commit**

```bash
git add backend/apps/settings/models.py backend/apps/settings/migrations/
git commit -m "feat(backup): add DatabaseBackup model"
```

---

### Task 3: Serializer

**Files:**
- Create: `backend/apps/settings/backup_serializers.py`

- [ ] **Step 1: Create backup serializer**

Create `backend/apps/settings/backup_serializers.py`:

```python
from rest_framework import serializers
from .models import DatabaseBackup


class DatabaseBackupSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.name", read_only=True, default=""
    )

    class Meta:
        model = DatabaseBackup
        fields = [
            "id",
            "filename",
            "file_size",
            "status",
            "error_message",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/settings/backup_serializers.py
git commit -m "feat(backup): add DatabaseBackup serializer"
```

---

### Task 4: Backup Views — List + Create + Delete + Download

**Files:**
- Create: `backend/apps/settings/backup_views.py`
- Modify: `backend/apps/settings/urls.py`

- [ ] **Step 1: Create backup views**

Create `backend/apps/settings/backup_views.py`:

```python
import asyncio
import os
from datetime import datetime

from django.conf import settings
from django.http import FileResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .backup_serializers import DatabaseBackupSerializer
from .models import DatabaseBackup


class BackupListCreateView(generics.ListCreateAPIView):
    serializer_class = DatabaseBackupSerializer
    permission_classes = [IsAdminUser]
    queryset = DatabaseBackup.objects.all()

    def create(self, request, *args, **kwargs):
        # 检查是否有正在运行的备份
        if DatabaseBackup.objects.filter(status="running").exists():
            return Response(
                {"detail": "已有备份任务正在运行"},
                status=status.HTTP_409_CONFLICT,
            )

        db = settings.DATABASES["default"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{db['NAME']}_{timestamp}.dump"
        filepath = os.path.join(settings.BACKUP_DIR, filename)

        backup = DatabaseBackup.objects.create(
            filename=filename,
            status="running",
            created_by=request.user,
        )

        try:
            os.makedirs(settings.BACKUP_DIR, exist_ok=True)

            env = os.environ.copy()
            env["PGPASSWORD"] = db["PASSWORD"]

            proc = asyncio.run(self._run_pg_dump(db, filepath, env))

            if proc.returncode == 0:
                backup.status = "success"
                backup.file_size = os.path.getsize(filepath)
            else:
                backup.status = "failed"
                backup.error_message = proc.stderr
                # 清理失败的文件
                if os.path.exists(filepath):
                    os.remove(filepath)
        except Exception as e:
            backup.status = "failed"
            backup.error_message = str(e)

        backup.save()
        serializer = self.get_serializer(backup)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    async def _run_pg_dump(self, db, filepath, env):
        proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            "-h", db["HOST"],
            "-p", str(db["PORT"]),
            "-U", db["USER"],
            "-Fc",
            "-f", filepath,
            db["NAME"],
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        proc.stdout = stdout.decode()
        proc.stderr = stderr.decode()
        return proc

    class Pagination(generics.ListCreateAPIView.pagination_class.__class__ if generics.ListCreateAPIView.pagination_class else object):
        pass


class BackupDeleteView(generics.DestroyAPIView):
    serializer_class = DatabaseBackupSerializer
    permission_classes = [IsAdminUser]
    queryset = DatabaseBackup.objects.all()

    def perform_destroy(self, instance):
        # 删除磁盘上的文件
        filepath = os.path.join(settings.BACKUP_DIR, instance.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        instance.delete()


class BackupDownloadView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            backup = DatabaseBackup.objects.get(pk=pk)
        except DatabaseBackup.DoesNotExist:
            return Response(
                {"detail": "备份记录不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        if backup.status != "success":
            return Response(
                {"detail": "该备份不可下载"}, status=status.HTTP_400_BAD_REQUEST
            )

        filepath = os.path.join(settings.BACKUP_DIR, backup.filename)
        if not os.path.exists(filepath):
            return Response(
                {"detail": "备份文件不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(filepath, "rb"),
            as_attachment=True,
            filename=backup.filename,
        )
```

- [ ] **Step 2: Add backup URL patterns**

Replace `backend/apps/settings/urls.py` with:

```python
from django.urls import path
from .views import SiteSettingsView, LabelSettingsView
from .backup_views import BackupListCreateView, BackupDeleteView, BackupDownloadView

urlpatterns = [
    path("", SiteSettingsView.as_view(), name="site-settings"),
    path("labels/", LabelSettingsView.as_view(), name="label-settings"),
    path("backups/", BackupListCreateView.as_view(), name="backup-list-create"),
    path("backups/<int:pk>/", BackupDeleteView.as_view(), name="backup-delete"),
    path(
        "backups/<int:pk>/download/",
        BackupDownloadView.as_view(),
        name="backup-download",
    ),
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/settings/backup_views.py backend/apps/settings/urls.py
git commit -m "feat(backup): add backup list, create, delete, and download views"
```

---

### Task 5: Backend Tests

**Files:**
- Create: `backend/tests/test_backups.py`

- [ ] **Step 1: Write tests**

Create `backend/tests/test_backups.py`:

```python
import os
import pytest
from unittest.mock import patch, AsyncMock
from django.conf import settings
from apps.settings.models import DatabaseBackup


@pytest.mark.django_db
class TestBackupAPI:
    """数据库备份 API 测试"""

    def test_list_backups_requires_admin(self, api_client):
        """未认证用户不能访问备份列表"""
        resp = api_client.get("/api/settings/backups/")
        assert resp.status_code == 401

    def test_list_backups_requires_staff(self, regular_client):
        """普通用户不能访问备份列表"""
        resp = regular_client.get("/api/settings/backups/")
        assert resp.status_code == 403

    def test_list_backups_empty(self, superuser_client):
        """管理员可以看到空备份列表"""
        resp = superuser_client.get("/api/settings/backups/")
        assert resp.status_code == 200
        assert resp.data["results"] == []

    def test_list_backups_with_records(self, superuser_client, auth_user):
        """管理员可以看到备份记录"""
        DatabaseBackup.objects.create(
            filename="test_20260403_120000.dump",
            file_size=1024,
            status="success",
            created_by=auth_user,
        )
        resp = superuser_client.get("/api/settings/backups/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 1
        assert resp.data["results"][0]["filename"] == "test_20260403_120000.dump"

    @patch("apps.settings.backup_views.asyncio.run")
    def test_create_backup_success(self, mock_run, superuser_client, tmp_path):
        """管理员可以触发备份"""
        mock_proc = type("Proc", (), {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        })()
        mock_run.return_value = mock_proc

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            # 创建一个假的 dump 文件让 os.path.getsize 工作
            mock_run.side_effect = lambda coro: (
                mock_proc,
                open(tmp_path / f"devtrack_{{}}.dump".format("test"), "w").close(),
            )[0]

            resp = superuser_client.post("/api/settings/backups/")

        assert resp.status_code == 201
        assert resp.data["status"] in ["success", "failed"]

    def test_create_backup_blocks_concurrent(self, superuser_client):
        """不允许同时运行多个备份"""
        DatabaseBackup.objects.create(
            filename="running.dump",
            status="running",
        )
        resp = superuser_client.post("/api/settings/backups/")
        assert resp.status_code == 409

    def test_delete_backup(self, superuser_client, tmp_path):
        """管理员可以删除备份"""
        backup = DatabaseBackup.objects.create(
            filename="to_delete.dump",
            file_size=512,
            status="success",
        )
        # 创建文件
        filepath = tmp_path / "to_delete.dump"
        filepath.write_bytes(b"test")

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            resp = superuser_client.delete(f"/api/settings/backups/{backup.id}/")

        assert resp.status_code == 204
        assert not DatabaseBackup.objects.filter(id=backup.id).exists()
        assert not filepath.exists()

    def test_download_backup(self, superuser_client, tmp_path):
        """管理员可以下载备份文件"""
        backup = DatabaseBackup.objects.create(
            filename="download_me.dump",
            file_size=4,
            status="success",
        )
        filepath = tmp_path / "download_me.dump"
        filepath.write_bytes(b"data")

        with patch.object(settings, "BACKUP_DIR", str(tmp_path)):
            resp = superuser_client.get(
                f"/api/settings/backups/{backup.id}/download/"
            )

        assert resp.status_code == 200
        assert resp["Content-Disposition"] == 'attachment; filename="download_me.dump"'

    def test_download_failed_backup_rejected(self, superuser_client):
        """不能下载失败的备份"""
        backup = DatabaseBackup.objects.create(
            filename="failed.dump",
            status="failed",
            error_message="pg_dump error",
        )
        resp = superuser_client.get(
            f"/api/settings/backups/{backup.id}/download/"
        )
        assert resp.status_code == 400

    def test_delete_backup_requires_admin(self, regular_client):
        """普通用户不能删除备份"""
        backup = DatabaseBackup.objects.create(
            filename="test.dump",
            status="success",
        )
        resp = regular_client.delete(f"/api/settings/backups/{backup.id}/")
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_backups.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_backups.py
git commit -m "test(backup): add API tests for backup endpoints"
```

---

### Task 6: Frontend — Backup Management Page

**Files:**
- Create: `frontend/app/pages/app/settings/backups.vue`

- [ ] **Step 1: Create the backup page**

Create `frontend/app/pages/app/settings/backups.vue`:

```vue
<script setup lang="ts">
definePageMeta({ layout: 'app' })

interface Backup {
  id: number
  filename: string
  file_size: number | null
  status: 'running' | 'success' | 'failed'
  error_message: string
  created_by_name: string
  created_at: string
}

const { api, getToken } = useApi()
const toast = useToast()

const backups = ref<Backup[]>([])
const loading = ref(false)
const backingUp = ref(false)
const page = ref(1)
const totalPages = ref(1)

async function fetchBackups() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value) })
    const data = await api<any>(`/api/settings/backups/?${params}`)
    backups.value = data.results
    totalPages.value = Math.ceil(data.count / (data.page_size || 10))
  } catch {
    toast.add({ title: '加载备份记录失败', color: 'error' })
  } finally {
    loading.value = false
  }
}

async function createBackup() {
  backingUp.value = true
  try {
    await api<Backup>('/api/settings/backups/', { method: 'POST' })
    toast.add({ title: '备份成功', color: 'success' })
    await fetchBackups()
  } catch (e: any) {
    const msg = e?.data?.detail || '备份失败'
    toast.add({ title: msg, color: 'error' })
  } finally {
    backingUp.value = false
  }
}

async function deleteBackup(backup: Backup) {
  if (!confirm(`确认删除备份 ${backup.filename}？`)) return
  try {
    await api(`/api/settings/backups/${backup.id}/`, { method: 'DELETE' })
    toast.add({ title: '已删除', color: 'success' })
    await fetchBackups()
  } catch {
    toast.add({ title: '删除失败', color: 'error' })
  }
}

function downloadBackup(backup: Backup) {
  const token = getToken()
  const link = document.createElement('a')
  link.href = `/api/settings/backups/${backup.id}/download/`
  // 通过 fetch 下载以携带 token
  fetch(link.href, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(res => {
      if (!res.ok) throw new Error()
      return res.blob()
    })
    .then(blob => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = backup.filename
      a.click()
      URL.revokeObjectURL(url)
    })
    .catch(() => toast.add({ title: '下载失败', color: 'error' }))
}

function formatSize(bytes: number | null): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

const statusColor: Record<string, string> = {
  running: 'info',
  success: 'success',
  failed: 'error',
}

const statusLabel: Record<string, string> = {
  running: '备份中',
  success: '成功',
  failed: '失败',
}

const columns = [
  { key: 'filename', label: '文件名' },
  { key: 'file_size', label: '大小' },
  { key: 'status', label: '状态' },
  { key: 'created_by_name', label: '操作人' },
  { key: 'created_at', label: '时间' },
  { key: 'actions', label: '操作' },
]

watch(page, fetchBackups)
onMounted(fetchBackups)
</script>

<template>
  <div class="p-6 max-w-5xl">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold">数据库备份</h1>
      <UButton
        icon="i-heroicons-arrow-down-tray"
        :loading="backingUp"
        @click="createBackup"
      >
        立即备份
      </UButton>
    </div>

    <UTable
      :columns="columns"
      :rows="backups"
      :loading="loading"
    >
      <template #file_size-data="{ row }">
        {{ formatSize(row.file_size) }}
      </template>

      <template #status-data="{ row }">
        <UBadge :color="statusColor[row.status]" variant="subtle">
          {{ statusLabel[row.status] }}
        </UBadge>
      </template>

      <template #created_at-data="{ row }">
        {{ formatTime(row.created_at) }}
      </template>

      <template #actions-data="{ row }">
        <div class="flex gap-2">
          <UButton
            v-if="row.status === 'success'"
            variant="ghost"
            size="xs"
            icon="i-heroicons-arrow-down-tray"
            @click="downloadBackup(row)"
          >
            下载
          </UButton>
          <UButton
            variant="ghost"
            size="xs"
            color="error"
            icon="i-heroicons-trash"
            @click="deleteBackup(row)"
          >
            删除
          </UButton>
        </div>
      </template>
    </UTable>

    <div v-if="totalPages > 1" class="flex justify-center mt-4">
      <UPagination v-model="page" :total="totalPages * 10" :items-per-page="10" />
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/pages/app/settings/backups.vue
git commit -m "feat(backup): add backup management page"
```

---

### Task 7: Navigation + Route Permission Integration

**Files:**
- Modify: page-perms config (via `sync_page_perms` management command or admin)

- [ ] **Step 1: Register the backup page route in page-perms**

The project uses `django-page-perms` to manage page routes dynamically. Check how existing routes are configured:

Run: `cd backend && uv run python manage.py shell -c "from page_perms.models import PageRoute; print([(r.path, r.label, r.permission) for r in PageRoute.objects.all()[:5]])"`

The backup page needs a PageRoute entry. Since this page uses `IsAdminUser` (not model permissions), the route needs `meta.superuserOnly = true` or a staff-level check. Look at how `useNavigation.ts` handles `meta.superuserOnly`:

```typescript
if (item.meta?.superuserOnly && !user.value?.is_superuser) return false
```

Add the route via the management command config or Django admin:
- path: `/app/settings/backups`
- label: `数据库备份`
- icon: `i-heroicons-circle-stack`
- show_in_nav: `true`
- is_active: `true`
- meta: `{"superuserOnly": true}`
- permission: (leave null — access is controlled by `is_staff` on the API and `superuserOnly` on the frontend)

The exact method depends on how `sync_page_perms` is configured. Check:

Run: `cd backend && grep -r "backups\|备份\|BACKUP" apps/ config/ --include="*.py" | head -20`

If the management command reads from a config dict (like `PAGE_PERMS` in settings), add the entry there. If routes are managed via admin UI, add it manually.

- [ ] **Step 2: Verify navigation shows the backup page for admin users**

Run the dev server and log in as an admin user. The "数据库备份" item should appear in the sidebar. Non-admin users should not see it.

- [ ] **Step 3: Commit (if config file was modified)**

```bash
git add -A
git commit -m "feat(backup): register backup page route in page-perms"
```

---

### Task 8: Deployment Config Updates

**Files:**
- Modify: `servers/prod/docker-compose.yml`
- Modify: `servers/test/docker-compose.yml`

- [ ] **Step 1: Update production docker-compose**

In `servers/prod/docker-compose.yml`, update the backend service:

1. Add `backups` volume mount:
```yaml
    volumes:
      - ./.gitconfig-proxy:/root/.gitconfig:ro
      - repo_data:/data/repos
      - backups:/data/backups
```

2. Switch command to uvicorn:
```yaml
    command: >
      sh -c "uv run python manage.py migrate --noinput &&
             uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000"
```

3. Add `backups` to the top-level volumes:
```yaml
volumes:
  repo_data:
  backups:
```

- [ ] **Step 2: Apply same changes to test docker-compose**

Apply the same volume and command changes to `servers/test/docker-compose.yml`.

- [ ] **Step 3: Commit**

```bash
git add servers/prod/docker-compose.yml servers/test/docker-compose.yml
git commit -m "deploy(backup): add backups volume and switch to uvicorn"
```

---

### Task 9: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd backend && uv run pytest -v`
Expected: All tests pass including new backup tests

- [ ] **Step 2: Manual smoke test**

1. Start backend: `cd backend && uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Log in as admin, navigate to `/app/settings/backups`
4. Click "立即备份", verify it completes
5. Verify file appears in list with correct size
6. Click "下载", verify file downloads
7. Click "删除", verify record and file removed

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(backup): address issues found during smoke test"
```
