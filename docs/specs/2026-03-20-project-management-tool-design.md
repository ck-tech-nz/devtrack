# Project Management Tool (theme-pm) — Design Spec

## Overview

A dev team project management tool built as a Nuxt 3 SPA, reusing theme-a's Crystal design system. Core function is issue/bug tracking with GitHub repo integration (readonly) and AI-powered analysis. The tool is for internal development teams, with Chinese UI.

**Key principle:** AI and GitHub are hot-pluggable enhancement modules. The system provides full project management functionality without them. When unavailable, affected UI areas show graceful offline indicators.

## Technical Approach

- **Phase:** Demo with mock data (方案 C), architecture ready for future Django REST API backend
- **Stack:** Nuxt 3 (SPA mode) + Nuxt UI + Tailwind CSS + ECharts
- **Location:** `theme-pm/` directory, sibling to theme-a/b/c
- **Design system:** Crystal (purple/violet) theme, Inter font, same component patterns as theme-a
- **User/group management:** Django Admin (no frontend needed)
- **Language:** Simplified Chinese (zh-CN)

## Page Structure

```
layouts/
  default.vue          — 侧边栏 + 顶栏（复用 theme-a 模式）
  auth.vue             — 登录页布局

pages/
  index.vue            — 登录页
  app/
    dashboard.vue      — 项目概览仪表盘
    projects/
      index.vue        — 项目列表
      [id].vue         — 单个项目详情（含看板视图）
    issues/
      index.vue        — Issue 列表（表格，筛选/排序）
      [id].vue         — Issue 详情（含 AI 分析、GitHub 关联）
    repos/
      index.vue        — 绑定的 GitHub 仓库列表
      [id].vue         — 仓库详情（commits、PRs、Issues）
    ai-insights.vue    — AI 项目洞察（效率统计、趋势预警）
```

### Sidebar Navigation

1. **项目概览** — Dashboard
2. **项目管理** — 项目列表
3. **问题跟踪** — Issue 列表
4. **GitHub 仓库** — 仓库列表
5. **AI 洞察** — 项目分析

GitHub 仓库和 AI 洞察在侧边栏显示连接状态：绿点 = 在线，灰点 + "离线" = 不可用。

## Data Models

### Project（项目）

| Field | Type | Description |
|-------|------|-------------|
| id | string | 唯一标识 |
| name | string | 项目名称 |
| description | string | 项目描述 |
| status | enum | 进行中 / 已完成 / 已归档 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |
| linked_repos | string[] | 关联的 GitHub 仓库 ID |
| members | Member[] | 成员列表（含角色） |

### Issue（问题）

| Field | Type | Description |
|-------|------|-------------|
| id | string | 唯一标识 |
| project_id | string | 所属项目 |
| title | string | 问题标题 |
| description | string | 问题描述 |
| priority | enum | P0 / P1 / P2 / P3 |
| status | enum | 待处理 / 进行中 / 已解决 / 已关闭 |
| labels | string[] | 标签（前端/后端/Bug/优化/需求等） |
| reporter | string | 提出人 |
| assignee | string | 负责人 |
| cause | string | 原因分析 |
| solution | string | 解决办法 |
| created_at | datetime | 创建时间 |
| resolved_at | datetime | 解决时间 |
| resolution_hours | number | 解决耗时（小时） |
| branch_name | string | 一键创建的分支名（如 `fix/issue-42-login-bug`） |
| branch_created_at | datetime | 分支创建时间 |
| branch_merged_at | datetime | 分支合并到 main 的时间 |
| linked_commits | string[] | 关联 GitHub commit SHA |
| linked_prs | number[] | 关联 GitHub PR 编号 |
| ai_analysis | AIAnalysis | AI 分析结果 |

### AIAnalysis（AI 分析结果，可选）

| Field | Type | Description |
|-------|------|-------------|
| suggested_priority | enum | 建议优先级 |
| suggested_labels | string[] | 建议分类 |
| resolution_hints | string[] | 解决方向建议 |
| related_files | string[] | 关联代码文件 |

### Repo（GitHub 仓库，只读）

| Field | Type | Description |
|-------|------|-------------|
| id | string | 唯一标识 |
| name | string | 仓库名 |
| full_name | string | owner/repo |
| url | string | GitHub URL |
| description | string | 仓库描述 |
| default_branch | string | 默认分支 |
| language | string | 主要语言 |
| stars | number | Star 数 |
| connected_at | datetime | 绑定时间 |
| status | enum | 在线 / 离线 |
| recent_commits | Commit[] | 最近提交 |
| open_prs | PR[] | 开放 PR |
| open_issues | GHIssue[] | 开放 Issue |

### User（用户，Django Admin 管理）

| Field | Type | Description |
|-------|------|-------------|
| id | string | 唯一标识 |
| name | string | 姓名 |
| email | string | 邮箱 |
| github_id | string | GitHub 用户名 |
| role | string | 角色 |
| avatar | string | 头像 URL |

### Developer Stats（开发者统计，派生数据）

| Field | Type | Description |
|-------|------|-------------|
| user_id | string | 用户 ID |
| project_id | string | 项目 ID |
| avg_resolution_hours | number | 平均处理时间（小时），基于 branch_merged_at - branch_created_at |
| monthly_resolved_count | number | 月均解决数 |
| priority_distribution | object | P0/P1/P2/P3 各处理数量 |
| resolution_trend | TrendPoint[] | 按月处理量趋势 |

### Sub-types（子类型定义）

| Type | Fields |
|------|--------|
| Member | user_id: string, role: enum (owner / admin / member) |
| Commit | sha: string, message: string, author: string, date: datetime |
| PR | number: number, title: string, author: string, status: enum (open / merged / closed), created_at: datetime |
| GHIssue | number: number, title: string, author: string, status: enum (open / closed), labels: string[], created_at: datetime |
| TrendPoint | month: string, count: number |
| Bottleneck | type: enum (assignee / label), name: string, pending_count: number |
| Alert | message: string, severity: enum (warning / critical), metric: string, change_pct: number |

### AI Insight（AI 洞察，可选模块）

| Field | Type | Description |
|-------|------|-------------|
| project_id | string | 项目 ID |
| generated_at | datetime | 生成时间 |
| team_efficiency | object | 解决速度趋势、人均处理量 |
| bottlenecks | Bottleneck[] | 瓶颈识别（积压最多的人/标签） |
| trend_alerts | Alert[] | 预警（如"P0 问题本周增长 200%"） |
| recommendations | string[] | 建议（如"建议拆分前端标签"） |

## Page Functionality

### Dashboard（项目概览）

- 4 个统计卡片：总 Issue 数、待处理、进行中、本周已解决
- Issue 趋势折线图（近 30 天，按天统计新增/解决）
- 优先级分布饼图（P0-P3）
- 开发者排行榜（本月解决数 Top 5）
- 最近活动流（最新创建/解决/评论的 Issue）

### Issue 列表页

- 表格视图：标题、优先级、状态、负责人、提出人、创建时间、解决耗时
- 筛选：优先级、状态、标签、负责人
- 排序：创建时间、优先级、解决耗时
- 批量操作：分配负责人、修改优先级

### Issue 详情页

- 基本信息区：标题、描述、优先级、状态、标签、提出人、负责人
- 操作栏：
  - "创建分支"按钮（自动生成分支名如 `fix/issue-{id}-{slug}`，demo 阶段为 mock 操作，仅填充 branch_name 和 branch_created_at 字段）
  - 状态流转按钮
- GitHub 关联区：关联的 commits、PRs 列表（离线时灰色提示）
- AI 分析区：建议优先级、分类、解决方向、关联代码文件（离线时灰色提示）
- 时间线：原因分析、解决办法、操作记录

### 项目看板页（项目详情内）

- 三列看板：待处理 → 进行中 → 已解决（已关闭的 Issue 不显示在看板上）
- 卡片显示：标题、优先级 badge、负责人头像
- 简单展示，不要求拖拽功能

### GitHub 仓库页

- 仓库列表：名称、语言、连接状态（在线/离线）、绑定时间
- 仓库详情：基本信息、最近 commits 列表、Open PRs、Open Issues

### AI 洞察页

- 页面顶部状态条：AI 服务在线/离线
- 团队效率：平均解决时间趋势图、人均处理量柱状图
- 开发者统计表：每人的平均处理时间、月处理量、优先级分布
- 瓶颈识别：积压最多的负责人/标签
- 趋势预警卡片：如"P0 本周 +200%"

## Hot-Plug Design

AI 和 GitHub 模块采用热插拔设计：

1. **状态检测**：composable `useServiceStatus()` 维护各服务连接状态
2. **优雅降级**：
   - 侧边栏导航项显示在线/离线状态点
   - Issue 详情页的 AI 分析区和 GitHub 关联区在离线时显示灰色占位提示
   - AI 洞察页离线时显示"AI 服务暂不可用"提示卡片
   - GitHub 仓库页离线时显示"GitHub 连接不可用"提示
3. **核心不受影响**：Dashboard、项目管理、Issue 跟踪、看板视图完全独立运作

## Mock Data Scope

Demo 阶段 mock 数据覆盖：
- 3 个项目
- 50+ 个 Issue（含各种状态、优先级分布）
- 2 个 GitHub 仓库（含 mock commits、PRs）
- 10 个用户（含 email、github_id）
- 开发者统计数据
- AI 分析结果和洞察数据
