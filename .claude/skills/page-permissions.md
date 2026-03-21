---
name: page-permissions
description: 新增页面时，配置 Django 权限与前端路由守卫、侧边栏的联动
---

# 前端页面权限管理

本项目通过 `django-page-perms` 包控制前端页面的可见性和可访问性。
包的配置格式、API 端点、前端集成模式详见 `packages/django-page-perms/README.md`。

## 权限流转架构

```
Django Model Meta.permissions
        ↓
PAGE_PERMS["SEED_ROUTES"] + PAGE_PERMS["SEED_GROUPS"] (backend/config/settings.py)
        ↓
python manage.py sync_page_perms
        ↓
/api/auth/me/ 返回用户 permissions 列表
        ↓
前端 useAuth().can() 判断权限
        ↓
┌─ useNavigation: filteredNavItems 控制侧边栏可见性
└─ auth.global.ts: routePermissions 控制路由可访问性
```

## 新增页面 Checklist

### 1. 声明权限

已有 model 自动提供 `view_xxx` / `add_xxx` / `change_xxx` / `delete_xxx`，无需额外操作。
自定义权限在 model 的 `Meta.permissions` 中声明，然后 `makemigrations && migrate`。

### 2. 配置路由和用户组

编辑 `backend/config/settings.py` 中的 `PAGE_PERMS`：

- `SEED_ROUTES` 添加路由条目
- `SEED_GROUPS` 将权限分配到用户组

配置格式详见 `packages/django-page-perms/README.md` → Configuration。
然后执行 `python manage.py sync_page_perms`。

### 3. 前端 — 注册导航项

编辑 `frontend/app/composables/useNavigation.ts`，在 `navItems` 中添加条目。
`permission` 格式为 `app_label.codename`，与 `/api/auth/me/` 返回值一致。
`filteredNavItems` 会自动过滤掉用户没有权限的条目。

### 4. 前端 — 注册路由守卫

编辑 `frontend/app/middleware/auth.global.ts`，在 `routePermissions` 中添加映射。
路由匹配规则：前缀匹配，`/app/new-page` 同时覆盖 `/app/new-page/xxx` 子路由。

### 5. 无权限页面

不设置 `permission` 字段，不添加 `routePermissions` 映射即可。

## 关键文件

| 文件 | 职责 |
|------|------|
| `packages/django-page-perms/README.md` | 包文档：配置格式、API、前端集成 |
| `backend/config/settings.py` | `PAGE_PERMS` 配置（路由 + 用户组） |
| `frontend/app/composables/useAuth.ts` | `can(permission)` 权限判断 |
| `frontend/app/composables/useNavigation.ts` | 导航项定义 + `filteredNavItems` 过滤 |
| `frontend/app/middleware/auth.global.ts` | 路由守卫 + `routePermissions` 映射 |
| `frontend/app/pages/app/forbidden.vue` | 403 无权限页面 |
