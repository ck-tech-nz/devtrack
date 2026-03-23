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

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

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
    "apps.repos",
    "apps.ai",
    # Packages
    "page_perms",
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
        "NAME": os.environ.get("DB_NAME", "devtrack"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "25432"),
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

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

# Page permissions configuration
PAGE_PERMS = {
    "PROTECTED_PATHS": ["/app/permissions"],
    "SEED_ROUTES": [
        {"path": "/app/issues", "label": "问题跟踪", "icon": "i-heroicons-bug-ant", "permission": "issues.view_issue", "sort_order": 0},
        {"path": "/app/dashboard", "label": "项目概览", "icon": "i-heroicons-squares-2x2", "permission": "issues.view_dashboard", "sort_order": 1},
        {"path": "/app/projects", "label": "项目管理", "icon": "i-heroicons-folder-open", "permission": "projects.view_project", "sort_order": 2},
        {"path": "/app/repos", "label": "GitHub 仓库", "icon": "i-heroicons-code-bracket", "permission": "repos.view_repo", "sort_order": 3, "meta": {"serviceKey": "github"}},
        {"path": "/app/ai-insights", "label": "AI 洞察", "icon": "i-heroicons-cpu-chip", "permission": "ai.view_analysis", "sort_order": 4, "meta": {"serviceKey": "ai"}},
        {"path": "/app/users", "label": "用户管理", "icon": "i-heroicons-users", "permission": "users.view_user", "sort_order": 5},
        {"path": "/app/permissions", "label": "权限管理", "icon": "i-heroicons-shield-check", "permission": None, "sort_order": 99, "meta": {"superuserOnly": True}},
    ],
    "SEED_GROUPS": {
        "管理员": {"apps": ["projects", "issues", "settings", "repos", "ai", "users"]},
        "开发者": {"permissions": ["view_project", "view_issue", "add_issue", "change_issue", "view_activity", "view_dashboard", "view_analysis", "add_analysis"]},
        "产品经理": {"inherit": "开发者", "permissions": ["add_project", "change_project", "manage_project_members"]},
        "只读成员": {"permissions_startswith": ["view_"]},
    },
}
