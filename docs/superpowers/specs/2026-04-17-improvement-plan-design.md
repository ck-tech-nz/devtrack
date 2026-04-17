# 个人提升计划（Improvement Plan）设计文档

## 概述

基于 KPI 分析数据，为每位开发者生成月度个人提升计划。包含结构化行动项、积分体系、管理员验收流程。AI 月初自动生成草案，管理员审核编辑后发布给员工，员工执行并提交证据，管理员月末验收打分。

## 导航变更

现有 "AI 洞察" 改为 "AI 分析" 组，包含：

| 页面 | 路由 | 原页面 | 权限 |
|------|------|--------|------|
| 团队分析 | `/app/ai/team-analysis` | 原 AI 洞察 | `ai.view_analysis` |
| 我的提升计划 | `/app/ai/my-plan` | 新页面 | 所有登录用户 |
| 团队计划管理 | `/app/ai/plans` | 新页面 | `kpi.change_improvementplan` |

PAGE_PERMS SEED_ROUTES 变更：
- 删除 `/app/ai-insights`
- 新增 `/app/ai/team-analysis`（继承原权限和 serviceKey）
- 新增 `/app/ai/my-plan`（permission=None，所有登录用户可见）
- 新增 `/app/ai/plans`（permission=`kpi.change_improvementplan`）

useNavigation.ts GROUP_DEFS 变更：
- 新增 "AI 分析" 组：`['/app/ai/team-analysis', '/app/ai/my-plan', '/app/ai/plans']`

## 数据模型

### ImprovementPlan

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user | FK → User | 所属员工 |
| period | CharField(7) | "2026-04" 月度周期 |
| status | CharField | `draft` / `published` / `archived` |
| source_kpi_scores | JSONField | 生成时的 KPI 评分快照 |
| created_by | FK → User, null | AI 生成为 null，手动创建记录创建人 |
| reviewed_by | FK → User, null | 审核/发布的管理员 |
| published_at | DateTimeField, null | 发布时间 |
| archived_at | DateTimeField, null | 归档时间 |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

Unique constraint: `(user, period)`

Django app: `kpi`（复用现有 app，新增模型）

### ActionItem

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| plan | FK → ImprovementPlan | 所属计划，cascade delete |
| source | CharField | `ai_generated` / `manager_added` |
| dimension | CharField | `efficiency` / `output` / `quality` / `capability` / `general` |
| title | CharField(200) | "提高 P0 问题响应速度" |
| description | TextField | 具体方法和建议 |
| measurable_target | CharField(200) | "P0 平均解决时间 < 24h" |
| points | PositiveIntegerField | 分值，管理员设定 |
| priority | CharField | `high` / `medium` / `low` |
| status | CharField | `pending` / `in_progress` / `submitted` / `verified` / `not_achieved` |
| quality_factor | DecimalField(3,2), null | 验收时系数：0.5 / 0.8 / 1.0 / 1.2 |
| sort_order | PositiveIntegerField | 排序，default=0 |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

computed (前端计算): `earned_points = points × quality_factor`（仅 verified 状态）

### ActionItemComment

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| action_item | FK → ActionItem | cascade delete |
| author | FK → User | 评论人 |
| content | TextField | 评论内容 |
| attachment | FileField, null | 截图/文件（上传至 MinIO） |
| created_at | DateTimeField | auto_now_add |

### 权限

在 ImprovementPlan Meta 中定义自定义权限：
- `change_improvementplan`（管理员编辑/发布/归档/验收）
- `view_own_plan`（员工查看自己的计划）

SEED_GROUPS 更新：
- 管理员：获得所有 kpi 权限（包含 change_improvementplan）
- 开发者：增加 `view_own_plan`
- 产品经理：继承开发者，增加 `view_own_plan`

## API 设计

### 计划 CRUD

```
GET    /api/ai/plans/                      管理员：团队所有计划（?period=2026-04 筛选）
POST   /api/ai/plans/generate/             管理员：为指定用户生成 AI 草案（body: {user_id}）
GET    /api/ai/plans/me/                   员工：我的计划（当月 published + 历史 archived）
GET    /api/ai/plans/{id}/                 计划详情（含所有行动项）
PUT    /api/ai/plans/{id}/                 管理员：编辑计划（修改行动项列表）
POST   /api/ai/plans/{id}/publish/         管理员：发布（draft → published）
POST   /api/ai/plans/{id}/archive/         管理员：归档（published → archived）
```

### 行动项操作

```
PUT    /api/ai/action-items/{id}/          管理员：编辑行动项字段
POST   /api/ai/action-items/{id}/status/   员工：更新状态（body: {status: "submitted"}）
POST   /api/ai/action-items/{id}/verify/   管理员：验收（body: {status, quality_factor}）
```

### 评论

```
GET    /api/ai/action-items/{id}/comments/ 评论列表
POST   /api/ai/action-items/{id}/comments/ 新增评论（multipart，支持 attachment）
```

### 权限矩阵

| 操作 | 员工 | 管理员 |
|------|------|--------|
| 查看自己的计划 | ✓ | ✓ |
| 查看他人的计划 | ✗ | ✓ |
| 生成/编辑/发布/归档 | ✗ | ✓ |
| 更新自己行动项状态 | ✓ | ✗ |
| 验收/打质量系数 | ✗ | ✓ |
| 留 comment | ✓（仅自己的计划） | ✓（所有计划） |

## 页面设计

### 1. 我的提升计划 `/app/ai/my-plan`

员工视角，显示当月已发布计划 + 历史归档。

顶部总览卡片：
- 行动项数量
- 总分值
- 已得分（已验收项的 points × quality_factor 之和）
- 完成进度条

行动项列表：
- 每项显示：优先级标签、标题、分值、状态 badge
- 点击展开详情：描述、可量化目标、评论区
- 员工可更新状态：pending → in_progress → submitted
- submitted 时要求至少留一条 comment 作为完成证据

底部历史归档折叠列表。

### 2. 工作台卡片（home.vue）

在现有工作台右侧或底部新增卡片"我的提升计划"：
- 显示当月计划：完成进度 (3/5)、已得分 / 总分
- 列出未完成的行动项（最多 3 条）
- "查看全部 →" 链接到 `/app/ai/my-plan`
- 无计划时不显示此卡片

### 3. 团队计划管理 `/app/ai/plans`

管理员视角，按月管理所有员工的计划。

顶部：月份选择器 + "批量生成草案" 按钮

员工列表表格：
- 头像、姓名、计划状态、行动项数、总分值、已得分
- 操作：编辑 / 发布 / 验收 / 归档

点击编辑进入计划编辑页：
- 可增删行动项
- 可修改每项的标题、描述、目标、分值、优先级
- 可查看员工提交的 comment 和截图
- 验收操作：选择 verified/not_achieved + quality_factor

### 4. 团队分析 `/app/ai/team-analysis`

原 `/app/ai-insights` 页面迁移至新路由，内容不变。

## AI 草案生成引擎

### 模块

新建 `backend/apps/kpi/plan_generator.py`，替代 suggestions.py 在计划生成场景的角色。suggestions.py 继续用于 KPI 详情页的即时建议显示。

### 生成规则

| 触发条件 | 维度 | 行动项标题模板 | 默认分值 | 优先级 |
|---------|------|--------------|---------|--------|
| efficiency < team_avg | efficiency | "提高日均解决量至 {target} 个" | 30 | high |
| P0/P1 avg_hours > 24 | efficiency | "P0/P1 响应时间控制在 24h 内" | 30 | high |
| self_introduced_bug_rate > 0.1 | quality | "自引 Bug 率降至 10% 以下" | 20 | medium |
| churn_rate > 0.2 | quality | "代码 Churn 率控制在 20% 以下" | 20 | medium |
| conventional_ratio < 0.5 | quality | "Conventional Commits 比率提升至 50%" | 10 | low |
| avg_commit_size > 300 | quality | "单次提交控制在 150 行以内" | 10 | low |
| repo_coverage < 2 | capability | "参与至少 2 个仓库的开发" | 20 | medium |
| as_helper_count == 0 | capability | "本月协助处理至少 2 个他人问题" | 20 | medium |

- measurable_target 基于实际数据动态生成
- 生成 3-6 项，上限 8 项
- 分值为建议值，管理员可修改

### Celery 定时任务

每月 1 号 09:00 执行 `generate_monthly_plans`：
1. 刷新上月 KPI 快照
2. 自动归档上月所有 `published` 状态的计划
3. 遍历所有活跃非机器人用户
4. 为每人生成 draft 计划 + 行动项（跳过已存在当月计划的用户）

## 行动项状态流转

```
pending ──→ in_progress ──→ submitted ──→ verified
  │              │              │            (管理员验收，选质量系数)
  │              │              │
  │              │              └──→ not_achieved
  │              │                   (管理员判定未达成)
  │              │
  └──── 员工操作 ─┘
```

- 员工只能向前推进：pending → in_progress → submitted
- 管理员可将 submitted → verified 或 not_achieved
- verified 后不可回退
- 管理员验收时必须选择 quality_factor（0.5 / 0.8 / 1.0 / 1.2）

## 积分计算

- 每个行动项有管理员设定的 `points`（分值）
- 验收通过时：`earned = points × quality_factor`
- 计划总得分：所有 verified 行动项的 earned 之和
- 分值单位为"分"，不显示任何货币符号或金额

## 不在本期范围

- 奖金计算/发放模块
- 跨月行动项延续
- 员工申诉流程
- 行动项模板库
