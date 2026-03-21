# django-page-perms 设计文档

## 概述

将前端页面-权限映射、组-权限分配、自定义权限创建从硬编码变为后端 API 驱动的动态配置系统，封装为可复用的 Django 包。

### 目标

1. 替代散落在 `useNavigation.ts`、`auth.global.ts`、`setup_groups.py` 三处的硬编码权限映射
2. 提供 superuser 专用的前端管理界面，支持运行时配置
3. 后端封装为独立 PyPI 包，可安装到任何 Django + DRF 项目
4. README 提供前端集成指引，不绑定具体前端框架

### 约束

- 管理页面仅 Django superuser 可访问（系统级操作，误操作可能导致服务异常）
- 后端包用 uv 管理
- 开发阶段在 monorepo 的 `packages/django-page-perms/` 目录，editable install 到当前项目
- 前端管理页面为当前项目的具体实现，不包含在包内

## 包结构

```
packages/django-page-perms/
├── pyproject.toml              # uv 管理
├── README.md                   # 安装说明 + 前端集成指引
├── page_perms/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── management/
│       └── commands/
│           └── sync_page_perms.py
```

当前项目通过 `uv add --editable ../packages/django-page-perms` 引入。

## Models

### PageRoute

前端路由与 Django Permission 的映射关系。

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | CharField(max_length=255), unique | 前端路由路径，如 `/app/issues` |
| `label` | CharField(max_length=100) | 显示名称，如 `问题追踪` |
| `icon` | CharField(max_length=100), blank | 图标类名，如 `i-heroicons-bug-ant` |
| `permission` | ForeignKey(Permission), null, on_delete=SET_NULL | 关联的 Django Permission，null 表示无需权限 |
| `show_in_nav` | BooleanField, default=True | 是否显示在侧边栏导航 |
| `sort_order` | IntegerField, default=0 | 侧边栏排序 |
| `is_active` | BooleanField, default=True | 是否启用 |
| `synced` | BooleanField, default=False | 是否由 sync_page_perms 命令写入（区分种子数据和 UI 手动添加） |

路由匹配规则：前缀匹配，`/app/issues` 覆盖 `/app/issues/xxx`。

### 自定义权限

不新建 Permission model。纯逻辑权限通过 Django 内置 `auth.Permission` 创建，挂靠 `page_perms | page_route` 的 content_type。

## API 设计

所有接口挂载在使用方配置的前缀下：

```python
# 使用方的 urls.py
path("api/page-perms/", include("page_perms.urls"))
```

### PageRoute 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/routes/` | IsAuthenticated | 列出所有活跃路由（前端启动时拉取） |
| POST | `/routes/` | IsSuperUser | 创建路由映射 |
| PATCH | `/routes/{id}/` | IsSuperUser | 修改路由映射 |
| DELETE | `/routes/{id}/` | IsSuperUser | 删除路由映射 |

GET `/routes/` 返回示例：

```json
[
  {
    "id": 1,
    "path": "/app/issues",
    "label": "问题追踪",
    "icon": "i-heroicons-bug-ant",
    "permission": "issues.view_issue",
    "show_in_nav": true,
    "sort_order": 1,
    "is_active": true
  }
]
```

### Permission 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/permissions/` | IsSuperUser | 列出所有权限，按 app 分组，标注来源（model / 自定义） |
| POST | `/permissions/` | IsSuperUser | 创建纯逻辑权限（挂靠 page_route content type） |
| DELETE | `/permissions/{id}/` | IsSuperUser | 删除自定义权限。model 权限不可删 |

### Group 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/groups/` | IsSuperUser | 列出所有组及其关联的权限 |
| PATCH | `/groups/{id}/` | IsSuperUser | 修改组的权限列表 |

### 配置项

```python
PAGE_PERMS = {
    "ROUTE_LIST_PERMISSION": "IsAuthenticated",  # GET /routes/ 的权限，可覆盖
}
```

## Management Command: sync_page_perms

替代现有 `setup_groups.py`，幂等同步种子数据。

```bash
uv run python manage.py sync_page_perms
```

### 种子数据配置

使用方在 Django settings 中定义：

```python
PAGE_PERMS = {
    "SEED_ROUTES": [
        {"path": "/app/dashboard", "label": "项目概览", "icon": "i-heroicons-squares-2x2", "permission": "issues.view_dashboard", "sort_order": 0},
        {"path": "/app/issues", "label": "问题追踪", "icon": "i-heroicons-bug-ant", "permission": "issues.view_issue", "sort_order": 1},
    ],
    "SEED_GROUPS": {
        "管理员": {"apps": ["projects", "issues", "settings", "repos"]},
        "开发者": {"permissions": ["view_project", "view_issue", "add_issue", "change_issue", "view_activity", "view_dashboard"]},
        "产品经理": {"inherit": "开发者", "permissions": ["add_project", "change_project", "manage_project_members"]},
        "只读成员": {"permissions_startswith": ["view_"]},
    },
}
```

### 幂等性规则

- PageRoute 以 `path` 为 key，存在则更新，不存在则创建，标记 `synced=True`
- Group 以 `name` 为 key，权限集合做全量同步
- 不删除 UI 中手动添加的数据（只同步 `synced=True` 的记录）

### 与现有 setup_groups.py 的迁移

1. 在 `backend/config/settings.py` 中配置 `PAGE_PERMS` 种子数据
2. 将 `setup_groups.py` 中的组定义迁移到 `SEED_GROUPS`
3. 运行 `sync_page_perms` 替代 `setup_groups`
4. 删除旧的 `setup_groups.py`

## 前端集成方案（当前项目）

### 新增 composable

**`usePagePerms.ts`** — 启动时调用 GET `/api/page-perms/routes/`，缓存路由配置。

### 改造现有文件

1. **`useNavigation.ts`** — `navItems` 从 `usePagePerms` 读取，不再硬编码。`filteredNavItems` 逻辑不变（仍用 `can()` 过滤）
2. **`auth.global.ts`** — `routePermissions` 从 `usePagePerms` 读取映射表，不再硬编码

### 新增管理页面

`/app/permissions` — 单页面三个 Tab，仅 superuser 可见：

**Tab 1：页面路由映射**
- 表格展示所有 PageRoute，支持内联编辑
- permission 字段下拉选择（从权限列表拉取）
- 拖拽排序 sort_order
- 开关切换 is_active 和 show_in_nav

**Tab 2：组-权限分配**
- 左侧列出所有组
- 右侧权限 checkbox 矩阵，按 app 分组
- 修改后调用 PATCH `/groups/{id}/`

**Tab 3：权限列表**
- 表格展示所有权限，标注来源（model / 自定义）
- Model 权限只读，自定义权限可删除
- 支持创建纯逻辑权限（表单：codename + 名称）

### 启动时序

```
用户登录
  → /api/auth/me/        返回 user.permissions    ──┐
  → /api/page-perms/routes/ 返回路由配置            ──┤ 并发
  → useNavigation 构建 navItems（from routes）       ←┘
  → auth.global.ts 构建 routePermissions（from routes）
  → 页面渲染
```

## 安全与边界情况

### 安全防护

1. **写操作全部限 superuser** — 包的 IsSuperUser permission class 在 view 层拦截
2. **Model 权限不可删** — API 层面判断 content_type 是否指向真实 model，是则拒绝
3. **防止锁死** — 删除或停用 `/app/permissions` 路由时，API 返回 400 拒绝（管理页面不能被自己关掉）
4. **变更审计** — 组-权限修改记录到 Django LogEntry（who、when、diff）

### 边界情况

1. **路由配置 API 请求失败** — 前端显示全局错误提示，不渲染受保护页面，不做 fallback
2. **权限被删但路由还引用** — ForeignKey on_delete=SET_NULL，路由变为"无需权限"，API 返回时标注 warning
3. **并发修改** — 用 Django update_fields 做字段级更新，降低冲突概率
4. **sync_page_perms 与 UI 修改冲突** — command 只操作 `synced=True` 的记录，不触碰 UI 手动添加的数据

## 测试策略

包自带测试，使用 `pytest-django` + `factory-boy`：

- **Model 测试** — PageRoute 唯一约束、排序、on_delete 行为
- **API 测试** — CRUD 权限控制（superuser vs 普通用户 vs 未认证）
- **Command 测试** — 幂等性、种子数据同步、不删除手动数据
