# DevTrack Backend Service — Design Spec

## Overview

为 DevTrack 项目管理工具开发 Django REST Framework 后端，替代现有 mock 数据，提供真实的 API 服务。初始范围覆盖核心 CRUD（Users、Projects、Issues）+ Dashboard 统计聚合接口。

## 技术栈

- **框架**: Django 5 + Django REST Framework
- **数据库**: PostgreSQL (`pg://postgres:postgres@127.0.0.1:25432`)
- **认证**: JWT（djangorestframework-simplejwt）
- **单例配置**: django-solo
- **测试**: pytest + pytest-django + factory_boy + faker
- **开发方式**: TDD

## 目录结构

```
devtrack/
├── frontend/              ← 已有 Nuxt 3 项目
├── backend/
│   ├── config/            ← Django 项目配置
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── settings/      ← 系统设置（singleton）
│   │   ├── users/         ← 用户模型 + JWT 认证
│   │   ├── projects/      ← 项目 + 成员 CRUD
│   │   └── issues/        ← Issue CRUD + Dashboard 聚合
│   ├── tests/
│   │   ├── conftest.py    ← 共享 fixtures
│   │   ├── factories.py   ← factory_boy 工厂
│   │   ├── test_auth.py
│   │   ├── test_settings.py
│   │   ├── test_users.py
│   │   ├── test_projects.py
│   │   ├── test_issues.py
│   │   └── test_dashboard.py
│   ├── manage.py
│   └── requirements.txt
└── docs/
```

## 数据模型

### settings app — SiteSettings（单例）

基于 `django-solo` 的 `SingletonModel`，全局只有一行记录。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| labels | JSONField | `["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"]` | Issue 可用标签 |
| priorities | JSONField | `["P0", "P1", "P2", "P3"]` | 优先级选项 |
| issue_statuses | JSONField | `["待处理", "进行中", "已解决", "已关闭"]` | Issue 状态选项 |

### users app — User

扩展 `AbstractUser`。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDField (pk) | 主键 |
| username | CharField | 登录用户名（继承） |
| name | CharField(max_length=50) | 显示姓名 |
| email | EmailField | 邮箱 |
| github_id | CharField(max_length=100, blank=True) | GitHub 用户名 |
| avatar | URLField(blank=True) | 头像 URL |
| groups | M2M → Group（继承） | 角色，Group.name 作为角色展示名（如"管理员"、"前端开发"） |
| user_permissions | M2M → Permission（继承） | Django 内置权限，通常通过 Group 间接分配 |

### projects app — Project

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDField (pk) | 主键 |
| name | CharField(max_length=100) | 项目名 |
| description | TextField(blank=True) | 描述 |
| status | CharField(max_length=20) | 进行中 / 已完成 / 已归档 |
| remark | TextField(blank=True) | 备注 |
| estimated_completion | DateField(null=True) | 预计完成日期 |
| actual_hours | DecimalField(max_digits=8, decimal_places=2, null=True) | 实际工时 |
| linked_repos | JSONField(default=list) | 关联的 GitHub 仓库名列表（如 `["postloan-backend"]`），前端项目卡片展示用 |
| members | M2M → User through ProjectMember | 成员 |
| created_at | DateTimeField(auto_now_add=True) | 创建时间 |
| updated_at | DateTimeField(auto_now=True) | 更新时间 |

### projects app — ProjectMember

| 字段 | 类型 | 说明 |
|------|------|------|
| project | FK → Project | |
| user | FK → User | |
| role | CharField(max_length=20) | owner / admin / member |
| unique_together | (project, user) | |

### issues app — Issue

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDField (pk) | 主键 |
| number | AutoField (unique) | 自增展示编号，前端显示为 `ISS-001` 格式 |
| project | FK → Project | 所属项目 |
| title | CharField(max_length=200) | 标题 |
| description | TextField(blank=True) | 描述 |
| priority | CharField(max_length=10) | P0 / P1 / P2 / P3 |
| status | CharField(max_length=20) | 待处理 / 进行中 / 已解决 / 已关闭 |
| labels | JSONField(default=list) | 标签数组，serializer 层校验来自 SiteSettings.labels |
| reporter | FK → User(related_name="reported_issues") | 提出人 |
| assignee | FK → User(null=True, related_name="assigned_issues") | 负责人 |
| remark | TextField(blank=True) | 备注 |
| estimated_completion | DateField(null=True) | 预计完成 |
| actual_hours | DecimalField(max_digits=8, decimal_places=2, null=True) | 实际工时 |
| cause | TextField(blank=True) | 原因分析 |
| solution | TextField(blank=True) | 解决办法 |
| created_at | DateTimeField(auto_now_add=True) | 创建时间 |
| updated_at | DateTimeField(auto_now=True) | 更新时间 |
| resolved_at | DateTimeField(null=True) | 解决时间 |

**计算属性**：
- `resolution_hours` — 由 `resolved_at - created_at` 在 serializer 中计算，不存储
- `display_id` — serializer 中格式化为 `ISS-{number:03d}`

**校验策略**：所有动态枚举值（labels、priority、status、role）在 **serializer 层** 校验，从 SiteSettings 读取合法值列表。Model 层不做校验，保证 Django Admin 和 API 使用同一套规则。

**未纳入字段**（属于 GitHub/AI 模块，后续扩展）：
- branch_name, branch_created_at, branch_merged_at
- linked_commits, linked_prs
- ai_analysis

### issues app — Activity（活动记录）

Issue 变更时自动创建活动记录，用于 Dashboard 活动流。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDField (pk) | 主键 |
| user | FK → User | 操作人 |
| action | CharField(max_length=20) | 动作类型：created / updated / resolved / closed / assigned |
| issue | FK → Issue | 关联 Issue |
| detail | CharField(max_length=200, blank=True) | 补充信息（如"优先级从 P2 改为 P0"） |
| created_at | DateTimeField(auto_now_add=True) | 操作时间 |

Activity 记录通过 Issue serializer 的 `save()` 方法自动创建，不暴露独立的 CRUD 接口。

## API 设计

所有接口前缀 `/api/`，需 JWT 认证（除 login/refresh）。

### 认证

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/auth/login/` | 登录，返回 access + refresh token |
| POST | `/api/auth/refresh/` | 刷新 access token |
| GET | `/api/auth/me/` | 当前用户信息（含 groups + permissions） |

`GET /api/auth/me/` 响应格式：

```json
{
  "id": "uuid",
  "name": "张三",
  "email": "zhangsan@example.com",
  "avatar": "",
  "groups": ["前端开发"],
  "permissions": ["view_project", "add_issue", "change_issue", "view_issue", "view_dashboard"]
}
```

### 系统设置

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/settings/` | 获取系统设置 |

### 用户

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/users/` | 用户列表 |
| GET | `/api/users/:id/` | 用户详情 |

用户创建和管理通过 Django Admin。

### 项目

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/projects/` | 项目列表（含成员数、issue 统计） |
| POST | `/api/projects/` | 创建项目 |
| GET | `/api/projects/:id/` | 项目详情（含成员列表） |
| PATCH | `/api/projects/:id/` | 更新项目 |
| DELETE | `/api/projects/:id/` | 删除项目 |
| GET | `/api/projects/:id/members/` | 项目成员列表 |
| POST | `/api/projects/:id/members/` | 添加成员 |
| DELETE | `/api/projects/:id/members/:user_id/` | 移除成员 |
| GET | `/api/projects/:id/issues/` | 该项目下的 issues |

### Issues

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/issues/` | Issue 列表（筛选 + 搜索） |
| POST | `/api/issues/` | 创建 Issue |
| GET | `/api/issues/:id/` | Issue 详情 |
| PATCH | `/api/issues/:id/` | 更新 Issue |
| DELETE | `/api/issues/:id/` | 删除 Issue |
| POST | `/api/issues/batch-update/` | 批量操作（分配负责人、改优先级） |

**筛选**: query params `?priority=P0&status=进行中&assignee=uuid&labels=前端&project_id=uuid`
**搜索**: `?search=关键词`（DRF SearchFilter，匹配 title 和 display_id）
**分页**: `PageNumberPagination`，默认 20 条
**排序**: `?ordering=-created_at,priority`

**批量操作请求格式**：

```json
{
  "ids": ["uuid1", "uuid2"],
  "action": "assign",       // assign | set_priority
  "value": "user-uuid"      // assignee UUID 或 "P0"/"P1" 等
}
```

### Dashboard 聚合

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats/` | 总 Issue 数、待处理、进行中、本周已解决 |
| GET | `/api/dashboard/trends/` | 近 30 天每日新增/解决趋势 |
| GET | `/api/dashboard/priority-distribution/` | P0-P3 分布 |
| GET | `/api/dashboard/developer-leaderboard/` | 本月解决数 Top 5 |
| GET | `/api/dashboard/recent-activity/` | 最近活动流 |

Dashboard 接口为只读聚合查询，归属 issues app。均不分页，返回单个对象或数组。

**响应格式定义**：

`GET /api/dashboard/stats/` — 返回单个对象：

```json
{
  "total": 55,
  "pending": 12,
  "in_progress": 8,
  "resolved_this_week": 5
}
```

`GET /api/dashboard/trends/` — 滚动 30 天，每日一条：

```json
[
  { "date": "2026-02-18", "created": 3, "resolved": 2 },
  { "date": "2026-02-19", "created": 1, "resolved": 4 }
]
```

`GET /api/dashboard/priority-distribution/` — 按优先级聚合：

```json
[
  { "priority": "P0", "count": 5 },
  { "priority": "P1", "count": 12 },
  { "priority": "P2", "count": 25 },
  { "priority": "P3", "count": 13 }
]
```

`GET /api/dashboard/developer-leaderboard/` — 本月 Top 5，含基础统计：

```json
[
  {
    "user_id": "uuid",
    "user_name": "张三",
    "monthly_resolved_count": 15,
    "avg_resolution_hours": 4.2
  }
]
```

`GET /api/dashboard/recent-activity/` — 最近 20 条 Activity 记录：

```json
[
  {
    "id": "uuid",
    "user_name": "张三",
    "action": "resolved",
    "issue_title": "登录页样式错乱",
    "issue_id": "uuid",
    "issue_display_id": "ISS-042",
    "created_at": "2026-03-20T10:30:00Z"
  }
]
```

## TDD 策略

### 工具链

- `pytest` + `pytest-django` — 测试运行器
- `factory_boy` — 模型工厂
- `faker`（zh_CN locale）— 测试数据生成

### 测试层次

**Model 测试**：
- SiteSettings singleton 行为
- Issue resolution_hours 计算属性
- ProjectMember unique_together 约束

**API 测试**：
- 每个端点的 CRUD 正常流程（200/201/204）
- 认证检查（未登录 → 401）
- 筛选/分页/排序正确性
- 批量操作原子性
- Dashboard 聚合结果正确性

### Factory 设计

从 `mock.ts` 提取数据结构和分布特征，建立 factory_boy 工厂：
- `UserFactory` — 覆盖各角色
- `ProjectFactory` — 含成员关系
- `IssueFactory` — 覆盖各 priority/status/labels 组合
- `SiteSettingsFactory` — 预填默认配置

### TDD 循环

每个 API 端点开发顺序：
1. 写 Factory（如果还没有）
2. 写 API 测试（assert 预期响应）
3. 跑测试 → 红
4. 写 model → serializer → view → urls
5. 跑测试 → 绿
6. 重构

## 前端对接

### Nuxt proxy 配置

```ts
// nuxt.config.ts
routeRules: {
  '/api/**': { proxy: 'http://localhost:8000/api/**' }
}
```

### 前端改造

- 新建 `composables/useApi.ts` — 封装 `$fetch`，统一注入 JWT token，处理 token 刷新
- 新建 `composables/useAuth.ts` — 封装当前用户信息、`can(perm)` 权限判断函数
- 登录页接入 JWT 认证，token 存 localStorage
- 逐页从 `mock.ts` 切换到 `useApi` 调用真实 API
- Nuxt middleware 做页面级权限拦截，无权限时重定向
- 侧边栏导航项根据 `can()` 动态显示/隐藏

## 权限设计

基于 Django 内置的 `Group` + `Permission` 系统。不使用自定义 `role` 字段，Group.name 即角色展示名。

### 预设 Groups（角色）

| Group | 说明 | 典型权限 |
|-------|------|---------|
| 管理员 | 全部权限 | 所有 add/change/delete/view |
| 开发者 | 可操作 Issue，查看项目 | view/add/change Issue, view Project, view Dashboard |
| 产品经理 | 可管理项目和 Issue | view/add/change Project, view/add/change Issue, view Dashboard |
| 只读成员 | 仅查看 | 所有 view_* 权限 |

### 权限列表

使用 Django 自动生成的 model permissions（`add_`/`change_`/`delete_`/`view_` 前缀），外加自定义权限：

**自动生成**：

- `view_project` / `add_project` / `change_project` / `delete_project`
- `view_issue` / `add_issue` / `change_issue` / `delete_issue`
- `view_activity`

**自定义**（在 model Meta 中定义）：

- `batch_update_issue` — 批量操作 Issue
- `manage_project_members` — 管理项目成员
- `view_dashboard` — 查看 Dashboard

### 后端权限检查

使用 DRF 的 `DjangoModelPermissions`（自动映射 HTTP method → model permission），自定义权限用 `@permission_required` 装饰器或自定义 Permission class。

### 前端权限控制

- **页面级**：Nuxt route middleware 检查 `permissions` 数组，无权限重定向到 403
- **元素级**：`v-if="can('delete_project')"` 控制按钮/菜单项可见性
- **侧边栏**：每个导航项关联所需权限，动态渲染

## 不在本次范围

- GitHub 仓库模块（repos app、webhook）
- AI 洞察模块（ai_analysis、insights 接口）
- 用户注册 / 密码重置
- 文件上传 / 头像上传
- WebSocket / 实时通知
- Docker 部署配置
