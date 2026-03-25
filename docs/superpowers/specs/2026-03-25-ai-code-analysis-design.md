# AI Code Analysis for Issues — Design Spec

## Overview

Extend DevTrack's AI insights to support **code-aware analysis** of Issues. Clone project repositories to the server, integrate [opencode](https://opencode.ai) as an AI coding agent, and let it analyze source code to provide root cause analysis and solution recommendations directly on Issues.

## Goals

1. Clone/pull GitHub repos to server-local storage for code access
2. Use opencode CLI (with DeepSeek/Zhipu via API) to analyze code in the context of an Issue
3. Auto-trigger analysis on Issue create/update; manual re-trigger via button
4. Append AI findings to Issue fields (`cause`, `solution`, `remark`) with clear AI attribution and timestamp
5. Expose git log of cloned repos on frontend

## Non-Goals

- Real-time code editing or auto-fix (read-only analysis only)
- Replacing existing team_insights analysis (stays on current LLMClient)
- RAG/embedding-based code indexing (opencode handles code understanding)
- Celery or heavy task queue (thread pool is sufficient for now)

---

## Architecture

### Data Flow

```
Issue created/updated
        │
        ▼
Django post_save signal ──► ThreadPoolExecutor
        │                         │
        ▼                         ▼
Manual button ──────────►  IssueAnalysisService
  POST /api/issues/{id}/         │
       ai-analyze/               ▼
                          Check: repo cloned? running analysis exists?
                                 │
                                 ▼
                          Load Prompt (slug: issue_code_analysis)
                          Build prompt with Issue context
                                 │
                                 ▼
                          subprocess: opencode in repo directory
                          (cwd=/data/repos/{org}/{name}/)
                                 │
                                 ▼
                          Parse structured JSON response
                                 │
                                 ▼
                          Append to Issue.cause / .solution / .remark
                          (AI decides which field, marked with attribution)
```

### Components

```
backend/
├── apps/repos/
│   ├── models.py          # Repo: +clone_status, +current_branch, +cloned_at
│   │                      #        +local_path (computed property)
│   └── services.py        # +RepoCloneService (clone/pull/log/branch)
├── apps/projects/
│   └── models.py          # Project: +repos M2M to Repo
├── apps/issues/
│   ├── models.py          # Issue: +repo FK (nullable)
│   ├── views.py           # +IssueAIAnalyzeView
│   └── signals.py         # post_save → auto-trigger analysis
├── apps/ai/
│   ├── models.py          # Analysis: +issue FK, +TriggerType.AUTO
│   ├── services.py        # +IssueAnalysisService (opencode subprocess)
│   └── opencode.py        # OpenCodeRunner: config generation, subprocess management
frontend/
├── app/pages/app/repos/[id].vue   # +clone button, +git log tab, +branch switcher
└── app/pages/app/issues/[id].vue  # +AI analyze button, +AI content rendering
```

---

## Model Changes

### Repo (extend existing)

```python
# New fields
clone_status = CharField(max_length=20, default="not_cloned")
    # choices: not_cloned, cloning, cloned, failed
current_branch = CharField(max_length=100, blank=True)
cloned_at = DateTimeField(null=True, blank=True)

# Computed property
@property
def local_path(self) -> str:
    # e.g. /data/repos/myorg/myrepo/
    return f"/data/repos/{self.full_name}/"
```

### Project (extend existing)

```python
repos = ManyToManyField("repos.Repo", blank=True, related_name="projects")
```

### Issue (extend existing)

```python
repo = ForeignKey("repos.Repo", on_delete=models.SET_NULL,
                  null=True, blank=True, related_name="issues",
                  verbose_name="关联仓库")
```

Frontend logic on Issue create:
- User selects Project
- If Project has 1 repo → auto-fill `repo`
- If Project has N repos → show dropdown to pick one
- If Project has 0 repos → hide repo field

### Analysis (extend existing)

```python
# New fields
issue = ForeignKey("issues.Issue", on_delete=models.CASCADE,
                   null=True, blank=True, related_name="analyses")

# Extend TriggerType
class TriggerType(models.TextChoices):
    PAGE_OPEN = "page_open", "页面打开"
    MANUAL = "manual", "手动刷新"
    AUTO = "auto", "自动触发"
```

---

## Repo Clone Service

New class `RepoCloneService` in `apps/repos/services.py`:

```python
class RepoCloneService:
    BASE_DIR = "/data/repos"

    def clone_or_pull(self, repo: Repo, branch: str = None) -> None:
        """Clone if not exists, pull if exists. Optionally switch branch."""
        # - Set repo.clone_status = "cloning"
        # - If local_path not exists: git clone <url> <local_path>
        # - If exists: git -C <local_path> pull
        # - If branch: git -C <local_path> checkout <branch>
        # - Update repo.clone_status, current_branch, cloned_at
        # - On error: clone_status = "failed"

    def get_log(self, repo: Repo, limit: int = 50) -> list[dict]:
        """Return recent commits as [{hash, author, date, message}]."""
        # git -C <local_path> log --format='{"hash":"%H","author":"%an","date":"%aI","message":"%s"}' -n <limit>

    def get_branches(self, repo: Repo) -> list[str]:
        """Return list of remote branch names."""
        # git -C <local_path> branch -r --format='%(refname:short)'
```

Git authentication: uses `repo.github_token` via URL embedding (`https://x-access-token:{token}@github.com/{full_name}.git`) — same pattern as existing GitHub sync.

Docker: add `git` to backend Dockerfile (`apt-get install -y git`).

---

## opencode Integration

### OpenCodeRunner

New module `apps/ai/opencode.py`:

```python
class OpenCodeRunner:
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config

    def generate_config(self, repo_path: str) -> dict:
        """Generate opencode.json content for the repo directory."""
        # Maps LLMConfig fields to opencode provider config
        # Supports DeepSeek, Zhipu, or any OpenAI-compatible provider

    def run(self, repo_path: str, prompt: str, timeout: int = 120) -> str:
        """
        1. Write temporary opencode.json to repo_path
        2. subprocess.run opencode with prompt, cwd=repo_path
        3. Capture stdout, clean up config
        4. Return raw response
        """
```

### Configuration Mapping

LLMConfig → opencode.json:

```json
{
  "provider": {
    "deepseek": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "DeepSeek",
      "options": {
        "baseURL": "{llm_config.base_url}",
        "apiKey": "{llm_config.api_key}"
      },
      "models": {
        "{prompt.llm_model}": { "name": "{prompt.llm_model}" }
      }
    }
  },
  "model": "{provider_id}/{prompt.llm_model}"
}
```

### IssueAnalysisService

New class in `apps/ai/services.py`:

```python
class IssueAnalysisService:
    def analyze(self, issue: Issue, triggered_by: str, user=None) -> Analysis:
        """
        1. Validate: issue.repo exists and clone_status == "cloned"
        2. Check no running analysis for this issue (prevent duplicates)
        3. Load Prompt(slug="issue_code_analysis")
        4. Build prompt from template with issue context:
           - title, description, labels, priority, status
           - existing cause/solution/remark (so AI doesn't repeat)
        5. Create Analysis record (status=running, issue=issue)
        6. Run OpenCodeRunner in repo directory
        7. Parse JSON response: {target_field, content}
        8. Append to issue field with AI attribution
        9. Update Analysis status
        """

    def _append_ai_content(self, issue: Issue, field: str, content: str):
        """Append AI analysis to the specified field with attribution."""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        block = f"\n\n---\n🤖 AI 分析 | {timestamp}\n{content}"
        current = getattr(issue, field)
        setattr(issue, field, current + block)
        issue.save(update_fields=[field, "updated_at"])
```

### Prompt Template

Slug: `issue_code_analysis`

System prompt guides the AI to:
- Analyze the codebase in context of the issue
- Determine root cause
- Suggest a solution with specific file/code references
- Return structured JSON with `target_field` and `content`
- Choose the most appropriate field (`cause` / `solution` / `remark`)

Managed via existing Django admin Prompt interface.

---

## API Endpoints

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repos/{id}/clone/` | POST | Clone/pull repo. Body: `{"branch": "dev"}` (optional) |
| `/api/repos/{id}/git-log/` | GET | Commit list. Query: `?limit=50` |
| `/api/repos/{id}/branches/` | GET | List remote branches |
| `/api/issues/{id}/ai-analyze/` | POST | Trigger AI code analysis |
| `/api/ai/analysis/{id}/status/` | GET | Poll analysis status |

### Response Formats

**Clone:**
```json
// 202 Accepted
{"detail": "克隆任务已启动", "clone_status": "cloning"}
```

**Git Log:**
```json
[
  {"hash": "abc123", "author": "dev", "date": "2026-03-25T10:00:00+08:00", "message": "fix login bug"},
  ...
]
```

**AI Analyze:**
```json
// 202 Accepted (async)
{"analysis_id": "uuid", "status": "running"}

// 400 if no repo linked
{"detail": "请先关联仓库"}

// 400 if repo not cloned
{"detail": "请先同步代码"}

// 409 if analysis already running
{"analysis_id": "uuid", "status": "running"}
```

**Analysis Status:**
```json
{"id": "uuid", "status": "done|running|failed", "error_message": null}
```

---

## Async Execution

- `ThreadPoolExecutor(max_workers=2)` — module-level singleton in services
- Clone and AI analysis both run in the thread pool
- API returns 202 immediately with task/analysis ID
- Frontend polls status endpoint until done, then refreshes data
- opencode subprocess timeout: 120 seconds
- Clone subprocess timeout: 300 seconds (large repos)

---

## Auto-Trigger via Signal

```python
# apps/issues/signals.py
@receiver(post_save, sender=Issue)
def trigger_ai_analysis(sender, instance, created, update_fields, **kwargs):
    if created:
        # New issue — trigger if repo is linked and cloned
        _maybe_analyze(instance, triggered_by="auto")
    elif update_fields and "description" in update_fields:
        # Description changed — re-analyze
        _maybe_analyze(instance, triggered_by="auto")

def _maybe_analyze(issue, triggered_by):
    if not issue.repo or issue.repo.clone_status != "cloned":
        return
    IssueAnalysisService().analyze_async(issue, triggered_by=triggered_by)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Repo not cloned | 400: "请先同步代码" |
| Issue has no repo | 400: "请先关联仓库" |
| Analysis already running for issue | 409: return existing analysis ID |
| opencode process timeout (120s) | Analysis.status = failed, error stored |
| opencode returns non-JSON | raw_response saved, status = failed |
| LLM API key invalid / quota exceeded | Error captured in error_message |
| Git clone fails (auth, network) | Repo.clone_status = failed, error logged |

---

## AI Content Attribution

AI-generated content appended to Issue fields uses this format:

```
---
🤖 AI 分析 | 2026-03-25 14:30
{analysis content here}
```

Frontend rendering:
- Detect `---\n🤖 AI 分析` separator in field content
- Render AI blocks in a distinct card style (light background, subtle border)
- Show timestamp from the separator line
- Original user content renders normally above

---

## Frontend Changes

### Issue Detail Page (`issues/[id].vue`)
- "AI 分析" button in toolbar (disabled if no repo linked or repo not cloned)
- Loading spinner while analysis is running
- AI content blocks styled distinctly in cause/solution/remark fields

### Issue Create/Edit Form
- After selecting Project: auto-populate repo if project has exactly 1 repo, else show repo dropdown
- Repo field hidden if project has no repos

### Repo Detail Page (`repos/[id].vue`)
- "同步代码" button → triggers clone/pull
- Clone status badge (not_cloned / cloning / cloned / failed)
- Branch switcher dropdown
- New "提交记录" tab with git log list (hash, author, date, message)

---

## Dependencies

### Backend
- `git` binary in Docker image
- `opencode` binary in Docker image (installed via `curl -fsSL https://opencode.ai/install | bash`)
- No new Python packages (subprocess calls only)

### Frontend
- No new packages

---

## Testing Strategy

### Backend Tests
- `test_repo_clone_service.py` — mock subprocess, test clone/pull/log/branches
- `test_opencode_runner.py` — mock subprocess, test config generation, response parsing
- `test_issue_analysis_service.py` — mock OpenCodeRunner, test field appending, duplicate prevention, error handling
- `test_issue_analysis_views.py` — test API endpoints, permission checks, validation
- `test_signals.py` — test auto-trigger on create/update, skip when no repo

### Frontend
- Component tests for AI content rendering
- Form logic for auto-populating repo field
