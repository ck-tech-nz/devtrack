# DevTrack Backend Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django REST Framework backend with JWT auth, permissions, and Dashboard aggregation APIs, then connect the existing Nuxt 4 frontend to real API endpoints.

**Architecture:** Django 5 + DRF with 4 apps (settings, users, projects, issues). PostgreSQL database. TDD with pytest + factory_boy. Frontend connects via Nuxt routeRules proxy.

**Tech Stack:** Django 5, DRF, djangorestframework-simplejwt, django-solo, pytest, pytest-django, factory_boy, faker, PostgreSQL

**Spec:** `docs/specs/2026-03-20-backend-service-design.md`

---

## File Map

### backend/ — New files

```
backend/
├── config/
│   ├── __init__.py
│   ├── settings.py          ← Django settings (DB, auth, apps, REST config)
│   ├── urls.py               ← Root URL conf, includes app urls under /api/
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── permissions.py        ← FullDjangoModelPermissions (enforces view_* on GET)
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── models.py         ← SiteSettings (SingletonModel)
│   │   ├── serializers.py    ← SiteSettingsSerializer
│   │   ├── views.py          ← SiteSettingsView (retrieve only)
│   │   ├── urls.py
│   │   ├── admin.py          ← SingletonModelAdmin
│   │   └── apps.py
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py         ← Custom User (AbstractUser + UUID pk)
│   │   ├── serializers.py    ← UserSerializer, MeSerializer
│   │   ├── views.py          ← UserViewSet (list/retrieve), MeView
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── apps.py
│   ├── projects/
│   │   ├── __init__.py
│   │   ├── models.py         ← Project, ProjectMember
│   │   ├── serializers.py    ← ProjectSerializer, ProjectMemberSerializer
│   │   ├── views.py          ← ProjectViewSet, ProjectMemberViewSet, ProjectIssuesView
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── apps.py
│   └── issues/
│       ├── __init__.py
│       ├── models.py         ← Issue, Activity
│       ├── serializers.py    ← IssueSerializer, IssueListSerializer, BatchUpdateSerializer, ActivitySerializer
│       ├── views.py          ← IssueViewSet, BatchUpdateView, DashboardViews
│       ├── urls.py
│       ├── admin.py
│       └── apps.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py            ← pytest fixtures, API client helpers
│   ├── factories.py           ← All factory_boy factories
│   ├── test_settings.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_projects.py
│   ├── test_issues.py
│   ├── test_dashboard.py
│   └── test_permissions.py
├── manage.py
├── requirements.txt
├── pytest.ini
└── setup.cfg
```

### frontend/ — Modified files

```
frontend/
├── nuxt.config.ts                          ← Add routeRules proxy
└── app/
    ├── composables/
    │   ├── useApi.ts                       ← NEW: $fetch wrapper with JWT
    │   └── useAuth.ts                      ← NEW: auth state + can() helper
    ├── middleware/
    │   └── auth.global.ts                  ← NEW: global route permission guard
    ├── pages/
    │   └── index.vue                       ← Modify: real JWT login
    └── components/
        └── AppSidebar.vue                  ← Modify: permission-based nav
```

---

## Task 1: Django Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config/settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `__init__.py`
- Create: `backend/manage.py`
- Create: `backend/pytest.ini`
- Create: `backend/apps/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
backend/requirements.txt
```

```txt
django>=5.1,<6.0
djangorestframework>=3.15,<4.0
djangorestframework-simplejwt>=5.3,<6.0
django-solo>=2.3,<3.0
django-filter>=24.0,<25.0
psycopg[binary]>=3.2,<4.0
pytest>=8.0,<9.0
pytest-django>=4.9,<5.0
factory-boy>=3.3,<4.0
faker>=30.0,<40.0
```

- [ ] **Step 2: Create Django project using django-admin**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
pip install -r requirements.txt
django-admin startproject config .
```

This generates `manage.py` and `config/` with `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `__init__.py`.

- [ ] **Step 3: Create apps directory and __init__.py**

```bash
mkdir -p apps
touch apps/__init__.py
```

- [ ] **Step 4: Configure settings.py**

Replace the generated `config/settings.py` with project-specific settings:

```python
# config/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-devtrack-dev-only-change-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1")

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "django_filters",
    "solo",
    # Local apps
    "apps.settings",
    "apps.users",
    "apps.projects",
    "apps.issues",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "devtrack",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "127.0.0.1",
        "PORT": "25432",
    }
}

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- [ ] **Step 5: Configure root urls.py**

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.urls")),
]
```

- [ ] **Step 6: Create apps/urls.py (app router)**

```python
# apps/urls.py
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.users.auth_urls")),
    path("settings/", include("apps.settings.urls")),
    path("users/", include("apps.users.urls")),
    path("projects/", include("apps.projects.urls")),
    path("issues/", include("apps.issues.urls")),
    path("dashboard/", include("apps.issues.dashboard_urls")),
]
```

- [ ] **Step 7: Create pytest.ini**

```ini
# backend/pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests/test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 8: Create the devtrack database in PostgreSQL**

```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 25432 -U postgres -c "CREATE DATABASE devtrack;"
```

- [ ] **Step 9: Verify Django starts**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
python manage.py check
```

Expected: `System check identified no issues` (will show warnings about missing apps — that's fine, they're created next).

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold Django project with settings, pytest config"
```

---

## Task 2: Settings App (SiteSettings Singleton)

**Files:**
- Create: `backend/apps/settings/models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `apps.py`, `__init__.py`
- Create: `backend/tests/test_settings.py`
- Create: `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/factories.py`

- [ ] **Step 1: Create test infrastructure — conftest.py and factories.py**

```python
# backend/tests/__init__.py
```

```python
# backend/tests/conftest.py
import pytest
from rest_framework.test import APIClient
from tests.factories import UserFactory, SiteSettingsFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def site_settings():
    return SiteSettingsFactory()
```

```python
# backend/tests/factories.py
import factory
from faker import Faker
from django.contrib.auth import get_user_model
from apps.settings.models import SiteSettings

fake = Faker("zh_CN")
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(lambda: fake.user_name())
    name = factory.LazyFunction(lambda: fake.name())
    email = factory.LazyFunction(lambda: fake.email())
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class SiteSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteSettings
        django_get_or_create = ("id",)

    id = 1
    labels = ["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"]
    priorities = ["P0", "P1", "P2", "P3"]
    issue_statuses = ["待处理", "进行中", "已解决", "已关闭"]
```

- [ ] **Step 2: Write failing tests for SiteSettings**

```python
# backend/tests/test_settings.py
import pytest
from apps.settings.models import SiteSettings

pytestmark = pytest.mark.django_db


class TestSiteSettingsModel:
    def test_singleton_only_one_instance(self, site_settings):
        """SiteSettings should only allow one row."""
        second = SiteSettings.objects.create()
        assert SiteSettings.objects.count() == 1

    def test_default_labels(self, site_settings):
        assert "前端" in site_settings.labels
        assert "Bug" in site_settings.labels
        assert len(site_settings.labels) == 10

    def test_default_priorities(self, site_settings):
        assert site_settings.priorities == ["P0", "P1", "P2", "P3"]

    def test_default_issue_statuses(self, site_settings):
        assert site_settings.issue_statuses == ["待处理", "进行中", "已解决", "已关闭"]


class TestSiteSettingsAPI:
    def test_get_settings_authenticated(self, auth_client, site_settings):
        response = auth_client.get("/api/settings/")
        assert response.status_code == 200
        assert response.data["labels"] == site_settings.labels
        assert response.data["priorities"] == site_settings.priorities
        assert response.data["issue_statuses"] == site_settings.issue_statuses

    def test_get_settings_unauthenticated(self, api_client, site_settings):
        response = api_client.get("/api/settings/")
        assert response.status_code == 401
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
python -m pytest tests/test_settings.py -v
```

Expected: FAIL (models don't exist yet)

- [ ] **Step 4: Create settings app**

```python
# backend/apps/settings/__init__.py
```

```python
# backend/apps/settings/apps.py
from django.apps import AppConfig


class SettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.settings"
    verbose_name = "系统设置"
```

```python
# backend/apps/settings/models.py
from django.db import models
from solo.models import SingletonModel


class SiteSettings(SingletonModel):
    labels = models.JSONField(
        default=lambda: ["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"],
        verbose_name="Issue 标签",
    )
    priorities = models.JSONField(
        default=lambda: ["P0", "P1", "P2", "P3"],
        verbose_name="优先级选项",
    )
    issue_statuses = models.JSONField(
        default=lambda: ["待处理", "进行中", "已解决", "已关闭"],
        verbose_name="Issue 状态选项",
    )

    class Meta:
        verbose_name = "系统设置"
        verbose_name_plural = "系统设置"

    def __str__(self):
        return "系统设置"
```

```python
# backend/apps/settings/serializers.py
from rest_framework import serializers
from .models import SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["labels", "priorities", "issue_statuses"]
```

```python
# backend/apps/settings/views.py
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from .models import SiteSettings
from .serializers import SiteSettingsSerializer


class SiteSettingsView(RetrieveAPIView):
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return SiteSettings.get_solo()
```

```python
# backend/apps/settings/urls.py
from django.urls import path
from .views import SiteSettingsView

urlpatterns = [
    path("", SiteSettingsView.as_view(), name="site-settings"),
]
```

```python
# backend/apps/settings/admin.py
from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import SiteSettings

admin.site.register(SiteSettings, SingletonModelAdmin)
```

- [ ] **Step 5: Create users app stub (needed for auth_client fixture)**

Minimal User model needed for the test fixtures to work. Full users app is Task 3.

```python
# backend/apps/users/__init__.py
```

```python
# backend/apps/users/apps.py
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "用户管理"
```

```python
# backend/apps/users/models.py
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, verbose_name="姓名")
    github_id = models.CharField(max_length=100, blank=True, verbose_name="GitHub ID")
    avatar = models.URLField(blank=True, verbose_name="头像")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.name or self.username
```

```python
# backend/apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "name", "email", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("扩展信息", {"fields": ("name", "github_id", "avatar")}),
    )
```

- [ ] **Step 6: Create stub apps.py for projects and issues (needed for migrations)**

```python
# backend/apps/projects/__init__.py
```

```python
# backend/apps/projects/apps.py
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    verbose_name = "项目管理"
```

```python
# backend/apps/projects/models.py
# Implemented in Task 4
```

```python
# backend/apps/projects/admin.py
```

```python
# backend/apps/issues/__init__.py
```

```python
# backend/apps/issues/apps.py
from django.apps import AppConfig


class IssuesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.issues"
    verbose_name = "问题跟踪"
```

```python
# backend/apps/issues/models.py
# Implemented in Task 5
```

```python
# backend/apps/issues/admin.py
```

- [ ] **Step 7: Create stub URL files for apps not yet implemented**

```python
# backend/apps/users/urls.py
from django.urls import path

urlpatterns = []
```

```python
# backend/apps/users/auth_urls.py
from django.urls import path

urlpatterns = []
```

```python
# backend/apps/projects/urls.py
from django.urls import path

urlpatterns = []
```

```python
# backend/apps/issues/urls.py
from django.urls import path

urlpatterns = []
```

```python
# backend/apps/issues/dashboard_urls.py
from django.urls import path

urlpatterns = []
```

- [ ] **Step 8: Run migrations and tests**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
python manage.py makemigrations settings users
python manage.py migrate
python -m pytest tests/test_settings.py -v
```

Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat(backend): add settings app with SiteSettings singleton + TDD tests"
```

---

## Task 3: Users App — JWT Auth + User API

**Files:**
- Modify: `backend/apps/users/models.py` (already created in Task 2)
- Create: `backend/apps/users/serializers.py`, `views.py`
- Modify: `backend/apps/users/urls.py`, `auth_urls.py`
- Create: `backend/tests/test_auth.py`, `backend/tests/test_users.py`

- [ ] **Step 1: Write failing auth tests**

```python
# backend/tests/test_auth.py
import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestLogin:
    def test_login_success(self, api_client):
        user = UserFactory(username="zhangsan")
        response = api_client.post("/api/auth/login/", {
            "username": "zhangsan",
            "password": "testpass123",
        })
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client):
        UserFactory(username="zhangsan")
        response = api_client.post("/api/auth/login/", {
            "username": "zhangsan",
            "password": "wrong",
        })
        assert response.status_code == 401

    def test_refresh_token(self, api_client):
        user = UserFactory(username="zhangsan")
        login = api_client.post("/api/auth/login/", {
            "username": "zhangsan",
            "password": "testpass123",
        })
        response = api_client.post("/api/auth/refresh/", {
            "refresh": login.data["refresh"],
        })
        assert response.status_code == 200
        assert "access" in response.data


class TestMe:
    def test_me_authenticated(self, api_client):
        user = UserFactory(username="zhangsan", name="张三", email="zs@example.com")
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 200
        assert response.data["name"] == "张三"
        assert response.data["email"] == "zs@example.com"
        assert "groups" in response.data
        assert "permissions" in response.data

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401

    def test_me_includes_group_names(self, api_client):
        from django.contrib.auth.models import Group
        user = UserFactory()
        group = Group.objects.create(name="前端开发")
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert "前端开发" in response.data["groups"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_auth.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement auth URLs and MeView**

```python
# backend/apps/users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "github_id", "avatar"]


class MeSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "github_id", "avatar", "groups", "permissions"]

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    def get_permissions(self, obj):
        return list(obj.get_all_permissions())
```

```python
# backend/apps/users/views.py
from rest_framework.generics import RetrieveAPIView, ListAPIView, RetrieveAPIView as DetailView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, MeSerializer

User = get_user_model()


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # No pagination for user dropdown


class UserDetailView(DetailView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
```

```python
# backend/apps/users/auth_urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token-login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
]
```

```python
# backend/apps/users/urls.py
from django.urls import path
from .views import UserListView, UserDetailView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_auth.py -v
```

Expected: All PASS

- [ ] **Step 5: Write failing user list/detail tests**

```python
# backend/tests/test_users.py
import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserList:
    def test_list_users(self, auth_client):
        UserFactory.create_batch(3)
        response = auth_client.get("/api/users/")
        assert response.status_code == 200
        # auth_client creates 1 user + 3 = 4 total
        assert len(response.data) == 4

    def test_list_users_unauthenticated(self, api_client):
        response = api_client.get("/api/users/")
        assert response.status_code == 401


class TestUserDetail:
    def test_get_user_detail(self, auth_client):
        user = UserFactory(name="李四", github_id="lisi")
        response = auth_client.get(f"/api/users/{user.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "李四"
        assert response.data["github_id"] == "lisi"
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/test_users.py -v
```

Expected: All PASS (views already implemented)

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): add JWT auth (login/refresh/me) + user list/detail API"
```

---

## Task 4: Projects App — Project + Members CRUD

**Files:**
- Modify: `backend/apps/projects/models.py`
- Create: `backend/apps/projects/serializers.py`, `views.py`
- Modify: `backend/apps/projects/urls.py`, `admin.py`
- Modify: `backend/tests/factories.py` — add ProjectFactory, ProjectMemberFactory
- Create: `backend/tests/test_projects.py`

- [ ] **Step 1: Add factories**

Add to `backend/tests/factories.py`:

```python
from apps.projects.models import Project, ProjectMember


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.LazyFunction(lambda: fake.catch_phrase())
    description = factory.LazyFunction(lambda: fake.paragraph())
    status = "进行中"


class ProjectMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectMember

    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = "member"
```

- [ ] **Step 2: Write failing project tests**

```python
# backend/tests/test_projects.py
import pytest
from tests.factories import UserFactory, ProjectFactory, ProjectMemberFactory

pytestmark = pytest.mark.django_db


class TestProjectList:
    def test_list_projects(self, auth_client):
        ProjectFactory.create_batch(3)
        response = auth_client.get("/api/projects/")
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_list_includes_member_count(self, auth_client):
        project = ProjectFactory()
        ProjectMemberFactory.create_batch(2, project=project)
        response = auth_client.get("/api/projects/")
        result = response.data["results"][0]
        assert result["member_count"] == 2


class TestProjectDetail:
    def test_get_project_detail(self, auth_client):
        project = ProjectFactory(name="测试项目")
        response = auth_client.get(f"/api/projects/{project.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "测试项目"

    def test_project_detail_includes_members(self, auth_client):
        project = ProjectFactory()
        member = ProjectMemberFactory(project=project, role="owner")
        response = auth_client.get(f"/api/projects/{project.id}/")
        assert len(response.data["members"]) == 1
        assert response.data["members"][0]["role"] == "owner"


class TestProjectCreate:
    def test_create_project(self, auth_client):
        response = auth_client.post("/api/projects/", {
            "name": "新项目",
            "description": "描述",
            "status": "进行中",
        })
        assert response.status_code == 201
        assert response.data["name"] == "新项目"


class TestProjectUpdate:
    def test_update_project(self, auth_client):
        project = ProjectFactory()
        response = auth_client.patch(f"/api/projects/{project.id}/", {
            "name": "改名了",
        })
        assert response.status_code == 200
        assert response.data["name"] == "改名了"


class TestProjectDelete:
    def test_delete_project(self, auth_client):
        project = ProjectFactory()
        response = auth_client.delete(f"/api/projects/{project.id}/")
        assert response.status_code == 204


class TestProjectMembers:
    def test_list_members(self, auth_client):
        project = ProjectFactory()
        ProjectMemberFactory(project=project, role="owner")
        response = auth_client.get(f"/api/projects/{project.id}/members/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_add_member(self, auth_client):
        project = ProjectFactory()
        user = UserFactory()
        response = auth_client.post(f"/api/projects/{project.id}/members/", {
            "user_id": str(user.id),
            "role": "member",
        })
        assert response.status_code == 201

    def test_remove_member(self, auth_client):
        project = ProjectFactory()
        member = ProjectMemberFactory(project=project)
        response = auth_client.delete(
            f"/api/projects/{project.id}/members/{member.user.id}/"
        )
        assert response.status_code == 204


class TestProjectIssues:
    def test_list_project_issues(self, auth_client, site_settings):
        from tests.factories import IssueFactory
        project = ProjectFactory()
        IssueFactory.create_batch(3, project=project)
        IssueFactory()  # Different project
        response = auth_client.get(f"/api/projects/{project.id}/issues/")
        assert response.status_code == 200
        assert response.data["count"] == 3
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/test_projects.py -v
```

Expected: FAIL

- [ ] **Step 4: Implement Project models**

```python
# backend/apps/projects/models.py
import uuid
from django.conf import settings
from django.db import models


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="项目名")
    description = models.TextField(blank=True, verbose_name="描述")
    status = models.CharField(max_length=20, verbose_name="状态")
    remark = models.TextField(blank=True, verbose_name="备注")
    estimated_completion = models.DateField(null=True, blank=True, verbose_name="预计完成")
    actual_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="实际工时"
    )
    linked_repos = models.JSONField(default=list, verbose_name="关联仓库")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ProjectMember",
        related_name="projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "项目"
        verbose_name_plural = "项目"
        ordering = ["-updated_at"]
        permissions = [
            ("manage_project_members", "Can manage project members"),
        ]

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="project_members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=20, verbose_name="角色")

    class Meta:
        verbose_name = "项目成员"
        verbose_name_plural = "项目成员"
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.user} - {self.project} ({self.role})"
```

- [ ] **Step 5: Implement Project serializers**

```python
# backend/apps/projects/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectMember

User = get_user_model()


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["user_id", "user_name", "avatar", "role"]


class ProjectMemberCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=["owner", "admin", "member"])

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("用户不存在")
        return value


class ProjectListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    issue_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "linked_repos",
            "member_count", "issue_count", "created_at", "updated_at",
        ]

    def get_member_count(self, obj):
        return obj.project_members.count()

    def get_issue_count(self, obj):
        return obj.issues.count() if hasattr(obj, "issues") else 0


class ProjectDetailSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(source="project_members", many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "linked_repos",
            "members", "created_at", "updated_at",
        ]


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "linked_repos",
        ]
```

- [ ] **Step 6: Implement Project views**

```python
# backend/apps/projects/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Project, ProjectMember
from .serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateUpdateSerializer,
    ProjectMemberSerializer,
    ProjectMemberCreateSerializer,
)

User = get_user_model()


class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProjectCreateUpdateSerializer
        return ProjectListSerializer


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProjectCreateUpdateSerializer
        return ProjectDetailSerializer


class ProjectMemberListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(project_id=self.kwargs["project_pk"])

    def create(self, request, project_pk=None):
        serializer = ProjectMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(Project, pk=project_pk)
        member = ProjectMember.objects.create(
            project=project,
            user_id=serializer.validated_data["user_id"],
            role=serializer.validated_data["role"],
        )
        return Response(
            ProjectMemberSerializer(member).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectMemberDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            ProjectMember,
            project_id=self.kwargs["project_pk"],
            user_id=self.kwargs["user_pk"],
        )


class ProjectIssuesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.issues.models import Issue
        return Issue.objects.filter(project_id=self.kwargs["project_pk"])

    def get_serializer_class(self):
        from apps.issues.serializers import IssueListSerializer
        return IssueListSerializer
```

```python
# backend/apps/projects/urls.py
from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListCreateView,
    ProjectMemberDeleteView,
    ProjectIssuesView,
)

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("<uuid:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<uuid:project_pk>/members/", ProjectMemberListCreateView.as_view(), name="project-members"),
    path("<uuid:project_pk>/members/<uuid:user_pk>/", ProjectMemberDeleteView.as_view(), name="project-member-delete"),
    path("<uuid:project_pk>/issues/", ProjectIssuesView.as_view(), name="project-issues"),
]
```

```python
# backend/apps/projects/admin.py
from django.contrib import admin
from .models import Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at")
    inlines = [ProjectMemberInline]
```

- [ ] **Step 7: Run migrations and tests**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
python manage.py makemigrations projects
python manage.py migrate
python -m pytest tests/test_projects.py -v
```

Expected: Most tests PASS. `TestProjectIssues` may fail (depends on Issue model — that's OK, it's tested in Task 5).

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat(backend): add projects app — Project + ProjectMember CRUD with tests"
```

---

## Task 5: Issues App — Issue + Activity CRUD

**Files:**
- Modify: `backend/apps/issues/models.py`
- Create: `backend/apps/issues/serializers.py`, `views.py`
- Modify: `backend/apps/issues/urls.py`, `admin.py`
- Modify: `backend/tests/factories.py` — add IssueFactory, ActivityFactory
- Create: `backend/tests/test_issues.py`

- [ ] **Step 1: Add factories**

Add to `backend/tests/factories.py`:

```python
from apps.issues.models import Issue, Activity


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue

    project = factory.SubFactory(ProjectFactory)
    title = factory.LazyFunction(lambda: fake.sentence())
    description = factory.LazyFunction(lambda: fake.paragraph())
    priority = factory.Iterator(["P0", "P1", "P2", "P3"])
    status = "待处理"
    labels = factory.LazyFunction(lambda: [fake.random_element(["前端", "后端", "Bug"])])
    reporter = factory.SubFactory(UserFactory)


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activity

    user = factory.SubFactory(UserFactory)
    issue = factory.SubFactory(IssueFactory)
    action = "created"
    detail = ""
```

- [ ] **Step 2: Write failing issue tests**

```python
# backend/tests/test_issues.py
import pytest
from tests.factories import UserFactory, IssueFactory, SiteSettingsFactory

pytestmark = pytest.mark.django_db


class TestIssueList:
    def test_list_issues(self, auth_client, site_settings):
        IssueFactory.create_batch(3)
        response = auth_client.get("/api/issues/")
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_filter_by_priority(self, auth_client, site_settings):
        IssueFactory(priority="P0")
        IssueFactory(priority="P1")
        response = auth_client.get("/api/issues/?priority=P0")
        assert response.data["count"] == 1

    def test_filter_by_status(self, auth_client, site_settings):
        IssueFactory(status="待处理")
        IssueFactory(status="进行中")
        response = auth_client.get("/api/issues/?status=待处理")
        assert response.data["count"] == 1

    def test_filter_by_assignee(self, auth_client, site_settings):
        user = UserFactory()
        IssueFactory(assignee=user)
        IssueFactory()  # No assignee
        response = auth_client.get(f"/api/issues/?assignee={user.id}")
        assert response.data["count"] == 1

    def test_search_by_title(self, auth_client, site_settings):
        IssueFactory(title="登录页面崩溃")
        IssueFactory(title="支付功能异常")
        response = auth_client.get("/api/issues/?search=登录")
        assert response.data["count"] == 1

    def test_ordering(self, auth_client, site_settings):
        IssueFactory(priority="P3")
        IssueFactory(priority="P0")
        response = auth_client.get("/api/issues/?ordering=priority")
        results = response.data["results"]
        assert results[0]["priority"] == "P0"

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/issues/")
        assert response.status_code == 401


class TestIssueDetail:
    def test_get_issue_detail(self, auth_client, site_settings):
        issue = IssueFactory(title="Bug修复")
        response = auth_client.get(f"/api/issues/{issue.id}/")
        assert response.status_code == 200
        assert response.data["title"] == "Bug修复"
        assert "display_id" in response.data
        assert response.data["display_id"].startswith("ISS-")

    def test_resolution_hours_computed(self, auth_client, site_settings):
        from django.utils import timezone
        from datetime import timedelta
        issue = IssueFactory()
        issue.resolved_at = issue.created_at + timedelta(hours=5)
        issue.save()
        response = auth_client.get(f"/api/issues/{issue.id}/")
        assert response.data["resolution_hours"] == pytest.approx(5.0, abs=0.1)

    def test_resolution_hours_null_when_unresolved(self, auth_client, site_settings):
        issue = IssueFactory()
        response = auth_client.get(f"/api/issues/{issue.id}/")
        assert response.data["resolution_hours"] is None


class TestIssueCreate:
    def test_create_issue(self, auth_client, site_settings):
        from tests.factories import ProjectFactory
        project = ProjectFactory()
        response = auth_client.post("/api/issues/", {
            "project": str(project.id),
            "title": "新Issue",
            "priority": "P1",
            "status": "待处理",
            "labels": ["前端", "Bug"],
        })
        assert response.status_code == 201
        assert response.data["title"] == "新Issue"

    def test_create_issue_invalid_label(self, auth_client, site_settings):
        from tests.factories import ProjectFactory
        project = ProjectFactory()
        response = auth_client.post("/api/issues/", {
            "project": str(project.id),
            "title": "新Issue",
            "priority": "P1",
            "status": "待处理",
            "labels": ["不存在的标签"],
        })
        assert response.status_code == 400

    def test_create_issue_creates_activity(self, auth_client, site_settings):
        from tests.factories import ProjectFactory
        from apps.issues.models import Activity
        project = ProjectFactory()
        auth_client.post("/api/issues/", {
            "project": str(project.id),
            "title": "新Issue",
            "priority": "P1",
            "status": "待处理",
            "labels": [],
        })
        assert Activity.objects.filter(action="created").count() == 1


class TestIssueUpdate:
    def test_update_issue(self, auth_client, site_settings):
        issue = IssueFactory()
        response = auth_client.patch(f"/api/issues/{issue.id}/", {
            "title": "更新后的标题",
        })
        assert response.status_code == 200
        assert response.data["title"] == "更新后的标题"

    def test_update_status_creates_activity(self, auth_client, site_settings):
        from apps.issues.models import Activity
        issue = IssueFactory(status="待处理")
        auth_client.patch(f"/api/issues/{issue.id}/", {"status": "已解决"})
        assert Activity.objects.filter(action="resolved").exists()

    def test_update_assignee_creates_activity(self, auth_client, site_settings):
        from apps.issues.models import Activity
        user = UserFactory()
        issue = IssueFactory()
        auth_client.patch(f"/api/issues/{issue.id}/", {"assignee": str(user.id)})
        assert Activity.objects.filter(action="assigned").exists()


class TestIssueDelete:
    def test_delete_issue(self, auth_client, site_settings):
        issue = IssueFactory()
        response = auth_client.delete(f"/api/issues/{issue.id}/")
        assert response.status_code == 204


class TestBatchUpdate:
    def test_batch_assign(self, auth_client, site_settings):
        issues = IssueFactory.create_batch(3)
        user = UserFactory()
        response = auth_client.post("/api/issues/batch-update/", {
            "ids": [str(i.id) for i in issues],
            "action": "assign",
            "value": str(user.id),
        }, format="json")
        assert response.status_code == 200
        assert response.data["updated"] == 3

    def test_batch_set_priority(self, auth_client, site_settings):
        issues = IssueFactory.create_batch(2)
        response = auth_client.post("/api/issues/batch-update/", {
            "ids": [str(i.id) for i in issues],
            "action": "set_priority",
            "value": "P0",
        }, format="json")
        assert response.status_code == 200
        from apps.issues.models import Issue
        for issue in Issue.objects.filter(id__in=[i.id for i in issues]):
            assert issue.priority == "P0"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/test_issues.py -v
```

Expected: FAIL

- [ ] **Step 4: Implement Issue and Activity models**

```python
# backend/apps/issues/models.py
import uuid
from django.conf import settings
from django.db import models


class Issue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveIntegerField(unique=True, editable=False, null=True)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="issues"
    )
    title = models.CharField(max_length=200, verbose_name="标题")
    description = models.TextField(blank=True, verbose_name="描述")
    priority = models.CharField(max_length=10, verbose_name="优先级")
    status = models.CharField(max_length=20, verbose_name="状态")
    labels = models.JSONField(default=list, verbose_name="标签")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_issues",
        verbose_name="提出人",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues",
        verbose_name="负责人",
    )
    remark = models.TextField(blank=True, verbose_name="备注")
    estimated_completion = models.DateField(null=True, blank=True, verbose_name="预计完成")
    actual_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="实际工时"
    )
    cause = models.TextField(blank=True, verbose_name="原因分析")
    solution = models.TextField(blank=True, verbose_name="解决办法")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="解决时间")

    # Override default AutoField pk behavior: use UUID as pk, number as auto-increment display field
    # Django requires exactly one primary key. We use id (UUID) as pk and number as a separate unique field.
    # Since AutoField requires primary_key=True by default, use PositiveIntegerField with a custom save.

    class Meta:
        verbose_name = "Issue"
        verbose_name_plural = "Issues"
        ordering = ["-created_at"]
        permissions = [
            ("batch_update_issue", "Can batch update issues"),
            ("view_dashboard", "Can view dashboard"),
        ]

    def __str__(self):
        if self.number:
            return f"ISS-{self.number:03d} {self.title}"
        return self.title

    def save(self, *args, **kwargs):
        if self._state.adding and not self.number:
            last = Issue.objects.order_by("-number").values_list("number", flat=True).first()
            self.number = (last or 0) + 1
        super().save(*args, **kwargs)


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activities",
    )
    action = models.CharField(max_length=20, verbose_name="动作")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="activities")
    detail = models.CharField(max_length=200, blank=True, verbose_name="详情")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "活动记录"
        verbose_name_plural = "活动记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.action} {self.issue}"
```

**Note:** `number` uses `PositiveIntegerField` instead of `AutoField` since Django only allows one AutoField pk. The `save()` method handles auto-increment. `bulk_create()` will NOT auto-assign `number` — always use `.save()` or create via serializer.

- [ ] **Step 5: Implement Issue serializers**

```python
# backend/apps/issues/serializers.py
from rest_framework import serializers
from django.utils import timezone
from apps.settings.models import SiteSettings
from .models import Issue, Activity


class ActivitySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    issue_title = serializers.CharField(source="issue.title", read_only=True)
    issue_id = serializers.UUIDField(source="issue.id", read_only=True)
    issue_display_id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id", "user_name", "action", "issue_title",
            "issue_id", "issue_display_id", "detail", "created_at",
        ]

    def get_issue_display_id(self, obj):
        return f"ISS-{obj.issue.number:03d}" if obj.issue.number else None


class IssueListSerializer(serializers.ModelSerializer):
    display_id = serializers.SerializerMethodField()
    reporter_name = serializers.CharField(source="reporter.name", read_only=True, default=None)
    assignee_name = serializers.CharField(source="assignee.name", read_only=True, default=None)
    resolution_hours = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "number", "display_id", "project", "title", "priority",
            "status", "labels", "reporter", "reporter_name",
            "assignee", "assignee_name", "resolution_hours",
            "created_at", "updated_at",
        ]

    def get_display_id(self, obj):
        return f"ISS-{obj.number:03d}" if obj.number else None

    def get_resolution_hours(self, obj):
        if obj.resolved_at and obj.created_at:
            delta = obj.resolved_at - obj.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None


class IssueDetailSerializer(IssueListSerializer):
    class Meta(IssueListSerializer.Meta):
        fields = IssueListSerializer.Meta.fields + [
            "description", "remark", "estimated_completion",
            "actual_hours", "cause", "solution", "resolved_at",
        ]


class IssueCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = [
            "project", "title", "description", "priority", "status",
            "labels", "assignee", "remark", "estimated_completion",
            "actual_hours", "cause", "solution",
        ]

    def validate_labels(self, value):
        settings = SiteSettings.get_solo()
        valid = set(settings.labels)
        invalid = [l for l in value if l not in valid]
        if invalid:
            raise serializers.ValidationError(f"无效的标签: {invalid}")
        return value

    def validate_priority(self, value):
        settings = SiteSettings.get_solo()
        if value not in settings.priorities:
            raise serializers.ValidationError(f"无效的优先级: {value}")
        return value

    def validate_status(self, value):
        settings = SiteSettings.get_solo()
        if value not in settings.issue_statuses:
            raise serializers.ValidationError(f"无效的状态: {value}")
        return value

    def create(self, validated_data):
        validated_data["reporter"] = self.context["request"].user
        issue = super().create(validated_data)
        Activity.objects.create(
            user=self.context["request"].user,
            issue=issue,
            action="created",
        )
        return issue

    def update(self, instance, validated_data):
        user = self.context["request"].user
        old_status = instance.status
        old_assignee = instance.assignee_id
        issue = super().update(instance, validated_data)

        # Track status changes
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

        # Track assignee changes
        new_assignee = validated_data.get("assignee")
        if "assignee" in validated_data and str(getattr(new_assignee, "id", None)) != str(old_assignee):
            Activity.objects.create(
                user=user, issue=issue, action="assigned",
                detail=f"分配给 {new_assignee.name}" if new_assignee else "取消分配",
            )

        return issue


class BatchUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField())
    action = serializers.ChoiceField(choices=["assign", "set_priority"])
    value = serializers.CharField()
```

- [ ] **Step 6: Implement Issue views**

```python
# backend/apps/issues/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import get_user_model
from .models import Issue, Activity
from .serializers import (
    IssueListSerializer,
    IssueDetailSerializer,
    IssueCreateUpdateSerializer,
    BatchUpdateSerializer,
)

User = get_user_model()


class IssueListCreateView(generics.ListCreateAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee")
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["priority", "status", "assignee", "project"]
    search_fields = ["title"]
    ordering_fields = ["created_at", "priority", "updated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IssueCreateUpdateSerializer
        return IssueListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        labels = self.request.query_params.get("labels")
        if labels:
            qs = qs.filter(labels__contains=[labels])
        return qs


class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return IssueCreateUpdateSerializer
        return IssueDetailSerializer


class BatchUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BatchUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        issues = Issue.objects.filter(id__in=data["ids"])
        count = issues.count()

        if data["action"] == "assign":
            user = User.objects.get(id=data["value"])
            issues.update(assignee=user)
        elif data["action"] == "set_priority":
            issues.update(priority=data["value"])

        return Response({"updated": count})
```

```python
# backend/apps/issues/urls.py
from django.urls import path
from .views import IssueListCreateView, IssueDetailView, BatchUpdateView

urlpatterns = [
    path("", IssueListCreateView.as_view(), name="issue-list"),
    path("batch-update/", BatchUpdateView.as_view(), name="issue-batch-update"),
    path("<uuid:pk>/", IssueDetailView.as_view(), name="issue-detail"),
]
```

```python
# backend/apps/issues/admin.py
from django.contrib import admin
from .models import Issue, Activity


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "priority", "status", "assignee", "created_at")
    list_filter = ("priority", "status")
    search_fields = ("title",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("issue", "user", "action", "created_at")
    list_filter = ("action",)
```

- [ ] **Step 7: Run migrations and tests**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
python manage.py makemigrations issues
python manage.py migrate
python -m pytest tests/test_issues.py -v
```

Expected: All PASS

- [ ] **Step 8: Re-run project tests (ProjectIssues depends on Issue model)**

```bash
python -m pytest tests/test_projects.py::TestProjectIssues -v
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat(backend): add issues app — Issue + Activity CRUD, batch update, label validation"
```

---

## Task 6: Dashboard Aggregation Endpoints

**Files:**
- Create: `backend/apps/issues/dashboard_urls.py` (already stubbed)
- Modify: `backend/apps/issues/views.py` — add dashboard views
- Create: `backend/tests/test_dashboard.py`

- [ ] **Step 1: Write failing dashboard tests**

```python
# backend/tests/test_dashboard.py
import pytest
from datetime import timedelta
from django.utils import timezone
from tests.factories import UserFactory, IssueFactory, ActivityFactory, SiteSettingsFactory

pytestmark = pytest.mark.django_db


class TestDashboardStats:
    def test_stats(self, auth_client, site_settings):
        IssueFactory(status="待处理")
        IssueFactory(status="待处理")
        IssueFactory(status="进行中")
        IssueFactory(status="已解决", resolved_at=timezone.now())
        response = auth_client.get("/api/dashboard/stats/")
        assert response.status_code == 200
        assert response.data["total"] == 4
        assert response.data["pending"] == 2
        assert response.data["in_progress"] == 1
        assert response.data["resolved_this_week"] >= 1


class TestDashboardTrends:
    def test_trends_returns_30_days(self, auth_client, site_settings):
        IssueFactory()
        response = auth_client.get("/api/dashboard/trends/")
        assert response.status_code == 200
        assert len(response.data) == 30

    def test_trends_shape(self, auth_client, site_settings):
        IssueFactory()
        response = auth_client.get("/api/dashboard/trends/")
        entry = response.data[0]
        assert "date" in entry
        assert "created" in entry
        assert "resolved" in entry


class TestDashboardPriorityDistribution:
    def test_priority_distribution(self, auth_client, site_settings):
        IssueFactory(priority="P0")
        IssueFactory(priority="P0")
        IssueFactory(priority="P1")
        response = auth_client.get("/api/dashboard/priority-distribution/")
        assert response.status_code == 200
        p0 = next(d for d in response.data if d["priority"] == "P0")
        assert p0["count"] == 2


class TestDashboardLeaderboard:
    def test_leaderboard(self, auth_client, site_settings):
        user = UserFactory(name="高手")
        for _ in range(5):
            IssueFactory(assignee=user, status="已解决", resolved_at=timezone.now())
        response = auth_client.get("/api/dashboard/developer-leaderboard/")
        assert response.status_code == 200
        assert len(response.data) <= 5
        assert response.data[0]["user_name"] == "高手"
        assert response.data[0]["monthly_resolved_count"] == 5


class TestDashboardRecentActivity:
    def test_recent_activity(self, auth_client, site_settings):
        ActivityFactory.create_batch(5)
        response = auth_client.get("/api/dashboard/recent-activity/")
        assert response.status_code == 200
        assert len(response.data) == 5

    def test_recent_activity_max_20(self, auth_client, site_settings):
        ActivityFactory.create_batch(25)
        response = auth_client.get("/api/dashboard/recent-activity/")
        assert len(response.data) == 20

    def test_recent_activity_shape(self, auth_client, site_settings):
        ActivityFactory()
        response = auth_client.get("/api/dashboard/recent-activity/")
        entry = response.data[0]
        assert "user_name" in entry
        assert "action" in entry
        assert "issue_title" in entry
        assert "issue_display_id" in entry
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_dashboard.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement dashboard views**

Add to `backend/apps/issues/views.py`:

```python
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, F, Q
from django.db.models.functions import TruncDate
from .serializers import ActivitySerializer


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return Response({
            "total": Issue.objects.count(),
            "pending": Issue.objects.filter(status="待处理").count(),
            "in_progress": Issue.objects.filter(status="进行中").count(),
            "resolved_this_week": Issue.objects.filter(
                resolved_at__gte=week_start
            ).count(),
        })


class DashboardTrendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        start = today - timedelta(days=29)
        dates = [start + timedelta(days=i) for i in range(30)]

        created_counts = dict(
            Issue.objects.filter(created_at__date__gte=start)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .values_list("date", "count")
        )
        resolved_counts = dict(
            Issue.objects.filter(resolved_at__date__gte=start)
            .annotate(date=TruncDate("resolved_at"))
            .values("date")
            .annotate(count=Count("id"))
            .values_list("date", "count")
        )

        return Response([
            {
                "date": d.isoformat(),
                "created": created_counts.get(d, 0),
                "resolved": resolved_counts.get(d, 0),
            }
            for d in dates
        ])


class DashboardPriorityDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            Issue.objects.values("priority")
            .annotate(count=Count("id"))
            .order_by("priority")
        )
        return Response(list(data))


class DashboardLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        data = (
            Issue.objects.filter(status="已解决", resolved_at__gte=month_start)
            .values("assignee")
            .annotate(
                monthly_resolved_count=Count("id"),
                avg_resolution_hours=Avg(
                    (F("resolved_at") - F("created_at")),
                ),
            )
            .order_by("-monthly_resolved_count")[:5]
        )
        result = []
        for entry in data:
            user = User.objects.filter(id=entry["assignee"]).first()
            if user:
                avg_hours = entry["avg_resolution_hours"]
                if avg_hours:
                    avg_hours = round(avg_hours.total_seconds() / 3600, 1)
                result.append({
                    "user_id": str(user.id),
                    "user_name": user.name,
                    "monthly_resolved_count": entry["monthly_resolved_count"],
                    "avg_resolution_hours": avg_hours,
                })
        return Response(result)


class DashboardRecentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = Activity.objects.select_related("user", "issue")[:20]
        return Response(ActivitySerializer(activities, many=True).data)
```

- [ ] **Step 4: Wire up dashboard URLs**

```python
# backend/apps/issues/dashboard_urls.py
from django.urls import path
from .views import (
    DashboardStatsView,
    DashboardTrendsView,
    DashboardPriorityDistributionView,
    DashboardLeaderboardView,
    DashboardRecentActivityView,
)

urlpatterns = [
    path("stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("trends/", DashboardTrendsView.as_view(), name="dashboard-trends"),
    path("priority-distribution/", DashboardPriorityDistributionView.as_view(), name="dashboard-priority"),
    path("developer-leaderboard/", DashboardLeaderboardView.as_view(), name="dashboard-leaderboard"),
    path("recent-activity/", DashboardRecentActivityView.as_view(), name="dashboard-activity"),
]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_dashboard.py -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): add dashboard aggregation endpoints — stats, trends, leaderboard, activity"
```

---

## Task 7: Permissions Setup

**Files:**
- Create: `backend/apps/permissions.py`
- Modify: `backend/tests/conftest.py` — update auth_client with admin permissions
- Create: `backend/tests/test_permissions.py`
- Create: `backend/apps/users/management/commands/setup_groups.py`

**Important:** Step order matters. Update the `auth_client` fixture FIRST (Step 1), then add permission classes (Step 3). Otherwise all existing tests break.

- [ ] **Step 1: Update auth_client fixture to include admin permissions**

This must happen BEFORE adding permission classes to views, otherwise all existing tests that use `auth_client` will get 403.

Update `backend/tests/conftest.py`:

```python
@pytest.fixture
def auth_client(api_client):
    from django.contrib.auth.models import Group, Permission
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="管理员")
    group.permissions.set(
        Permission.objects.filter(content_type__app_label__in=["projects", "issues", "settings"])
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client
```

- [ ] **Step 2: Create custom FullDjangoModelPermissions**

DRF's built-in `DjangoModelPermissions` does NOT enforce `view_*` on GET — it allows any authenticated user to read. We need a custom class.

```python
# backend/apps/permissions.py
from rest_framework.permissions import DjangoModelPermissions


class FullDjangoModelPermissions(DjangoModelPermissions):
    """Extends DjangoModelPermissions to also check view_* on GET/HEAD/OPTIONS."""

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
```

- [ ] **Step 3: Write failing permission tests**

```python
# backend/tests/test_permissions.py
import pytest
from django.contrib.auth.models import Group, Permission
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestPermissionEnforcement:
    def test_readonly_user_cannot_create_project(self, api_client):
        group = Group.objects.create(name="只读成员")
        view_perm = Permission.objects.get(codename="view_project")
        group.permissions.add(view_perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/projects/", {"name": "Test", "status": "进行中"})
        assert response.status_code == 403

    def test_readonly_user_can_list_projects(self, api_client):
        group = Group.objects.create(name="只读成员")
        view_perm = Permission.objects.get(codename="view_project")
        group.permissions.add(view_perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/projects/")
        assert response.status_code == 200

    def test_no_view_permission_cannot_list_projects(self, api_client):
        """User with NO view_project permission should get 403 on GET."""
        group = Group.objects.create(name="空权限组")
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/projects/")
        assert response.status_code == 403

    def test_admin_can_create_project(self, api_client):
        group = Group.objects.create(name="管理员")
        for perm in Permission.objects.filter(content_type__app_label__in=["projects", "issues"]):
            group.permissions.add(perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/projects/", {"name": "Test", "status": "进行中"})
        assert response.status_code == 201

    def test_me_returns_permissions(self, api_client):
        group = Group.objects.create(name="开发者")
        perm = Permission.objects.get(codename="view_project")
        group.permissions.add(perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert "projects.view_project" in response.data["permissions"]
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
python -m pytest tests/test_permissions.py -v
```

Expected: FAIL (views don't check permissions yet)

- [ ] **Step 5: Add FullDjangoModelPermissions to views**

Update `backend/apps/projects/views.py`:

```python
from apps.permissions import FullDjangoModelPermissions

class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    ...

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    ...
```

Update `backend/apps/issues/views.py` similarly for `IssueListCreateView` and `IssueDetailView`.

Keep `IsAuthenticated` only (no model permissions) on: Dashboard views, Settings, Me, Users.

- [ ] **Step 6: Run permission tests**

```bash
python -m pytest tests/test_permissions.py -v
```

Expected: All PASS

- [ ] **Step 7: Re-run ALL tests to verify nothing broke**

```bash
python -m pytest -v
```

Expected: All PASS (auth_client now has admin permissions)

- [ ] **Step 8: Create management command to seed default groups**

```python
# backend/apps/users/management/__init__.py
```

```python
# backend/apps/users/management/commands/__init__.py
```

```python
# backend/apps/users/management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Create default permission groups"

    def handle(self, *args, **options):
        groups_config = {
            "管理员": Permission.objects.filter(
                content_type__app_label__in=["projects", "issues", "settings"]
            ),
            "开发者": Permission.objects.filter(
                codename__in=[
                    "view_project",
                    "view_issue", "add_issue", "change_issue",
                    "view_activity", "view_dashboard",
                ]
            ),
            "产品经理": Permission.objects.filter(
                codename__in=[
                    "view_project", "add_project", "change_project",
                    "view_issue", "add_issue", "change_issue",
                    "view_activity", "view_dashboard",
                    "manage_project_members",
                ]
            ),
            "只读成员": Permission.objects.filter(
                codename__startswith="view_"
            ),
        }

        for group_name, perms in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(perms)
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} group: {group_name} ({perms.count()} permissions)")
```

- [ ] **Step 9: Run setup_groups and commit**

```bash
python manage.py setup_groups
git add backend/
git commit -m "feat(backend): add Django permissions — FullDjangoModelPermissions, groups, setup_groups command"
```

---

## Task 8: Frontend Integration — useApi + useAuth + Proxy

**Files:**
- Modify: `frontend/nuxt.config.ts`
- Create: `frontend/app/composables/useApi.ts`
- Create: `frontend/app/composables/useAuth.ts`
- Create: `frontend/app/middleware/auth.global.ts`
- Modify: `frontend/app/pages/index.vue`

- [ ] **Step 1: Add routeRules proxy to nuxt.config.ts**

Add to the `nuxt.config.ts` export:

```ts
routeRules: {
  '/api/**': { proxy: 'http://localhost:8000/api/**' }
}
```

- [ ] **Step 2: Create useApi composable**

```typescript
// frontend/app/composables/useApi.ts
export function useApi() {
  const getToken = () => localStorage.getItem('access_token')
  const getRefreshToken = () => localStorage.getItem('refresh_token')

  const setTokens = (access: string, refresh: string) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  const clearTokens = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function refreshAccessToken(): Promise<string | null> {
    const refresh = getRefreshToken()
    if (!refresh) return null
    try {
      const data = await $fetch<{ access: string }>('/api/auth/refresh/', {
        method: 'POST',
        body: { refresh },
      })
      localStorage.setItem('access_token', data.access)
      return data.access
    } catch {
      clearTokens()
      navigateTo('/')
      return null
    }
  }

  async function api<T>(url: string, options: any = {}): Promise<T> {
    const token = getToken()
    const headers = {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }

    try {
      return await $fetch<T>(url, { ...options, headers })
    } catch (error: any) {
      if (error?.response?.status === 401 && token) {
        const newToken = await refreshAccessToken()
        if (newToken) {
          return $fetch<T>(url, {
            ...options,
            headers: { ...options.headers, Authorization: `Bearer ${newToken}` },
          })
        }
      }
      throw error
    }
  }

  return { api, setTokens, clearTokens, getToken }
}
```

- [ ] **Step 3: Create useAuth composable**

```typescript
// frontend/app/composables/useAuth.ts
interface AuthUser {
  id: string
  name: string
  email: string
  avatar: string
  groups: string[]
  permissions: string[]
}

export function useAuth() {
  const user = useState<AuthUser | null>('auth_user', () => null)
  const { api, clearTokens } = useApi()

  async function fetchMe() {
    try {
      user.value = await api<AuthUser>('/api/auth/me/')
    } catch {
      user.value = null
    }
  }

  function can(permission: string): boolean {
    return user.value?.permissions.includes(permission) ?? false
  }

  function hasGroup(groupName: string): boolean {
    return user.value?.groups.includes(groupName) ?? false
  }

  function logout() {
    clearTokens()
    user.value = null
    navigateTo('/')
  }

  return { user, fetchMe, can, hasGroup, logout }
}
```

- [ ] **Step 4: Create auth middleware**

```typescript
// frontend/app/middleware/auth.global.ts
export default defineNuxtRouteMiddleware((to) => {
  if (to.path === '/' || to.path === '/login') return

  const { getToken } = useApi()
  if (!getToken()) {
    return navigateTo('/')
  }
})
```

- [ ] **Step 5: Update login page to use real JWT**

Update `frontend/app/pages/index.vue` — replace the mock login with real API call:

The login handler should:

```typescript
const { setTokens } = useApi()
const { fetchMe } = useAuth()

async function handleLogin() {
  try {
    const data = await $fetch<{ access: string; refresh: string }>('/api/auth/login/', {
      method: 'POST',
      body: { username: username.value, password: password.value },
    })
    setTokens(data.access, data.refresh)
    await fetchMe()
    navigateTo('/app/dashboard')
  } catch (error) {
    // Show error message
  }
}
```

- [ ] **Step 6: Verify end-to-end login flow**

Start both servers:

```bash
# Terminal 1: Django backend
cd /Users/ck/Git/matrix/devtrack/backend
python manage.py runserver

# Terminal 2: Nuxt frontend
cd /Users/ck/Git/matrix/devtrack/frontend
npm run dev
```

1. Create a superuser: `python manage.py createsuperuser`
2. Run `python manage.py setup_groups`
3. Open `http://localhost:3004`
4. Login with the superuser credentials
5. Verify redirect to dashboard

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): add JWT auth integration — useApi, useAuth, proxy config, login page"
```

---

## Task 9: Frontend Page Migration — Dashboard + Projects + Issues

**Files:**
- Modify: `frontend/app/pages/app/dashboard.vue`
- Modify: `frontend/app/pages/app/projects/index.vue`
- Modify: `frontend/app/pages/app/projects/[id].vue`
- Modify: `frontend/app/pages/app/issues/index.vue`
- Modify: `frontend/app/pages/app/issues/[id].vue`
- Modify: `frontend/app/components/AppSidebar.vue`

This task replaces mock data imports with `useApi()` calls on each page. Each page follows the same pattern:

1. Replace `import { xxx } from '~/data/mock'` with `const { api } = useApi()`
2. Replace static data with `ref()` + `onMounted` fetch
3. Update template bindings as needed

- [ ] **Step 1: Migrate Dashboard page**

Replace mock data with API calls:

```typescript
const { api } = useApi()
const stats = ref(null)
const trends = ref([])
const priorityDist = ref([])
const leaderboard = ref([])
const recentActivity = ref([])

onMounted(async () => {
  const [s, t, p, l, a] = await Promise.all([
    api('/api/dashboard/stats/'),
    api('/api/dashboard/trends/'),
    api('/api/dashboard/priority-distribution/'),
    api('/api/dashboard/developer-leaderboard/'),
    api('/api/dashboard/recent-activity/'),
  ])
  stats.value = s
  trends.value = t
  priorityDist.value = p
  leaderboard.value = l
  recentActivity.value = a
})
```

- [ ] **Step 2: Migrate Projects pages**

Projects list — replace mock with `api('/api/projects/')`.
Project detail — replace mock with `api('/api/projects/${id}/')` and `api('/api/projects/${id}/issues/')`.

- [ ] **Step 3: Migrate Issues pages**

Issues list — replace mock with `api('/api/issues/')`, wire up filter params.
Issue detail — replace mock with `api('/api/issues/${id}/')`.

- [ ] **Step 4: Update AppSidebar with permission-based navigation**

```typescript
const { can } = useAuth()

// Filter nav items by permission
const visibleNavItems = computed(() =>
  navItems.filter(item => {
    if (item.permission) return can(item.permission)
    return true
  })
)
```

Add `permission` field to nav items in `useNavigation.ts`:

```typescript
{ label: '项目概览', icon: '...', to: '/app/dashboard', permission: 'issues.view_dashboard' },
{ label: '项目管理', icon: '...', to: '/app/projects', permission: 'projects.view_project' },
// etc.
```

- [ ] **Step 5: Verify all pages load with real data**

1. Create test data via Django admin or shell
2. Navigate through all pages
3. Verify data displays correctly

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): migrate all pages from mock data to real API endpoints"
```

---

## Task 10: Final Integration Test + Cleanup

- [ ] **Step 1: Run full backend test suite**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
python -m pytest -v --tb=short
```

Expected: All PASS

- [ ] **Step 2: Create admin superuser and seed data**

```bash
python manage.py createsuperuser --username admin --email admin@devtrack.local
python manage.py setup_groups
```

- [ ] **Step 3: Verify full end-to-end flow**

1. Start both servers
2. Login as admin
3. Create a project via UI
4. Add members to project
5. Create issues
6. Verify dashboard stats update
7. Test filters and search on issues page
8. Test batch operations

- [ ] **Step 4: Remove mock data dependency check**

Verify no frontend page still imports from `~/data/mock`. If all pages are migrated, the mock file can be kept as reference but should not be imported.

```bash
cd /Users/ck/Git/matrix/devtrack/frontend
grep -r "data/mock" app/pages/ app/components/
```

Expected: No results (all mock imports removed)

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete backend + frontend integration — DevTrack fully connected"
```
