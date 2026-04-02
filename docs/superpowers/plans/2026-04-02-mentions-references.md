# @mention / #issue Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `@user` and `#issue` autocomplete in the markdown editor, render them as highlighted links in preview, and create notifications for mentioned users.

**Architecture:** Textarea-based autocomplete with floating dropdown. Store references as `@[Name](user:ID)` / `#[ISS-NNN](issue:NNN)` in markdown. Custom markdown-it plugin for rendering. Mention parsing in issue serializer triggers notification creation via the Notification app.

**Tech Stack:** Django REST Framework, Nuxt 4, markdown-it, textarea-caret (npm), Tailwind CSS

**Prerequisite:** Notification App must be implemented first (see `docs/superpowers/plans/2026-04-02-notification-app.md`).

---

### Task 1: Backend — extend issue search to support number

**Files:**
- Modify: `backend/apps/issues/views.py:57`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_issues.py`, inside `TestIssueList`:

```python
    def test_search_by_number(self, auth_client, site_settings):
        issue = IssueFactory(title="某个问题")
        response = auth_client.get(f"/api/issues/?search={issue.pk}")
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == issue.pk
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_issues.py::TestIssueList::test_search_by_number -v
```

Expected: FAIL — search by number returns 0 results because `search_fields` only includes `title`.

- [ ] **Step 3: Add number to search_fields**

In `backend/apps/issues/views.py`, line 57, change:

```python
    search_fields = ["title"]
```

to:

```python
    search_fields = ["title", "=pk"]
```

The `=` prefix means exact match, so `?search=61` matches issue with pk=61.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_issues.py::TestIssueList::test_search_by_number -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/issues/views.py backend/tests/test_issues.py
git commit -m "feat(issues): add issue number to search fields for mention autocomplete"
```

---

### Task 2: Backend — mention parsing service

**Files:**
- Create: `backend/apps/notifications/services.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_notifications.py`:

```python
class TestMentionParsing:
    def test_extract_mentions(self):
        from apps.notifications.services import extract_mentioned_user_ids
        text = "请 @[张三](user:5) 和 @[李四](user:12) 看看这个问题"
        ids = extract_mentioned_user_ids(text)
        assert ids == {5, 12}

    def test_extract_no_mentions(self):
        from apps.notifications.services import extract_mentioned_user_ids
        assert extract_mentioned_user_ids("普通文本") == set()

    def test_extract_ignores_invalid(self):
        from apps.notifications.services import extract_mentioned_user_ids
        text = "邮件 user@example.com 和 @[张三](user:5)"
        assert extract_mentioned_user_ids(text) == {5}

    def test_create_mention_notifications(self, auth_user):
        from apps.notifications.services import create_mention_notifications
        from apps.notifications.models import NotificationRecipient
        user2 = UserFactory()
        issue = IssueFactory(reporter=auth_user)
        new_desc = f"请 @[{user2.name}](user:{user2.id}) 看看"
        create_mention_notifications(
            issue=issue,
            old_description="",
            new_description=new_desc,
            actor=auth_user,
        )
        assert NotificationRecipient.objects.filter(user=user2).count() == 1
        notif = NotificationRecipient.objects.get(user=user2).notification
        assert notif.notification_type == "mention"
        assert notif.source_issue == issue
        assert notif.source_user == auth_user

    def test_no_self_notification(self, auth_user):
        from apps.notifications.services import create_mention_notifications
        from apps.notifications.models import NotificationRecipient
        issue = IssueFactory(reporter=auth_user)
        new_desc = f"@[{auth_user.name}](user:{auth_user.id}) 看看"
        create_mention_notifications(
            issue=issue,
            old_description="",
            new_description=new_desc,
            actor=auth_user,
        )
        assert NotificationRecipient.objects.filter(user=auth_user).count() == 0

    def test_no_duplicate_on_update(self, auth_user):
        from apps.notifications.services import create_mention_notifications
        from apps.notifications.models import NotificationRecipient
        user2 = UserFactory()
        issue = IssueFactory(reporter=auth_user)
        desc = f"@[{user2.name}](user:{user2.id}) 看看"
        # First save
        create_mention_notifications(issue=issue, old_description="", new_description=desc, actor=auth_user)
        # Second save — same mention, no new notification
        create_mention_notifications(issue=issue, old_description=desc, new_description=desc, actor=auth_user)
        assert NotificationRecipient.objects.filter(user=user2).count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_notifications.py::TestMentionParsing -v
```

Expected: FAIL — `extract_mentioned_user_ids` does not exist.

- [ ] **Step 3: Implement the service**

Create `backend/apps/notifications/services.py`:

```python
import re
from django.contrib.auth import get_user_model
from .models import Notification, NotificationRecipient

User = get_user_model()

MENTION_RE = re.compile(r'@\[([^\]]+)\]\(user:(\d+)\)')


def extract_mentioned_user_ids(text: str) -> set[int]:
    return {int(m.group(2)) for m in MENTION_RE.finditer(text)}


def create_mention_notifications(*, issue, old_description: str, new_description: str, actor):
    old_ids = extract_mentioned_user_ids(old_description)
    new_ids = extract_mentioned_user_ids(new_description)
    added_ids = new_ids - old_ids - {actor.id}

    if not added_ids:
        return

    users = User.objects.filter(id__in=added_ids, is_active=True)
    for user in users:
        notification = Notification.objects.create(
            notification_type=Notification.Type.MENTION,
            title=f"{actor.name or actor.username} 在 #{issue.pk} 中提到了你",
            content=f"问题: {issue.title}",
            source_user=actor,
            source_issue=issue,
            target_type=Notification.TargetType.USER,
        )
        NotificationRecipient.objects.create(
            notification=notification,
            user=user,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_notifications.py::TestMentionParsing -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/notifications/services.py backend/tests/test_notifications.py
git commit -m "feat(notifications): add mention parsing service with tests"
```

---

### Task 3: Backend — integrate mention notifications into issue serializer

**Files:**
- Modify: `backend/apps/issues/serializers.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_issues.py`:

```python
class TestMentionNotification:
    def test_create_issue_with_mention(self, auth_client, auth_user, site_settings):
        from tests.factories import ProjectFactory, UserFactory
        from apps.notifications.models import NotificationRecipient
        user2 = UserFactory()
        project = ProjectFactory()
        response = auth_client.post("/api/issues/", {
            "project": str(project.id),
            "title": "测试提及",
            "description": f"请 @[{user2.name}](user:{user2.id}) 看看",
            "priority": "P2",
            "status": "待处理",
            "labels": ["前端"],
        }, format="json")
        assert response.status_code == 201
        assert NotificationRecipient.objects.filter(user=user2).count() == 1

    def test_update_issue_with_new_mention(self, auth_client, auth_user, site_settings):
        from tests.factories import UserFactory
        from apps.notifications.models import NotificationRecipient
        user2 = UserFactory()
        issue = IssueFactory(reporter=auth_user, description="原始描述")
        response = auth_client.patch(f"/api/issues/{issue.id}/", {
            "description": f"请 @[{user2.name}](user:{user2.id}) 看看",
        }, format="json")
        assert response.status_code == 200
        assert NotificationRecipient.objects.filter(user=user2).count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_issues.py::TestMentionNotification -v
```

Expected: FAIL — no NotificationRecipient created (mention parsing not wired in yet).

- [ ] **Step 3: Wire mention parsing into the serializer**

In `backend/apps/issues/serializers.py`, add at the top:

```python
from apps.notifications.services import create_mention_notifications
```

Then in the `create()` method of `IssueCreateUpdateSerializer`, after `_sync_attachments` equivalent (after the attachment linking block, before `return issue`), add:

```python
        create_mention_notifications(
            issue=issue,
            old_description="",
            new_description=issue.description,
            actor=self.context["request"].user,
        )
```

In the `update()` method, before the `_sync_attachments` call, capture the old description and add the mention call after:

At the start of `update()`, save the old description:

```python
        old_description = instance.description
```

At the end of `update()`, after `_sync_attachments(issue, user)`, add:

```python
        if "description" in validated_data:
            create_mention_notifications(
                issue=issue,
                old_description=old_description,
                new_description=issue.description,
                actor=user,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_issues.py::TestMentionNotification -v
```

Expected: All PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd backend && uv run pytest -x
```

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/issues/serializers.py backend/tests/test_issues.py
git commit -m "feat(issues): wire mention parsing to create notifications on issue save"
```

---

### Task 4: Frontend — install textarea-caret dependency

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install the package**

```bash
cd frontend && npm install textarea-caret
```

Note: `textarea-caret` is a small utility that calculates pixel coordinates of the caret in a textarea. If the package doesn't exist on npm or has issues, we'll implement a minimal version inline.

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add textarea-caret dependency for mention autocomplete"
```

---

### Task 5: Frontend — MentionDropdown component

**Files:**
- Create: `frontend/app/components/MentionDropdown.vue`

- [ ] **Step 1: Create the component**

Create `frontend/app/components/MentionDropdown.vue`:

```vue
<template>
  <div
    v-if="visible && items.length > 0"
    class="absolute z-50 w-64 max-h-48 overflow-y-auto bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg"
    :style="{ top: `${position.top}px`, left: `${position.left}px` }"
  >
    <button
      v-for="(item, idx) in items"
      :key="item.id"
      class="w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2"
      :class="idx === selectedIndex
        ? 'bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300'
        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
      @mousedown.prevent="selectItem(idx)"
    >
      <template v-if="type === 'user'">
        <UIcon name="i-heroicons-user-circle" class="w-4 h-4 text-gray-400 flex-shrink-0" />
        <span class="truncate">{{ item.label }}</span>
      </template>
      <template v-else>
        <span class="text-xs font-mono text-gray-400 flex-shrink-0">{{ item.prefix }}</span>
        <span class="truncate">{{ item.label }}</span>
      </template>
    </button>
  </div>
</template>

<script setup lang="ts">
export interface MentionItem {
  id: number
  label: string
  prefix?: string  // e.g. "#ISS-061" for issues
}

const props = defineProps<{
  visible: boolean
  items: MentionItem[]
  position: { top: number; left: number }
  type: 'user' | 'issue'
}>()

const emit = defineEmits<{
  select: [item: MentionItem]
}>()

const selectedIndex = ref(0)

watch(() => props.items, () => {
  selectedIndex.value = 0
})

function selectItem(idx: number) {
  emit('select', props.items[idx])
}

function moveUp() {
  selectedIndex.value = Math.max(0, selectedIndex.value - 1)
}

function moveDown() {
  selectedIndex.value = Math.min(props.items.length - 1, selectedIndex.value + 1)
}

function confirmSelection() {
  if (props.items.length > 0) {
    emit('select', props.items[selectedIndex.value])
  }
}

defineExpose({ moveUp, moveDown, confirmSelection })
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/MentionDropdown.vue
git commit -m "feat(mentions): add MentionDropdown component"
```

---

### Task 6: Frontend — integrate autocomplete into MarkdownEditor

**Files:**
- Modify: `frontend/app/components/MarkdownEditor.vue`

- [ ] **Step 1: Add imports and state for autocomplete**

In `frontend/app/components/MarkdownEditor.vue`, in the `<script setup>` section, after the existing imports and before `const props`, add:

```typescript
import getCaretCoordinates from 'textarea-caret'
```

After the `const fileInputRef` line, add:

```typescript
const mentionRef = ref<InstanceType<typeof MentionDropdown> | null>(null)
const mentionVisible = ref(false)
const mentionType = ref<'user' | 'issue'>('user')
const mentionItems = ref<{ id: number; label: string; prefix?: string }[]>([])
const mentionPosition = ref({ top: 0, left: 0 })
const mentionTriggerStart = ref(0)

let userCache: { id: number; name: string }[] | null = null
```

- [ ] **Step 2: Add mention detection and data fetching functions**

After the `let userCache` line, add:

```typescript
function detectMentionTrigger(): { type: 'user' | 'issue'; query: string; start: number } | null {
  const ta = textareaRef.value
  if (!ta) return null
  const text = props.modelValue || ''
  const cursor = ta.selectionStart
  const before = text.slice(0, cursor)

  // Check for @mention trigger
  const atMatch = before.match(/@([^\s@]*)$/)
  if (atMatch) {
    return { type: 'user', query: atMatch[1], start: cursor - atMatch[0].length }
  }

  // Check for #issue trigger
  const hashMatch = before.match(/#([^\s#]*)$/)
  if (hashMatch) {
    return { type: 'issue', query: hashMatch[1], start: cursor - hashMatch[0].length }
  }

  return null
}

async function fetchUserSuggestions(query: string) {
  if (!userCache) {
    userCache = await api<{ id: number; name: string }[]>('/api/users/choices/')
  }
  const q = query.toLowerCase()
  return userCache
    .filter(u => u.name.toLowerCase().includes(q))
    .slice(0, 8)
    .map(u => ({ id: u.id, label: u.name }))
}

async function fetchIssueSuggestions(query: string) {
  if (!query) return []
  const data = await api<{ count: number; results: { id: number; title: string }[] }>(
    `/api/issues/?search=${encodeURIComponent(query)}&page_size=8`
  )
  return data.results.map(i => ({
    id: i.id,
    label: i.title,
    prefix: `#ISS-${String(i.id).padStart(3, '0')}`,
  }))
}

function updateMentionPosition() {
  const ta = textareaRef.value
  if (!ta) return
  const coords = getCaretCoordinates(ta, ta.selectionStart)
  mentionPosition.value = {
    top: coords.top + coords.height + 4 - ta.scrollTop,
    left: coords.left,
  }
}

async function handleMentionInput() {
  const trigger = detectMentionTrigger()
  if (!trigger) {
    mentionVisible.value = false
    return
  }
  mentionType.value = trigger.type
  mentionTriggerStart.value = trigger.start
  updateMentionPosition()

  if (trigger.type === 'user') {
    mentionItems.value = await fetchUserSuggestions(trigger.query)
  } else {
    mentionItems.value = await fetchIssueSuggestions(trigger.query)
  }
  mentionVisible.value = mentionItems.value.length > 0
}

function insertMention(item: { id: number; label: string; prefix?: string }) {
  const ta = textareaRef.value
  if (!ta) return
  const cursor = ta.selectionStart
  let replacement: string
  if (mentionType.value === 'user') {
    replacement = `@[${item.label}](user:${item.id}) `
  } else {
    const prefix = item.prefix || `#ISS-${String(item.id).padStart(3, '0')}`
    replacement = `#[${prefix}](issue:${item.id}) `
  }
  replaceRange(mentionTriggerStart.value, cursor, replacement)
  mentionVisible.value = false
}

function handleMentionKeydown(e: KeyboardEvent) {
  if (!mentionVisible.value) return
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    mentionRef.value?.moveUp()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    mentionRef.value?.moveDown()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    mentionRef.value?.confirmSelection()
  } else if (e.key === 'Escape') {
    mentionVisible.value = false
  }
}
```

- [ ] **Step 3: Wire up the textarea events**

In the template, update the `<textarea>` element to add `@keydown` and update the `@input`:

```html
      <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        class="w-full min-h-[260px] p-4 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-y outline-none"
        @input="onTextareaInput"
        @keydown="handleMentionKeydown"
        @paste="handlePaste"
      />
```

Add the input handler:

```typescript
function onTextareaInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
  nextTick(handleMentionInput)
}
```

- [ ] **Step 4: Add the MentionDropdown to the template**

Inside the edit mode `<div v-show="mode === 'edit'">`, right after the `<textarea>`, add:

```html
      <!-- Mention autocomplete -->
      <MentionDropdown
        ref="mentionRef"
        :visible="mentionVisible"
        :items="mentionItems"
        :position="mentionPosition"
        :type="mentionType"
        @select="insertMention"
      />
```

Note: The parent `<div v-show="mode === 'edit'">` needs `class="relative"` added for the absolute positioning of the dropdown to work.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/components/MarkdownEditor.vue
git commit -m "feat(mentions): integrate @user and #issue autocomplete into markdown editor"
```

---

### Task 7: Frontend — markdown-it mention rendering plugin

**Files:**
- Modify: `frontend/app/components/MarkdownEditor.vue`

- [ ] **Step 1: Add the markdown-it plugin**

In `frontend/app/components/MarkdownEditor.vue`, after the markdown-it instance creation (`const md = new MarkdownIt(...).use(taskLists, ...)`), add a custom inline rule:

```typescript
// Mention rendering plugin
function mentionPlugin(md: MarkdownIt) {
  // @[Name](user:ID)
  md.inline.ruler.push('mention_user', (state, silent) => {
    if (state.src.charCodeAt(state.pos) !== 0x40 /* @ */) return false
    if (state.src.charCodeAt(state.pos + 1) !== 0x5B /* [ */) return false

    const match = state.src.slice(state.pos).match(/^@\[([^\]]+)\]\(user:(\d+)\)/)
    if (!match) return false
    if (!silent) {
      const token = state.push('mention_user', '', 0)
      token.content = match[1]
      token.meta = { id: match[2] }
    }
    state.pos += match[0].length
    return true
  })

  md.renderer.rules.mention_user = (tokens, idx) => {
    const name = tokens[idx].content
    return `<span class="mention-user">@${name}</span>`
  }

  // #[ISS-NNN](issue:ID)
  md.inline.ruler.push('mention_issue', (state, silent) => {
    if (state.src.charCodeAt(state.pos) !== 0x23 /* # */) return false
    if (state.src.charCodeAt(state.pos + 1) !== 0x5B /* [ */) return false

    const match = state.src.slice(state.pos).match(/^#\[([^\]]+)\]\(issue:(\d+)\)/)
    if (!match) return false
    if (!silent) {
      const token = state.push('mention_issue', '', 0)
      token.content = match[1]
      token.meta = { id: match[2] }
    }
    state.pos += match[0].length
    return true
  })

  md.renderer.rules.mention_issue = (tokens, idx) => {
    const label = tokens[idx].content
    const id = tokens[idx].meta.id
    return `<a href="/app/issues/${id}" class="mention-issue">${label}</a>`
  }
}

const md = new MarkdownIt({ html: false, linkify: true })
  .use(taskLists, { enabled: true })
  .use(mentionPlugin)
```

Note: This replaces the existing `const md = ...` line. The mentionPlugin function must be defined before the `md` constant.

- [ ] **Step 2: Add mention styles**

Append to the `<style>` section:

```css
/* Mention styles */
.markdown-body .mention-user {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-size: 0.9em;
  font-weight: 500;
}
.markdown-body .mention-issue {
  background: #dcfce7;
  color: #15803d;
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-size: 0.9em;
  font-weight: 500;
  text-decoration: none;
}
.markdown-body .mention-issue:hover {
  text-decoration: underline;
}
:root.dark .markdown-body .mention-user {
  background: #1e3a5f;
  color: #93c5fd;
}
:root.dark .markdown-body .mention-issue {
  background: #14532d;
  color: #86efac;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/MarkdownEditor.vue
git commit -m "feat(mentions): add markdown-it plugin for @user and #issue rendering"
```

---

### Task 8: Frontend — render mentions in notifications page

**Files:**
- Modify: `frontend/app/pages/app/notifications.vue`

The notification `content` field may also contain mention syntax. The notifications page already uses `md.renderInline()` but doesn't have the mention plugin. We need to share the markdown-it instance or add the plugin there too.

- [ ] **Step 1: Extract mention plugin to a composable**

Create `frontend/app/composables/useMentionMarkdown.ts`:

```typescript
import MarkdownIt from 'markdown-it'
import taskLists from 'markdown-it-task-lists'

function mentionPlugin(md: MarkdownIt) {
  md.inline.ruler.push('mention_user', (state, silent) => {
    if (state.src.charCodeAt(state.pos) !== 0x40) return false
    if (state.src.charCodeAt(state.pos + 1) !== 0x5B) return false
    const match = state.src.slice(state.pos).match(/^@\[([^\]]+)\]\(user:(\d+)\)/)
    if (!match) return false
    if (!silent) {
      const token = state.push('mention_user', '', 0)
      token.content = match[1]
      token.meta = { id: match[2] }
    }
    state.pos += match[0].length
    return true
  })

  md.renderer.rules.mention_user = (tokens, idx) => {
    return `<span class="mention-user">@${tokens[idx].content}</span>`
  }

  md.inline.ruler.push('mention_issue', (state, silent) => {
    if (state.src.charCodeAt(state.pos) !== 0x23) return false
    if (state.src.charCodeAt(state.pos + 1) !== 0x5B) return false
    const match = state.src.slice(state.pos).match(/^#\[([^\]]+)\]\(issue:(\d+)\)/)
    if (!match) return false
    if (!silent) {
      const token = state.push('mention_issue', '', 0)
      token.content = match[1]
      token.meta = { id: match[2] }
    }
    state.pos += match[0].length
    return true
  })

  md.renderer.rules.mention_issue = (tokens, idx) => {
    const id = tokens[idx].meta.id
    return `<a href="/app/issues/${id}" class="mention-issue">${tokens[idx].content}</a>`
  }
}

export function useMentionMarkdown() {
  const md = new MarkdownIt({ html: false, linkify: true })
    .use(taskLists, { enabled: true })
    .use(mentionPlugin)

  return { md, mentionPlugin }
}
```

- [ ] **Step 2: Update MarkdownEditor to use the shared composable**

In `frontend/app/components/MarkdownEditor.vue`, replace the local `mentionPlugin` function and `const md = ...` with:

```typescript
const { md } = useMentionMarkdown()
```

Remove the local `mentionPlugin` function and the old `import MarkdownIt` / `import taskLists` / `const md` lines.

- [ ] **Step 3: Update notifications page to use the shared composable**

In `frontend/app/pages/app/notifications.vue`, replace the local `import MarkdownIt` and `const md` with:

```typescript
const { md } = useMentionMarkdown()
```

And update `renderMarkdown` to use `md.renderInline(text)` (it already does).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/composables/useMentionMarkdown.ts frontend/app/components/MarkdownEditor.vue frontend/app/pages/app/notifications.vue
git commit -m "refactor: extract mention markdown plugin to shared composable"
```

---

### Task 9: Manual integration test

- [ ] **Step 1: Start backend and frontend**

```bash
cd backend && uv run python manage.py runserver &
cd frontend && npm run dev &
```

- [ ] **Step 2: Test autocomplete**

Open an issue detail page. In the description editor:
1. Type `@` — user dropdown should appear
2. Type a few characters to filter
3. Use ↑↓ to navigate, Enter to select
4. Verify the inserted format: `@[Name](user:ID)`
5. Type `#` then a number or text — issue dropdown should appear
6. Select an issue, verify format: `#[ISS-NNN](issue:ID)`

- [ ] **Step 3: Test rendering**

Switch to preview mode:
- `@[Name](user:ID)` renders as a blue highlighted `@Name` span
- `#[ISS-NNN](issue:ID)` renders as a green highlighted link, clicking navigates to the issue

- [ ] **Step 4: Test notifications**

1. Log in as user A, create/edit an issue mentioning user B
2. Log in as user B, check bell icon — should show new notification
3. Click the notification — should navigate to the issue

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend && uv run pytest -x
```

Expected: All tests PASS.

- [ ] **Step 6: Commit if any fixes were needed**

```bash
git add -A && git commit -m "fix(mentions): integration fixes"
```
