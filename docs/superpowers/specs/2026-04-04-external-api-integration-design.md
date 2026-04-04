# External API Integration Design

**Date**: 2026-04-04
**GitHub Issue**: #1 — 贷后智能体平台接入需求
**Scope**: Section 5 only (DevTrack side of the integration)

## Overview

Provide a RESTful API for external platforms (starting with 贷后智能体平台) to create issues in DevTrack and query their status. No webhooks — external platforms poll for updates.

## Out of Scope

- Outbound webhooks / status change callbacks
- Retry queues / async job processing
- Auto-assignment rules beyond default assignee per API key
- Frontend API key management page (use Django admin)

---

## 1. Model Changes

### 1.1 Issue Model — New Fields

Add to `apps/issues/models.py`:

```python
source = models.CharField(max_length=50, null=True, blank=True, verbose_name="来源")
source_meta = models.JSONField(null=True, blank=True, verbose_name="来源元数据")
```

- `source`: identifies origin, e.g. `"agent_platform"`. `null` for normal issues created within DevTrack.
- `source_meta`: stores the full external payload. Schema:

```json
{
  "feedback_id": "FB202604040001",
  "reporter": {
    "tenant_id": "T001",
    "tenant_name": "XX催收公司",
    "user_id": "U001",
    "user_name": "张三",
    "contact": "13800138000"
  },
  "context": {
    "page_url": "/case/import",
    "page_title": "案件导入",
    "browser": "Chrome 120.0",
    "os": "Windows 11",
    "resolution": "1920x1080",
    "navigation_path": ["/dashboard", "/case/list", "/case/import"],
    "console_errors": ["TypeError: Cannot read property..."]
  },
  "attachments": [
    {"type": "screenshot", "url": "https://cdn.example.com/fb/screenshot_001.png"},
    {"type": "file", "url": "https://cdn.example.com/fb/error_log.txt"}
  ]
}
```

### 1.2 ExternalAPIKey Model

New model in `apps/settings/models.py`:

```python
class ExternalAPIKey(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称")
    key = models.CharField(max_length=64, unique=True, verbose_name="API Key")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, verbose_name="关联项目")
    default_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="默认负责人"
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True)
```

- Each key binds to a specific project and default assignee.
- `key` is a 64-char random token, generated on save if blank.
- Managed via Django admin.

---

## 2. Authentication

### 2.1 APIKeyAuthentication

New DRF authentication class at `apps/settings/auth.py` (or similar):

- Checks `Authorization: Bearer {api_key}` header.
- Looks up `ExternalAPIKey` where `key` matches and `is_active=True`.
- On match: sets `request.user` to `api_key.default_assignee` and attaches `request.api_key` (the `ExternalAPIKey` instance) for views to access `project`.
- On failure: returns 401.

### 2.2 Permissions

External API views use `AllowAny` for DRF permissions since authentication is fully handled by the API key class. No Django model permissions needed — the API key is the authorization boundary.

---

## 3. API Endpoints

### 3.1 URL Structure

New namespace mounted at `/api/external/`:

```
POST   /api/external/issues/           # Create issue
GET    /api/external/issues/           # List issues (filtered)
GET    /api/external/issues/{id}/      # Get issue detail
```

All endpoints require API key auth.

### 3.2 Create Issue — `POST /api/external/issues/`

**Request body** (follows spec 5.4.1):

```json
{
  "title": "案件导入页面上传Excel后无响应",
  "type": "bug",
  "priority": "P1",
  "description": "上传5MB的Excel文件后页面卡住不动...",
  "module": "case_management",
  "source_feedback_id": "FB202604040001",
  "reporter": {
    "tenant_id": "T001",
    "tenant_name": "XX催收公司",
    "user_id": "U001",
    "user_name": "张三",
    "contact": "13800138000"
  },
  "context": {
    "page_url": "/case/import",
    "page_title": "案件导入",
    "browser": "Chrome 120.0",
    "os": "Windows 11",
    "resolution": "1920x1080",
    "navigation_path": ["/dashboard", "/case/list", "/case/import"],
    "console_errors": ["TypeError: Cannot read property..."]
  },
  "attachments": [
    {"type": "screenshot", "url": "https://cdn.example.com/fb/screenshot_001.png"}
  ]
}
```

**Field mapping logic:**

| Request field | Issue field | Mapping |
|---|---|---|
| `title` | `title` | Direct |
| `type` | `labels` | `bug`/`BUG` → "Bug", `feature`/`功能建议` → "需求", `improvement`/`体验改进` → "优化", else → label as-is |
| `priority` | `priority` | Direct (P0/P1/P2), default P2 if missing |
| `description` | `description` | Direct |
| `module` | `labels` | Appended as additional label |
| `source_feedback_id` | `source_meta.feedback_id` | Packed into JSON |
| `reporter` | `source_meta.reporter` | Packed into JSON |
| `context` | `source_meta.context` | Packed into JSON |
| `attachments` | `source_meta.attachments` | Packed into JSON |

**Auto-set fields:**
- `source` = `"agent_platform"`
- `project` = from `request.api_key.project`
- `assignee` = from `request.api_key.default_assignee`
- `reporter` (FK) = from `request.api_key.default_assignee`
- `status` = `"待处理"`

**Response** (201):

```json
{
  "id": 42,
  "issue_number": "ISS-042",
  "title": "案件导入页面上传Excel后无响应",
  "status": "待处理",
  "priority": "P1",
  "created_at": "2026-04-04T10:00:00Z"
}
```

**Duplicate prevention:** If `source_feedback_id` is provided and an issue with matching `source_meta__feedback_id` already exists, return 409 Conflict with the existing issue's ID.

### 3.3 Query Issue — `GET /api/external/issues/{id}/`

**Response** (200):

```json
{
  "id": 42,
  "issue_number": "ISS-042",
  "title": "案件导入页面上传Excel后无响应",
  "status": "待处理",
  "priority": "P1",
  "assignee": "李四",
  "labels": ["Bug", "case_management"],
  "created_at": "2026-04-04T10:00:00Z",
  "updated_at": "2026-04-04T11:30:00Z",
  "resolved_at": null,
  "source_feedback_id": "FB202604040001"
}
```

Scoped to the API key's project — cannot query issues from other projects.

### 3.4 List Issues — `GET /api/external/issues/`

**Query parameters:**
- `feedback_id` — filter by `source_meta__feedback_id`
- `status` — filter by status
- `priority` — filter by priority
- `page` / `page_size` — pagination (default 20, max 100)

Returns paginated list of issues (same shape as 3.3). Scoped to API key's project and `source="agent_platform"`.

---

## 4. Django Admin

Register `ExternalAPIKey` in `apps/settings/admin.py`:

- List display: `name`, `project`, `default_assignee`, `is_active`, `created_at`
- Key auto-generated on save if blank (using `secrets.token_hex(32)`)
- Read-only display of the key after creation

---

## 5. Frontend Changes

### 5.1 Issue Detail Page

When `source` is not null, display a collapsible "外部来源" section:

- Source name (来源平台)
- Feedback ID (反馈编号)
- Reporter info: name, tenant, contact (报告人信息)
- Context: page URL, browser, OS (上下文信息)
- Attachments as clickable links (附件)

### 5.2 Issue List / Kanban

- External issues show a small "外部" badge/tag to distinguish them from internally-created issues.

### 5.3 No Form Changes

External issues are created via API only. The existing issue create/edit forms don't need `source` or `source_meta` fields.

---

## 6. Testing

- **API key auth**: valid key, invalid key, inactive key, missing header
- **Create issue**: full payload, minimal payload, duplicate `source_feedback_id` (409), type-to-label mapping
- **Query/list**: project scoping, filter by feedback_id/status/priority, pagination
- **Model**: `source` and `source_meta` fields nullable, migration works
