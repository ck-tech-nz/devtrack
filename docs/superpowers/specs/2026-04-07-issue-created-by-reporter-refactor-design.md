# Issue Model: Separate created_by from reporter

**Date:** 2026-04-07
**Status:** Approved

## Problem

The Issue model's `reporter` ForeignKey conflates two concepts:
1. **Who created the record in the system** — the Django user or API key owner
2. **Who actually reported the problem** — may be a different person entirely

For external API issues, the API key owner becomes `reporter`, but the real reporter's name is buried in `source_meta.reporter.user_name`. This makes it impossible to display or query the actual reporter cleanly.

## Design

### Model Changes (Issue)

**Rename:** `reporter` FK → `created_by` FK
```python
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    related_name="created_issues", verbose_name="创建人",
)
```

**Add:** `updated_by` FK — set on every update via serializer
```python
updated_by = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    related_name="updated_issues", verbose_name="更新人",
)
```

**Add:** `reporter` CharField — free-text name of the person who reported the problem
```python
reporter = models.CharField(max_length=100, blank=True, default="", verbose_name="提出人")
```

Existing `created_at` and `updated_at` fields are unchanged.

### Migration Strategy

Single migration, 3 operations in order:

1. `RenameField` — `reporter` → `created_by` (preserves existing FK data)
2. `AddField` — `updated_by` (null=True, blank=True)
3. `AddField` — `reporter` CharField (blank=True, default="")

No data migration needed.

### Serializer Changes

**IssueListSerializer** (read):
- Rename `reporter_name` → `created_by_name` (SerializerMethodField, reads `created_by.name`)
- Add `updated_by` (FK id), `updated_by_name` (SerializerMethodField)
- Add `reporter` (CharField, direct field)
- The `get_created_by_name` method no longer needs the `source_meta` fallback (that was a temporary fix)

**IssueDetailSerializer**: inherits from IssueListSerializer, no extra changes.

**IssueCreateUpdateSerializer** (write):
- Add `reporter` to writable fields
- `create()`: set `created_by = request.user`
- `update()`: set `updated_by = request.user` on every update

### External API Changes

**external/views.py** — Issue creation:
- `created_by = request.api_key.default_assignee` (renamed from `reporter`)
- Auto-populate `reporter` (CharField) from `data["reporter"]["user_name"]` when present in payload

**external/serializers.py** — Response serializer:
- Update field references from `reporter` FK to `created_by`

### Frontend Changes

**issues/index.vue** (list page):
- Table column `提出人` displays `reporter` (CharField) with fallback to `created_by_name`
- Create modal: add `reporter` text input field, pre-filled with current user's display name (option C)
- User can clear or change before submitting

**issues/[id].vue** (detail page):
- Display `reporter` with fallback to `created_by_name`
- Show `created_by_name` separately as 创建人 metadata

### Admin Changes

**issues/admin.py**: Update `list_display` — replace `reporter` reference, optionally add `created_by`.

### Test & Factory Changes

**factories.py**: Rename `reporter = factory.SubFactory(UserFactory)` → `created_by = factory.SubFactory(UserFactory)`

**test_issues.py, test_external_api.py, test_notifications.py**: Update all `reporter=` keyword args to `created_by=`, update assertions for the new `reporter` CharField and `updated_by` field.

## Full Change Map

| Layer | File | Change |
|-------|------|--------|
| Model | `apps/issues/models.py` | Rename FK, add 2 fields |
| Migration | `apps/issues/migrations/000X_*` | RenameField + 2 AddField |
| Serializers | `apps/issues/serializers.py` | Rename refs, add new fields, set `updated_by` on update |
| Views | `apps/issues/views.py` | Update `select_related` to use `created_by` |
| Admin | `apps/issues/admin.py` | Update `list_display` |
| External views | `apps/external/views.py` | `created_by=`, auto-fill `reporter` from payload |
| External serializer | `apps/external/serializers.py` | Update response fields |
| Factories | `tests/factories.py` | Rename field |
| Tests | `test_issues.py`, `test_external_api.py`, `test_notifications.py` | Update field references |
| Frontend list | `pages/app/issues/index.vue` | Column update, add reporter input to create modal |
| Frontend detail | `pages/app/issues/[id].vue` | Display reporter with fallback |
| Mock data | `data/mock.ts` | Update field names |

## Not Changed

- `assignee` / `assignee_name` — unrelated, no change
- `source_meta.reporter` — kept as-is in external API payloads for backward compatibility
- Dashboard / AI services — these query by `assignee`, not `reporter`
- `created_at` / `updated_at` — already exist, no change
