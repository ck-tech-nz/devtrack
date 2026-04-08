# Issue Soft Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow admins to soft-delete issues (single + bulk) with `is_deleted` flag instead of hard delete.

**Architecture:** Add `is_deleted` + `deleted_at` fields to Issue model. Use a custom manager to exclude deleted issues by default so all existing queries work unchanged. Override `perform_destroy` on the detail view. Add `"delete"` action to batch update. Frontend adds delete button on detail page and batch delete button on list page, both behind `issues.delete_issue` permission.

**Tech Stack:** Django, DRF, Nuxt 3, Nuxt UI

---

### Task 1: Add soft delete fields to Issue model

**Files:**
- Modify: `backend/apps/issues/models.py:12-67`

- [ ] **Step 1: Add custom manager and fields to Issue model**

In `backend/apps/issues/models.py`, add a custom manager that excludes deleted issues, and add `is_deleted` + `deleted_at` fields:

```python
class IssueManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Issue(models.Model):
    # ... existing fields ...
    is_deleted = models.BooleanField(default=False, verbose_name="已删除")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="删除时间")

    objects = IssueManager()
    all_objects = models.Manager()

    class Meta:
        # ... existing meta unchanged ...
```

Add `is_deleted` after `source_meta` (line 62), and `deleted_at` after `is_deleted`. Add the two manager lines before `class Meta`.

- [ ] **Step 2: Generate migration**

Run:
```bash
cd /Users/ck/Git/matrix/devtrack/backend && uv run python manage.py makemigrations issues
```
Expected: A new migration file is created adding `is_deleted` and `deleted_at` fields.

- [ ] **Step 3: Apply migration**

Run:
```bash
cd /Users/ck/Git/matrix/devtrack/backend && uv run python manage.py migrate
```
Expected: Migration applies successfully.

- [ ] **Step 4: Commit**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
git add apps/issues/models.py apps/issues/migrations/
git commit -m "feat(issues): add soft delete fields (is_deleted, deleted_at) with custom manager"
```

---

### Task 2: Update backend views for soft delete

**Files:**
- Modify: `backend/apps/issues/views.py:77-109`
- Modify: `backend/apps/issues/serializers.py:209-212`

- [ ] **Step 1: Override perform_destroy in IssueDetailView**

In `backend/apps/issues/views.py`, add a `perform_destroy` method to `IssueDetailView` (after line 87):

```python
class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.select_related("created_by", "assignee").prefetch_related("attachments")
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]

    def get_queryset(self):
        return _with_ai_fields(super().get_queryset())

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return IssueCreateUpdateSerializer
        return IssueDetailSerializer

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])
```

- [ ] **Step 2: Add delete action to BatchUpdateSerializer and BatchUpdateView**

In `backend/apps/issues/serializers.py`, update `BatchUpdateSerializer` to accept `"delete"` action and make `value` optional:

```python
class BatchUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=["assign", "set_priority", "set_status", "delete"])
    value = serializers.CharField(required=False, default="")
```

In `backend/apps/issues/views.py`, add the delete branch to `BatchUpdateView.post` (after line 107):

```python
        elif data["action"] == "delete":
            issues.update(is_deleted=True, deleted_at=timezone.now())
```

- [ ] **Step 3: Commit**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
git add apps/issues/views.py apps/issues/serializers.py
git commit -m "feat(issues): implement soft delete in detail and batch update views"
```

---

### Task 3: Update admin to show soft-deleted issues

**Files:**
- Modify: `backend/apps/issues/admin.py`

- [ ] **Step 1: Update IssueAdmin to use all_objects and show is_deleted**

```python
@admin.register(Issue)
class IssueAdmin(ModelAdmin):
    list_display = ("id", "title", "priority", "status", "assignee", "created_by", "is_deleted", "created_at")
    list_filter = ("priority", "status", "is_deleted")
    search_fields = ("title",)

    def get_queryset(self, request):
        return Issue.all_objects.all()
```

- [ ] **Step 2: Commit**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
git add apps/issues/admin.py
git commit -m "feat(issues): show soft-deleted issues in admin with is_deleted filter"
```

---

### Task 4: Write backend tests for soft delete

**Files:**
- Modify: `backend/tests/test_issues.py:143-148`

- [ ] **Step 1: Update existing delete test and add new soft delete tests**

Replace `TestIssueDelete` class and add batch delete test:

```python
class TestIssueDelete:
    def test_soft_delete_issue(self, auth_client, site_settings):
        issue = IssueFactory()
        response = auth_client.delete(f"/api/issues/{issue.id}/")
        assert response.status_code == 204
        # Issue still exists in DB but is_deleted=True
        from apps.issues.models import Issue
        assert Issue.all_objects.filter(id=issue.id, is_deleted=True).exists()
        # Not visible via normal queryset
        assert not Issue.objects.filter(id=issue.id).exists()

    def test_soft_deleted_issue_not_in_list(self, auth_client, site_settings):
        issue = IssueFactory()
        auth_client.delete(f"/api/issues/{issue.id}/")
        response = auth_client.get("/api/issues/")
        assert response.data["count"] == 0

    def test_soft_deleted_issue_not_accessible(self, auth_client, site_settings):
        issue = IssueFactory()
        auth_client.delete(f"/api/issues/{issue.id}/")
        response = auth_client.get(f"/api/issues/{issue.id}/")
        assert response.status_code == 404


class TestBatchDelete:
    def test_batch_delete(self, auth_client, site_settings):
        issues = IssueFactory.create_batch(3)
        response = auth_client.post("/api/issues/batch-update/", {
            "ids": [i.id for i in issues],
            "action": "delete",
        }, format="json")
        assert response.status_code == 200
        assert response.data["updated"] == 3
        from apps.issues.models import Issue
        assert Issue.objects.count() == 0
        assert Issue.all_objects.filter(is_deleted=True).count() == 3
```

- [ ] **Step 2: Run tests**

Run:
```bash
cd /Users/ck/Git/matrix/devtrack/backend && uv run pytest tests/test_issues.py -v
```
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
cd /Users/ck/Git/matrix/devtrack/backend
git add tests/test_issues.py
git commit -m "test(issues): add soft delete and batch delete tests"
```

---

### Task 5: Add delete button to issue detail page

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Add delete button to the header area**

In the detail page header (line 18), there's an empty div: `<div class="flex items-center space-x-2"></div>`. Add a delete button inside it:

```vue
<div class="flex items-center space-x-2">
  <UButton
    v-if="can('issues.delete_issue')"
    icon="i-heroicons-trash"
    color="error"
    variant="outline"
    size="sm"
    @click="showDeleteConfirm = true"
  >
    删除
  </UButton>
</div>
```

- [ ] **Step 2: Add delete confirmation modal**

Add after the existing label management modal (after line 581, before the closing `</div>`):

```vue
<!-- 删除问题确认弹窗 -->
<UModal v-model:open="showDeleteConfirm">
  <template #content>
    <div class="modal-form">
      <div class="modal-header">
        <h3>删除问题</h3>
        <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showDeleteConfirm = false" />
      </div>
      <div class="modal-body">
        <p class="text-sm text-gray-700 dark:text-gray-300">
          确认删除问题 <span class="font-medium">#{{ issue.id }} {{ issue.title }}</span>？
        </p>
      </div>
      <div class="modal-footer">
        <UButton variant="outline" color="neutral" @click="showDeleteConfirm = false">取消</UButton>
        <UButton color="error" :loading="deleting" @click="handleDeleteIssue">确认删除</UButton>
      </div>
    </div>
  </template>
</UModal>
```

- [ ] **Step 3: Add script logic**

In the `<script setup>` section, import `useAuth` and add delete logic:

```typescript
const { can } = useAuth()
const showDeleteConfirm = ref(false)
const deleting = ref(false)
const router = useRouter()

async function handleDeleteIssue() {
  if (!issue.value) return
  deleting.value = true
  try {
    await api(`/api/issues/${issue.value.id}/`, { method: 'DELETE' })
    router.push('/app/issues')
  } catch (e) {
    console.error('Delete issue failed:', e)
  } finally {
    deleting.value = false
  }
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/ck/Git/matrix/devtrack/frontend
git add app/pages/app/issues/\\[id\\].vue
git commit -m "feat(issues): add delete button with confirmation on detail page"
```

---

### Task 6: Add batch delete to issue list page

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

- [ ] **Step 1: Add batch delete button to the batch action bar**

In the batch actions bar (after line 122, before the closing `</div>` of the button group), add:

```vue
<UButton v-if="can('issues.delete_issue')" size="xs" color="error" variant="outline" @click="showBatchDeleteConfirm = true">批量删除</UButton>
```

- [ ] **Step 2: Add batch delete confirmation modal**

Add a confirmation modal in the template (after the batch actions bar, around line 124):

```vue
<!-- 批量删除确认弹窗 -->
<UModal v-model:open="showBatchDeleteConfirm">
  <template #content>
    <div class="modal-form">
      <div class="modal-header">
        <h3>批量删除</h3>
        <UButton icon="i-heroicons-x-mark" variant="ghost" color="neutral" size="sm" @click="showBatchDeleteConfirm = false" />
      </div>
      <div class="modal-body">
        <p class="text-sm text-gray-700 dark:text-gray-300">
          确认删除选中的 <span class="font-medium">{{ selectedRowsData.length }}</span> 个问题？
        </p>
      </div>
      <div class="modal-footer">
        <UButton variant="outline" color="neutral" @click="showBatchDeleteConfirm = false">取消</UButton>
        <UButton color="error" :loading="batchDeleting" @click="handleBatchDelete">确认删除</UButton>
      </div>
    </div>
  </template>
</UModal>
```

- [ ] **Step 3: Add script logic**

In the `<script setup>` section, import `useAuth` and add batch delete logic:

```typescript
const { can } = useAuth()
const showBatchDeleteConfirm = ref(false)
const batchDeleting = ref(false)

async function handleBatchDelete() {
  const ids = selectedRowsData.value.map((row: any) => row.id)
  if (!ids.length) return
  batchDeleting.value = true
  try {
    await api('/api/issues/batch-update/', {
      method: 'POST',
      body: { ids, action: 'delete' },
    })
    showBatchDeleteConfirm.value = false
    rowSelection.value = {}
    await fetchIssues()
  } catch (e) {
    console.error('Batch delete failed:', e)
  } finally {
    batchDeleting.value = false
  }
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/ck/Git/matrix/devtrack/frontend
git add app/pages/app/issues/index.vue
git commit -m "feat(issues): add batch delete button with confirmation on list page"
```

---

### Task 7: Run full test suite

- [ ] **Step 1: Run all backend tests**

Run:
```bash
cd /Users/ck/Git/matrix/devtrack/backend && uv run pytest -x -v
```
Expected: All tests pass. The custom manager ensures deleted issues are excluded from all existing queries automatically.

- [ ] **Step 2: Fix any failures**

If any tests fail due to the custom manager, check if they need to use `Issue.all_objects` instead of `Issue.objects`.

- [ ] **Step 3: Final commit if fixes needed**

```bash
git add -A && git commit -m "fix(issues): resolve test failures from soft delete manager"
```
