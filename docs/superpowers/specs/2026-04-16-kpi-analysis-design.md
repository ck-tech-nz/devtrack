# KPI 分析功能设计文档

## 概述

新增跨仓库、跨项目的开发者 KPI 分析页面。基于问题（Issue）数据和 Git Commit 数据，对开发人员进行多维评估、打分、排名，并提供改进建议和趋势追踪。

## 设计决策

| 决策项 | 结论 |
|--------|------|
| 目标受众 | 分层可见：管理者看全员数据+评分，普通员工只看自己 |
| 难度评估 | 优先级作为紧急度权重 + 客观指标（耗时、协作人数、活动数）作为复杂度信号 |
| 时间维度 | 快捷周期（本周/本月/本季度）+ 自定义日期范围 |
| 评分展示 | 混合制：核心指标用绝对值，综合评分用相对排名 |
| 角色筛选 | 支持按用户组筛选，默认只看开发人员 |
| 数据存储 | 预计算存入数据库 + 手动刷新按钮触发重新计算 |
| 页面模式 | 混合模式：团队仪表盘 + 个人多维档案（4 标签页） |
| 改进建议 | 短板提示 + 趋势环比 + 能力画像，规则引擎自动生成 |
| 导航位置 | 用户管理菜单下 |

---

## 数据模型

### 新增 Django App：`kpi`

### KPISnapshot 模型

预计算快照，每次计算生成一条记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUIDField (PK) | 主键 |
| `user` | FK(User) | 被评估的用户 |
| `period_start` | DateField | 统计起始日期 |
| `period_end` | DateField | 统计截止日期 |
| `issue_metrics` | JSONField | 问题相关指标（结构见下） |
| `commit_metrics` | JSONField | Commit 相关指标（结构见下） |
| `scores` | JSONField | 各维度评分 0-100 |
| `rankings` | JSONField | 团队内排名百分位 |
| `suggestions` | JSONField | 自动生成的改进建议 |
| `computed_at` | DateTimeField | 计算时间 |
| `created_at` | DateTimeField(auto_now_add) | 记录创建时间 |

**唯一约束：** `(user, period_start, period_end)` — 同一用户同一时间范围只保留一条快照，刷新时覆盖更新。

### issue_metrics JSON 结构

```json
{
  "assigned_count": 32,
  "resolved_count": 28,
  "resolution_rate": 0.875,
  "avg_resolution_hours": 12.3,
  "daily_resolved_avg": 2.1,
  "weekly_resolved_avg": 14.7,
  "weighted_issue_value": 186,
  "priority_breakdown": {
    "P0": {"assigned": 5, "resolved": 5, "avg_hours": 4.2},
    "P1": {"assigned": 10, "resolved": 9, "avg_hours": 8.5},
    "P2": {"assigned": 12, "resolved": 10, "avg_hours": 16.1},
    "P3": {"assigned": 5, "resolved": 4, "avg_hours": 24.0}
  },
  "as_helper_count": 8
}
```

### commit_metrics JSON 结构

```json
{
  "total_commits": 154,
  "additions": 12500,
  "deletions": 3200,
  "lines_changed": 15700,
  "self_introduced_bug_rate": 0.08,
  "churn_rate": 0.12,
  "avg_commit_size": 102,
  "commit_size_distribution": {
    "small": 80,
    "medium": 50,
    "large": 24
  },
  "file_type_breadth": [".py", ".vue", ".ts", ".css", ".html"],
  "work_rhythm": {
    "by_hour": [0, 0, 0, 0, 0, 0, 2, 5, 12, 18, 15, 10, 8, 14, 16, 12, 8, 5, 3, 1, 0, 0, 0, 0],
    "by_weekday": [25, 30, 28, 32, 27, 8, 4]
  },
  "refactor_ratio": 0.15,
  "commit_type_distribution": {
    "feat": 60,
    "fix": 30,
    "refactor": 23,
    "chore": 15,
    "docs": 10,
    "test": 8,
    "style": 5,
    "other": 3
  },
  "repo_coverage": [
    {"repo_id": "uuid", "repo_name": "Post-Loan-Agent", "commits": 80},
    {"repo_id": "uuid", "repo_name": "Frontend-App", "commits": 74}
  ],
  "conventional_ratio": 0.92
}
```

### scores JSON 结构

```json
{
  "efficiency": 95,
  "output": 100,
  "quality": 85,
  "capability": 90,
  "growth": 88,
  "overall": 92
}
```

### rankings JSON 结构

```json
{
  "efficiency_percentile": 95,
  "output_percentile": 100,
  "quality_percentile": 78,
  "capability_percentile": 85,
  "growth_percentile": 80,
  "overall_rank": 1,
  "total_developers": 6
}
```

### suggestions JSON 结构

```json
{
  "shortcomings": [
    {
      "dimension": "quality",
      "message": "自引入 Bug 率 8%，高于团队均值 5%，建议加强代码自测",
      "severity": "medium"
    }
  ],
  "trends": [
    {
      "dimension": "efficiency",
      "direction": "up",
      "change_percent": 12,
      "message": "效率评分本期提升 12%，保持势头"
    },
    {
      "dimension": "quality",
      "direction": "down",
      "change_percent": -5,
      "periods": 2,
      "message": "质量评分连续 2 个周期下降，关注是否有阻塞因素"
    }
  ],
  "profile": "高效产出型，质量有提升空间"
}
```

---

## 评分体系

### 问题价值分

每个已解决问题的价值分：

```
issue_value = priority_weight × complexity_signal

priority_weight:
  P0 = 4, P1 = 3, P2 = 2, P3 = 1

complexity_signal = normalize(
  resolution_hours × 0.4 +
  helper_count × 0.3 +
  activity_count × 0.3
)
```

`normalize` 对团队所有问题的 complexity_signal 做 min-max 归一化到 [0.5, 2.0]，避免极端值，确保最简单的问题也有基础分。

### 五维评分（0-100）

**1. 效率分（Efficiency）**
- 日均解决问题数（40%）
- 平均解决耗时的倒数，越快越高（40%）
- P0/P1 响应速度（20%）
- 计算方式：各指标先在团队内算百分位，再加权求和

**2. 产出分（Output）**
- 加权问题价值总分（40%）
- 解决问题数（30%）
- Commit 数量 + 代码变更量（20%）
- 跨仓库覆盖广度（10%）

**3. 质量分（Quality）**
- 自引入 Bug 率的倒数（30%）— 越低越好
- 代码流失率的倒数（25%）— 越低越好
- 提交粒度合理性（20%）— 偏离中位数越远分越低
- Conventional commit 规范率（25%）

**4. 能力分（Capability）**
- 技术栈广度：文件类型数（25%）
- 目录/仓库覆盖面（25%）
- 高优先级问题处理占比（25%）
- 协作参与度：作为 helper 的次数（25%）

**5. 成长分（Growth）**
- 效率维度环比变化（25%）
- 产出维度环比变化（25%）
- 质量维度环比变化（25%）
- 能力维度环比变化（25%）
- 正增长得高分，负增长得低分，无历史数据默认 50

### 综合评分

```
overall = efficiency × 0.25 + output × 0.25 + quality × 0.25 + capability × 0.15 + growth × 0.10
```

---

## Commit 指标挖掘

所有 commit 指标基于已克隆仓库的 git log，通过 `GitAuthorAlias` 关联到系统用户。跨所有该用户关联的仓库聚合。

### 自引入 Bug 率

同一作者在一次 `feat`/`refactor` 提交后 72 小时内，对同一文件提交 `fix` 类型 commit 的比例。

```
self_introduced_bug_rate = self_fix_count / total_feat_refactor_count
```

### 代码流失率（Churn Rate）

统计周期内，某作者编写的代码在 30 天内被任何人（包括自己）修改的行数占其总新增行数的比例。

```
churn_rate = churned_lines / total_additions
```

### 提交粒度

每次 commit 的 `lines_changed`（additions + deletions）。计算平均值和分布：
- small: < 50 行
- medium: 50-200 行
- large: > 200 行

### 技术栈广度

统计该作者在周期内修改的文件的唯一扩展名集合。

### 工作节奏

按提交时间戳统计：
- `by_hour`: 24 小时分布（0-23 点各多少次提交）
- `by_weekday`: 周一到周日各多少次提交

### 重构贡献

```
refactor_ratio = refactor_type_commits / total_commits
```

---

## 改进建议规则引擎

### 短板提示规则

| 条件 | 建议内容 | 严重程度 |
|------|----------|----------|
| 效率分 < 团队均值 | "平均解决耗时高于团队均值 X%，建议关注问题分解和时间管理" | medium |
| 自引入 Bug 率 > 团队均值 | "自引入 Bug 率 X%，高于团队均值，建议加强代码自测" | high |
| 代码流失率 > 0.2 | "代码流失率 X%，部分代码稳定性不足，建议加强设计评审" | medium |
| 提交粒度平均 > 300 行 | "平均每次提交 X 行，建议拆分为更小的原子提交" | low |
| P0 处理占比 < 10% | "高优先级问题处理占比仅 X%，建议提升紧急响应能力" | medium |
| conventional_ratio < 0.5 | "仅 X% 的提交遵循规范格式，建议统一提交信息规范" | low |

### 趋势提示规则

| 条件 | 建议内容 |
|------|----------|
| 某维度环比下降 > 10% | "⚠️ {维度}评分本期下降 X%，关注是否有阻塞因素" |
| 某维度连续 3+ 周期下降 | "🔴 {维度}连续 N 个周期下降，建议重点关注" |
| 某维度环比提升 > 10% | "🎯 {维度}本期提升 X%，保持势头" |
| 某维度连续 3+ 周期提升 | "🌟 {维度}连续 N 个周期提升，表现优秀" |

### 能力画像生成

根据五维评分的最高分和最低分自动归类：

| 最高维度 | 最低维度 | 画像 |
|----------|----------|------|
| 效率 | 质量 | "快速响应型，质量有提升空间" |
| 产出 | 能力 | "高产出型，建议拓展技术广度" |
| 质量 | 效率 | "精工细作型，可适当提升响应速度" |
| 能力 | 产出 | "技术全面型，可聚焦提升产出量" |
| 均衡（差异 < 10） | — | "均衡发展型，各维度表现稳定" |

---

## 页面结构

### 第一层：团队仪表盘

**路由：** `/app/kpi`
**权限：** `kpi.view_kpisnapshot`（管理员组）

**布局：**
1. **顶部工具栏**
   - 时间快捷按钮：本周 / 本月 / 本季度
   - 自定义日期范围选择器
   - 角色筛选下拉框（默认"开发人员"）
   - 刷新数据按钮（需 `kpi.refresh_kpi` 权限）

2. **总览统计卡片**（4 列）
   - 活跃开发者数
   - 本周期解决问题数
   - 团队平均解决耗时
   - 团队平均综合分

3. **开发者排名表**
   - 列：排名、开发者（头像+名称）、综合分、效率、产出、质量、能力、成长、趋势（环比百分比）、操作（查看详情）
   - 按综合分降序
   - 点击行跳转到个人档案

### 第二层：个人 KPI 档案

**路由：** `/app/kpi/:userId`（管理者访问任意用户），`/app/kpi/me`（员工访问自己）
**权限：** `kpi.view_own_kpi`（所有非只读用户）

**布局：**
1. **用户头部**
   - 头像、名称、角色组、总 commit 数、关联仓库数
   - 综合评分（大字）

2. **标签页导航**

   **标签 1 — 问题指标：**
   - 左：五维雷达图
   - 右：指标卡片（负责问题数、已解决数+解决率、平均解决耗时、日均解决数、加权问题价值）
   - 下方：按优先级分解的明细表

   **标签 2 — Commit 分析：**
   - 提交总数、代码增删量、conventional commit 率
   - 自引入 Bug 率、代码流失率（醒目卡片）
   - 提交粒度分布直方图
   - 技术栈广度标签列表
   - 工作节奏热力图（小时 × 星期）
   - 提交类型分布饼图
   - 仓库覆盖列表

   **标签 3 — 趋势变化：**
   - 五维评分趋势折线图（X轴时间，5条线）
   - 关键指标环比卡片（本期 vs 上期，绿色/红色箭头）
   - 连续趋势高亮提示

   **标签 4 — 改进建议：**
   - 能力画像一句话摘要（顶部醒目位置）
   - 短板提示列表（按严重程度排序）
   - 趋势提示列表
   - 综合改进建议

---

## 权限设计

### 新增权限

| 权限 codename | 说明 | 分配给 |
|---------------|------|--------|
| `view_kpisnapshot` | 查看团队 KPI 仪表盘（Django 自动生成） | 管理员 |
| `view_own_kpi` | 查看自己的 KPI 档案（Meta.permissions 自定义） | 管理员、开发者、产品经理、测试 |
| `refresh_kpi` | 触发 KPI 数据刷新（Meta.permissions 自定义） | 管理员 |

### 路由守卫

- `/app/kpi` — 需要 `kpi.view_kpisnapshot`
- `/app/kpi/me` — 需要 `kpi.view_own_kpi`
- `/app/kpi/:userId` — 需要 `kpi.view_kpisnapshot`（管理者），或 userId === 当前用户（员工自己）

### 导航

在 `useNavigation.ts` 的 `GROUP_DEFS` 中，`用户管理` 的 paths 新增 `/app/kpi`。

在 `PAGE_PERMS.SEED_ROUTES` 新增（插入到 users 和 notifications 之间，notifications 的 sort_order 从 6 调整为 7）：
```python
{"path": "/app/kpi", "label": "KPI 分析", "icon": "i-heroicons-chart-bar-square", "permission": "kpi.view_kpisnapshot", "sort_order": 6}
```

---

## API 设计

### 团队仪表盘

```
GET /api/kpi/team/
  Query: period=week|month|quarter, start=YYYY-MM-DD, end=YYYY-MM-DD, role=开发人员
  Response: {
    "summary": { "active_count", "resolved_count", "avg_resolution_hours", "avg_overall_score" },
    "developers": [
      { "user_id", "user_name", "avatar", "scores", "rankings", "trend_percent" }
    ]
  }
  Permission: kpi.view_kpisnapshot
```

### 个人 KPI 档案

```
GET /api/kpi/users/{user_id}/summary/
  Response: { "user", "scores", "rankings", "profile" }
  Permission: kpi.view_kpisnapshot 或 user_id == 当前用户

GET /api/kpi/users/{user_id}/issues/
  Response: { "issue_metrics", "priority_breakdown" }

GET /api/kpi/users/{user_id}/commits/
  Response: { "commit_metrics" }

GET /api/kpi/users/{user_id}/trends/
  Query: periods=6 (返回最近 N 个周期的历史快照)
  Response: { "history": [{ "period_start", "period_end", "scores" }], "changes": {...} }

GET /api/kpi/users/{user_id}/suggestions/
  Response: { "suggestions" }
```

### 自己的 KPI（普通员工快捷路径）

```
GET /api/kpi/me/summary/        → 等价于 /api/kpi/users/{current_user}/summary/
GET /api/kpi/me/issues/
GET /api/kpi/me/commits/
GET /api/kpi/me/trends/
GET /api/kpi/me/suggestions/
```

### 数据刷新

```
POST /api/kpi/refresh/
  Body: { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" } (可选，默认当前周期)
  Permission: kpi.refresh_kpi
  Response: { "status": "completed", "computed_at": "...", "user_count": N }
```

同步执行（项目无 Celery）。前端显示 loading 状态。如果未来计算量增长导致超时，再引入异步方案。

---

## 计算服务

### KPI 计算流程

1. 确定目标用户列表（按角色筛选）
2. 确定时间范围
3. 对每个用户：
   a. 从 Issue 表聚合问题指标（assignee + helpers）
   b. 从所有关联仓库的 Commit 表聚合 commit 指标（通过 GitAuthorAlias）
   c. 计算问题价值分
   d. 计算五维绝对分数
4. 汇总所有用户后，计算团队百分位排名
5. 获取上一个周期的快照，计算成长分和趋势
6. 运行改进建议规则引擎
7. 写入/更新 KPISnapshot 记录

### 计算触发方式

- **手动触发：** 管理者点击"刷新数据"按钮，调用 `POST /api/kpi/refresh/`
- **定时任务（可选，未来扩展）：** 每天凌晨自动计算前一天的数据

### 性能考虑

- Commit 数据依赖已克隆的仓库（`clone_status="cloned"`）
- Issue 查询排除软删除记录（`is_deleted=False`）
- 大时间范围的 commit 遍历可能较慢，刷新接口应异步执行
- 建议使用 Django 的 `select_related` / `prefetch_related` 优化查询
