# Issue Description: Image Upload & Markdown Editor

**Date:** 2026-03-24
**Status:** Approved

## Overview

Add image upload support to the issue description field via MinIO object storage, and replace the plain textarea with a GitHub-style Markdown editor (Write/Preview tabs).

## Requirements

- Description field becomes a Markdown editor with Edit/Preview tab switching
- Images can be uploaded by click (single/multi), drag-and-drop, or paste
- Images stored in MinIO with a dedicated user and bucket
- Single file limit: 5MB, allowed types: png, jpeg, gif, webp
- Other text fields (remark, cause, solution) remain plain text
- Issue model unchanged — description stores Markdown source text

## Architecture

### MinIO Setup

One-time initialization via `mc` CLI script:

1. Create bucket `devtrack-uploads` with public read policy
2. Create dedicated user `devtrack-app` with access key/secret key
3. Grant `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on `devtrack-uploads` only

Environment variables added to `.env` (values are placeholders — all come from env vars, never hardcoded in code):
```
MINIO_ENDPOINT=<host:port>
MINIO_ACCESS_KEY=<devtrack-app access key>
MINIO_SECRET_KEY=<devtrack-app secret key>
MINIO_BUCKET=devtrack-uploads
MINIO_USE_SSL=False
MINIO_PUBLIC_URL=http://<host:port>/devtrack-uploads
```

### Backend — `tools` App

New Django app `backend/apps/tools/` as a general-purpose utility layer (future: email, SMS, third-party integrations). No models, no migrations directory needed.

**Storage module (`storage.py`):**
- `boto3` S3 client configured for MinIO endpoint, with `use_ssl` from `MINIO_USE_SSL`
- `upload_file(file) -> url` function
- File stored at path `{year}/{month}/{day}/{uuid}.{ext}`
- Returns public URL: `{MINIO_PUBLIC_URL}/{path}`

**Upload API (`views.py`):**
- `POST /api/tools/upload/image/`
- Permission: `IsAuthenticated`
- Request: `multipart/form-data`, single file per request (field `file`)
- Validation: file type whitelist, 5MB size limit (client-side check + server-side)
- Success response (200): `{"url": "...", "filename": "..."}`
- Error responses: `400` bad type/missing file (`{"detail": "..."}`), `413` size exceeded (`{"detail": "..."}`)
- Frontend uploads multiple files via `Promise.all` of individual requests

**Django config:**
- Set `DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024` in `settings.py` (Django default is 2.5MB)

**URL registration:**
- `backend/apps/tools/urls.py` defines routes
- `backend/apps/urls.py` includes `tools/` prefix

### Frontend — `MarkdownEditor.vue` Component

Reusable component with `v-model` binding.

**Interface:**
```vue
<MarkdownEditor v-model="issue.description" placeholder="添加描述..." />
```

**Layout (GitHub-style):**
- Top tab bar: 「编辑」 / 「预览」
- Edit mode: plain textarea for Markdown input
- Preview mode: rendered Markdown HTML via `markdown-it`
- Bottom toolbar: image upload button + hint text "粘贴、拖放或点击上传图片"

**Image upload interactions:**
- Click: bottom toolbar button triggers hidden file input (multi-select)
- Drag-and-drop: drag files onto editor area, highlight on dragover
- Paste: Ctrl+V to paste clipboard images
- Client-side validation: check file size (≤5MB) and type before uploading, toast on rejection

**Upload flow:**
1. Insert placeholder `![上传中...]()`
2. Call `POST /api/tools/upload/image/`
3. On success: replace with `![filename](url)`
4. On failure: replace with `![上传失败]()`, show toast error

**Markdown rendering:**
- `markdown-it` with `html: false` (no raw HTML allowed — prevents XSS)
- Images rendered with `max-width: 100%`
- Styles aligned with GitHub markdown-body

**Image access:** Images are served directly from MinIO via public read bucket policy. No CORS issues since images are loaded as `<img src>` tags (not XHR), which are not subject to CORS restrictions.

### Issue Creation

The issue creation modal (in `issues/index.vue`) currently uses a minimal form. The Markdown editor will only be applied to the detail/edit page (`issues/[id].vue`). The creation modal keeps its simple textarea — users can add rich descriptions after creating the issue.

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `backend/apps/tools/__init__.py` | App init |
| `backend/apps/tools/apps.py` | App config |
| `backend/apps/tools/storage.py` | MinIO boto3 upload utility |
| `backend/apps/tools/views.py` | Image upload API view |
| `backend/apps/tools/urls.py` | URL routes |
| `frontend/app/components/MarkdownEditor.vue` | Markdown editor component |
| `scripts/minio-init.sh` | MinIO initialization script |

### Modified Files
| File | Change |
|------|--------|
| `backend/.env` | Add MINIO_* env vars |
| `backend/config/settings.py` | Register `apps.tools`, add MinIO config, set `DATA_UPLOAD_MAX_MEMORY_SIZE` |
| `backend/apps/urls.py` | Add `tools/` route |
| `backend/pyproject.toml` | Add `boto3` dependency |
| `frontend/app/pages/app/issues/[id].vue` | Replace UTextarea with MarkdownEditor for description |
| `frontend/package.json` | Add `markdown-it` dependency |

### Unchanged
- Issue model (description remains TextField, stores Markdown source)
- Issue serializers
- Remark, cause, solution fields (stay plain text)
- Issue creation modal (keeps simple textarea)

## Known Limitations

- **Orphaned images:** If a user uploads an image but discards the edit, the image remains in MinIO. A cleanup mechanism (periodic job checking referenced URLs) can be added later if storage becomes a concern.
