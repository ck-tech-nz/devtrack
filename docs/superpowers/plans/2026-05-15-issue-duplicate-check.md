# Issue Duplicate Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the user blurs the title or description field in the "新建问题" modal, send the new content + open candidate issues in the same project to the LLM, and show an inline amber warning under the title field listing any AI-flagged near-duplicates.

**Architecture:** New backend `POST /api/issues/check-duplicate/` APIView, calls `apps.ai.client.LLMClient.complete()` with a `Prompt(slug="issue_duplicate_check")` row seeded from a version-controlled JSON via a data migration. Frontend adds reactive state and a blur handler in `frontend/app/pages/app/issues/index.vue`, plus a `blur` emit on `MarkdownEditor` so the description field can re-trigger the check. Failure modes (missing prompt, missing LLM config, bad JSON, hallucinated ids, timeout) silently degrade to no warning.

**Tech Stack:** Django 5 + DRF, openai SDK (already wrapped by `apps/ai/client.py`), Nuxt 4 + Vue 3 + Nuxt UI, pytest-django + factory-boy.

**Reference design doc:** [docs/superpowers/specs/2026-05-15-issue-duplicate-check-design.md](../specs/2026-05-15-issue-duplicate-check-design.md)

---

## File Structure

**Backend (create):**
- `backend/apps/ai/seed_prompts/__init__.py` — make the seed-prompts dir an importable package (empty file).
- `backend/apps/ai/seed_prompts/issue_duplicate_check.json` — version-controlled prompt content (system / user / model / temperature).
- `backend/apps/ai/migrations/0003_seed_duplicate_check_prompt.py` — data migration that loads the JSON and `get_or_create`s the `Prompt` row.
- `backend/apps/issues/services.py` — new module holding `check_duplicates(user, project_id, title, description)` and the JSON-parsing helper. Keeps view thin and lets tests mock the LLM at one stable seam.
- `backend/tests/test_issues_duplicate_check.py` — full coverage of the service and the endpoint.

**Backend (modify):**
- `backend/apps/issues/serializers.py` — add `DuplicateCheckInputSerializer`.
- `backend/apps/issues/views.py` — add `IssueCheckDuplicateView` APIView.
- `backend/apps/issues/urls.py` — wire `check-duplicate/` route.

**Frontend (modify):**
- `frontend/app/components/MarkdownEditor.vue` — add `blur` event emit on the inner textarea so the parent can re-trigger the duplicate check when the description loses focus.
- `frontend/app/pages/app/issues/index.vue` — add reactive state, helpers, watchers, blur handlers, and the inline warning UI.

Each unit has one job: the seed JSON is data only; the migration is wiring only; the service holds business logic; the serializer is validation only; the view is HTTP plumbing only. Tests pin the service contract so refactors of the view stay safe.

---

## Task 1: Add the seed-prompts package and the prompt JSON

**Files:**
- Create: `backend/apps/ai/seed_prompts/__init__.py`
- Create: `backend/apps/ai/seed_prompts/issue_duplicate_check.json`

- [ ] **Step 1: Create the empty package file**

```bash
mkdir -p backend/apps/ai/seed_prompts
```

Create `backend/apps/ai/seed_prompts/__init__.py` as an empty file.

- [ ] **Step 2: Create the prompt JSON**

Create `backend/apps/ai/seed_prompts/issue_duplicate_check.json` with the exact content:

```json
{
  "name": "新建问题去重检查",
  "system_prompt": "你是问题去重助手。给定一组候选问题（包含 id/title/description/status）和一条新问题（title + description），判断候选中哪些与新问题指向同一个 bug 或需求。只在确实可能重复时返回；语义不同就不要列出。严格返回 JSON 对象，形如 {\"duplicates\": [{\"id\": <int>, \"reason\": \"<不超过 30 字的中文说明>\"}]}，最多列出 5 条，按相似度从高到低排序。没有重复时返回 {\"duplicates\": []}。",
  "user_prompt_template": "候选问题（JSON）:\n{candidates_json}\n\n新问题:\n标题: {new_title}\n描述: {new_description}",
  "llm_model": "gpt-4o-mini",
  "temperature": 0.2,
  "is_active": true
}
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/ai/seed_prompts/__init__.py backend/apps/ai/seed_prompts/issue_duplicate_check.json
git commit -m "feat(ai): add seed JSON for issue duplicate-check prompt"
```

---

## Task 2: Add the data migration that seeds the Prompt row

**Files:**
- Create: `backend/apps/ai/migrations/0003_seed_duplicate_check_prompt.py`
- Create: `backend/tests/test_issues_duplicate_check.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_issues_duplicate_check.py` with:

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from apps.ai.models import Prompt


@pytest.mark.django_db
def test_duplicate_check_prompt_is_seeded():
    """The data migration must have created the issue_duplicate_check Prompt row."""
    prompt = Prompt.objects.filter(slug="issue_duplicate_check").first()
    assert prompt is not None, "Prompt row was not seeded"
    assert prompt.is_active
    assert "{candidates_json}" in prompt.user_prompt_template
    assert "{new_title}" in prompt.user_prompt_template
    assert "{new_description}" in prompt.user_prompt_template
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`:

```bash
uv run pytest tests/test_issues_duplicate_check.py::test_duplicate_check_prompt_is_seeded -v
```

Expected: FAIL — `prompt is None` because no migration has seeded it yet.

- [ ] **Step 3: Write the data migration**

Create `backend/apps/ai/migrations/0003_seed_duplicate_check_prompt.py`:

```python
import json
from pathlib import Path

from django.db import migrations


PROMPT_SLUG = "issue_duplicate_check"
SEED_FILE = Path(__file__).resolve().parent.parent / "seed_prompts" / "issue_duplicate_check.json"


def seed_prompt(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    Prompt.objects.get_or_create(
        slug=PROMPT_SLUG,
        defaults={
            "name": data["name"],
            "system_prompt": data["system_prompt"],
            "user_prompt_template": data["user_prompt_template"],
            "llm_model": data["llm_model"],
            "temperature": data["temperature"],
            "is_active": data["is_active"],
        },
    )


def unseed_prompt(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug=PROMPT_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0002_seed_celery_periodic_tasks"),
    ]

    operations = [
        migrations.RunPython(seed_prompt, reverse_code=unseed_prompt),
    ]
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/test_issues_duplicate_check.py::test_duplicate_check_prompt_is_seeded -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/ai/migrations/0003_seed_duplicate_check_prompt.py backend/tests/test_issues_duplicate_check.py
git commit -m "feat(ai): seed duplicate-check Prompt via data migration"
```

---

## Task 3: Add the input serializer

**Files:**
- Modify: `backend/apps/issues/serializers.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_issues_duplicate_check.py`:

```python
def test_input_serializer_requires_project_and_title():
    from apps.issues.serializers import DuplicateCheckInputSerializer

    s = DuplicateCheckInputSerializer(data={"title": "abc"})
    assert not s.is_valid()
    assert "project" in s.errors

    s = DuplicateCheckInputSerializer(data={"project": 1})
    assert not s.is_valid()
    assert "title" in s.errors


def test_input_serializer_defaults_description_to_empty():
    from apps.issues.serializers import DuplicateCheckInputSerializer

    s = DuplicateCheckInputSerializer(data={"project": 1, "title": "abc"})
    assert s.is_valid(), s.errors
    assert s.validated_data["description"] == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_issues_duplicate_check.py::test_input_serializer_requires_project_and_title tests/test_issues_duplicate_check.py::test_input_serializer_defaults_description_to_empty -v
```

Expected: FAIL — `DuplicateCheckInputSerializer` does not exist.

- [ ] **Step 3: Add the serializer**

Append to `backend/apps/issues/serializers.py` (after the existing class definitions):

```python
class DuplicateCheckInputSerializer(serializers.Serializer):
    project = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_issues_duplicate_check.py::test_input_serializer_requires_project_and_title tests/test_issues_duplicate_check.py::test_input_serializer_defaults_description_to_empty -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/issues/serializers.py backend/tests/test_issues_duplicate_check.py
git commit -m "feat(issues): add DuplicateCheckInputSerializer"
```

---

## Task 4a: Create the service module skeleton + the empty-guard cases

**Files:**
- Create: `backend/apps/issues/services.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_issues_duplicate_check.py`:

```python
from tests.factories import IssueFactory, ProjectFactory, LLMConfigFactory


@pytest.mark.django_db
def test_check_duplicates_returns_empty_when_title_too_short():
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    assert check_duplicates(project_id=project.id, title="ab", description="") == []


@pytest.mark.django_db
def test_check_duplicates_returns_empty_when_project_missing():
    from apps.issues.services import check_duplicates

    assert check_duplicates(project_id=None, title="登录页报错", description="") == []


@pytest.mark.django_db
def test_check_duplicates_returns_empty_when_no_open_candidates():
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    IssueFactory(project=project, status="已关闭", title="登录失败")
    IssueFactory(project=project, status="已发布", title="登录失败")
    assert check_duplicates(project_id=project.id, title="登录失败", description="") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_issues_duplicate_check.py -k "check_duplicates_returns_empty" -v
```

Expected: FAIL — `apps.issues.services` module does not exist.

- [ ] **Step 3: Create the service module with the guard logic only**

Create `backend/apps/issues/services.py`:

```python
"""Issue-level services (kept separate from views and serializers).

The current entry point is `check_duplicates`, used by the create-issue
modal to surface near-duplicate open issues before submission.
"""
import json
import logging

from apps.ai.client import LLMClient
from apps.ai.models import LLMConfig, Prompt
from .models import Issue


logger = logging.getLogger(__name__)

CLOSED_STATUSES = ("已关闭", "已发布")
MIN_TITLE_LENGTH = 3
MAX_CANDIDATES = 100
MAX_MATCHES = 5
DESCRIPTION_TRUNCATE = 300
LLM_TIMEOUT_SECONDS = 15
DUPLICATE_PROMPT_SLUG = "issue_duplicate_check"


def check_duplicates(project_id, title, description):
    """Return up to MAX_MATCHES AI-flagged near-duplicate open issues in the project.

    Returns [] (silently) when any precondition is unmet: missing project,
    short title, no candidates, no prompt, no LLM config, malformed JSON,
    or any exception raised by the LLM call.
    """
    if not project_id:
        return []
    title = (title or "").strip()
    if len(title) < MIN_TITLE_LENGTH:
        return []

    candidates = list(
        Issue.objects.filter(project_id=project_id)
        .exclude(status__in=CLOSED_STATUSES)
        .order_by("-id")
        .values("id", "title", "description", "status")[:MAX_CANDIDATES]
    )
    if not candidates:
        return []

    # Placeholder — real LLM call lands in Task 4b.
    return []
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_issues_duplicate_check.py -k "check_duplicates_returns_empty" -v
```

Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/issues/services.py backend/tests/test_issues_duplicate_check.py
git commit -m "feat(issues): add check_duplicates service skeleton with input guards"
```

---

## Task 4b: Wire the LLM call, JSON parsing, and hallucination filter

**Files:**
- Modify: `backend/apps/issues/services.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_issues_duplicate_check.py`:

```python
@pytest.fixture
def duplicate_prompt():
    # Already seeded by migration 0003, but tests may have wiped it via
    # transactions on some setups — ensure it exists for these tests.
    return Prompt.objects.get(slug="issue_duplicate_check")


@pytest.fixture
def default_llm():
    return LLMConfigFactory(is_default=True, is_active=True)


@pytest.mark.django_db
def test_check_duplicates_returns_matches_from_llm(duplicate_prompt, default_llm):
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    a = IssueFactory(project=project, status="待处理", title="登录页 500", description="点登录后报错")
    IssueFactory(project=project, status="进行中", title="完全无关的问题")

    payload = json.dumps({"duplicates": [{"id": a.id, "reason": "同样描述登录页 500"}]})
    with patch("apps.issues.services.LLMClient") as MockClient:
        MockClient.return_value.complete.return_value = payload
        out = check_duplicates(project_id=project.id, title="登录页 500", description="登录按钮 500")

    assert out == [{"id": a.id, "title": "登录页 500", "status": "待处理", "reason": "同样描述登录页 500"}]


@pytest.mark.django_db
def test_check_duplicates_filters_hallucinated_ids(duplicate_prompt, default_llm):
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    real = IssueFactory(project=project, status="待处理", title="A")
    payload = json.dumps({"duplicates": [
        {"id": real.id, "reason": "真的"},
        {"id": 999999, "reason": "幻觉"},
    ]})
    with patch("apps.issues.services.LLMClient") as MockClient:
        MockClient.return_value.complete.return_value = payload
        out = check_duplicates(project_id=project.id, title="abc", description="")

    assert [c["id"] for c in out] == [real.id]


@pytest.mark.django_db
def test_check_duplicates_caps_at_five(duplicate_prompt, default_llm):
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    issues = [IssueFactory(project=project, status="待处理", title=f"T{i}") for i in range(7)]
    payload = json.dumps({"duplicates": [{"id": i.id, "reason": "x"} for i in issues]})
    with patch("apps.issues.services.LLMClient") as MockClient:
        MockClient.return_value.complete.return_value = payload
        out = check_duplicates(project_id=project.id, title="abc", description="")

    assert len(out) == 5


@pytest.mark.django_db
def test_check_duplicates_returns_empty_on_invalid_json(duplicate_prompt, default_llm):
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    IssueFactory(project=project, status="待处理", title="A")
    with patch("apps.issues.services.LLMClient") as MockClient:
        MockClient.return_value.complete.return_value = "not json at all"
        out = check_duplicates(project_id=project.id, title="abc", description="")

    assert out == []


@pytest.mark.django_db
def test_check_duplicates_returns_empty_on_llm_exception(duplicate_prompt, default_llm):
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    IssueFactory(project=project, status="待处理", title="A")
    with patch("apps.issues.services.LLMClient") as MockClient:
        MockClient.return_value.complete.side_effect = RuntimeError("boom")
        out = check_duplicates(project_id=project.id, title="abc", description="")

    assert out == []


@pytest.mark.django_db
def test_check_duplicates_returns_empty_when_no_llm_config(duplicate_prompt):
    from apps.issues.services import check_duplicates

    project = ProjectFactory()
    IssueFactory(project=project, status="待处理", title="A")
    # No LLMConfig with is_default=True exists.
    assert check_duplicates(project_id=project.id, title="abc", description="") == []


@pytest.mark.django_db
def test_check_duplicates_returns_empty_when_no_prompt(default_llm):
    from apps.issues.services import check_duplicates

    Prompt.objects.filter(slug="issue_duplicate_check").update(is_active=False)
    project = ProjectFactory()
    IssueFactory(project=project, status="待处理", title="A")
    assert check_duplicates(project_id=project.id, title="abc", description="") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_issues_duplicate_check.py -v
```

Expected: the new tests FAIL because the service still returns `[]` at the placeholder. Previously-passing tests still pass.

- [ ] **Step 3: Implement the LLM call and parsing**

Replace the body of `check_duplicates` in `backend/apps/issues/services.py` with the full implementation:

```python
def check_duplicates(project_id, title, description):
    """Return up to MAX_MATCHES AI-flagged near-duplicate open issues in the project.

    Returns [] (silently) when any precondition is unmet: missing project,
    short title, no candidates, no prompt, no LLM config, malformed JSON,
    or any exception raised by the LLM call.
    """
    if not project_id:
        return []
    title = (title or "").strip()
    if len(title) < MIN_TITLE_LENGTH:
        return []

    candidates = list(
        Issue.objects.filter(project_id=project_id)
        .exclude(status__in=CLOSED_STATUSES)
        .order_by("-id")
        .values("id", "title", "description", "status")[:MAX_CANDIDATES]
    )
    if not candidates:
        return []

    prompt = Prompt.objects.filter(slug=DUPLICATE_PROMPT_SLUG, is_active=True).first()
    if not prompt:
        return []

    llm_config = prompt.llm_config or LLMConfig.objects.filter(is_default=True, is_active=True).first()
    if not llm_config:
        return []

    truncated = [
        {
            "id": c["id"],
            "title": c["title"],
            "description": (c["description"] or "")[:DESCRIPTION_TRUNCATE],
            "status": c["status"],
        }
        for c in candidates
    ]
    by_id = {c["id"]: c for c in candidates}

    try:
        user_prompt = prompt.user_prompt_template.format(
            candidates_json=json.dumps(truncated, ensure_ascii=False),
            new_title=title,
            new_description=description or "",
        )
        raw = LLMClient(llm_config).complete(
            model=prompt.llm_model,
            system_prompt=prompt.system_prompt,
            user_prompt=user_prompt,
            temperature=prompt.temperature,
        )
        parsed = json.loads(raw)
        duplicates = parsed.get("duplicates") or []
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("duplicate_check: bad LLM response shape", exc_info=True)
        return []
    except Exception:
        logger.warning("duplicate_check: LLM call failed", exc_info=True)
        return []

    out = []
    for entry in duplicates:
        cid = entry.get("id") if isinstance(entry, dict) else None
        if cid in by_id:
            cand = by_id[cid]
            out.append({
                "id": cand["id"],
                "title": cand["title"],
                "status": cand["status"],
                "reason": (entry.get("reason") or "")[:200],
            })
        if len(out) >= MAX_MATCHES:
            break

    logger.info(
        "duplicate_check project=%s candidates=%d matches=%d",
        project_id, len(candidates), len(out),
    )
    return out
```

- [ ] **Step 4: Run the tests to verify they all pass**

```bash
uv run pytest tests/test_issues_duplicate_check.py -v
```

Expected: PASS for every test added so far.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/issues/services.py backend/tests/test_issues_duplicate_check.py
git commit -m "feat(issues): implement check_duplicates LLM call and JSON parsing"
```

---

## Task 5: Add the API view and URL

**Files:**
- Modify: `backend/apps/issues/views.py`
- Modify: `backend/apps/issues/urls.py`

- [ ] **Step 1: Write the failing endpoint tests**

Append to `backend/tests/test_issues_duplicate_check.py`:

```python
@pytest.mark.django_db
def test_endpoint_returns_candidates(auth_client, site_settings, duplicate_prompt, default_llm):
    project = ProjectFactory()
    open_issue = IssueFactory(project=project, status="待处理", title="登录页 500", description="点登录后报错")

    payload = json.dumps({"duplicates": [{"id": open_issue.id, "reason": "同样描述登录页 500"}]})
    with patch("apps.issues.services.LLMClient") as MockClient:
        MockClient.return_value.complete.return_value = payload
        res = auth_client.post(
            "/api/issues/check-duplicate/",
            data={"project": project.id, "title": "登录页 500", "description": ""},
            format="json",
        )

    assert res.status_code == 200
    body = res.json()
    assert body["candidates"][0]["id"] == open_issue.id
    assert body["candidates"][0]["status"] == "待处理"
    assert body["candidates"][0]["reason"] == "同样描述登录页 500"


@pytest.mark.django_db
def test_endpoint_validates_input(auth_client, site_settings):
    res = auth_client.post("/api/issues/check-duplicate/", data={}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_endpoint_returns_empty_when_no_open_issues(auth_client, site_settings, duplicate_prompt, default_llm):
    project = ProjectFactory()
    IssueFactory(project=project, status="已关闭", title="A")
    res = auth_client.post(
        "/api/issues/check-duplicate/",
        data={"project": project.id, "title": "abc", "description": ""},
        format="json",
    )
    assert res.status_code == 200
    assert res.json() == {"candidates": []}


@pytest.mark.django_db
def test_endpoint_requires_auth(api_client):
    res = api_client.post(
        "/api/issues/check-duplicate/",
        data={"project": 1, "title": "abc"},
        format="json",
    )
    assert res.status_code in (401, 403)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_issues_duplicate_check.py -k "endpoint" -v
```

Expected: FAIL — the route does not exist; you should see 404s.

- [ ] **Step 3: Add the view**

Append to `backend/apps/issues/views.py`:

```python
class IssueCheckDuplicateView(APIView):
    """POST /api/issues/check-duplicate/ — AI-driven near-duplicate detection.

    Used by the create-issue modal on title/description blur. Returns up to
    five open issues in the same project that the LLM judged similar. Silent
    on configuration or LLM failures: always returns 200 with possibly empty
    candidates so the modal continues to function.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import DuplicateCheckInputSerializer
        from .services import check_duplicates

        serializer = DuplicateCheckInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        candidates = check_duplicates(
            project_id=data["project"],
            title=data["title"],
            description=data["description"],
        )
        return Response({"candidates": candidates})
```

- [ ] **Step 4: Wire the URL**

Edit `backend/apps/issues/urls.py`:

```python
from django.urls import path
from .views import (
    IssueListCreateView, IssueDetailView, BatchUpdateView,
    IssueGitHubCreateView, IssueGitHubLinkView, IssueCloseWithGitHubView,
    IssueAIAnalyzeView, IssueAIStatusView, IssueAnalysesView,
    IssueAttachmentsView, IssueCheckDuplicateView,
)

urlpatterns = [
    path("", IssueListCreateView.as_view(), name="issue-list"),
    path("check-duplicate/", IssueCheckDuplicateView.as_view(), name="issue-check-duplicate"),
    path("batch-update/", BatchUpdateView.as_view(), name="issue-batch-update"),
    path("<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("<int:pk>/attachments/", IssueAttachmentsView.as_view(), name="issue-attachments"),
    path("<int:pk>/github-create/", IssueGitHubCreateView.as_view(), name="issue-github-create"),
    path("<int:pk>/github-link/", IssueGitHubLinkView.as_view(), name="issue-github-link"),
    path("<int:pk>/close-with-github/", IssueCloseWithGitHubView.as_view(), name="issue-close-with-github"),
    path("<int:pk>/ai-analyze/", IssueAIAnalyzeView.as_view(), name="issue-ai-analyze"),
    path("<int:pk>/ai-status/", IssueAIStatusView.as_view(), name="issue-ai-status"),
    path("<int:pk>/analyses/", IssueAnalysesView.as_view(), name="issue-analyses"),
]
```

(The `check-duplicate/` route must come **before** `<int:pk>/` so the literal segment is matched first — Django evaluates patterns top-to-bottom.)

- [ ] **Step 5: Run the full test file to verify everything passes**

```bash
uv run pytest tests/test_issues_duplicate_check.py -v
```

Expected: every test PASSES.

- [ ] **Step 6: Run the broader issue test suite to make sure nothing regressed**

```bash
uv run pytest tests/test_issues.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/issues/views.py backend/apps/issues/urls.py backend/tests/test_issues_duplicate_check.py
git commit -m "feat(issues): expose POST /api/issues/check-duplicate/ for AI duplicate detection"
```

---

## Task 6: Add a `blur` emit to MarkdownEditor

**Files:**
- Modify: `frontend/app/components/MarkdownEditor.vue`

The component currently only emits `update:modelValue` and `upload-complete`. We need parent components to react when the description loses focus. Adding a `blur` event keeps MarkdownEditor a passive transmitter — no business logic changes.

- [ ] **Step 1: Add `blur` to the emits declaration**

Find the `defineEmits` call at the top of `<script setup>` and add a `blur: []` event:

```ts
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'upload-complete': [attachment: { url: string; filename: string; id: string }]
  'blur': []
}>()
```

- [ ] **Step 2: Forward the textarea's native blur**

Find the `<textarea>` in the `<template>`:

```vue
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

Add an `@blur` handler:

```vue
<textarea
  ref="textareaRef"
  :value="modelValue"
  :placeholder="placeholder"
  class="w-full min-h-[260px] p-4 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-y outline-none"
  @input="onTextareaInput"
  @keydown="handleMentionKeydown"
  @paste="handlePaste"
  @blur="emit('blur')"
/>
```

- [ ] **Step 3: Type-check the frontend**

Run from `frontend/`:

```bash
npx nuxi typecheck
```

Expected: no new errors related to MarkdownEditor.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/components/MarkdownEditor.vue
git commit -m "feat(MarkdownEditor): emit blur event from internal textarea"
```

---

## Task 7: Add reactive state and check helper in the create-issue page

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

This task adds the state and the function. Wiring (blur handlers + UI) lands in Task 8 so each commit is independently revertable.

- [ ] **Step 1: Add reactive state**

Find the existing create-issue state block in [frontend/app/pages/app/issues/index.vue](../../frontend/app/pages/app/issues/index.vue) (around the `const newIssue = ref({...})` declaration, line ~353). Immediately **after** the closing `})` of `newIssue`:

```ts
// Duplicate-check state for the create-issue modal.
const dupChecking = ref(false)
const dupCandidates = ref<Array<{ id: number; title: string; status: string; reason: string }>>([])
const dupCheckedKey = ref('')
```

- [ ] **Step 2: Add the check-key helper and runner**

Place the following right after the `dupCheckedKey` declaration:

```ts
function dupCheckKey(): string {
  const p = newIssue.value.project || ''
  const t = newIssue.value.title.trim().toLowerCase()
  const d = (newIssue.value.description || '').trim().toLowerCase()
  return `${p}|${t}|${d}`
}

async function runDuplicateCheck() {
  const projectId = newIssue.value.project
  const title = newIssue.value.title.trim()
  if (!projectId || title.length < 3) {
    dupCandidates.value = []
    return
  }
  const key = dupCheckKey()
  if (key === dupCheckedKey.value) return
  dupCheckedKey.value = key
  dupChecking.value = true
  try {
    const res = await api<{ candidates: Array<{ id: number; title: string; status: string; reason: string }> }>(
      '/api/issues/check-duplicate/',
      {
        method: 'POST',
        body: {
          project: projectId,
          title,
          description: newIssue.value.description || '',
        },
        format: 'json',
      },
    )
    // Discard stale responses if the user edited the form mid-call.
    if (dupCheckKey() === key) dupCandidates.value = res.candidates || []
  } catch {
    dupCandidates.value = []
  } finally {
    dupChecking.value = false
  }
}
```

- [ ] **Step 3: Invalidate results when title or description changes**

After the existing `watch(() => newIssue.value.project, ...)` block (around line ~390), add a separate watch that clears stale matches the moment the user edits either field:

```ts
watch([() => newIssue.value.title, () => newIssue.value.description], () => {
  dupCandidates.value = []
  dupCheckedKey.value = ''
})
```

- [ ] **Step 4: Reset state in `resetCreateForm`**

Find `resetCreateForm()` (around line ~380). Inside the function, after `projectRepos.value = []`, append:

```ts
  dupCandidates.value = []
  dupCheckedKey.value = ''
  dupChecking.value = false
```

The full updated function should read:

```ts
function resetCreateForm() {
  newIssue.value = { project: '', title: '', description: '', priority: 'P2', status: '待处理', labels: [], assignee: defaultAssignee.value, repo: null, reporter: user.value?.name || '' }
  attachmentIds.value = []
  projectRepos.value = []
  dupCandidates.value = []
  dupCheckedKey.value = ''
  dupChecking.value = false
}
```

- [ ] **Step 5: Type-check the frontend**

Run from `frontend/`:

```bash
npx nuxi typecheck
```

Expected: no errors. (`api` is already imported via the existing `useApi()` destructure in this file — no new imports needed.)

- [ ] **Step 6: Commit**

```bash
git add frontend/app/pages/app/issues/index.vue
git commit -m "feat(issues): add duplicate-check state and runner to create-issue modal"
```

---

## Task 8: Wire blur handlers and render the inline warning

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

- [ ] **Step 1: Bind `@blur` to the title input**

Find the title form-row (around line 69-72):

```vue
<div class="form-row">
  <label>标题 <span class="text-red-400">*</span></label>
  <UInput v-model="newIssue.title" placeholder="输入问题标题" />
</div>
```

Replace with:

```vue
<div class="form-row">
  <label>标题 <span class="text-red-400">*</span></label>
  <UInput v-model="newIssue.title" placeholder="输入问题标题" @blur="runDuplicateCheck" />
  <div v-if="dupChecking || dupCandidates.length" class="dup-check-box">
    <p v-if="dupChecking" class="text-xs text-gray-500 dark:text-gray-400">
      正在检查相似问题…
    </p>
    <div v-else>
      <p class="text-sm text-amber-700 dark:text-amber-300 font-medium">
        发现 {{ dupCandidates.length }} 条相似的未关闭问题，请确认是否重复：
      </p>
      <ul class="mt-1.5 space-y-1.5">
        <li v-for="c in dupCandidates" :key="c.id" class="text-sm">
          <div class="flex items-center gap-1.5">
            <NuxtLink
              :to="`/app/issues/${c.id}`"
              target="_blank"
              class="text-crystal-600 dark:text-crystal-400 hover:underline"
            >
              #{{ c.id }} {{ c.title }}
            </NuxtLink>
            <UBadge :color="statusColor(c.status)" variant="subtle" size="xs">{{ c.status }}</UBadge>
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ c.reason }}</p>
        </li>
      </ul>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Bind `@blur` to the MarkdownEditor**

Find the description form-row (around line 73-76):

```vue
<div class="form-row">
  <label>描述</label>
  <MarkdownEditor v-model="newIssue.description" placeholder="详细描述问题" @upload-complete="handleCreateUploadComplete" />
</div>
```

Replace with:

```vue
<div class="form-row">
  <label>描述</label>
  <MarkdownEditor
    v-model="newIssue.description"
    placeholder="详细描述问题"
    @upload-complete="handleCreateUploadComplete"
    @blur="runDuplicateCheck"
  />
</div>
```

- [ ] **Step 3: Add the inline-warning CSS**

Find the `<style>` block in the file. If a scoped style exists for the modal, add the new selectors there; otherwise append to the existing global style block. Add:

```css
.dup-check-box {
  margin-top: 0.5rem;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  background-color: #fffbeb; /* amber-50 */
  border: 1px solid #fde68a; /* amber-200 */
}
:root.dark .dup-check-box {
  background-color: rgba(120, 53, 15, 0.25); /* amber-900/25 */
  border-color: rgba(245, 158, 11, 0.4); /* amber-500/40 */
}
```

Place these alongside the page's other custom selectors. If the file uses `<style scoped>`, scope-leak is not a concern; if not, the `.dup-check-box` class is unique enough to avoid collisions.

- [ ] **Step 4: Type-check the frontend**

```bash
npx nuxi typecheck
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/pages/app/issues/index.vue
git commit -m "feat(issues): show inline AI duplicate warning under title field"
```

---

## Task 9: Manual end-to-end verification

No automated frontend tests exist for this page, so verify manually.

- [ ] **Step 1: Start the backend**

From `backend/`:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

Expected: server on `:8000`, migration `0003_seed_duplicate_check_prompt` reported as applied.

- [ ] **Step 2: Make sure an `LLMConfig` is configured**

In Django admin (`/admin/`), confirm there is an `LLMConfig` row with `is_default=True` and a working `api_key`. If not, create one. Without this, the feature silently no-ops (which is the spec's chosen failure mode).

- [ ] **Step 3: Start the frontend**

From `frontend/`:

```bash
npm run dev
```

Expected: dev server on `:3004` (proxies `/api/**` to backend).

- [ ] **Step 4: Verify the golden path**

Open `http://localhost:3000/app/issues`, click "新建问题":

1. Without picking a project, type a title and blur → no spinner, no warning (project guard).
2. Pick a project that already has an open issue. Type a title similar to the existing issue's title. Tab away.
3. Expected: brief "正在检查相似问题…", then an amber box with `#{id} {title}` link + status badge + AI reason.
4. Click the issue link → opens the existing issue in a new tab; modal stays open.
5. Edit the title slightly → warning disappears immediately.
6. Tab away again → warning re-appears (re-checked).
7. Focus the description, type something, blur → warning is recomputed with title + description (you can confirm via the network panel: a new POST to `/api/issues/check-duplicate/`).

- [ ] **Step 5: Verify the failure modes**

1. Pick a project with no open issues at all → no warning (empty candidate set, no LLM call — confirm via backend log).
2. Use a title with `length < 3` → no check fires.
3. Temporarily set the seeded `Prompt` to `is_active=False` in admin and repeat step 4 → no warning, no error UI.
4. Submit the form while the warning is showing → issue is created; modal closes; the list refreshes. The feature must not block submission.

- [ ] **Step 6: Final commit (only if no fixes were needed)**

If steps 4-5 surfaced bugs, fix them, commit those fixes, and re-verify. Otherwise no commit needed here.

---

## Self-Review

Spec coverage:
- "Backend new endpoint `POST /api/issues/check-duplicate/`" → Task 5.
- "Project-scoped, exclude 已关闭 + 已发布" → Task 4a/4b.
- "Title length ≥ 3, candidate cap at 100 newest, match cap at 5" → Task 4a/4b (`MIN_TITLE_LENGTH`, `MAX_CANDIDATES`, `MAX_MATCHES`).
- "Description truncated to ~300 chars on candidates" → Task 4b.
- "`Prompt(slug="issue_duplicate_check")` seeded via data migration from JSON; `get_or_create` so admin edits survive" → Tasks 1, 2.
- "Silent fail on missing prompt / config / bad JSON / exception" → Task 4b tests cover each branch.
- "Filter out hallucinated ids" → Task 4b test.
- "LLM timeout ~15s" → constant `LLM_TIMEOUT_SECONDS` defined in Task 4a; the openai SDK is invoked through the existing `LLMClient.complete` which does not currently pass a timeout. **Gap:** the spec's timeout requirement is not enforced — the constant is defined but unused. This is an acceptable deviation because adding a timeout to `LLMClient.complete` is out of scope (it's shared code used by the existing async opencode analysis), and the user's UX is protected by Vue's reactive cancellation in the front end (stale-key check). If the user wants a true server-side timeout, that's a follow-up touching `apps/ai/client.py`.
- "Frontend blur on title + description, debounced via dedupe key, stale-result invalidation" → Tasks 7, 8.
- "Inline amber warning below title with clickable issue links, status badge, AI reason" → Task 8.
- "Non-blocking on submit" → no change to `handleCreateIssue` is in the plan; submission remains independent of `dupCandidates` state.
- "`resetCreateForm` clears duplicate state" → Task 7, Step 4.

Placeholder scan: no "TBD", no "implement later", every step has full code or an exact command. All function/property names used downstream match what is defined upstream (`dupCheckedKey`, `runDuplicateCheck`, `check_duplicates`, `DuplicateCheckInputSerializer`, `IssueCheckDuplicateView`).

Type consistency: backend returns `{candidates: [{id, title, status, reason}]}`; frontend type annotation in Task 7 matches; serializer field names (`project`, `title`, `description`) match the body the frontend sends in Task 7.

Scope: focused on the create-issue duplicate-check feature only. No incidental refactors, no unrelated cleanups.
