# Design: Reusable AI Chat Shell + Team Performance Assistant

**Date:** 2026-06-04
**Status:** Approved design (pre-implementation)
**Author:** ck + Claude

## 1. Goal & Background

Today the AI chat box only exists on the home/workbench page as the Issue creation
wizard (`AiIssueWizard`). We want to (a) extract a **reusable chat shell** so the same
dialog UX can be mounted on other pages, and (b) build the first new consumer: an AI
assistant on the **团队绩效管理** (Team Performance Management) admin page.

The performance assistant is a **ChatGPT-style multi-turn chat backed by tool calling
(function calling)**: the model decides which internal tools to call to read data, and
— only when the admin confirms — to write tasks. It serves four capabilities:

1. **Quickly generate tasks** for a manager (draft → confirm → write).
2. **Build an employee profile** (画像).
3. **Flag an employee's potential problems**.
4. **Critique a manager's improper actions** (e.g. demands too high, scoring too low) and advise.

Capabilities 2–4 are pure chat output (text + data cards), **no DB writes**. Only
capability 1 writes, and only after explicit human confirmation.

A reference production implementation (the FastAPI "贷后智能体" `run_tool_agent`) validated
this pattern; this design adapts its good patterns to DevTrakr's **synchronous Django** stack.

### Locked decisions (from brainstorming)

| # | Decision | Choice |
|---|---|---|
| Interaction model | Single smart chat, AI detects intent | ✓ |
| Context scope | Free-form — AI resolves the subject (employee/manager) from text via tools | ✓ |
| Task generation | Draft → admin confirms → write `ActionItem(source=ai)` | ✓ |
| Eval outputs (#2–#4) | Text + cards, **no DB writes** | ✓ |
| Frontend reuse | **A1** — extract `AiChatShell`, perf assistant is first consumer, Issue wizard migrates as fast-follow | ✓ |
| Agent runtime | **Hand-rolled thin runtime** in `apps/ai/agents/` (not OpenAI Agents SDK / Pydantic AI) | ✓ |
| Tool interface | In-process **permission-scoped tool registry**, MCP-portable | ✓ |
| SSE delivery | **Inline `StreamingHttpResponse`** (sync generator), matching existing issues chat | ✓ |
| Conversation persistence | **localStorage** (reuse shell), MVP | ✓ |
| Permissions | Reuse existing `adminOnly` + `kpi.change_improvementplan` | ✓ |

The SDK evaluation (OpenAI Agents SDK 0.17.x vs Pydantic AI 1.105 vs hand-rolled) concluded
**hand-rolled** because DevTrakr's hard constraints (per-request DB-driven provider/model/prompt,
DashScope OpenAI-compatible `/chat/completions` only, synchronous blocking + manual SSE frames,
existing `(event, payload)` protocol and `AiWizardError` contract) all fall where the frameworks
either don't help or must be worked around (Responses-API default, tracing phoning home to OpenAI,
async-first, global non-concurrency-safe singletons). Switch trigger: when ≥2 agents need mutual
**handoff / multi-step orchestration**, re-evaluate OpenAI Agents SDK.

## 2. Architecture Overview

```
┌─ Frontend (Nuxt) ───────────────────────────────────────────────┐
│ AiChatShell.vue        (NEW, generic)                            │
│   thread render · SSE stream · input · attachments · clear ·     │
│   localStorage persistence (namespaced storageKey)               │
│   props: endpoint, placeholder, storageKey                       │
│   slot #card  → domain card rendering (by card.kind)             │
│ useAiChatStream.ts     (NEW, generic: SSE parse + turn state)    │
│                                                                  │
│ Consumer 1: PerfAssistant.vue (NEW)  — cards: kpi_chart,         │
│   plan_table, employee_profile, manager_review, task_draft       │
│ Consumer 2 (fast-follow): AiIssueWizard migrates onto AiChatShell │
└──────────────────────────────────────────────────────────────────┘
            │ POST /api/ai/agents/{key}/chat/   (SSE, inline)
            │ POST /api/kpi/perf-agent/commit-tasks/  (write, on confirm)
┌─ Backend (Django, sync) ─────────────────────────────────────────┐
│ apps/ai/agents/         (NEW — generic runtime, reused by all)   │
│   registry.py    @tool decorator + global TOOL_REGISTRY          │
│   runtime.py     sync tool-calling loop → yields SSE events      │
│   sse.py         unified event protocol helpers                  │
│   definitions.py AgentDef {key, prompt_slug, tools[], model}     │
│   prompts.py     load_system_prompt: DB Prompt → hardcoded fallbk │
│ apps/ai/views.py  AgentChatView (POST {key}/chat/), tools intro   │
│ apps/ai/client.py  +chat_with_tools()  +stream()   (additions)   │
│ apps/ai/models.py  LLMConfig +supports_tools flag                │
│                                                                  │
│ apps/kpi/perf_tools/    (NEW — kpi contributes its tools)        │
│   employee.py, kpi.py, plan.py, manager.py (read tools)          │
│   write.py     create_action_items (human-in-loop)              │
│   agent.py     PERF_AGENT AgentDef                              │
│ apps/kpi/perf_agent_views.py  commit-tasks endpoint              │
│                                                                  │
│ Reused: ai.LLMClient · ai.LLMConfig · ai.Prompt                  │
│ Data: kpi(KPISnapshot/ImprovementPlan/ActionItem) · issues · users│
└──────────────────────────────────────────────────────────────────┘
```

**Layering principle.** `AiChatShell` knows nothing about domain content — it owns the
message stream, streaming, input, scroll, and persistence. Domain content (issue draft
card, task draft card, KPI chart, tool-call lines) is rendered through a `#card` slot keyed
by `card.kind`. The generic agent runtime lives in `apps/ai/agents/`; `apps/kpi` only
contributes its tools + one `AgentDef`. This is what makes "通用组件" pay off: a future agent
on another page = a new DB `Prompt` + a few `@tool` functions + an `AgentDef` + mounting
`AiChatShell` — no new loop, no new protocol, no new frontend.

## 3. Unified SSE Event Protocol

The shell understands only this set; domain meaning lives in `payload` + the `#card` slot.
Frames are emitted in the existing DevTrakr SSE format (`event: <name>\ndata: <json>\n\n`).

| event | payload | shell behavior |
|---|---|---|
| `thinking` | `{label}` | transient status line ("正在分析…" / "正在查询 张三 的 KPI…"); auto-clears |
| `tool_call` | `{id, name, label}` | insert a tool-activity line (🔧 …) |
| `tool_result` | `{id, status}` | mark that line ✓/✗ (no raw data shown) |
| `text` | `{delta}` | stream-append assistant text bubble (token-level) |
| `card` | `{kind, data}` | **slot render** a domain card (emitted directly by tools, not by the LLM) |
| `done` | `{}` | finalize the turn |
| `error` | `{message}` | red error + retry |

> When the Issue wizard migrates, its "draft card" and "dup hint" become additional `card`
> kinds — the protocol is unchanged. That is the proof of genericity.

## 4. Backend: Tool-Calling Runtime (`apps/ai/agents/`)

### 4.1 Tool registry (code-as-registry)

Tools are internal Python functions registered via a decorator into one global registry.
The JSON Schema sent to the LLM is **derived from type hints + docstring** (via pydantic,
already a transitive dep of `openai`), so the signature is the single source of truth — no
hand-written schema, no drift.

```python
# apps/ai/agents/registry.py
TOOL_REGISTRY: dict[str, ToolSpec] = {}

def tool(*, permission: str | None = None):
    """Register a tool. JSON schema is derived from the function signature + docstring."""
    def deco(fn):
        spec = ToolSpec.from_callable(fn, permission=permission)  # pydantic-derived schema
        TOOL_REGISTRY[spec.name] = spec
        return fn
    return deco
```

```python
# apps/kpi/perf_tools/kpi.py
@tool(permission="kpi.view_kpisnapshot")
def get_kpi_snapshots(actor: User, user_id: str, periods: int = 3) -> dict:
    """查询某员工最近几期 KPI 快照（评分/排名/指标）。"""
    # `actor` = the requesting user, injected by the runtime for permission scoping.
    # Returns {"data": {...}, "_viz": [ {"kind": "kpi_chart", "data": {...}} ]}
    ...
```

Rules:
- Every tool's **first parameter is `actor: User`**, injected by the runtime (not part of the
  LLM-facing schema). Tools enforce `actor` permission/scoping — least privilege, "runs as the user".
- The `permission` string is checked before execution; denial returns a structured "无权限"
  result the LLM relays politely (not a stream crash).
- A tool may return a `_viz` list of card descriptors (see 4.3).

### 4.2 Agent definition & system prompt

```python
# apps/ai/agents/definitions.py
@dataclass(frozen=True)
class AgentDef:
    key: str            # URL segment, e.g. "perf"
    prompt_slug: str    # DB Prompt slug for the system prompt
    tool_names: list[str]  # allowlist — subset of the global registry
    # model/temperature/llm_config resolved from the DB Prompt row
```

System prompt loads with a **fallback chain** so safety guardrails never vanish:
`DB Prompt(slug)` → hardcoded `SYSTEM_PROMPT` constant. (Optional Redis cache layer in front,
deferred.) The hardcoded constant carries the non-negotiable guardrails (no prompt-leak, scope
limits, tone).

### 4.3 The loop (sync generator)

`run_agent` is a **synchronous generator** yielding `(event_name, payload)` tuples, consumed by
an inline `StreamingHttpResponse` — matching the existing issues chat. (Adaptation of the
reference's async generator.)

```
run_agent(agent_def, messages, actor):
  system = load_system_prompt(agent_def.prompt_slug)
  msgs = [{"role":"system","content":system}, *messages]
  tools = [TOOL_REGISTRY[n].schema for n in agent_def.tool_names]
  yield ("thinking", {"label": "正在分析您的问题…"})

  for round_i in range(MAX_TOOL_ROUNDS):            # default 4, configurable
    resp = LLMClient.chat_with_tools(model, msgs, tools, tool_choice="auto")
    if resp.tool_calls:
      msgs.append(assistant_msg_with_tool_calls(resp))
      for tc in resp.tool_calls:
        spec = TOOL_REGISTRY[tc.name]
        yield ("tool_call", {"id": tc.id, "name": tc.name, "label": spec.label})
        try:
          check_permission(actor, spec.permission)
          result = spec.fn(actor=actor, **tc.args)   # in-process ORM query
        except Exception as e:
          yield ("tool_result", {"id": tc.id, "status": "error"})
          msgs.append(tool_msg(tc.id, {"error": str(e)}))   # let LLM recover/ask
          continue
        for viz in result.pop("_viz", []):           # cards render immediately,
          yield ("card", viz)                         # before any LLM text
        if spec.is_write:                             # create_action_items: HUMAN-IN-LOOP
          yield ("card", {"kind": "task_draft", "data": result["draft"]})
          yield ("done", {})                          # PAUSE — wait for commit endpoint
          return
        yield ("tool_result", {"id": tc.id, "status": "ok"})
        msgs.append(tool_msg(tc.id, result["data"]))
      continue                                        # next round
    if resp.text:                                     # no tools → final answer already
      yield ("text", {"delta": resp.text}); yield ("done", {}); return

  # Tool rounds done → final streamed insight (token-level)
  for chunk in LLMClient.stream(model, system, build_final_prompt(msgs)):
    yield ("text", {"delta": chunk})
  yield ("done", {})
```

`build_final_prompt` instructs: *"图表/表格/卡片已展示给用户，只给总结性洞察，不要逐条罗列已展示的数据。"*
Length budget tuned per agent (manager critique #4 gets a larger budget than a stat summary).

### 4.4 LLMClient additions

- `chat_with_tools(model, messages, tools, tool_choice, timeout) -> ToolResponse` — sync
  `chat.completions.create(tools=…, tool_choice=…)`; normalizes `message.tool_calls` vs text.
- `stream(model, system_prompt, user_prompt, timeout) -> Iterator[str]` — sync
  `chat.completions.create(stream=True)` yielding content deltas.
- Both reuse the existing per-request `LLMConfig` resolution, retry, and DashScope tolerances
  (no `json_object` on VL models, `/v1/models` parsing). The client layer stays the source of
  truth for provider quirks.

### 4.5 LLMConfig change

Add `supports_tools: BooleanField(default=True)` (mirrors `supports_json_mode`). Before a chat
turn, if the resolved config has `supports_tools=False`, return a clear config error
("当前模型不支持工具调用，请在 LLM 配置选择支持 function-calling 的模型") instead of a provider 4xx.

## 5. Tools for the Performance Assistant

| tool | params | returns (data + `_viz` card) | source | serves |
|---|---|---|---|---|
| `resolve_employee` | `name` | candidates `[{id,name,dept}]`; empty/many → AI asks in text | `users.User` | all (entity resolution) |
| `get_kpi_snapshots` | `user_id, periods=3` | scores/rankings/metrics + `kpi_chart` | `kpi.KPISnapshot` | #2 #3 |
| `get_plan` | `user_id, period?` | plan + ActionItems (manager `scores` vs `self_scores`, status, `not_achieved_reason`, `acknowledged`, points, dimension) + `plan_table` | `kpi.ImprovementPlan/ActionItem` | #1 #2 #3 |
| `get_issue_stats` | `user_id, period?` | assigned/resolved counts, avg resolution time | `issues.Issue/Activity` (reuse `kpi/metrics.py`) | #2 |
| `get_manager_review_stats` | `manager_id, period?` | avg score given, self↔manager gap, points/target distribution + `manager_review` | `kpi.ActionItem` (`reviewed_by=manager`) | **#4** |
| `create_action_items` ⚠️write | `user_id, period, items[]` | `task_draft` card; commit writes `ActionItem(source=ai)` | writes `kpi.ActionItem` | #1 |

`list_team` (org-wide ranking/comparison) is **out of scope** (YAGNI — all four capabilities are
per-person/per-manager). The "manager" in #4 is identified via `ActionItem.reviewed_by` /
`ImprovementPlan.created_by`.

## 6. Write Confirmation Loop (capability #1)

1. AI calls `create_action_items` → runtime validates args, emits `card{kind:"task_draft"}`,
   then `done` — **the turn pauses; nothing is written**.
2. Frontend renders editable task cards (reuse `StepDraft.vue` editing approach: title /
   description / dimension / points / priority / due_date / measurable_target).
3. Admin edits and clicks "确认创建" → `POST /api/kpi/perf-agent/commit-tasks/` →
   server writes `ActionItem(source=ai)` into the employee's current-period `ImprovementPlan`
   (creating a draft plan if none exists).
4. The commit result ("已创建 N 条") is appended to the client-side conversation as a
   `role:tool` message so the next turn knows the tasks landed.

**Safety property:** writes happen **only** in the dedicated commit endpoint after explicit
confirmation — never inside the streaming loop. Commit is idempotent (one-time draft token;
button disables after submit).

## 7. Endpoints

| method | path | purpose |
|---|---|---|
| POST | `/api/ai/agents/{key}/chat/` | generic agent chat (SSE inline stream); body = `{messages}` |
| GET | `/api/ai/agents/{key}/tools/` | introspection — the tool schemas this agent exposes |
| POST | `/api/kpi/perf-agent/commit-tasks/` | write confirmed `ActionItem`s |

Plus a management command `list_agent_tools` printing the registry (name / description / params /
permission) for ops visibility. Permission gate on all: `adminOnly` + `kpi.change_improvementplan`.

## 8. Observability & Maintenance

- **Tool catalog**: `uv run python manage.py list_agent_tools`; `GET …/tools/` endpoint.
- **Runtime**: `tool_call`/`tool_result` SSE events show what the agent is doing live; each tool
  call also emits a structured log (actor / tool / args / duration / ok|err).
- **Guard test**: assert every registered tool has a derivable schema, a permission, and an
  `actor`-first signature.
- **Audit (optional, deferred)**: persist each agent run to the `Analysis` model for #4 traceability.
  Off by default (MVP).

## 9. Error Handling & Runaway Protection

- **Max tool rounds** `MAX_TOOL_ROUNDS=4`; on exceed, emit a short "先给目前结论" text + `done`.
- **Per-tool timeout** via `LLMClient.timeout`; overall token budget cap.
- **Tool error** → caught, `tool_result{status:error}` + a `role:tool` error message so the LLM
  recovers or asks; the stream never crashes.
- **resolve_employee** no/many matches → returns candidates; AI asks in text (not an error).
- **Permission denied** in a tool → structured "无权限" relayed politely.
- **Model lacks tools** → pre-flight `supports_tools` check → clear config error.
- **Writes isolated** to the commit endpoint (see §6).

## 10. Testing Strategy

- **Backend (pytest, LLM fully mocked — never hit a real provider):**
  - Tool unit tests with factories (`KPISnapshot` / `ImprovementPlan` / `ActionItem`): correct
    scoped data + **permission scoping enforced** + correct `_viz` cards.
  - Agent loop: mock `chat_with_tools` to return scripted `tool_calls` → assert tools execute,
    correct SSE events emitted, loop pauses on the write tool, respects `MAX_TOOL_ROUNDS`.
  - `commit-tasks/`: creates `ActionItem(source=ai)`, validation, permission, idempotency.
  - Registry guard test (§8).
- **Frontend:**
  - `AiChatShell`: renders all event types (`thinking`/`tool_call`/`tool_result`/`text`/`card`/
    `done`/`error`) from a mocked stream; localStorage persistence namespacing.
  - `npx nuxi typecheck`.
  - Manual `/verify` against a real conversation (resolve → read → cards → streamed insight;
    and draft → confirm → write).

## 11. Out of Scope / Deferred

- Issue wizard migration onto `AiChatShell` (fast-follow, separate plan).
- DB-persisted conversations (`ChatSession`/`ChatMessage`) + session tabs + 👍/👎 feedback.
- Multi-agent handoff / orchestration; MCP server exposure; multi-model fallback.
- Finer-grained permissions (team lead → only own reports); audit persistence.
- `list_team` org-wide comparison; image attachments in the perf agent.

## 12. Side Task

Nav label rename **团队计划管理 → 团队绩效管理** for `/app/ai/plans`: already edited in
`backend/page_perms.json`; takes effect after `uv run python manage.py sync_page_perms`
(overrides the recent `b78fd4e` "团队任务" rename). Confirm whether `/app/ai/my-plan`
(now "我的任务") should change too.
