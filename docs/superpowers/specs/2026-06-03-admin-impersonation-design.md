# 超级管理员模拟登录（Impersonation）设计

日期：2026-06-03
分支：feat/task-dispatch-review

## 目标

超级管理员（`is_superuser`）可以在「用户管理」页面以某个普通用户的身份登录（模拟登录），
完整地以该用户身份操作系统，并随时一键返回自己的管理员账号。

非目标（YAGNI）：

- 不建审计表，也不写服务器日志（用户明确不需要任何记录）。
- 不支持模拟其他超管（除超管外，其余用户均可模拟）。
- 不支持嵌套模拟（模拟会话中再发起模拟）。

## 安全模型（核心）

模拟登录会让一个账号以另一个账号的身份执行任意操作，是高风险功能。所有防护以**后端为唯一可信边界**，
前端的按钮可见性只是装饰，无法绕过后端校验。

- **唯一发起者**：仅 `request.user.is_superuser == True` 可调用模拟接口，否则 403。
- **唯一禁止的目标**：`is_superuser == True` → 拒绝（403），避免横向提权。
  - 由于发起者自己也是超管，「目标非超管」这一条天然排除了自己以及所有其他超管，无需单独的 self 校验。
  - staff / 机器人 / 普通用户等非超管账号均可模拟。
  - 实务护栏：目标 `is_active == False` 时返回 400「该用户未激活」——因为 simplejwt 鉴权会拒绝停用用户，
    签发的 token 调用任何接口都会立即 401，与其给管理员一个不可用的会话，不如直接报错。此为功能性兜底，不属于策略限制。
- **禁止嵌套模拟**：若当前请求 token 已携带 `impersonated_by` 声明，拒绝再次发起（403）。
  （理论上模拟态用户必为非超管，已被 `is_superuser` 拦截；此处为纵深防御，显式再挡一层。）
- **不可伪造**：`impersonated_by` 声明写在已签名的 JWT 中，客户端无法篡改。
- **短期模拟会话**：模拟签发的 refresh token 生命周期缩短为 **30 分钟**（access 仍沿用默认 2h）。
  即使模拟凭证泄露，可刷新窗口也仅 30 分钟，远小于普通会话的 7 天。

## 返回机制：前端暂存原 token（方案 A）

- `impersonated_by` 声明记录发起者（actor）身份，用于前端横幅显示与「返回管理员」。
- 模拟前，前端把管理员当前的 `access_token` / `refresh_token` 暂存到 `admin_access_token` / `admin_refresh_token`。
- 「返回管理员」时恢复这两个 key，清除暂存，重新拉取 `me`。
- 管理员原会话完整保留，无需额外的后端 stop 接口。

## 后端

### 1. 模拟登录接口 `POST /api/auth/impersonate/`

文件：`backend/apps/users/views.py`（新增 `ImpersonateView`），在 `backend/apps/users/auth_urls.py` 注册。

- `permission_classes = [IsAuthenticated]`，并在 `post` 内显式校验 `request.user.is_superuser`。
- 请求体：`{ "user_id": <int> }`。
- 校验顺序与返回：
  - 当前 token 已是模拟态（`request.auth` 含 `impersonated_by`）→ 403「不可嵌套模拟」。
  - 非超管 → 403「无权模拟登录」。
  - `user_id` 缺失/非法 → 400。
  - 目标不存在 → 404。
  - 目标 `is_superuser` → 403「不能模拟管理员账号」（同时覆盖了「模拟自己」的情况）。
  - 目标 `is_active == False` → 400「该用户未激活」（功能性兜底，见安全模型）。
- 签发 token：

  ```python
  from datetime import timedelta
  from rest_framework_simplejwt.tokens import RefreshToken

  refresh = RefreshToken.for_user(target)
  refresh.set_exp(lifetime=timedelta(minutes=30))   # 模拟会话短期
  refresh["impersonated_by"] = actor.id
  refresh["impersonated_by_username"] = actor.username
  access = refresh.access_token
  access["impersonated_by"] = actor.id
  access["impersonated_by_username"] = actor.username
  return Response({"access": str(access), "refresh": str(refresh)})
  ```

- 声明传递：simplejwt 的 `/api/auth/refresh/` 会把 refresh token 中的非保留声明复制到新 access token，
  因此 `impersonated_by` 在刷新后仍然保留，模拟态不会因刷新而丢失。

### 2. `/api/auth/me/` 暴露模拟态

文件：`backend/apps/users/views.py` 的 `MeView`。

- 重写 `retrieve`（或在响应里追加字段），从 `request.auth` 读取 `impersonated_by` / `impersonated_by_username`，
  追加到响应：`impersonated_by`（int | null）、`impersonated_by_username`（str | null）。
- 该字段来自 token，不落库、不改 User 模型。
- 作用：页面刷新后前端仍能据此渲染模拟横幅。

## 前端

### 3. `frontend/app/composables/useAuth.ts`

- 扩展 `AuthUser` 接口：新增 `username: string`、`impersonated_by: number | null`、`impersonated_by_username: string | null`。
- 新增 `impersonate(userId)`：
  1. `POST /api/auth/impersonate/ { user_id }`。
  2. 把当前 `access_token`/`refresh_token` 暂存到 `admin_access_token`/`admin_refresh_token`。
  3. `setTokens(res.access, res.refresh)`。
  4. `await fetchMe()`，`navigateTo('/app')`（或首页）。
- 新增 `stopImpersonation()`：
  1. 从 `admin_*` 恢复 `access_token`/`refresh_token`，删除暂存 key。
  2. `await fetchMe()`，`navigateTo('/app/users')`。
  3. 兜底：若无暂存 token（异常情况），调用 `logout()`。
- `impersonate` / `stopImpersonation` 一并 export。

### 4. 模拟横幅组件

文件：`frontend/app/components/ImpersonationBanner.vue`，在 `frontend/app/layouts/default.vue` 的 slot 上方渲染。

- 当 `auth.user?.impersonated_by` 存在时显示一条醒目横幅：
  「⚠ 您正在以 {{ user.name || user.username }} 的身份操作 · [返回管理员]」。
- 「返回管理员」按钮调用 `stopImpersonation()`。

### 5. 用户管理页操作入口

文件：`frontend/app/pages/app/users/index.vue`。

- 在 `UTable` 增加「操作」列，每行一个「模拟登录」`UButton`。
- 可见条件：`auth.user?.is_superuser && !row.is_superuser`。
  （`!row.is_superuser` 已天然排除发起者自己与其他超管，故无需额外的 self 判断。）
- 点击 → 确认（`UModal` 或 `confirm`）→ `impersonate(row.id)`。
- 失败时用 `useToast` 提示后端返回的错误信息（如目标已停用时的 400）。
  - 需确认 `AdminUserSerializer` 行数据是否包含 `is_superuser`；缺失则在该序列化器补该字段，
    以便前端正确判断按钮可见性。

## 错误处理

- 后端各分支返回明确的中文 `detail` 与对应 HTTP 状态码。
- 前端 `impersonate` 捕获异常，`useToast().add({ title: 错误信息, color: 'error' })`。

## 测试（后端 pytest，`backend/tests/`）

新增 `tests/test_impersonation.py`：

- 超管模拟普通用户 → 200，返回 access/refresh，且 access 解码后含 `impersonated_by == actor.id`。
- 超管可模拟 staff（非超管）用户 → 200。
- 超管不能模拟另一个超管 → 403（同一断言覆盖「模拟自己」）。
- 超管不能模拟已停用用户 → 400。
- 非超管发起 → 403。
- 模拟态 token（带 `impersonated_by`）再次发起 → 403（禁止嵌套）。
- 用模拟 token 调 `/api/auth/me/` → 响应含 `impersonated_by` / `impersonated_by_username`。
- 模拟 refresh token 过期时间约为 30 分钟（断言 exp 与 iat 间隔 ≤ 普通 refresh）。

前端类型检查：`npx nuxi typecheck` 通过。

## 受影响文件清单

- `backend/apps/users/views.py` — 新增 `ImpersonateView`，`MeView` 暴露模拟态。
- `backend/apps/users/auth_urls.py` — 注册 `impersonate/`。
- `backend/apps/users/serializers.py` — 必要时给 `AdminUserSerializer` 补 `is_superuser`（前端判断按钮可见用）。
- `backend/tests/test_impersonation.py` — 新增测试。
- `frontend/app/composables/useAuth.ts` — `impersonate` / `stopImpersonation` + 接口字段。
- `frontend/app/components/ImpersonationBanner.vue` — 新增横幅。
- `frontend/app/layouts/default.vue` — 挂载横幅。
- `frontend/app/pages/app/users/index.vue` — 模拟登录按钮。
