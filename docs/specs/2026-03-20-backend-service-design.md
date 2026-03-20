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
| roles | JSONField | `["管理员", "开发者", "前端开发", "后端开发", "测试", "产品经理"]` | 用户角色选项 |

### users app — User

扩展 `AbstractUser`。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDField (pk) | 主键 |
| username | CharField | 登录用户名（继承） |
| name | CharField(max_length=50) | 显示姓名 |
| email | EmailField | 邮箱 |
| github_id | CharField(max_length=100, blank=True) | GitHub 用户名 |
| role | CharField(max_length=20) | 角色，校验来自 SiteSettings.roles |
| avatar | URLField(blank=True) | 头像 URL |

### projects app — Project

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUIDField (pk) | 主键 |
| name | CharField(max_length=100) | 项目名 |
| description | TextField(blank=True) | 描述 |
| status | CharField(max_length=20) | 进行中 / 已完成 / 已归档 |
| remark | TextField(blank=True) | 备注 |
| estimated_completion | DateField(null=True) | 预计完成日期 |
| actual_hours | DecimalField(null=True) | 实际工时 |
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
| project | FK → Project | 所属项目 |
| title | CharField(max_length=200) | 标题 |
| description | TextField(blank=True) | 描述 |
| priority | CharField(max_length=10) | P0 / P1 / P2 / P3 |
| status | CharField(max_length=20) | 待处理 / 进行中 / 已解决 / 已关闭 |
| labels | JSONField(default=list) | 标签数组，校验来自 SiteSettings.labels |
| reporter | FK → User(related_name="reported_issues") | 提出人 |
| assignee | FK → User(null=True, related_name="assigned_issues") | 负责人 |
| remark | TextField(blank=True) | 备注 |
| estimated_completion | DateField(null=True) | 预计完成 |
| actual_hours | DecimalField(null=True) | 实际工时 |
| cause | TextField(blank=True) | 原因分析 |
| solution | TextField(blank=True) | 解决办法 |
| created_at | DateTimeField(auto_now_add=True) | 创建时间 |
| resolved_at | DateTimeField(null=True) | 解决时间 |

**计算属性**：
- `resolution_hours` — 由 `resolved_at - created_at` 在 serializer 中计算，不存储

**未纳入字段**（属于 GitHub/AI 模块，后续扩展）：
- branch_name, branch_created_at, branch_merged_at
- linked_commits, linked_prs
- ai_analysis

## API 设计

所有接口前缀 `/api/`，需 JWT 认证（除 login/refresh）。

### 认证

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/auth/login/` | 登录，返回 access + refresh token |
| POST | `/api/auth/refresh/` | 刷新 access token |
| GET | `/api/auth/me/` | 当前用户信息 |

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
| GET | `/api/issues/` | Issue 列表（筛选：priority, status, labels, assignee, project_id） |
| POST | `/api/issues/` | 创建 Issue |
| GET | `/api/issues/:id/` | Issue 详情 |
| PATCH | `/api/issues/:id/` | 更新 Issue |
| DELETE | `/api/issues/:id/` | 删除 Issue |
| PATCH | `/api/issues/batch/` | 批量操作（分配负责人、改优先级） |

**筛选**: query params `?priority=P0&status=进行中&assignee=uuid&labels=前端`
**分页**: `PageNumberPagination`，默认 20 条
**排序**: `?ordering=-created_at,priority`

### Dashboard 聚合

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats/` | 总 Issue 数、待处理、进行中、本周已解决 |
| GET | `/api/dashboard/trends/` | 近 30 天每日新增/解决趋势 |
| GET | `/api/dashboard/priority-distribution/` | P0-P3 分布 |
| GET | `/api/dashboard/developer-leaderboard/` | 本月解决数 Top 5 |
| GET | `/api/dashboard/recent-activity/` | 最近活动流 |

Dashboard 接口为只读聚合查询，归属 issues app。

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
devServer: {
  proxy: {
    '/api': { target: 'http://localhost:8000' }
  }
}
```

### 前端改造

- 新建 `composables/useApi.ts` — 封装 `$fetch`，统一注入 JWT token，处理 token 刷新
- 登录页接入 JWT 认证，token 存 localStorage
- 逐页从 `mock.ts` 切换到 `useApi` 调用真实 API

## 不在本次范围

- GitHub 仓库模块（repos app、webhook）
- AI 洞察模块（ai_analysis、insights 接口）
- 用户注册 / 密码重置
- 文件上传 / 头像上传
- WebSocket / 实时通知
- Docker 部署配置
