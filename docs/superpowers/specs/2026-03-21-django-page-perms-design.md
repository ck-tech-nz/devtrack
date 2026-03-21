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
- 包的 PageRoute model 使用 auto-increment integer PK（非 UUID）。作为独立可复用包，不继承宿主项目的 PK 策略，保持对任何 Django 项目的兼容性

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
| `meta` | JSONField, default=dict, blank | 前端自定义元数据（如 `{"serviceKey": "github"}`），包本身不解释此字段，由前端自行使用 |
| `source` | CharField(max_length=20), default="manual" | 数据来源：`"seed"`（sync 命令写入）或 `"manual"`（UI 手动添加），用于 sync 命令的幂等性判断 |

路由匹配规则：前缀匹配，`/app/issues` 覆盖 `/app/issues/xxx`。

> **设计决策：扁平结构，不支持嵌套导航。** 当前项目的 NavItem 接口有 `children` 字段，但实际未使用嵌套。PageRoute 保持扁平结构。如未来需要层级导航，可通过 `meta` 字段或新增 `parent` FK 扩展。

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
| GET | `/routes/` | IsAuthenticated | 列出活跃路由（前端启动时拉取）。Superuser 可加 `?all=true` 查看含非活跃路由 |
| POST | `/routes/` | IsSuperUser | 创建路由映射 |
| PATCH | `/routes/{id}/` | IsSuperUser | 修改路由映射，支持 partial update（DRF `partial=True`），前端可只发送变更字段 |
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
    "is_active": true,
    "meta": {}
  },
  {
    "id": 4,
    "path": "/app/repos",
    "label": "GitHub 仓库",
    "icon": "i-heroicons-code-bracket",
    "permission": "repos.view_repo",
    "show_in_nav": true,
    "sort_order": 3,
    "is_active": true,
    "meta": {"serviceKey": "github"}
  }
]
```

**Permission 字段的序列化：** API 输入输出均使用 `"app_label.codename"` 字符串格式（如 `"issues.view_issue"`）。Serializer 内部解析该字符串并关联到 `auth.Permission` FK。如果字符串不匹配任何已有 Permission，返回 400 错误。`permission` 为 `null` 时表示无需权限。

> **信息泄露说明：** GET `/routes/` 对所有认证用户开放，意味着普通用户可通过 API 看到完整路由列表（包括无权访问的路由）。这是有意设计 — 前端路由守卫需要完整映射表来正确拦截未授权访问。路由路径本身不构成敏感信息。

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

**SEED_GROUPS 语义说明：**

- `apps` — 授予指定 app 的所有权限。可与 `permissions` 合并使用
- `permissions` — 按 codename 精确匹配。跨 app 的同名 codename 会全部匹配
- `permissions_startswith` — 前缀匹配所有 app 中以该前缀开头的 codename
- `inherit` — **同步时快照**，将目标组在 seed 配置中定义的权限合并到当前组。不是运行时的动态关联 — 后续在 UI 中修改被继承组的权限，不会自动传播到继承方
- 以上字段可自由组合，最终权限集合取并集

### 幂等性规则

- PageRoute 以 `path` 为 key，存在则更新，不存在则创建，标记 `source="seed"`
- Group 以 `name` 为 key，权限集合做全量同步
- 不删除 `source="manual"` 的数据（sync 命令只操作 `source="seed"` 的记录）

### 与现有 setup_groups.py 的迁移

1. 在 `backend/config/settings.py` 中配置 `PAGE_PERMS` 种子数据
2. 将 `setup_groups.py` 中的组定义迁移到 `SEED_GROUPS`
3. 运行 `sync_page_perms` 替代 `setup_groups`
4. 删除旧的 `setup_groups.py`

## 前端集成方案（当前项目）

### 新增 composable

**`usePagePerms.ts`** — 启动时调用 GET `/api/page-perms/routes/`，缓存路由配置。

### 改造现有文件

1. **`useNavigation.ts`** — `navItems` 从 `usePagePerms` 读取，不再硬编码。`filteredNavItems` 逻辑不变（仍用 `can()` 过滤）。`serviceKey` 等前端特有逻辑从 `meta` 字段读取
2. **`auth.global.ts`** — `routePermissions` 从 `usePagePerms` 读取映射表，不再硬编码

### 面包屑迁移

当前 `useNavigation.ts` 中面包屑的第一级（路由匹配 navItems 的 label）可以自动从 PageRoute 数据生成。子页面的面包屑（如"项目详情"、"Issue 详情"）属于前端页面级逻辑，保留在前端硬编码，不纳入包的管理范围

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
3. **防止锁死** — 删除或停用 `/app/permissions` 路由时，API 返回 400 拒绝（管理页面不能被自己关掉）。注：Django superuser 天然绕过所有权限检查，因此即使组权限被误改，superuser 仍可通过 API 访问所有端点恢复配置
4. **变更审计** — 组-权限修改记录到 Django LogEntry（who、when、diff）

### 边界情况

1. **路由配置 API 请求失败** — 前端显示全局错误提示，不渲染受保护页面，不做 fallback
2. **权限被删但路由还引用** — ForeignKey on_delete=SET_NULL，路由变为"无需权限"，API 返回时标注 warning
3. **并发修改** — 用 Django update_fields 做字段级更新，降低冲突概率
4. **sync_page_perms 与 UI 修改冲突** — command 只操作 `source="seed"` 的记录，不触碰 `source="manual"` 的数据
5. **路由配置缓存过期** — 前端启动时拉取一次路由配置，在用户会话期间不会自动更新。Superuser 修改配置后，其他已登录用户需刷新页面才能看到变化。这是可接受的最终一致性 — 权限变更本身就是低频操作，不值得引入 WebSocket 或轮询

## Migrations

包自带预生成的 migrations（标准 Django 可复用包做法）。使用方安装后运行 `python manage.py migrate` 即可，无需手动 `makemigrations`。

## 测试策略

包自带测试，使用 `pytest-django` + `factory-boy`：

- **Model 测试** — PageRoute 唯一约束、排序、on_delete=SET_NULL 行为
- **API 测试** — CRUD 权限控制（superuser vs 普通用户 vs 未认证）、partial update、`?all=true` 参数、permission 字符串解析与 400 校验
- **安全防护测试** — 管理页面锁死保护（不可删除/停用 `/app/permissions`）、model 权限不可删除、非 superuser 写操作被拒绝
- **Command 测试** — 幂等性、种子数据同步、不删除 `source="manual"` 数据、inherit 快照语义
