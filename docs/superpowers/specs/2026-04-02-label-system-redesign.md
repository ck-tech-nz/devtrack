# Label System Redesign

**Date:** 2026-04-02
**Approach:** Popover picker + modal management (Approach B)

## Overview

Redesign the label/tag system from simple string arrays to rich objects with colors and descriptions. Replace the inline toggle buttons on the issue detail page with a GitHub-style label picker popover, and add a modal for label CRUD.

## Backend Changes

### 1. SiteSettings Label Format Change

**Current format** (`backend/apps/settings/models.py:18-21`):
```json
["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"]
```

**New format:**
```json
{
  "前端": {"foreground": "#ffffff", "background": "#0075ca", "description": "前端相关问题"},
  "后端": {"foreground": "#ffffff", "background": "#e99695", "description": "后端相关问题"},
  "Bug": {"foreground": "#ffffff", "background": "#d73a4a", "description": "程序错误"}
}
```

Each label key maps to an object with:
- `foreground` — hex color for text on the pill
- `background` — hex color for the pill background / dot color
- `description` — short description shown in the picker

### 2. Data Migration

A data migration converts the existing string array to the new dict format:
- Assigns colors from a preset palette (cycling through ~10 distinct colors)
- Sets empty descriptions
- Preserves all existing label names as keys

### 3. Default Labels Update

Update `default_labels()` in `backend/apps/settings/models.py` to return the new dict format with sensible default colors.

### 4. Validation Changes

**`backend/apps/issues/serializers.py:105-111` — `validate_labels()`:**
Change `set(site_settings.labels)` to `set(site_settings.labels.keys())` since labels is now a dict.

**Issue.labels field** (`backend/apps/issues/models.py:33`): No change — remains a JSONField storing `["前端", "Bug"]` string arrays. Only the SiteSettings shape changes.

**Label filter** (`backend/apps/issues/views.py:68-70`): No change — `qs.filter(labels__contains=[labels])` still works since Issue.labels is still a string array.

### 5. New API Endpoint: Label Management

**`PATCH /api/settings/labels/`** — Updates the labels dict in SiteSettings.

- **Permission:** `IsAuthenticated` (matches existing settings endpoint)
- **Request body:** Full labels dict (replaces entire labels field)
- **Validation:** Each value must have `foreground`, `background`, `description` keys; colors must be valid hex
- **Response:** Updated labels dict

Add a new view `LabelSettingsView` in `backend/apps/settings/views.py` and register in `backend/apps/settings/urls.py`.

## Frontend Changes

### 1. Label Data Type

`labelItems` changes from `ref<string[]>` to `ref<Record<string, { foreground: string; background: string; description: string }>>`.

Derive label names via `Object.keys(labelItems.value)`.

### 2. Issue Detail Page — Label Picker Popover

**Location:** `frontend/app/pages/app/issues/[id].vue`, replaces lines 174-185.

**Header row:**
- Left: "标签" label text
- Right: gear icon (`i-heroicons-cog-6-tooth`)
- Clicking the row toggles a `UPopover`

**Popover content:**
- Title: "应用标签"
- Search input with placeholder "筛选标签"
- Scrollable list (max-h-64), each row contains:
  - Checkbox (checked if label is in `form.labels`)
  - Color dot (circle, colored with `background`)
  - Label name (bold)
  - Description (smaller, gray text below name)
- Clicking a row toggles the label on the issue and auto-saves
- Footer: "编辑标签" link that closes the popover and opens the management modal

**Applied labels display:**
Below the header row, show applied labels as colored pills using `foreground`/`background` from settings. If no labels applied, show subtle "无标签" placeholder.

### 3. Label Management Modal

**Trigger:** "编辑标签" link in the picker popover footer.

**Modal content (`UModal`):**
- Header: "管理标签"
- "新增标签" button at top
- List of all labels, each row shows:
  - Color pill preview (name rendered with foreground/background)
  - Description text
  - Edit button (pencil icon)
- **Edit mode** (inline, expands the row):
  - Name input
  - Description input
  - Background color input (text input with hex value + color preview swatch)
  - Foreground color input (text input with hex value + color preview swatch)
  - Save / Cancel buttons per row
- **Add new label:**
  - Same fields as edit mode, appended at top
- **Delete:**
  - Small trash icon per label, with confirmation
  - Deleting a label removes it from settings; existing issues that have it will retain the string but it won't appear in the picker

**Save behavior:**
- Each add/edit/delete immediately calls `PATCH /api/settings/labels/` with the full updated dict
- After save, refreshes `labelItems` so the picker reflects changes

### 4. Issues List Page Impact

**`frontend/app/pages/app/issues/index.vue`:**
- `labelOptions` (line 294): Change from `settingsData.labels` (string[]) to `Object.keys(settingsData.labels)`
- Create-issue modal's `USelectMenu` continues to work with string array of label names
- Label display in the issue table: optionally render colored pills using settings lookup (nice-to-have, not required for MVP)

## File Change Summary

| File | Change |
|------|--------|
| `backend/apps/settings/models.py` | Update `default_labels()` to return dict format |
| `backend/apps/settings/migrations/XXXX_*.py` | Data migration: array → dict |
| `backend/apps/settings/serializers.py` | Add `LabelSettingsSerializer` with validation |
| `backend/apps/settings/views.py` | Add `LabelSettingsView` (PATCH endpoint) |
| `backend/apps/settings/urls.py` | Register `labels/` route |
| `backend/apps/issues/serializers.py` | Update `validate_labels` to use `.keys()` |
| `frontend/app/pages/app/issues/[id].vue` | Replace label toggle buttons with picker popover + management modal |
| `frontend/app/pages/app/issues/index.vue` | Update `labelOptions` derivation from dict |
