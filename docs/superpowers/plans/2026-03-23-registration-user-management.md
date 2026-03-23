# Registration, User Management & Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add self-service registration (with admin approval), admin user management, personal profile page, and 20 built-in geek-themed SVG avatars to DevTrakr.

**Architecture:** Backend adds registration endpoint (AllowAny), upgrades user list/detail views with FullDjangoModelPermissions, adds change-password endpoint. Frontend adds 4 new pages (register, user list, user detail, profile) plus a reusable avatar picker component. Avatar identifiers stored in User.avatar CharField, mapped to SVG assets on frontend.

**Tech Stack:** Django REST Framework, Nuxt 4 (Vue 3), Nuxt UI, simplejwt, pytest + factory-boy

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `backend/apps/users/avatar_choices.py` | List of 20 avatar identifiers (single source of truth) |
| `backend/tests/test_register.py` | Registration endpoint tests |
| `backend/tests/test_user_admin.py` | Admin user list/detail/update tests |
| `backend/tests/test_profile.py` | Profile update + change password tests |
| `frontend/app/assets/images/avatars/*.svg` | 20 SVG avatar files |
| `frontend/app/composables/useAvatars.ts` | Avatar list, resolver, random picker |
| `frontend/app/components/AvatarPicker.vue` | Reusable avatar grid picker |
| `frontend/app/pages/register.vue` | Registration page |
| `frontend/app/pages/app/users/index.vue` | Admin user list page |
| `frontend/app/pages/app/users/[id].vue` | Admin user detail page |
| `frontend/app/pages/app/profile.vue` | Personal profile page |

### Modified Files

| File | Change |
|------|--------|
| `backend/apps/users/models.py` | `avatar` URLField → CharField(max_length=50) |
| `backend/apps/users/serializers.py` | Add RegisterSerializer, AdminUserSerializer, AdminUserUpdateSerializer, ChangePasswordSerializer |
| `backend/apps/users/views.py` | Add RegisterView, ChangePasswordView; upgrade UserListView/UserDetailView permissions |
| `backend/apps/users/auth_urls.py` | Add register/ and me/change-password/ routes |
| `backend/config/settings.py` | Add /app/users to SEED_ROUTES, add "users" to admin group apps |
| `backend/tests/conftest.py` | Add "users" to auth_client admin group apps |
| `frontend/app/pages/index.vue` | Add "去注册" link |
| `frontend/app/components/AppHeader.vue` | Add "个人资料" to user dropdown |
| `frontend/app/middleware/auth.global.ts` | Allow /register without auth |

---

### Task 1: Avatar model field migration

**Files:**
- Modify: `backend/apps/users/models.py:8`

- [ ] **Step 1: Change avatar field type**

In `backend/apps/users/models.py`, change line 8:

```python
# Before:
avatar = models.URLField(blank=True, verbose_name="头像")

# After:
avatar = models.CharField(max_length=50, blank=True, verbose_name="头像")
```

- [ ] **Step 2: Generate and apply migration**

```bash
cd backend
uv run python manage.py makemigrations users
uv run python manage.py migrate
```

Expected: Migration created and applied successfully.

- [ ] **Step 3: Commit**

```bash
git add backend/apps/users/models.py backend/apps/users/migrations/
git commit -m "refactor(users): change avatar field from URLField to CharField for identifier storage"
```

---

### Task 2: Avatar identifiers + backend registration serializer & view

**Files:**
- Create: `backend/apps/users/avatar_choices.py`
- Modify: `backend/apps/users/serializers.py`
- Modify: `backend/apps/users/views.py`
- Modify: `backend/apps/users/auth_urls.py`

- [ ] **Step 1: Create avatar choices module**

Create `backend/apps/users/avatar_choices.py`:

```python
import random

AVATAR_CHOICES = [
    "terminal-hacker",
    "robot",
    "bug-monster",
    "code-cat",
    "cpu-brain",
    "wifi-wizard",
    "binary-ghost",
    "docker-whale",
    "git-octopus",
    "code-ninja",
    "keyboard-warrior",
    "stack-overflow",
    "404-alien",
    "firewall-guard",
    "one-up-mushroom",
    "recursion-owl",
    "rubber-duck",
    "infinite-coffee",
    "sudo-penguin",
    "null-pointer",
]


def random_avatar():
    return random.choice(AVATAR_CHOICES)
```

- [ ] **Step 2: Add RegisterSerializer to serializers.py**

Append to `backend/apps/users/serializers.py`:

```python
from django.contrib.auth.password_validation import validate_password
from .avatar_choices import AVATAR_CHOICES, random_avatar


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    name = serializers.CharField(max_length=50, required=False, default="")
    email = serializers.EmailField(required=False, default="")
    avatar = serializers.CharField(max_length=50, required=False, default="")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该用户名已被注册")
        return value

    def validate_avatar(self, value):
        if value and value not in AVATAR_CHOICES:
            raise serializers.ValidationError("无效的头像选择")
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "两次密码输入不一致"})
        validate_password(data["password"])
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        avatar = validated_data.pop("avatar", "") or random_avatar()
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            name=validated_data.get("name", ""),
            email=validated_data.get("email", ""),
            avatar=avatar,
            is_active=False,
        )
        return user
```

- [ ] **Step 3: Add RegisterView to views.py**

Add to `backend/apps/users/views.py`:

```python
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer, UserSerializer

class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )
```

Also add the `Response` import at top: `from rest_framework.response import Response`

- [ ] **Step 4: Add register URL to auth_urls.py**

Modify `backend/apps/users/auth_urls.py`:

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView, RegisterView

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token-login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("register/", RegisterView.as_view(), name="auth-register"),
]
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/users/avatar_choices.py backend/apps/users/serializers.py backend/apps/users/views.py backend/apps/users/auth_urls.py
git commit -m "feat(auth): add registration endpoint with avatar support"
```

---

### Task 3: Registration tests

**Files:**
- Create: `backend/tests/test_register.py`

- [ ] **Step 1: Write registration tests**

Create `backend/tests/test_register.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from apps.users.avatar_choices import AVATAR_CHOICES

pytestmark = pytest.mark.django_db
User = get_user_model()


class TestRegister:
    URL = "/api/auth/register/"

    def test_register_success(self, api_client):
        response = api_client.post(self.URL, {
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "name": "新用户",
            "email": "new@example.com",
            "avatar": "robot",
        })
        assert response.status_code == 201
        assert response.data["username"] == "newuser"
        assert response.data["name"] == "新用户"
        user = User.objects.get(username="newuser")
        assert user.is_active is False
        assert user.avatar == "robot"

    def test_register_random_avatar(self, api_client):
        response = api_client.post(self.URL, {
            "username": "randomavatar",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert response.status_code == 201
        user = User.objects.get(username="randomavatar")
        assert user.avatar in AVATAR_CHOICES

    def test_register_duplicate_username(self, api_client):
        User.objects.create_user(username="taken", password="pass")
        response = api_client.post(self.URL, {
            "username": "taken",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert response.status_code == 400
        assert "username" in response.data

    def test_register_password_mismatch(self, api_client):
        response = api_client.post(self.URL, {
            "username": "mismatch",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass456!",
        })
        assert response.status_code == 400
        assert "password_confirm" in response.data

    def test_register_weak_password(self, api_client):
        response = api_client.post(self.URL, {
            "username": "weakpass",
            "password": "123",
            "password_confirm": "123",
        })
        assert response.status_code == 400

    def test_register_invalid_avatar(self, api_client):
        response = api_client.post(self.URL, {
            "username": "badavatar",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "avatar": "nonexistent",
        })
        assert response.status_code == 400
        assert "avatar" in response.data

    def test_inactive_user_cannot_login(self, api_client):
        api_client.post(self.URL, {
            "username": "inactive",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        response = api_client.post("/api/auth/login/", {
            "username": "inactive",
            "password": "StrongPass123!",
        })
        assert response.status_code == 401
```

- [ ] **Step 2: Run tests**

```bash
cd backend && uv run pytest tests/test_register.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_register.py
git commit -m "test(auth): add registration endpoint tests"
```

---

### Task 4: Admin user serializers & views

**Files:**
- Modify: `backend/apps/users/serializers.py`
- Modify: `backend/apps/users/views.py`

- [ ] **Step 1: Add AdminUserSerializer and AdminUserUpdateSerializer**

Append to `backend/apps/users/serializers.py`:

```python
class AdminUserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "avatar", "github_id", "is_active", "date_joined", "groups"]

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    groups = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = User
        fields = ["name", "email", "avatar", "is_active", "groups"]

    def validate_avatar(self, value):
        if value and value not in AVATAR_CHOICES:
            raise serializers.ValidationError("无效的头像选择")
        return value

    def validate_groups(self, value):
        from django.contrib.auth.models import Group
        groups = []
        for name in value:
            try:
                groups.append(Group.objects.get(name=name))
            except Group.DoesNotExist:
                raise serializers.ValidationError(f"用户组 '{name}' 不存在")
        return groups

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance
```

- [ ] **Step 2: Upgrade UserListView and UserDetailView**

Replace the `UserListView` and `UserDetailView` classes in `backend/apps/users/views.py`:

```python
from apps.permissions import FullDjangoModelPermissions
from .serializers import (
    UserSerializer, MeSerializer, RegisterSerializer,
    AdminUserSerializer, AdminUserUpdateSerializer,
)


class UserListView(ListAPIView):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserSerializer
    permission_classes = [FullDjangoModelPermissions]


class UserDetailView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [FullDjangoModelPermissions]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def update(self, request, *args, **kwargs):
        """Use AdminUserUpdateSerializer for input but return AdminUserSerializer for response."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = AdminUserUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserSerializer(instance).data)
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/users/serializers.py backend/apps/users/views.py
git commit -m "feat(users): add admin user serializers, upgrade list/detail views with permissions"
```

---

### Task 5: Admin user management tests

**Files:**
- Create: `backend/tests/test_user_admin.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Update auth_client fixture to include users app permissions**

In `backend/tests/conftest.py`, update the `auth_client` fixture's `filter` to include `"users"`:

```python
# Before:
group.permissions.set(
    Permission.objects.filter(content_type__app_label__in=["projects", "issues", "settings", "repos", "ai"])
)

# After:
group.permissions.set(
    Permission.objects.filter(content_type__app_label__in=["projects", "issues", "settings", "repos", "ai", "users"])
)
```

- [ ] **Step 2: Write admin user management tests**

Create `backend/tests/test_user_admin.py`:

```python
import pytest
from django.contrib.auth.models import Group
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestAdminUserList:
    def test_list_users_with_admin(self, auth_client):
        UserFactory.create_batch(3)
        response = auth_client.get("/api/users/")
        assert response.status_code == 200
        assert len(response.data) >= 4  # 3 + auth_client user
        first = response.data[0]
        assert "is_active" in first
        assert "date_joined" in first
        assert "groups" in first

    def test_list_users_without_permission(self, regular_client):
        response = regular_client.get("/api/users/")
        assert response.status_code == 403

    def test_list_users_unauthenticated(self, api_client):
        response = api_client.get("/api/users/")
        assert response.status_code == 401


class TestAdminUserDetail:
    def test_get_user_detail(self, auth_client):
        user = UserFactory(name="李四", avatar="robot")
        response = auth_client.get(f"/api/users/{user.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "李四"
        assert response.data["avatar"] == "robot"
        assert "is_active" in response.data

    def test_update_user(self, auth_client):
        user = UserFactory(name="旧名字")
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "name": "新名字",
            "email": "new@example.com",
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.name == "新名字"

    def test_activate_user(self, auth_client):
        user = UserFactory(is_active=False)
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "is_active": True,
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is True

    def test_deactivate_user(self, auth_client):
        user = UserFactory(is_active=True)
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "is_active": False,
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is False

    def test_assign_groups(self, auth_client):
        user = UserFactory()
        Group.objects.create(name="测试组")
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "groups": ["测试组"],
        }, format="json")
        assert response.status_code == 200
        assert "测试组" in list(user.groups.values_list("name", flat=True))

    def test_assign_nonexistent_group(self, auth_client):
        user = UserFactory()
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "groups": ["不存在的组"],
        }, format="json")
        assert response.status_code == 400

    def test_update_without_permission(self, regular_client):
        user = UserFactory()
        response = regular_client.patch(f"/api/users/{user.id}/", {
            "name": "hack",
        }, format="json")
        assert response.status_code == 403
```

- [ ] **Step 3: Run tests**

```bash
cd backend && uv run pytest tests/test_user_admin.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_user_admin.py backend/tests/conftest.py
git commit -m "test(users): add admin user management tests"
```

---

### Task 6: Change password endpoint + profile tests

**Files:**
- Modify: `backend/apps/users/serializers.py`
- Modify: `backend/apps/users/views.py`
- Modify: `backend/apps/users/auth_urls.py`
- Create: `backend/tests/test_profile.py`

- [ ] **Step 1: Add ChangePasswordSerializer**

Append to `backend/apps/users/serializers.py`:

```python
class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("当前密码错误")
        return value

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "两次密码输入不一致"})
        validate_password(data["new_password"])
        return data
```

- [ ] **Step 2: Add ChangePasswordView**

Add to `backend/apps/users/views.py`:

```python
from rest_framework.views import APIView
from .serializers import ChangePasswordSerializer


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "密码修改成功"})
```

- [ ] **Step 3: Add change-password URL**

Update `backend/apps/users/auth_urls.py`:

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView, RegisterView, ChangePasswordView

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token-login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("me/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("register/", RegisterView.as_view(), name="auth-register"),
]
```

- [ ] **Step 4: Write profile tests**

Create `backend/tests/test_profile.py`:

```python
import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestProfileUpdate:
    def test_update_name_and_email(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/auth/me/", {
            "name": "新昵称",
            "email": "newemail@example.com",
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.name == "新昵称"
        assert user.email == "newemail@example.com"

    def test_update_avatar(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/auth/me/", {
            "avatar": "docker-whale",
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.avatar == "docker-whale"

    def test_update_settings(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/auth/me/", {
            "settings": {"theme": "dark", "sidebar_auto_collapse": True},
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.settings["theme"] == "dark"


class TestChangePassword:
    URL = "/api/auth/me/change-password/"

    def test_change_password_success(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL, {
            "current_password": "testpass123",
            "new_password": "NewStrongPass456!",
            "new_password_confirm": "NewStrongPass456!",
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("NewStrongPass456!")

    def test_change_password_wrong_current(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL, {
            "current_password": "wrongpassword",
            "new_password": "NewStrongPass456!",
            "new_password_confirm": "NewStrongPass456!",
        })
        assert response.status_code == 400
        assert "current_password" in response.data

    def test_change_password_mismatch(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL, {
            "current_password": "testpass123",
            "new_password": "NewStrongPass456!",
            "new_password_confirm": "DifferentPass789!",
        })
        assert response.status_code == 400

    def test_change_password_unauthenticated(self, api_client):
        response = api_client.post(self.URL, {
            "current_password": "x",
            "new_password": "y",
            "new_password_confirm": "y",
        })
        assert response.status_code == 401
```

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/test_profile.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/users/serializers.py backend/apps/users/views.py backend/apps/users/auth_urls.py backend/tests/test_profile.py
git commit -m "feat(auth): add change-password endpoint with profile tests"
```

---

### Task 7: PAGE_PERMS configuration

**Files:**
- Modify: `backend/config/settings.py:111-127`

- [ ] **Step 1: Add user management route and permissions**

In `backend/config/settings.py`, in the `PAGE_PERMS` dict:

Add to `SEED_ROUTES` list (after the ai-insights entry, before permissions):
```python
{"path": "/app/users", "label": "用户管理", "icon": "i-heroicons-users", "permission": "users.view_user", "sort_order": 5},
```

In `SEED_GROUPS`, change the `"管理员"` entry to include `"users"`:
```python
"管理员": {"apps": ["projects", "issues", "settings", "repos", "ai", "users"]},
```

- [ ] **Step 2: Run sync_page_perms**

```bash
cd backend && uv run python manage.py sync_page_perms
```

Expected: Shows "Synced 7 routes" and "Updated group: 管理员".

- [ ] **Step 3: Run all existing tests to verify no regressions**

```bash
cd backend && uv run pytest -x -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/config/settings.py
git commit -m "feat(perms): add user management route and admin group permissions"
```

---

### Task 8: SVG avatars + frontend composable

**Files:**
- Create: `frontend/app/assets/images/avatars/*.svg` (20 files)
- Create: `frontend/app/composables/useAvatars.ts`

- [ ] **Step 1: Create 20 SVG avatar files**

Create each file in `frontend/app/assets/images/avatars/`. Each SVG should be `viewBox="0 0 100 100"`, geek-themed, distinctive. Use the designs from the brainstorm visual companion as reference.

Files to create:
`terminal-hacker.svg`, `robot.svg`, `bug-monster.svg`, `code-cat.svg`, `cpu-brain.svg`, `wifi-wizard.svg`, `binary-ghost.svg`, `docker-whale.svg`, `git-octopus.svg`, `code-ninja.svg`, `keyboard-warrior.svg`, `stack-overflow.svg`, `404-alien.svg`, `firewall-guard.svg`, `one-up-mushroom.svg`, `recursion-owl.svg`, `rubber-duck.svg`, `infinite-coffee.svg`, `sudo-penguin.svg`, `null-pointer.svg`

- [ ] **Step 2: Create useAvatars composable**

Create `frontend/app/composables/useAvatars.ts`:

```typescript
interface AvatarInfo {
  id: string
  label: string
}

const avatarList: AvatarInfo[] = [
  { id: 'terminal-hacker', label: '终端黑客' },
  { id: 'robot', label: '机器人' },
  { id: 'bug-monster', label: 'Bug 怪兽' },
  { id: 'code-cat', label: '代码猫' },
  { id: 'cpu-brain', label: 'CPU 大脑' },
  { id: 'wifi-wizard', label: 'WiFi 巫师' },
  { id: 'binary-ghost', label: '二进制幽灵' },
  { id: 'docker-whale', label: 'Docker 鲸' },
  { id: 'git-octopus', label: 'Git 章鱼' },
  { id: 'code-ninja', label: '代码忍者' },
  { id: 'keyboard-warrior', label: '键盘战士' },
  { id: 'stack-overflow', label: '栈溢出' },
  { id: '404-alien', label: '404 外星人' },
  { id: 'firewall-guard', label: '防火墙守卫' },
  { id: 'one-up-mushroom', label: '1-UP 蘑菇' },
  { id: 'recursion-owl', label: '递归猫头鹰' },
  { id: 'rubber-duck', label: '小黄鸭调试' },
  { id: 'infinite-coffee', label: '无限咖啡' },
  { id: 'sudo-penguin', label: 'Sudo 企鹅' },
  { id: 'null-pointer', label: '空指针' },
]

// Eager-import all SVGs from the avatars directory
const avatarModules = import.meta.glob('~/assets/images/avatars/*.svg', { eager: true, import: 'default' })

function resolveAvatarUrl(id: string): string {
  const key = Object.keys(avatarModules).find(k => k.includes(`/${id}.svg`))
  return key ? (avatarModules[key] as string) : ''
}

function randomAvatarId(): string {
  return avatarList[Math.floor(Math.random() * avatarList.length)].id
}

export function useAvatars() {
  return { avatarList, resolveAvatarUrl, randomAvatarId }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/assets/images/avatars/ frontend/app/composables/useAvatars.ts
git commit -m "feat(avatars): add 20 geek-themed SVG avatars and useAvatars composable"
```

---

### Task 9: AvatarPicker component

**Files:**
- Create: `frontend/app/components/AvatarPicker.vue`

- [ ] **Step 1: Create AvatarPicker component**

Create `frontend/app/components/AvatarPicker.vue`:

```vue
<template>
  <div>
    <div v-if="modelValue" class="flex items-center gap-3 mb-4">
      <img :src="resolveAvatarUrl(modelValue)" :alt="modelValue" class="w-16 h-16 rounded-full ring-2 ring-crystal-500" />
      <span class="text-sm text-gray-500 dark:text-gray-400">{{ avatarList.find(a => a.id === modelValue)?.label }}</span>
    </div>
    <div class="grid grid-cols-5 gap-3">
      <button
        v-for="avatar in avatarList"
        :key="avatar.id"
        type="button"
        class="relative group rounded-full overflow-hidden transition-all"
        :class="modelValue === avatar.id ? 'ring-3 ring-crystal-500 scale-110' : 'ring-1 ring-gray-200 dark:ring-gray-700 hover:ring-crystal-300'"
        @click="$emit('update:modelValue', avatar.id)"
      >
        <img :src="resolveAvatarUrl(avatar.id)" :alt="avatar.label" class="w-14 h-14" />
        <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <span class="text-white text-[10px] font-medium">{{ avatar.label }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()

const { avatarList, resolveAvatarUrl } = useAvatars()
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/AvatarPicker.vue
git commit -m "feat(ui): add reusable AvatarPicker component"
```

---

### Task 10: Registration page + login page link

**Files:**
- Create: `frontend/app/pages/register.vue`
- Modify: `frontend/app/pages/index.vue`
- Modify: `frontend/app/middleware/auth.global.ts`

- [ ] **Step 1: Allow /register in auth middleware**

In `frontend/app/middleware/auth.global.ts`, change line 2:

```typescript
// Before:
if (to.path === '/' || to.path === '/login') return

// After:
if (to.path === '/' || to.path === '/login' || to.path === '/register') return
```

- [ ] **Step 2: Create registration page**

Create `frontend/app/pages/register.vue`:

```vue
<template>
  <div class="w-full max-w-sm">
    <div class="text-center mb-8">
      <img src="~/assets/images/logo-icon.svg" alt="DevTrakr" class="w-14 h-14 mx-auto mb-4" />
      <h1 class="text-2xl font-semibold text-gray-900">DevTrakr</h1>
      <p class="text-sm text-gray-400 mt-1">项目管理平台</p>
    </div>

    <form class="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8" @submit.prevent="handleRegister">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">注册</h2>
      <div class="space-y-4">
        <UFormField label="用户名" required>
          <UInput v-model="form.username" placeholder="请输入用户名" icon="i-heroicons-user" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="密码" required>
          <UInput v-model="form.password" type="password" placeholder="请输入密码" icon="i-heroicons-lock-closed" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="确认密码" required>
          <UInput v-model="form.password_confirm" type="password" placeholder="请再次输入密码" icon="i-heroicons-lock-closed" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="昵称">
          <UInput v-model="form.name" placeholder="请输入昵称" icon="i-heroicons-user-circle" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="邮箱" hint="用于接收通知">
          <UInput v-model="form.email" type="email" placeholder="请输入邮箱" icon="i-heroicons-envelope" size="lg" class="w-full" />
        </UFormField>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">选择头像</label>
          <AvatarPicker v-model="form.avatar" />
        </div>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <UButton block size="lg" color="primary" :loading="loading" type="submit">注册</UButton>
      </div>
    </form>

    <p class="text-center text-sm text-gray-500 mt-4">
      已有账号？
      <NuxtLink to="/" class="text-crystal-500 hover:text-crystal-700 font-medium">返回登录</NuxtLink>
    </p>
    <p class="text-center text-xs text-gray-400 mt-6">&copy; 2026 DevTrakr 项目管理平台</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { randomAvatarId } = useAvatars()

const form = ref({
  username: '',
  password: '',
  password_confirm: '',
  name: '',
  email: '',
  avatar: randomAvatarId(),
})
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  if (form.value.password !== form.value.password_confirm) {
    error.value = '两次密码输入不一致'
    return
  }
  loading.value = true
  try {
    await $fetch('/api/auth/register/', {
      method: 'POST',
      body: form.value,
    })
    await navigateTo('/?registered=1')
  } catch (e: any) {
    const data = e?.data || e?.response?._data
    if (data && typeof data === 'object') {
      const msgs = Object.entries(data)
        .map(([k, v]) => Array.isArray(v) ? v.join(', ') : v)
        .join('; ')
      error.value = msgs || '注册失败，请重试'
    } else {
      error.value = '注册失败，请重试'
    }
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 3: Add register link and success toast to login page**

In `frontend/app/pages/index.vue`, add after the `</form>` tag and before the copyright line:

```vue
<p class="text-center text-sm text-gray-500 mt-4">
  还没有账号？
  <NuxtLink to="/register" class="text-crystal-500 hover:text-crystal-700 font-medium">去注册</NuxtLink>
</p>
```

In the `<script setup>` section, add success message handling:

```typescript
const route = useRoute()
const registered = computed(() => route.query.registered === '1')
```

Add a success alert above the form (after `<h2>` line):

```vue
<div v-if="registered" class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
  注册成功，请等待管理员审批后登录
</div>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/register.vue frontend/app/pages/index.vue frontend/app/middleware/auth.global.ts
git commit -m "feat(frontend): add registration page with avatar picker"
```

---

### Task 11: User list page (admin)

**Files:**
- Create: `frontend/app/pages/app/users/index.vue`

- [ ] **Step 1: Create user list page**

Create `frontend/app/pages/app/users/index.vue`:

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">用户管理</h1>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400 dark:text-gray-500">加载中...</div>
    </div>

    <div v-else class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
      <UTable :data="users" :columns="columns" :ui="{ th: 'text-xs', td: 'text-sm' }">
        <template #username-cell="{ row }">
          <NuxtLink :to="`/app/users/${row.original.id}`" class="text-crystal-500 dark:text-crystal-400 hover:text-crystal-700 dark:hover:text-crystal-300 font-medium flex items-center gap-2">
            <img v-if="row.original.avatar" :src="resolveAvatarUrl(row.original.avatar)" class="w-6 h-6 rounded-full" />
            {{ row.original.username }}
          </NuxtLink>
        </template>
        <template #is_active-cell="{ row }">
          <UBadge :color="row.original.is_active ? 'success' : 'warning'" variant="subtle" size="xs">
            {{ row.original.is_active ? '已激活' : '待审批' }}
          </UBadge>
        </template>
        <template #groups-cell="{ row }">
          <div class="flex gap-1 flex-wrap">
            <UBadge v-for="g in row.original.groups" :key="g" color="neutral" variant="subtle" size="xs">{{ g }}</UBadge>
            <span v-if="!row.original.groups?.length" class="text-gray-300 dark:text-gray-600">-</span>
          </div>
        </template>
        <template #date_joined-cell="{ row }">
          {{ row.original.date_joined?.slice(0, 10) || '-' }}
        </template>
      </UTable>
      <div class="flex items-center justify-between px-4 py-3 border-t border-gray-50 dark:border-gray-800">
        <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ users.length }} 位用户</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()

const loading = ref(true)
const users = ref<any[]>([])

const columns = [
  { accessorKey: 'username', header: '用户名' },
  { accessorKey: 'name', header: '昵称' },
  { accessorKey: 'email', header: '邮箱' },
  { accessorKey: 'is_active', header: '状态' },
  { accessorKey: 'groups', header: '用户组' },
  { accessorKey: 'date_joined', header: '注册时间' },
]

onMounted(async () => {
  try {
    users.value = await api<any[]>('/api/users/')
  } catch (e) {
    console.error('Failed to load users:', e)
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/pages/app/users/index.vue
git commit -m "feat(frontend): add admin user list page"
```

---

### Task 12: User detail page (admin)

**Files:**
- Create: `frontend/app/pages/app/users/[id].vue`

- [ ] **Step 1: Create user detail page**

Create `frontend/app/pages/app/users/[id].vue`:

```vue
<template>
  <div class="space-y-6 max-w-2xl">
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400">加载中...</div>
    </div>

    <template v-else-if="user">
      <div class="flex items-center gap-4">
        <img v-if="user.avatar" :src="resolveAvatarUrl(user.avatar)" class="w-16 h-16 rounded-full" />
        <div class="w-16 h-16 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xl font-semibold text-crystal-600 dark:text-crystal-400" v-else>
          {{ (user.name || user.username || '?').slice(0, 1) }}
        </div>
        <div>
          <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{{ user.username }}</h1>
          <UBadge :color="user.is_active ? 'success' : 'warning'" variant="subtle" size="sm" class="mt-1">
            {{ user.is_active ? '已激活' : '待审批' }}
          </UBadge>
        </div>
        <div class="ml-auto">
          <UButton
            :color="user.is_active ? 'warning' : 'success'"
            variant="soft"
            :loading="toggling"
            @click="toggleActive"
          >
            {{ user.is_active ? '停用用户' : '激活用户' }}
          </UButton>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <UFormField label="用户名">
            <UInput :model-value="user.username" disabled size="lg" class="w-full" />
          </UFormField>
          <UFormField label="昵称">
            <UInput v-model="form.name" size="lg" class="w-full" />
          </UFormField>
        </div>
        <UFormField label="邮箱">
          <UInput v-model="form.email" type="email" size="lg" class="w-full" />
        </UFormField>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">头像</label>
          <AvatarPicker v-model="form.avatar" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">用户组</label>
          <div class="flex gap-2 flex-wrap items-center">
            <UBadge v-for="g in form.groups" :key="g" color="primary" variant="subtle" class="gap-1">
              {{ g }}
              <button type="button" class="hover:text-red-500" @click="form.groups = form.groups.filter(x => x !== g)">&times;</button>
            </UBadge>
            <USelect
              :items="availableGroups"
              placeholder="+ 添加"
              size="sm"
              class="w-32"
              @update:model-value="addGroup"
            />
          </div>
        </div>
        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <div class="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
          <UButton variant="outline" color="neutral" @click="$router.back()">取消</UButton>
          <UButton :loading="saving" @click="handleSave">保存</UButton>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { api } = useApi()
const { resolveAvatarUrl } = useAvatars()

const loading = ref(true)
const saving = ref(false)
const toggling = ref(false)
const error = ref('')
const user = ref<any>(null)
const allGroups = ref<string[]>([])

const form = ref({ name: '', email: '', avatar: '', groups: [] as string[] })

const availableGroups = computed(() =>
  allGroups.value.filter(g => !form.value.groups.includes(g))
)

function addGroup(name: string) {
  if (name && !form.value.groups.includes(name)) {
    form.value.groups.push(name)
  }
}

async function toggleActive() {
  toggling.value = true
  try {
    const data = await api<any>(`/api/users/${route.params.id}/`, {
      method: 'PATCH',
      body: { is_active: !user.value.is_active },
    })
    user.value.is_active = data.is_active
  } catch (e) {
    console.error('Toggle failed:', e)
  } finally {
    toggling.value = false
  }
}

async function handleSave() {
  saving.value = true
  error.value = ''
  try {
    const data = await api<any>(`/api/users/${route.params.id}/`, {
      method: 'PATCH',
      body: { name: form.value.name, email: form.value.email, avatar: form.value.avatar, groups: form.value.groups },
    })
    user.value = { ...user.value, ...data }
    form.value = { name: data.name, email: data.email, avatar: data.avatar, groups: data.groups || [] }
  } catch (e: any) {
    error.value = '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [userData, groupsData] = await Promise.all([
      api<any>(`/api/users/${route.params.id}/`),
      api<any>('/api/page-perms/groups/').catch(() => []),
    ])
    user.value = userData
    form.value = { name: userData.name, email: userData.email, avatar: userData.avatar, groups: userData.groups || [] }
    allGroups.value = (Array.isArray(groupsData) ? groupsData : groupsData.results || []).map((g: any) => g.name)
  } catch (e) {
    console.error('Failed to load user:', e)
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/pages/app/users/\\[id\\].vue
git commit -m "feat(frontend): add admin user detail page with activate/deactivate"
```

---

### Task 13: Profile page

**Files:**
- Create: `frontend/app/pages/app/profile.vue`
- Modify: `frontend/app/components/AppHeader.vue`

- [ ] **Step 1: Create profile page**

Create `frontend/app/pages/app/profile.vue`:

```vue
<template>
  <div class="space-y-6 max-w-2xl">
    <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">个人资料</h1>

    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 space-y-6">
      <!-- Avatar & basic info -->
      <div class="flex items-center gap-4 pb-4 border-b border-gray-100 dark:border-gray-800">
        <img v-if="form.avatar" :src="resolveAvatarUrl(form.avatar)" class="w-16 h-16 rounded-full" />
        <div>
          <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ user?.username }}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">{{ user?.groups?.join(', ') || '无用户组' }}</div>
        </div>
      </div>

      <!-- Avatar picker -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">修改头像</label>
        <AvatarPicker v-model="form.avatar" />
      </div>

      <!-- Editable fields -->
      <div class="grid grid-cols-2 gap-4">
        <UFormField label="昵称">
          <UInput v-model="form.name" size="lg" class="w-full" />
        </UFormField>
        <UFormField label="邮箱" hint="用于接收通知">
          <UInput v-model="form.email" type="email" size="lg" class="w-full" />
        </UFormField>
      </div>

      <!-- Change password -->
      <div class="pt-4 border-t border-gray-100 dark:border-gray-800">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">修改密码</h3>
        <div class="space-y-3">
          <UFormField label="当前密码">
            <UInput v-model="pw.current" type="password" placeholder="请输入当前密码" size="lg" class="w-full" />
          </UFormField>
          <div class="grid grid-cols-2 gap-4">
            <UFormField label="新密码">
              <UInput v-model="pw.new_password" type="password" placeholder="请输入新密码" size="lg" class="w-full" />
            </UFormField>
            <UFormField label="确认新密码">
              <UInput v-model="pw.confirm" type="password" placeholder="请确认新密码" size="lg" class="w-full" />
            </UFormField>
          </div>
        </div>
      </div>

      <!-- Personal settings -->
      <div class="pt-4 border-t border-gray-100 dark:border-gray-800">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">个人设置</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-gray-700 dark:text-gray-300">侧栏自动收起</div>
              <div class="text-xs text-gray-400">窗口较小时自动折叠导航栏</div>
            </div>
            <USwitch v-model="settingsForm.sidebar_auto_collapse" />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-gray-700 dark:text-gray-300">问题列表默认视图</div>
              <div class="text-xs text-gray-400">打开问题跟踪页时的默认展示方式</div>
            </div>
            <USelect v-model="settingsForm.issues_view_mode" :items="viewModeOptions" size="sm" class="w-24" />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-gray-700 dark:text-gray-300">项目默认视图</div>
              <div class="text-xs text-gray-400">打开项目管理页时的默认展示方式</div>
            </div>
            <USelect v-model="settingsForm.project_view_mode" :items="viewModeOptions" size="sm" class="w-24" />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-gray-700 dark:text-gray-300">主题</div>
              <div class="text-xs text-gray-400">界面颜色模式</div>
            </div>
            <USelect v-model="settingsForm.theme" :items="themeOptions" size="sm" class="w-24" />
          </div>
        </div>
      </div>

      <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
      <p v-if="success" class="text-sm text-green-600">{{ success }}</p>
      <div class="flex justify-end pt-4 border-t border-gray-100 dark:border-gray-800">
        <UButton :loading="saving" @click="handleSave">保存修改</UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { api } = useApi()
const { user, fetchMe } = useAuth()
const { resolveAvatarUrl } = useAvatars()
const { settings } = useUserSettings()

const saving = ref(false)
const error = ref('')
const success = ref('')

const form = ref({ name: '', email: '', avatar: '' })
const pw = ref({ current: '', new_password: '', confirm: '' })
const settingsForm = ref({ sidebar_auto_collapse: false, issues_view_mode: 'table' as string, project_view_mode: 'kanban' as string, theme: 'light' as string })

const viewModeOptions = [{ label: '列表', value: 'table' }, { label: '看板', value: 'kanban' }]
const themeOptions = [{ label: '浅色', value: 'light' }, { label: '深色', value: 'dark' }, { label: '跟随系统', value: 'auto' }]

watch(user, (u) => {
  if (u) {
    form.value = { name: u.name || '', email: u.email || '', avatar: u.avatar || '' }
  }
}, { immediate: true })

watch(settings, (s) => {
  settingsForm.value = { ...s }
}, { immediate: true })

async function handleSave() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    // Save profile + settings
    await api('/api/auth/me/', {
      method: 'PATCH',
      body: { name: form.value.name, email: form.value.email, avatar: form.value.avatar, settings: settingsForm.value },
    })

    // Change password if filled
    if (pw.value.current && pw.value.new_password) {
      if (pw.value.new_password !== pw.value.confirm) {
        error.value = '两次新密码输入不一致'
        saving.value = false
        return
      }
      await api('/api/auth/me/change-password/', {
        method: 'POST',
        body: {
          current_password: pw.value.current,
          new_password: pw.value.new_password,
          new_password_confirm: pw.value.confirm,
        },
      })
      pw.value = { current: '', new_password: '', confirm: '' }
    }

    await fetchMe()
    success.value = '保存成功'
  } catch (e: any) {
    const data = e?.data || e?.response?._data
    if (data && typeof data === 'object') {
      const msgs = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join('; ')
      error.value = msgs || '保存失败'
    } else {
      error.value = '保存失败'
    }
  } finally {
    saving.value = false
  }
}
</script>
```

- [ ] **Step 2: Add "个人资料" to AppHeader dropdown**

In `frontend/app/components/AppHeader.vue`, update the `userMenuItems`:

```typescript
// Before:
const userMenuItems = [
  [{
    label: '退出登录',
    icon: 'i-heroicons-arrow-right-on-rectangle',
    onSelect: () => logout(),
  }],
]

// After:
const userMenuItems = [
  [{
    label: '个人资料',
    icon: 'i-heroicons-user-circle',
    onSelect: () => navigateTo('/app/profile'),
  }],
  [{
    label: '退出登录',
    icon: 'i-heroicons-arrow-right-on-rectangle',
    onSelect: () => logout(),
  }],
]
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/profile.vue frontend/app/components/AppHeader.vue
git commit -m "feat(frontend): add profile page with settings, link from header"
```

---

### Task 14: Update AppHeader avatar display + final integration

**Files:**
- Modify: `frontend/app/components/AppHeader.vue`

- [ ] **Step 1: Show avatar image in header if user has one**

In `frontend/app/components/AppHeader.vue`, add the `useAvatars` import and update the avatar display in the dropdown trigger:

Add to `<script setup>`:
```typescript
const { resolveAvatarUrl } = useAvatars()
```

Replace the avatar circle div in the template:

```vue
<!-- Before: -->
<div class="w-8 h-8 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
  <span class="text-crystal-600 dark:text-crystal-400 text-sm font-medium">{{ displayInitial }}</span>
</div>

<!-- After: -->
<img v-if="user?.avatar" :src="resolveAvatarUrl(user.avatar)" class="w-8 h-8 rounded-full" />
<div v-else class="w-8 h-8 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center">
  <span class="text-crystal-600 dark:text-crystal-400 text-sm font-medium">{{ displayInitial }}</span>
</div>
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/AppHeader.vue
git commit -m "feat(ui): show avatar image in header, fallback to initial"
```

---

### Task 15: Run all backend tests + final verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest -v
```

Expected: All tests pass including new test_register.py, test_user_admin.py, test_profile.py.

- [ ] **Step 2: Run sync_page_perms to verify config**

```bash
cd backend && uv run python manage.py sync_page_perms
```

Expected: Syncs 7 routes (including /app/users) and updates groups.

- [ ] **Step 3: Frontend typecheck**

```bash
cd frontend && npx nuxi typecheck
```

Expected: No type errors.

- [ ] **Step 4: Final commit if any fixes needed**

Fix any issues found, commit with descriptive message.
