# Issue Attachment Linking on Creation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix attachment linking so images uploaded during issue creation are correctly bound to the issue via explicit ID passing instead of broken URL regex matching.

**Architecture:** Frontend collects attachment UUIDs from upload responses, sends them as `attachment_ids` in the issue creation payload. Backend pops the IDs, creates the issue, then links the attachments via the existing M2M relationship.

**Tech Stack:** Django REST Framework (backend serializer), Vue 3 / Nuxt (frontend page component)

---

### Task 1: Backend — Add `attachment_ids` field and link attachments on create

**Files:**
- Modify: `backend/apps/issues/serializers.py:91-137`
- Test: `backend/tests/test_attachments.py`

- [ ] **Step 1: Write the failing test**

Add a new test to `TestAttachmentSync` in `backend/tests/test_attachments.py`. Insert after the existing `test_create_issue_links_matching_attachments` test (line 63):

```python
def test_create_issue_links_attachments_by_id(self, auth_client, auth_user, site_settings):
    from apps.tools.models import Attachment
    from apps.issues.models import Issue
    from tests.factories import ProjectFactory
    project = ProjectFactory()
    att1 = AttachmentFactory(uploaded_by=auth_user, file_url="/uploads/2026/04/02/a.png")
    att2 = AttachmentFactory(uploaded_by=auth_user, file_url="/uploads/2026/04/02/b.png")
    other_user_att = AttachmentFactory(file_url="/uploads/2026/04/02/c.png")
    response = auth_client.post("/api/issues/", {
        "project": project.id,
        "title": "附件测试",
        "description": "![a](/uploads/2026/04/02/a.png)",
        "priority": "P1",
        "status": "待处理",
        "labels": [],
        "attachment_ids": [str(att1.id), str(att2.id), str(other_user_att.id)],
    }, format="json")
    assert response.status_code == 201
    issue = Issue.objects.get(id=response.data["id"])
    linked = set(issue.attachments.values_list("id", flat=True))
    # Only att1 and att2 linked (owned by auth_user), other_user_att filtered out
    assert att1.id in linked
    assert att2.id in linked
    assert other_user_att.id not in linked
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_attachments.py::TestAttachmentSync::test_create_issue_links_attachments_by_id -v`
Expected: FAIL — serializer rejects unknown field `attachment_ids`

- [ ] **Step 3: Implement the backend changes**

In `backend/apps/issues/serializers.py`, make these changes to `IssueCreateUpdateSerializer`:

1. Add the field declaration (after line 94):

```python
attachment_ids = serializers.ListField(
    child=serializers.UUIDField(), required=False, write_only=True, default=list,
)
```

2. Add `"attachment_ids"` to the `fields` list in `Meta` (line 99):

```python
fields = [
    "id", "project", "repo", "title", "description", "priority", "status",
    "labels", "assignee", "helpers", "remark", "estimated_completion",
    "actual_hours", "cause", "solution", "attachment_ids",
]
```

3. Replace the `create()` method (lines 125-137):

```python
def create(self, validated_data):
    helpers = validated_data.pop("helpers", [])
    attachment_ids = validated_data.pop("attachment_ids", [])
    validated_data["reporter"] = self.context["request"].user
    issue = super().create(validated_data)
    if helpers:
        issue.helpers.set(helpers)
    Activity.objects.create(
        user=self.context["request"].user,
        issue=issue,
        action="created",
    )
    if attachment_ids:
        from apps.tools.models import Attachment
        atts = Attachment.objects.filter(id__in=attachment_ids, uploaded_by=self.context["request"].user)
        issue.attachments.add(*atts)
    return issue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_attachments.py::TestAttachmentSync::test_create_issue_links_attachments_by_id -v`
Expected: PASS

- [ ] **Step 5: Run full attachment test suite to check for regressions**

Run: `cd backend && uv run pytest tests/test_attachments.py -v`
Expected: All tests pass. Note: `test_create_issue_links_matching_attachments` still passes because it uses absolute HTTP URLs which `_sync_attachments` can still match. However, since we removed `_sync_attachments` from `create()`, this old test will now fail. Update it:

In `test_create_issue_links_matching_attachments`, the test relies on the old `_sync_attachments` call in `create()`. Since we removed it, convert this test to also use `attachment_ids`:

```python
def test_create_issue_links_matching_attachments(self, auth_client, auth_user, site_settings, settings):
    from apps.tools.models import Attachment
    from apps.issues.models import Issue
    from tests.factories import ProjectFactory
    project = ProjectFactory()
    att = AttachmentFactory(
        uploaded_by=auth_user,
        file_url="http://minio:9000/devtrack-uploads/2026/03/27/abc.png",
    )
    response = auth_client.post("/api/issues/", {
        "project": project.id,
        "title": "测试问题",
        "description": "截图: ![img](http://minio:9000/devtrack-uploads/2026/03/27/abc.png)",
        "priority": "P1",
        "status": "待处理",
        "labels": [],
        "attachment_ids": [str(att.id)],
    }, format="json")
    assert response.status_code == 201
    issue = Issue.objects.get(id=response.data["id"])
    assert issue.attachments.filter(id=att.id).exists()
```

Run: `cd backend && uv run pytest tests/test_attachments.py -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
cd backend
git add apps/issues/serializers.py tests/test_attachments.py
git commit -m "feat(backend): link attachments by ID on issue creation

Replace URL regex matching in create() with explicit attachment_ids
field. Frontend sends UUIDs from upload responses, backend links them
via M2M after creating the issue."
```

---

### Task 2: Frontend — Collect and send attachment IDs during issue creation

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

- [ ] **Step 1: Add `attachmentIds` reactive array**

In `frontend/app/pages/app/issues/index.vue`, after the `newIssue` ref declaration (line 315), add:

```typescript
const attachmentIds = ref<string[]>([])
```

- [ ] **Step 2: Add upload-complete handler function**

After the `closeCreateModal` function (line 350), add:

```typescript
function handleCreateUploadComplete(uploaded: { url: string; filename: string; id: string }) {
  attachmentIds.value.push(uploaded.id)
}
```

- [ ] **Step 3: Wire `@upload-complete` on the MarkdownEditor in the create modal**

Change line 74 from:

```vue
<MarkdownEditor v-model="newIssue.description" placeholder="详细描述问题" />
```

to:

```vue
<MarkdownEditor v-model="newIssue.description" placeholder="详细描述问题" @upload-complete="handleCreateUploadComplete" />
```

- [ ] **Step 4: Include `attachment_ids` in the POST body**

In the `handleCreateIssue` function, after line 365 (`labels: newIssue.value.labels,`), add:

```typescript
attachment_ids: attachmentIds.value,
```

- [ ] **Step 5: Clear `attachmentIds` on modal close**

In `closeCreateModal` (line 348), add `attachmentIds.value = []` after the `newIssue.value = ...` reset. Also add it after the successful creation in `handleCreateIssue` (line 372), after the `newIssue.value = ...` reset:

```typescript
attachmentIds.value = []
```

- [ ] **Step 6: Commit**

```bash
cd frontend
git add app/pages/app/issues/index.vue
git commit -m "feat(frontend): send attachment_ids when creating issues

Collect attachment UUIDs from MarkdownEditor upload-complete events and
include them in the issue creation POST body."
```

---

### Task 3: Manual verification

- [ ] **Step 1: Start dev servers**

Run backend and frontend dev servers.

- [ ] **Step 2: Test the fix**

1. Open the issues page, click "新建问题"
2. Fill in title, paste or drag an image into the description editor
3. Wait for upload to complete (placeholder replaced with markdown image)
4. Click "创建"
5. Open the newly created issue detail page
6. Verify the image appears in the description AND shows in the attachments section

- [ ] **Step 3: Test without attachments**

Create an issue with no images in the description. Verify it still creates successfully (no errors from empty `attachment_ids`).
