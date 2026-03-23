# Registration, User Management & Profile Design

## Overview

Add self-service registration with admin approval, an admin user management module, and a personal profile page to DevTrakr. Includes 20 built-in SVG geek-themed avatars.

## Pages

| Route | Layout | Auth Required | Permission |
|-------|--------|--------------|------------|
| `/register` | `auth` | No | None |
| `/app/users` | `default` | Yes | `users.view_user` |
| `/app/users/[id]` | `default` | Yes | `users.change_user` |
| `/app/profile` | `default` | Yes | None (any logged-in user) |

## 1. Registration Page (`/register`)

### Frontend

- Reuses `auth` layout (gradient background + centered card), same style as login page
- Fields:
  - Username (required)
  - Password (required)
  - Confirm password (required)
  - Nickname (label: "昵称", optional)
  - Email (optional, hint: "用于接收通知")
  - Avatar picker: grid of 20 SVG avatars, click to select, random default if not selected
- On success: redirect to `/` (login page) with a success toast: "注册成功，请等待管理员审批后登录"
- Login page (`/index.vue`) adds a "还没有账号？去注册" link to `/register`

### Backend

- New endpoint: `POST /api/auth/register/`
- No authentication required (`AllowAny`)
- Request body: `{ username, password, password_confirm, name?, email?, avatar? }`
- Validation:
  - `username` unique check
  - `password` matches `password_confirm`
  - Django password validators applied
- Creates user with `is_active = False`
- If `avatar` not provided, randomly assigns one from the 20 built-in avatar identifiers
- Returns `201` with `{ id, username, name, email, avatar }`
- New serializer: `RegisterSerializer`

## 2. User List Page (`/app/users`)

### Frontend

- UTable layout consistent with issues list page
- Columns: Username (link to detail), Nickname, Email, Status, Groups, Registration date
- Status display:
  - `is_active = True` → green badge "已激活"
  - `is_active = False` → amber badge "待审批", row highlighted with amber background
- Requires `users.view_user` permission
- Added to `PAGE_PERMS.SEED_ROUTES` with label "用户管理", icon `i-heroicons-users`
- Added to `PAGE_PERMS.SEED_GROUPS` → "管理员" group gets `users` app permissions

### Backend

- Expand `UserListView` to return additional fields: `is_active`, `date_joined`, `groups`
- New serializer: `AdminUserSerializer` with fields: `id, username, name, email, avatar, github_id, is_active, date_joined, groups`
- Keep existing `UserSerializer` for non-admin contexts
- Add pagination support

## 3. User Detail Page (`/app/users/[id]`)

### Frontend

- Top section: avatar display, username, status badge, activate/deactivate button
- Form section: editable fields for nickname, email, group assignment
- Activate button: toggles `is_active`, prominent placement
- Group assignment: display current groups as tags, dropdown to add groups
- Requires `users.change_user` permission
- Save button PATCHes user data

### Backend

- Upgrade `UserDetailView` from `RetrieveAPIView` to `RetrieveUpdateAPIView`
- Uses `AdminUserSerializer` for reads
- New `AdminUserUpdateSerializer` for writes: allows updating `name, email, avatar, is_active, groups`
- `groups` field accepts list of group names, resolves to Group objects
- Permission: `users.change_user` (enforced by `FullDjangoModelPermissions`)

## 4. Profile Page (`/app/profile`)

### Frontend

- Accessed via AppHeader user dropdown menu → "个人资料"
- Sections:
  1. **Avatar & basic info**: avatar display with change option (avatar picker grid), username (read-only), group display (read-only)
  2. **Editable fields**: nickname, email (hint: "用于接收通知")
  3. **Change password**: current password, new password, confirm new password
  4. **Personal settings**: mirrors current `useUserSettings` options
     - Sidebar auto-collapse (toggle)
     - Issues default view mode (kanban/table select)
     - Project default view mode (kanban/table select)
     - Theme (light/dark/auto select)
- Single "保存修改" button saves all changes

### Backend

- Uses existing `PATCH /api/auth/me/` endpoint (MeView)
- Extend `MeSerializer` to support writing: `name, email, avatar, settings`
- New endpoint: `POST /api/auth/me/change-password/`
  - Request: `{ current_password, new_password, new_password_confirm }`
  - Validates current password
  - Applies Django password validators to new password
  - Returns `200` on success

## 5. Avatar System

### Storage

- 20 SVG files in `frontend/app/assets/images/avatars/`
- Naming: `{identifier}.svg` (e.g., `terminal-hacker.svg`, `bug-monster.svg`)
- Avatar identifiers list:
  1. `terminal-hacker` — 终端黑客
  2. `robot` — 机器人
  3. `bug-monster` — Bug 怪兽
  4. `code-cat` — 代码猫
  5. `cpu-brain` — CPU 大脑
  6. `wifi-wizard` — WiFi 巫师
  7. `binary-ghost` — 二进制幽灵
  8. `docker-whale` — Docker 鲸
  9. `git-octopus` — Git 章鱼
  10. `code-ninja` — 代码忍者
  11. `keyboard-warrior` — 键盘战士
  12. `stack-overflow` — 栈溢出
  13. `404-alien` — 404 外星人
  14. `firewall-guard` — 防火墙守卫
  15. `one-up-mushroom` — 1-UP 蘑菇
  16. `recursion-owl` — 递归猫头鹰
  17. `rubber-duck` — 小黄鸭调试
  18. `infinite-coffee` — 无限咖啡
  19. `sudo-penguin` — Sudo 企鹅
  20. `null-pointer` — 空指针

### User model change

- The existing `avatar` field (URLField) stores the avatar identifier string (e.g., `terminal-hacker`) instead of a URL
- Frontend maps identifier → imported SVG asset for rendering
- A shared composable `useAvatars()` provides the avatar list and a helper to resolve identifier → component/URL

### Avatar picker component

- Reusable `AvatarPicker.vue` component used in both registration and profile pages
- Grid layout showing all 20 avatars
- Click to select, selected avatar gets a highlight ring
- Shows current selection prominently above the grid

## 6. Permission & Navigation Configuration

### PAGE_PERMS changes in `settings.py`

```python
SEED_ROUTES += [
    {"path": "/app/users", "label": "用户管理", "icon": "i-heroicons-users",
     "permission": "users.view_user", "sort_order": 5},
]
SEED_GROUPS["管理员"]["apps"] += ["users"]  # adds users app perms to admin group
```

### Auth middleware

- `/register` added to allowed unauthenticated paths (alongside `/` and `/login`)
- `/app/profile` needs no special permission mapping — any authenticated user can access

## 7. Data Flow

### Registration flow

```
User fills form → POST /api/auth/register/
  → Validate fields, check username unique
  → Create User(is_active=False, avatar=selected_or_random)
  → Return 201
  → Frontend redirects to / with success message
```

### Admin approval flow

```
Admin opens /app/users → sees pending users (is_active=False, amber highlight)
  → Clicks user → /app/users/[id]
  → Clicks "激活用户" → PATCH /api/users/[id]/ {is_active: true}
  → User can now log in
```

### Profile update flow

```
User clicks avatar dropdown → "个人资料" → /app/profile
  → Edits fields → "保存修改"
  → PATCH /api/auth/me/ {name, email, avatar, settings}
  → Password change: POST /api/auth/me/change-password/
```

## 8. Files to Create

| File | Purpose |
|------|---------|
| `frontend/app/pages/register.vue` | Registration page |
| `frontend/app/pages/app/users/index.vue` | User list (admin) |
| `frontend/app/pages/app/users/[id].vue` | User detail (admin) |
| `frontend/app/pages/app/profile.vue` | Personal profile |
| `frontend/app/components/AvatarPicker.vue` | Reusable avatar grid picker |
| `frontend/app/composables/useAvatars.ts` | Avatar list & helpers |
| `frontend/app/assets/images/avatars/*.svg` | 20 SVG avatar files |
| `backend/apps/users/serializers.py` | Add RegisterSerializer, AdminUserSerializer, AdminUserUpdateSerializer |
| `backend/apps/users/views.py` | Add RegisterView, ChangePasswordView, update UserDetailView |
| `backend/apps/users/auth_urls.py` | Add register and change-password routes |

## 9. Files to Modify

| File | Change |
|------|--------|
| `frontend/app/pages/index.vue` | Add "去注册" link |
| `frontend/app/components/AppHeader.vue` | Add "个人资料" to user dropdown menu |
| `frontend/app/middleware/auth.global.ts` | Allow `/register` path without auth |
| `backend/config/settings.py` | Add `/app/users` to SEED_ROUTES, add `users` to admin group apps |
| `backend/apps/users/urls.py` | Keep existing, UserDetailView now supports PATCH |

## 10. Testing

- Backend tests:
  - `test_register.py`: successful registration, duplicate username, password mismatch, password validation, random avatar assignment
  - `test_user_admin.py`: list users, update user, activate/deactivate, group assignment (requires admin permissions)
  - `test_profile.py`: update profile, change password (wrong current password, mismatch, success)
- Frontend: manual testing of all 4 pages + avatar picker interaction
