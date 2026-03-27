# AI Analysis Separation Design

## Summary

Decouple AI analysis results from Issue text fields (`cause`, `solution`, `remark`) into a dedicated API endpoint. Analysis results are already stored in the `Analysis` model's `parsed_result` field — this change stops duplicating them into Issue fields and provides a clean API for retrieval.

## Problem

Current architecture stores AI analysis results in two places:

1. **`Analysis.parsed_result`** — structured JSON in the AI analysis record
2. **Issue fields** — appended to `cause`/`solution`/`remark` with `\n---\n🤖 AI 分析 |` markers

This causes:
- User content and AI content mixed in the same fields, separated only by string parsing
- Multiple analysis runs accumulate in text fields, no way to delete/edit individual runs
- Duplicate storage between `Analysis.parsed_result` and Issue fields
- Frontend requires `parseAIContent()` to split AI blocks from user text

## Design

### New API Endpoint

**`GET /api/issues/{id}/analyses/`**

Returns all `issue_code_analysis` records for the issue, ordered by `-created_at`. Unpaginated list (analysis count per issue is small).

```json
[
  {
    "id": 42,
    "status": "done",
    "triggered_by": "manual",
    "triggered_by_user": "CK",
    "created_at": "2026-03-25T07:41:00Z",
    "error_message": null,
    "results": {
      "cause": "在 backend/app/models/case_operations.py:122 中..."
    }
  },
  {
    "id": 41,
    "status": "failed",
    "triggered_by": "auto",
    "triggered_by_user": null,
    "created_at": "2026-03-25T06:00:00Z",
    "error_message": "分析超时，请重试",
    "results": null
  }
]
```

- `id` is an integer (matches `Analysis` model's default auto-increment PK)
- Includes all statuses (`pending`, `running`, `done`, `failed`) so the frontend can show progress and errors
- `results` is `null` for non-done analyses
- `results` maps field name to content — only populated fields are included (typically one field per analysis, since the current AI flow assigns output to a single guessed field)
- `triggered_by_user` is the display name string (falls back to username)

### Backend Changes

#### 1. `backend/apps/issues/views.py` — New `IssueAnalysesView`

```python
class IssueAnalysesView(generics.ListAPIView):
    """GET /api/issues/{id}/analyses/ — unpaginated list"""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request, pk=None):
        issue = get_object_or_404(Issue, pk=pk)
        analyses = Analysis.objects.filter(
            issue=issue,
            analysis_type="issue_code_analysis",
        ).select_related("triggered_by_user").order_by("-created_at")

        data = []
        for a in analyses:
            results = None
            if a.status == Analysis.Status.DONE and a.parsed_result:
                pr = a.parsed_result
                # Handle old format {"target_field": "cause", "content": "..."}
                # and current format {"cause": "..."}
                if "target_field" in pr:
                    results = {pr["target_field"]: pr.get("content", "")}
                else:
                    results = {k: v for k, v in pr.items()
                              if k in ("cause", "solution", "remark") and v}

            data.append({
                "id": a.id,
                "status": a.status,
                "triggered_by": a.triggered_by,
                "triggered_by_user": (a.triggered_by_user.name or a.triggered_by_user.username)
                                      if a.triggered_by_user else None,
                "created_at": a.created_at.isoformat(),
                "error_message": a.error_message if a.status == Analysis.Status.FAILED else None,
                "results": results,
            })

        return Response(data)
```

#### 2. `backend/apps/issues/urls.py` — Register endpoint

Add: `path("<int:pk>/analyses/", IssueAnalysesView.as_view())`

Note: Issue uses integer PK (Django default auto-increment), matching all existing issue URL patterns.

#### 3. `backend/apps/ai/services.py` — Stop appending to Issue fields

In `IssueAnalysisService._execute_analysis`:
- Remove the `self._append_ai_content(issue, target_field, content)` call
- Keep `parsed_result` storing `{"target_field": field, "content": content}` format (same as current) — the view normalizes both formats on read
- Keep `_guess_target_field` logic to determine which key gets the content when AI returns unstructured text
- Remove `_append_ai_content` method entirely

#### 4. `backend/apps/issues/signals.py` — Clean up dead guard

The loop-prevention guard that skips auto-trigger when `update_fields` includes `cause`/`solution`/`remark` becomes dead code once `_append_ai_content` is removed. Clean it up.

#### 5. No model changes

The `Analysis` model already has all needed fields. No schema changes needed.

### Frontend Changes

#### 1. Sidebar AI section expansion (`frontend/app/pages/app/issues/[id].vue`)

The existing sidebar "AI 分析" card becomes the primary AI display area:
- **Header**: title + service status dot + trigger button (moved from page header)
- **Running state**: progress bar (existing)
- **Analysis history**: list of cards, each showing:
  - Timestamp + trigger type badge (手动/自动)
  - Content sections for cause/solution (collapsible if long)
  - Error message for failed analyses
- New `fetchAnalyses()` function calls `GET /api/issues/{id}/analyses/` on mount and after analysis completes

#### 2. Main content cleanup

- Remove `parseAIContent()` function
- Remove AI block rendering (blue cards with 🤖 icon) from cause/solution/remark sections
- These fields become pure user-editable textareas

#### 3. AI trigger button

Move from page header to sidebar AI section header. Keeps the same logic (POST to `/ai-analyze/`, poll status).

#### 4. Poll completion handler

Update `pollAnalysisStatus` to call `fetchAnalyses()` instead of `fetchIssue()` when analysis completes (issue data no longer changes from AI analysis).

### Migration Strategy

- **No data migration** — existing AI content already appended to Issue fields stays as-is. Since `parseAIContent()` is removed, legacy AI markers in text fields will show as plain text. This is acceptable given low data volume; users can manually clean up if needed.
- Old `parsed_result` format (`{"target_field": "cause", "content": "..."}`) is handled in the view via format detection
- New analyses continue using the same `parsed_result` format (single field per analysis)

### What Does NOT Change

- `Analysis` model schema
- Signal-based auto-trigger on issue create/description update (only loop guard cleanup)
- Manual trigger endpoint (`POST /api/issues/{id}/ai-analyze/`)
- Status polling endpoint (`GET /api/ai/analysis/{id}/status/`)
- `OpenCodeRunner` and LLM integration
