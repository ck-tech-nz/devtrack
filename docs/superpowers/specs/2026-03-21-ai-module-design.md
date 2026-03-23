# AI 模块设计文档

## 概述

为 DevTrack 构建 AI 分析基础设施，支持从 DevTrack issues 和 GitHub issues 中提取洞察。包含：提示词与 LLM 配置管理、分析结果全流程存储、GitHub 数据定期同步、页面权限接入。

### 目标

1. 替换 `ai-insights.vue` 中的 mock 数据，接入真实 LLM 分析
2. 建立可扩展的 AI 分析基础设施，支持后续增加分析类型
3. GitHub Issues 定期同步到本地，作为分析数据源之一
4. 通过 `django-page-perms` 控制 AI 页面访问权限

### 约束

- LLM 调用同步执行（方案 A），前端展示友好加载状态
- 支持 OpenAI 及兼容 OpenAI 标准的 API（DeepSeek 等）
- GitHub token 使用 Fine-grained PAT，只读权限，限定特定仓库
- 代码同步不在本 spec 范围内，留待后续 spec
- 页面权限精细到每个 AI 页面独立一个 Django permission

---

## 架构

新增 Django app `apps/ai/`，GitHub 同步扩展现有 `apps/repos/`。

```text
数据流：
前端打开 /app/ai-insights
    │
    ▼
GET /api/ai/insights/?type=team_insights
    │
    ▼
AIAnalysisService.get_or_run()
    ├── 有 ≤1h 成功记录且数据未变 → 返回缓存 Analysis.parsed_result
    └── 否则 → 聚合数据 → 渲染提示词 → 调 LLM → 存 Analysis → 返回结果
    │
    ▼
前端渲染（等待期间显示"AI 正在分析数据，请稍候..."）
```

```text
apps/ai/
├── models.py        # LLMConfig, Prompt, Analysis
├── services.py      # 新鲜度判断、数据聚合、LLM 调用
├── client.py        # OpenAI-compatible 客户端封装
├── views.py
├── urls.py
├── admin.py
└── serializers.py

apps/repos/
├── models.py        # 新增 GitHubIssue；Repo 新增 github_token、last_synced_at
└── services.py      # GitHub 同步逻辑（新增）
```

---

## 模型设计

**PK 策略**：新模型遵循项目现有代码惯例，使用 `BigAutoField`（即 Django 默认）。`DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` 已在 `settings.py` 设置，新 app 无需额外声明。

### `LLMConfig`（`apps/ai/models.py`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | CharField(100), unique | 显示名，如 `OpenAI GPT-4o`、`DeepSeek` |
| `api_key` | CharField(500) | API Key（明文存储，Django admin 管理；后续可升级为加密字段） |
| `base_url` | CharField(500), blank | 留空则使用 OpenAI 默认地址 |
| `supports_json_mode` | BooleanField, default=True | 是否支持 `response_format=json_object`（DeepSeek 支持，其他兼容 API 可能不支持） |
| `is_default` | BooleanField | 全局唯一默认配置，保存时 `save()` 自动将其他记录置为 False |
| `is_active` | BooleanField, default=True | |
| `created_at` | DateTimeField, auto_now_add | |
| `updated_at` | DateTimeField, auto_now | |

### `Prompt`（`apps/ai/models.py`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `slug` | CharField(100), unique | 不可变标识符，作为 `analysis_type` 的查询键，如 `team_insights` |
| `name` | CharField(200) | 可修改的显示名，如 `团队效率洞察` |
| `system_prompt` | TextField | 系统提示词 |
| `user_prompt_template` | TextField | 用户提示词，支持 `{variable}` 占位符 |
| `model` | CharField(100) | 如 `gpt-4o`、`deepseek-chat` |
| `temperature` | FloatField, default=0.3 | |
| `llm_config` | FK(LLMConfig, null=True, on_delete=SET_NULL) | null 时使用 `is_default=True` 的配置 |
| `is_active` | BooleanField, default=True | |
| `created_at` | DateTimeField, auto_now_add | |
| `updated_at` | DateTimeField, auto_now | |

### `Analysis`（`apps/ai/models.py`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `analysis_type` | CharField(100) | 对应 `Prompt.slug`，如 `team_insights` |
| `prompt_template` | FK(Prompt, null=True, on_delete=SET_NULL) | 记录使用的模板（模板可能被删除，故可空） |
| `triggered_by` | CharField(20) | `page_open` / `manual` |
| `triggered_by_user` | FK(settings.AUTH_USER_MODEL, null=True, on_delete=SET_NULL) | `manual` 时记录触发人，`page_open` 时为 null |
| `status` | CharField(20) | `pending` / `running` / `done` / `failed` |
| `data_hash` | CharField(32) | 输入数据摘要的 MD5，用于检测数据变更（见新鲜度说明） |
| `input_context` | JSONField | 发给 LLM 前的结构化数据 |
| `prompt_snapshot` | JSONField | 快照：system_prompt、user_prompt、model、base_url、temperature |
| `raw_response` | TextField, null | LLM 原始回包 |
| `parsed_result` | JSONField, null | 解析后的结构化结果，前端读这个 |
| `error_message` | TextField, null | 失败原因 |
| `created_at` | DateTimeField, auto_now_add | |
| `updated_at` | DateTimeField, auto_now | |

### `GitHubIssue`（`apps/repos/models.py`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `repo` | FK(Repo, on_delete=CASCADE) | |
| `github_id` | PositiveIntegerField | GitHub issue number |
| `title` | CharField(500) | |
| `body` | TextField, blank | |
| `state` | CharField(20) | `open` / `closed` |
| `labels` | JSONField, default=list | label 名称列表 |
| `assignees` | JSONField, default=list | GitHub username 列表 |
| `github_created_at` | DateTimeField | GitHub 原始创建时间 |
| `github_updated_at` | DateTimeField | GitHub 原始更新时间（用于增量同步跳过未变更记录） |
| `github_closed_at` | DateTimeField, null | |
| `synced_at` | DateTimeField | 本次写入时间 |

`Meta: unique_together = ("repo", "github_id")`

### `Repo` 新增字段（`apps/repos/models.py`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `github_token` | CharField(200), blank | Fine-grained PAT（明文存储，Django admin 管理） |
| `last_synced_at` | DateTimeField, null | 最近一次同步时间 |

---

## GitHub Fine-grained PAT 配置指引

为每个需要同步的仓库生成只读 PAT：

1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens**
2. 点击 **Generate new token**，填写名称（如 `devtrack-readonly`）和过期时间
3. **Repository access** 选 **Only select repositories**，勾选目标仓库
4. **Repository permissions** 中开启：
   - `Issues` → **Read-only**
   - `Metadata` → **Read-only**（必选，自动勾上）
   - `Contents` → **Read-only**（代码同步功能上线时再开启，现在可跳过）
5. 生成后复制 token，填入 Django admin → Repo → `github_token` 字段

每个仓库可使用独立 token，也可共用一个具有多仓库权限的 token。

---

## GitHub 同步

### 触发方式

**不使用 APScheduler**（多 worker 部署下会产生重复任务）。改用两种触发方式：

- **OS 级定时任务**：通过 cron / systemd timer 定期调用 management command：

  ```bash
  0 * * * * cd /app && uv run python manage.py sync_github_issues
  ```

  Docker 部署时在 `docker-compose.yml` 中加独立 cron service。

- **手动触发**：管理员调用 `POST /api/ai/sync-github/`，或直接运行 management command：

  ```bash
  uv run python manage.py sync_github_issues [--repo <full_name>]
  ```

### 同步逻辑（`apps/repos/services.py`）

```text
GitHubSyncService.sync_repo(repo):
    使用 repo.github_token 调用 GitHub REST API
    分页获取所有 issues（state=all）
    for each issue:
        if 本地记录存在且 github_updated_at 未变 → 跳过
        GitHubIssue.objects.update_or_create(
            repo=repo, github_id=issue.number,
            defaults={title, body, state, labels, assignees,
                      github_created_at, github_updated_at, github_closed_at,
                      synced_at=now()}
        )
    repo.last_synced_at = now()
    repo.save(update_fields=["last_synced_at"])

GitHubSyncService.sync_all():
    for repo in Repo.objects.exclude(github_token=""):
        sync_repo(repo)
```

---

## AI Service 层（`apps/ai/services.py`）

### 新鲜度判断

```text
AIAnalysisService.get_or_run(analysis_type, triggered_by, user=None):
    latest = Analysis.objects.filter(analysis_type=analysis_type, status="done")
                          .order_by("-created_at").first()

    if latest and not is_stale(latest):
        return latest  # 返回缓存

    return run(analysis_type, triggered_by, user)

is_stale(run):
    if (now - run.created_at) > 1 hour: return True
    if compute_data_hash(run.analysis_type) != run.data_hash: return True
    return False
```

**关于 `compute_data_hash` 的性能**：新鲜度检查会在缓存命中时也调用一次数据聚合。当前数据规模（内部工具）可以接受。`data_hash` 的输入应为轻量摘要（各表的记录数 + 最大 `updated_at`），而非完整数据，以降低查询成本。

### 运行流程

```text
run(analysis_type, triggered_by, user=None):
    # 获取模板
    template = Prompt.objects.filter(slug=analysis_type, is_active=True).first()
    if not template:
        raise AIConfigurationError(f"No active Prompt for '{analysis_type}'")

    # 获取 LLM 配置
    llm_config = template.llm_config
    if llm_config is None:
        llm_config = LLMConfig.objects.filter(is_default=True, is_active=True).first()
    if llm_config is None:
        raise AIConfigurationError("No default LLMConfig configured")

    # 聚合数据
    context = aggregate_context(analysis_type)
    data_hash = md5(json.dumps(compute_hash_input(analysis_type), sort_keys=True))

    # 创建运行记录
    user_prompt = template.user_prompt_template.format(**context)
    ai_run = Analysis.objects.create(
        analysis_type=analysis_type,
        prompt_template=template,
        triggered_by=triggered_by,
        triggered_by_user=user if triggered_by == "manual" else None,
        status="running",
        data_hash=data_hash,
        input_context=context,
        prompt_snapshot={
            "system_prompt": template.system_prompt,
            "user_prompt": user_prompt,
            "model": template.model,
            "base_url": llm_config.base_url,
            "temperature": template.temperature,
        },
    )

    try:
        raw = LLMClient(llm_config).complete(
            model=template.model,
            system_prompt=template.system_prompt,
            user_prompt=user_prompt,
            temperature=template.temperature,
        )
        parsed = parse_json_response(raw)  # 解析失败时抛出 ValueError
        ai_run.raw_response = raw
        ai_run.parsed_result = parsed
        ai_run.status = "done"
        ai_run.save(update_fields=["raw_response", "parsed_result", "status", "updated_at"])
    except Exception as e:
        ai_run.status = "failed"
        ai_run.error_message = str(e)
        ai_run.save(update_fields=["status", "error_message", "updated_at"])
        raise

    return ai_run
```

`AIConfigurationError`（自定义异常）由 view 层捕获，返回 HTTP 503。

### LLM 客户端（`apps/ai/client.py`）

```python
class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url or None,  # None = OpenAI 默认
        )

    def complete(self, model, system_prompt, user_prompt, temperature) -> str:
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        if self.config.supports_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
```

---

## API 端点

挂载在 `/api/ai/`。权限统一使用 `FullDjangoModelPermissions`，与项目其他 app 保持一致。

**注意**：这两个端点是 action 风格的 `APIView`（非 `ListAPIView`），`FullDjangoModelPermissions` 需要 `queryset` 来解析模型名。每个视图必须显式声明 `queryset = Analysis.objects.none()`，否则运行时会抛出 `AssertionError`。

| 方法 | 路径 | 权限检查模型 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/ai/insights/` | `Analysis`（需 `ai.view_analysis`） | 获取分析结果，`?type=team_insights` |
| `POST` | `/api/ai/insights/refresh/` | `Analysis`（需 `ai.add_analysis`） | 强制刷新（manual 触发） |
| `POST` | `/api/ai/sync-github/` | `IsAdminUser`（`is_staff=True`） | 手动触发 GitHub 同步 |

### `GET /api/ai/insights/?type=team_insights` 返回结构

成功（缓存或刚完成）：
```json
{
  "status": "done",
  "updated_at": "2026-03-21T10:00:00Z",
  "is_fresh": true,
  "result": { ...parsed_result... }
}
```

失败（LLM 调用出错，HTTP 200，前端根据 status 展示错误）：
```json
{
  "status": "failed",
  "updated_at": "2026-03-21T10:00:00Z",
  "error_message": "LLM 服务暂不可用，请稍后重试"
}
```

配置缺失（HTTP 503）：
```json
{
  "detail": "AI 分析暂不可用：未配置提示词模板"
}
```

无历史记录（第一次运行中，HTTP 200）：
```json
{
  "status": "no_data",
  "result": null
}
```

---

## 页面权限

### `PAGE_PERMS.SEED_ROUTES` 更新（`settings.py`）

**更新**现有 `/app/ai-insights` 条目（不是新增），将 `"permission": None` 改为：

```python
{
    "path": "/app/ai-insights",
    "label": "AI 洞察",
    "icon": "i-heroicons-cpu-chip",
    "permission": "ai.view_analysis",
    "sort_order": 4,
    "meta": {"serviceKey": "ai"},
},
```

### `PAGE_PERMS.SEED_GROUPS` 更新（`settings.py`）

将 `ai` 加入 `管理员` 组的 apps 列表，并为 `只读成员` 显式添加 `ai.view_analysis`：

```python
"SEED_GROUPS": {
    "管理员": {"apps": ["projects", "issues", "settings", "repos", "ai"]},
    # 开发者：追加 view_analysis（查看洞察）和 add_analysis（触发刷新）
    "开发者": {"permissions": ["view_project", "view_issue", "add_issue", "change_issue",
                                "view_activity", "view_dashboard", "view_analysis", "add_analysis"]},
    # 产品经理继承开发者，因此也自动获得 view_analysis 和 add_analysis，这是预期行为
    "产品经理": {"inherit": "开发者", "permissions": ["add_project", "change_project", "manage_project_members"]},
    "只读成员": {"permissions_startswith": ["view_"]},  # 自动包含 view_analysis
},
```

运行 `uv run python manage.py sync_page_perms` 后生效。

---

## 前端变更（`ai-insights.vue`）

- 移除 `import { aiInsights, developerStats } from '~/data/mock'`
- 使用 `useAsyncData` 调用 `GET /api/ai/insights/?type=team_insights`
- 加载中展示："AI 正在分析数据，请稍候..."（带 spinner）
- `status=failed` 时展示错误提示卡片，包含 `error_message`
- `status=no_data` 时展示空状态引导
- 刷新按钮调用 `POST /api/ai/insights/refresh/`，完成后重新拉取数据

---

## Django Admin 配置（`apps/ai/admin.py`）

Admin 是 `LLMConfig` 和 `Prompt` 的唯一管理界面。

**`LLMConfig`**：

- `list_display = ["name", "base_url", "is_default", "is_active"]`
- `readonly_fields = ["created_at", "updated_at"]`
- `api_key` 不加入 `readonly_fields`（需要可编辑），但应在 `list_display` 中隐藏（避免列表页明文展示）

**`Prompt`**：

- `list_display = ["slug", "name", "model", "llm_config", "is_active"]`
- `readonly_fields = ["created_at", "updated_at"]`

**`Analysis`**：

- `list_display = ["analysis_type", "triggered_by", "status", "created_at"]`
- `readonly_fields = ["input_context", "prompt_snapshot", "raw_response", "parsed_result", "data_hash", "created_at", "updated_at"]`
- 只读查看，不允许在 admin 中手动创建或编辑运行记录

---

## 实现时必须完成的接线步骤

以下步骤不涉及业务逻辑，但缺少任一步骤都会导致运行失败：

1. **`INSTALLED_APPS`**（`config/settings.py`）：添加 `"apps.ai"`
2. **根 URL 路由**（`apps/urls.py`）：添加 `path("ai/", include("apps.ai.urls"))`
3. **依赖安装**：`uv add openai`（`LLMClient` 依赖 `openai` 包）
4. **迁移**：`uv run python manage.py makemigrations ai && uv run python manage.py makemigrations repos && uv run python manage.py migrate`
5. **同步权限和组**：`uv run python manage.py sync_page_perms`

---

## `parse_json_response` 定义

```python
def parse_json_response(raw: str) -> dict:
    """解析 LLM 返回的 JSON 字符串。"""
    text = raw.strip()
    # 去除 markdown 代码围栏（部分模型在非 json_mode 下会包裹输出）
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)  # 解析失败时抛出 ValueError，由调用方捕获
```

---

## `aggregate_context` 定义（`team_insights`）

`aggregate_context("team_insights")` 返回的 `input_context` 结构，同时作为 `user_prompt_template` 的占位符来源：

```python
{
    "period_days": 30,                      # 统计周期
    "total_issues": int,                    # DevTrack issue 总数
    "open_issues": int,
    "closed_issues": int,
    "issues_by_priority": {"P0": int, "P1": int, ...},
    "issues_by_assignee": [
        {"name": str, "open": int, "closed": int, "avg_hours": float | None}
    ],
    "github_issues_summary": [
        {
            "repo": str,                    # full_name
            "open": int,
            "closed": int,
            "labels": [str],               # 出现频率最高的 label（top 10）
        }
    ],
    "recent_closed_issues": [              # 近 30 天关闭的 issue（最多 50 条）
        {"title": str, "priority": str, "assignee": str, "hours_to_close": float}
    ],
}
```

`compute_hash_input("team_insights")` 使用轻量摘要（不包含完整数据）：

```python
def _ts(val):
    return val.isoformat() if val is not None else "1970-01-01T00:00:00+00:00"

{
    "issue_count": Issue.objects.count(),
    "issue_max_updated": _ts(Issue.objects.aggregate(m=Max("updated_at"))["m"]),
    "github_issue_count": GitHubIssue.objects.count(),
    "github_issue_max_synced": _ts(GitHubIssue.objects.aggregate(m=Max("synced_at"))["m"]),
}
```

空表时 `Max()` 返回 `None`，`_ts` 回退为 epoch 字符串，确保首次安装（尚无数据）时不会崩溃。

---

## 不在本 spec 范围内

- GitHub 代码文件同步（留待后续 spec）
- AI 分析配置的前端管理界面
- 多 `analysis_type` 的扩展（当前只实现 `team_insights`）
- 异步任务队列（Celery）
- API Key 加密存储（当前明文存储，后续可引入 `django-fernet-fields`）
