# Repo Detail Page Redesign

## Summary

Redesign the repo list cards and detail page. Cards become minimal (name + issue stats). Detail page gets a dashboard, kanban/list views for GitHub issues, and a collapsible info drawer. The existing `KanbanBoard` component is generalized for reuse.

## Repo List Card Changes

**Before:** Card shows `full_name`, description, language, stars, status, connected date.

**After:**
- Title: `repo.name` (bold, primary text)
- Subtitle: `repo.full_name` (small gray text)
- Issue stats: "Open: X / Closed: Y" — annotated counts from backend
- Status badge (kept as-is)
- Removed: description, language, stars, connected date

**Backend change:** Add `open_issues_count` and `closed_issues_count` as annotated fields to `RepoListCreateView` queryset, exposed via `RepoSerializer`.

## Repo Detail Page

### Header
- `repo.name` as page title
- `repo.full_name` as subtitle (small gray)
- Info icon button (toggles right slideover)
- Refresh button (triggers GitHub issue sync, with loading state)
- Status badge

### Dashboard Section (always visible)
2-3 stat cards in a horizontal row:
- **Open issues** count
- **Closed issues** count
- **Priority breakdown** — extracted from labels containing "priority" or matching P0/P1/P2/P3 patterns. Only shown if any issues have priority labels. Displayed as small badges with counts.

### View Toggle (看板 / 列表)
Pill toggle below dashboard, same style as the issues page toggle.

**Kanban view:**
- Dropdown to switch grouping mode:
  - **By state:** 2 columns — `open` | `closed`
  - **By label:** one column per unique label found across issues
- Cards show: `#github_id`, title, state badge, assignees, priority label (if present)
- Drag-and-drop is NOT supported (GitHub issues state is read-only from DevTrack)

**List view:**
- Table columns: `#` (github_id), title, state, labels (as badges), assignees, created date
- Click row to open GitHub issue URL (external link) or expand inline — TBD based on simplicity
- Pagination not needed initially (GitHub issues are fetched per-repo, typically <200)

### Info Slideover (right drawer)

- Collapsed by default, toggled via header info icon
- Uses Nuxt UI `USlideover` component (verify component name in Nuxt UI v3.1.x — may be `UDrawer` in some versions)
- Content: default branch, connected time, status, last synced time, GitHub URL (as link)

## Backend Changes

### RepoSerializer
Add read-only annotated fields and expose `last_synced_at`:
```python
open_issues_count = serializers.IntegerField(read_only=True)
closed_issues_count = serializers.IntegerField(read_only=True)
```

Add `last_synced_at`, `open_issues_count`, `closed_issues_count` to `fields` list.

### RepoListCreateView / RepoDetailView
Annotate queryset:
```python
from django.db.models import Count, Q

queryset = Repo.objects.annotate(
    open_issues_count=Count("github_issues", filter=Q(github_issues__state="open")),
    closed_issues_count=Count("github_issues", filter=Q(github_issues__state="closed")),
)
```

### Sync Endpoint

Add a POST endpoint at `/api/repos/<int:pk>/sync/` that triggers `GitHubSyncService.sync_repo()` and returns the updated repo data. Uses `[IsAuthenticated, FullDjangoModelPermissions]` for consistency with the rest of the project.

URL ordering in `urls.py`: place `<int:pk>/sync/` before `<int:pk>/` to ensure it matches first.

**Error handling:**
- On GitHub API failure (rate limit, invalid token, network): return 502 with `{"detail": "GitHub 同步失败: <error message>"}`.
- Sync is synchronous — acceptable since a single repo typically has <500 issues and the GitHub API is paginated.
- Frontend shows error toast on failure, success toast with "已同步 X 条 Issue" on success.

### GitHubIssue Serializer
`GitHubIssueBriefSerializer` already exists with the needed fields. Add `body`, `assignees`, `github_closed_at` for the detail view:

```python
class GitHubIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubIssue
        fields = [
            "id", "github_id", "title", "body", "state",
            "labels", "assignees",
            "github_created_at", "github_updated_at", "github_closed_at",
        ]
```

### GitHub Issues per Repo
The existing `GitHubIssueListView` already supports `?repo=<id>` filtering. No new endpoint needed.

## Frontend Component Changes

### Generalize KanbanBoard

Current `components/projects/KanbanBoard.vue` is hardcoded to DevTrack issue statuses (待处理/进行中/已解决) with hardcoded card templates and always-on drag-and-drop.

**Approach:** Use scoped slots for card content. The board handles column layout, drag-and-drop infrastructure, and column headers. Each consumer provides its own card template via a `#card` slot.

Move from `components/projects/` to `components/shared/KanbanBoard.vue` since it's now used across multiple features.

```typescript
defineProps<{
  columns: Array<{ key: string; label: string; items: any[] }>
  draggable?: boolean  // default true, false for GitHub issues
}>()

defineEmits<{
  'drop': [payload: { itemId: any; fromColumn: string; toColumn: string }]
}>()

// Slot: #card="{ item }" — consumer provides card content
```

The issues page computes columns from issues and provides a card slot with priority badge + assignee avatar + NuxtLink. The repo detail page computes columns from GitHub issues (grouped by state or label) and provides its own card slot with `#github_id`, title, labels, assignees.

### New Files

- `frontend/app/components/shared/KanbanBoard.vue` — generalized kanban with scoped slots

### Modified Files

- `frontend/app/pages/app/repos/index.vue` — update card layout, fetch issue counts
- `frontend/app/pages/app/repos/[id].vue` — complete rewrite with dashboard + kanban/list + slideover
- `frontend/app/pages/app/issues/index.vue` — switch to new shared KanbanBoard with `#card` slot
- `backend/apps/repos/views.py` — add annotations, add sync endpoint
- `backend/apps/repos/serializers.py` — add counts, add `last_synced_at`, add full issue serializer
- `backend/apps/repos/urls.py` — add sync URL

### Removed Files

- `frontend/app/components/projects/KanbanBoard.vue` — replaced by shared version

## Priority Label Extraction

Priority is extracted client-side from the `labels` JSON array. Match logic:
1. Label name contains "P0", "P1", "P2", "P3" (case-insensitive)
2. Label name contains "priority" (fallback grouping)
3. No match → no priority shown

This avoids any backend schema changes and works with any GitHub label naming convention.

## Out of Scope
- Editing GitHub issues from DevTrack (read-only)
- Drag-and-drop state changes for GitHub issues
- GitHub commits or PR data
- Pagination for GitHub issues list
