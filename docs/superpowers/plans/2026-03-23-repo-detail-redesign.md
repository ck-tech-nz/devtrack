# Repo Detail Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign repo list cards (name + issue stats) and repo detail page (dashboard + kanban/list + info drawer), generalizing the KanbanBoard component for reuse.

**Architecture:** Backend adds annotated issue counts to RepoSerializer and a sync endpoint. Frontend extracts KanbanBoard into a shared slot-based component, rewrites the repo detail page with dashboard stats + view toggle + slideover info panel.

**Tech Stack:** Django REST Framework, Nuxt 4, Nuxt UI v3, Vue 3 Composition API, TailwindCSS

**Spec:** `docs/superpowers/specs/2026-03-23-repo-detail-redesign.md`

---

### Task 1: Backend — Add issue counts, last_synced_at, and assignees to serializers

**Files:**
- Modify: `backend/apps/repos/serializers.py`
- Modify: `backend/apps/repos/views.py`
- Test: `backend/tests/test_repos.py`

- [ ] **Step 1: Write failing tests for issue counts and last_synced_at**

Add to `backend/tests/test_repos.py`:

```python
from tests.factories import RepoFactory, GitHubIssueFactory


class TestRepoIssueCounts:
    def test_list_includes_issue_counts(self, auth_client):
        repo = RepoFactory()
        GitHubIssueFactory.create_batch(3, repo=repo, state="open")
        GitHubIssueFactory.create_batch(2, repo=repo, state="closed")
        response = auth_client.get("/api/repos/")
        assert response.status_code == 200
        data = response.data[0]
        assert data["open_issues_count"] == 3
        assert data["closed_issues_count"] == 2

    def test_detail_includes_issue_counts(self, auth_client):
        repo = RepoFactory()
        GitHubIssueFactory.create_batch(5, repo=repo, state="open")
        response = auth_client.get(f"/api/repos/{repo.id}/")
        assert response.status_code == 200
        assert response.data["open_issues_count"] == 5
        assert response.data["closed_issues_count"] == 0

    def test_detail_includes_last_synced_at(self, auth_client):
        repo = RepoFactory()
        response = auth_client.get(f"/api/repos/{repo.id}/")
        assert "last_synced_at" in response.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_repos.py::TestRepoIssueCounts -v`
Expected: FAIL — `open_issues_count` key not found in response data.

- [ ] **Step 3: Update serializers**

In `backend/apps/repos/serializers.py`, update both serializers:

1. Add `assignees` to `GitHubIssueBriefSerializer` (needed by the repo detail kanban/table):

```python
class GitHubIssueBriefSerializer(serializers.ModelSerializer):
    repo_full_name = serializers.CharField(source="repo.full_name", read_only=True)

    class Meta:
        model = GitHubIssue
        fields = [
            "id", "repo", "repo_full_name", "github_id", "title",
            "state", "labels", "assignees",
            "github_created_at", "github_updated_at",
        ]
        read_only_fields = fields
```

2. Add annotated fields and `last_synced_at` to `RepoSerializer`:

```python
class RepoSerializer(serializers.ModelSerializer):
    open_issues_count = serializers.IntegerField(read_only=True, default=0)
    closed_issues_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Repo
        fields = [
            "id", "name", "full_name", "url", "description",
            "default_branch", "language", "stars", "status",
            "connected_at", "last_synced_at",
            "open_issues_count", "closed_issues_count",
        ]
        read_only_fields = ["id", "connected_at", "last_synced_at"]
```

- [ ] **Step 4: Add queryset annotations to views**

In `backend/apps/repos/views.py`, update both views to use an annotated queryset:

```python
from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Repo, GitHubIssue
from .serializers import RepoSerializer, GitHubIssueBriefSerializer


class RepoListCreateView(generics.ListCreateAPIView):
    serializer_class = RepoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Repo.objects.annotate(
            open_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="open")
            ),
            closed_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="closed")
            ),
        )


class RepoDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = RepoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Repo.objects.annotate(
            open_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="open")
            ),
            closed_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="closed")
            ),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_repos.py -v`
Expected: All pass including the new `TestRepoIssueCounts` tests.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/repos/serializers.py backend/apps/repos/views.py backend/tests/test_repos.py
git commit -m "feat(repos): add issue counts and last_synced_at to repo API"
```

---

### Task 2: Backend — Add sync endpoint

**Files:**
- Modify: `backend/apps/repos/views.py`
- Modify: `backend/apps/repos/urls.py`
- Test: `backend/tests/test_repos.py`

- [ ] **Step 1: Write failing test for sync endpoint**

Add to `backend/tests/test_repos.py`:

```python
from unittest.mock import patch, MagicMock


class TestRepoSync:
    def test_sync_triggers_service(self, auth_client):
        repo = RepoFactory(github_token="ghp_test123")
        with patch("apps.repos.views.GitHubSyncService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            response = auth_client.post(f"/api/repos/{repo.id}/sync/")
        assert response.status_code == 200
        mock_instance.sync_repo.assert_called_once()
        assert response.data["id"] == repo.id

    def test_sync_returns_502_on_github_failure(self, auth_client):
        repo = RepoFactory(github_token="ghp_test123")
        with patch("apps.repos.views.GitHubSyncService") as MockService:
            mock_instance = MagicMock()
            mock_instance.sync_repo.side_effect = Exception("API rate limit")
            MockService.return_value = mock_instance
            response = auth_client.post(f"/api/repos/{repo.id}/sync/")
        assert response.status_code == 502

    def test_sync_unauthenticated(self, api_client):
        repo = RepoFactory()
        response = api_client.post(f"/api/repos/{repo.id}/sync/")
        assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_repos.py::TestRepoSync -v`
Expected: FAIL — 404 (URL not found).

- [ ] **Step 3: Add the sync view**

Add to `backend/apps/repos/views.py`:

```python
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.permissions import FullDjangoModelPermissions
from .services import GitHubSyncService

logger = logging.getLogger(__name__)


class RepoSyncView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()  # FullDjangoModelPermissions 需要 queryset 确定模型

    def post(self, request, pk):
        try:
            repo = Repo.objects.annotate(
                open_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="open")
                ),
                closed_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="closed")
                ),
            ).get(pk=pk)
        except Repo.DoesNotExist:
            return Response(
                {"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            GitHubSyncService().sync_repo(repo)
            repo.refresh_from_db()
            repo = Repo.objects.annotate(
                open_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="open")
                ),
                closed_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="closed")
                ),
            ).get(pk=pk)
            serializer = RepoSerializer(repo)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("GitHub sync failed for repo %s", pk)
            return Response(
                {"detail": f"GitHub 同步失败: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
```

- [ ] **Step 4: Add URL pattern**

Update `backend/apps/repos/urls.py`:

```python
from django.urls import path
from .views import RepoListCreateView, RepoDetailView, GitHubIssueListView, RepoSyncView

urlpatterns = [
    path("", RepoListCreateView.as_view(), name="repo-list"),
    path("github-issues/", GitHubIssueListView.as_view(), name="github-issue-list"),
    path("<int:pk>/sync/", RepoSyncView.as_view(), name="repo-sync"),
    path("<int:pk>/", RepoDetailView.as_view(), name="repo-detail"),
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_repos.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/repos/views.py backend/apps/repos/urls.py backend/tests/test_repos.py
git commit -m "feat(repos): add sync endpoint POST /api/repos/<id>/sync/"
```

---

### Task 3: Frontend — Create shared KanbanBoard component

**Files:**
- Create: `frontend/app/components/shared/KanbanBoard.vue`
- Modify: `frontend/app/pages/app/issues/index.vue`
- Remove: `frontend/app/components/projects/KanbanBoard.vue`

- [ ] **Step 1: Create the shared KanbanBoard with scoped slots**

Create `frontend/app/components/shared/KanbanBoard.vue`:

```vue
<template>
  <div class="grid gap-4" :style="{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }">
    <div
      v-for="col in columns"
      :key="col.key"
      class="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 transition-colors"
      :class="draggable && dragOverTarget === col.key ? 'ring-2 ring-crystal-300 dark:ring-crystal-700 bg-crystal-50 dark:bg-crystal-950' : ''"
      @dragover.prevent="draggable && onDragOver(col.key)"
      @dragleave="draggable && onDragLeave()"
      @drop="draggable && onDrop(col.key)"
    >
      <div class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{{ col.label }}</h4>
        <UBadge color="neutral" variant="subtle" size="xs">{{ col.items.length }}</UBadge>
      </div>
      <div class="space-y-2">
        <div
          v-for="item in col.items"
          :key="itemKey(item)"
          :draggable="draggable"
          class="bg-white dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-800 p-3 hover:shadow-sm transition-shadow"
          :class="[
            draggable ? 'cursor-grab active:cursor-grabbing' : '',
            draggable && draggingId === itemKey(item) ? 'opacity-40' : '',
          ]"
          @dragstart="draggable && onDragStart(itemKey(item))"
          @dragend="draggable && onDragEnd()"
        >
          <slot name="card" :item="item" :column="col.key" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  columns: Array<{ key: string; label: string; items: any[] }>
  itemKey?: (item: any) => string | number
  draggable?: boolean
}>(), {
  itemKey: (item: any) => item.id,
  draggable: true,
})

const emit = defineEmits<{
  drop: [payload: { itemId: string | number; fromColumn: string; toColumn: string }]
}>()

const { draggingId, dragOverTarget, onDragStart, onDragEnd, onDragOver, onDragLeave } = useDragDrop<string | number>()

const draggingFromColumn = ref<string | null>(null)

function onDrop(toColumn: string) {
  const itemId = draggingId.value
  if (itemId == null) return

  // 查找拖拽项所属的列
  const fromCol = props.columns.find(c => c.items.some(i => props.itemKey(i) === itemId))
  if (fromCol && fromCol.key !== toColumn) {
    emit('drop', { itemId, fromColumn: fromCol.key, toColumn })
  }
  onDragEnd()
}
</script>
```

- [ ] **Step 2: Update issues page to use shared KanbanBoard**

In `frontend/app/pages/app/issues/index.vue`, replace:

```vue
<ProjectsKanbanBoard v-else-if="viewMode === 'kanban'" :issues="issues" @update:status="onStatusChange" />
```

With:

```vue
<SharedKanbanBoard
  v-else-if="viewMode === 'kanban'"
  :columns="kanbanColumns"
  :item-key="(item: any) => item.id"
  @drop="onKanbanDrop"
>
  <template #card="{ item }">
    <NuxtLink :to="`/app/issues/${item.id}`" class="block">
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-xs text-gray-400 dark:text-gray-500">#{{ item.id }}</span>
        <UBadge
          :color="item.priority === 'P0' ? 'error' : item.priority === 'P1' ? 'warning' : item.priority === 'P2' ? 'warning' : 'neutral'"
          variant="subtle"
          size="xs"
        >
          {{ item.priority }}
        </UBadge>
      </div>
      <p class="text-sm text-gray-900 dark:text-gray-100 font-medium line-clamp-2">{{ item.title }}</p>
      <div class="mt-2 flex items-center">
        <div class="w-5 h-5 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
          <span class="text-crystal-600 dark:text-crystal-400 text-[10px] font-medium">{{ (item.assignee_name || '?').slice(0, 1) }}</span>
        </div>
        <span class="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{{ item.assignee_name || '-' }}</span>
      </div>
    </NuxtLink>
  </template>
</SharedKanbanBoard>
```

Add computed and handler in `<script setup>`:

```typescript
const kanbanColumns = computed(() => [
  { key: '待处理', label: '待处理', items: issues.value.filter(i => i.status === '待处理') },
  { key: '进行中', label: '进行中', items: issues.value.filter(i => i.status === '进行中') },
  { key: '已解决', label: '已解决', items: issues.value.filter(i => i.status === '已解决') },
])

function onKanbanDrop({ itemId, toColumn }: { itemId: string | number; fromColumn: string; toColumn: string }) {
  onStatusChange({ issueId: itemId as number, newStatus: toColumn })
}
```

Remove the old `onStatusChange` emit handler's dependency on `ProjectsKanbanBoard`.

- [ ] **Step 3: Delete old KanbanBoard**

Delete `frontend/app/components/projects/KanbanBoard.vue`.

- [ ] **Step 4: Verify issues page still works**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/components/shared/KanbanBoard.vue frontend/app/pages/app/issues/index.vue
git rm frontend/app/components/projects/KanbanBoard.vue
git commit -m "refactor: extract KanbanBoard to shared component with scoped slots"
```

---

### Task 4: Frontend — Update repo list card

**Files:**
- Modify: `frontend/app/pages/app/repos/index.vue`

- [ ] **Step 1: Update the card template**

Replace the card `<NuxtLink>` block in `frontend/app/pages/app/repos/index.vue` (the `v-for` loop) with:

```vue
<NuxtLink v-for="repo in repos" :key="repo.id" :to="`/app/repos/${repo.id}`" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 hover:shadow-sm transition-shadow block">
  <div class="flex items-center justify-between mb-2">
    <div>
      <h3 class="font-semibold text-gray-900 dark:text-gray-100">{{ repo.name }}</h3>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ repo.full_name }}</p>
    </div>
    <UBadge :color="repo.status === '在线' ? 'success' : 'neutral'" variant="subtle" size="xs">{{ repo.status }}</UBadge>
  </div>
  <div class="flex items-center text-xs text-gray-400 dark:text-gray-500 space-x-4 mt-3">
    <span class="flex items-center">
      <UIcon name="i-heroicons-exclamation-circle" class="w-3.5 h-3.5 mr-1 text-amber-500" />
      Open {{ repo.open_issues_count ?? 0 }}
    </span>
    <span class="flex items-center">
      <UIcon name="i-heroicons-check-circle" class="w-3.5 h-3.5 mr-1 text-emerald-500" />
      Closed {{ repo.closed_issues_count ?? 0 }}
    </span>
  </div>
</NuxtLink>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/repos/index.vue
git commit -m "feat(repos): update repo card with name title and issue stats"
```

---

### Task 5: Frontend — Rewrite repo detail page

**Files:**
- Modify: `frontend/app/pages/app/repos/[id].vue`

- [ ] **Step 1: Rewrite the detail page**

Replace the entire content of `frontend/app/pages/app/repos/[id].vue` with the implementation below. This is the largest single change — it includes:

1. Header with repo name, full_name subtitle, info button, refresh button, status badge
2. Dashboard stat cards (open, closed, priority breakdown)
3. View toggle (看板/列表) with kanban grouping dropdown
4. KanbanBoard with GitHub issue cards via scoped slot
5. List table view
6. Info slideover

```vue
<template>
  <div v-if="loading" class="flex items-center justify-center py-20">
    <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
  </div>
  <div v-else-if="repo" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">{{ repo.name }}</h1>
        <p class="text-sm text-gray-400 dark:text-gray-500 mt-0.5">{{ repo.full_name }}</p>
      </div>
      <div class="flex items-center space-x-2">
        <UBadge :color="repo.status === '在线' ? 'success' : 'neutral'" variant="subtle">{{ repo.status }}</UBadge>
        <UButton
          icon="i-heroicons-arrow-path"
          variant="outline"
          color="neutral"
          size="sm"
          :loading="syncing"
          @click="handleSync"
        >
          同步
        </UButton>
        <UButton
          icon="i-heroicons-information-circle"
          variant="ghost"
          color="neutral"
          size="sm"
          @click="showInfo = true"
        />
      </div>
    </div>

    <!-- Dashboard Stats -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <DashboardStatCard
        label="Open Issues"
        :value="repo.open_issues_count ?? 0"
        icon="i-heroicons-exclamation-circle"
        icon-bg="bg-amber-50 dark:bg-amber-950"
        icon-color="text-amber-500"
      />
      <DashboardStatCard
        label="Closed Issues"
        :value="repo.closed_issues_count ?? 0"
        icon="i-heroicons-check-circle"
        icon-bg="bg-emerald-50 dark:bg-emerald-950"
        icon-color="text-emerald-500"
      />
      <div v-if="priorityStats.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
        <span class="text-sm text-gray-500 dark:text-gray-400">优先级分布</span>
        <div class="mt-2 flex flex-wrap gap-2">
          <UBadge
            v-for="p in priorityStats"
            :key="p.label"
            :color="p.label === 'P0' ? 'error' : p.label === 'P1' ? 'warning' : 'neutral'"
            variant="subtle"
            size="sm"
          >
            {{ p.label }}: {{ p.count }}
          </UBadge>
        </div>
      </div>
    </div>

    <!-- View Toggle -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
          <button
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
            :class="viewMode === 'kanban' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
            @click="viewMode = 'kanban'"
          >
            看板
          </button>
          <button
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
            :class="viewMode === 'table' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
            @click="viewMode = 'table'"
          >
            列表
          </button>
        </div>
        <USelect
          v-if="viewMode === 'kanban'"
          v-model="kanbanGroup"
          :items="[{ label: '按状态', value: 'state' }, { label: '按标签', value: 'label' }]"
          value-key="value"
          size="xs"
        />
      </div>
      <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ ghIssues.length }} 条</span>
    </div>

    <!-- Loading Issues -->
    <div v-if="issuesLoading" class="flex items-center justify-center py-10">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载 Issues 中...</div>
    </div>

    <!-- Kanban View -->
    <SharedKanbanBoard
      v-else-if="viewMode === 'kanban'"
      :columns="kanbanColumns"
      :item-key="(item: any) => item.id"
      :draggable="false"
    >
      <template #card="{ item }">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-xs text-gray-400 dark:text-gray-500">#{{ item.github_id }}</span>
          <div class="flex items-center gap-1">
            <UBadge
              :color="item.state === 'open' ? 'warning' : 'success'"
              variant="subtle"
              size="xs"
            >
              {{ item.state === 'open' ? '开放' : '已关闭' }}
            </UBadge>
            <UBadge
              v-if="extractPriority(item.labels)"
              :color="extractPriority(item.labels)!.startsWith('P0') ? 'error' : extractPriority(item.labels)!.startsWith('P1') ? 'warning' : 'neutral'"
              variant="subtle"
              size="xs"
            >
              {{ extractPriority(item.labels) }}
            </UBadge>
          </div>
        </div>
        <p class="text-sm text-gray-900 dark:text-gray-100 font-medium line-clamp-2">{{ item.title }}</p>
        <div v-if="item.assignees?.length" class="mt-2 flex items-center">
          <div class="w-5 h-5 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
            <span class="text-crystal-600 dark:text-crystal-400 text-[10px] font-medium">{{ item.assignees[0].slice(0, 1).toUpperCase() }}</span>
          </div>
          <span class="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{{ item.assignees[0] }}</span>
        </div>
      </template>
    </SharedKanbanBoard>

    <!-- Table View -->
    <div v-else-if="!issuesLoading" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
      <UTable
        :data="ghIssues"
        :columns="tableColumns"
        :ui="{ th: 'text-xs', td: 'text-sm' }"
      >
        <template #github_id-cell="{ row }">
          <span class="text-gray-500 dark:text-gray-400">#{{ row.original.github_id }}</span>
        </template>
        <template #title-cell="{ row }">
          <span class="text-gray-900 dark:text-gray-100 line-clamp-1">{{ row.original.title }}</span>
        </template>
        <template #state-cell="{ row }">
          <UBadge :color="row.original.state === 'open' ? 'warning' : 'success'" variant="subtle" size="xs">
            {{ row.original.state === 'open' ? '开放' : '已关闭' }}
          </UBadge>
        </template>
        <template #labels-cell="{ row }">
          <div class="flex flex-wrap gap-1">
            <UBadge v-for="label in row.original.labels" :key="label" color="neutral" variant="subtle" size="xs">{{ label }}</UBadge>
          </div>
        </template>
        <template #assignees-cell="{ row }">
          {{ row.original.assignees?.join(', ') || '-' }}
        </template>
        <template #github_created_at-cell="{ row }">
          {{ row.original.github_created_at?.slice(0, 10) || '-' }}
        </template>
      </UTable>
    </div>

    <!-- Info Slideover -->
    <USlideover v-model:open="showInfo" title="仓库信息" side="right">
      <template #content>
        <div class="p-6 space-y-4">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">仓库信息</h3>
          <div class="space-y-3">
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">GitHub URL</p>
              <a :href="repo.url" target="_blank" class="text-sm text-crystal-500 hover:text-crystal-700 break-all">{{ repo.url }}</a>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">默认分支</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.default_branch }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">状态</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.status }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">绑定时间</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.connected_at?.slice(0, 10) }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 dark:text-gray-500">最近同步</p>
              <p class="text-sm text-gray-900 dark:text-gray-100">{{ repo.last_synced_at?.slice(0, 16)?.replace('T', ' ') || '从未同步' }}</p>
            </div>
          </div>
        </div>
      </template>
    </USlideover>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()

const loading = ref(true)
const repo = ref<any>(null)
const ghIssues = ref<any[]>([])
const issuesLoading = ref(false)
const syncing = ref(false)
const showInfo = ref(false)
const viewMode = ref<'kanban' | 'table'>('kanban')
const kanbanGroup = ref('state')

const tableColumns = [
  { accessorKey: 'github_id', header: '#' },
  { accessorKey: 'title', header: '标题' },
  { accessorKey: 'state', header: '状态' },
  { accessorKey: 'labels', header: '标签' },
  { accessorKey: 'assignees', header: '负责人' },
  { accessorKey: 'github_created_at', header: '创建时间' },
]

// 从标签中提取优先级
function extractPriority(labels: string[]): string | null {
  if (!labels?.length) return null
  const match = labels.find(l => /^P[0-3]$/i.test(l) || /priority/i.test(l))
  return match || null
}

// 统计优先级分布
const priorityStats = computed(() => {
  const counts: Record<string, number> = {}
  for (const issue of ghIssues.value) {
    const p = extractPriority(issue.labels)
    if (p) counts[p] = (counts[p] || 0) + 1
  }
  return Object.entries(counts)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

// 看板列计算
const kanbanColumns = computed(() => {
  if (kanbanGroup.value === 'state') {
    return [
      { key: 'open', label: '开放', items: ghIssues.value.filter(i => i.state === 'open') },
      { key: 'closed', label: '已关闭', items: ghIssues.value.filter(i => i.state === 'closed') },
    ]
  }
  // 按标签分组
  const labelMap: Record<string, any[]> = {}
  for (const issue of ghIssues.value) {
    if (!issue.labels?.length) {
      const key = '无标签'
      if (!labelMap[key]) labelMap[key] = []
      labelMap[key].push(issue)
    } else {
      for (const label of issue.labels) {
        if (!labelMap[label]) labelMap[label] = []
        labelMap[label].push(issue)
      }
    }
  }
  return Object.entries(labelMap).map(([key, items]) => ({
    key,
    label: key,
    items,
  }))
})

async function fetchIssues() {
  issuesLoading.value = true
  try {
    ghIssues.value = await api<any[]>(`/api/repos/github-issues/?repo=${route.params.id}`)
  } catch (e) {
    console.error('Failed to load GitHub issues:', e)
  } finally {
    issuesLoading.value = false
  }
}

const toast = useToast()

async function handleSync() {
  syncing.value = true
  try {
    const data = await api<any>(`/api/repos/${route.params.id}/sync/`, { method: 'POST' })
    repo.value = data
    await fetchIssues()
    toast.add({ title: `已同步 ${ghIssues.value.length} 条 Issue`, color: 'success' })
  } catch (e: any) {
    console.error('Sync failed:', e)
    const detail = e?.data?.detail || e?.response?._data?.detail || '同步失败，请重试'
    toast.add({ title: detail, color: 'error' })
  } finally {
    syncing.value = false
  }
}

onMounted(async () => {
  try {
    const [repoData] = await Promise.all([
      api<any>(`/api/repos/${route.params.id}/`),
    ])
    repo.value = repoData
    await fetchIssues()
  } catch (e) {
    console.error('Failed to load repo:', e)
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/repos/[id].vue
git commit -m "feat(repos): rewrite detail page with dashboard, kanban/list, info drawer"
```

---

### Task 6: End-to-end verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Manual smoke test**

Start backend and frontend dev servers, then verify:
1. `/app/repos` — cards show repo name (bold), full_name (small), issue counts
2. `/app/repos/<id>` — dashboard stats display, kanban/list toggle works, grouping dropdown switches columns
3. Info icon opens slideover with repo details
4. Sync button triggers refresh and updates counts
5. Issues page kanban still works with drag-and-drop

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address issues found during smoke testing"
```
