# django-page-perms Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Django package (`django-page-perms`) that replaces hardcoded page-permission mappings with an API-driven dynamic configuration system, plus a superuser management UI in the current project.

**Architecture:** Standalone Django package in `packages/django-page-perms/` with a `PageRoute` model mapping frontend routes to Django permissions. The package provides DRF API endpoints for CRUD on routes, permissions, and groups. The current project installs it via editable install and builds a Nuxt management page consuming the APIs.

**Tech Stack:** Django 5.x, Django REST Framework, uv (package manager), Nuxt 4 (SPA), Nuxt UI

**Spec:** `docs/superpowers/specs/2026-03-21-django-page-perms-design.md`

---

## File Structure

### Package files (create all)

```
packages/django-page-perms/
├── pyproject.toml
├── README.md
├── page_perms/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                  # PageRoute model
│   ├── serializers.py             # PageRouteSerializer, PermissionSerializer, GroupSerializer
│   ├── permissions.py             # IsSuperUser permission class
│   ├── views.py                   # PageRouteViewSet, PermissionViewSet, GroupViewSet
│   ├── urls.py                    # Router registration
│   ├── admin.py                   # Django admin registration
│   ├── conf.py                    # Package settings with defaults
│   └── management/
│       └── commands/
│           └── sync_page_perms.py # Seed data sync command
```

### Test files (in host project's test directory)

```
backend/tests/
├── test_page_perms_models.py       # PageRoute model constraints
├── test_page_perms_routes_api.py   # PageRoute CRUD + permissions
├── test_page_perms_permissions_api.py  # Permission list/create/delete
├── test_page_perms_groups_api.py   # Group list/patch
├── test_page_perms_safety.py       # Lockout prevention, model perm protection
└── test_page_perms_sync.py         # sync_page_perms idempotency
```

Note: Tests live in `backend/tests/` (not the package) because they need the host project's Django settings and database.

### Host project files (modify)

```
backend/config/settings.py              # Add page_perms to INSTALLED_APPS + PAGE_PERMS config
backend/apps/urls.py                    # Add page-perms/ URL include
backend/pyproject.toml                  # Add editable dependency on django-page-perms

frontend/app/composables/usePagePerms.ts      # NEW: fetch + cache route config
frontend/app/composables/useNavigation.ts     # REWRITE: read from usePagePerms instead of hardcoded
frontend/app/middleware/auth.global.ts        # MODIFY: read routePermissions from usePagePerms
frontend/app/components/AppSidebar.vue        # MODIFY: read serviceKey from item.meta
frontend/app/pages/app/permissions.vue        # NEW: superuser management page (3 tabs)
backend/apps/users/serializers.py             # MODIFY: add is_superuser to MeSerializer
```

---

## Task 1: Package scaffold and model

**Files:**
- Create: `packages/django-page-perms/pyproject.toml`
- Create: `packages/django-page-perms/page_perms/__init__.py`
- Create: `packages/django-page-perms/page_perms/apps.py`
- Create: `packages/django-page-perms/page_perms/models.py`
- Create: `packages/django-page-perms/page_perms/admin.py`
- Create: `packages/django-page-perms/page_perms/conf.py`

- [ ] **Step 1: Create package directory structure**

```bash
mkdir -p packages/django-page-perms/page_perms/management/commands
mkdir -p packages/django-page-perms/tests
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
# packages/django-page-perms/pyproject.toml
[project]
name = "django-page-perms"
version = "0.1.0"
description = "Dynamic page-permission mapping for Django + DRF projects"
requires-python = ">=3.12"
dependencies = [
    "django>=4.2",
    "djangorestframework>=3.14",
]

[dependency-groups]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-django>=4.9,<5.0",
    "factory-boy>=3.3,<4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Create `page_perms/__init__.py`**

```python
# packages/django-page-perms/page_perms/__init__.py
# Django 5.x auto-discovers AppConfig from apps.py; no default_app_config needed.
```

- [ ] **Step 4: Create `page_perms/apps.py`**

```python
# packages/django-page-perms/page_perms/apps.py
from django.apps import AppConfig


class PagePermsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "page_perms"
    verbose_name = "Page Permissions"
```

- [ ] **Step 5: Create `page_perms/conf.py`**

Package settings with defaults. Reads from Django `settings.PAGE_PERMS`.

```python
# packages/django-page-perms/page_perms/conf.py
from django.conf import settings


def get_config():
    defaults = {
        "ROUTE_LIST_PERMISSION": "IsAuthenticated",
        "PROTECTED_PATHS": ["/app/permissions"],
        "SEED_ROUTES": [],
        "SEED_GROUPS": {},
    }
    user_config = getattr(settings, "PAGE_PERMS", {})
    return {**defaults, **user_config}
```

- [ ] **Step 6: Create `page_perms/models.py`**

```python
# packages/django-page-perms/page_perms/models.py
from django.contrib.auth.models import Permission
from django.db import models


class PageRoute(models.Model):
    path = models.CharField(max_length=255, unique=True, verbose_name="路由路径")
    label = models.CharField(max_length=100, verbose_name="显示名称")
    icon = models.CharField(max_length=100, blank=True, default="", verbose_name="图标")
    permission = models.ForeignKey(
        Permission,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_routes",
        verbose_name="所需权限",
    )
    show_in_nav = models.BooleanField(default=True, verbose_name="显示在导航栏")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    meta = models.JSONField(default=dict, blank=True, verbose_name="元数据")
    source = models.CharField(
        max_length=20, default="manual", verbose_name="来源",
        help_text="seed = sync command, manual = UI",
    )

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "页面路由"
        verbose_name_plural = "页面路由"

    def __str__(self):
        return f"{self.path} → {self.permission or '(无权限要求)'}"
```

- [ ] **Step 7: Create `page_perms/admin.py`**

```python
# packages/django-page-perms/page_perms/admin.py
from django.contrib import admin
from .models import PageRoute


@admin.register(PageRoute)
class PageRouteAdmin(admin.ModelAdmin):
    list_display = ("path", "label", "permission", "show_in_nav", "is_active", "sort_order", "source")
    list_filter = ("is_active", "show_in_nav", "source")
    search_fields = ("path", "label")
```

- [ ] **Step 8: Generate initial migration**

```bash
cd packages/django-page-perms
# Create a temporary Django settings for makemigrations
python -c "
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
# We'll generate from the host project instead
"
```

Since the package needs a Django project to generate migrations, we'll do this from the host project after installing the package in Task 2.

- [ ] **Step 9: Create empty `__init__.py` files**

```bash
touch packages/django-page-perms/page_perms/management/__init__.py
touch packages/django-page-perms/page_perms/management/commands/__init__.py
touch packages/django-page-perms/tests/__init__.py
```

- [ ] **Step 10: Commit**

```bash
git add packages/django-page-perms/
git commit -m "feat(page-perms): scaffold package with PageRoute model"
```

---

## Task 2: Install package in host project and generate migration

**Files:**
- Modify: `backend/pyproject.toml` — add editable dependency
- Modify: `backend/config/settings.py:16-33` — add to INSTALLED_APPS, add PAGE_PERMS config
- Modify: `backend/apps/urls.py:1-11` — add page-perms URL include

- [ ] **Step 1: Add editable dependency to host project**

```bash
cd backend
uv add --editable ../packages/django-page-perms
```

This updates `backend/pyproject.toml` to include the editable dependency.

- [ ] **Step 2: Add `page_perms` to INSTALLED_APPS**

In `backend/config/settings.py`, add `"page_perms"` to `INSTALLED_APPS` after the local apps:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "apps.repos",
    # Packages
    "page_perms",
]
```

- [ ] **Step 3: Add PAGE_PERMS config to settings**

Append to `backend/config/settings.py`:

```python
# Page permissions configuration
PAGE_PERMS = {
    "PROTECTED_PATHS": ["/app/permissions"],
    "SEED_ROUTES": [
        {"path": "/app/issues", "label": "问题跟踪", "icon": "i-heroicons-bug-ant", "permission": "issues.view_issue", "sort_order": 0},
        {"path": "/app/dashboard", "label": "项目概览", "icon": "i-heroicons-squares-2x2", "permission": "issues.view_dashboard", "sort_order": 1},
        {"path": "/app/projects", "label": "项目管理", "icon": "i-heroicons-folder-open", "permission": "projects.view_project", "sort_order": 2},
        {"path": "/app/repos", "label": "GitHub 仓库", "icon": "i-heroicons-code-bracket", "permission": "repos.view_repo", "sort_order": 3, "meta": {"serviceKey": "github"}},
        {"path": "/app/ai-insights", "label": "AI 洞察", "icon": "i-heroicons-cpu-chip", "permission": None, "sort_order": 4, "meta": {"serviceKey": "ai"}},
        {"path": "/app/permissions", "label": "权限管理", "icon": "i-heroicons-shield-check", "permission": None, "sort_order": 99, "meta": {"superuserOnly": True}},
    ],
    "SEED_GROUPS": {
        "管理员": {"apps": ["projects", "issues", "settings", "repos"]},  # Note: repos added (missing from old setup_groups.py)
        "开发者": {"permissions": ["view_project", "view_issue", "add_issue", "change_issue", "view_activity", "view_dashboard"]},
        "产品经理": {"inherit": "开发者", "permissions": ["add_project", "change_project", "manage_project_members"]},
        "只读成员": {"permissions_startswith": ["view_"]},
    },
}
```

- [ ] **Step 4: Add URL route**

In `backend/apps/urls.py`, add the page-perms include:

```python
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.users.auth_urls")),
    path("settings/", include("apps.settings.urls")),
    path("users/", include("apps.users.urls")),
    path("projects/", include("apps.projects.urls")),
    path("issues/", include("apps.issues.urls")),
    path("dashboard/", include("apps.issues.dashboard_urls")),
    path("repos/", include("apps.repos.urls")),
    path("page-perms/", include("page_perms.urls")),
]
```

- [ ] **Step 5: Generate and check migration**

```bash
cd backend
uv run python manage.py makemigrations page_perms
```

Move the generated migration file into the package:

```bash
# The migration is generated in the package's page_perms/migrations/ directory
# Verify it exists:
ls packages/django-page-perms/page_perms/migrations/0001_initial.py
```

- [ ] **Step 6: Apply migration**

```bash
cd backend
uv run python manage.py migrate page_perms
```

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/config/settings.py backend/apps/urls.py packages/django-page-perms/
git commit -m "feat(page-perms): install package in host project, generate migration"
```

---

## Task 3: Package permissions and serializers

**Files:**
- Create: `packages/django-page-perms/page_perms/permissions.py`
- Create: `packages/django-page-perms/page_perms/serializers.py`

- [ ] **Step 1: Create `page_perms/permissions.py`**

```python
# packages/django-page-perms/page_perms/permissions.py
from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Only allow Django superusers."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
```

- [ ] **Step 2: Create `page_perms/serializers.py`**

```python
# packages/django-page-perms/page_perms/serializers.py
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import PageRoute


def resolve_permission(perm_string):
    """Resolve 'app_label.codename' string to a Permission instance."""
    if not perm_string:
        return None
    try:
        app_label, codename = perm_string.split(".", 1)
    except ValueError:
        raise serializers.ValidationError(
            {"permission": f"Invalid format: '{perm_string}'. Expected 'app_label.codename'."}
        )
    try:
        return Permission.objects.get(
            content_type__app_label=app_label, codename=codename
        )
    except Permission.DoesNotExist:
        raise serializers.ValidationError(
            {"permission": f"Permission '{perm_string}' does not exist."}
        )


class PageRouteSerializer(serializers.ModelSerializer):
    # Accept/return permission as "app_label.codename" string, not FK integer
    permission = serializers.CharField(allow_null=True, required=False, default=None)

    class Meta:
        model = PageRoute
        fields = [
            "id", "path", "label", "icon", "permission",
            "show_in_nav", "sort_order", "is_active", "meta", "source",
        ]
        read_only_fields = ["source"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.permission:
            ct = instance.permission.content_type
            data["permission"] = f"{ct.app_label}.{instance.permission.codename}"
        else:
            data["permission"] = None
        return data

    def validate_permission(self, value):
        """Validate and resolve the permission string to a Permission instance."""
        return resolve_permission(value)

    def create(self, validated_data):
        # validate_permission already resolved the string to a Permission instance
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # validate_permission already resolved the string to a Permission instance
        return super().update(instance, validated_data)


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    source = serializers.SerializerMethodField()
    full_codename = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "app_label", "source", "full_codename"]
        read_only_fields = ["id", "codename", "name", "app_label", "source", "full_codename"]

    def get_source(self, obj):
        """Return 'model' if permission belongs to a real model, 'custom' otherwise."""
        ct = obj.content_type
        # page_perms content type means it's a custom logical permission
        if ct.app_label == "page_perms":
            return "custom"
        return "model"

    def get_full_codename(self, obj):
        return f"{obj.content_type.app_label}.{obj.codename}"


class CreatePermissionSerializer(serializers.Serializer):
    codename = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=255)

    def validate_codename(self, value):
        ct = ContentType.objects.get_for_model(PageRoute)
        if Permission.objects.filter(content_type=ct, codename=value).exists():
            raise serializers.ValidationError(f"Permission with codename '{value}' already exists.")
        return value

    def create(self, validated_data):
        ct = ContentType.objects.get_for_model(PageRoute)
        return Permission.objects.create(
            content_type=ct,
            codename=validated_data["codename"],
            name=validated_data["name"],
        )


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]
        read_only_fields = ["id", "name"]

    def get_permissions(self, obj):
        return [
            f"{p.content_type.app_label}.{p.codename}"
            for p in obj.permissions.select_related("content_type").all()
        ]


class GroupUpdateSerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.CharField())

    def update(self, instance, validated_data):
        perm_strings = validated_data["permissions"]
        perms = []
        for perm_string in perm_strings:
            try:
                app_label, codename = perm_string.split(".", 1)
            except ValueError:
                raise serializers.ValidationError(
                    {"permissions": f"Invalid format: '{perm_string}'. Expected 'app_label.codename'."}
                )
            try:
                perm = Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
                perms.append(perm)
            except Permission.DoesNotExist:
                raise serializers.ValidationError(
                    {"permissions": f"Permission '{perm_string}' does not exist."}
                )
        instance.permissions.set(perms)
        return instance
```

- [ ] **Step 3: Commit**

```bash
git add packages/django-page-perms/page_perms/permissions.py packages/django-page-perms/page_perms/serializers.py
git commit -m "feat(page-perms): add IsSuperUser permission class and serializers"
```

---

## Task 4: Package views and URL routing

**Files:**
- Create: `packages/django-page-perms/page_perms/views.py`
- Create: `packages/django-page-perms/page_perms/urls.py`

- [ ] **Step 1: Create `page_perms/views.py`**

```python
# packages/django-page-perms/page_perms/views.py
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .conf import get_config
from .models import PageRoute
from .permissions import IsSuperUser
from .serializers import (
    CreatePermissionSerializer,
    GroupSerializer,
    GroupUpdateSerializer,
    PageRouteSerializer,
    PermissionSerializer,
)


class PageRouteViewSet(viewsets.ModelViewSet):
    serializer_class = PageRouteSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action == "list":
            config = get_config()
            perm_class = config.get("ROUTE_LIST_PERMISSION", "IsAuthenticated")
            if perm_class == "IsAuthenticated":
                return [IsAuthenticated()]
            # Allow custom permission classes via dotted path if needed
            return [IsAuthenticated()]
        return [IsSuperUser()]

    def get_queryset(self):
        qs = PageRoute.objects.select_related("permission__content_type").all()
        # Non-superusers only see active routes
        if not (self.request.user and self.request.user.is_superuser):
            qs = qs.filter(is_active=True)
        elif self.request.query_params.get("all") != "true":
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        config = get_config()
        if instance.path in config["PROTECTED_PATHS"]:
            return Response(
                {"detail": f"Cannot delete protected route: {instance.path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        config = get_config()
        # Prevent deactivating protected paths
        if instance.path in config["PROTECTED_PATHS"]:
            if "is_active" in request.data and not request.data["is_active"]:
                return Response(
                    {"detail": f"Cannot deactivate protected route: {instance.path}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().partial_update(request, *args, **kwargs)


class PermissionViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUser]

    def list(self, request):
        permissions = Permission.objects.select_related("content_type").all()
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = CreatePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perm = serializer.save()
        return Response(
            PermissionSerializer(perm).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        try:
            perm = Permission.objects.select_related("content_type").get(pk=pk)
        except Permission.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Only allow deleting custom permissions (content_type = page_perms.pageroute)
        ct = ContentType.objects.get_for_model(PageRoute)
        if perm.content_type != ct:
            return Response(
                {"detail": "Cannot delete model-generated permissions."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        perm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUser]

    def list(self, request):
        groups = Group.objects.prefetch_related("permissions__content_type").all()
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        try:
            group = Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        old_perms = set(
            f"{p.content_type.app_label}.{p.codename}"
            for p in group.permissions.select_related("content_type").all()
        )

        serializer = GroupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(group, serializer.validated_data)

        new_perms = set(serializer.validated_data["permissions"])
        added = new_perms - old_perms
        removed = old_perms - new_perms

        # Audit log via Django LogEntry
        if added or removed:
            ct = ContentType.objects.get_for_model(Group)
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=ct.pk,
                object_id=str(group.pk),
                object_repr=group.name,
                action_flag=CHANGE,
                change_message=f"Permissions changed. Added: {sorted(added)}. Removed: {sorted(removed)}.",
            )

        return Response(GroupSerializer(group).data)
```

- [ ] **Step 2: Create `page_perms/urls.py`**

```python
# packages/django-page-perms/page_perms/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import GroupViewSet, PageRouteViewSet, PermissionViewSet

router = DefaultRouter()
router.register("routes", PageRouteViewSet, basename="pageroute")

urlpatterns = [
    path("", include(router.urls)),
    path("permissions/", PermissionViewSet.as_view({"get": "list", "post": "create"})),
    path("permissions/<int:pk>/", PermissionViewSet.as_view({"delete": "destroy"})),
    path("groups/", GroupViewSet.as_view({"get": "list"})),
    path("groups/<int:pk>/", GroupViewSet.as_view({"patch": "partial_update"})),
]
```

- [ ] **Step 3: Verify server starts**

```bash
cd backend
uv run python manage.py runserver --noreload &
sleep 2
curl -s http://localhost:8000/api/page-perms/routes/ | head -20
kill %1
```

Expected: 401 Unauthorized (no auth token) — confirms URL routing works.

- [ ] **Step 4: Commit**

```bash
git add packages/django-page-perms/page_perms/views.py packages/django-page-perms/page_perms/urls.py
git commit -m "feat(page-perms): add views and URL routing"
```

---

## Task 5: sync_page_perms management command

**Files:**
- Create: `packages/django-page-perms/page_perms/management/commands/sync_page_perms.py`

- [ ] **Step 1: Create the command**

```python
# packages/django-page-perms/page_perms/management/commands/sync_page_perms.py
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from page_perms.conf import get_config
from page_perms.models import PageRoute


class Command(BaseCommand):
    help = "Sync page routes and group permissions from PAGE_PERMS settings"

    def handle(self, *args, **options):
        config = get_config()
        self._sync_routes(config.get("SEED_ROUTES", []))
        self._sync_groups(config.get("SEED_GROUPS", {}))

    def _resolve_permission(self, perm_string):
        """Resolve 'app_label.codename' or just 'codename' to Permission."""
        if not perm_string:
            return None
        if "." in perm_string:
            app_label, codename = perm_string.split(".", 1)
            try:
                return Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
            except Permission.DoesNotExist:
                self.stderr.write(f"  Warning: permission '{perm_string}' not found, skipping")
                return None
        # No app_label, try codename across all apps
        perms = Permission.objects.filter(codename=perm_string)
        if perms.count() == 1:
            return perms.first()
        if perms.count() > 1:
            self.stderr.write(f"  Warning: ambiguous codename '{perm_string}', skipping")
        else:
            self.stderr.write(f"  Warning: permission '{perm_string}' not found, skipping")
        return None

    def _sync_routes(self, seed_routes):
        self.stdout.write("Syncing page routes...")
        for route_data in seed_routes:
            path = route_data["path"]
            perm_string = route_data.get("permission")
            permission = self._resolve_permission(perm_string) if perm_string else None

            defaults = {
                "label": route_data["label"],
                "icon": route_data.get("icon", ""),
                "permission": permission,
                "show_in_nav": route_data.get("show_in_nav", True),
                "sort_order": route_data.get("sort_order", 0),
                "is_active": route_data.get("is_active", True),
                "meta": route_data.get("meta", {}),
                "source": "seed",
            }

            route, created = PageRoute.objects.update_or_create(
                path=path, defaults=defaults
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {path}")

        self.stdout.write(self.style.SUCCESS(f"  Synced {len(seed_routes)} routes"))

    def _sync_groups(self, seed_groups):
        self.stdout.write("Syncing groups...")

        # First pass: resolve all group permission sets (needed for inherit)
        resolved = {}
        for group_name, config in seed_groups.items():
            perms = set()

            # apps: all permissions for listed apps
            if "apps" in config:
                perms.update(
                    Permission.objects.filter(
                        content_type__app_label__in=config["apps"]
                    )
                )

            # permissions: explicit codenames
            if "permissions" in config:
                for codename in config["permissions"]:
                    perms.update(Permission.objects.filter(codename=codename))

            # permissions_startswith: prefix match
            if "permissions_startswith" in config:
                for prefix in config["permissions_startswith"]:
                    perms.update(
                        Permission.objects.filter(codename__startswith=prefix)
                    )

            resolved[group_name] = perms

        # Second pass: handle inherit (snapshot semantics)
        for group_name, config in seed_groups.items():
            if "inherit" in config:
                parent_name = config["inherit"]
                if parent_name in resolved:
                    resolved[group_name].update(resolved[parent_name])
                else:
                    self.stderr.write(
                        f"  Warning: inherit target '{parent_name}' not found for group '{group_name}'"
                    )

        # Third pass: create/update groups
        for group_name, perms in resolved.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(perms)
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} group: {group_name} ({len(perms)} permissions)")

        self.stdout.write(self.style.SUCCESS(f"  Synced {len(seed_groups)} groups"))
```

- [ ] **Step 2: Test the command manually**

```bash
cd backend
uv run python manage.py sync_page_perms
```

Expected output: lists created/updated routes and groups.

- [ ] **Step 3: Commit**

```bash
git add packages/django-page-perms/page_perms/management/commands/sync_page_perms.py
git commit -m "feat(page-perms): add sync_page_perms management command"
```

---

## Task 6: Package tests

**Files:**
- Create: `packages/django-page-perms/tests/conftest.py`
- Create: `packages/django-page-perms/tests/factories.py`
- Create: `packages/django-page-perms/tests/test_models.py`
- Create: `packages/django-page-perms/tests/test_routes_api.py`
- Create: `packages/django-page-perms/tests/test_permissions_api.py`
- Create: `packages/django-page-perms/tests/test_groups_api.py`
- Create: `packages/django-page-perms/tests/test_safety.py`
- Create: `packages/django-page-perms/tests/test_sync_command.py`
- Create: `packages/django-page-perms/pytest.ini`

Note: Package tests live in `backend/tests/` since they need the host project's Django settings and database.

- [ ] **Step 1: Add shared `superuser_client` and `regular_client` fixtures to conftest**

In `backend/tests/conftest.py`, add these fixtures (they are used across all page-perms test files):

```python
@pytest.fixture
def superuser_client(api_client):
    user = UserFactory(is_superuser=True, is_staff=True)
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def regular_client(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client
```

- [ ] **Step 2: Create `backend/tests/test_page_perms_models.py`**

```python
# backend/tests/test_page_perms_models.py
import pytest
from django.contrib.auth.models import Permission
from django.db import IntegrityError

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestPageRouteModel:
    def test_create_route_without_permission(self):
        route = PageRoute.objects.create(
            path="/app/test", label="Test", sort_order=0
        )
        assert route.permission is None
        assert route.is_active is True
        assert route.source == "manual"

    def test_create_route_with_permission(self):
        perm = Permission.objects.filter(codename="view_issue").first()
        route = PageRoute.objects.create(
            path="/app/test", label="Test", permission=perm
        )
        assert route.permission == perm

    def test_unique_path_constraint(self):
        PageRoute.objects.create(path="/app/test", label="Test")
        with pytest.raises(IntegrityError):
            PageRoute.objects.create(path="/app/test", label="Duplicate")

    def test_ordering_by_sort_order(self):
        PageRoute.objects.create(path="/app/b", label="B", sort_order=2)
        PageRoute.objects.create(path="/app/a", label="A", sort_order=1)
        routes = list(PageRoute.objects.values_list("path", flat=True))
        assert routes == ["/app/a", "/app/b"]

    def test_permission_set_null_on_delete(self):
        perm = Permission.objects.filter(codename="view_issue").first()
        route = PageRoute.objects.create(
            path="/app/test", label="Test", permission=perm
        )
        perm.delete()
        route.refresh_from_db()
        assert route.permission is None
```

- [ ] **Step 3: Run model tests**

```bash
cd backend
uv run pytest tests/test_page_perms_models.py -v
```

Expected: all pass.

- [ ] **Step 4: Create `backend/tests/test_page_perms_routes_api.py`**

```python
# backend/tests/test_page_perms_routes_api.py
import pytest
from django.contrib.auth.models import Permission

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestPageRouteList:
    def test_authenticated_user_can_list_routes(self, regular_client):
        PageRoute.objects.create(path="/app/test", label="Test", is_active=True)
        response = regular_client.get("/api/page-perms/routes/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_unauthenticated_cannot_list(self, api_client):
        response = api_client.get("/api/page-perms/routes/")
        assert response.status_code == 401

    def test_inactive_routes_hidden_from_regular_user(self, regular_client):
        PageRoute.objects.create(path="/app/a", label="A", is_active=True)
        PageRoute.objects.create(path="/app/b", label="B", is_active=False)
        response = regular_client.get("/api/page-perms/routes/")
        assert len(response.data) == 1

    def test_superuser_sees_inactive_with_all_param(self, superuser_client):
        PageRoute.objects.create(path="/app/a", label="A", is_active=True)
        PageRoute.objects.create(path="/app/b", label="B", is_active=False)
        response = superuser_client.get("/api/page-perms/routes/?all=true")
        assert len(response.data) == 2

    def test_regular_user_all_param_ignored(self, regular_client):
        PageRoute.objects.create(path="/app/a", label="A", is_active=True)
        PageRoute.objects.create(path="/app/b", label="B", is_active=False)
        response = regular_client.get("/api/page-perms/routes/?all=true")
        assert len(response.data) == 1  # still only active routes

    def test_permission_serialized_as_string(self, regular_client):
        perm = Permission.objects.get(codename="view_issue")
        PageRoute.objects.create(path="/app/test", label="Test", permission=perm)
        response = regular_client.get("/api/page-perms/routes/")
        assert response.data[0]["permission"] == "issues.view_issue"

    def test_null_permission_serialized(self, regular_client):
        PageRoute.objects.create(path="/app/test", label="Test", permission=None)
        response = regular_client.get("/api/page-perms/routes/")
        assert response.data[0]["permission"] is None


class TestPageRouteCRUD:
    def test_superuser_can_create(self, superuser_client):
        response = superuser_client.post("/api/page-perms/routes/", {
            "path": "/app/new",
            "label": "New Page",
            "permission": "issues.view_issue",
        }, format="json")
        assert response.status_code == 201
        assert PageRoute.objects.filter(path="/app/new").exists()

    def test_regular_user_cannot_create(self, regular_client):
        response = regular_client.post("/api/page-perms/routes/", {
            "path": "/app/new", "label": "New",
        }, format="json")
        assert response.status_code == 403

    def test_invalid_permission_returns_400(self, superuser_client):
        response = superuser_client.post("/api/page-perms/routes/", {
            "path": "/app/new",
            "label": "New",
            "permission": "nonexistent.perm",
        }, format="json")
        assert response.status_code == 400

    def test_partial_update(self, superuser_client):
        route = PageRoute.objects.create(path="/app/test", label="Old", is_active=True)
        response = superuser_client.patch(
            f"/api/page-perms/routes/{route.pk}/",
            {"label": "New"},
            format="json",
        )
        assert response.status_code == 200
        route.refresh_from_db()
        assert route.label == "New"

    def test_delete(self, superuser_client):
        route = PageRoute.objects.create(path="/app/test", label="Test")
        response = superuser_client.delete(f"/api/page-perms/routes/{route.pk}/")
        assert response.status_code == 204
        assert not PageRoute.objects.filter(pk=route.pk).exists()
```

- [ ] **Step 5: Create `backend/tests/test_page_perms_permissions_api.py`**

```python
# backend/tests/test_page_perms_permissions_api.py
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestPermissionList:
    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get("/api/page-perms/permissions/")
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_regular_user_cannot_list(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/page-perms/permissions/")
        assert response.status_code == 403

    def test_permissions_have_source_field(self, superuser_client):
        response = superuser_client.get("/api/page-perms/permissions/")
        sources = {p["source"] for p in response.data}
        assert "model" in sources


class TestPermissionCreate:
    def test_create_custom_permission(self, superuser_client):
        response = superuser_client.post("/api/page-perms/permissions/", {
            "codename": "view_analytics",
            "name": "Can view analytics",
        }, format="json")
        assert response.status_code == 201
        assert response.data["source"] == "custom"
        assert response.data["app_label"] == "page_perms"

    def test_duplicate_codename_returns_400(self, superuser_client):
        ct = ContentType.objects.get_for_model(PageRoute)
        Permission.objects.create(content_type=ct, codename="existing", name="Existing")
        response = superuser_client.post("/api/page-perms/permissions/", {
            "codename": "existing",
            "name": "Duplicate",
        }, format="json")
        assert response.status_code == 400


class TestPermissionDelete:
    def test_delete_custom_permission(self, superuser_client):
        ct = ContentType.objects.get_for_model(PageRoute)
        perm = Permission.objects.create(content_type=ct, codename="temp", name="Temp")
        response = superuser_client.delete(f"/api/page-perms/permissions/{perm.pk}/")
        assert response.status_code == 204

    def test_cannot_delete_model_permission(self, superuser_client):
        perm = Permission.objects.get(codename="view_issue")
        response = superuser_client.delete(f"/api/page-perms/permissions/{perm.pk}/")
        assert response.status_code == 400
        assert "model-generated" in response.data["detail"]
```

- [ ] **Step 6: Create `backend/tests/test_page_perms_groups_api.py`**

```python
# backend/tests/test_page_perms_groups_api.py
import pytest
from django.contrib.auth.models import Group, Permission

pytestmark = pytest.mark.django_db


class TestGroupList:
    def test_superuser_can_list(self, superuser_client):
        Group.objects.create(name="TestGroup")
        response = superuser_client.get("/api/page-perms/groups/")
        assert response.status_code == 200
        assert any(g["name"] == "TestGroup" for g in response.data)

    def test_regular_user_cannot_list(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/page-perms/groups/")
        assert response.status_code == 403


class TestGroupUpdate:
    def test_update_group_permissions(self, superuser_client):
        group = Group.objects.create(name="TestGroup")
        response = superuser_client.patch(
            f"/api/page-perms/groups/{group.pk}/",
            {"permissions": ["issues.view_issue", "projects.view_project"]},
            format="json",
        )
        assert response.status_code == 200
        assert len(response.data["permissions"]) == 2

    def test_invalid_permission_returns_400(self, superuser_client):
        group = Group.objects.create(name="TestGroup")
        response = superuser_client.patch(
            f"/api/page-perms/groups/{group.pk}/",
            {"permissions": ["nonexistent.perm"]},
            format="json",
        )
        assert response.status_code == 400

    def test_audit_log_created(self, superuser_client):
        from django.contrib.admin.models import LogEntry
        group = Group.objects.create(name="TestGroup")
        superuser_client.patch(
            f"/api/page-perms/groups/{group.pk}/",
            {"permissions": ["issues.view_issue"]},
            format="json",
        )
        assert LogEntry.objects.filter(object_repr="TestGroup").exists()
```

- [ ] **Step 7: Create `backend/tests/test_page_perms_safety.py`**

```python
# backend/tests/test_page_perms_safety.py
import pytest

from page_perms.models import PageRoute
pytestmark = pytest.mark.django_db


class TestLockoutProtection:
    def test_cannot_delete_protected_route(self, superuser_client):
        route = PageRoute.objects.create(
            path="/app/permissions", label="权限管理"
        )
        response = superuser_client.delete(f"/api/page-perms/routes/{route.pk}/")
        assert response.status_code == 400
        assert "protected" in response.data["detail"].lower()

    def test_cannot_deactivate_protected_route(self, superuser_client):
        route = PageRoute.objects.create(
            path="/app/permissions", label="权限管理", is_active=True
        )
        response = superuser_client.patch(
            f"/api/page-perms/routes/{route.pk}/",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == 400

    def test_can_update_other_fields_on_protected_route(self, superuser_client):
        route = PageRoute.objects.create(
            path="/app/permissions", label="权限管理"
        )
        response = superuser_client.patch(
            f"/api/page-perms/routes/{route.pk}/",
            {"label": "Permission Management"},
            format="json",
        )
        assert response.status_code == 200
```

- [ ] **Step 8: Create `backend/tests/test_page_perms_sync.py`**

```python
# backend/tests/test_page_perms_sync.py
import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestSyncPagePerms:
    def test_creates_routes_from_seed(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/test", "label": "Test", "sort_order": 0},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        assert PageRoute.objects.filter(path="/app/test", source="seed").exists()

    def test_idempotent_routes(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/test", "label": "Test", "sort_order": 0},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        call_command("sync_page_perms")
        assert PageRoute.objects.filter(path="/app/test").count() == 1

    def test_does_not_touch_manual_routes(self, settings):
        PageRoute.objects.create(path="/app/custom", label="Custom", source="manual")
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/test", "label": "Test", "sort_order": 0},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        assert PageRoute.objects.filter(path="/app/custom", source="manual").exists()

    def test_creates_groups(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [],
            "SEED_GROUPS": {
                "TestGroup": {"permissions_startswith": ["view_"]},
            },
        }
        call_command("sync_page_perms")
        group = Group.objects.get(name="TestGroup")
        assert group.permissions.count() > 0

    def test_inherit_snapshot_semantics(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [],
            "SEED_GROUPS": {
                "Base": {"permissions": ["view_issue"]},
                "Extended": {"inherit": "Base", "permissions": ["add_issue"]},
            },
        }
        call_command("sync_page_perms")
        extended = Group.objects.get(name="Extended")
        codenames = set(extended.permissions.values_list("codename", flat=True))
        assert "view_issue" in codenames
        assert "add_issue" in codenames
```

- [ ] **Step 9: Run all package tests**

```bash
cd backend
uv run pytest tests/test_page_perms_*.py -v
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add backend/tests/test_page_perms_*.py
git commit -m "test(page-perms): add comprehensive tests for models, API, safety, sync"
```

---

## Task 7: Frontend `usePagePerms` composable

**Files:**
- Create: `frontend/app/composables/usePagePerms.ts`

- [ ] **Step 1: Create `usePagePerms.ts`**

```typescript
// frontend/app/composables/usePagePerms.ts

export interface PageRouteConfig {
  id: number
  path: string
  label: string
  icon: string
  permission: string | null
  show_in_nav: boolean
  sort_order: number
  is_active: boolean
  meta: Record<string, any>
}

export function usePagePerms() {
  const routes = useState<PageRouteConfig[]>('page_routes', () => [])
  const loaded = useState<boolean>('page_routes_loaded', () => false)
  const error = useState<string | null>('page_routes_error', () => null)
  const { api } = useApi()

  async function fetchRoutes() {
    try {
      routes.value = await api<PageRouteConfig[]>('/api/page-perms/routes/')
      loaded.value = true
      error.value = null
    } catch (e: any) {
      error.value = '无法加载页面配置，请刷新重试'
      console.error('Failed to fetch page routes:', e)
    }
  }

  /**
   * Build route permission map for auth middleware.
   * Returns Record<path, permission_string>.
   */
  const routePermissions = computed(() => {
    const map: Record<string, string> = {}
    for (const route of routes.value) {
      if (route.permission) {
        map[route.path] = route.permission
      }
    }
    return map
  })

  return { routes, loaded, error, fetchRoutes, routePermissions }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/composables/usePagePerms.ts
git commit -m "feat(frontend): add usePagePerms composable"
```

---

## Task 8: Rewrite `useNavigation.ts` to use `usePagePerms`

**Files:**
- Modify: `frontend/app/composables/useNavigation.ts` (full rewrite)

- [ ] **Step 1: Rewrite `useNavigation.ts`**

Replace the entire file:

```typescript
// frontend/app/composables/useNavigation.ts

export interface NavItem {
  label: string
  icon: string
  to?: string
  permission?: string
  meta?: Record<string, any>
}

export const useNavigation = () => {
  const { can, user } = useAuth()
  const { routes, loaded } = usePagePerms()

  const navItems = computed<NavItem[]>(() => {
    if (!loaded.value) return []
    return routes.value
      .filter(r => r.show_in_nav && r.is_active)
      .map(r => ({
        label: r.label,
        icon: r.icon,
        to: r.path,
        permission: r.permission ?? undefined,
        meta: r.meta,
      }))
  })

  const filteredNavItems = computed(() => {
    if (!user.value) return []
    return navItems.value.filter(item => {
      // Superuser-only pages
      if (item.meta?.superuserOnly && !user.value?.is_superuser) return false
      // Permission check
      if (item.permission && !can(item.permission)) return false
      return true
    })
  })

  const route = useRoute()
  const currentPath = computed(() => route.path)

  const breadcrumbs = computed(() => {
    const path = route.path
    const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/dashboard' }]

    // First-level: match from route config
    for (const item of navItems.value) {
      if (item.to === path) {
        crumbs.push({ label: item.label })
        return crumbs
      }
    }

    // Sub-pages: find parent route and add detail crumb
    for (const item of navItems.value) {
      if (item.to && path.startsWith(item.to + '/')) {
        crumbs.push({ label: item.label, to: item.to })
        crumbs.push({ label: '详情' })
        return crumbs
      }
    }

    return crumbs
  })

  return { navItems, filteredNavItems, currentPath, breadcrumbs }
}
```

Note: The `AuthUser` interface in `useAuth.ts` needs `is_superuser` added. This will be done in the next task.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/composables/useNavigation.ts
git commit -m "refactor(frontend): rewrite useNavigation to use API-driven routes"
```

---

## Task 9: Update `useAuth.ts` and `auth.global.ts`

**Files:**
- Modify: `frontend/app/composables/useAuth.ts:1-9` — add `is_superuser` to AuthUser
- Modify: `frontend/app/middleware/auth.global.ts` — use `usePagePerms` for route permissions

- [ ] **Step 1: Add `is_superuser` to AuthUser interface**

In `frontend/app/composables/useAuth.ts`, update the interface:

```typescript
interface AuthUser {
  id: string
  name: string
  email: string
  avatar: string
  groups: string[]
  permissions: string[]
  settings: Record<string, any>
  is_superuser: boolean
}
```

- [ ] **Step 2: Update the backend `MeSerializer` to include `is_superuser`**

In `backend/apps/users/serializers.py:19`, change:

```python
fields = ["id", "username", "name", "email", "github_id", "avatar", "groups", "permissions", "settings"]
read_only_fields = ["id", "username", "groups", "permissions"]
```

To:

```python
fields = ["id", "username", "name", "email", "github_id", "avatar", "groups", "permissions", "settings", "is_superuser"]
read_only_fields = ["id", "username", "groups", "permissions", "is_superuser"]
```

This is critical — without `is_superuser` in the API response, the frontend cannot gate the permissions management page or filter `superuserOnly` nav items.

- [ ] **Step 3: Rewrite `auth.global.ts`**

Replace the entire file:

```typescript
// frontend/app/middleware/auth.global.ts

export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/' || to.path === '/login') return
  if (to.path === '/app/forbidden') return

  const { getToken } = useApi()
  if (!getToken()) {
    return navigateTo('/')
  }

  const { user, fetchMe, can } = useAuth()
  const { loaded, fetchRoutes, routePermissions, error } = usePagePerms()

  // Ensure user data is loaded
  if (!user.value) {
    await fetchMe()
  }

  if (!user.value) {
    return navigateTo('/')
  }

  // Ensure route config is loaded
  if (!loaded.value) {
    await fetchRoutes()
  }

  // If route config failed to load, block access to protected pages
  if (error.value && to.path.startsWith('/app/')) {
    return navigateTo('/app/forbidden')
  }

  // Check route permission
  const perms = routePermissions.value
  for (const [prefix, perm] of Object.entries(perms)) {
    if (to.path === prefix || to.path.startsWith(prefix + '/')) {
      if (!can(perm)) {
        return navigateTo('/app/forbidden')
      }
      break
    }
  }
})
```

- [ ] **Step 4: Update `AppSidebar.vue` for `meta.serviceKey`**

The rewritten `NavItem` interface puts `serviceKey` in `meta` instead of as a top-level property. In `frontend/app/components/AppSidebar.vue:31-33`, change:

```vue
<ServiceStatusDot
  v-if="item.serviceKey"
  :online="isOnline(item.serviceKey)"
/>
```

To:

```vue
<ServiceStatusDot
  v-if="item.meta?.serviceKey"
  :online="isOnline(item.meta.serviceKey)"
/>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/composables/useAuth.ts frontend/app/middleware/auth.global.ts frontend/app/components/AppSidebar.vue backend/apps/users/serializers.py
git commit -m "refactor(frontend): switch auth middleware to API-driven route permissions"
```

---

## Task 10: Frontend permissions management page

**Files:**
- Create: `frontend/app/pages/app/permissions.vue`

- [ ] **Step 1: Create the management page**

This is a single page with three tabs: 页面路由映射, 组-权限分配, 权限列表. Since this is a large component, create it with all three tabs. The page is only visible to superusers (controlled by the meta.superuserOnly in the route config and a client-side guard).

```vue
<!-- frontend/app/pages/app/permissions.vue -->
<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">权限管理</h1>
    </div>

    <UTabs :items="tabs" v-model="activeTab">
      <template #routes>
        <div class="space-y-4 p-4">
          <div class="flex justify-end">
            <UButton icon="i-heroicons-plus" label="添加路由" @click="showAddRoute = true" />
          </div>
          <UTable :rows="allRoutes" :columns="routeColumns">
            <template #cell-permission="{ row }">
              <UBadge v-if="row.permission" color="blue" variant="subtle">{{ row.permission }}</UBadge>
              <span v-else class="text-gray-400">无</span>
            </template>
            <template #cell-is_active="{ row }">
              <UToggle :model-value="row.is_active" @update:model-value="toggleRouteActive(row, $event)" />
            </template>
            <template #cell-show_in_nav="{ row }">
              <UToggle :model-value="row.show_in_nav" @update:model-value="toggleRouteNav(row, $event)" />
            </template>
            <template #cell-actions="{ row }">
              <UButton
                icon="i-heroicons-trash"
                color="red"
                variant="ghost"
                size="xs"
                @click="deleteRoute(row)"
              />
            </template>
          </UTable>
        </div>
      </template>

      <template #groups>
        <div class="space-y-4 p-4">
          <div v-for="group in groups" :key="group.id" class="border rounded-lg p-4">
            <h3 class="font-medium mb-2">{{ group.name }}</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
              <label
                v-for="perm in allPermissions"
                :key="perm.id"
                class="flex items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="group.permissions.includes(perm.full_codename)"
                  @change="toggleGroupPerm(group, perm.full_codename, $event)"
                />
                <span>{{ perm.full_codename }}</span>
              </label>
            </div>
            <UButton
              class="mt-2"
              size="xs"
              label="保存"
              @click="saveGroup(group)"
            />
          </div>
        </div>
      </template>

      <template #permissions>
        <div class="space-y-4 p-4">
          <div class="flex justify-end">
            <UButton icon="i-heroicons-plus" label="创建自定义权限" @click="showAddPerm = true" />
          </div>
          <UTable :rows="allPermissions" :columns="permColumns">
            <template #cell-source="{ row }">
              <UBadge :color="row.source === 'model' ? 'gray' : 'green'" variant="subtle">
                {{ row.source === 'model' ? 'Model' : '自定义' }}
              </UBadge>
            </template>
            <template #cell-actions="{ row }">
              <UButton
                v-if="row.source === 'custom'"
                icon="i-heroicons-trash"
                color="red"
                variant="ghost"
                size="xs"
                @click="deletePerm(row)"
              />
            </template>
          </UTable>
        </div>
      </template>
    </UTabs>

    <!-- Add Route Modal -->
    <UModal v-model="showAddRoute">
      <UCard>
        <template #header>添加路由映射</template>
        <div class="space-y-4">
          <UFormGroup label="路径">
            <UInput v-model="newRoute.path" placeholder="/app/xxx" />
          </UFormGroup>
          <UFormGroup label="名称">
            <UInput v-model="newRoute.label" placeholder="页面名称" />
          </UFormGroup>
          <UFormGroup label="图标">
            <UInput v-model="newRoute.icon" placeholder="i-heroicons-xxx" />
          </UFormGroup>
          <UFormGroup label="权限">
            <USelectMenu
              v-model="newRoute.permission"
              :options="permOptions"
              placeholder="无需权限"
              clearable
            />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton variant="ghost" label="取消" @click="showAddRoute = false" />
            <UButton label="创建" @click="createRoute" />
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Add Permission Modal -->
    <UModal v-model="showAddPerm">
      <UCard>
        <template #header>创建自定义权限</template>
        <div class="space-y-4">
          <UFormGroup label="Codename">
            <UInput v-model="newPerm.codename" placeholder="view_xxx" />
          </UFormGroup>
          <UFormGroup label="名称">
            <UInput v-model="newPerm.name" placeholder="Can view xxx" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton variant="ghost" label="取消" @click="showAddPerm = false" />
            <UButton label="创建" @click="createPerm" />
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { user } = useAuth()

// Redirect non-superusers
if (!user.value?.is_superuser) {
  navigateTo('/app/forbidden')
}

const activeTab = ref(0)
const tabs = [
  { label: '页面路由', slot: 'routes' },
  { label: '组-权限', slot: 'groups' },
  { label: '权限列表', slot: 'permissions' },
]

// --- Routes Tab ---
const allRoutes = ref<any[]>([])
const routeColumns = [
  { key: 'path', label: '路径' },
  { key: 'label', label: '名称' },
  { key: 'icon', label: '图标' },
  { key: 'permission', label: '权限' },
  { key: 'sort_order', label: '排序' },
  { key: 'is_active', label: '启用' },
  { key: 'show_in_nav', label: '导航' },
  { key: 'actions', label: '操作' },
]

async function loadRoutes() {
  allRoutes.value = await api<any[]>('/api/page-perms/routes/?all=true')
}

const showAddRoute = ref(false)
const newRoute = ref({ path: '', label: '', icon: '', permission: null as string | null })

async function createRoute() {
  await api('/api/page-perms/routes/', {
    method: 'POST',
    body: newRoute.value,
  })
  showAddRoute.value = false
  newRoute.value = { path: '', label: '', icon: '', permission: null }
  await loadRoutes()
}

async function toggleRouteActive(row: any, value: boolean) {
  await api(`/api/page-perms/routes/${row.id}/`, {
    method: 'PATCH',
    body: { is_active: value },
  })
  await loadRoutes()
}

async function toggleRouteNav(row: any, value: boolean) {
  await api(`/api/page-perms/routes/${row.id}/`, {
    method: 'PATCH',
    body: { show_in_nav: value },
  })
  await loadRoutes()
}

async function deleteRoute(row: any) {
  if (!confirm(`确定删除路由 ${row.path}？`)) return
  await api(`/api/page-perms/routes/${row.id}/`, { method: 'DELETE' })
  await loadRoutes()
}

// --- Groups Tab ---
const groups = ref<any[]>([])

async function loadGroups() {
  groups.value = await api<any[]>('/api/page-perms/groups/')
}

function toggleGroupPerm(group: any, perm: string, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  if (checked) {
    group.permissions.push(perm)
  } else {
    group.permissions = group.permissions.filter((p: string) => p !== perm)
  }
}

async function saveGroup(group: any) {
  await api(`/api/page-perms/groups/${group.id}/`, {
    method: 'PATCH',
    body: { permissions: group.permissions },
  })
  await loadGroups()
}

// --- Permissions Tab ---
const allPermissions = ref<any[]>([])
const permColumns = [
  { key: 'full_codename', label: '完整 Codename' },
  { key: 'name', label: '名称' },
  { key: 'app_label', label: 'App' },
  { key: 'source', label: '来源' },
  { key: 'actions', label: '操作' },
]

async function loadPermissions() {
  allPermissions.value = await api<any[]>('/api/page-perms/permissions/')
}

const permOptions = computed(() =>
  allPermissions.value.map(p => p.full_codename)
)

const showAddPerm = ref(false)
const newPerm = ref({ codename: '', name: '' })

async function createPerm() {
  await api('/api/page-perms/permissions/', {
    method: 'POST',
    body: newPerm.value,
  })
  showAddPerm.value = false
  newPerm.value = { codename: '', name: '' }
  await loadPermissions()
}

async function deletePerm(row: any) {
  if (!confirm(`确定删除权限 ${row.full_codename}？`)) return
  await api(`/api/page-perms/permissions/${row.id}/`, { method: 'DELETE' })
  await loadPermissions()
}

// Load all data
onMounted(async () => {
  await Promise.all([loadRoutes(), loadGroups(), loadPermissions()])
})
</script>
```

Note: The exact Nuxt UI component API may need adjustment during implementation based on the specific version of Nuxt UI in use (v2 vs v3 have different APIs for UTabs, UTable, etc.). The implementer should check which version is installed and adapt accordingly.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/pages/app/permissions.vue
git commit -m "feat(frontend): add permissions management page with 3 tabs"
```

---

## Task 11: Remove old `setup_groups.py` and clean up

**Files:**
- Delete: `backend/apps/users/management/commands/setup_groups.py`
- Modify: `backend/tests/conftest.py:13-19` — update admin group setup if needed

- [ ] **Step 1: Verify `sync_page_perms` covers all existing group logic**

```bash
cd backend
uv run python manage.py sync_page_perms
# Verify output matches the four groups with correct permission counts
```

- [ ] **Step 2: Delete old `setup_groups.py`**

```bash
rm backend/apps/users/management/commands/setup_groups.py
```

- [ ] **Step 3: Update CLAUDE.md**

Update the command reference in `CLAUDE.md` to replace `setup_groups` with `sync_page_perms`:

Replace:
```
uv run python manage.py setup_groups       # Sync permission groups (管理员/开发者/产品经理/只读成员)
```

With:
```
uv run python manage.py sync_page_perms    # Sync page routes + permission groups from PAGE_PERMS config
```

- [ ] **Step 4: Run all tests to verify nothing broke**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: replace setup_groups with sync_page_perms, clean up"
```

---

## Task 12: Package README

**Files:**
- Create: `packages/django-page-perms/README.md`

- [ ] **Step 1: Write README**

```markdown
# django-page-perms

Dynamic page-permission mapping for Django + DRF projects. Maps frontend routes to Django permissions via a database-backed configuration, with API endpoints for runtime management.

## Installation

```bash
pip install django-page-perms
# or with uv:
uv add django-page-perms
```

## Quick Start

1. Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "page_perms",
]
```

2. Include URLs:

```python
# urls.py
path("api/page-perms/", include("page_perms.urls")),
```

3. Run migrations:

```bash
python manage.py migrate page_perms
```

4. Configure seed data in `settings.py` (see Configuration below).

5. Sync:

```bash
python manage.py sync_page_perms
```

## Configuration

```python
PAGE_PERMS = {
    # Permission class for GET /routes/ (default: all authenticated users)
    "ROUTE_LIST_PERMISSION": "IsAuthenticated",

    # Routes that cannot be deleted or deactivated via API
    "PROTECTED_PATHS": ["/app/permissions"],

    # Seed route data (synced by sync_page_perms command)
    "SEED_ROUTES": [
        {
            "path": "/app/dashboard",
            "label": "Dashboard",
            "icon": "dashboard-icon",
            "permission": "myapp.view_dashboard",  # app_label.codename format, or None
            "sort_order": 0,
            "meta": {},  # arbitrary JSON for frontend use
        },
    ],

    # Seed group-permission assignments
    "SEED_GROUPS": {
        "Admin": {"apps": ["myapp"]},                        # all perms for listed apps
        "Developer": {"permissions": ["view_item"]},          # explicit codenames
        "Manager": {"inherit": "Developer", "permissions": ["add_item"]},  # snapshot inherit
        "Viewer": {"permissions_startswith": ["view_"]},      # prefix match
    },
}
```

### SEED_GROUPS options

| Key | Description |
|-----|-------------|
| `apps` | Grant all permissions for listed Django app labels |
| `permissions` | Grant permissions by exact codename (matched across all apps) |
| `permissions_startswith` | Grant permissions where codename starts with prefix |
| `inherit` | Merge another group's seed permissions (snapshot at sync time, not live) |

All options can be combined; the final permission set is the union.

## API Endpoints

### Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/routes/` | Authenticated | List active routes. Superuser: add `?all=true` for inactive |
| POST | `/routes/` | Superuser | Create route |
| PATCH | `/routes/{id}/` | Superuser | Partial update (any subset of fields) |
| DELETE | `/routes/{id}/` | Superuser | Delete route (protected paths blocked) |

**Response format:**

```json
{
  "id": 1,
  "path": "/app/dashboard",
  "label": "Dashboard",
  "icon": "icon-class",
  "permission": "myapp.view_dashboard",
  "show_in_nav": true,
  "sort_order": 0,
  "is_active": true,
  "meta": {},
  "source": "seed"
}
```

The `permission` field accepts and returns `"app_label.codename"` strings. Set to `null` for no permission requirement.

### Permissions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/permissions/` | Superuser | List all permissions with source (model/custom) |
| POST | `/permissions/` | Superuser | Create custom permission (`codename` + `name`) |
| DELETE | `/permissions/{id}/` | Superuser | Delete custom permission (model perms blocked) |

### Groups

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/groups/` | Superuser | List groups with their permissions |
| PATCH | `/groups/{id}/` | Superuser | Set group permissions (list of `"app_label.codename"` strings) |

## Frontend Integration Guide

### 1. Fetch route config at startup

On login, call `GET /api/page-perms/routes/` to get the full route-permission mapping. Cache the result for the session.

### 2. Build navigation

Filter routes where `show_in_nav` is true. For each route, check if the current user has the required `permission` (from your user/auth endpoint). Hide routes the user cannot access.

### 3. Build route guard

From the routes response, build a `path → permission` map. In your router middleware, check if the current route matches any path prefix. If it does and the user lacks the permission, redirect to a forbidden page.

### 4. Handle `meta` field

The `meta` JSON field is for frontend-specific data (e.g., feature flags, service keys). The backend does not interpret it.

### 5. Error handling

If the routes API fails, do not fall back to hardcoded routes. Show an error state instead. This prevents stale permission data from causing security issues.
```

- [ ] **Step 2: Commit**

```bash
git add packages/django-page-perms/README.md
git commit -m "docs(page-perms): add package README with API docs and frontend guide"
```

---

## Task 13: Final integration test

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
uv run pytest -v
```

Expected: all pass.

- [ ] **Step 2: Start backend and verify API manually**

```bash
cd backend
uv run python manage.py sync_page_perms
uv run python manage.py runserver
```

In another terminal, test with a superuser token:

```bash
# Login to get token (adjust credentials)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# List routes
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/page-perms/routes/ | python3 -m json.tool

# List permissions
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/page-perms/permissions/ | python3 -m json.tool

# List groups
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/page-perms/groups/ | python3 -m json.tool
```

- [ ] **Step 3: Start frontend and verify**

```bash
cd frontend
npm run dev
```

Navigate to the app. Verify:
- Sidebar loads from API (not hardcoded)
- Route guard works (try accessing a page without permission)
- `/app/permissions` page loads for superuser
- Three tabs display data correctly

- [ ] **Step 4: Final commit if any adjustments were needed**

```bash
git add -A
git commit -m "fix: integration adjustments for django-page-perms"
```
