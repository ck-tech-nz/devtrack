# Issue Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `Attachment` model to the `tools` app so Issues can track uploaded images, with sync from description Markdown, re-insert from sidebar panel, and MinIO cleanup on delete.

**Architecture:** `Attachment` records are created on upload (issue=null), then linked to an Issue when the Issue is created/updated by scanning MinIO URLs in `description`. Attachments are never unlinked on description edit — only on explicit delete. The Issue detail sidebar shows image attachments with insert-back and delete actions.

**Tech Stack:** Django/DRF backend (Python), boto3 for MinIO, Nuxt 4 / Vue 3 frontend with `useApi` composable.

---

## File Map

| Action | File |
|--------|------|
| Create | `backend/apps/tools/models.py` |
| Create | `backend/apps/tools/serializers.py` |
| Create | `backend/apps/tools/admin.py` |
| Modify | `backend/apps/tools/storage.py` |
| Modify | `backend/apps/tools/views.py` |
| Modify | `backend/apps/tools/urls.py` |
| Modify | `backend/apps/issues/serializers.py` |
| Modify | `backend/apps/issues/views.py` |
| Modify | `backend/apps/issues/urls.py` |
| Modify | `backend/tests/factories.py` |
| Modify | `backend/tests/test_upload.py` |
| Create | `backend/tests/test_attachments.py` |
| Modify | `frontend/app/pages/app/issues/[id].vue` |

---

### Task 1: Attachment Model + Migration

**Files:**
- Create: `backend/apps/tools/models.py`
- Test: `backend/tests/test_attachments.py` (first test only)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_attachments.py
import pytest
from tests.factories import UserFactory, IssueFactory


@pytest.mark.django_db
class TestAttachmentModel:
    def test_attachment_str(self):
        from apps.tools.models import Attachment
        from tests.factories import AttachmentFactory
        a = AttachmentFactory(file_name="screenshot.png")
        assert str(a) == "screenshot.png"

    def test_is_image_true(self):
        from apps.tools.models import Attachment
        from tests.factories import AttachmentFactory
        a = AttachmentFactory(mime_type="image/png")
        assert a.is_image is True

    def test_is_image_false(self):
        from apps.tools.models import Attachment
        from tests.factories import AttachmentFactory
        a = AttachmentFactory(mime_type="application/pdf")
        assert a.is_image is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_attachments.py -v
```
Expected: ImportError — `AttachmentFactory` not defined, `Attachment` model not defined.

- [ ] **Step 3: Create the Attachment model**

```python
# backend/apps/tools/models.py
import uuid
from django.conf import settings
from django.db import models


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        "issues.Issue", on_delete=models.CASCADE,
        related_name="attachments", null=True, blank=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="attachments",
    )
    file_name = models.CharField(max_length=255, verbose_name="文件名")
    file_key = models.CharField(max_length=500, verbose_name="存储键")
    file_url = models.URLField(max_length=1000, verbose_name="访问地址")
    file_size = models.PositiveIntegerField(verbose_name="文件大小")
    mime_type = models.CharField(max_length=100, verbose_name="类型")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "附件"
        verbose_name_plural = "附件"
        ordering = ["-created_at"]

    def __str__(self):
        return self.file_name

    @property
    def is_image(self):
        return self.mime_type.startswith("image/")
```

- [ ] **Step 4: Add AttachmentFactory to factories.py**

Add at the bottom of `backend/tests/factories.py`:

```python
from apps.tools.models import Attachment

class AttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attachment

    issue = None
    uploaded_by = factory.SubFactory(UserFactory)
    file_name = factory.Sequence(lambda n: f"screenshot_{n}.png")
    file_key = factory.Sequence(lambda n: f"2026/03/27/{n:04d}.png")
    file_url = factory.LazyAttribute(lambda o: f"http://minio:9000/devtrack-uploads/{o.file_key}")
    file_size = 102400
    mime_type = "image/png"
```

- [ ] **Step 5: Generate and apply migration**

```bash
cd backend && uv run python manage.py makemigrations tools
uv run python manage.py migrate
```
Expected: `Migrations for 'tools': tools/migrations/0001_initial.py`

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_attachments.py::TestAttachmentModel -v
```
Expected: 3 PASSED.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/tools/models.py backend/apps/tools/migrations/ backend/tests/factories.py backend/tests/test_attachments.py
git commit -m "feat(tools): add Attachment model"
```

---

### Task 2: Update storage.py to Return Key and Support Delete

**Files:**
- Modify: `backend/apps/tools/storage.py`

- [ ] **Step 1: Update `upload_image` to return `(url, key)` and add `delete_object`**

Replace the full contents of `backend/apps/tools/storage.py`:

```python
import uuid
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings


def get_s3_client():
    scheme = "https" if settings.MINIO_USE_SSL else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4", proxies={}),
        region_name="us-east-1",
    )


def upload_image(file) -> tuple[str, str]:
    """Upload a file to MinIO. Returns (public_url, object_key)."""
    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "bin"
    now = datetime.now()
    key = f"{now.year}/{now.month:02d}/{now.day:02d}/{uuid.uuid4().hex}.{ext}"

    client = get_s3_client()
    client.upload_fileobj(
        file,
        settings.MINIO_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )
    return f"{settings.MINIO_PUBLIC_URL}/{key}", key


def delete_object(key: str) -> None:
    """Delete an object from MinIO by its object key."""
    client = get_s3_client()
    client.delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/tools/storage.py
git commit -m "feat(tools): upload_image returns (url, key); add delete_object"
```

---

### Task 3: AttachmentSerializer

**Files:**
- Create: `backend/apps/tools/serializers.py`

- [ ] **Step 1: Create the serializer**

```python
# backend/apps/tools/serializers.py
from rest_framework import serializers
from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "file_name", "file_url", "file_size", "mime_type", "created_at"]
        read_only_fields = fields
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/tools/serializers.py
git commit -m "feat(tools): add AttachmentSerializer"
```

---

### Task 4: Update ImageUploadView to Create Attachment Record

**Files:**
- Modify: `backend/apps/tools/views.py`
- Modify: `backend/tests/test_upload.py`

- [ ] **Step 1: Update test — mock must now return a tuple and expect Attachment creation**

Replace `backend/tests/test_upload.py` with:

```python
import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
class TestImageUpload:
    URL = "/api/tools/upload/image/"

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.post(self.URL)
        assert response.status_code == 401

    def test_no_file_returns_400(self, auth_client):
        response = auth_client.post(self.URL)
        assert response.status_code == 400

    def test_invalid_type_returns_400(self, auth_client):
        f = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "类型" in response.data["detail"]

    def test_oversized_file_returns_400(self, auth_client):
        f = SimpleUploadedFile("big.png", b"x" * (6 * 1024 * 1024), content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "大小" in response.data["detail"]

    @patch("apps.tools.storage.upload_image")
    def test_valid_upload_creates_attachment(self, mock_upload, auth_client):
        from apps.tools.models import Attachment
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/03/24/abc.png",
            "2026/03/24/abc.png",
        )
        f = SimpleUploadedFile("screenshot.png", b"\x89PNG" + b"\x00" * 100, content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
        assert response.data["url"] == "http://minio:9000/devtrack-uploads/2026/03/24/abc.png"
        assert response.data["filename"] == "screenshot.png"
        assert Attachment.objects.filter(file_url=response.data["url"]).exists()

    @patch("apps.tools.storage.upload_image")
    def test_upload_with_issue_links_attachment(self, mock_upload, auth_client):
        from apps.tools.models import Attachment
        from tests.factories import IssueFactory
        issue = IssueFactory()
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/03/24/def.png",
            "2026/03/24/def.png",
        )
        f = SimpleUploadedFile("photo.png", b"\x89PNG" + b"\x00" * 100, content_type="image/png")
        response = auth_client.post(
            self.URL, {"file": f, "issue_id": issue.id}, format="multipart"
        )
        assert response.status_code == 200
        assert Attachment.objects.filter(issue=issue).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_upload.py -v
```
Expected: `test_valid_upload_creates_attachment` FAILs (Attachment not created yet), old test also fails due to mock return value change.

- [ ] **Step 3: Update ImageUploadView**

Replace `backend/apps/tools/views.py` with:

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.tools.storage as tools_storage
from .models import Attachment

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "未提供文件"}, status=400)
        if file.content_type not in ALLOWED_TYPES:
            return Response(
                {"detail": f"不支持的文件类型: {file.content_type}，仅支持 PNG/JPEG/GIF/WebP"},
                status=400,
            )
        if file.size > MAX_SIZE:
            return Response(
                {"detail": f"文件大小 ({file.size // 1024 // 1024}MB) 超过限制 (5MB)"},
                status=400,
            )

        url, key = tools_storage.upload_image(file)

        issue_id = request.data.get("issue_id")
        issue = None
        if issue_id:
            from apps.issues.models import Issue
            issue = Issue.objects.filter(pk=issue_id).first()

        Attachment.objects.create(
            issue=issue,
            uploaded_by=request.user,
            file_name=file.name,
            file_key=key,
            file_url=url,
            file_size=file.size,
            mime_type=file.content_type,
        )

        return Response({"url": url, "filename": file.name})


class AttachmentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        attachment = Attachment.objects.filter(pk=pk).first()
        if not attachment:
            return Response({"detail": "附件不存在"}, status=404)
        if attachment.uploaded_by != request.user and not request.user.is_staff:
            return Response({"detail": "无权限删除此附件"}, status=403)
        tools_storage.delete_object(attachment.file_key)
        attachment.delete()
        return Response(status=204)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_upload.py -v
```
Expected: all 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/tools/views.py backend/tests/test_upload.py
git commit -m "feat(tools): create Attachment on upload; add AttachmentDeleteView"
```

---

### Task 5: Wire Delete Endpoint to URLs

**Files:**
- Modify: `backend/apps/tools/urls.py`

- [ ] **Step 1: Add delete route**

```python
# backend/apps/tools/urls.py
from django.urls import path
from apps.tools.views import ImageUploadView, AttachmentDeleteView

urlpatterns = [
    path("upload/image/", ImageUploadView.as_view(), name="upload-image"),
    path("attachments/<uuid:pk>/", AttachmentDeleteView.as_view(), name="attachment-delete"),
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/tools/urls.py
git commit -m "feat(tools): register attachment delete URL"
```

---

### Task 6: Sync Attachments When Issue is Saved + Issue Detail Includes Attachments

**Files:**
- Modify: `backend/apps/issues/serializers.py`
- Modify: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write tests for attachment sync**

Add to `backend/tests/test_attachments.py`:

```python
@pytest.mark.django_db
class TestAttachmentSync:
    def test_create_issue_links_attachments_from_description(self, auth_client, site_settings):
        from apps.tools.models import Attachment
        from tests.factories import ProjectFactory, UserFactory
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=auth_client.handler._force_authenticate[0].id
                                 if hasattr(auth_client.handler, '_force_authenticate')
                                 else auth_client._credentials.get('HTTP_AUTHORIZATION', ''))
        # Use auth_client directly — create orphan attachment first
        from tests.factories import AttachmentFactory
        project = ProjectFactory()
        # We need to get the user from auth_client
        # auth_client is force_authenticated so we get user from DB
        att = AttachmentFactory(
            issue=None,
            file_url="http://minio:9000/devtrack-uploads/2026/03/27/abc.png",
        )
        # Override uploaded_by to be the authenticated user
        from django.contrib.auth import get_user_model
        # The auth_client fixture uses a fresh user — we need to grab it
        # Update attachment to belong to that user
        att.uploaded_by = User.objects.last()
        att.save()

        description = "See screenshot: ![img](http://minio:9000/devtrack-uploads/2026/03/27/abc.png)"
        response = auth_client.post("/api/issues/", {
            "project": project.id,
            "title": "Test issue",
            "description": description,
            "priority": "P1",
            "status": "待处理",
            "labels": [],
        }, format="json")
        assert response.status_code == 201
        att.refresh_from_db()
        assert att.issue_id == response.data["id"]

    def test_detail_serializer_includes_attachments(self, auth_client, site_settings):
        from tests.factories import IssueFactory, AttachmentFactory
        issue = IssueFactory()
        AttachmentFactory(issue=issue)
        AttachmentFactory(issue=issue)
        response = auth_client.get(f"/api/issues/{issue.id}/")
        assert response.status_code == 200
        assert len(response.data["attachments"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_attachments.py::TestAttachmentSync -v
```
Expected: FAIL — `attachments` key missing from detail response.

- [ ] **Step 3: Update IssueCreateUpdateSerializer to sync attachments**

In `backend/apps/issues/serializers.py`, add a helper function before the serializer classes and update `create` and `update`:

```python
# Add after imports, before class definitions:
import re
from django.conf import settings as django_settings


def _sync_attachments(issue, user):
    """Link unowned Attachment records whose URL appears in issue.description."""
    from apps.tools.models import Attachment
    if not issue.description:
        return
    minio_base = django_settings.MINIO_PUBLIC_URL
    urls = set(re.findall(r'https?://\S+', issue.description))
    cleaned = {re.sub(r'[)"\']+$', '', u) for u in urls}
    for url in cleaned:
        if url.startswith(minio_base):
            Attachment.objects.filter(
                file_url=url, issue=None, uploaded_by=user
            ).update(issue=issue)
```

Then in `IssueCreateUpdateSerializer.create()`, add the sync call after `super().create()`:

```python
def create(self, validated_data):
    validated_data["reporter"] = self.context["request"].user
    issue = super().create(validated_data)
    Activity.objects.create(
        user=self.context["request"].user,
        issue=issue,
        action="created",
    )
    _sync_attachments(issue, self.context["request"].user)
    return issue
```

And in `update()`, add after `super().update()`:

```python
def update(self, instance, validated_data):
    user = self.context["request"].user
    old_status = instance.status
    old_assignee = instance.assignee_id
    issue = super().update(instance, validated_data)

    new_status = validated_data.get("status")
    if new_status and new_status != old_status:
        action = "resolved" if new_status == "已解决" else "closed" if new_status == "已关闭" else "updated"
        Activity.objects.create(
            user=user, issue=issue, action=action,
            detail=f"状态从 {old_status} 改为 {new_status}",
        )
        if new_status == "已解决" and not issue.resolved_at:
            issue.resolved_at = timezone.now()
            issue.save(update_fields=["resolved_at"])

    new_assignee = validated_data.get("assignee")
    if "assignee" in validated_data and str(getattr(new_assignee, "id", None)) != str(old_assignee):
        Activity.objects.create(
            user=user, issue=issue, action="assigned",
            detail=f"分配给 {new_assignee.name}" if new_assignee else "取消分配",
        )

    _sync_attachments(issue, user)
    return issue
```

- [ ] **Step 4: Add `attachments` field to IssueDetailSerializer**

In `backend/apps/issues/serializers.py`, update the imports and `IssueDetailSerializer`:

```python
# Add to imports at top:
from apps.tools.serializers import AttachmentSerializer
```

```python
class IssueDetailSerializer(IssueListSerializer):
    github_issues = GitHubIssueBriefSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta(IssueListSerializer.Meta):
        fields = IssueListSerializer.Meta.fields + [
            "description", "estimated_completion",
            "actual_hours", "resolved_at", "github_issues", "attachments",
        ]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/test_attachments.py -v
```
Expected: `TestAttachmentModel` (3 PASSED), `TestAttachmentSync::test_detail_serializer_includes_attachments` PASSED.

Note: `test_create_issue_links_attachments_from_description` requires matching the auth user — skip for now or run all tests to verify no regressions.

```bash
cd backend && uv run pytest -x
```
Expected: all pass or only the user-matching test fails (see step 6).

- [ ] **Step 6: Fix the sync test to work with auth_client fixture**

Replace the `test_create_issue_links_attachments_from_description` test with a cleaner version that doesn't require extracting the user from the client:

```python
    def test_create_issue_links_attachments_from_description(self, auth_client, site_settings):
        from apps.tools.models import Attachment
        from tests.factories import ProjectFactory, AttachmentFactory, UserFactory
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Upload a file first to get an attachment owned by the auth user
        # We simulate by creating the attachment with the most-recently-created user
        # (auth_client fixture always creates a fresh UserFactory user last)
        user = User.objects.order_by("-date_joined").first()
        project = ProjectFactory()
        att = AttachmentFactory(
            issue=None,
            uploaded_by=user,
            file_url="http://minio:9000/devtrack-uploads/2026/03/27/abc.png",
        )

        description = "截图: ![img](http://minio:9000/devtrack-uploads/2026/03/27/abc.png)"
        response = auth_client.post("/api/issues/", {
            "project": project.id,
            "title": "测试问题",
            "description": description,
            "priority": "P1",
            "status": "待处理",
            "labels": [],
        }, format="json")
        assert response.status_code == 201
        att.refresh_from_db()
        assert att.issue_id == response.data["id"]
```

- [ ] **Step 7: Run all tests**

```bash
cd backend && uv run pytest -x
```
Expected: all PASSED.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/issues/serializers.py backend/tests/test_attachments.py
git commit -m "feat(issues): sync attachments from description on save; add attachments to detail"
```

---

### Task 7: Issue Attachments List Endpoint

**Files:**
- Modify: `backend/apps/issues/views.py`
- Modify: `backend/apps/issues/urls.py`
- Modify: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write test**

Add to `backend/tests/test_attachments.py`:

```python
@pytest.mark.django_db
class TestAttachmentDeleteAPI:
    def test_delete_attachment_calls_minio(self, auth_client):
        from unittest.mock import patch
        from tests.factories import AttachmentFactory
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.order_by("-date_joined").first()
        att = AttachmentFactory(uploaded_by=user, file_key="2026/03/27/test.png")

        with patch("apps.tools.storage.delete_object") as mock_del:
            response = auth_client.delete(f"/api/tools/attachments/{att.id}/")
        assert response.status_code == 204
        mock_del.assert_called_once_with("2026/03/27/test.png")
        from apps.tools.models import Attachment
        assert not Attachment.objects.filter(id=att.id).exists()

    def test_delete_attachment_forbidden_for_other_user(self, auth_client):
        from tests.factories import AttachmentFactory, UserFactory
        other_user = UserFactory()
        att = AttachmentFactory(uploaded_by=other_user)
        response = auth_client.delete(f"/api/tools/attachments/{att.id}/")
        assert response.status_code == 403

    def test_delete_nonexistent_returns_404(self, auth_client):
        import uuid
        response = auth_client.delete(f"/api/tools/attachments/{uuid.uuid4()}/")
        assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_attachments.py::TestAttachmentDeleteAPI -v
```
Expected: all 3 FAIL (endpoints not yet wired).

- [ ] **Step 3: Run tests after URLs are already wired (Task 5 did this)**

The URL was already added in Task 5. Run:

```bash
cd backend && uv run pytest tests/test_attachments.py::TestAttachmentDeleteAPI -v
```
Expected: all 3 PASSED (URLs registered in Task 5, view implemented in Task 4).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_attachments.py
git commit -m "test(tools): add attachment delete API tests"
```

---

### Task 8: Django Admin for Tools App

**Files:**
- Create: `backend/apps/tools/admin.py`

- [ ] **Step 1: Create admin.py**

```python
# backend/apps/tools/admin.py
from django.contrib import admin
from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["file_name", "mime_type", "file_size_kb", "issue", "uploaded_by", "created_at"]
    list_filter = ["mime_type", "created_at"]
    search_fields = ["file_name", "issue__title", "uploaded_by__name"]
    raw_id_fields = ["issue", "uploaded_by"]
    readonly_fields = ["id", "file_key", "file_url", "file_size", "mime_type", "created_at"]

    @admin.display(description="大小 (KB)")
    def file_size_kb(self, obj):
        return f"{obj.file_size // 1024} KB"
```

- [ ] **Step 2: Verify admin loads**

```bash
cd backend && uv run python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/tools/admin.py
git commit -m "feat(tools): add Django admin for Attachment model"
```

---

### Task 9: Frontend — Attachments Panel in Issue Detail

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

The issue detail page already fetches issue data via `GET /api/issues/{id}/` which now includes `attachments`. We need to:
1. Show an "附件" panel in the sidebar
2. Let users click an image to insert it into the description
3. Let users delete an attachment (with confirmation)

- [ ] **Step 1: Add `attachments` reactive state and functions to the `<script setup>` block**

Find the `<script setup lang="ts">` section in `frontend/app/pages/app/issues/[id].vue`. Locate where `issue` ref is defined (likely `const issue = ref(...)`) and the `saveAll` / `updateField` functions. Add the following after the existing computed/function definitions (before the closing of `<script setup>`):

```typescript
// Attachments
const attachments = computed(() => (issue.value?.attachments ?? []).filter((a: any) => a.mime_type?.startsWith('image/')))

async function deleteAttachment(id: string) {
  const { api } = useApi()
  try {
    await api(`/api/tools/attachments/${id}/`, { method: 'DELETE' })
    if (issue.value) {
      issue.value.attachments = issue.value.attachments.filter((a: any) => a.id !== id)
    }
  } catch {
    // 删除失败不做提示，下次刷新会恢复
  }
}

function insertAttachmentToDescription(attachment: any) {
  form.value.description = (form.value.description || '') + `\n![${attachment.file_name}](${attachment.file_url})`
}
```

- [ ] **Step 2: Add attachments panel to the sidebar in the template**

In the template, find the sidebar section (the `<div class="space-y-4">` that contains the "信息", "关联仓库", "AI 分析", "GitHub 关联" cards). Add this new card **before** the "关联仓库" card:

```html
<!-- 附件 -->
<div v-if="attachments.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
  <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">附件图片</h3>
  <div class="grid grid-cols-2 gap-2">
    <div
      v-for="att in attachments"
      :key="att.id"
      class="relative group rounded-lg overflow-hidden border border-gray-100 dark:border-gray-800"
    >
      <img
        :src="att.file_url"
        :alt="att.file_name"
        class="w-full h-20 object-cover cursor-pointer hover:opacity-80 transition-opacity"
        :title="att.file_name"
        @click="insertAttachmentToDescription(att)"
      />
      <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-1">
        <button
          class="text-white text-xs bg-primary-600 hover:bg-primary-700 rounded px-1.5 py-0.5"
          @click.stop="insertAttachmentToDescription(att)"
        >插入</button>
        <button
          class="text-white text-xs bg-red-600 hover:bg-red-700 rounded px-1.5 py-0.5"
          @click.stop="deleteAttachment(att.id)"
        >删除</button>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Verify in browser**

Start the dev servers:
```bash
# Terminal 1
cd backend && uv run python manage.py runserver

# Terminal 2
cd frontend && npm run dev
```

1. Open an existing issue at `http://localhost:3000/app/issues/{id}`
2. Switch to edit mode in the Markdown editor
3. Paste or drag an image — verify it uploads and the URL appears in description
4. Save the issue — verify the attachment appears in the "附件图片" panel
5. Delete the image URL from description, save again — verify attachment panel still shows it
6. Click "插入" — verify `![filename](url)` is appended to description
7. Click "删除" — verify panel updates and the image is removed

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "feat(issues): add attachments panel with insert and delete actions"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| Attachment model in tools app | Task 1 |
| Issue can bind multiple attachments | Task 1 (ForeignKey with related_name) |
| Image URLs in description sync to attachments on save | Task 6 |
| Attachments NOT removed when URL deleted from description | Task 6 (`_sync_attachments` only adds, never removes) |
| Re-insert image from attachments panel | Task 9 (insertAttachmentToDescription) |
| Only image type attachments shown in panel | Task 9 (computed filter on mime_type) |
| Delete attachment removes MinIO object | Task 4 (AttachmentDeleteView calls delete_object) |
| Django admin for tools app | Task 8 |

### Placeholder Check

No TBD, TODO, or placeholder phrases found.

### Type Consistency

- `upload_image` returns `tuple[str, str]` → used as `url, key = tools_storage.upload_image(file)` in Task 4 ✓
- `Attachment.file_key` used in `delete_object(attachment.file_key)` ✓
- `AttachmentSerializer` fields match `Attachment` model fields ✓
- `issue.attachments` from `related_name="attachments"` used in `IssueDetailSerializer` ✓
- Frontend `att.id`, `att.file_url`, `att.file_name`, `att.mime_type` match serializer output ✓
