# AI Testing Platform Implementation Plan

> **For agentic workers:** Implement task-by-task. Keep each task independently verifiable before moving to the next one.

**Goal:** Build the Phase 1 MVP of a general-purpose AI-driven software testing platform: project-bound test environments, admin-managed model settings, reusable test flows, browser-run records, and a minimal AI Test Harness that can test arbitrary configured web projects.

**Spec:** `docs/superpowers/specs/2026-05-26-ai-testing-platform-design.md`

**Architecture:** New Django app `apps/ai_testing` owns test environments, model settings, flows, runs, steps, artifacts, Harness services, and Playwright integration. Existing `apps.ai.LLMConfig` is reused as the provider configuration. Existing `POST /api/issues/` is reused for failed test report Issue creation. Frontend route is `/app/ai-testing`, gated by `django-page-perms`.

**Phase 1 MVP Scope:**

- Create `apps/ai_testing`
- Models: `ProjectEnvironment`, `AITestingModelSettings`, `TestFlow`, `TestRun`, `TestStepRun`, `BrowserArtifact`
- Admin management for environments, model settings, flows, and runs
- Page permissions: `/app/ai-testing`, `view_ai_testing`, `manage_ai_testing`
- API for environments, flows, runs, steps, artifacts
- Minimal Harness service with controlled browser tools
- A sample DevTrakr smoke flow for validating the platform locally: login and create Issue
- Cleanup strategy for sample flows: delete test data if configured; otherwise close supported records
- Failed/timeout/cancelled run can create a report Issue by reusing `POST /api/issues/`
- Successful full artifacts retained for 30 days; failed/timeout/cancelled artifacts retained until deleted

---

## File Structure

### Backend New Files

- `backend/apps/ai_testing/__init__.py`
- `backend/apps/ai_testing/apps.py`
- `backend/apps/ai_testing/models.py`
- `backend/apps/ai_testing/admin.py`
- `backend/apps/ai_testing/permissions.py`
- `backend/apps/ai_testing/serializers.py`
- `backend/apps/ai_testing/views.py`
- `backend/apps/ai_testing/urls.py`
- `backend/apps/ai_testing/services.py`
- `backend/apps/ai_testing/browser.py`
- `backend/apps/ai_testing/agent.py`
- `backend/apps/ai_testing/prompts.py`
- `backend/apps/ai_testing/crypto.py`
- `backend/apps/ai_testing/tasks.py`
- `backend/apps/ai_testing/migrations/__init__.py`
- `backend/tests/test_ai_testing_models.py`
- `backend/tests/test_ai_testing_api.py`
- `backend/tests/test_ai_testing_services.py`

### Backend Modified Files

- `backend/config/settings.py`
- `backend/apps/urls.py`
- `backend/apps/issues/models.py` or source constants location, if `ai_testing` needs to be added to allowed Issue sources
- `backend/apps/issues/serializers.py`, only if current `ALLOWED_ISSUE_SOURCES` does not already allow `ai_testing`
- `backend/tests/factories.py`

### Frontend New Files

- `frontend/app/pages/app/ai-testing/index.vue`
- `frontend/app/components/ai-testing/EnvironmentPanel.vue`
- `frontend/app/components/ai-testing/FlowList.vue`
- `frontend/app/components/ai-testing/RunConsole.vue`
- `frontend/app/components/ai-testing/RunTimeline.vue`
- `frontend/app/components/ai-testing/RunArtifacts.vue`

### Frontend Modified Files

- `frontend/app/composables/useNavigation.ts`
- `frontend/app/middleware/auth.global.ts`, if route permissions are hard-coded there

---

## Task 1: Bootstrap `apps.ai_testing`

**Files:**

- Create `backend/apps/ai_testing/`
- Modify `backend/config/settings.py`
- Modify `backend/apps/urls.py`

- [ ] Create app skeleton and migrations package.
- [ ] Add `AiTestingConfig` with verbose name `AI 测试`.
- [ ] Register `apps.ai_testing` in `INSTALLED_APPS`.
- [ ] Mount API routes at `/api/ai-testing/`.
- [ ] Create stub `urls.py`.
- [ ] Run `uv run python manage.py check`.

**Acceptance:**

- Django starts cleanly.
- `/api/ai-testing/` route include is registered without import errors.

---

## Task 2: Models and Migrations

**Files:**

- `backend/apps/ai_testing/models.py`
- generated migrations

- [ ] Add `AITestingModelSettings`.
  - FK to `apps.ai.LLMConfig`
  - planner model, critic model, temperature, tool call timeout, max agent turns, critic review toggle
  - `is_global_default`, enforced as a single global default
- [ ] Add `ProjectEnvironment`.
  - FK to `projects.Project`
  - base URL, login type, encrypted login config or credential fields
  - optional FK to `AITestingModelSettings`
  - URL allowlist, write/dangerous action flags, artifact retention policy, concurrency limit
- [ ] Add `TestFlow`.
  - FK project and optional default environment
  - natural-language description, success criteria, max steps, timeout, cleanup policy
- [ ] Add `TestRun`.
  - FK project, environment, optional flow
  - status lifecycle: pending/running/success/failed/timeout/cancelled
  - input snapshot, final summary, failure reason, timestamps
- [ ] Add `TestStepRun`.
  - step index, skill name, tool name, redacted input, result, URL, status, error
- [ ] Add `BrowserArtifact`.
  - screenshot, trace, console log, network log, video
  - file plus metadata
- [ ] Generate and apply migration.
- [ ] Add model tests for defaults, relationships, global default enforcement, status choices.

**Acceptance:**

- Migrations apply cleanly.
- Model tests pass.
- No plaintext credential values are exposed by model helper methods or `__str__`.

---

## Task 3: Credential Encryption Helper

**Files:**

- `backend/apps/ai_testing/crypto.py`
- `backend/tests/test_ai_testing_models.py`

- [ ] Implement encryption/decryption helper using a key derived from `DJANGO_SECRET_KEY`.
- [ ] Keep encrypted values opaque in DB fields.
- [ ] Add helpers on `ProjectEnvironment` for setting and retrieving login secrets.
- [ ] Ensure serializers never return plaintext secrets.
- [ ] Add tests for round trip encryption, no plaintext storage, and missing/invalid secret handling.

**Acceptance:**

- Test credentials can be used by services but are not returned via API or admin list views.

---

## Task 4: Admin Interfaces

**Files:**

- `backend/apps/ai_testing/admin.py`

- [ ] Register `AITestingModelSettings`.
- [ ] Register `ProjectEnvironment`.
- [ ] Register `TestFlow`.
- [ ] Register `TestRun`, `TestStepRun`, `BrowserArtifact` as mostly read-only execution records.
- [ ] Mask credential fields in admin list/detail displays.
- [ ] Put `AITestingModelSettings` management in Django admin only for v1.

**Acceptance:**

- Admin can create model settings and project environments.
- Admin can inspect runs and artifacts without seeing plaintext passwords.

---

## Task 5: Page Permissions

**Files:**

- `backend/config/settings.py` or page permission config location
- `backend/page_perms.json` if generated by command
- `frontend/app/composables/useNavigation.ts`
- `frontend/app/middleware/auth.global.ts`, if needed

- [ ] Add route `/app/ai-testing`.
- [ ] Add permission codes `view_ai_testing` and `manage_ai_testing`.
- [ ] Add AI Testing nav item.
- [ ] Run `uv run python manage.py sync_page_perms`.
- [ ] Confirm the route is hidden or forbidden for users without permission.

**Acceptance:**

- AI Testing page appears only for permitted users.
- Project-level data is still filtered by project membership/management rights.

---

## Task 6: API Serializers and Views

**Files:**

- `backend/apps/ai_testing/serializers.py`
- `backend/apps/ai_testing/views.py`
- `backend/apps/ai_testing/urls.py`
- `backend/tests/test_ai_testing_api.py`

- [ ] Add project-scoped environment list/create/update APIs.
- [ ] Add flow list/create/update APIs.
- [ ] Add run create/detail/cancel APIs.
- [ ] Add run steps API.
- [ ] Add artifact download/view API with project permission checks.
- [ ] Redact credentials from all API responses.
- [ ] Add tests for auth, project access, manager-only environment writes, and run visibility.

**Suggested Routes:**

| Method | URL | Purpose |
|---|---|---|
| `GET` | `/api/ai-testing/environments/?project={id}` | List project environments |
| `POST` | `/api/ai-testing/environments/` | Create environment |
| `PATCH` | `/api/ai-testing/environments/{id}/` | Update environment |
| `GET` | `/api/ai-testing/flows/?project={id}` | List flows |
| `POST` | `/api/ai-testing/flows/` | Create flow |
| `PATCH` | `/api/ai-testing/flows/{id}/` | Update flow |
| `POST` | `/api/ai-testing/runs/` | Create and enqueue run |
| `GET` | `/api/ai-testing/runs/{id}/` | Run report |
| `POST` | `/api/ai-testing/runs/{id}/cancel/` | Cancel run |
| `GET` | `/api/ai-testing/runs/{id}/steps/` | Step timeline |
| `GET` | `/api/ai-testing/artifacts/{id}/` | Artifact access |

**Acceptance:**

- API supports creating and inspecting test runs without browser execution yet.
- Permission boundaries are covered by tests.

---

## Task 7: Issue Creation Integration

**Files:**

- `backend/apps/ai_testing/services.py`
- `backend/apps/issues/serializers.py`, if `ai_testing` source is not allowed
- `backend/tests/test_ai_testing_services.py`

- [ ] Confirm `ALLOWED_ISSUE_SOURCES` includes or can include `ai_testing`.
- [ ] Implement service that builds Issue payload from failed/timeout/cancelled `TestRun`.
- [ ] Reuse existing Issue serializer/service path instead of adding duplicate Issue creation endpoint.
- [ ] Use defaults:
  - title: `[AI测试失败] {run.name}`
  - priority: AI suggestion if valid, otherwise `P2`
  - labels: AI suggestion if valid, otherwise `AI测试`
  - assignee: AI suggestion if project member, otherwise null for existing auto assignment
  - source: `ai_testing`
  - source_meta: run/environment/status IDs
- [ ] Add tests for payload generation and validation fallback.

**Acceptance:**

- Failed test reports become normal Issues through the existing workflow.
- Invalid AI suggestions cannot create invalid assignee/label/priority values.

---

## Task 8: Browser Tool Runtime

**Files:**

- `backend/apps/ai_testing/browser.py`
- `backend/apps/ai_testing/services.py`
- `backend/tests/test_ai_testing_services.py`

- [ ] Add Playwright dependency if missing.
- [ ] Implement controlled tools:
  - `open_url`
  - `observe_page`
  - `click`
  - `fill`
  - `select_option`
  - `press`
  - `wait_for_text`
  - `wait_for_navigation`
  - `assert_text`
  - `take_screenshot`
  - `get_console_logs`
  - `get_network_errors`
- [ ] Redact sensitive input from tool logs.
- [ ] Enforce URL allowlist from `ProjectEnvironment`.
- [ ] Enforce write and dangerous action policy.
- [ ] Save screenshots/logs as `BrowserArtifact`.
- [ ] Add unit tests for redaction, allowlist rejection, and artifact creation.

**Acceptance:**

- Browser runtime can execute controlled operations and produce artifacts.
- Browser cannot access disallowed URLs or log plaintext passwords.

---

## Task 9: AI Agent Harness

**Files:**

- `backend/apps/ai_testing/agent.py`
- `backend/apps/ai_testing/prompts.py`
- `backend/apps/ai_testing/services.py`
- `backend/apps/ai_testing/tasks.py`

- [ ] Implement run lifecycle lock: one worker per `TestRun`.
- [ ] Resolve model settings:
  1. environment override
  2. global `AITestingModelSettings`
  3. fallback to default `apps.ai.LLMConfig` with conservative params
- [ ] Build system prompt around Test Harness and Skill concepts.
- [ ] Implement tool-call loop with max turns and timeout.
- [ ] Save each tool call as `TestStepRun`.
- [ ] Always capture final screenshot/logs on failure/timeout.
- [ ] Mark final status and summary.
- [ ] Add Celery task `run_ai_test(test_run_id)`.

**Acceptance:**

- A run can move from pending to terminal status.
- Steps and artifacts are recorded.
- Max turns, timeout, and cancellation are enforced.

---

## Task 10: Sample Smoke Flow

**Files:**

- `backend/apps/ai_testing/services.py`
- `backend/apps/ai_testing/management/commands/seed_ai_testing.py` or data migration
- `backend/tests/test_ai_testing_services.py`

- [ ] Seed or provide helper to create an optional sample `TestFlow` for DevTrakr: login and create Issue.
- [ ] Keep the sample flow clearly marked as demo/smoke data, not as the purpose of the platform.
- [ ] Use `ProjectEnvironment` credentials and base URL so the same mechanism works for any configured web project.
- [ ] Created sample records should include `AI_TEST_{run_id}`.
- [ ] Cleanup behavior for sample-created data:
  - if delete enabled: delete test Issue
  - otherwise: close test Issue
  - on failure: keep test data for diagnosis
- [ ] Add integration-style service tests with browser calls mocked.

**Acceptance:**

- The platform can seed an optional sample workflow for local validation.
- Generic flows remain first-class and are not coupled to DevTrakr.
- Cleanup behavior is deterministic and configurable.

---

## Task 11: Artifact Retention

**Files:**

- `backend/apps/ai_testing/tasks.py`
- migration or settings if periodic cleanup is scheduled

- [ ] Add task to prune successful run full artifacts after 30 days.
- [ ] Never auto-delete failed/timeout/cancelled run artifacts.
- [ ] Keep structured run and step summaries for successful runs.
- [ ] Add tests for retention selection logic.

**Acceptance:**

- Storage growth is bounded for successful runs.
- Failure evidence remains until deleted by an authorized user.

---

## Task 12: Frontend MVP

**Files:**

- `frontend/app/pages/app/ai-testing/index.vue`
- `frontend/app/components/ai-testing/*.vue`
- navigation and route permission files

- [ ] Build `/app/ai-testing` page.
- [ ] Show project/environment selector.
- [ ] Show flows list and run button.
- [ ] Show run console with status, final result, and step timeline.
- [ ] Show artifacts and failure screenshot links.
- [ ] Add button to create Issue from failed/timeout/cancelled run using existing Issue create flow or service payload.
- [ ] Keep model settings out of normal frontend; v1 uses Django admin.

**Acceptance:**

- Admin/tester can configure environment in admin, then run a flow from frontend.
- Run status and steps are visible without reading server logs.

---

## Task 13: Verification

- [ ] Backend: `cd backend && uv run python manage.py check`
- [ ] Backend tests: `cd backend && uv run pytest tests/test_ai_testing_models.py tests/test_ai_testing_api.py tests/test_ai_testing_services.py`
- [ ] Frontend build or type check per existing project conventions.
- [ ] Manual smoke:
  - open `http://localhost:3004/app/ai-testing`
  - select a configured test environment
  - run a generic flow, or use the optional DevTrakr login/create-Issue smoke flow for local validation
  - verify success report
  - verify cleanup behavior
  - force a failure and create a report Issue
