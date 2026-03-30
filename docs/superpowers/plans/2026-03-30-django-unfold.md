# Django Unfold Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default Django admin theme with django-unfold for a modern UI, fully adopting Unfold's base classes across all admin registrations.

**Architecture:** Install django-unfold, configure sidebar navigation with grouped Chinese labels, migrate all 7 admin files to use `unfold.admin.ModelAdmin`/`TabularInline`, and adapt the JsonSchemaWidget template to use Tailwind CSS classes.

**Tech Stack:** Django 5.1+, django-unfold 0.87+, Tailwind CSS (bundled with Unfold)

**Spec:** `docs/superpowers/specs/2026-03-30-django-unfold-design.md`

---

### Task 1: Install django-unfold and configure settings

**Files:**
- Modify: `backend/pyproject.toml:5-18` (add dependency)
- Modify: `backend/config/settings.py:20-41` (INSTALLED_APPS + UNFOLD config)

- [ ] **Step 1: Add django-unfold to pyproject.toml**

In `backend/pyproject.toml`, add `"django-unfold>=0.87"` to the `dependencies` list:

```python
dependencies = [
    "django>=5.1,<6.0",
    "djangorestframework>=3.15,<4.0",
    "djangorestframework-simplejwt>=5.3,<6.0",
    "django-solo>=2.3,<3.0",
    "django-filter>=24.0,<25.0",
    "psycopg[binary]>=3.2,<4.0",
    "django-page-perms",
    "openai>=2.29.0,<3.0",
    "requests>=2.32.5",
    "whitenoise>=6.12.0",
    "boto3>=1.35,<2.0",
    "python-dotenv>=1.0,<2.0",
    "django-unfold>=0.87",
]
```

- [ ] **Step 2: Install the dependency**

Run: `cd backend && uv sync`
Expected: Installs django-unfold and its dependencies successfully.

- [ ] **Step 3: Add "unfold" to INSTALLED_APPS before django.contrib.admin**

In `backend/config/settings.py`, update `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "unfold",
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
    "apps.tools",
    # Packages
    "page_perms",
]
```

- [ ] **Step 4: Add UNFOLD configuration dict with sidebar navigation**

In `backend/config/settings.py`, add the import at the top of the file (after `from datetime import timedelta`):

```python
from django.urls import reverse_lazy
```

Then at the bottom of the file (after `PAGE_PERMS`), add:

```python
UNFOLD = {
    "SITE_TITLE": "DevTrack",
    "SITE_HEADER": "DevTrack 管理后台",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "项目管理",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "项目",
                        "icon": "folder_open",
                        "link": reverse_lazy("admin:projects_project_changelist"),
                    },
                    {
                        "title": "问题",
                        "icon": "bug_report",
                        "link": reverse_lazy("admin:issues_issue_changelist"),
                    },
                    {
                        "title": "活动",
                        "icon": "history",
                        "link": reverse_lazy("admin:issues_activity_changelist"),
                    },
                ],
            },
            {
                "title": "代码仓库",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "仓库",
                        "icon": "source",
                        "link": reverse_lazy("admin:repos_repo_changelist"),
                    },
                    {
                        "title": "GitHub Issues",
                        "icon": "issue",
                        "link": reverse_lazy("admin:repos_githubissue_changelist"),
                    },
                ],
            },
            {
                "title": "AI 配置",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "LLM 配置",
                        "icon": "smart_toy",
                        "link": reverse_lazy("admin:ai_llmconfig_changelist"),
                    },
                    {
                        "title": "提示词",
                        "icon": "description",
                        "link": reverse_lazy("admin:ai_prompt_changelist"),
                    },
                    {
                        "title": "分析记录",
                        "icon": "analytics",
                        "link": reverse_lazy("admin:ai_analysis_changelist"),
                    },
                ],
            },
            {
                "title": "用户与权限",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "用户",
                        "icon": "people",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": "用户组",
                        "icon": "group_work",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": "系统",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "站点设置",
                        "icon": "settings",
                        "link": reverse_lazy("admin:settings_sitesettings_changelist"),
                    },
                    {
                        "title": "附件",
                        "icon": "attach_file",
                        "link": reverse_lazy("admin:tools_attachment_changelist"),
                    },
                ],
            },
        ],
    },
}
```

- [ ] **Step 5: Verify the dev server starts without errors**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/config/settings.py
git commit -m "feat(admin): install django-unfold and configure sidebar navigation"
```

---

### Task 2: Migrate projects admin to Unfold base classes

**Files:**
- Modify: `backend/apps/projects/admin.py`

- [ ] **Step 1: Replace imports and base classes**

Replace the entire file with:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Project, ProjectMember


class ProjectMemberInline(TabularInline):
    model = ProjectMember
    extra = 1


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("name", "status", "created_at")
    inlines = [ProjectMemberInline]
```

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/projects/admin.py
git commit -m "feat(admin): migrate projects admin to Unfold base classes"
```

---

### Task 3: Migrate issues admin to Unfold base classes

**Files:**
- Modify: `backend/apps/issues/admin.py`

- [ ] **Step 1: Replace imports and base classes**

Replace the entire file with:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Issue, Activity


@admin.register(Issue)
class IssueAdmin(ModelAdmin):
    list_display = ("id", "title", "priority", "status", "assignee", "created_at")
    list_filter = ("priority", "status")
    search_fields = ("title",)


@admin.register(Activity)
class ActivityAdmin(ModelAdmin):
    list_display = ("issue", "user", "action", "created_at")
    list_filter = ("action",)
```

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/issues/admin.py
git commit -m "feat(admin): migrate issues admin to Unfold base classes"
```

---

### Task 4: Migrate repos admin to Unfold base classes

**Files:**
- Modify: `backend/apps/repos/admin.py`

- [ ] **Step 1: Replace imports and base classes**

Replace the entire file with:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Repo, GitHubIssue


@admin.register(Repo)
class RepoAdmin(ModelAdmin):
    list_display = ("full_name", "language", "stars", "status", "last_synced_at", "connected_at")
    readonly_fields = ("connected_at", "last_synced_at")


@admin.register(GitHubIssue)
class GitHubIssueAdmin(ModelAdmin):
    list_display = ("repo", "github_id", "title", "state", "synced_at")
    readonly_fields = (
        "repo", "github_id", "title", "body", "state", "labels",
        "assignees", "github_created_at", "github_updated_at",
        "github_closed_at", "synced_at",
    )
    list_filter = ("state", "repo")
    search_fields = ("title",)
```

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/repos/admin.py
git commit -m "feat(admin): migrate repos admin to Unfold base classes"
```

---

### Task 5: Migrate ai admin to Unfold base classes

**Files:**
- Modify: `backend/apps/ai/admin.py`

- [ ] **Step 1: Replace imports and base classes**

Replace the entire file with:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import LLMConfig, Prompt, Analysis


@admin.register(LLMConfig)
class LLMConfigAdmin(ModelAdmin):
    list_display = ("name", "base_url", "supports_json_mode", "is_default", "is_active")
    readonly_fields = ("created_at", "updated_at")
    # api_key absent from list_display to avoid plaintext exposure in list view


@admin.register(Prompt)
class PromptAdmin(ModelAdmin):
    list_display = ("slug", "name", "llm_model", "llm_config", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Analysis)
class AnalysisAdmin(ModelAdmin):
    list_display = ("analysis_type", "triggered_by", "status", "created_at")
    readonly_fields = (
        "input_context", "prompt_snapshot", "raw_response", "parsed_result",
        "data_hash", "created_at", "updated_at",
    )
    list_filter = ("status", "analysis_type", "triggered_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
```

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/ai/admin.py
git commit -m "feat(admin): migrate ai admin to Unfold base classes"
```

---

### Task 6: Migrate tools admin to Unfold base classes

**Files:**
- Modify: `backend/apps/tools/admin.py`

- [ ] **Step 1: Replace imports and base classes**

Replace the entire file with:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(ModelAdmin):
    list_display = ["file_name", "mime_type", "file_size_kb", "uploaded_by", "created_at"]
    list_filter = ["mime_type", "created_at"]
    search_fields = ["file_name", "uploaded_by__name"]
    raw_id_fields = ["uploaded_by"]
    readonly_fields = ["id", "file_key", "file_url", "file_size", "mime_type", "created_at"]

    @admin.display(description="大小 (KB)")
    def file_size_kb(self, obj):
        return f"{obj.file_size // 1024} KB"
```

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/tools/admin.py
git commit -m "feat(admin): migrate tools admin to Unfold base classes"
```

---

### Task 7: Migrate settings admin to Unfold base classes (django-solo)

**Files:**
- Modify: `backend/apps/settings/admin.py`

- [ ] **Step 1: Replace with multiple-inheritance admin class**

Replace the entire file with:

```python
from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin, SingletonModelAdmin):
    pass
```

Note: `ModelAdmin` (Unfold) must come first in MRO so Unfold's templates and styling take precedence. `SingletonModelAdmin` provides the singleton behavior (redirect to change form, no add/delete).

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/settings/admin.py
git commit -m "feat(admin): migrate settings admin to Unfold with django-solo MRO"
```

---

### Task 8: Migrate users admin to Unfold base classes

**Files:**
- Modify: `backend/apps/users/admin.py`

- [ ] **Step 1: Replace imports and base classes**

Replace the entire file with:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from apps.widgets import JsonSchemaWidget
from .models import User

USER_SETTINGS_SCHEMA = {
    "sidebar_auto_collapse": {"type": "boolean", "label": "侧边栏自动折叠", "default": False},
    "issues_view_mode": {"type": "select", "label": "问题视图模式", "choices": ["kanban", "table"], "default": "table"},
    "project_view_mode": {"type": "select", "label": "项目视图模式", "choices": ["kanban", "table"], "default": "kanban"},
    "theme": {"type": "select", "label": "主题", "choices": ["light", "dark", "auto"], "default": "light"},
}


@admin.register(User)
class UserAdmin(ModelAdmin, BaseUserAdmin):
    list_display = ("username", "name", "email", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (("扩展信息", {"fields": ("name", "github_id", "avatar", "settings")}),)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "settings":
            kwargs["widget"] = JsonSchemaWidget(schema=USER_SETTINGS_SCHEMA)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
```

Note: `ModelAdmin` (Unfold) first for styling, `BaseUserAdmin` second for fieldsets/functionality.

- [ ] **Step 2: Verify**

Run: `cd backend && uv run python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/users/admin.py
git commit -m "feat(admin): migrate users admin to Unfold with BaseUserAdmin MRO"
```

---

### Task 9: Adapt JsonSchemaWidget template to Unfold's Tailwind styling

**Files:**
- Modify: `backend/apps/users/templates/widgets/json_schema.html`

- [ ] **Step 1: Replace inline CSS with Tailwind classes**

Replace the entire file with:

```html
<div id="json-widget-{{ widget.json_name }}" class="mt-1">
  {% for field in widget.fields %}
  <div class="flex items-center mb-3 gap-3">
    <label class="min-w-[140px] font-normal text-sm text-gray-500 dark:text-gray-400"
           for="id_{{ widget.json_name }}__{{ field.key }}">
      {{ field.label }}
    </label>

    {% if field.type == "boolean" %}
      <input type="checkbox"
             id="id_{{ widget.json_name }}__{{ field.key }}"
             name="{{ widget.json_name }}__{{ field.key }}"
             {% if field.value %}checked{% endif %}
             data-json-field="{{ field.key }}"
             data-json-type="boolean"
             class="rounded border-gray-300 text-primary-600 shadow-sm focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-900" />

    {% elif field.type == "select" %}
      <select id="id_{{ widget.json_name }}__{{ field.key }}"
              name="{{ widget.json_name }}__{{ field.key }}"
              data-json-field="{{ field.key }}"
              data-json-type="select"
              class="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-gray-200">
        {% for choice in field.choices %}
          <option value="{{ choice }}" {% if field.value == choice %}selected{% endif %}>{{ choice }}</option>
        {% endfor %}
      </select>

    {% elif field.type == "number" %}
      <input type="number"
             id="id_{{ widget.json_name }}__{{ field.key }}"
             name="{{ widget.json_name }}__{{ field.key }}"
             value="{{ field.value }}"
             data-json-field="{{ field.key }}"
             data-json-type="number"
             class="border border-gray-300 rounded-md px-3 py-2 w-[120px] text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-gray-200" />

    {% else %}
      <input type="text"
             id="id_{{ widget.json_name }}__{{ field.key }}"
             name="{{ widget.json_name }}__{{ field.key }}"
             value="{{ field.value }}"
             data-json-field="{{ field.key }}"
             data-json-type="text"
             class="border border-gray-300 rounded-md px-3 py-2 w-[240px] text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-gray-200" />
    {% endif %}
  </div>
  {% endfor %}

  <input type="hidden" name="{{ widget.json_name }}" id="id_{{ widget.json_name }}" value="" />
</div>

<script>
(function() {
  var container = document.getElementById('json-widget-{{ widget.json_name }}');
  var hidden = document.getElementById('id_{{ widget.json_name }}');

  function collect() {
    var result = {};
    var inputs = container.querySelectorAll('[data-json-field]');
    for (var i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      var key = el.getAttribute('data-json-field');
      var type = el.getAttribute('data-json-type');
      if (type === 'boolean') {
        result[key] = el.checked;
      } else if (type === 'number') {
        result[key] = el.value ? parseFloat(el.value) : 0;
      } else {
        result[key] = el.value;
      }
    }
    hidden.value = JSON.stringify(result);
  }

  // 表单提交前组装 JSON
  var form = container.closest('form');
  if (form) {
    form.addEventListener('submit', collect);
  }

  // 初始化隐藏字段
  collect();
})();
</script>
```

Changes: all inline `style` attributes replaced with Tailwind utility classes. Dark mode variants added (`dark:` prefix). JavaScript unchanged.

- [ ] **Step 2: Verify visually**

Run: `cd backend && uv run python manage.py runserver`
Navigate to `/api/admin/` → Users → edit a user → scroll to 扩展信息 section. Verify the settings fields render with proper Unfold-consistent styling in both light and dark modes.

- [ ] **Step 3: Commit**

```bash
git add backend/apps/users/templates/widgets/json_schema.html
git commit -m "feat(admin): adapt JsonSchemaWidget template to Unfold Tailwind styling"
```

---

### Task 10: Collect static files and smoke test

- [ ] **Step 1: Collect static files**

Run: `cd backend && uv run python manage.py collectstatic --noinput`
Expected: Completes without errors. Unfold's static assets are collected.

- [ ] **Step 2: Run existing tests**

Run: `cd backend && uv run pytest`
Expected: All existing tests pass. Admin class changes don't affect API tests.

- [ ] **Step 3: Smoke test the admin UI**

Run: `cd backend && uv run python manage.py runserver`
Visit `/api/admin/` and verify:
- Unfold theme is applied (modern UI, not default Django admin)
- Sidebar shows 5 navigation groups with Chinese labels
- Each group expands/collapses and links to the correct model changelist
- All model list views load without errors
- User edit form shows the JsonSchemaWidget with Tailwind-styled fields
- SiteSettings still redirects to the singleton edit form
- Analysis model is still read-only (no add/change buttons)

- [ ] **Step 4: Commit any remaining changes**

```bash
git add -A
git commit -m "chore(admin): collect static files for Unfold theme"
```
