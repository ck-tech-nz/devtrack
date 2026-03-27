# AI Analysis Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple AI analysis results from Issue text fields into a dedicated API endpoint, and move AI display to the sidebar.

**Architecture:** New `GET /api/issues/{id}/analyses/` endpoint reads from existing `Analysis` model. Backend stops appending to Issue fields. Frontend fetches analyses separately and renders them in the sidebar.

**Tech Stack:** Django REST Framework, Nuxt 4 (Vue 3), existing `Analysis` model

**Spec:** `docs/superpowers/specs/2026-03-25-ai-analysis-separation-design.md`

---

### Task 1: Backend — New analyses endpoint

**Files:**
- Modify: `backend/apps/issues/views.py` (add `IssueAnalysesView`)
- Modify: `backend/apps/issues/urls.py` (register route)
- Create: `backend/tests/test_issue_analyses.py`

- [ ] **Step 1: Write failing tests for the new endpoint**

Create `backend/tests/test_issue_analyses.py`:

```python
import pytest
from tests.factories import IssueFactory, AnalysisFactory, UserFactory


@pytest.mark.django_db
class TestIssueAnalysesEndpoint:
    def test_list_analyses_returns_done(self, auth_client):
        issue = IssueFactory()
        user = UserFactory(name="CK")
        AnalysisFactory(
            analysis_type="issue_code_analysis",
            issue=issue,
            status="done",
            triggered_by="manual",
            triggered_by_user=user,
            parsed_result={"target_field": "cause", "content": "根因在 models.py"},
        )
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        item = resp.data[0]
        assert item["status"] == "done"
        assert item["results"] == {"cause": "根因在 models.py"}
        assert item["triggered_by_user"] == "CK"
        assert item["error_message"] is None

    def test_list_analyses_failed_has_error(self, auth_client):
        issue = IssueFactory()
        AnalysisFactory(
            analysis_type="issue_code_analysis",
            issue=issue,
            status="failed",
            error_message="分析超时",
        )
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 200
        assert resp.data[0]["results"] is None
        assert resp.data[0]["error_message"] == "分析超时"

    def test_list_analyses_running_has_no_results(self, auth_client):
        issue = IssueFactory()
        AnalysisFactory(
            analysis_type="issue_code_analysis",
            issue=issue,
            status="running",
        )
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 200
        assert resp.data[0]["results"] is None
        assert resp.data[0]["error_message"] is None

    def test_list_analyses_excludes_other_types(self, auth_client):
        issue = IssueFactory()
        AnalysisFactory(analysis_type="team_insights", issue=issue, status="done")
        AnalysisFactory(analysis_type="issue_code_analysis", issue=issue, status="done",
                        parsed_result={"target_field": "cause", "content": "test"})
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert len(resp.data) == 1

    def test_list_analyses_ordered_newest_first(self, auth_client):
        issue = IssueFactory()
        a1 = AnalysisFactory(analysis_type="issue_code_analysis", issue=issue, status="done",
                             parsed_result={"target_field": "cause", "content": "old"})
        a2 = AnalysisFactory(analysis_type="issue_code_analysis", issue=issue, status="done",
                             parsed_result={"target_field": "cause", "content": "new"})
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.data[0]["id"] == a2.id
        assert resp.data[1]["id"] == a1.id

    def test_list_analyses_requires_auth(self, api_client):
        issue = IssueFactory()
        resp = api_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_issue_analyses.py -v`
Expected: FAIL (404 — route not registered yet)

- [ ] **Step 3: Implement `IssueAnalysesView` and register route**

Add to `backend/apps/issues/views.py` (after existing imports, add `from apps.ai.models import Analysis`; after `IssueAIStatusView`):

```python
class IssueAnalysesView(APIView):
    """GET /api/issues/{id}/analyses/ — 返回该 Issue 的 AI 分析历史"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)

        analyses = (
            Analysis.objects
            .filter(issue=issue, analysis_type="issue_code_analysis")
            .select_related("triggered_by_user")
            .order_by("-created_at")
        )

        data = []
        for a in analyses:
            results = None
            if a.status == Analysis.Status.DONE and a.parsed_result:
                pr = a.parsed_result
                if "target_field" in pr:
                    results = {pr["target_field"]: pr.get("content", "")}
                else:
                    results = {k: v for k, v in pr.items()
                              if k in ("cause", "solution", "remark") and v}

            data.append({
                "id": a.id,
                "status": a.status,
                "triggered_by": a.triggered_by,
                "triggered_by_user": (
                    a.triggered_by_user.name or a.triggered_by_user.username
                ) if a.triggered_by_user else None,
                "created_at": a.created_at.isoformat(),
                "error_message": a.error_message if a.status == Analysis.Status.FAILED else None,
                "results": results,
            })

        return Response(data)
```

Add to `backend/apps/issues/urls.py`:
- Import: add `IssueAnalysesView` to the import list
- Route: `path("<int:pk>/analyses/", IssueAnalysesView.as_view(), name="issue-analyses"),`

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_issue_analyses.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/issues/views.py backend/apps/issues/urls.py backend/tests/test_issue_analyses.py
git commit -m "feat(api): add GET /api/issues/{id}/analyses/ endpoint"
```

---

### Task 2: Backend — Remove `_append_ai_content` from service

**Files:**
- Modify: `backend/apps/ai/services.py:306` (remove `_append_ai_content` call)
- Modify: `backend/apps/ai/services.py:321-330` (remove `_append_ai_content` method)
- Modify: `backend/tests/test_issue_analysis.py` (update existing tests that assert on Issue field appending)

- [ ] **Step 1: Write test verifying AI analysis no longer modifies Issue fields**

Add to `backend/tests/test_issue_analyses.py` (note: uses same `settings.REPO_CLONE_DIR` pattern as existing tests since `local_path` is a computed property, not a model field):

```python
import json
from unittest.mock import patch


@pytest.mark.django_db
class TestIssueAnalysisServiceNoAppend:
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        from tests.factories import RepoFactory, PromptFactory, LLMConfigFactory
        settings.REPO_CLONE_DIR = "/tmp/test_repos"
        LLMConfigFactory(is_default=True)
        PromptFactory(
            slug="issue_code_analysis",
            system_prompt="你是代码分析专家",
            user_prompt_template="分析问题: {title}\n描述: {description}",
        )
        self.repo = RepoFactory(clone_status="cloned", full_name="org/test-repo")

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analysis_does_not_modify_issue_fields(self, MockRunner):
        from apps.ai.services import IssueAnalysisService

        issue = IssueFactory(repo=self.repo, cause="用户写的原因", solution="", remark="")
        mock_instance = MockRunner.return_value
        mock_instance.run.return_value = json.dumps({
            "target_field": "cause",
            "content": "AI分析结果"
        })

        svc = IssueAnalysisService()
        analysis = svc.analyze(issue, triggered_by="manual")

        issue.refresh_from_db()
        assert issue.cause == "用户写的原因"  # unchanged — AI result only in Analysis.parsed_result
        assert analysis.status == "done"
        assert analysis.parsed_result["target_field"] == "cause"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_issue_analyses.py::TestIssueAnalysisServiceNoAppend -v`
Expected: FAIL (cause will contain appended AI content)

- [ ] **Step 3: Remove `_append_ai_content` call and method**

In `backend/apps/ai/services.py`:
- Line 306: Remove `self._append_ai_content(issue, target_field, content)`
- Lines 321-330: Remove the entire `_append_ai_content` method

Also remove the now-unused `transaction` import from `django.db` if nothing else uses it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_issue_analyses.py::TestIssueAnalysisServiceNoAppend -v`
Expected: PASS

- [ ] **Step 5: Update existing tests in `test_issue_analysis.py`**

Three tests in `backend/tests/test_issue_analysis.py` assert on the old behavior and must be updated:

**`test_analyze_appends_to_cause`** (line 27): Rename and update — it should now verify `parsed_result` instead of Issue field:

```python
@patch("apps.ai.services.OpenCodeRunner")
def test_analyze_stores_result_in_parsed_result(self, MockRunner):
    mock_instance = MockRunner.return_value
    mock_instance.run.return_value = json.dumps({
        "target_field": "cause",
        "content": "根因是空指针"
    })
    analysis = self.svc.analyze(self.issue, triggered_by="manual")
    assert analysis.status == "done"
    assert analysis.parsed_result["target_field"] == "cause"
    assert analysis.parsed_result["content"] == "根因是空指针"
    self.issue.refresh_from_db()
    assert "根因是空指针" not in (self.issue.cause or "")
```

**`test_analyze_rejects_invalid_field`** (line 42): Invalid `target_field` no longer raises (since `_append_ai_content` is gone). The AI output gets stored in `parsed_result` with `target_field="remark"` (fallback). Update:

```python
@patch("apps.ai.services.OpenCodeRunner")
def test_analyze_invalid_field_falls_back_to_remark(self, MockRunner):
    mock_instance = MockRunner.return_value
    mock_instance.run.return_value = json.dumps({
        "target_field": "status",
        "content": "恶意内容"
    })
    analysis = self.svc.analyze(self.issue, triggered_by="manual")
    assert analysis.status == "done"
    assert analysis.parsed_result["target_field"] == "remark"
```

**`test_analyze_preserves_existing_content`** (line 90): No longer meaningful since AI never touches Issue fields. Remove this test entirely.

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `cd backend && uv run pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/apps/ai/services.py backend/tests/test_issue_analyses.py backend/tests/test_issue_analysis.py
git commit -m "refactor: remove _append_ai_content, stop writing AI results to Issue fields"
```

---

### Task 3: Backend — Clean up signal dead guard

**Files:**
- Modify: `backend/apps/issues/signals.py:10-13`

- [ ] **Step 1: Simplify the signal**

In `backend/apps/issues/signals.py`, replace lines 10-13:

```python
    elif update_fields and "description" in update_fields:
        # Only trigger on explicit description updates (update_fields specified)
        # Skip AI-appended fields to prevent loops
        if not (set(update_fields) & {"cause", "solution", "remark"}):
            _maybe_analyze(instance, triggered_by="auto")
```

With:

```python
    elif update_fields and "description" in update_fields:
        _maybe_analyze(instance, triggered_by="auto")
```

The loop guard is no longer needed because `_append_ai_content` has been removed.

- [ ] **Step 2: Run full test suite**

Run: `cd backend && uv run pytest -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/apps/issues/signals.py
git commit -m "refactor: remove dead loop guard from issue signal"
```

---

### Task 4: Frontend — Add analyses fetching and sidebar display

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Add analyses state and fetch function**

In the `<script setup>` section, after `let pollTimer` (line 316), add:

```typescript
const analyses = ref<any[]>([])

async function fetchAnalyses() {
  if (!issue.value?.id) return
  analyses.value = await api<any[]>(`/api/issues/${issue.value.id}/analyses/`).catch(() => []) || []
}
```

- [ ] **Step 2: Call `fetchAnalyses` on mount**

In `onMounted` (line 598), after `checkRunningAnalysis()` (line 614), add:

```typescript
  fetchAnalyses()
```

- [ ] **Step 3: Update poll completion to fetch analyses**

In `pollAnalysisStatus` (line 434), change the done/failed handler (lines 441-444):

From:
```typescript
        if (res.status === 'done' || res.status === 'failed') {
          clearInterval(pollTimer!)
          aiAnalyzing.value = false
          await fetchIssue()
        }
```

To:
```typescript
        if (res.status === 'done' || res.status === 'failed') {
          clearInterval(pollTimer!)
          aiAnalyzing.value = false
          await fetchAnalyses()
        }
```

- [ ] **Step 4: Replace sidebar AI section with analysis history**

Replace the sidebar "AI 分析" card (lines 190-208) with:

```html
<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5 space-y-3">
  <div class="flex items-center justify-between">
    <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">AI 分析</h3>
    <div class="flex items-center gap-2">
      <ServiceStatusDot :online="isOnline('ai')" />
      <UButton
        v-if="issue.repo"
        size="xs"
        variant="soft"
        icon="i-heroicons-cpu-chip"
        :loading="aiAnalyzing"
        :disabled="aiAnalyzing || issueRepo?.clone_status !== 'cloned'"
        @click="triggerAIAnalysis"
      >{{ aiAnalyzing ? '分析中...' : '分析' }}</UButton>
    </div>
  </div>

  <!-- 运行状态 -->
  <div v-if="aiAnalyzing" class="space-y-2">
    <div class="flex items-center gap-2">
      <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-blue-500 animate-spin" />
      <span class="text-sm text-blue-500 dark:text-blue-400">正在分析代码...</span>
    </div>
    <div class="text-xs text-gray-400">opencode 正在分析仓库代码，通常需要 1-3 分钟</div>
    <div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 overflow-hidden">
      <div class="bg-blue-500 h-1.5 rounded-full ai-progress-bar"></div>
    </div>
  </div>

  <!-- 前置条件提示 -->
  <div v-else-if="!issue.repo" class="text-sm text-gray-400 dark:text-gray-500">请先关联仓库</div>
  <div v-else-if="issueRepo?.clone_status !== 'cloned'" class="text-sm text-gray-400 dark:text-gray-500">请先同步仓库代码</div>

  <!-- 分析历史 -->
  <div v-if="analyses.length" class="space-y-2 max-h-96 overflow-y-auto">
    <div v-for="a in analyses" :key="a.id" class="rounded-lg border text-sm"
      :class="a.status === 'failed' ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20' : 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'">
      <div class="px-3 py-2">
        <div class="flex items-center justify-between text-xs mb-1">
          <div class="flex items-center gap-1" :class="a.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'">
            <UIcon name="i-heroicons-cpu-chip" class="w-3 h-3" />
            <span>{{ a.created_at?.slice(0, 16).replace('T', ' ') }}</span>
          </div>
          <UBadge :color="a.triggered_by === 'manual' ? 'primary' : 'neutral'" variant="subtle" size="xs">
            {{ a.triggered_by === 'manual' ? '手动' : '自动' }}
          </UBadge>
        </div>
        <div v-if="a.status === 'failed'" class="text-xs text-red-600 dark:text-red-400">{{ a.error_message }}</div>
        <div v-else-if="a.status === 'running'" class="text-xs text-blue-500">分析中...</div>
        <template v-else-if="a.results">
          <div v-for="(content, field) in a.results" :key="field" class="mt-1">
            <div class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ fieldLabel(field) }}</div>
            <div class="text-sm whitespace-pre-wrap mt-0.5 text-gray-700 dark:text-gray-300 max-h-40 overflow-y-auto">{{ content }}</div>
          </div>
        </template>
      </div>
    </div>
  </div>
  <p v-else-if="!aiAnalyzing && issue.repo && issueRepo?.clone_status === 'cloned'" class="text-sm text-gray-400 dark:text-gray-500">暂无分析记录</p>
</div>
```

- [ ] **Step 5: Add `fieldLabel` helper**

In `<script setup>`, add after `parseAIContent` function (or anywhere in the script):

```typescript
function fieldLabel(field: string) {
  const labels: Record<string, string> = { cause: '原因分析', solution: '解决方案', remark: '备注' }
  return labels[field] || field
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "feat(frontend): display AI analyses in sidebar with history cards"
```

---

### Task 5: Frontend — Clean up main content area

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Remove AI button from page header**

In the header (lines 19-28), remove the AI 分析 button:

```html
        <UButton
          v-if="issue.repo"
          color="primary"
          variant="soft"
          size="sm"
          icon="i-heroicons-cpu-chip"
          :loading="aiAnalyzing"
          :disabled="aiAnalyzing || issueRepo?.clone_status !== 'cloned'"
          @click="triggerAIAnalysis"
        >{{ aiAnalyzing ? '分析中...' : 'AI 分析' }}</UButton>
```

- [ ] **Step 2: Simplify cause/solution/remark fields**

Replace the 分析记录 section (lines 91-143) — remove all `parseAIContent` rendering, keep only the textareas:

```html
<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
  <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">分析记录</h3>
  <div class="space-y-4">
    <div class="form-row">
      <label>备注</label>
      <UTextarea v-model="form.remark" :rows="2" placeholder="备注信息" />
    </div>
    <div class="form-row">
      <label>原因分析</label>
      <UTextarea v-model="form.cause" :rows="3" placeholder="问题原因" />
    </div>
    <div class="form-row">
      <label>解决方案</label>
      <UTextarea v-model="form.solution" :rows="3" placeholder="解决办法" />
    </div>
  </div>
</div>
```

- [ ] **Step 3: Remove `parseAIContent` function**

Delete the `parseAIContent` function (lines 456-470).

- [ ] **Step 4: Verify frontend runs without errors**

Run: `cd frontend && npm run dev`
Open: `http://localhost:3004/app/issues/{any-id}` — verify:
- Sidebar shows AI section with trigger button and analysis history
- Main content shows clean textareas without AI blocks
- AI trigger button works and polls correctly

- [ ] **Step 5: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "refactor(frontend): clean up AI content from Issue fields, remove parseAIContent"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests pass

- [ ] **Step 2: Manual end-to-end test**

1. Open an issue with a linked + cloned repo
2. Click sidebar "分析" button
3. Verify progress bar shows in sidebar
4. Wait for completion, verify analysis card appears in sidebar
5. Verify cause/solution/remark textareas are NOT modified
6. Refresh page, verify analysis history persists

- [ ] **Step 3: Final commit (if any cleanup needed)**
