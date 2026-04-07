# Issue created_by / reporter Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate the Issue model's "who created the record" (FK) from "who reported the problem" (free-text), and add `updated_by` audit tracking.

**Architecture:** Rename the `reporter` FK to `created_by`, add `updated_by` FK for audit trail, add `reporter` CharField for the actual reporter's name. External API auto-fills `reporter` from `source_meta.reporter.user_name`. Frontend pre-fills reporter with current user's display name.

**Tech Stack:** Django 5, DRF, Nuxt 4 (Vue 3), PostgreSQL

---

### Task 1: Migration — Rename reporter FK, add new fields

**Files:**
- Create: `backend/apps/issues/migrations/0003_rename_reporter_created_by.py`

- [ ] **Step 1: Create the migration file**

```python
# backend/apps/issues/migrations/0003_rename_reporter_created_by.py
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("issues", "0002_issue_source_issue_source_meta"),
    ]

    operations = [
        migrations.RenameField(
            model_name="issue",
            old_name="reporter",
            new_name="created_by",
        ),
        migrations.AddField(
            model_name="issue",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updated_issues",
                to=settings.AUTH_USER_MODEL,
                verbose_name="更新人",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="reporter",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="提出人",
            ),
        ),
    ]
```

- [ ] **Step 2: Run the migration**

Run: `cd backend && uv run python manage.py migrate issues`
Expected: `Applying issues.0003_rename_reporter_created_by... OK`

- [ ] **Step 3: Commit**

```bash
git add backend/apps/issues/migrations/0003_rename_reporter_created_by.py
git commit -m "feat(issues): add migration to rename reporter FK to created_by, add updated_by and reporter CharField"
```

---

### Task 2: Update Issue model

**Files:**
- Modify: `backend/apps/issues/models.py:34-41`

- [ ] **Step 1: Update the model fields**

Replace lines 34-41 in `backend/apps/issues/models.py`. Change the `reporter` FK to `created_by`, and add `updated_by` FK and `reporter` CharField:

```python
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_issues", verbose_name="创建人",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_issues", verbose_name="负责人",
    )
    helpers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="helped_issues",
        verbose_name="协助人",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="updated_issues", verbose_name="更新人",
    )
    reporter = models.CharField(max_length=100, blank=True, default="", verbose_name="提出人")
```

- [ ] **Step 2: Verify migration state is clean**

Run: `cd backend && uv run python manage.py makemigrations --check`
Expected: `No changes detected` (our hand-written migration already covers this)

- [ ] **Step 3: Commit**

```bash
git add backend/apps/issues/models.py
git commit -m "feat(issues): update Issue model — created_by FK, updated_by FK, reporter CharField"
```

---

### Task 3: Update serializers

**Files:**
- Modify: `backend/apps/issues/serializers.py:50-78` (IssueListSerializer)
- Modify: `backend/apps/issues/serializers.py:102-163` (IssueCreateUpdateSerializer)

- [ ] **Step 1: Update IssueListSerializer**

Replace the `IssueListSerializer` class (lines 50-78) with:

```python
class IssueListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    assignee_name = serializers.CharField(source="assignee.name", read_only=True, default=None)
    helpers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    helpers_names = serializers.SerializerMethodField()
    resolution_hours = serializers.SerializerMethodField()
    github_issues = GitHubIssueLinkSerializer(many=True, read_only=True)
    ai_cause = serializers.CharField(read_only=True, default='')
    ai_solution = serializers.CharField(read_only=True, default='')

    class Meta:
        model = Issue
        fields = [
            "id", "project", "repo", "title", "priority",
            "status", "labels", "reporter",
            "created_by", "created_by_name",
            "updated_by", "updated_by_name",
            "assignee", "assignee_name", "helpers", "helpers_names", "remark", "cause", "solution",
            "ai_cause", "ai_solution",
            "resolution_hours", "created_at", "updated_at", "github_issues",
            "estimated_completion", "source",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.name or obj.created_by.username
        return None

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.name or obj.updated_by.username
        return None

    def get_helpers_names(self, obj):
        return [u.name or u.username for u in obj.helpers.all()]

    def get_resolution_hours(self, obj):
        if obj.resolved_at and obj.created_at:
            delta = obj.resolved_at - obj.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None
```

- [ ] **Step 2: Update IssueCreateUpdateSerializer fields and methods**

In the `IssueCreateUpdateSerializer.Meta.fields` list (line 112-116), add `"reporter"` to the writable fields:

```python
    class Meta:
        model = Issue
        fields = [
            "id", "project", "repo", "title", "description", "priority", "status",
            "labels", "assignee", "helpers", "reporter", "remark", "estimated_completion",
            "actual_hours", "cause", "solution", "attachment_ids",
        ]
        read_only_fields = ["id"]
```

In the `create()` method (line 140-163), change `validated_data["reporter"]` to `validated_data["created_by"]`:

```python
    def create(self, validated_data):
        helpers = validated_data.pop("helpers", [])
        attachment_ids = validated_data.pop("attachment_ids", [])
        validated_data["created_by"] = self.context["request"].user
        issue = super().create(validated_data)
        if helpers:
            issue.helpers.set(helpers)
        Activity.objects.create(
            user=self.context["request"].user,
            issue=issue,
            action="created",
        )
        if attachment_ids:
            atts = Attachment.objects.filter(
                id__in=attachment_ids, uploaded_by=self.context["request"].user,
            )
            issue.attachments.add(*atts)
        create_mention_notifications(
            issue=issue,
            old_description="",
            new_description=issue.description,
            actor=self.context["request"].user,
        )
        return issue
```

In the `update()` method (line 165-201), add `updated_by` tracking:

```python
    def update(self, instance, validated_data):
        old_description = instance.description
        helpers = validated_data.pop("helpers", None)
        user = self.context["request"].user
        old_status = instance.status
        old_assignee = instance.assignee_id
        validated_data["updated_by"] = user
        issue = super().update(instance, validated_data)
        if helpers is not None:
            issue.helpers.set(helpers)

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
        if "description" in validated_data:
            create_mention_notifications(
                issue=issue,
                old_description=old_description,
                new_description=issue.description,
                actor=user,
            )
        return issue
```

- [ ] **Step 3: Run existing tests to check for breakage**

Run: `cd backend && uv run pytest tests/test_issues.py -x -q`
Expected: Some tests will fail because factories and test assertions still use `reporter=`. That's expected — we'll fix them in Task 5.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/issues/serializers.py
git commit -m "feat(issues): update serializers — created_by_name, updated_by, reporter CharField"
```

---

### Task 4: Update views, admin, and external API

**Files:**
- Modify: `backend/apps/issues/views.py:53,78`
- Modify: `backend/apps/issues/admin.py:8`
- Modify: `backend/apps/external/views.py:56-66`

- [ ] **Step 1: Update views.py select_related calls**

In `backend/apps/issues/views.py`, change both `select_related("reporter", "assignee")` calls:

Line 53:
```python
    queryset = Issue.objects.select_related("created_by", "assignee").prefetch_related("github_issues__repo")
```

Line 78:
```python
    queryset = Issue.objects.select_related("created_by", "assignee").prefetch_related("attachments")
```

- [ ] **Step 2: Update admin.py**

In `backend/apps/issues/admin.py` line 8, add `created_by` to `list_display`:

```python
    list_display = ("id", "title", "priority", "status", "assignee", "created_by", "created_at")
```

- [ ] **Step 3: Update external/views.py issue creation**

In `backend/apps/external/views.py` lines 56-66, update the `Issue.objects.create()` call to use `created_by` and auto-populate `reporter` from the payload:

```python
        reporter_name = ""
        if data.get("reporter") and isinstance(data["reporter"], dict):
            reporter_name = data["reporter"].get("user_name", "")

        issue = Issue.objects.create(
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", "P2"),
            labels=data.get("_labels", []),
            status="待处理",
            source="agent_platform",
            source_meta=source_meta or None,
            project=request.api_key.project,
            created_by=request.api_key.default_assignee,
            reporter=reporter_name,
        )
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/issues/views.py backend/apps/issues/admin.py backend/apps/external/views.py
git commit -m "feat(issues): update views, admin, external API for created_by rename"
```

---

### Task 5: Update factories and tests

**Files:**
- Modify: `backend/tests/factories.py:77`
- Modify: `backend/tests/test_issues.py:196`
- Modify: `backend/tests/test_external_api.py:178-179`
- Modify: `backend/tests/test_notifications.py:129,146,160`

- [ ] **Step 1: Update IssueFactory**

In `backend/tests/factories.py` line 77, rename `reporter` to `created_by`:

```python
    created_by = factory.SubFactory(UserFactory)
```

- [ ] **Step 2: Update test_issues.py**

In `backend/tests/test_issues.py` line 196, change `reporter=auth_user` to `created_by=auth_user`:

```python
        issue = IssueFactory(created_by=auth_user, description="原始描述")
```

- [ ] **Step 3: Update test_external_api.py**

In `backend/tests/test_external_api.py` line 178-179, update the assertions:

```python
        assert issue.created_by == api_key_obj.default_assignee
        assert issue.reporter == "张三"
```

(The `reporter` is now a CharField that should have been auto-populated from the payload's `reporter.user_name`.)

- [ ] **Step 4: Update test_notifications.py**

In `backend/tests/test_notifications.py`, change all `reporter=auth_user` to `created_by=auth_user` (lines 129, 146, 160):

Line 129:
```python
        issue = IssueFactory(created_by=auth_user)
```

Line 146:
```python
        issue = IssueFactory(created_by=auth_user)
```

Line 160:
```python
        issue = IssueFactory(created_by=auth_user)
```

- [ ] **Step 5: Run all tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/tests/factories.py backend/tests/test_issues.py backend/tests/test_external_api.py backend/tests/test_notifications.py
git commit -m "test(issues): update factories and tests for created_by rename"
```

---

### Task 6: Frontend — Issue list page

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

- [ ] **Step 1: Add reporter input to create modal**

In the create modal template, after the assignee row (around line 93), add a reporter input in the same grid:

Find this block (lines 85-94):
```html
            <div class="form-grid-2">
              <div class="form-row">
                <label>标签</label>
                <USelectMenu v-model="newIssue.labels" :items="labelOptions" multiple placeholder="选择标签" />
              </div>
              <div class="form-row">
                <label>负责人</label>
                <USelect v-model="newIssue.assignee" :items="createAssigneeOptions" placeholder="选择负责人" value-key="value" />
              </div>
            </div>
```

Replace with:
```html
            <div class="form-grid-2">
              <div class="form-row">
                <label>标签</label>
                <USelectMenu v-model="newIssue.labels" :items="labelOptions" multiple placeholder="选择标签" />
              </div>
              <div class="form-row">
                <label>负责人</label>
                <USelect v-model="newIssue.assignee" :items="createAssigneeOptions" placeholder="选择负责人" value-key="value" />
              </div>
            </div>
            <div class="form-row">
              <label>提出人</label>
              <UInput v-model="newIssue.reporter" placeholder="提出人姓名" />
            </div>
```

- [ ] **Step 2: Update newIssue state to include reporter**

In the `<script setup>` section, update `newIssue` ref (around line 312) to include `reporter`:

```typescript
const newIssue = ref({
  project: '',
  title: '',
  description: '',
  priority: 'P2',
  status: '待处理',
  labels: [] as string[],
  assignee: defaultAssignee.value,
  reporter: user.value?.name || '',
  repo: null as string | null,
})
```

Update the `closeCreateModal` function reset (around line 356):
```typescript
  newIssue.value = { project: '', title: '', description: '', priority: 'P2', status: '待处理', labels: [], assignee: defaultAssignee.value, reporter: user.value?.name || '', repo: null }
```

Update the `handleCreateIssue` function reset (around line 386):
```typescript
    newIssue.value = { project: '', title: '', description: '', priority: 'P2', status: '待处理', labels: [], assignee: defaultAssignee.value, reporter: user.value?.name || '', repo: null }
```

- [ ] **Step 3: Send reporter in create request**

In `handleCreateIssue`, add reporter to the body (around line 383, after the repo line):

```typescript
    if (newIssue.value.reporter) body.reporter = newIssue.value.reporter
```

- [ ] **Step 4: Update table column and cell template**

Update the column definition (around line 419) — change `reporter_name` to `reporter`:
```typescript
    { accessorKey: 'reporter', header: '提出人' },
```

Update the cell template (around lines 220-222) — change `reporter_name` to show `reporter` with fallback to `created_by_name`:
```html
        <template #reporter-cell="{ row }">
          <span class="block truncate" :title="row.original.reporter || row.original.created_by_name">{{ row.original.reporter || row.original.created_by_name || '-' }}</span>
        </template>
```

Remove the old `reporter_name-cell` template if it exists.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/pages/app/issues/index.vue
git commit -m "feat(issues): update issue list page — reporter input, created_by_name display"
```

---

### Task 7: Frontend — Issue detail page

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Update the 信息 section**

In the detail page (around line 237-238), update the 提出人 display to use `reporter` with fallback to `created_by_name`:

```html
            <div class="text-sm">
              <span class="text-gray-400 dark:text-gray-500">提出人</span>
              <p class="text-gray-900 dark:text-gray-100 mt-0.5">{{ issue.reporter || issue.created_by_name || '-' }}</p>
            </div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "feat(issues): update issue detail page — reporter with created_by_name fallback"
```

---

### Task 8: Update mock data

**Files:**
- Modify: `frontend/app/data/mock.ts`

- [ ] **Step 1: Update mock data field names**

This file uses `reporter` as a mock user ID field. Since the real `reporter` field is now a string name, update references as appropriate. The mock data isn't used in production but should stay consistent.

No structural change needed — the mock `reporter` field already holds a string value, which aligns with the new CharField.

- [ ] **Step 2: Commit (if changes made)**

Skip this commit if no changes are needed.

---

### Task 9: Final verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass

- [ ] **Step 2: Run frontend type check**

Run: `cd frontend && npx nuxi typecheck`
Expected: No type errors related to the changes

- [ ] **Step 3: Verify migration applies cleanly on fresh DB**

Run: `cd backend && uv run python manage.py migrate --run-syncdb`
Expected: All migrations apply without error

- [ ] **Step 4: Final commit (if any remaining changes)**

```bash
git add -A
git commit -m "chore(issues): final cleanup for created_by/reporter refactor"
```
