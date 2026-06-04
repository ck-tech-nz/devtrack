# 工作台个性化 + 服务器资源卡片 — 设计文档

日期: 2026-06-04
分支: `feat/dashboard-customization`
范围: 仅前端 (`frontend/`) + 部署环境变量

## 目标

工作台首页 (`/app/home`, `frontend/app/pages/app/home.vue`) 增加两项能力:

1. **服务器资源卡片** — 在「最近动态」之后新增一张卡片,通过 iframe 嵌入展示运行系统的**基础设施**资源监控(非软件服务监控)。嵌入地址形如:
   ```
   http://localhost:9300/embed?key=smk_-jNiwEc4r9Im9IfsA9uEaxp0GqxqUxYW
   ```
2. **个性化工作台** — 工作台上的区块可由用户自行 **显示 / 隐藏 / 上下移位**(本期仅支持上下移动,不做拖拽)。每个用户的布局独立保存,跨设备同步。

## 决策(已与用户确认)

| 决策点 | 选择 |
|---|---|
| 嵌入地址来源 | **运行时环境变量** `NUXT_PUBLIC_SERVER_MONITOR_URL`(非 SiteSettings) |
| 卡片可见范围 | **所有登录用户可见**(不做权限门) |
| 可定制范围 | **除 AI 向导外的全部区块** |
| 编辑交互 | **「编辑布局」模式**:进入后每个区块出现 上移/下移/显隐 控件,完成后退出 |
| 布局形态 | **单列全宽堆叠**(上下移位的语义前提) |

## 关键前提(已验证)

- **个性化纯前端,无后端改动。** `MeSerializer` (`backend/apps/users/serializers.py`) 已将 `settings` 作为可写 JSONField 暴露,`useUserSettings` (`frontend/app/composables/useUserSettings.ts`) 已实现对 `/api/auth/me/` 的防抖 PATCH。布局偏好作为 `settings.dashboard_layout` 一起保存即可,无需迁移。
- **嵌入地址运行时可变。** 前端由 Nitro node server 运行(`Dockerfile` → `node .output/server/index.mjs`,非 `nuxi generate` 静态导出),因此 `runtimeConfig.public` 在**运行时**从 `NUXT_PUBLIC_*` 环境变量读取。单一镜像即可在 test/prod 显示不同地址,契合 Watchtower 自动拉取的部署模型。
- **组件命名约定。** `components/dashboard/StatCard.vue` 自动导入为 `DashboardStatCard`;新区块组件放入 `components/dashboard/` 即遵循同一约定。

## 区块清单与默认顺序

定义一份规范的区块注册表,默认顺序如下(新卡片落在「最近动态」之后,符合需求):

| id | 标题 | 现有实现 | 内容存在条件 (available) |
|---|---|---|---|
| `stats` | 数据概览(四个统计卡一组) | 内联,4× `DashboardStatCard` | 恒为 true |
| `uptime` | 生产环境监控 | `UptimeMonitorsHomeWidget.vue` | 存在 production 监控项 |
| `todos` | 我的待办 | 内联 | `myIssues.length > 0` |
| `mentions` | 提及我的 | 内联 | `mentions.length > 0` |
| `tasks` | 我的任务 | 内联 | `myTasks.length > 0` |
| `activity` | 最近动态 | 内联 | `recentActivity.length > 0` |
| `server` | 服务器资源 | **新增** | 配置了 `serverMonitorUrl` |

AI 向导 (`AiIssueWizard`) **不在**注册表内,始终固定在列表上方。

## 架构

采用「抽取区块组件」方案:`home.vue` 由 600+ 行的全能页面瘦身为编排者。

### 1. 数据流

- `home.vue` 保留现有 `onMounted` 中的 `Promise.all` 并行取数(stats / 待办 / 通知 / 动态 / 计划),以及 `loading` 状态,行为不变。
- 各区块为**展示型组件**,数据通过 props 传入(`uptime` 仍走自身的 `useUptimeMonitors` 单例,保持不变)。
- 取数与渲染解耦:`home.vue` 负责取数与编排,区块负责呈现。

### 2. `useDashboardLayout()` 组合式函数 (`frontend/app/composables/useDashboardLayout.ts`)

- 状态:`settings.dashboard_layout`,形如 `Array<{ id: string; visible: boolean }>`。数组顺序即展示顺序;`visible` 为显隐开关。
- **加载时与注册表合并**:注册表中缺失的 id 追加到末尾(老用户自动获得新的 `server` 卡片);保存数据中不在注册表的 id 丢弃 → 向前兼容。合并为纯函数,便于单测。
- 暴露:
  - `orderedBlocks` — 合并后的有序区块描述(含 id、title、visible)。
  - `editing` — 编辑模式开关(`ref<boolean>`,仅运行时,不持久化)。
  - `moveUp(id)` / `moveDown(id)` — 调整顺序(到达两端时对应方向禁用)。
  - `toggleVisible(id)` — 切换显隐。
  - `reset()` — 恢复注册表默认顺序与默认可见性。
- 所有变更通过 `useUserSettings().update('dashboard_layout', next)` 持久化(沿用其 500ms 防抖 PATCH)。

### 3. `DashboardBlock.vue` 包装组件 (`frontend/app/components/dashboard/Block.vue` → `DashboardBlock`)

职责:渲染门控 + 编辑控件。Props:`id`、`title`、`available`(由父级传入)、是否首/末(用于禁用箭头);默认插槽承载区块内容。

- **普通模式**:仅当 `visible && available` 时渲染默认插槽内容;否则不渲染(保持现有「空内容自动隐藏」的行为)。
- **编辑模式**:渲染**所有**注册表区块(即使 `available` 为 false 也显示,用灰显占位 "暂无内容 / 未配置监控地址"),便于排序与显隐;每个区块叠加控件条:
  - `↑` 上移 / `↓` 下移(首/末禁用对应按钮)
  - 眼睛图标:显示/隐藏切换(隐藏态视觉灰显)
  - 区块外框虚线高亮,提示处于可编辑状态。

### 4. 编辑入口

- 工作台内容顶部、「数据概览」上方、可排序区域**之外**放置一个 ghost 风格 `编辑布局` 按钮(右对齐)。
- 进入编辑模式后按钮变为 `完成`,旁边出现 `重置默认` 链接。
- AI 向导始终在最上方,不受编辑模式影响。

### 5. 布局形态

- 可排序区域为**单列全宽堆叠**。
- 这是相对当前 UI 的唯一可见变化:目前「我的待办 + 提及我的」「我的任务 + 最近动态」分别为 2 列并排;改为单列后各自全宽堆叠,页面变长,但上下移位语义清晰无歧义。

### 6. `DashboardServerResource.vue` (`frontend/app/components/dashboard/ServerResource.vue` → `DashboardServerResource`)

- 读取 `useRuntimeConfig().public.serverMonitorUrl`;为空 → `available = false`(普通模式隐藏,编辑模式占位)。
- 卡片标题 **服务器资源**,沿用「最近动态」的可折叠表头形态,默认展开。
- 内容:`<iframe :src="serverMonitorUrl" loading="lazy" style="width:100%;height:640px;border:0" />`。
- 卡片样式复用首页现有 `.section-card` 视觉规范(浅色/暗色)。

### 7. 配置接线

- `frontend/nuxt.config.ts`:`runtimeConfig.public` 增加 `serverMonitorUrl: ''`(空串 → 运行时由 `NUXT_PUBLIC_SERVER_MONITOR_URL` 覆盖)。
- 本地开发:`frontend/.env` 写入 `NUXT_PUBLIC_SERVER_MONITOR_URL=http://localhost:9300/embed?key=smk_-jNiwEc4r9Im9IfsA9uEaxp0GqxqUxYW`。
- 部署:在各环境的 docker-compose / `.env` 中设置同名变量(test/prod 各自不同)。
- **部署前提(他方配置)**:9300 端口的监控工具需允许来自 app 源的内嵌(CSP `frame-ancestors` / `X-Frame-Options`),否则浏览器会拒绝渲染 iframe。该项不在本仓库范围内,需在监控工具侧配置;若未放行,卡片会空白——属预期,需在部署文档中提示。

## 数据契约

`settings.dashboard_layout`(存于用户 `settings` JSON 内):

```jsonc
[
  { "id": "stats",    "visible": true },
  { "id": "uptime",   "visible": true },
  { "id": "todos",    "visible": true },
  { "id": "mentions", "visible": true },
  { "id": "tasks",    "visible": true },
  { "id": "activity", "visible": true },
  { "id": "server",   "visible": true }
]
```

- 缺省(老用户无该字段)→ 使用注册表默认顺序、全部 `visible: true`。
- 合并规则见 §2。

## 涉及文件

**新增**
- `frontend/app/composables/useDashboardLayout.ts`
- `frontend/app/components/dashboard/Block.vue`
- `frontend/app/components/dashboard/ServerResource.vue`
- `frontend/app/components/dashboard/Todos.vue`、`Mentions.vue`、`Tasks.vue`、`Activity.vue`(从 `home.vue` 抽取)
- `frontend/app/components/dashboard/StatsRow.vue`(四个统计卡一组,从 `home.vue` 抽取)
- 单测:`useDashboardLayout` 合并/移位/显隐纯逻辑

**修改**
- `frontend/app/pages/app/home.vue` — 瘦身为编排者:取数 + 有序渲染 `DashboardBlock`
- `frontend/app/composables/useUserSettings.ts` — `UserSettings` 接口增加 `dashboard_layout` 字段及默认值
- `frontend/nuxt.config.ts` — `runtimeConfig.public.serverMonitorUrl`
- `frontend/.env`(本地)及部署 compose/`.env`(环境变量)

**无后端改动、无数据库迁移。**

## 测试与验收

- **单测(Vitest)**:`useDashboardLayout` 的合并(缺失追加 / 未知丢弃 / 缺省回退)、`moveUp/moveDown` 边界、`toggleVisible`、`reset`。
- **手动 QA(`/browse`)**:
  - 进入编辑模式 → 上下移动一个区块 → 完成 → 刷新页面顺序保留。
  - 隐藏一个区块 → 普通模式不显示 → 重新进入编辑模式仍可见并可恢复。
  - `重置默认` 恢复初始顺序与可见性。
  - 配置 `NUXT_PUBLIC_SERVER_MONITOR_URL` 后「服务器资源」卡片显示 iframe;留空则该卡片隐藏。
  - 空内容区块(如无待办)在普通模式自动隐藏,编辑模式以占位出现。
- **类型检查**:`npx nuxi typecheck` 通过。

## 显式不做(YAGNI)

- 不做拖拽排序(本期仅上下移动)。
- 不做多列/磁贴自由布局。
- 不做服务器资源卡片的权限门(所有人可见)。
- 不把嵌入地址做成 SiteSettings/后台可编辑字段(用环境变量)。
- 不改动 AI 向导的位置或可见性。
