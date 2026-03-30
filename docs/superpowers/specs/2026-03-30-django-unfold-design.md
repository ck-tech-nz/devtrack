# Django Unfold Integration — Design Spec

**Date:** 2026-03-30
**Goal:** Replace the default Django admin theme with django-unfold for a modern UI, fully adopting Unfold's base classes and adapting all existing customizations.
**Approach:** A — Theme + Full Class Migration (visual upgrade, no dashboard or enhanced features yet; can graduate to Approach C later).

## 1. Installation & Settings

- Add `django-unfold` to `pyproject.toml` dependencies.
- In `INSTALLED_APPS`, place `"unfold"` **before** `"django.contrib.admin"` (required for Unfold's template overrides to take effect).
- Add an `UNFOLD` configuration dict in `settings.py` with:
  - `SITE_TITLE` and `SITE_HEADER` in Chinese
  - `SIDEBAR` navigation config (see Section 3)
  - Default theme colors (can be customized later)

## 2. Admin Class Migration

All 7 admin files (`users`, `projects`, `issues`, `repos`, `settings`, `ai`, `tools`) switch base class imports:

| Django default | Unfold replacement |
|---|---|
| `django.contrib.admin.ModelAdmin` | `unfold.admin.ModelAdmin` |
| `django.contrib.admin.TabularInline` | `unfold.admin.TabularInline` |
| `django.contrib.admin.StackedInline` | `unfold.admin.StackedInline` |

### Special cases

- **`SiteSettingsAdmin`** — Uses `django-solo`'s `SingletonModelAdmin`. Use multiple inheritance with Unfold first: `class SiteSettingsAdmin(ModelAdmin, SingletonModelAdmin)`.
- **`UserAdmin`** — Extends `BaseUserAdmin` from `django.contrib.auth.admin`. Use `class UserAdmin(ModelAdmin, BaseUserAdmin)` — Unfold first for styling, `BaseUserAdmin` for fieldsets/functionality.
- **`AnalysisAdmin`** — Already read-only via custom `has_add_permission`/`has_change_permission` returning False. No behavioral changes needed, just the base class swap.

### What stays the same

All existing `list_display`, `list_filter`, `search_fields`, `readonly_fields`, `raw_id_fields`, inline configurations, and custom permissions remain unchanged.

## 3. Sidebar Navigation Grouping

Sidebar groups, ordered by usage frequency:

```
项目管理 (Project Management)
  ├── 项目 (Projects)          → projects.project
  ├── 问题 (Issues)            → issues.issue
  └── 活动 (Activity)          → issues.activity

代码仓库 (Code Repos)
  ├── 仓库 (Repos)             → repos.repo
  └── GitHub Issues            → repos.githubissue

AI 配置 (AI Configuration)
  ├── LLM 配置 (LLM Config)    → ai.llmconfig
  ├── 提示词 (Prompts)         → ai.prompt
  └── 分析记录 (Analysis)      → ai.analysis

用户与权限 (Users & Permissions)
  ├── 用户 (Users)             → users.user
  └── 用户组 (Groups)          → auth.group

系统 (System)
  ├── 站点设置 (Site Settings)  → settings.sitesettings
  └── 附件 (Attachments)       → tools.attachment
```

Configured via the `UNFOLD["SIDEBAR"]` setting using navigation items that point to model admin URLs.

## 4. JsonSchemaWidget Template Adaptation

**File:** `backend/apps/users/templates/widgets/json_schema.html`

- Replace inline CSS styles with Unfold's Tailwind utility classes (`border`, `rounded-md`, `px-3`, `py-2`, `text-sm`, etc.) to match Unfold's form input styling.
- Adapt checkbox, select, and text input elements to visually blend with the rest of the admin.
- Keep the existing client-side JavaScript for JSON serialization — no changes needed.
- No changes to the Python widget class in `backend/apps/widgets.py`.

## Out of Scope

- Admin dashboard page (Approach B)
- Unfold display decorators, action confirmations, enhanced filters (Approach C)
- These can be layered on after evaluating the base integration.

## Files Affected

| File | Change |
|---|---|
| `backend/pyproject.toml` | Add `django-unfold` dependency |
| `backend/config/settings.py` | Add `"unfold"` to INSTALLED_APPS, add `UNFOLD` config dict |
| `backend/apps/users/admin.py` | Swap to Unfold base classes (ModelAdmin + BaseUserAdmin) |
| `backend/apps/projects/admin.py` | Swap ModelAdmin + TabularInline |
| `backend/apps/issues/admin.py` | Swap ModelAdmin |
| `backend/apps/repos/admin.py` | Swap ModelAdmin |
| `backend/apps/settings/admin.py` | Swap ModelAdmin + SingletonModelAdmin MRO |
| `backend/apps/ai/admin.py` | Swap ModelAdmin |
| `backend/apps/tools/admin.py` | Swap ModelAdmin |
| `backend/apps/users/templates/widgets/json_schema.html` | Replace inline CSS with Tailwind classes |
