# AI 驱动的软件测试平台方案设计

**Date**: 2026-05-26
**Status**: Draft
**Scope**: 在 DevTrack 中新增基于大模型与无头浏览器的软件业务流程测试能力，先覆盖单个自然语言业务流程的执行、判断、截图与日志回传，后续扩展为可保存、可编排、可调度的测试平台。

## 背景

当前常见的端到端测试通常依赖固定代码脚本，例如 Playwright、Cypress 或 Selenium 测试用例。这种方式稳定、可控，但也带来明显成本：

- 测试脚本需要工程师编写和维护。
- 页面结构或文案变化后，选择器和断言容易失效。
- 业务人员很难直接参与测试流程创建。
- 新业务流程上线时，自动化测试沉淀速度较慢。

本方案希望在 DevTrack 中提供一种更接近“软件测试专家”的能力：用户用自然语言描述业务流程和成功标准，系统通过大模型理解页面、控制浏览器执行操作，并返回成功、失败原因、日志和截图。

该能力不是完全替代传统自动化测试，而是优先覆盖冒烟测试、主流程回归测试、业务验收测试和页面可用性检查。

## Goals

1. 支持用户创建一个自然语言测试任务，输入目标地址、登录信息、业务流程描述和成功判断标准。
2. 使用大模型作为测试执行代理，基于当前页面状态决定下一步浏览器操作。
3. 使用 Playwright 作为浏览器执行层，支持无头浏览器操作、截图、控制台日志、网络错误和 trace 采集。
4. 每次执行返回明确结果：成功、失败、超时或中断。
5. 失败时提供可诊断信息，包括失败步骤、页面截图、浏览器日志、网络错误和 AI 判断摘要。
6. 支持将一次自然语言流程沉淀为可复用的测试流程模板。
7. 为后续多流程测试套件、定时执行、失败通知和智能维护预留模型和接口空间。

## Confirmed Decisions

1. 平台目标是通用型 AI 测试工具，允许测试任意项目 URL。DevTrack / DevTrakr 自身只作为本地验证平台能力的可选 smoke target。
2. 每个测试目标项目应配置独立 `ProjectEnvironment`，该模型放在独立 `apps/ai_testing/` 中并关联项目。环境和凭证仅服务于 AI 测试，不应增加到项目主对象上。
3. 本地 Qwen 3.6 API 当前可以满足 v1 需求，平台优先复用现有 AI 配置，但 AI 测试可以增加专用执行参数。
4. 测试产物按结果区分保留：失败、超时、中断默认永久保留且允许用户删除；成功执行的完整产物默认按周期清理。
5. 项目级权限隔离是必需能力，测试流程、执行记录、截图、日志和 trace 均按项目授权访问。
6. 生产或其他敏感环境是否允许写操作应由环境策略配置，不能在平台层固定为绝对允许或绝对禁止。
7. cleanup v1 先支持“删除”和“关闭”两种动作，覆盖最常见的数据清理和状态回收场景。
8. 可提供一个可选 DevTrakr smoke flow：“登录并创建 Issue”，用于验证平台能力，不作为平台目标本身。
9. 不成功的测试执行支持一键创建 Issue，但不新增重复的 Issue 创建接口。前端或 AI 测试服务生成 Issue payload 后复用现有 `POST /api/issues/`，并通过 `source` / `source_meta` 记录来源。
10. `ProjectEnvironment` 测试凭证 v1 使用后端加密字段保存。即使是测试环境账号密码，也不明文入库、不在 API、日志或步骤记录中返回明文，这是基础安全规范。
11. AI 测试页面权限接入现有 `django-page-perms`，新增独立权限码，例如 `view_ai_testing`、`manage_ai_testing`。
12. 一键创建 Issue 时，assignee、label、priority 可由 AI 建议，但 Harness 必须校验合法性并提供兜底值。
13. cleanup 是环境/流程级配置。成功后可选择删除测试数据；如果不删除且对象支持状态流转，则关闭测试数据。可选 DevTrakr smoke flow 默认建议：不删除则关闭 Issue。
14. `AITestingModelSettings` 支持全局默认配置，也允许项目环境覆盖；未配置覆盖时使用全局默认。
15. 一键创建 Issue 的兜底 label 使用 `AI测试`。
16. `AITestingModelSettings` v1 管理入口放在 Django admin，不优先做普通用户前端配置页。
17. 测试凭证加密密钥 v1 由 `DJANGO_SECRET_KEY` 派生，不新增独立密钥配置。
18. AI 测试前端页面路由使用 `/app/ai-testing`。

## Non-Goals

- v1 不做完整测试管理平台，不覆盖复杂测试计划、测试用例评审、测试覆盖率统计。
- v1 不追求完全替代手写 Playwright / Cypress 脚本。
- v1 不支持任意代码执行，AI 只能调用平台暴露的受控浏览器工具。
- v1 不做跨浏览器兼容性测试，默认使用 Chromium。
- v1 不做高并发压测、接口压测或性能测试。
- v1 不自动修改被测系统数据，除非用户在测试目标中明确允许创建或变更测试数据。
- v1 不提供复杂的视觉回归对比，只保存截图用于诊断。

## 核心原则

### 以 Test Harness 为核心，而不是以提示词为核心

本平台不应设计成“用户管理一段提示词，然后让大模型自由测试”。更稳妥的架构是 AI Test Harness：

- Harness 定义测试任务、环境、权限、工具、状态机、证据采集和退出条件。
- 大模型是 Harness 中的一个决策引擎，负责根据页面状态选择下一步动作。
- 提示词是策略配置的一部分，但不是系统边界，也不是唯一控制面。
- 测试流程、断言、工具调用、失败证据和清理策略都需要结构化保存。

这样可以随着模型能力提升持续替换或增强决策引擎，而不重写平台主体。

### 通用测试 Skill 应平台化沉淀

无论是冒烟测试、回归测试、验收测试还是可用性测试，都有大量共通能力，例如登录、导航、表单填写、列表搜索、创建记录、编辑记录、删除前确认、等待异步结果、读取提示信息、判断成功状态、截图取证和失败归因。

这些能力不应该让用户在每个测试提示词里反复描述。平台需要把它们沉淀为可复用的测试 Skill 和 Harness 策略：

- 用户描述业务意图，例如“创建一个客户并确认出现在列表中”。
- Harness 选择合适的通用 Skill，例如登录、进入菜单、填写表单、提交、列表验证。
- 大模型只在 Skill 内部做上下文决策，例如识别当前页面上哪个按钮最像“保存”。
- 执行结果沉淀为结构化步骤和证据，而不是只保存一段自然语言提示词。

长期看，平台竞争力不在于让用户写更长的提示词，而在于内置越来越多稳定、可组合、可观测的测试 Skill。

### AI 负责决策，平台负责边界

大模型不直接执行任意代码，也不直接访问系统资源。平台只向大模型开放有限的浏览器工具，例如打开页面、点击、输入、等待、截图、读取页面摘要、读取日志、完成成功或失败。

### 所有操作可追踪

每一步操作都要保存结构化记录，包括操作类型、目标元素、输入内容摘要、执行结果、错误信息、页面 URL、截图引用和模型决策摘要。

### 失败优先解释

测试失败不是只返回 `failed`。平台需要说明失败发生在哪一步、当时页面是什么状态、AI 判断依据是什么、有没有控制台错误或网络错误，以及是否可能是页面变化、权限问题、数据校验问题或模型误判。

### 自然语言开始，结构化沉淀

用户可以从自然语言描述开始创建流程，但平台要逐步沉淀为可编辑、可复用、可版本化的测试资产，包括流程模板、步骤草稿、断言规则、测试数据和执行历史。

### 不确定性受控

AI 执行必须有最大步骤数、最大耗时、工具调用约束、敏感操作拦截、失败回退策略和人工复核入口，避免无限循环和不可预期操作。

## Architecture Overview

```text
用户创建测试任务
    │
    ▼
测试任务 API
    │  保存任务、流程描述、成功标准、执行配置
    ▼
AI 测试编排服务
    │  构造系统提示词、页面观察、工具调用上下文
    ▼
浏览器工具层（Playwright）
    │  open_url / click / fill / wait / assert / screenshot / logs
    ▼
被测 Web 系统
    │
    ▼
结果采集与报告
    │  步骤记录、截图、console、network、trace、AI 摘要
    ▼
测试执行报告
```

更准确的长期架构如下：

```text
                ┌──────────────────────┐
                │      Test Harness     │
                │ 任务 / 环境 / 权限 / 状态机 │
                └──────────┬───────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌──────────────┐ ┌────────────────┐
│ AI Planner      │ │ Tool Runtime │ │ Evidence Store │
│ LLM / future AGI│ │ Playwright   │ │ screenshots/logs│
└────────┬────────┘ └──────┬───────┘ └────────┬───────┘
         │                 │                  │
         ▼                 ▼                  ▼
   下一步动作建议       浏览器真实执行          可追踪报告
```

建议新增 Django app：

```text
apps/ai_testing/
├── models.py          # TestFlow, TestRun, TestStepRun, BrowserArtifact
├── serializers.py
├── views.py
├── urls.py
├── services.py        # 测试编排、任务生命周期、报告生成
├── browser.py         # Playwright 执行封装
├── agent.py           # LLM 工具调用循环
├── prompts.py         # 系统提示词和模板渲染
├── tasks.py           # Celery 异步执行
└── admin.py
```

前端新增入口建议放在 DevTrack 的平台能力或 AI 能力区域，页面可以先命名为“AI 测试”。

## Harness 可视化与管理员体验

Harness 是平台的核心控制面，不能只存在于后端配置或提示词中。管理员需要通过可视化界面理解、配置和审计 Harness 的行为。

### 管理员可视化目标

- 看得见：当前项目有哪些测试环境、测试账号、可用 Skill、风险策略和执行限制。
- 管得住：能配置允许访问的 URL、是否允许写操作、危险操作策略、并发限制、产物保留策略。
- 查得清：每次执行的 AI 决策、工具调用、截图、日志、trace 和失败原因都能回放。
- 改得动：能调整 Skill 参数、成功条件、cleanup 策略和模型配置，而不是只能改一整段提示词。
- 可审计：能知道是谁创建流程、谁修改环境、谁放开危险操作、哪次执行产生了什么数据。

### 管理员页面建议

v1 后台可以包含以下视图：

| View | Purpose |
|---|---|
| Project Environments | 管理项目环境、基础 URL、登录方式、测试账号、URL 白名单 |
| Harness Policy | 配置最大步骤数、最大耗时、并发限制、危险操作策略、产物保留周期 |
| Skill Library | 查看内置 Skill、启用/禁用 Skill、配置 Skill 风险等级和参数 |
| Test Runs Console | 查看运行中和历史执行，支持步骤时间线、截图、日志、trace |
| Failure Review | 按失败原因聚合，辅助管理员判断是系统缺陷、测试数据问题、页面变化还是 AI 误判 |
| Model Settings | 管理本地模型或兼容 OpenAI API 的模型配置 |

### Harness 运行轨迹

执行详情页不应只显示最终成功或失败，而应显示可回放的轨迹：

```text
Run #1024 - 创建客户流程
  Environment: staging
  Model: qwen3.6
  Policy: write allowed, dangerous actions blocked

  1. Skill: login_with_project_environment
     Tool: fill(username), fill(password), click(login)
     Result: success

  2. Skill: navigate_to_feature
     Tool: click("客户管理")
     Result: success

  3. Skill: fill_form_by_labels
     Tool: fill("客户名称", "AI_TEST_1024_客户A")
     Result: success

  4. Skill: submit_and_wait_result
     Tool: click("保存"), wait_for_text("保存成功")
     Result: failed
     Evidence: screenshot, console logs, network error
```

管理员应该能从这里直接看到：这次执行用了哪个环境、哪个模型、哪些 Skill、调用了哪些工具、失败证据是什么，以及是否触发了风险策略。

## 核心用户流程

### v1 手动执行单个流程

1. 用户进入“AI 测试”页面。
2. 创建测试任务，填写：
   - 测试名称
   - 目标系统 URL
   - 登录方式和测试账号
   - 业务流程描述
   - 成功判断标准
   - 最大执行步骤数
   - 最大执行时间
3. 用户点击运行。
4. 后端创建 `TestRun`，异步启动 Playwright 浏览器。
5. AI 根据页面观察结果调用工具执行操作。
6. 每一步写入 `TestStepRun`，必要时保存截图和日志。
7. 达到成功标准后结束为成功；遇到错误、超时或无法继续时结束为失败。
8. 前端展示报告、失败截图、关键日志和步骤轨迹。

### 后续流程模板化

1. 用户可以将一次成功或经过人工确认的测试保存为 `TestFlow`。
2. 再次执行时可复用流程描述、成功标准、登录配置和执行约束。
3. 用户可以编辑提示词、步骤说明或断言规则。
4. 平台保留执行历史，用于比较稳定性和失败趋势。

## AI Agent 工具设计

AI 不直接操作 Playwright API，而是通过受控工具调用：

| Tool | Purpose |
|---|---|
| `open_url(url)` | 打开目标页面 |
| `observe_page()` | 获取当前 URL、标题、可交互元素摘要、可见文本摘要 |
| `click(target)` | 点击按钮、链接、菜单项或其他可交互元素 |
| `fill(target, value)` | 输入文本，敏感值在日志中脱敏 |
| `select_option(target, value)` | 选择下拉选项 |
| `press(key)` | 发送键盘操作，例如 Enter、Escape |
| `wait_for_text(text, timeout)` | 等待指定文本出现 |
| `wait_for_navigation(timeout)` | 等待页面跳转或加载完成 |
| `assert_text(text)` | 断言页面存在指定文本 |
| `take_screenshot(reason)` | 保存当前页面截图 |
| `get_console_logs()` | 获取浏览器 console 日志 |
| `get_network_errors()` | 获取失败网络请求 |
| `finish_success(summary)` | 标记测试成功 |
| `finish_failure(reason)` | 标记测试失败 |

工具层需要统一返回结构：

```json
{
  "ok": true,
  "message": "Clicked button: 保存",
  "page_url": "https://example.com/projects",
  "screenshot_id": 123,
  "data": {}
}
```

## 通用测试 Skill 设计

测试 Skill 是比单个浏览器工具更高一层的可复用能力。工具解决“点击、输入、等待”这类原子动作，Skill 解决“登录、创建、搜索、验证、清理”这类测试任务。

### Skill 分层

```text
业务意图
  例如：创建客户并验证出现在列表中
    │
    ▼
测试 Skill
  login / navigate / create_record / search_list / assert_created / cleanup
    │
    ▼
浏览器工具
  observe_page / click / fill / wait_for_text / take_screenshot
```

### v1 通用 Skill 候选

| Skill | Purpose |
|---|---|
| `login_with_project_environment` | 使用项目环境配置完成登录 |
| `navigate_to_feature` | 根据菜单、面包屑、链接进入目标功能 |
| `fill_form_by_labels` | 根据 label、placeholder、字段语义填写表单 |
| `submit_and_wait_result` | 提交表单并等待成功、失败或校验提示 |
| `search_record_in_list` | 在列表页搜索并定位目标记录 |
| `assert_page_state` | 根据业务成功标准判断页面状态 |
| `capture_failure_evidence` | 失败时采集截图、console、network 和页面摘要 |
| `cleanup_created_data` | 根据 run id 或 cleanup 说明清理测试数据 |

### Skill 的保存形式

Skill 不应该只是一段提示词。建议保存为结构化定义：

```json
{
  "slug": "fill_form_by_labels",
  "name": "按字段语义填写表单",
  "inputs_schema": {
    "fields": "array",
    "submit": "boolean"
  },
  "allowed_tools": ["observe_page", "click", "fill", "select_option", "take_screenshot"],
  "success_condition": "所有必填字段已填写，且没有明显校验错误",
  "risk_level": "write",
  "max_steps": 12
}
```

提示词可以作为 Skill 的一部分，但 Skill 还必须包含输入结构、允许工具、风险等级、最大步骤数、成功条件和证据采集要求。

## Prompt 角色设计

系统提示词应明确要求模型扮演软件测试专家：

- 以完成用户给定业务流程为目标。
- 每次只选择一个最合理的浏览器动作。
- 优先使用页面上可见的稳定信息，例如按钮文案、label、placeholder、role。
- 不猜测危险操作，不删除生产数据，不提交不可逆操作，除非测试目标明确要求。
- 遇到不确定状态时先观察页面或截图。
- 成功必须基于用户给定成功标准，而不是仅凭页面跳转。
- 失败时要给出清晰原因和证据。

## Data Model

### `ProjectEnvironment` — 项目测试环境

每个测试目标项目可以配置多个环境，例如 development、testing、staging、production-readonly。AI 测试必须绑定到某个环境执行。

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `project` | FK Project | 所属 DevTrack 项目 |
| `name` | CharField(100) | 环境名称，例如 `staging` |
| `base_url` | URLField(500) | 被测系统基础 URL |
| `login_type` | CharField(50) | `username_password` / `saved_session` / `none`，后续扩展 SSO |
| `login_config` | JSONField | 登录页、字段提示、成功判断等非敏感配置 |
| `credential_ref` | CharField(200, blank=True) | 凭证引用，不直接在 API 明文返回 |
| `model_settings` | FK AITestingModelSettings, null=True | 环境级模型设置覆盖，为空时使用全局默认 |
| `allowed_url_patterns` | JSONField | URL 白名单 |
| `allow_write_actions` | BooleanField(default=False) | 是否允许创建或修改数据 |
| `allow_dangerous_actions` | BooleanField(default=False) | 是否允许删除、付款、发布等高风险操作 |
| `artifact_retention_policy` | JSONField | 成功/失败产物保留策略 |
| `max_concurrent_runs` | PositiveIntegerField(default=1) | 环境级并发限制 |
| `is_active` | BooleanField(default=True) | |
| `created_at` / `updated_at` | auto | |

### `AITestingModelSettings` — AI 测试专用模型参数

AI 测试复用现有 AI 模块的 `LLMConfig` 作为 provider 配置来源，包括 API key、base URL、可用模型列表和 JSON mode 能力。但测试执行还需要保存专用运行参数，避免影响其他 AI 分析功能。

该模型放在 `apps/ai_testing/` 中，通过 FK 关联 `apps.ai.LLMConfig`。它不是 `LLMConfig` 的替代品，而是 AI 测试对现有模型配置的运行时包装。

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `llm_config` | FK AI LLMConfig, null=True | 为空时使用现有 AI 默认配置 |
| `planner_model` | CharField(100, blank=True) | 为空时使用 `llm_config` 默认模型 |
| `critic_model` | CharField(100, blank=True) | 可选，用于复核成功/失败判断 |
| `temperature` | FloatField(default=0.1) | 测试执行应偏稳定 |
| `tool_call_timeout_secs` | PositiveIntegerField(default=60) | 单次工具调用超时 |
| `max_agent_turns` | PositiveIntegerField(default=30) | 单次执行最大模型决策轮数 |
| `enable_critic_review` | BooleanField(default=False) | v1 可关闭，后续开启 |
| `is_global_default` | BooleanField(default=False) | 全局默认配置，全局仅一条 |
| `created_at` / `updated_at` | auto | |

配置选择规则：

1. 如果 `ProjectEnvironment.model_settings` 有值，优先使用环境覆盖配置。
2. 否则使用 `AITestingModelSettings.is_global_default=True` 的全局默认配置。
3. 如果没有全局默认配置，则回退到现有 AI 默认 `LLMConfig` 并使用内置保守参数。

### `TestFlow` — 可复用测试流程

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `name` | CharField(200) | 测试流程名称 |
| `description` | TextField | 业务流程自然语言描述 |
| `project` | FK Project | 所属项目 |
| `environment` | FK ProjectEnvironment, null=True | 默认执行环境 |
| `target_url` | URLField(500) | 默认目标地址 |
| `success_criteria` | TextField | 成功判断标准 |
| `login_config` | JSONField | 登录方式配置，敏感字段不直接明文返回前端 |
| `max_steps` | PositiveIntegerField(default=30) | 最大 AI 工具调用步数 |
| `timeout_secs` | PositiveIntegerField(default=300) | 单次执行最大耗时 |
| `status` | CharField(20) | `draft` / `active` / `archived` |
| `created_by` | FK User | 创建人 |
| `created_at` / `updated_at` | auto | |

### `TestRun` — 单次执行

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `flow` | FK TestFlow, null=True | 一次性任务可为空 |
| `project` | FK Project | 所属项目 |
| `environment` | FK ProjectEnvironment | 本次执行环境 |
| `name` | CharField(200) | 执行名称 |
| `target_url` | URLField(500) | 本次实际目标地址 |
| `input_snapshot` | JSONField | 流程描述、成功标准、配置快照 |
| `status` | CharField(20) | `pending` / `running` / `success` / `failed` / `timeout` / `cancelled` |
| `started_at` | DateTimeField(null=True) | |
| `finished_at` | DateTimeField(null=True) | |
| `final_summary` | TextField(blank=True) | AI 生成的最终摘要 |
| `failure_reason` | TextField(blank=True) | 失败原因 |
| `created_by` | FK User | 触发人 |
| `created_at` / `updated_at` | auto | |

### `TestStepRun` — 单步执行记录

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `run` | FK TestRun | |
| `step_index` | PositiveIntegerField | 从 1 开始 |
| `thought_summary` | TextField(blank=True) | AI 决策摘要，不保存完整隐私链路 |
| `tool_name` | CharField(100) | 调用的工具 |
| `tool_input` | JSONField | 敏感值脱敏后保存 |
| `tool_result` | JSONField | 工具返回结果 |
| `page_url` | URLField(1000, blank=True) | 执行后的 URL |
| `status` | CharField(20) | `success` / `failed` |
| `error_message` | TextField(blank=True) | |
| `created_at` | DateTimeField(auto_now_add=True) | |

### `BrowserArtifact` — 截图、trace、日志文件

| Field | Type | Notes |
|---|---|---|
| `id` | auto PK | |
| `run` | FK TestRun | |
| `step` | FK TestStepRun, null=True | |
| `artifact_type` | CharField(30) | `screenshot` / `trace` / `console_log` / `network_log` / `video` |
| `file` | FileField | 存储路径 |
| `metadata` | JSONField | URL、viewport、错误摘要等 |
| `created_at` | DateTimeField(auto_now_add=True) | |

## 执行生命周期

```text
pending
  │
  ▼
running
  ├── finish_success      → success
  ├── finish_failure      → failed
  ├── max_steps reached   → failed
  ├── timeout reached     → timeout
  └── user cancelled      → cancelled
```

执行服务需要保证：

- 一个 `TestRun` 只能被一个 worker 执行。
- 浏览器上下文在执行结束后必须关闭。
- 失败和超时也要尽量保存最后截图、console 日志和 network 错误。
- 敏感输入，例如密码、token、cookie，不写入明文日志。

## API Draft

| Method | URL | Purpose |
|---|---|---|
| `GET` | `/api/ai-testing/flows/` | 测试流程列表 |
| `POST` | `/api/ai-testing/flows/` | 创建测试流程 |
| `GET` | `/api/ai-testing/flows/{id}/` | 流程详情 |
| `PATCH` | `/api/ai-testing/flows/{id}/` | 更新流程 |
| `POST` | `/api/ai-testing/flows/{id}/run/` | 执行已保存流程 |
| `POST` | `/api/ai-testing/runs/` | 创建并执行一次性测试 |
| `GET` | `/api/ai-testing/runs/{id}/` | 执行详情和报告 |
| `POST` | `/api/ai-testing/runs/{id}/cancel/` | 取消执行 |
| `GET` | `/api/ai-testing/runs/{id}/steps/` | 步骤轨迹 |
| `GET` | `/api/ai-testing/artifacts/{id}/` | 下载或查看截图、日志、trace |

失败、超时或中断的一键创建 Issue 复用现有 Issue 创建接口：

```http
POST /api/issues/
```

AI 测试侧负责生成默认字段：

- `project`: `TestRun.project_id`
- `title`: `[AI测试失败] {run.name}`
- `description`: 失败摘要、失败步骤、环境、截图链接、日志摘要、执行详情链接
- `priority`: AI 可建议，Harness 校验；兜底默认 `P2`
- `assignee`: AI 可建议，必须是项目成员；不合法或为空时走现有自动分配
- `labels`: AI 可建议，必须属于系统已有 label；兜底可使用 `AI测试`
- `source`: `ai_testing`
- `source_meta`: `{"test_run_id": ..., "environment_id": ..., "status": ...}`

## Frontend Draft

v1 页面建议包含：

- 测试流程列表
- 创建/编辑流程弹窗
- 一次性测试运行入口
- 执行详情页或抽屉
- 步骤时间线
- 最终结论
- 失败截图预览
- console/network 错误摘要
- trace 下载入口

执行中页面需要轮询 `TestRun` 状态，或后续升级为 WebSocket / SSE 实时推送步骤。

## 登录与凭证管理

v1 优先使用项目环境配置，而不是要求用户每次手动填写目标系统信息。每个项目可以维护一个或多个测试环境，例如开发、测试、预发、生产只读环境。

环境配置建议包含：

- 环境名称
- 基础 URL
- 登录方式
- 测试账号引用
- 允许执行的操作级别
- 是否允许创建测试数据
- 是否允许危险操作
- URL 访问白名单

简单账号密码登录配置可作为第一种登录方式：

- 登录页 URL
- 用户名字段提示
- 密码字段提示
- 用户名
- 密码
- 登录按钮提示
- 登录成功判断文本

凭证处理要求：

- 密码类字段使用后端加密字段保存或通过加密引用保存，不在 API 明文返回。
- 执行测试时仅在后端临时解密给浏览器会话使用。
- 步骤日志中对 `fill(password)` 自动脱敏。
- 浏览器上下文按执行隔离，执行结束后清理 cookie 和 localStorage。
- 后续可支持复用登录态、OAuth、SSO 或手动录制登录态。

## 测试范围与项目权限

平台允许测试任意项目 URL，但必须绑定到 DevTrack 项目和项目环境配置。测试流程、执行报告、截图和 trace 都属于某个项目环境。

“单独页面权限”指是否需要给 AI 测试这个功能入口配置独立权限。例如用户能访问 AI 分析页面，不代表一定能访问 AI 测试页面，因为 AI 测试会操作浏览器、使用测试凭证、产生截图和业务数据。建议采用两层权限：

- **功能入口权限**：控制用户是否能看到和进入“AI 测试”页面。
- **项目级权限**：进入页面后，用户只能查看和操作自己有权限的项目测试环境、流程和执行记录。

权限要求：

- 只有项目成员可以查看该项目下的测试流程和执行记录。
- 只有具备项目管理权限的用户可以新增或修改环境配置、测试账号和危险操作策略。
- 只有具备执行权限的用户可以触发测试运行。
- 只有具备 Issue 创建权限的用户可以从失败测试一键创建 Issue。
- 截图、trace、日志文件与项目权限绑定，不能作为公开文件暴露。
- 跨项目复用流程时，需要复制为目标项目的新流程，避免权限和凭证混用。

## 测试数据策略

AI 浏览器测试经常会创建或修改业务数据，因此必须把测试数据策略作为 Harness 的一部分。

cleanup 不等于“每次都删除测试痕迹”。最佳实践是按环境、数据类型和审计要求选择处理方式：

- 在短生命周期测试环境中，可以优先删除或回滚。
- 在需要排查问题的场景中，应保留失败数据，方便开发复现。
- 在有审计需求的系统中，删除可能不是最佳选择，归档、关闭、标记为测试数据更合适。
- 在生产或生产只读环境中，默认不应创建需要 cleanup 的数据，除非环境策略明确允许。

推荐策略按优先级从高到低：

1. **独立测试环境**：优先在测试、预发或沙箱环境执行。测试账号只拥有测试环境权限。
2. **Run ID 命名**：所有 AI 创建的数据都带上唯一前缀或后缀，例如 `AI_TEST_{run_id}_项目A`，方便识别和清理。
3. **清理策略**：测试流程可以定义 cleanup 阶段，在主流程成功或失败后按策略删除、关闭、归档、标记或保留本次创建的数据。
4. **TTL 清理任务**：对无法立即清理的数据，增加过期时间和定时清理任务，例如删除 7 天前的 AI 测试数据。
5. **快照回滚**：如果被测系统支持数据库快照、租户克隆或事务回滚，优先使用快照回滚。
6. **环境策略控制**：生产或敏感环境是否允许写操作由 `ProjectEnvironment` 策略决定，默认建议只读，但允许管理员按项目风险配置。

v1 可以先实现最实用的两项：Run ID 命名和用户可配置 cleanup 策略。cleanup 默认不自动执行，只有流程或环境明确配置后才执行。cleanup 动作先支持：

- **删除**：适合临时创建的测试数据，例如测试客户、测试 Issue、测试项目。
- **关闭**：适合不应物理删除、但可以结束状态的数据，例如 Issue、工单、告警、任务。

归档、标记、保留属于后续增强。它们主要用于有审计要求或无法删除的数据场景，v1 可以不做。

对可选 DevTrakr smoke flow“登录并创建 Issue”，成功后的 cleanup 作为样例工作流配置项：

- 如果配置允许删除测试数据，则删除测试创建的 Issue。
- 如果不允许删除，则关闭测试创建的 Issue。
- 测试失败时默认保留现场，方便复现和诊断。

平台应明确建议用户优先配置测试、预发或沙箱环境执行 AI 测试，而不是直接使用生产环境。生产环境即使被配置，也应默认更谨慎，例如只读、危险操作拦截、写操作需显式开启。

## Artifact Retention

执行产物包括截图、trace、console 日志、network 日志和最终报告。

保留策略建议：

- 失败、超时、中断的执行记录和产物默认永久保留，允许有权限的用户手动删除。
- 成功执行的完整截图和 trace 默认保留 30 天。
- 成功执行的结构化报告和步骤摘要可长期保留，用于趋势分析。
- 用户手动标记为基准样本的成功执行永久保留。
- 管理员可以配置项目级保留周期和存储上限。

这样既保留排障证据，又避免成功运行产生的截图和 trace 长期堆积。

## 安全与风控

### URL 访问限制

平台应限制可测试的目标地址，避免 SSRF 或访问内部敏感服务。可以复用或参考 `apps/uptime/url_safety.py` 中的 URL 安全策略。

### 危险操作拦截

AI 在点击“删除”、“清空”、“付款”、“发布生产”等高风险操作前，应触发拦截：

- v1 可以直接禁止，除非任务配置中明确允许危险操作。
- 后续可以加入人工确认。

### 执行资源限制

- 单次执行最大步骤数。
- 单次执行最大耗时。
- 单用户并发限制。
- 全局浏览器 worker 并发限制。
- 截图和 trace 文件保留周期。

### 数据脱敏

- 密码、token、cookie、Authorization header 不进入日志。
- 截图可能包含业务数据，需要按项目权限控制访问。
- 报告导出时应提示可能包含敏感页面内容。

## MVP 范围

第一阶段只做最小闭环：

1. 创建一次性测试任务。
2. 后端异步执行 Playwright + LLM 工具调用循环。
3. 支持打开页面、登录、点击、输入、等待、断言、截图。
4. 保存 `TestRun`、`TestStepRun` 和失败截图。
5. 前端展示执行状态、步骤轨迹、最终结果和失败诊断。
6. 支持将一次测试保存为 `TestFlow`。

MVP 结束标准：

- 能稳定完成一个明确的业务主流程测试。
- 能在失败时返回足够定位问题的截图、步骤和日志。
- 能重复执行已保存流程。

## Model Strategy

v1 应优先兼容本地 OpenAI-compatible 大模型 API。当前可使用本地已部署的 Qwen 3.6 作为首选模型，但平台不应绑定具体模型。

模型能力要求：

- 支持稳定的工具调用或 JSON 格式输出。
- 能理解中文业务流程描述。
- 能处理较长页面摘要和步骤历史。
- 低温度执行，优先稳定性而不是创造性。
- 可配置模型、base URL、API key、temperature、max tokens。

如果本地模型在工具调用稳定性、页面理解或长上下文上不足，可以保留切换到其他 OpenAI-compatible 模型的能力。长期可以把模型分层：

- Planner model：负责规划和下一步动作。
- Critic model：负责复核成功/失败判断。
- Vision model：负责在 DOM 摘要不足时理解截图。
- Repair model：负责根据历史失败建议修复流程。

## Evolution Roadmap

### Phase 1: AI 执行单个流程

- 自然语言测试目标
- AI 控制浏览器
- 成功/失败判断
- 截图和日志回传

### Phase 2: 流程模板化

- 保存测试流程
- 编辑流程描述和成功标准
- 重复执行
- 人工确认和修正步骤

### Phase 3: 测试套件

- 多个流程组合执行
- 冒烟测试套件
- 回归测试套件
- 执行报告汇总

### Phase 4: 自动化调度

- 定时执行
- 发版后触发
- 失败通知
- 历史趋势分析

### Phase 5: 智能维护

- 页面变化后自动尝试修复定位方式
- 自动识别按钮文案变化
- 自动建议断言调整
- 从失败历史中归纳稳定性问题

### Phase 6: 面向更强模型能力的 Harness 演进

未来模型能力增强后，平台重点不应只是让提示词更复杂，而是让 Harness 支持更高级的测试工作流：

- **自主探索**：AI 根据产品页面自动发现可测试路径，生成候选流程。
- **流程录制与泛化**：用户手动操作一次，AI 将操作归纳为可复用测试流程。
- **自愈测试**：页面结构、按钮文案或交互路径变化时，AI 根据历史证据自动修复定位策略。
- **多 Agent 协作**：Planner 负责执行，Critic 负责质检，Data Agent 负责准备和清理测试数据。
- **测试意图版本化**：保存的是业务意图和断言，而不是脆弱的页面选择器。
- **风险感知执行**：Harness 根据环境、权限、数据类型和操作风险动态决定是否允许 AI 继续。
- **从失败中学习**：把失败归因沉淀为项目知识，后续执行时自动避开已知问题或给出更早预警。

## Open Questions

当前无开放问题。

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| AI 操作不稳定 | 测试结果偶发失败 | 限制工具、增加页面观察、保存步骤、支持人工修正 |
| 页面变化导致误判 | 成功/失败判断不可靠 | 明确成功标准，支持断言规则和人工确认 |
| 敏感数据泄露 | 日志或截图包含账号、业务数据 | 凭证脱敏、权限控制、文件保留策略 |
| 浏览器执行资源过高 | worker 被占满或服务器负载升高 | 并发限制、超时、队列控制 |
| 测试误操作生产数据 | 删除或修改真实数据 | URL 白名单、危险操作拦截、测试环境优先 |
| LLM 成本不可控 | 高频执行导致费用增加 | 限制步骤数、缓存页面摘要、定时任务配额 |
