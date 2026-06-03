# 超级管理员模拟登录 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让超级管理员在「用户管理」页面以任意非超管用户的身份登录，完整以其身份操作系统，并可一键返回自己的管理员账号。

**Architecture:** 后端新增 `POST /api/auth/impersonate/`，校验发起者为超管、目标非超管后，签发携带 `impersonated_by` 声明的短期 JWT；`/api/auth/me/` 从 token 暴露模拟态。前端把管理员原 token 暂存到 `admin_*` key，换入模拟 token，并在布局顶部显示横幅可一键恢复。安全以后端为唯一可信边界。

**Tech Stack:** Django REST Framework + rest_framework_simplejwt（后端）；Nuxt 4 SPA + Nuxt UI（前端）；pytest（后端测试）。

设计文档：`docs/superpowers/specs/2026-06-03-admin-impersonation-design.md`

---

## File Structure

- `backend/apps/users/serializers.py` — `AdminUserSerializer` 补 `is_superuser`（前端按钮可见用）；`MeSerializer.to_representation` 暴露模拟态。
- `backend/apps/users/views.py` — 新增 `ImpersonateView`。
- `backend/apps/users/auth_urls.py` — 注册 `impersonate/` 路由。
- `backend/tests/test_impersonation.py` — 新增后端测试。
- `frontend/app/composables/useAuth.ts` — `impersonate` / `stopImpersonation` + `AuthUser` 字段。
- `frontend/app/components/ImpersonationBanner.vue` — 新增模拟态横幅。
- `frontend/app/layouts/default.vue` — 挂载横幅。
- `frontend/app/pages/app/users/index.vue` — 每行「模拟登录」按钮。

---

## Task 1: AdminUserSerializer 暴露 is_superuser

让用户列表返回 `is_superuser`，前端据此决定是否显示「模拟登录」按钮。

**Files:**
- Modify: `backend/apps/users/serializers.py:93-101`（`AdminUserSerializer`）
- Test: `backend/tests/test_impersonation.py`

- [ ] **Step 1: 写失败的测试**

新建 `backend/tests/test_impersonation.py`：

```python
import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_list_includes_is_superuser(superuser_client):
    UserFactory(is_superuser=False)
    resp = superuser_client.get("/api/users/")
    assert resp.status_code == 200
    assert all("is_superuser" in row for row in resp.json())
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_impersonation.py::test_user_list_includes_is_superuser -v`
Expected: FAIL —— 返回行中没有 `is_superuser` 键（KeyError/assert False）。

- [ ] **Step 3: 给序列化器补字段**

`backend/apps/users/serializers.py` 中 `AdminUserSerializer.Meta.fields` 增加 `"is_superuser"`：

```python
class AdminUserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "avatar", "github_id", "is_active", "is_superuser", "date_joined", "groups"]

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_impersonation.py::test_user_list_includes_is_superuser -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/apps/users/serializers.py backend/tests/test_impersonation.py
git commit -m "feat(users): expose is_superuser in admin user list"
```

---

## Task 2: ImpersonateView 模拟登录接口

核心接口：超管签发目标用户的短期 JWT，带 `impersonated_by` 声明。

**Files:**
- Modify: `backend/apps/users/views.py`（新增 `ImpersonateView`，并补 import）
- Modify: `backend/apps/users/auth_urls.py`（注册路由）
- Test: `backend/tests/test_impersonation.py`

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_impersonation.py` 追加。注意 fixture：`superuser_client`（已认证超管）、`regular_client`（已认证普通用户）来自 `conftest.py`。

```python
from rest_framework_simplejwt.tokens import AccessToken


def test_superuser_can_impersonate_regular_user(superuser_client):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 200
    body = resp.json()
    assert "access" in body and "refresh" in body
    token = AccessToken(body["access"])
    assert token["user_id"] == target.id
    assert token["impersonated_by"] is not None


def test_can_impersonate_staff_non_superuser(superuser_client):
    target = UserFactory(is_superuser=False, is_staff=True, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 200


def test_cannot_impersonate_superuser(superuser_client):
    target = UserFactory(is_superuser=True, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 403


def test_cannot_impersonate_inactive_user(superuser_client):
    target = UserFactory(is_superuser=False, is_active=False)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 400


def test_target_not_found_returns_404(superuser_client):
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": 99999999})
    assert resp.status_code == 404


def test_regular_user_cannot_impersonate(regular_client):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = regular_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 403


def test_nested_impersonation_rejected(superuser_client, api_client):
    target = UserFactory(is_superuser=False, is_active=True)
    other = UserFactory(is_superuser=False, is_active=True)
    # 先拿到一个模拟 token
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    access = resp.json()["access"]
    # 用模拟 token 再次发起模拟 → 应被拒
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp2 = api_client.post("/api/auth/impersonate/", {"user_id": other.id})
    assert resp2.status_code == 403


def test_impersonation_refresh_token_is_short_lived(superuser_client):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken(resp.json()["refresh"])
    # 30 分钟模拟会话：exp - iat 应远小于默认 7 天（604800s），留足余量断言 ≤ 3600s
    assert refresh["exp"] - refresh["iat"] <= 3600
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_impersonation.py -v -k "impersonate or nested or short_lived or not_found"`
Expected: FAIL —— 路由不存在（404 对所有用例），因为 `ImpersonateView` 尚未实现。

- [ ] **Step 3: 实现 ImpersonateView**

`backend/apps/users/views.py` 顶部补 import：

```python
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
```

在文件末尾新增视图：

```python
class ImpersonateView(APIView):
    """超管模拟登录：签发目标用户的短期 JWT，带 impersonated_by 声明。
    安全边界完全由本接口校验，前端按钮可见性仅为装饰。"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        actor = request.user
        # 纵深防御：禁止在模拟态中再次发起模拟
        if request.auth is not None and request.auth.get("impersonated_by"):
            return Response({"detail": "不可嵌套模拟"}, status=status.HTTP_403_FORBIDDEN)
        if not actor.is_superuser:
            return Response({"detail": "无权模拟登录"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "缺少 user_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 唯一禁止的目标：超管（同时覆盖了模拟自己的情况）
        if target.is_superuser:
            return Response({"detail": "不能模拟管理员账号"}, status=status.HTTP_403_FORBIDDEN)
        # 功能性兜底：停用用户的 token 鉴权必失败，直接报错
        if not target.is_active:
            return Response({"detail": "该用户未激活"}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(target)
        refresh.set_exp(lifetime=timedelta(minutes=30))  # 模拟会话短期
        refresh["impersonated_by"] = actor.id
        refresh["impersonated_by_username"] = actor.username
        access = refresh.access_token
        access["impersonated_by"] = actor.id
        access["impersonated_by_username"] = actor.username
        return Response({"access": str(access), "refresh": str(refresh)})
```

- [ ] **Step 4: 注册路由**

`backend/apps/users/auth_urls.py`：import 增加 `ImpersonateView`，urlpatterns 增加一行。

```python
from .views import MeView, RegisterView, ChangePasswordView, AdminSessionView, ImpersonateView
```

```python
    path("impersonate/", ImpersonateView.as_view(), name="auth-impersonate"),
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_impersonation.py -v`
Expected: PASS（含 Task 1 的用例）。

- [ ] **Step 6: 提交**

```bash
git add backend/apps/users/views.py backend/apps/users/auth_urls.py backend/tests/test_impersonation.py
git commit -m "feat(auth): super-admin impersonation endpoint with short-lived token"
```

---

## Task 3: /api/auth/me/ 暴露模拟态

前端刷新后仍能据此渲染横幅。

**Files:**
- Modify: `backend/apps/users/serializers.py`（`MeSerializer.to_representation`，约 44-52 行）
- Test: `backend/tests/test_impersonation.py`

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_impersonation.py` 追加：

```python
def test_me_reflects_impersonation(superuser_client, api_client, site_settings):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    access = resp.json()["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = api_client.get("/api/auth/me/")
    assert me.status_code == 200
    body = me.json()
    assert body["id"] == target.id
    assert body["impersonated_by"] is not None
    assert body["impersonated_by_username"]


def test_me_without_impersonation_is_null(superuser_client):
    me = superuser_client.get("/api/auth/me/")
    # force_authenticate 无 token，字段应为 None 且不报错
    assert me.json()["impersonated_by"] is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_impersonation.py -v -k "me_reflects or me_without"`
Expected: FAIL —— 响应中无 `impersonated_by` 键（KeyError）。

- [ ] **Step 3: 在 MeSerializer.to_representation 注入字段**

`backend/apps/users/serializers.py` 中 `MeSerializer.to_representation`（现有方法，设置 `default_project` 的那个）末尾、`return data` 之前追加：

```python
    def to_representation(self, instance):
        data = super().to_representation(instance)
        from apps.projects.utils import get_effective_default_project
        proj = get_effective_default_project(instance)
        data["default_project"] = (
            {"id": str(proj.id), "name": proj.name} if proj else None
        )
        # 模拟态：从请求 token 读取，不落库
        request = self.context.get("request")
        token = getattr(request, "auth", None) if request else None
        data["impersonated_by"] = token.get("impersonated_by") if token is not None else None
        data["impersonated_by_username"] = (
            token.get("impersonated_by_username") if token is not None else None
        )
        return data
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_impersonation.py -v`
Expected: PASS（全部用例）。

- [ ] **Step 5: 提交**

```bash
git add backend/apps/users/serializers.py backend/tests/test_impersonation.py
git commit -m "feat(auth): expose impersonation state in /auth/me/"
```

---

## Task 4: 前端 useAuth — impersonate / stopImpersonation

**Files:**
- Modify: `frontend/app/composables/useAuth.ts`

- [ ] **Step 1: 扩展 AuthUser 接口**

在 `interface AuthUser` 中增加三个字段：

```typescript
interface AuthUser {
  id: string
  username: string
  name: string
  email: string
  avatar: string
  groups: string[]
  permissions: string[]
  settings: Record<string, any>
  is_superuser: boolean
  default_project: { id: string; name: string } | null
  impersonated_by: number | null
  impersonated_by_username: string | null
}
```

- [ ] **Step 2: 实现 impersonate / stopImpersonation 并 export**

在 `useAuth()` 内、`logout` 之后新增两个函数，并加入 return。`setTokens` 来自 `useApi()`，需在解构中补上：

```typescript
  const { api, clearTokens, setTokens } = useApi()
```

```typescript
  // 模拟登录：暂存管理员原 token，换入目标用户 token
  async function impersonate(userId: number | string) {
    const res = await api<{ access: string; refresh: string }>('/api/auth/impersonate/', {
      method: 'POST',
      body: { user_id: userId },
    })
    localStorage.setItem('admin_access_token', localStorage.getItem('access_token') || '')
    localStorage.setItem('admin_refresh_token', localStorage.getItem('refresh_token') || '')
    setTokens(res.access, res.refresh)
    await fetchMe()
    await loadSettings(user.value?.settings)
    navigateTo('/app')
  }

  // 返回管理员：恢复暂存的原 token
  async function stopImpersonation() {
    const adminAccess = localStorage.getItem('admin_access_token')
    const adminRefresh = localStorage.getItem('admin_refresh_token')
    if (!adminAccess || !adminRefresh) {
      // 兜底：暂存丢失则直接登出
      logout()
      return
    }
    setTokens(adminAccess, adminRefresh)
    localStorage.removeItem('admin_access_token')
    localStorage.removeItem('admin_refresh_token')
    await fetchMe()
    navigateTo('/app/users')
  }

  return { user, fetchMe, can, hasGroup, logout, impersonate, stopImpersonation }
```

注意：`loadSettings` 已在 `useAuth` 顶部解构；若 `loadSettings` 非 async，去掉其 `await` 即可（按现有 `fetchMe` 用法保持一致——现有代码为 `loadSettings(user.value?.settings)`，不带 await，请同样不带 await）。修正 `impersonate` 中该行为：`loadSettings(user.value?.settings)`。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx nuxi typecheck`
Expected: 通过（无新增类型错误）。

- [ ] **Step 4: 提交**

```bash
git add frontend/app/composables/useAuth.ts
git commit -m "feat(frontend): impersonate/stopImpersonation in useAuth"
```

---

## Task 5: 模拟态横幅组件

**Files:**
- Create: `frontend/app/components/ImpersonationBanner.vue`
- Modify: `frontend/app/layouts/default.vue`

- [ ] **Step 1: 创建横幅组件**

`frontend/app/components/ImpersonationBanner.vue`：

```vue
<template>
  <div
    v-if="user?.impersonated_by"
    class="flex items-center justify-center gap-3 px-4 py-2 bg-amber-500 text-white text-sm font-medium"
    role="alert"
  >
    <UIcon name="i-heroicons-exclamation-triangle" class="w-4 h-4" />
    <span>您正在以「{{ user.name || user.username }}」的身份操作</span>
    <UButton size="xs" color="neutral" variant="solid" :loading="returning" @click="onReturn">
      返回管理员
    </UButton>
  </div>
</template>

<script setup lang="ts">
const { user, stopImpersonation } = useAuth()
const returning = ref(false)

async function onReturn() {
  returning.value = true
  try {
    await stopImpersonation()
  } finally {
    returning.value = false
  }
}
</script>
```

- [ ] **Step 2: 挂载到布局顶部**

`frontend/app/layouts/default.vue` 模板，在 `<SystemAlertBanner />` 上方加一行：

```vue
  <div class="flex flex-col h-screen">
    <ImpersonationBanner />
    <SystemAlertBanner />
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx nuxi typecheck`
Expected: 通过。

- [ ] **Step 4: 提交**

```bash
git add frontend/app/components/ImpersonationBanner.vue frontend/app/layouts/default.vue
git commit -m "feat(frontend): impersonation banner with return button"
```

---

## Task 6: 用户管理页「模拟登录」按钮

**Files:**
- Modify: `frontend/app/pages/app/users/index.vue`

- [ ] **Step 1: 在表格增加操作列**

在 `<UTable>` 内、`#date_joined-cell` 模板之后追加一个操作列模板（列定义见 Step 2）：

```vue
        <template #actions-cell="{ row }">
          <UButton
            v-if="auth.user?.is_superuser && !row.original.is_superuser"
            icon="i-heroicons-user-circle"
            size="xs"
            color="neutral"
            variant="soft"
            @click="onImpersonate(row.original)"
          >
            模拟登录
          </UButton>
        </template>
```

- [ ] **Step 2: 在 `<script setup>` 中接线**

确认/新增以下内容（沿用页面现有 `columns`、`auth` 写法）：
- 引入 auth 与 toast（若页面尚未有）：

```typescript
const auth = useAuth()
const toast = useToast()
```

- 在 `columns` 数组末尾追加操作列：

```typescript
  { accessorKey: 'actions', header: '操作' },
```

- 新增确认 + 调用逻辑：

```typescript
async function onImpersonate(row: { id: number | string; name?: string; username: string }) {
  const label = row.name || row.username
  if (!window.confirm(`确定以「${label}」的身份登录？你可以随时点击顶部横幅返回管理员。`)) return
  try {
    await auth.impersonate(row.id)
  } catch (e: any) {
    toast.add({ title: e?.data?.detail || '模拟登录失败', color: 'error' })
  }
}
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx nuxi typecheck`
Expected: 通过。

- [ ] **Step 4: 提交**

```bash
git add frontend/app/pages/app/users/index.vue
git commit -m "feat(frontend): impersonate button on user management page"
```

---

## Task 7: 全量验证

- [ ] **Step 1: 后端全量测试**

Run: `cd backend && uv run pytest tests/test_impersonation.py -v`
Expected: 全部 PASS。

- [ ] **Step 2: 后端回归（确认未破坏既有用户/认证测试）**

Run: `cd backend && uv run pytest tests/ -q -k "user or auth or me"`
Expected: 全部 PASS。

- [ ] **Step 3: 前端类型检查**

Run: `cd frontend && npx nuxi typecheck`
Expected: 通过。

- [ ] **Step 4: 手动冒烟（可选，需本地起服务）**

以超管登录 → 用户管理页点某普通用户「模拟登录」→ 顶部出现黄色横幅，页面以该用户身份显示 → 点「返回管理员」→ 恢复超管身份。

---

## Self-Review 结论

- **Spec 覆盖**：唯一禁止目标=超管（Task 2 `is_superuser` 校验）；停用兜底（Task 2）；禁止嵌套（Task 2）；短期 token（Task 2 `set_exp` + 测试）；me 暴露模拟态（Task 3）；前端暂存返回（Task 4）；横幅（Task 5）；按钮可见条件 `!row.is_superuser`（Task 6）。全部有对应任务。
- **占位符**：无。
- **类型一致性**：`impersonate(userId)` / `stopImpersonation()` 在 useAuth、横幅、用户页三处签名一致；`impersonated_by` 字段在后端响应与前端接口一致。
