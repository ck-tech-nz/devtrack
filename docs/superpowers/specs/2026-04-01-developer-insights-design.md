# Developer Insights — 开发者能力评估设计

## Overview

在仓库详情页新增「开发者洞察」Tab，基于 Git commit 数据对团队成员进行多维度能力评估。采用渐进式方案：Phase 1 建立指标基础，Phase 2 叠加 AI 洞察。

**本文档覆盖 Phase 1。**

## Architecture

### 新增 Models（repos app）

#### `Commit`

| Field | Type | Description |
|-------|------|-------------|
| repo | FK(Repo) | 所属仓库 |
| hash | CharField(40) | Git commit hash，unique_together with repo |
| author_name | CharField | Git author name（from %an） |
| author_email | CharField | Git author email（from %ae） |
| date | DateTimeField | 提交时间 |
| message | TextField | Commit message |
| additions | IntegerField | 新增行数（from --stat） |
| deletions | IntegerField | 删除行数（from --stat） |
| files_changed | JSONField | 变更文件路径列表 |

#### `GitAuthorAlias`

| Field | Type | Description |
|-------|------|-------------|
| repo | FK(Repo) | 所属仓库 |
| author_email | CharField | Git author email |
| author_name | CharField | Git author name |
| user | FK(User, nullable) | 手动关联的系统用户 |
| unique_together | (repo, author_email) | |

**关联流程：**
1. sync-commits 时，遇到新的 (repo, email) 自动创建 GitAuthorAlias
2. 自动尝试 email 匹配 User.email
3. 未关联的在「开发者洞察」Tab 顶部提醒管理员手动关联

### API Endpoints（repos app）

```
POST /api/repos/{id}/sync-commits/
     - 解析 git log --stat 写入 Commit 表
     - 创建/更新 GitAuthorAlias
     - clone/pull 成功后自动调用

GET  /api/repos/{id}/developer-insights/
     - query: ?days=90 (30 | 90 | all)
     - 返回: 所有开发者的四维评分 + 基础统计
     - 前端切换到「开发者洞察」Tab 时调用

GET  /api/repos/{id}/developer-insights/{alias_id}/
     - query: ?days=90
     - alias_id: GitAuthorAlias 的 UUID
     - 返回: 单人详情（雷达图数据 + 各维度明细 + commit 类型分布）

PATCH /api/repos/{id}/git-author-aliases/{id}/
     - body: { user: user_id }
     - 管理员手动关联 git author → user
```

### Service Layer

`DeveloperInsightsService` in `backend/apps/repos/services.py`：
- 接收 repo + days 参数
- 查询 Commit 表聚合计算
- 不做缓存，数据量小（几百条 commits）直接查询

## Metrics — 四维评分模型

每个维度 0-100 分，基于仓库内开发者的相对排名（百分位映射）。独立开发者默认 50 分基准。

### 1. 代码贡献量

| 子指标 | 权重 | 计算方式 |
|--------|------|----------|
| Commit 数量 | 50% | 个人 commit 数在团队内的百分位 |
| 代码行数（additions + deletions） | 50% | 个人行数在团队内的百分位 |

### 2. 效率

| 子指标 | 权重 | 计算方式 |
|--------|------|----------|
| 提交频率 | 50% | commits / 活跃周数 |
| 活跃天数占比 | 50% | 有提交的天数 / 时间范围总天数 |

### 3. 能力

| 子指标 | 权重 | 计算方式 |
|--------|------|----------|
| 涉及目录广度 | 50% | unique top-level directories 数量 |
| Commit 类型多样性 | 50% | Shannon entropy，基于 conventional commit prefix (feat/fix/refactor/chore...) |

### 4. 质量

| 子指标 | 权重 | 计算方式 |
|--------|------|----------|
| Fix 占比（反转） | 50% | (1 - fix_ratio) 映射到百分位 |
| Commit message 规范度 | 50% | 匹配 `type(scope): message` 格式的比例 |

### 评分参数

- **时间范围：** 默认 90 天，可切换 30 天 / 90 天 / 全部
- **计算时机：** 每次 sync-commits 后实时计算（不缓存）
- **Conventional commits 检测：** 正则 `^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)(\(.+\))?[!]?:\s.+`

## UI Design

### 位置

仓库详情页新增第三个 Tab「开发者洞察」，与 Issues / 提交记录 并列。

### 层级 1：团队总览（默认视图）

- 顶部：时间筛选器（30天 / **90天** / 全部）
- 未关联作者提醒条（如有）："N 位作者未关联用户，点击关联"
- 每个开发者一张卡片：
  - 头像 + 名字 + commit 数 + 关联用户名
  - 四维度分数条（水平 bar，0-100，带颜色区分）
  - 「查看详情 →」链接

### 层级 2：个人详情（点击进入）

- 顶部：「← 返回」+ 头像 + 名字 + email + 关联用户
- 雷达图：四维度可视化（贡献量 / 效率 / 能力 / 质量）
- 四格明细卡片：
  - 贡献量：commits 数、代码行数 (+/-) 
  - 效率：提交频率、活跃天数占比
  - 能力：涉及目录数、commit 类型分布
  - 质量：fix 占比、规范度百分比
- AI 洞察占位区（Phase 2，灰色虚线框）

### 未关联作者弹窗

- 点击提醒条 → 弹窗列出所有 user=null 的 GitAuthorAlias
- 每行：author_name + author_email + 下拉选择 User
- 保存后刷新指标

## Data Collection

扩展 `RepoCloneService`：

1. `sync_commits(repo)` — 新方法
   - 执行 `git log --format=%H%x00%ae%x00%an%x00%aI%x00%s --stat`
   - 解析每条 commit 的 hash、author_email、author_name、date、message、additions、deletions、files_changed
   - 写入 Commit 表（跳过已存在的 hash）
   - 创建/更新 GitAuthorAlias

2. `clone_or_pull()` 成功后自动调用 `sync_commits()`

3. 现有 `get_log()` 保留给「提交记录」Tab（轻量，不需要 stat 数据）

## Phase 2: AI Insights（后续）

Phase 1 完成后，叠加 AI 分析层：
- 将结构化指标 + commit messages + issue 数据作为 context 发给 AI
- 生成个人画像：技术栈偏好、工作节奏、成长趋势
- 团队洞察：贡献分布均衡度、协作模式、潜在风险
- 复用现有 AI 分析框架（apps/issues 中的 AI 模块）
