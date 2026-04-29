# Multi-File Upload in Markdown Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users upload PDF, Office docs, plain text/markdown, CSV, JSON, and ZIP files (alongside images) in `MarkdownEditor.vue`. Non-image files render as a download-friendly file card in the markdown preview.

**Architecture:** Backend gains an explicit MIME allowlist on the existing upload endpoint. Frontend widens its type/size gates and inserts `[]()` (vs `![]()`) for non-image files. The shared markdown-it instance gets a `link_open` override that turns links with known doc/archive extensions into a styled file card. No new files, no new endpoints.

**Tech Stack:** Django 5 / DRF, pytest-django, Vue 3 / Nuxt 4, markdown-it.

Spec: [docs/superpowers/specs/2026-04-29-multi-file-upload-markdown-editor-design.md](../specs/2026-04-29-multi-file-upload-markdown-editor-design.md)

---

## Task 1: Backend — MIME allowlist and tests

**Files:**
- Modify: `backend/apps/tools/views.py`
- Modify: `backend/tests/test_upload.py`

The existing `IMAGE_TYPES` constant is unused (no validation is performed today). Replace it with `ALLOWED_TYPES` and enforce on the request. The order of checks matters: file presence → type → size → upload. The existing test `test_invalid_type_returns_400` uses `text/plain` which will now be **allowed** — it must be updated to use a truly disallowed type.

- [ ] **Step 1: Update `test_invalid_type_returns_400` to use a disallowed type**

In `backend/tests/test_upload.py`, replace the existing test body:

```python
    def test_invalid_type_returns_400(self, auth_client):
        f = SimpleUploadedFile("malware.exe", b"MZ", content_type="application/x-msdownload")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "类型" in response.data["detail"]
```

- [ ] **Step 2: Add tests for newly allowed file types**

Append to `backend/tests/test_upload.py` inside `class TestImageUpload`:

```python
    @patch("apps.tools.storage.upload_image")
    def test_pdf_upload_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.pdf",
            "2026/04/29/abc.pdf",
        )
        f = SimpleUploadedFile("report.pdf", b"%PDF-1.4\n%test", content_type="application/pdf")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
        assert response.data["filename"] == "report.pdf"

    @patch("apps.tools.storage.upload_image")
    def test_docx_upload_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.docx",
            "2026/04/29/abc.docx",
        )
        f = SimpleUploadedFile(
            "spec.docx",
            b"PK\x03\x04",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200

    @patch("apps.tools.storage.upload_image")
    def test_zip_upload_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.zip",
            "2026/04/29/abc.zip",
        )
        f = SimpleUploadedFile("bundle.zip", b"PK\x03\x04", content_type="application/zip")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200

    @patch("apps.tools.storage.upload_image")
    def test_markdown_with_textplain_succeeds(self, mock_upload, auth_client):
        """Some browsers report .md files as text/plain — allow if extension matches."""
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.md",
            "2026/04/29/abc.md",
        )
        f = SimpleUploadedFile("notes.md", b"# Hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200

    @patch("apps.tools.storage.upload_image")
    def test_plain_txt_succeeds(self, mock_upload, auth_client):
        mock_upload.return_value = (
            "http://minio:9000/devtrack-uploads/2026/04/29/abc.txt",
            "2026/04/29/abc.txt",
        )
        f = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_upload.py -v`
Expected: 5 new tests FAIL (allowlist not implemented), `test_invalid_type_returns_400` FAILS (no type validation in code yet).

- [ ] **Step 4: Implement allowlist in `views.py`**

Replace the entire contents of `backend/apps/tools/views.py` with:

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.tools.storage as tools_storage
from .models import Attachment

MAX_SIZE = 20 * 1024 * 1024  # 20MB

ALLOWED_TYPES = {
    # Images
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    # PDF
    "application/pdf",
    # Word
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Excel
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # PowerPoint
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Text / data
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    # Archive
    "application/zip",
    "application/x-zip-compressed",
}

# Extensions that are allowed even when the browser reports an unusual MIME type
# (e.g. some browsers report .md as text/plain or empty).
EXTENSION_FALLBACK = {
    "md", "txt", "csv", "json", "zip",
}


def _is_allowed(file) -> bool:
    if file.content_type in ALLOWED_TYPES:
        return True
    name = file.name or ""
    if "." in name:
        ext = name.rsplit(".", 1)[-1].lower()
        if ext in EXTENSION_FALLBACK:
            return True
    return False


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "未提供文件"}, status=400)
        if not _is_allowed(file):
            return Response(
                {"detail": f"不支持的文件类型: {file.content_type}"},
                status=400,
            )
        if file.size > MAX_SIZE:
            return Response(
                {"detail": "文件大小超过限制 (20MB)"},
                status=400,
            )

        url, key = tools_storage.upload_image(file)

        attachment = Attachment.objects.create(
            uploaded_by=request.user,
            file_name=file.name,
            file_key=key,
            file_url=url,
            file_size=file.size,
            mime_type=file.content_type,
        )

        return Response({"url": url, "filename": file.name, "id": str(attachment.id)})


class AttachmentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        attachment = Attachment.objects.filter(pk=pk).first()
        if not attachment:
            return Response({"detail": "附件不存在"}, status=404)
        if attachment.uploaded_by != request.user and not request.user.is_staff:
            return Response({"detail": "无权限删除此附件"}, status=403)
        tools_storage.delete_object(attachment.file_key)
        attachment.delete()
        return Response(status=204)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_upload.py -v`
Expected: All tests PASS (10 tests including the original 5 plus the 5 new ones).

- [ ] **Step 6: Commit**

```bash
git add backend/apps/tools/views.py backend/tests/test_upload.py
git commit -m "feat(tools): allow PDF/Office/text/zip uploads with MIME allowlist"
```

---

## Task 2: Frontend — widen file picker accept and allowlist

**Files:**
- Modify: `frontend/app/components/MarkdownEditor.vue`

This task changes only the upload gate (allowlist + size limits) and the markdown insertion. File-card rendering comes in Task 3. The toolbar button is renamed `上传文件` and switched to a paperclip icon to reflect the broader scope.

- [ ] **Step 1: Update toolbar button title and icon**

In `frontend/app/components/MarkdownEditor.vue`, find lines 38-40:

```vue
        <button title="上传图片" class="toolbar-btn" @click="triggerFileInput">
          <UIcon name="i-heroicons-photo" class="w-4 h-4" />
        </button>
```

Replace with:

```vue
        <button title="上传文件" class="toolbar-btn" @click="triggerFileInput">
          <UIcon name="i-heroicons-paper-clip" class="w-4 h-4" />
        </button>
```

- [ ] **Step 2: Update file input `accept` and helper text**

In `frontend/app/components/MarkdownEditor.vue`, find lines 65-74:

```vue
      <div class="flex items-center gap-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <span class="text-xs text-gray-400 dark:text-gray-500">支持 Markdown 格式 · 粘贴、拖放或点击上传图片</span>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />
      </div>
```

Replace with:

```vue
      <div class="flex items-center gap-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <span class="text-xs text-gray-400 dark:text-gray-500">支持 Markdown 格式 · 粘贴、拖放或点击上传图片和文件</span>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/plain,text/markdown,text/csv,application/json,application/zip,application/x-zip-compressed,.md,.txt,.csv,.json,.zip"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />
      </div>
```

- [ ] **Step 3: Replace allowlist constants and rewrite `uploadFiles`**

In `frontend/app/components/MarkdownEditor.vue`, find lines 235-236:

```ts
const ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const MAX_SIZE = 5 * 1024 * 1024
```

Replace with:

```ts
const IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const ALLOWED_TYPES = new Set([
  // Images
  'image/png', 'image/jpeg', 'image/gif', 'image/webp',
  // PDF
  'application/pdf',
  // Word
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  // Excel
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  // PowerPoint
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  // Text / data
  'text/plain', 'text/markdown', 'text/csv', 'application/json',
  // Archive
  'application/zip', 'application/x-zip-compressed',
])
const EXTENSION_FALLBACK = new Set(['md', 'txt', 'csv', 'json', 'zip'])
const MAX_IMAGE_SIZE = 5 * 1024 * 1024
const MAX_FILE_SIZE = 20 * 1024 * 1024

function isAllowed(file: File): boolean {
  if (ALLOWED_TYPES.has(file.type)) return true
  const ext = file.name.includes('.') ? file.name.split('.').pop()!.toLowerCase() : ''
  return EXTENSION_FALLBACK.has(ext)
}

function isImage(file: File): boolean {
  return IMAGE_TYPES.has(file.type)
}
```

- [ ] **Step 4: Rewrite `uploadFiles` to branch on image vs non-image**

In `frontend/app/components/MarkdownEditor.vue`, find lines 426-454 (the entire `uploadFiles` function):

```ts
async function uploadFiles(files: File[]) {
  for (const file of files) {
    if (!ALLOWED_TYPES.has(file.type)) {
      toast.add({ title: `不支持的文件类型: ${file.type}`, color: 'error' })
      continue
    }
    if (file.size > MAX_SIZE) {
      toast.add({ title: `文件 ${file.name} 超过 5MB 限制`, color: 'error' })
      continue
    }

    const placeholder = `![上传中 ${file.name}...]()`
    insertAtCursor('\n' + placeholder + '\n')

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api<{ url: string; filename: string; id: string }>('/api/tools/upload/image/', {
        method: 'POST',
        body: formData,
      })
      replacePlaceholder(placeholder, `![${res.filename}](${res.url})`)
      emit('upload-complete', { url: res.url, filename: res.filename, id: res.id })
    } catch {
      replacePlaceholder(placeholder, `![上传失败 ${file.name}]()`)
      toast.add({ title: `上传失败: ${file.name}`, color: 'error' })
    }
  }
}
```

Replace with:

```ts
async function uploadFiles(files: File[]) {
  for (const file of files) {
    if (!isAllowed(file)) {
      toast.add({ title: `不支持的文件类型: ${file.type || file.name}`, color: 'error' })
      continue
    }
    const image = isImage(file)
    const limit = image ? MAX_IMAGE_SIZE : MAX_FILE_SIZE
    if (file.size > limit) {
      const label = image ? '图片' : '文件'
      const limitMb = image ? 5 : 20
      toast.add({ title: `${label} ${file.name} 超过 ${limitMb}MB 限制`, color: 'error' })
      continue
    }

    const prefix = image ? '!' : ''
    const placeholder = `${prefix}[上传中 ${file.name}...]()`
    insertAtCursor('\n' + placeholder + '\n')

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api<{ url: string; filename: string; id: string }>('/api/tools/upload/image/', {
        method: 'POST',
        body: formData,
      })
      replacePlaceholder(placeholder, `${prefix}[${res.filename}](${res.url})`)
      emit('upload-complete', { url: res.url, filename: res.filename, id: res.id })
    } catch {
      replacePlaceholder(placeholder, `${prefix}[上传失败 ${file.name}]()`)
      toast.add({ title: `上传失败: ${file.name}`, color: 'error' })
    }
  }
}
```

- [ ] **Step 5: Verify type checks pass**

Run: `cd frontend && npx nuxi typecheck`
Expected: PASS, no new errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/components/MarkdownEditor.vue
git commit -m "feat(editor): allow non-image file uploads with size-aware limits"
```

---

## Task 3: Frontend — file card rendering in markdown preview

**Files:**
- Modify: `frontend/app/composables/useMentionMarkdown.ts`
- Modify: `frontend/app/components/MarkdownEditor.vue` (CSS only)

The shared markdown-it instance gets a `link_open` rule override that detects file extensions in the href and rewrites the link as a styled card. The link's text content (filename) is preserved as-is between the override of `link_open` and `link_close`. CSS lives next to the existing `.markdown-body` styles.

- [ ] **Step 1: Override `link_open` and `link_close` in `useMentionMarkdown.ts`**

Replace the entire contents of `frontend/app/composables/useMentionMarkdown.ts` with:

```ts
import MarkdownIt from 'markdown-it'
import taskLists from 'markdown-it-task-lists'

const FILE_EXT_CATEGORY: Record<string, string> = {
  pdf: 'pdf',
  doc: 'word',
  docx: 'word',
  xls: 'excel',
  xlsx: 'excel',
  csv: 'excel',
  ppt: 'ppt',
  pptx: 'ppt',
  txt: 'text',
  md: 'text',
  json: 'text',
  zip: 'archive',
}

function getFileCategory(href: string | undefined): string | null {
  if (!href) return null
  // Strip query string and hash before extracting extension
  const clean = href.split('?')[0].split('#')[0]
  const lastDot = clean.lastIndexOf('.')
  const lastSlash = clean.lastIndexOf('/')
  if (lastDot < 0 || lastDot < lastSlash) return null
  const ext = clean.slice(lastDot + 1).toLowerCase()
  return FILE_EXT_CATEGORY[ext] || null
}

function fileCardPlugin(md: MarkdownIt) {
  const defaultLinkOpen = md.renderer.rules.link_open
    || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
  const defaultLinkClose = md.renderer.rules.link_close
    || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx]
    const hrefIndex = token.attrIndex('href')
    const href = hrefIndex >= 0 ? token.attrs![hrefIndex][1] : undefined
    const category = getFileCategory(href)
    if (!category) {
      return defaultLinkOpen(tokens, idx, options, env, self)
    }
    token.attrJoin('class', `md-file-card md-file-${category}`)
    token.attrSet('target', '_blank')
    token.attrSet('rel', 'noopener')
    token.attrSet('download', '')
    // Mark for link_close to know it should append the badge
    token.meta = { ...(token.meta || {}), fileCategory: category }
    const opener = self.renderToken(tokens, idx, options)
    return `${opener}<span class="md-file-icon" aria-hidden="true"></span><span class="md-file-name">`
  }

  md.renderer.rules.link_close = (tokens, idx, options, env, self) => {
    // Find the matching link_open by walking backwards
    let depth = 1
    let openIdx = idx - 1
    while (openIdx >= 0) {
      const t = tokens[openIdx]
      if (t.type === 'link_close') depth++
      if (t.type === 'link_open') {
        depth--
        if (depth === 0) break
      }
      openIdx--
    }
    const openToken = openIdx >= 0 ? tokens[openIdx] : null
    const category = openToken?.meta?.fileCategory as string | undefined
    if (!category) {
      return defaultLinkClose(tokens, idx, options, env, self)
    }
    const ext = (() => {
      const hrefIndex = openToken!.attrIndex('href')
      const href = hrefIndex >= 0 ? openToken!.attrs![hrefIndex][1] : ''
      const clean = href.split('?')[0].split('#')[0]
      return clean.slice(clean.lastIndexOf('.') + 1).toUpperCase()
    })()
    return `</span><span class="md-file-ext">${ext}</span>${self.renderToken(tokens, idx, options)}`
  }
}

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
    const label = `#问题-${String(id).padStart(3, '0')}`
    return `<a href="/app/issues/${id}" class="mention-issue">${label}</a>`
  }
}

export function useMentionMarkdown() {
  const md = new MarkdownIt({ html: false, linkify: true })
    .use(taskLists, { enabled: true })
    .use(fileCardPlugin)
    .use(mentionPlugin)

  return { md, mentionPlugin }
}
```

- [ ] **Step 2: Add file-card styles to `MarkdownEditor.vue`**

In `frontend/app/components/MarkdownEditor.vue`, find the closing `</style>` tag at the end of the file. Insert the following block immediately **before** that closing tag:

```css

/* File card (non-image attachments in markdown preview) */
.markdown-body .md-file-card {
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
  padding: 0.4em 0.75em;
  margin: 0.25em 0.25em 0.25em 0;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  color: #1f2937;
  text-decoration: none;
  font-size: 0.875em;
  line-height: 1.2;
  transition: background 0.15s, border-color 0.15s;
  max-width: 100%;
}
.markdown-body .md-file-card:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  text-decoration: none;
}
.markdown-body .md-file-card .md-file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.markdown-body .md-file-card .md-file-ext {
  font-size: 0.7em;
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 0.15em 0.4em;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.06);
  color: #4b5563;
}
.markdown-body .md-file-card .md-file-icon {
  display: inline-block;
  width: 1.1em;
  height: 1.1em;
  flex-shrink: 0;
  background-repeat: no-repeat;
  background-position: center;
  background-size: contain;
}
.markdown-body .md-file-pdf .md-file-icon::before { content: '📄'; }
.markdown-body .md-file-word .md-file-icon::before { content: '📝'; }
.markdown-body .md-file-excel .md-file-icon::before { content: '📊'; }
.markdown-body .md-file-ppt .md-file-icon::before { content: '📽'; }
.markdown-body .md-file-text .md-file-icon::before { content: '📄'; }
.markdown-body .md-file-archive .md-file-icon::before { content: '📦'; }

.markdown-body .md-file-pdf .md-file-ext { background: #fee2e2; color: #b91c1c; }
.markdown-body .md-file-word .md-file-ext { background: #dbeafe; color: #1d4ed8; }
.markdown-body .md-file-excel .md-file-ext { background: #dcfce7; color: #15803d; }
.markdown-body .md-file-ppt .md-file-ext { background: #ffedd5; color: #c2410c; }
.markdown-body .md-file-text .md-file-ext { background: #f3f4f6; color: #4b5563; }
.markdown-body .md-file-archive .md-file-ext { background: #e5e7eb; color: #374151; }

:root.dark .markdown-body .md-file-card {
  background: #1f2937;
  border-color: #374151;
  color: #e5e7eb;
}
:root.dark .markdown-body .md-file-card:hover {
  background: #374151;
  border-color: #4b5563;
}
:root.dark .markdown-body .md-file-card .md-file-ext {
  background: rgba(255, 255, 255, 0.08);
  color: #d1d5db;
}
:root.dark .markdown-body .md-file-pdf .md-file-ext { background: #7f1d1d; color: #fecaca; }
:root.dark .markdown-body .md-file-word .md-file-ext { background: #1e3a5f; color: #bfdbfe; }
:root.dark .markdown-body .md-file-excel .md-file-ext { background: #14532d; color: #bbf7d0; }
:root.dark .markdown-body .md-file-ppt .md-file-ext { background: #7c2d12; color: #fed7aa; }
:root.dark .markdown-body .md-file-text .md-file-ext { background: #374151; color: #e5e7eb; }
:root.dark .markdown-body .md-file-archive .md-file-ext { background: #4b5563; color: #f3f4f6; }
```

- [ ] **Step 3: Verify type checks pass**

Run: `cd frontend && npx nuxi typecheck`
Expected: PASS, no new errors.

- [ ] **Step 4: Manual test in dev server**

Start the backend and frontend if not already running:

```bash
# In one terminal:
cd backend && uv run python manage.py runserver
# In another:
cd frontend && npm run dev
```

Open `http://localhost:3004/app/issues/100` (or any existing issue), then:

1. **Image upload** (regression check): drag a `.png` into the description editor. Verify markdown shows `![filename](url)` and preview renders the inline image. Image still appears in preview.
2. **PDF upload**: click the paperclip icon and select a `.pdf`. Verify markdown shows `[filename.pdf](url)`. Switch to preview tab. Verify a file card appears with 📄 icon, filename, and red `PDF` badge. Click the card — file downloads.
3. **DOCX upload**: same as PDF, expect blue `DOCX` badge with 📝 icon.
4. **ZIP upload**: same as PDF, expect gray `ZIP` badge with 📦 icon.
5. **Markdown file**: drag a `.md` file. Should upload successfully. Card shows `MD` text-style badge.
6. **Disallowed type**: try dragging an `.exe`. Toast shows `不支持的文件类型: ...`, no upload happens.
7. **Oversize image**: try uploading a 10MB PNG. Toast shows `图片 ... 超过 5MB 限制`.
8. **Oversize file**: try uploading a 25MB PDF. Toast shows `文件 ... 超过 20MB 限制`.
9. **External plain link** (no extension): paste `https://example.com` as a markdown link `[example](https://example.com)`. Verify it renders as a normal link, not a file card.
10. **External link with non-doc extension**: `[a script](https://example.com/foo.js)` should render as a normal link (`.js` is not in `FILE_EXT_CATEGORY`).
11. **Mention regression**: type `@` to trigger user mention, `#` to trigger issue mention. Verify both still work.

If any step fails, fix in place and re-test before committing.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/composables/useMentionMarkdown.ts frontend/app/components/MarkdownEditor.vue
git commit -m "feat(editor): render non-image attachments as download cards in markdown preview"
```

---

## Self-Review

Spec coverage check:

- ✅ Allowlist for images + docs + text + archive — Task 1 backend, Task 2 frontend
- ✅ 5MB image / 20MB file size limits — Task 2 step 3-4
- ✅ Conditional markdown insertion (`![]()` vs `[]()`) — Task 2 step 4
- ✅ File-card rendering with extension detection — Task 3 step 1
- ✅ Backend MIME enforcement — Task 1 step 4
- ✅ Card styling (icon + filename + ext badge) — Task 3 step 2
- ✅ Dark mode card styles — Task 3 step 2
- ✅ Manual UI testing including regressions — Task 3 step 4
- ✅ Error toasts for type/size/upload-fail — Task 2 step 4 + existing catch path
- ✅ Helper text + accept attr + button title updates — Task 2 steps 1-2
- ✅ Markdown extension fallback for `.md` reported as `text/plain` — Task 1 covered by `text/plain` being in ALLOWED_TYPES + `EXTENSION_FALLBACK` for empty/odd MIMEs

Type consistency check:

- `ALLOWED_TYPES` (Set) used in frontend; `ALLOWED_TYPES` (set) in backend — same name, same role.
- `isImage` / `isAllowed` / `isAllowed` helpers defined in Task 2, used in Task 2.
- `FILE_EXT_CATEGORY` keys match the extensions used in CSS class names in Task 3 step 2.
- `md-file-pdf|word|excel|ppt|text|archive` classes referenced in JS and CSS match.

No placeholders. No TODOs. Each step has the exact code or command needed.

---

## Execution Handoff

Plan complete and saved to [docs/superpowers/plans/2026-04-29-multi-file-upload-markdown-editor.md](docs/superpowers/plans/2026-04-29-multi-file-upload-markdown-editor.md).

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
