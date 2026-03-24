# Image Upload & Markdown Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MinIO-based image upload and a GitHub-style Markdown editor to the issue description field.

**Architecture:** Backend `tools` app provides a single image upload API endpoint that stores files in MinIO via boto3. Frontend `MarkdownEditor.vue` component replaces the description textarea with Write/Preview tabs, supporting image upload via click, drag-and-drop, and paste.

**Tech Stack:** Django REST Framework, boto3 (MinIO S3-compatible), Nuxt 4, markdown-it, Nuxt UI

**Spec:** `docs/superpowers/specs/2026-03-24-image-upload-markdown-editor-design.md`

---

### Task 1: MinIO Initialization Script

**Files:**
- Create: `scripts/minio-init.sh`

This script is for the user to run manually. It creates the bucket, user, and access policy.

- [ ] **Step 1: Create the MinIO init script**

```bash
#!/usr/bin/env bash
# MinIO initialization for DevTrack
# Prerequisites: mc (MinIO Client) installed and alias configured
#
# Usage:
#   1. Set your MinIO alias:  mc alias set myminio http://121.31.38.35:19000 minioadmin minioadmin123
#   2. Run this script:       bash scripts/minio-init.sh myminio
#   3. Copy the access key and secret key output into backend/.env

set -euo pipefail

ALIAS="${1:?Usage: $0 <mc-alias>}"
BUCKET="devtrack-uploads"
USER="devtrack-app"

echo "==> Creating bucket: ${BUCKET}"
mc mb "${ALIAS}/${BUCKET}" --ignore-existing

echo "==> Setting public read policy on bucket"
mc anonymous set download "${ALIAS}/${BUCKET}"

echo "==> Creating policy: ${USER}-policy"
cat > /tmp/devtrack-policy.json <<'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::devtrack-uploads/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::devtrack-uploads"]
    }
  ]
}
POLICY
mc admin policy create "${ALIAS}" "${USER}-policy" /tmp/devtrack-policy.json

echo "==> Creating user: ${USER}"
# Generate a random password
PASSWORD=$(openssl rand -base64 24)
mc admin user add "${ALIAS}" "${USER}" "${PASSWORD}"
mc admin policy attach "${ALIAS}" "${USER}-policy" --user "${USER}"

echo "==> Creating access key for ${USER}"
mc admin user svcacct add "${ALIAS}" "${USER}"

echo ""
echo "============================================"
echo "Add the access key and secret key above to backend/.env:"
echo ""
echo "MINIO_ENDPOINT=121.31.38.35:19000"
echo "MINIO_ACCESS_KEY=<access key from above>"
echo "MINIO_SECRET_KEY=<secret key from above>"
echo "MINIO_BUCKET=devtrack-uploads"
echo "MINIO_USE_SSL=False"
echo "MINIO_PUBLIC_URL=http://121.31.38.35:19000/devtrack-uploads"
echo "============================================"

rm -f /tmp/devtrack-policy.json
```

- [ ] **Step 2: Commit**

```bash
chmod +x scripts/minio-init.sh
git add scripts/minio-init.sh
git commit -m "feat(tools): add MinIO initialization script"
```

---

### Task 2: Backend — `tools` App Scaffold & MinIO Storage

**Files:**
- Create: `backend/apps/tools/__init__.py`
- Create: `backend/apps/tools/apps.py`
- Create: `backend/apps/tools/storage.py`
- Modify: `backend/config/settings.py` (add app, add MinIO config, set DATA_UPLOAD_MAX_MEMORY_SIZE)
- Modify: `backend/pyproject.toml` (add boto3)

- [ ] **Step 1: Add boto3 dependency**

```bash
cd backend && uv add "boto3>=1.35,<2.0"
```

- [ ] **Step 2: Create `backend/apps/tools/__init__.py`**

Empty file.

- [ ] **Step 3: Create `backend/apps/tools/apps.py`**

```python
from django.apps import AppConfig


class ToolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tools"
    verbose_name = "工具服务"
```

- [ ] **Step 4: Create `backend/apps/tools/storage.py`**

```python
import uuid
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings


def get_s3_client():
    scheme = "https" if settings.MINIO_USE_SSL else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def upload_image(file) -> str:
    """Upload a file to MinIO and return the public URL."""
    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "bin"
    now = datetime.now()
    key = f"{now.year}/{now.month:02d}/{now.day:02d}/{uuid.uuid4().hex}.{ext}"

    client = get_s3_client()
    client.upload_fileobj(
        file,
        settings.MINIO_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )
    return f"{settings.MINIO_PUBLIC_URL}/{key}"
```

- [ ] **Step 5: Add MinIO settings to `backend/config/settings.py`**

After the `DEFAULT_AUTO_FIELD` line (line 128), add:

```python
# Upload size limit — set higher than 5MB so Django doesn't reject before the view's own check runs
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# MinIO / S3 storage
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "devtrack-uploads")
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "False").lower() in ("true", "1")
MINIO_PUBLIC_URL = os.environ.get("MINIO_PUBLIC_URL", "http://127.0.0.1:9000/devtrack-uploads")
```

Register the app in `INSTALLED_APPS` (after `"apps.ai"`):

```python
    "apps.tools",
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/tools/ backend/config/settings.py backend/pyproject.toml backend/uv.lock
git commit -m "feat(tools): add tools app with MinIO storage module"
```

---

### Task 3: Backend — Image Upload API Endpoint

**Files:**
- Create: `backend/apps/tools/views.py`
- Create: `backend/apps/tools/urls.py`
- Modify: `backend/apps/urls.py` (add `tools/` include)

- [ ] **Step 1: Write the test**

Create `backend/tests/test_upload.py`:

```python
import io

import pytest
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
class TestImageUpload:
    URL = "/api/tools/upload/image/"

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.post(self.URL)
        assert response.status_code == 401

    def test_no_file_returns_400(self, auth_client):
        response = auth_client.post(self.URL)
        assert response.status_code == 400

    def test_invalid_type_returns_400(self, auth_client):
        f = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "类型" in response.data["detail"]

    def test_oversized_file_returns_400(self, auth_client):
        # 6MB file
        f = SimpleUploadedFile("big.png", b"x" * (6 * 1024 * 1024), content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 400
        assert "大小" in response.data["detail"]

    @patch("apps.tools.storage.upload_image")
    def test_valid_upload_returns_url(self, mock_upload, auth_client):
        mock_upload.return_value = "http://minio:9000/devtrack-uploads/2026/03/24/abc.png"
        f = SimpleUploadedFile("screenshot.png", b"\x89PNG" + b"\x00" * 100, content_type="image/png")
        response = auth_client.post(self.URL, {"file": f}, format="multipart")
        assert response.status_code == 200
        assert response.data["url"] == "http://minio:9000/devtrack-uploads/2026/03/24/abc.png"
        assert response.data["filename"] == "screenshot.png"
        mock_upload.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_upload.py -v
```

Expected: ERRORS — module `apps.tools.views` / URL route not found.

- [ ] **Step 3: Create `backend/apps/tools/views.py`**

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tools.storage import upload_image

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "未提供文件"}, status=400)
        if file.content_type not in ALLOWED_TYPES:
            return Response(
                {"detail": f"不支持的文件类型: {file.content_type}，仅支持 PNG/JPEG/GIF/WebP"},
                status=400,
            )
        if file.size > MAX_SIZE:
            return Response(
                {"detail": f"文件大小 ({file.size // 1024 // 1024}MB) 超过限制 (5MB)"},
                status=400,
            )
        url = upload_image(file)
        return Response({"url": url, "filename": file.name})
```

- [ ] **Step 4: Create `backend/apps/tools/urls.py`**

```python
from django.urls import path

from apps.tools.views import ImageUploadView

urlpatterns = [
    path("upload/image/", ImageUploadView.as_view(), name="upload-image"),
]
```

- [ ] **Step 5: Add `tools/` route to `backend/apps/urls.py`**

Add after the `"ai/"` line (line 13):

```python
    path("tools/", include("apps.tools.urls")),
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_upload.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/tools/views.py backend/apps/tools/urls.py backend/apps/urls.py backend/tests/test_upload.py
git commit -m "feat(tools): add image upload API endpoint with tests"
```

---

### Task 4: Frontend — Install markdown-it

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install markdown-it**

```bash
cd frontend && npm install markdown-it @types/markdown-it
```

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): add markdown-it dependency"
```

---

### Task 5: Frontend — MarkdownEditor Component

**Files:**
- Create: `frontend/app/components/MarkdownEditor.vue`

- [ ] **Step 1: Create the MarkdownEditor component**

```vue
<template>
  <div
    class="markdown-editor border rounded-xl overflow-hidden"
    :class="[
      isDragging ? 'border-primary-500 bg-primary-50 dark:bg-primary-950' : 'border-gray-200 dark:border-gray-700',
    ]"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
  >
    <!-- Tab bar -->
    <div class="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
      <button
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="mode === 'edit'
          ? 'text-gray-900 dark:text-gray-100 border-b-2 border-primary-500'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
        @click="mode = 'edit'"
      >
        编辑
      </button>
      <button
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="mode === 'preview'
          ? 'text-gray-900 dark:text-gray-100 border-b-2 border-primary-500'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
        @click="mode = 'preview'"
      >
        预览
      </button>
    </div>

    <!-- Edit mode -->
    <div v-show="mode === 'edit'">
      <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        class="w-full min-h-[200px] p-4 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-y outline-none"
        @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        @paste="handlePaste"
      />
      <!-- Toolbar -->
      <div class="flex items-center gap-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <button
          class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          @click="triggerFileInput"
        >
          <UIcon name="i-heroicons-photo" class="w-4 h-4" />
          <span>添加图片</span>
        </button>
        <span class="text-xs text-gray-400 dark:text-gray-500">粘贴、拖放或点击上传图片</span>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />
      </div>
    </div>

    <!-- Preview mode -->
    <div
      v-show="mode === 'preview'"
      class="markdown-body min-h-[200px] p-4 bg-white dark:bg-gray-900 text-sm"
      v-html="renderedHtml"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { api } = useApi()
const toast = useToast()

const mode = ref<'edit' | 'preview'>('edit')
const isDragging = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedHtml = computed(() => {
  if (!props.modelValue) return '<p class="text-gray-400 dark:text-gray-500">无内容</p>'
  return md.render(props.modelValue)
})

const ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const MAX_SIZE = 5 * 1024 * 1024

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    uploadFiles(Array.from(input.files))
    input.value = ''
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) {
    uploadFiles(Array.from(e.dataTransfer.files))
  }
}

function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const images: File[] = []
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) images.push(file)
    }
  }
  if (images.length) {
    e.preventDefault()
    uploadFiles(images)
  }
}

function insertAtCursor(text: string): { start: number; end: number } {
  const ta = textareaRef.value
  if (!ta) {
    const current = props.modelValue || ''
    emit('update:modelValue', current + text)
    return { start: current.length, end: current.length + text.length }
  }
  const start = ta.selectionStart
  const before = props.modelValue.slice(0, start)
  const after = props.modelValue.slice(ta.selectionEnd)
  emit('update:modelValue', before + text + after)
  const newPos = start + text.length
  nextTick(() => {
    ta.selectionStart = ta.selectionEnd = newPos
    ta.focus()
  })
  return { start, end: start + text.length }
}

function replacePlaceholder(placeholder: string, replacement: string) {
  const current = props.modelValue || ''
  const idx = current.indexOf(placeholder)
  if (idx >= 0) {
    emit('update:modelValue', current.slice(0, idx) + replacement + current.slice(idx + placeholder.length))
  }
}

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
      const res = await api<{ url: string; filename: string }>('/api/tools/upload/image/', {
        method: 'POST',
        body: formData,
      })
      replacePlaceholder(placeholder, `![${res.filename}](${res.url})`)
    } catch {
      replacePlaceholder(placeholder, `![上传失败 ${file.name}]()`)
      toast.add({ title: `上传失败: ${file.name}`, color: 'error' })
    }
  }
}
</script>

<style>
/* Markdown preview styles */
.markdown-body h1 { font-size: 1.5em; font-weight: 700; margin: 0.67em 0; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3em; }
.markdown-body h2 { font-size: 1.25em; font-weight: 600; margin: 0.83em 0; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3em; }
.markdown-body h3 { font-size: 1.1em; font-weight: 600; margin: 1em 0; }
.markdown-body p { margin: 0.5em 0; line-height: 1.6; }
.markdown-body ul, .markdown-body ol { margin: 0.5em 0; padding-left: 2em; }
.markdown-body li { margin: 0.25em 0; }
.markdown-body code { background: #f3f4f6; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.875em; }
.markdown-body pre { background: #f3f4f6; padding: 1em; border-radius: 6px; overflow-x: auto; margin: 0.5em 0; }
.markdown-body pre code { background: none; padding: 0; }
.markdown-body blockquote { border-left: 4px solid #d1d5db; padding-left: 1em; color: #6b7280; margin: 0.5em 0; }
.markdown-body img { max-width: 100%; border-radius: 6px; margin: 0.5em 0; }
.markdown-body a { color: #2563eb; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body hr { border: none; border-top: 1px solid #e5e7eb; margin: 1em 0; }
.markdown-body table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
.markdown-body th, .markdown-body td { border: 1px solid #d1d5db; padding: 0.5em 0.75em; text-align: left; }
.markdown-body th { background: #f9fafb; font-weight: 600; }

/* Dark mode */
:root.dark .markdown-body code { background: #1f2937; }
:root.dark .markdown-body pre { background: #1f2937; }
:root.dark .markdown-body blockquote { border-left-color: #4b5563; color: #9ca3af; }
:root.dark .markdown-body h1, :root.dark .markdown-body h2 { border-bottom-color: #374151; }
:root.dark .markdown-body a { color: #60a5fa; }
:root.dark .markdown-body hr { border-top-color: #374151; }
:root.dark .markdown-body th, :root.dark .markdown-body td { border-color: #4b5563; }
:root.dark .markdown-body th { background: #1f2937; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/MarkdownEditor.vue
git commit -m "feat(frontend): add MarkdownEditor component with image upload"
```

---

### Task 6: Frontend — Integrate MarkdownEditor into Issue Detail Page

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue:33-34`

- [ ] **Step 1: Replace UTextarea with MarkdownEditor**

In `frontend/app/pages/app/issues/[id].vue`, find lines 33-34:

```html
              <label>描述</label>
              <UTextarea v-model="form.description" :rows="5" />
```

Replace with:

```html
              <label>描述</label>
              <MarkdownEditor v-model="form.description" placeholder="添加描述..." />
```

- [ ] **Step 2: Verify the page still loads correctly**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000/app/issues/<any-id>` in the browser. Verify:
- The description field shows Edit/Preview tabs
- Typing Markdown in edit mode works
- Switching to Preview renders the Markdown
- The image upload button and drag hint are visible

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "feat(issues): use MarkdownEditor for issue description"
```

---

### Task 7: Update .env with MinIO Configuration (Manual — Do Not Commit)

**Files:**
- Modify: `backend/.env` (local only, not committed — contains secrets)

- [ ] **Step 1: Add MinIO env vars to .env**

After the existing `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` lines, add:

```
MINIO_ENDPOINT=121.31.38.35:19000
MINIO_ACCESS_KEY=<to be filled after running minio-init.sh>
MINIO_SECRET_KEY=<to be filled after running minio-init.sh>
MINIO_BUCKET=devtrack-uploads
MINIO_USE_SSL=False
MINIO_PUBLIC_URL=http://121.31.38.35:19000/devtrack-uploads
```

Note: The `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` values will be filled in by the user after running `scripts/minio-init.sh`. Do not commit `.env` — it contains secrets.

---

### Task 8: Run Full Test Suite & Verify

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest -v
```

Expected: All tests pass, including the new `test_upload.py` tests.

- [ ] **Step 2: Run frontend type check**

```bash
cd frontend && npx nuxi typecheck
```

Expected: No type errors.

- [ ] **Step 3: Final commit if any fixes were needed**

Only if previous steps required fixes.
