---
name: page-permissions
description: 新增页面时，配置 Django 权限与前端路由守卫、侧边栏的联动
---

# 前端页面权限管理

本项目通过 Django Permission 控制前端页面的可见性和可访问性。新增页面时必须遵循以下步骤。

## 权限流转架构

```
Django Model Meta.permissions
        ↓
setup_groups.py 分配到用户组
        ↓
/api/auth/me/ 返回用户 permissions 列表
        ↓
前端 useAuth().can() 判断权限
        ↓
┌─ useNavigation: filteredNavItems 控制侧边栏可见性
└─ auth.global.ts: routePermissions 控制路由可访问性
```

## 新增页面 Checklist

### 1. Django 后端 — 声明权限

如果新页面对应已有 model，Django 自动提供 `view_xxx` / `add_xxx` / `change_xxx` / `delete_xxx`，无需额外操作。

如果需要自定义权限（如 dashboard），在 model 的 `Meta.permissions` 中声明：

```python
# backend/apps/<app>/models.py
class MyModel(models.Model):
    class Meta:
        permissions = [
            ("view_mypage", "Can view my page"),
        ]
```

然后执行 `python manage.py makemigrations && python manage.py migrate`。

### 2. Django 后端 — 分配权限到用户组

编辑 `backend/apps/users/management/commands/setup_groups.py`，将新权限加入对应的用户组：

```python
"开发者": Permission.objects.filter(
    codename__in=[
        # ...现有的
        "view_mypage",  # ← 新增
    ]
),
```

然后执行 `python manage.py setup_groups`。

### 3. 前端 — 注册导航项

编辑 `frontend/app/composables/useNavigation.ts`，在 `navItems` 数组中添加条目：

```ts
{
  label: '新页面',
  icon: 'i-heroicons-xxx',
  to: '/app/new-page',
  permission: '<app_label>.view_<model_name>',  // 格式: app_label.codename
}
```

`permission` 字段的值必须与 `/api/auth/me/` 返回的 permissions 列表中的格式一致（`app_label.codename`）。

侧边栏 `filteredNavItems` 会自动过滤掉用户没有权限的条目。

### 4. 前端 — 注册路由守卫

编辑 `frontend/app/middleware/auth.global.ts`，在 `routePermissions` 中添加映射：

```ts
const routePermissions: Record<string, string> = {
  // ...现有的
  '/app/new-page': '<app_label>.view_<model_name>',
}
```

路由匹配规则：前缀匹配，`/app/new-page` 同时覆盖 `/app/new-page/xxx` 子路由。

### 5. 无权限页面不需要配置 permission

如果某个页面不需要权限控制（所有登录用户都可见），在 `navItems` 中不设置 `permission` 字段，在 `routePermissions` 中不添加映射即可。

## 当前权限映射表

| 路由 | Django Permission | 说明 |
|------|------------------|------|
| `/app/dashboard` | `issues.view_dashboard` | 自定义权限 |
| `/app/issues/**` | `issues.view_issue` | model 默认权限 |
| `/app/projects/**` | `projects.view_project` | model 默认权限 |
| `/app/repos/**` | `repos.view_repo` | model 默认权限 |
| `/app/ai-insights` | 无（所有登录用户可见） | 未关联 model |

## 关键文件

| 文件 | 职责 |
|------|------|
| `frontend/app/composables/useAuth.ts` | `can(permission)` 权限判断 |
| `frontend/app/composables/useNavigation.ts` | 导航项定义 + `filteredNavItems` 过滤 |
| `frontend/app/middleware/auth.global.ts` | 路由守卫 + `routePermissions` 映射 |
| `frontend/app/pages/app/forbidden.vue` | 403 无权限页面 |
| `backend/apps/users/serializers.py` | `MeSerializer` 返回用户权限列表 |
| `backend/apps/users/management/commands/setup_groups.py` | 用户组权限分配 |
