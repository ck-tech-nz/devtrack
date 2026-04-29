# Multi-File Upload in Markdown Editor

## Problem

`MarkdownEditor.vue` currently rejects any file that is not an image. Users cannot
attach PDFs, Word/Excel/PowerPoint documents, plain text/markdown, CSV, JSON, or
ZIP archives to issue descriptions or notification bodies. The backend
`ImageUploadView` already accepts arbitrary content types and stores them in the
generic `Attachment` model — only the frontend gate is blocking the feature.

Goal: let users upload common document and archive types alongside images.
Images keep inline preview. Other types render as a download-friendly file card
in the markdown preview.

## Scope

**In scope:**

- Frontend allowlist expansion in `MarkdownEditor.vue` (click-to-upload and
  drag-and-drop).
- Per-type size limits (5MB images, 20MB other).
- Conditional markdown insertion: images use `![]()`, other files use `[]()`.
- File-card rendering in markdown preview, detected by file extension.
- Backend allowlist enforcement (defense in depth — currently no MIME check).

**Out of scope:**

- Renaming the `/api/tools/upload/image/` endpoint.
- Changes to the `Attachment` model or the delete endpoint.
- Paste-from-clipboard support for non-image files (rare and ambiguous).
- Changes to the mention/autocomplete code.
- Rich previews for non-image files (PDF inline viewer, etc.).

## Allowed file types

| Category | MIME types | Extensions |
| --- | --- | --- |
| Image | `image/png`, `image/jpeg`, `image/gif`, `image/webp` | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` |
| PDF | `application/pdf` | `.pdf` |
| Word | `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.doc`, `.docx` |
| Excel | `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xls`, `.xlsx` |
| PowerPoint | `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation` | `.ppt`, `.pptx` |
| Text | `text/plain`, `text/markdown`, `text/csv`, `application/json` | `.txt`, `.md`, `.csv`, `.json` |
| Archive | `application/zip`, `application/x-zip-compressed` | `.zip` |

Some browsers report markdown files as `text/markdown`, others as `text/plain` or
empty string — the frontend allowlist will accept both `text/markdown` and an
empty `file.type` if the extension matches `.md`. Backend uses the same fallback
logic.

## Size limits

| File type | Frontend limit | Backend limit |
| --- | --- | --- |
| Image | 5MB | 20MB (existing) |
| Other | 20MB | 20MB |

Frontend selects the limit based on whether `file.type` starts with `image/`.

## Markdown insertion

After successful upload:

- Image → `![<filename>](<url>)` (unchanged)
- Other → `[<filename>](<url>)`

The placeholder pattern during upload also branches:

- Image: `![上传中 <filename>...]()`
- Other: `[上传中 <filename>...]()`

`replacePlaceholder` continues to work because it matches by full string.

## File-card rendering

Detection: any `<a>` element produced by the markdown renderer whose href ends
in a known non-image extension (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`,
`.ppt`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.zip`) becomes a card.

Implementation: override the `link_open` and `link_close` renderer rules in
`useMentionMarkdown.ts`. When `link_open` sees a matching extension, emit a card
opener with class `md-file-card` and a category-specific icon class; `link_close`
emits a closing tag. The link text inside the `<a>` is preserved as the
filename. We do not need to modify the inline link parser.

Card markup:

```html
<a class="md-file-card md-file-pdf" href="<url>" target="_blank" rel="noopener" download>
  <span class="md-file-icon" aria-hidden="true"></span>
  <span class="md-file-name">report.pdf</span>
  <span class="md-file-ext">PDF</span>
</a>
```

The icon is rendered via CSS `::before` content keyed off the category class
(no `<UIcon>` because we're emitting raw HTML from markdown-it). Icons can be
unicode glyphs (📄 📊 📁) or background SVGs — pick whichever renders cleaner
during implementation.

Card styles live in the existing `<style>` block in `MarkdownEditor.vue`
alongside `.markdown-body` rules.

Categories and their CSS classes:

- `.md-file-pdf` (pdf)
- `.md-file-word` (doc, docx)
- `.md-file-excel` (xls, xlsx, csv)
- `.md-file-ppt` (ppt, pptx)
- `.md-file-text` (txt, md, json)
- `.md-file-archive` (zip)

A regular external link (e.g. `https://example.com`) is unaffected — only links
ending in one of the listed extensions match.

## Backend changes

`apps/tools/views.py`:

- Replace the `IMAGE_TYPES` constant with `ALLOWED_TYPES` mapping the full
  allowlist above.
- In `ImageUploadView.post`, after the size check, reject any `file.content_type`
  not in `ALLOWED_TYPES` with a 400 and message `不支持的文件类型`. Also accept
  the empty/`text/plain` case for `.md` files by checking the extension as a
  fallback.
- `MAX_SIZE` stays at 20MB.
- Endpoint URL stays at `/api/tools/upload/image/`.

## UI copy

- File picker `accept` attribute: comma-separated list of all allowed MIME types
  and extensions.
- Toolbar button title: `上传文件` (was `上传图片`).
- Toolbar icon: keep `i-heroicons-photo` or switch to `i-heroicons-paper-clip` —
  pick during implementation, paperclip is more accurate.
- Helper text under textarea: `支持 Markdown 格式 · 粘贴、拖放或点击上传图片和文件`.

## Error handling

| Condition | Behavior |
| --- | --- |
| MIME not in allowlist | Toast `不支持的文件类型: <mime>`, skip file |
| Image > 5MB | Toast `图片 <name> 超过 5MB 限制`, skip |
| Other > 20MB | Toast `文件 <name> 超过 20MB 限制`, skip |
| Upload network error | Replace placeholder with `[上传失败 <name>]()` (or `![]()` for images), toast |
| Backend rejects MIME | Same as upload network error path |

## Files touched

- `frontend/app/components/MarkdownEditor.vue` — allowlist, size logic,
  insertion branching, accept attr, copy, card styles.
- `frontend/app/composables/useMentionMarkdown.ts` — link_open/link_close
  override for file-card detection.
- `backend/apps/tools/views.py` — MIME allowlist enforcement.

## Testing

- Backend: extend `tests/test_upload.py` to cover (a) allowed non-image types
  upload successfully, (b) disallowed types return 400, (c) markdown extension
  fallback for empty content type.
- Frontend: manual test in browser — upload pdf/docx/zip, verify markdown
  inserts `[]()`, verify preview shows file card with correct icon, verify
  click downloads. Verify image upload still inserts `![]()` and renders
  inline.

## Open questions

None. Design decisions confirmed during brainstorming:

- Allowlist approach (not "everything", not "all but executables").
- 5MB image / 20MB file limits.
- File-card visual style (not plain link, not icon-prefixed link).
- Extension-based card detection (not URL prefix, not custom syntax).
