# Issue Attachment Linking on Creation

**Date:** 2026-04-02
**Status:** Draft

## Problem

When creating a new issue, images pasted into the markdown editor are uploaded immediately and an `Attachment` record is created. However, the attachment is never linked to the issue after creation.

**Root cause:** `_sync_attachments()` in `backend/apps/issues/serializers.py` uses `re.findall(r'https?://\S+', ...)` to find image URLs in the description, but `MINIO_PUBLIC_URL` defaults to `/uploads` (a relative path). The regex only matches absolute HTTP URLs, so it never finds the relative `/uploads/...` paths.

## Solution

Replace URL-based regex matching with explicit ID-based linking. The frontend already receives attachment IDs from the upload response — pass them to the backend during issue creation.

## Changes

### Frontend — `frontend/app/pages/app/issues/index.vue`

1. Add a reactive `attachmentIds` array (type `string[]`)
2. Add `@upload-complete` handler on the `MarkdownEditor` in the create modal that pushes `uploaded.id` to the array
3. Include `attachment_ids: attachmentIds.value` in the POST body to `/api/issues/`
4. Clear `attachmentIds` when the modal closes (in `closeCreateModal()`)

### Backend — `backend/apps/issues/serializers.py`

1. Add `attachment_ids` field to `IssueWriteSerializer`:
   - `serializers.ListField(child=serializers.UUIDField(), required=False, write_only=True, default=list)`
2. Add `"attachment_ids"` to the serializer's `fields` list
3. In `create()`:
   - Pop `attachment_ids` from `validated_data` before `super().create()`
   - After issue creation, query `Attachment.objects.filter(id__in=attachment_ids, uploaded_by=user)` and call `issue.attachments.set(matched)`
   - Remove the `_sync_attachments(issue, ...)` call
4. Keep `_sync_attachments` call in `update()` unchanged — it serves as a safety net for the detail page edit flow

### Not in scope

- Cleaning up orphaned attachments (no issue link) — separate concern
- Fixing `_sync_attachments` regex for relative URLs — the ID-based approach replaces it for creation
- Retroactively linking old unlinked attachments
