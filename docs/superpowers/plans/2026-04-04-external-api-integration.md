# External API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a RESTful API at `/api/external/` for external platforms to create issues and query their status, authenticated via API keys bound to specific projects.

**Architecture:** New `ExternalAPIKey` model in `settings` app binds API keys to projects + default assignees. A custom DRF `APIKeyAuthentication` class validates `Bearer` tokens. External views live under `/api/external/` with dedicated serializers. Two new fields (`source`, `source_meta`) on `Issue` model store provenance. Frontend shows source metadata on issue detail and a badge on list/kanban.

**Tech Stack:** Django REST Framework, PostgreSQL JSONField, Nuxt 4 (Vue 3), Tailwind CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `backend/apps/settings/models.py` | Add `ExternalAPIKey` model |
| Modify | `backend/apps/settings/admin.py` | Register `ExternalAPIKey` in Django admin |
| Modify | `backend/apps/issues/models.py` | Add `source`, `source_meta` fields |
| Create | `backend/apps/external/__init__.py` | External API package |
| Create | `backend/apps/external/authentication.py` | `APIKeyAuthentication` class |
| Create | `backend/apps/external/serializers.py` | Serializers for external create/read |
| Create | `backend/apps/external/views.py` | External API views |
| Create | `backend/apps/external/urls.py` | URL routing for `/api/external/` |
| Modify | `backend/apps/urls.py` | Mount external URLs |
| Create | `backend/tests/test_external_api.py` | All tests for external API |
| Modify | `backend/tests/factories.py` | Add `ExternalAPIKeyFactory` |
| Modify | `frontend/app/components/IssueCard.vue` | Add "外部" badge |
| Modify | `frontend/app/pages/app/issues/[id].vue` | Add "外部来源" collapsible section |

---

### Task 1: ExternalAPIKey Model + Migration

**Files:**
- Modify: `backend/apps/settings/models.py`
- Modify: `backend/apps/settings/admin.py`
- Modify: `backend/tests/factories.py`
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Write failing test for ExternalAPIKey model**

Create `backend/tests/test_external_api.py`:

```python
import pytest
from tests.factories import ExternalAPIKeyFactory


@pytest.mark.django_db
class TestExternalAPIKeyModel:
    def test_create_api_key(self):
        api_key = ExternalAPIKeyFactory()
        assert api_key.pk is not None
        assert len(api_key.key) == 64
        assert api_key.is_active is True
        assert api_key.project is not None
        assert api_key.default_assignee is not None

    def test_key_auto_generated_when_blank(self):
        api_key = ExternalAPIKeyFactory(key="")
        assert len(api_key.key) == 64

    def test_str_representation(self):
        api_key = ExternalAPIKeyFactory(name="Test Platform")
        assert str(api_key) == "Test Platform"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_external_api.py -v`
Expected: FAIL — `ExternalAPIKeyFactory` not found

- [ ] **Step 3: Add ExternalAPIKey model**

In `backend/apps/settings/models.py`, add after the `DatabaseBackup` class:

```python
import secrets

class ExternalAPIKey(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    key = models.CharField(max_length=64, unique=True, verbose_name="API Key")
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, verbose_name="关联项目"
    )
    default_assignee = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="默认负责人",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "外部 API Key"
        verbose_name_plural = "外部 API Keys"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)
        super().save(*args, **kwargs)
```

- [ ] **Step 4: Add factory**

In `backend/tests/factories.py`, add:

```python
from apps.settings.models import ExternalAPIKey

class ExternalAPIKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExternalAPIKey

    name = factory.Sequence(lambda n: f"External Platform {n}")
    key = factory.LazyFunction(lambda: __import__('secrets').token_hex(32))
    project = factory.SubFactory(ProjectFactory)
    default_assignee = factory.SubFactory(UserFactory)
    is_active = True
```

- [ ] **Step 5: Register in Django admin**

In `backend/apps/settings/admin.py`, add:

```python
from .models import DatabaseBackup, ExternalAPIKey, SiteSettings

@admin.register(ExternalAPIKey)
class ExternalAPIKeyAdmin(ModelAdmin):
    list_display = ("name", "project", "default_assignee", "is_active", "created_at")
    list_filter = ("is_active",)
    readonly_fields = ("created_at",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("key",)
        return self.readonly_fields
```

- [ ] **Step 6: Generate and apply migration**

Run: `cd backend && uv run python manage.py makemigrations settings && uv run python manage.py migrate`

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_external_api.py -v`
Expected: All 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/apps/settings/models.py backend/apps/settings/admin.py backend/apps/settings/migrations/ backend/tests/factories.py backend/tests/test_external_api.py
git commit -m "feat(external): add ExternalAPIKey model with admin and factory"
```

---

### Task 2: Issue Model — Add source and source_meta Fields

**Files:**
- Modify: `backend/apps/issues/models.py`
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Write failing test for new Issue fields**

Append to `backend/tests/test_external_api.py`:

```python
from tests.factories import IssueFactory


@pytest.mark.django_db
class TestIssueSourceFields:
    def test_issue_source_fields_default_null(self):
        issue = IssueFactory()
        assert issue.source is None
        assert issue.source_meta is None

    def test_issue_with_source_meta(self):
        meta = {
            "feedback_id": "FB001",
            "reporter": {"tenant_name": "Test Corp", "user_name": "张三"},
        }
        issue = IssueFactory(source="agent_platform", source_meta=meta)
        issue.refresh_from_db()
        assert issue.source == "agent_platform"
        assert issue.source_meta["feedback_id"] == "FB001"
        assert issue.source_meta["reporter"]["user_name"] == "张三"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestIssueSourceFields -v`
Expected: FAIL — `source` field doesn't exist

- [ ] **Step 3: Add fields to Issue model**

In `backend/apps/issues/models.py`, add after the `resolved_at` field (line 55):

```python
    source = models.CharField(max_length=50, null=True, blank=True, verbose_name="来源")
    source_meta = models.JSONField(null=True, blank=True, verbose_name="来源元数据")
```

- [ ] **Step 4: Generate and apply migration**

Run: `cd backend && uv run python manage.py makemigrations issues && uv run python manage.py migrate`

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestIssueSourceFields -v`
Expected: All 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/issues/models.py backend/apps/issues/migrations/
git commit -m "feat(issues): add source and source_meta fields for external tracking"
```

---

### Task 3: APIKeyAuthentication Class

**Files:**
- Create: `backend/apps/external/__init__.py`
- Create: `backend/apps/external/authentication.py`
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Write failing tests for API key authentication**

Append to `backend/tests/test_external_api.py`:

```python
from rest_framework.test import APIClient


@pytest.fixture
def api_key_obj():
    return ExternalAPIKeyFactory()


@pytest.fixture
def external_client(api_key_obj):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {api_key_obj.key}")
    return client


@pytest.mark.django_db
class TestAPIKeyAuthentication:
    def test_valid_key_authenticates(self, external_client, api_key_obj):
        # We'll test via a real endpoint in Task 5; for now test the class directly
        from apps.external.authentication import APIKeyAuthentication
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {api_key_obj.key}")
        auth = APIKeyAuthentication()
        user, auth_info = auth.authenticate(request)
        assert user == api_key_obj.default_assignee
        assert request.api_key == api_key_obj

    def test_invalid_key_returns_none(self):
        from apps.external.authentication import APIKeyAuthentication
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/", HTTP_AUTHORIZATION="Bearer invalid_key_here")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_inactive_key_returns_none(self):
        from apps.external.authentication import APIKeyAuthentication
        from rest_framework.test import APIRequestFactory

        inactive_key = ExternalAPIKeyFactory(is_active=False)
        factory = APIRequestFactory()
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {inactive_key.key}")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_missing_header_returns_none(self):
        from apps.external.authentication import APIKeyAuthentication
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestAPIKeyAuthentication -v`
Expected: FAIL — `apps.external.authentication` not found

- [ ] **Step 3: Create the external app package**

Create `backend/apps/external/__init__.py` (empty file).

- [ ] **Step 4: Implement APIKeyAuthentication**

Create `backend/apps/external/authentication.py`:

```python
from rest_framework.authentication import BaseAuthentication
from apps.settings.models import ExternalAPIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None

        key = auth_header[len(self.keyword) + 1:]
        try:
            api_key = ExternalAPIKey.objects.select_related(
                "default_assignee", "project"
            ).get(key=key, is_active=True)
        except ExternalAPIKey.DoesNotExist:
            return None

        request.api_key = api_key
        return (api_key.default_assignee, api_key)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestAPIKeyAuthentication -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/external/
git commit -m "feat(external): add APIKeyAuthentication class"
```

---

### Task 4: External Serializers

**Files:**
- Create: `backend/apps/external/serializers.py`
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Write failing tests for serializer validation and field mapping**

Append to `backend/tests/test_external_api.py`:

```python
@pytest.mark.django_db
class TestExternalIssueCreateSerializer:
    def test_valid_full_payload(self, site_settings):
        from apps.external.serializers import ExternalIssueCreateSerializer
        data = {
            "title": "测试问题",
            "type": "bug",
            "priority": "P1",
            "description": "详细描述",
            "module": "case_management",
            "source_feedback_id": "FB001",
            "reporter": {"tenant_name": "Test Corp", "user_name": "张三"},
            "context": {"page_url": "/test", "browser": "Chrome"},
            "attachments": [{"type": "screenshot", "url": "https://example.com/img.png"}],
        }
        serializer = ExternalIssueCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_minimal_payload(self, site_settings):
        from apps.external.serializers import ExternalIssueCreateSerializer
        data = {"title": "最简问题"}
        serializer = ExternalIssueCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_type_to_label_mapping(self, site_settings):
        from apps.external.serializers import ExternalIssueCreateSerializer
        for type_val, expected_label in [
            ("bug", "Bug"), ("BUG", "Bug"),
            ("feature", "需求"), ("功能建议", "需求"),
            ("improvement", "优化"), ("体验改进", "优化"),
        ]:
            data = {"title": "测试", "type": type_val}
            serializer = ExternalIssueCreateSerializer(data=data)
            assert serializer.is_valid(), serializer.errors
            assert expected_label in serializer.validated_data["_labels"]

    def test_module_appended_to_labels(self, site_settings):
        from apps.external.serializers import ExternalIssueCreateSerializer
        data = {"title": "测试", "type": "bug", "module": "case_management"}
        serializer = ExternalIssueCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert "Bug" in serializer.validated_data["_labels"]
        assert "case_management" in serializer.validated_data["_labels"]

    def test_default_priority(self, site_settings):
        from apps.external.serializers import ExternalIssueCreateSerializer
        data = {"title": "测试"}
        serializer = ExternalIssueCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data.get("priority", "P2") == "P2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestExternalIssueCreateSerializer -v`
Expected: FAIL — `apps.external.serializers` not found

- [ ] **Step 3: Implement serializers**

Create `backend/apps/external/serializers.py`:

```python
from rest_framework import serializers

TYPE_TO_LABEL = {
    "bug": "Bug",
    "BUG": "Bug",
    "feature": "需求",
    "功能建议": "需求",
    "improvement": "优化",
    "体验改进": "优化",
}


class ExternalIssueCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    type = serializers.CharField(required=False, default="")
    priority = serializers.CharField(required=False, default="P2")
    description = serializers.CharField(required=False, default="")
    module = serializers.CharField(required=False, default="")
    source_feedback_id = serializers.CharField(required=False, default="")
    reporter = serializers.DictField(required=False, default=dict)
    context = serializers.DictField(required=False, default=dict)
    attachments = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )

    def validate_priority(self, value):
        if value not in ("P0", "P1", "P2", "P3"):
            return "P2"
        return value

    def validate(self, data):
        labels = []
        type_val = data.pop("type", "")
        if type_val:
            mapped = TYPE_TO_LABEL.get(type_val, type_val)
            labels.append(mapped)
        module = data.pop("module", "")
        if module:
            labels.append(module)
        data["_labels"] = labels
        return data


class ExternalIssueResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    issue_number = serializers.SerializerMethodField()
    title = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    assignee = serializers.SerializerMethodField()
    labels = serializers.JSONField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField()
    source_feedback_id = serializers.SerializerMethodField()

    def get_issue_number(self, obj):
        return f"ISS-{obj.id:03d}"

    def get_assignee(self, obj):
        if obj.assignee:
            return obj.assignee.name or obj.assignee.username
        return None

    def get_source_feedback_id(self, obj):
        if obj.source_meta and isinstance(obj.source_meta, dict):
            return obj.source_meta.get("feedback_id")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestExternalIssueCreateSerializer -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/external/serializers.py
git commit -m "feat(external): add serializers with type-to-label mapping"
```

---

### Task 5: External API Views + URL Routing

**Files:**
- Create: `backend/apps/external/views.py`
- Create: `backend/apps/external/urls.py`
- Modify: `backend/apps/urls.py`
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Write failing tests for create issue endpoint**

Append to `backend/tests/test_external_api.py`:

```python
@pytest.mark.django_db
class TestExternalCreateIssue:
    def test_create_issue_full_payload(self, external_client, api_key_obj, site_settings):
        data = {
            "title": "案件导入页面上传Excel后无响应",
            "type": "bug",
            "priority": "P1",
            "description": "上传5MB的Excel文件后页面卡住不动",
            "module": "case_management",
            "source_feedback_id": "FB202604040001",
            "reporter": {
                "tenant_id": "T001", "tenant_name": "XX催收公司",
                "user_id": "U001", "user_name": "张三", "contact": "13800138000",
            },
            "context": {"page_url": "/case/import", "browser": "Chrome 120.0"},
            "attachments": [{"type": "screenshot", "url": "https://cdn.example.com/img.png"}],
        }
        resp = external_client.post("/api/external/issues/", data, format="json")
        assert resp.status_code == 201
        assert resp.data["title"] == "案件导入页面上传Excel后无响应"
        assert resp.data["status"] == "待处理"
        assert resp.data["priority"] == "P1"
        assert "issue_number" in resp.data

        # Verify the issue was created correctly
        from apps.issues.models import Issue
        issue = Issue.objects.get(pk=resp.data["id"])
        assert issue.source == "agent_platform"
        assert issue.project == api_key_obj.project
        assert issue.assignee == api_key_obj.default_assignee
        assert issue.reporter == api_key_obj.default_assignee
        assert issue.source_meta["feedback_id"] == "FB202604040001"
        assert issue.source_meta["reporter"]["user_name"] == "张三"
        assert "Bug" in issue.labels
        assert "case_management" in issue.labels

    def test_create_issue_minimal_payload(self, external_client, api_key_obj, site_settings):
        data = {"title": "最简问题"}
        resp = external_client.post("/api/external/issues/", data, format="json")
        assert resp.status_code == 201
        assert resp.data["status"] == "待处理"
        assert resp.data["priority"] == "P2"

    def test_duplicate_feedback_id_returns_409(self, external_client, api_key_obj, site_settings):
        data = {"title": "问题一", "source_feedback_id": "FB_DUP_001"}
        resp1 = external_client.post("/api/external/issues/", data, format="json")
        assert resp1.status_code == 201

        data2 = {"title": "问题二", "source_feedback_id": "FB_DUP_001"}
        resp2 = external_client.post("/api/external/issues/", data2, format="json")
        assert resp2.status_code == 409
        assert resp2.data["existing_issue_id"] == resp1.data["id"]

    def test_unauthenticated_returns_401(self, api_client, site_settings):
        resp = api_client.post("/api/external/issues/", {"title": "test"}, format="json")
        assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestExternalCreateIssue -v`
Expected: FAIL — URL not found (404)

- [ ] **Step 3: Implement views**

Create `backend/apps/external/views.py`:

```python
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from apps.issues.models import Issue, Activity
from .authentication import APIKeyAuthentication
from .serializers import ExternalIssueCreateSerializer, ExternalIssueResponseSerializer


class ExternalPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ExternalIssueListCreateView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        if not hasattr(request, "api_key") or request.api_key is None:
            return Response(
                {"detail": "认证失败"}, status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = ExternalIssueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Duplicate check
        feedback_id = data.get("source_feedback_id", "")
        if feedback_id:
            existing = Issue.objects.filter(
                source="agent_platform",
                source_meta__feedback_id=feedback_id,
            ).first()
            if existing:
                return Response(
                    {"detail": "反馈已存在", "existing_issue_id": existing.pk},
                    status=status.HTTP_409_CONFLICT,
                )

        # Build source_meta
        source_meta = {}
        if feedback_id:
            source_meta["feedback_id"] = feedback_id
        if data.get("reporter"):
            source_meta["reporter"] = data["reporter"]
        if data.get("context"):
            source_meta["context"] = data["context"]
        if data.get("attachments"):
            source_meta["attachments"] = data["attachments"]

        issue = Issue.objects.create(
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", "P2"),
            labels=data.get("_labels", []),
            status="待处理",
            source="agent_platform",
            source_meta=source_meta or None,
            project=request.api_key.project,
            assignee=request.api_key.default_assignee,
            reporter=request.api_key.default_assignee,
        )

        Activity.objects.create(
            user=request.api_key.default_assignee,
            issue=issue,
            action="created",
            detail="通过外部 API 创建",
        )

        response_serializer = ExternalIssueResponseSerializer(issue)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        if not hasattr(request, "api_key") or request.api_key is None:
            return Response(
                {"detail": "认证失败"}, status=status.HTTP_401_UNAUTHORIZED
            )

        qs = Issue.objects.select_related("assignee").filter(
            source="agent_platform",
            project=request.api_key.project,
        )

        # Filters
        feedback_id = request.query_params.get("feedback_id")
        if feedback_id:
            qs = qs.filter(source_meta__feedback_id=feedback_id)
        issue_status = request.query_params.get("status")
        if issue_status:
            qs = qs.filter(status=issue_status)
        priority = request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        paginator = ExternalPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ExternalIssueResponseSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ExternalIssueDetailView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, pk):
        if not hasattr(request, "api_key") or request.api_key is None:
            return Response(
                {"detail": "认证失败"}, status=status.HTTP_401_UNAUTHORIZED
            )

        issue = Issue.objects.select_related("assignee").filter(
            pk=pk,
            source="agent_platform",
            project=request.api_key.project,
        ).first()

        if not issue:
            return Response(
                {"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExternalIssueResponseSerializer(issue)
        return Response(serializer.data)
```

- [ ] **Step 4: Create URL routing**

Create `backend/apps/external/urls.py`:

```python
from django.urls import path
from .views import ExternalIssueListCreateView, ExternalIssueDetailView

urlpatterns = [
    path("issues/", ExternalIssueListCreateView.as_view(), name="external-issue-list"),
    path("issues/<int:pk>/", ExternalIssueDetailView.as_view(), name="external-issue-detail"),
]
```

- [ ] **Step 5: Mount external URLs**

In `backend/apps/urls.py`, add to the `urlpatterns` list:

```python
    path("external/", include("apps.external.urls")),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestExternalCreateIssue -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/external/ backend/apps/urls.py
git commit -m "feat(external): add issue create/list/detail API endpoints"
```

---

### Task 6: Query and List Endpoint Tests

**Files:**
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Write tests for query and list endpoints**

Append to `backend/tests/test_external_api.py`:

```python
@pytest.mark.django_db
class TestExternalQueryIssue:
    def test_get_issue_by_id(self, external_client, api_key_obj, site_settings):
        issue = IssueFactory(
            source="agent_platform",
            source_meta={"feedback_id": "FB001"},
            project=api_key_obj.project,
        )
        resp = external_client.get(f"/api/external/issues/{issue.pk}/")
        assert resp.status_code == 200
        assert resp.data["id"] == issue.pk
        assert resp.data["source_feedback_id"] == "FB001"
        assert "issue_number" in resp.data

    def test_get_issue_wrong_project_returns_404(self, external_client, site_settings):
        issue = IssueFactory(source="agent_platform")  # different project
        resp = external_client.get(f"/api/external/issues/{issue.pk}/")
        assert resp.status_code == 404

    def test_get_non_external_issue_returns_404(self, external_client, api_key_obj, site_settings):
        issue = IssueFactory(project=api_key_obj.project)  # source is None
        resp = external_client.get(f"/api/external/issues/{issue.pk}/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestExternalListIssues:
    def test_list_issues_scoped_to_project(self, external_client, api_key_obj, site_settings):
        IssueFactory(source="agent_platform", project=api_key_obj.project)
        IssueFactory(source="agent_platform", project=api_key_obj.project)
        IssueFactory(source="agent_platform")  # different project
        resp = external_client.get("/api/external/issues/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_filter_by_feedback_id(self, external_client, api_key_obj, site_settings):
        IssueFactory(
            source="agent_platform",
            source_meta={"feedback_id": "FB_FIND_ME"},
            project=api_key_obj.project,
        )
        IssueFactory(
            source="agent_platform",
            source_meta={"feedback_id": "FB_OTHER"},
            project=api_key_obj.project,
        )
        resp = external_client.get("/api/external/issues/?feedback_id=FB_FIND_ME")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_filter_by_status(self, external_client, api_key_obj, site_settings):
        IssueFactory(source="agent_platform", project=api_key_obj.project, status="待处理")
        IssueFactory(source="agent_platform", project=api_key_obj.project, status="进行中")
        resp = external_client.get("/api/external/issues/?status=待处理")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_filter_by_priority(self, external_client, api_key_obj, site_settings):
        IssueFactory(source="agent_platform", project=api_key_obj.project, priority="P0")
        IssueFactory(source="agent_platform", project=api_key_obj.project, priority="P2")
        resp = external_client.get("/api/external/issues/?priority=P0")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_pagination(self, external_client, api_key_obj, site_settings):
        for _ in range(25):
            IssueFactory(source="agent_platform", project=api_key_obj.project)
        resp = external_client.get("/api/external/issues/?page_size=10")
        assert resp.status_code == 200
        assert resp.data["count"] == 25
        assert len(resp.data["results"]) == 10
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_external_api.py::TestExternalQueryIssue tests/test_external_api.py::TestExternalListIssues -v`
Expected: All 8 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_external_api.py
git commit -m "test(external): add query and list endpoint tests"
```

---

### Task 7: Frontend — Issue Detail Source Metadata Section

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Add "外部来源" collapsible section to issue detail**

In `frontend/app/pages/app/issues/[id].vue`, find the sidebar section (the `<div class="space-y-4">` after `<!-- Sidebar -->`). Add the following as the last card in the sidebar, before the closing `</div>` of the sidebar column:

```vue
        <!-- 外部来源 -->
        <div v-if="issue.source" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
          <button class="flex items-center justify-between w-full" @click="showSourceMeta = !showSourceMeta">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">外部来源</h3>
            <UIcon :name="showSourceMeta ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'" class="w-4 h-4 text-gray-400" />
          </button>
          <div v-if="showSourceMeta && issue.source_meta" class="space-y-2 text-sm">
            <div v-if="issue.source" class="flex justify-between">
              <span class="text-gray-500 dark:text-gray-400">来源平台</span>
              <span class="text-gray-900 dark:text-gray-100">{{ issue.source }}</span>
            </div>
            <div v-if="issue.source_meta.feedback_id" class="flex justify-between">
              <span class="text-gray-500 dark:text-gray-400">反馈编号</span>
              <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.feedback_id }}</span>
            </div>
            <template v-if="issue.source_meta.reporter">
              <div class="border-t border-gray-100 dark:border-gray-800 pt-2 mt-2">
                <span class="text-xs font-medium text-gray-500 dark:text-gray-400">报告人信息</span>
              </div>
              <div v-if="issue.source_meta.reporter.user_name" class="flex justify-between">
                <span class="text-gray-500 dark:text-gray-400">姓名</span>
                <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.reporter.user_name }}</span>
              </div>
              <div v-if="issue.source_meta.reporter.tenant_name" class="flex justify-between">
                <span class="text-gray-500 dark:text-gray-400">租户</span>
                <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.reporter.tenant_name }}</span>
              </div>
              <div v-if="issue.source_meta.reporter.contact" class="flex justify-between">
                <span class="text-gray-500 dark:text-gray-400">联系方式</span>
                <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.reporter.contact }}</span>
              </div>
            </template>
            <template v-if="issue.source_meta.context">
              <div class="border-t border-gray-100 dark:border-gray-800 pt-2 mt-2">
                <span class="text-xs font-medium text-gray-500 dark:text-gray-400">上下文信息</span>
              </div>
              <div v-if="issue.source_meta.context.page_url" class="flex justify-between">
                <span class="text-gray-500 dark:text-gray-400">页面</span>
                <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.context.page_url }}</span>
              </div>
              <div v-if="issue.source_meta.context.browser" class="flex justify-between">
                <span class="text-gray-500 dark:text-gray-400">浏览器</span>
                <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.context.browser }}</span>
              </div>
              <div v-if="issue.source_meta.context.os" class="flex justify-between">
                <span class="text-gray-500 dark:text-gray-400">操作系统</span>
                <span class="text-gray-900 dark:text-gray-100">{{ issue.source_meta.context.os }}</span>
              </div>
            </template>
            <template v-if="issue.source_meta.attachments?.length">
              <div class="border-t border-gray-100 dark:border-gray-800 pt-2 mt-2">
                <span class="text-xs font-medium text-gray-500 dark:text-gray-400">外部附件</span>
              </div>
              <div v-for="(att, idx) in issue.source_meta.attachments" :key="idx">
                <a :href="att.url" target="_blank" class="text-primary-500 hover:underline text-xs">
                  {{ att.type || '附件' }} {{ idx + 1 }}
                </a>
              </div>
            </template>
          </div>
        </div>
```

- [ ] **Step 2: Add `showSourceMeta` ref to the script section**

In the `<script setup>` section, find where the reactive refs are declared and add:

```typescript
const showSourceMeta = ref(true)
```

- [ ] **Step 3: Ensure `source` and `source_meta` are included in the API response**

In `backend/apps/issues/serializers.py`, add `"source"` and `"source_meta"` to `IssueDetailSerializer.Meta.fields`:

```python
class IssueDetailSerializer(IssueListSerializer):
    github_issues = GitHubIssueBriefSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta(IssueListSerializer.Meta):
        fields = IssueListSerializer.Meta.fields + [
            "description", "estimated_completion",
            "actual_hours", "resolved_at", "github_issues", "attachments",
            "source", "source_meta",
        ]
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/issues/\[id\].vue backend/apps/issues/serializers.py
git commit -m "feat(frontend): add external source metadata section on issue detail"
```

---

### Task 8: Frontend — "外部" Badge on Issue Card and List

**Files:**
- Modify: `frontend/app/components/IssueCard.vue`
- Modify: `backend/apps/issues/serializers.py`

- [ ] **Step 1: Add `source` to IssueListSerializer**

In `backend/apps/issues/serializers.py`, add `"source"` to `IssueListSerializer.Meta.fields`:

```python
    class Meta:
        model = Issue
        fields = [
            "id", "project", "repo", "title", "priority",
            "status", "labels", "reporter", "reporter_name",
            "assignee", "assignee_name", "helpers", "helpers_names", "remark", "cause", "solution",
            "ai_cause", "ai_solution",
            "resolution_hours", "created_at", "updated_at", "github_issues",
            "estimated_completion", "source",
        ]
```

- [ ] **Step 2: Add "外部" badge to IssueCard.vue**

Replace the full content of `frontend/app/components/IssueCard.vue`:

```vue
<template>
  <NuxtLink
    :to="`/app/issues/${issue.id}`"
    class="block bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border border-white/85 dark:border-gray-700/50 rounded-xl p-3 active:scale-[0.98] transition-transform"
  >
    <div class="flex items-start justify-between gap-2">
      <p class="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2 flex-1">
        {{ issue.title }}
      </p>
      <div class="flex items-center gap-1 flex-shrink-0">
        <UBadge v-if="issue.source" color="info" variant="subtle" size="xs">外部</UBadge>
        <UBadge :color="priorityColor(issue.priority)" variant="subtle" size="xs">
          {{ priorityLabel(issue.priority) }}
        </UBadge>
      </div>
    </div>
    <div class="mt-2 flex items-center gap-2 text-[11px] text-gray-400 dark:text-gray-500">
      <UBadge
        :color="issue.status === '待处理' ? 'warning' : issue.status === '进行中' ? 'info' : issue.status === '已解决' ? 'success' : 'neutral'"
        variant="solid"
        size="xs"
      >
        {{ issue.status }}
      </UBadge>
      <span>{{ issue.assignee_name || '-' }}</span>
      <span v-if="issue.created_at">{{ issue.created_at.slice(5, 10) }}</span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
defineProps<{
  issue: {
    id: string | number
    title: string
    priority: string
    status: string
    assignee_name?: string
    created_at?: string
    source?: string | null
  }
}>()
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/IssueCard.vue backend/apps/issues/serializers.py
git commit -m "feat(frontend): add external badge on issue card and include source in list API"
```

---

### Task 9: Run Full Test Suite + Verify

**Files:**
- Test: `backend/tests/test_external_api.py`

- [ ] **Step 1: Run all external API tests**

Run: `cd backend && uv run pytest tests/test_external_api.py -v`
Expected: All tests PASS (approximately 22 tests)

- [ ] **Step 2: Run full backend test suite to check for regressions**

Run: `cd backend && uv run pytest -v`
Expected: All existing tests still PASS

- [ ] **Step 3: Run frontend type check**

Run: `cd frontend && npx nuxi typecheck`
Expected: No type errors

- [ ] **Step 4: Commit any fixes if needed, then final commit**

```bash
git add -A
git commit -m "test(external): verify full test suite passes with external API integration"
```
