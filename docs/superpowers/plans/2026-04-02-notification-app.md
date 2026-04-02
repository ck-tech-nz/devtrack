# Notification App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a general-purpose notification system with bell icon, dropdown panel, full notifications page, and Django Admin broadcast support.

**Architecture:** New `notifications` Django app with `Notification` + `NotificationRecipient` models. API viewset scoped to current user. Frontend `useNotifications` composable with 30s polling. Bell icon in AppHeader with dropdown, plus a full `/app/notifications` page.

**Tech Stack:** Django REST Framework, Nuxt 4, markdown-it, Tailwind CSS

---

### Task 1: Notification models + migration

**Files:**
- Create: `backend/apps/notifications/__init__.py`
- Create: `backend/apps/notifications/models.py`
- Modify: `backend/config/settings.py:21-43` (add to INSTALLED_APPS)

- [ ] **Step 1: Create the notifications app directory**

```bash
mkdir -p backend/apps/notifications
touch backend/apps/notifications/__init__.py
```

- [ ] **Step 2: Write the models**

Create `backend/apps/notifications/models.py`:

```python
import uuid
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        MENTION = "mention", "提及"
        SYSTEM = "system", "系统"
        BROADCAST = "broadcast", "广播"

    class TargetType(models.TextChoices):
        USER = "user", "个人"
        GROUP = "group", "组"
        ALL = "all", "全员"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(max_length=20, choices=Type.choices, verbose_name="类型")
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(blank=True, verbose_name="内容")
    source_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sent_notifications", verbose_name="触发者",
    )
    source_issue = models.ForeignKey(
        "issues.Issue", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="notifications", verbose_name="关联问题",
    )
    target_type = models.CharField(max_length=10, choices=TargetType.choices, verbose_name="目标类型")
    target_group = models.ForeignKey(
        "auth.Group", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="目标组",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class NotificationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="recipients",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notification_recipients",
    )
    is_read = models.BooleanField(default=False, verbose_name="已读")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="阅读时间")
    is_deleted = models.BooleanField(default=False, verbose_name="已删除")

    class Meta:
        verbose_name = "通知接收"
        verbose_name_plural = "通知接收"
        unique_together = [("notification", "user")]

    def __str__(self):
        return f"{self.notification.title} → {self.user}"
```

- [ ] **Step 3: Register app in INSTALLED_APPS**

In `backend/config/settings.py`, add `"apps.notifications"` after `"apps.tools"` in INSTALLED_APPS:

```python
    "apps.tools",
    "apps.notifications",
    # Packages
```

- [ ] **Step 4: Generate and apply migration**

```bash
cd backend && uv run python manage.py makemigrations notifications && uv run python manage.py migrate
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/notifications/ backend/config/settings.py
git commit -m "feat(notifications): add Notification and NotificationRecipient models"
```

---

### Task 2: Notification admin with broadcast recipient generation

**Files:**
- Create: `backend/apps/notifications/admin.py`

- [ ] **Step 1: Write the admin**

Create `backend/apps/notifications/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth import get_user_model
from unfold.admin import ModelAdmin, TabularInline
from .models import Notification, NotificationRecipient

User = get_user_model()


class RecipientInline(TabularInline):
    model = NotificationRecipient
    extra = 0
    readonly_fields = ("user", "is_read", "read_at")


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "notification_type", "target_type", "created_at")
    list_filter = ("notification_type", "target_type")
    search_fields = ("title",)
    inlines = [RecipientInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            self._create_recipients(obj)

    def _create_recipients(self, notification):
        if notification.target_type == Notification.TargetType.ALL:
            users = User.objects.filter(is_active=True)
        elif notification.target_type == Notification.TargetType.GROUP and notification.target_group:
            users = notification.target_group.user_set.filter(is_active=True)
        else:
            return
        recipients = [
            NotificationRecipient(notification=notification, user=u)
            for u in users
        ]
        NotificationRecipient.objects.bulk_create(recipients, ignore_conflicts=True)


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(ModelAdmin):
    list_display = ("notification", "user", "is_read", "is_deleted")
    list_filter = ("is_read", "is_deleted")
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/notifications/admin.py
git commit -m "feat(notifications): add admin with broadcast recipient generation"
```

---

### Task 3: Notification API — serializers, views, URLs

**Files:**
- Create: `backend/apps/notifications/serializers.py`
- Create: `backend/apps/notifications/views.py`
- Create: `backend/apps/notifications/urls.py`
- Modify: `backend/apps/urls.py`

- [ ] **Step 1: Write serializers**

Create `backend/apps/notifications/serializers.py`:

```python
from rest_framework import serializers
from .models import Notification, NotificationRecipient


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(source="recipient.is_read", read_only=True)
    read_at = serializers.DateTimeField(source="recipient.read_at", read_only=True)
    source_user_name = serializers.CharField(source="source_user.name", read_only=True, default=None)
    source_issue_title = serializers.CharField(source="source_issue.title", read_only=True, default=None)
    source_issue_id = serializers.IntegerField(source="source_issue_id", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "content",
            "source_user_name", "source_issue_id", "source_issue_title",
            "is_read", "read_at", "created_at",
        ]
```

- [ ] **Step 2: Write views**

Create `backend/apps/notifications/views.py`:

```python
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification, NotificationRecipient
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(
            recipients__user=self.request.user,
            recipients__is_deleted=False,
        ).select_related("source_user", "source_issue")
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(recipients__is_read=is_read.lower() == "true")
        return qs.order_by("-created_at")

    def get_serializer(self, *args, **kwargs):
        """Attach the recipient record to each notification for the serializer."""
        instance = kwargs.get("instance") or (args[0] if args else None)
        if instance is not None and hasattr(instance, "__iter__"):
            recipient_map = {
                r.notification_id: r
                for r in NotificationRecipient.objects.filter(
                    user=self.request.user,
                    notification__in=instance,
                )
            }
            for notif in instance:
                notif.recipient = recipient_map.get(notif.id)
        elif instance is not None:
            notif = instance
            notif.recipient = NotificationRecipient.objects.filter(
                user=self.request.user, notification=notif,
            ).first()
        return super().get_serializer(*args, **kwargs)


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationRecipient.objects.filter(
            user=request.user, is_read=False, is_deleted=False,
        ).count()
        return Response({"count": count})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            recipient = NotificationRecipient.objects.get(
                notification_id=pk, user=request.user,
            )
        except NotificationRecipient.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        recipient.is_read = True
        recipient.read_at = timezone.now()
        recipient.save(update_fields=["is_read", "read_at"])
        return Response({"detail": "已标记已读"})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = NotificationRecipient.objects.filter(
            user=request.user, is_read=False, is_deleted=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated})


class DeleteNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            recipient = NotificationRecipient.objects.get(
                notification_id=pk, user=request.user,
            )
        except NotificationRecipient.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        recipient.is_deleted = True
        recipient.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 3: Write URL routing**

Create `backend/apps/notifications/urls.py`:

```python
from django.urls import path
from .views import (
    NotificationListView, UnreadCountView,
    MarkReadView, MarkAllReadView, DeleteNotificationView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("<uuid:pk>/read/", MarkReadView.as_view(), name="notification-read"),
    path("read-all/", MarkAllReadView.as_view(), name="notification-read-all"),
    path("<uuid:pk>/", DeleteNotificationView.as_view(), name="notification-delete"),
]
```

- [ ] **Step 4: Register in root URL conf**

In `backend/apps/urls.py`, add:

```python
    path("notifications/", include("apps.notifications.urls")),
```

after the `"tools/"` line.

- [ ] **Step 5: Verify server starts**

```bash
cd backend && uv run python manage.py check
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/notifications/serializers.py backend/apps/notifications/views.py backend/apps/notifications/urls.py backend/apps/urls.py
git commit -m "feat(notifications): add API endpoints for list, read, read-all, delete"
```

---

### Task 4: Backend tests for notification API

**Files:**
- Create: `backend/tests/test_notifications.py`
- Modify: `backend/tests/factories.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add notification factories**

Append to `backend/tests/factories.py`:

```python
from apps.notifications.models import Notification, NotificationRecipient


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    notification_type = "system"
    title = factory.LazyFunction(lambda: fake.sentence())
    content = factory.LazyFunction(lambda: fake.paragraph())
    target_type = "user"


class NotificationRecipientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationRecipient

    notification = factory.SubFactory(NotificationFactory)
    user = factory.SubFactory(UserFactory)
    is_read = False
    is_deleted = False
```

- [ ] **Step 2: Add notifications permissions to auth_user fixture**

In `backend/tests/conftest.py`, update the `auth_user` fixture's permission filter to include `"notifications"`:

```python
    group.permissions.set(
        Permission.objects.filter(content_type__app_label__in=[
            "projects", "issues", "settings", "repos", "ai", "users", "notifications",
        ])
    )
```

- [ ] **Step 3: Write the tests**

Create `backend/tests/test_notifications.py`:

```python
import pytest
from tests.factories import (
    UserFactory, NotificationFactory, NotificationRecipientFactory,
)

pytestmark = pytest.mark.django_db


class TestNotificationList:
    def test_list_own_notifications(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user)
        # Another user's notification — should not appear
        NotificationRecipientFactory()
        response = auth_client.get("/api/notifications/")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == n.title

    def test_filter_unread(self, auth_client, auth_user):
        n1 = NotificationFactory(title="unread")
        NotificationRecipientFactory(notification=n1, user=auth_user, is_read=False)
        n2 = NotificationFactory(title="read")
        NotificationRecipientFactory(notification=n2, user=auth_user, is_read=True)
        response = auth_client.get("/api/notifications/?is_read=false")
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "unread"

    def test_deleted_not_shown(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user, is_deleted=True)
        response = auth_client.get("/api/notifications/")
        assert response.data["count"] == 0

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notifications/")
        assert response.status_code == 401


class TestUnreadCount:
    def test_count(self, auth_client, auth_user):
        for _ in range(3):
            n = NotificationFactory()
            NotificationRecipientFactory(notification=n, user=auth_user, is_read=False)
        n_read = NotificationFactory()
        NotificationRecipientFactory(notification=n_read, user=auth_user, is_read=True)
        response = auth_client.get("/api/notifications/unread-count/")
        assert response.status_code == 200
        assert response.data["count"] == 3


class TestMarkRead:
    def test_mark_single_read(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user, is_read=False)
        response = auth_client.post(f"/api/notifications/{n.id}/read/")
        assert response.status_code == 200
        assert response.data["detail"] == "已标记已读"
        # Verify via unread count
        response = auth_client.get("/api/notifications/unread-count/")
        assert response.data["count"] == 0

    def test_mark_nonexistent(self, auth_client):
        import uuid
        response = auth_client.post(f"/api/notifications/{uuid.uuid4()}/read/")
        assert response.status_code == 404


class TestMarkAllRead:
    def test_mark_all(self, auth_client, auth_user):
        for _ in range(3):
            n = NotificationFactory()
            NotificationRecipientFactory(notification=n, user=auth_user, is_read=False)
        response = auth_client.post("/api/notifications/read-all/")
        assert response.status_code == 200
        assert response.data["updated"] == 3
        response = auth_client.get("/api/notifications/unread-count/")
        assert response.data["count"] == 0


class TestDeleteNotification:
    def test_soft_delete(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user)
        response = auth_client.delete(f"/api/notifications/{n.id}/")
        assert response.status_code == 204
        # Should not appear in list
        response = auth_client.get("/api/notifications/")
        assert response.data["count"] == 0


class TestBroadcastAdmin:
    def test_broadcast_creates_recipients(self, auth_user):
        """Verify the admin save_model hook creates recipients for all active users."""
        from apps.notifications.models import Notification, NotificationRecipient
        n = Notification.objects.create(
            notification_type="broadcast",
            title="系统公告",
            content="维护通知",
            target_type="all",
        )
        # Simulate what admin does
        from apps.notifications.admin import NotificationAdmin
        admin_instance = NotificationAdmin(Notification, None)
        admin_instance._create_recipients(n)
        assert NotificationRecipient.objects.filter(notification=n, user=auth_user).exists()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/test_notifications.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_notifications.py backend/tests/factories.py backend/tests/conftest.py
git commit -m "test(notifications): add API tests for list, read, delete, broadcast"
```

---

### Task 5: Frontend — useNotifications composable

**Files:**
- Create: `frontend/app/composables/useNotifications.ts`

- [ ] **Step 1: Write the composable**

Create `frontend/app/composables/useNotifications.ts`:

```typescript
export interface NotificationItem {
  id: string
  notification_type: string
  title: string
  content: string
  source_user_name: string | null
  source_issue_id: number | null
  source_issue_title: string | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

const POLL_INTERVAL = 30_000

export function useNotifications() {
  const { api } = useApi()
  const unreadCount = useState<number>('notification_unread_count', () => 0)
  const notifications = useState<NotificationItem[]>('notification_list', () => [])
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function fetchUnreadCount() {
    try {
      const data = await api<{ count: number }>('/api/notifications/unread-count/')
      unreadCount.value = data.count
    } catch {
      // silently ignore polling errors
    }
  }

  async function fetchNotifications(params: { is_read?: string; page?: number } = {}) {
    const query = new URLSearchParams()
    if (params.is_read !== undefined) query.set('is_read', params.is_read)
    if (params.page) query.set('page', String(params.page))
    const qs = query.toString()
    const url = `/api/notifications/${qs ? '?' + qs : ''}`
    return await api<PaginatedResponse<NotificationItem>>(url)
  }

  async function fetchRecent() {
    const data = await api<PaginatedResponse<NotificationItem>>('/api/notifications/?page_size=5')
    notifications.value = data.results
    return data
  }

  async function markRead(id: string) {
    await api(`/api/notifications/${id}/read/`, { method: 'POST' })
    const item = notifications.value.find(n => n.id === id)
    if (item) item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  async function markAllRead() {
    await api('/api/notifications/read-all/', { method: 'POST' })
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  }

  async function deleteNotification(id: string) {
    await api(`/api/notifications/${id}/`, { method: 'DELETE' })
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  function startPolling() {
    if (pollTimer) return
    fetchUnreadCount()
    pollTimer = setInterval(fetchUnreadCount, POLL_INTERVAL)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    unreadCount,
    notifications,
    fetchUnreadCount,
    fetchNotifications,
    fetchRecent,
    markRead,
    markAllRead,
    deleteNotification,
    startPolling,
    stopPolling,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/composables/useNotifications.ts
git commit -m "feat(notifications): add useNotifications composable with polling"
```

---

### Task 6: Frontend — bell icon + dropdown in AppHeader

**Files:**
- Create: `frontend/app/components/NotificationBell.vue`
- Modify: `frontend/app/components/AppHeader.vue`

- [ ] **Step 1: Create NotificationBell component**

Create `frontend/app/components/NotificationBell.vue`:

```vue
<template>
  <div class="relative" ref="containerRef">
    <UButton
      icon="i-heroicons-bell"
      variant="ghost"
      color="neutral"
      size="sm"
      class="relative"
      @click="togglePanel"
    >
      <span
        v-if="unreadCount > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-medium rounded-full flex items-center justify-center"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </UButton>

    <!-- Dropdown panel -->
    <Transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0 translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-100"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-1"
    >
      <div
        v-if="open"
        class="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">通知</span>
          <button
            v-if="unreadCount > 0"
            class="text-xs text-primary-600 dark:text-primary-400 hover:underline"
            @click="handleMarkAllRead"
          >
            全部已读
          </button>
        </div>

        <!-- List -->
        <div class="max-h-80 overflow-y-auto">
          <div v-if="notifications.length === 0" class="py-8 text-center text-sm text-gray-400">
            暂无通知
          </div>
          <button
            v-for="n in notifications"
            :key="n.id"
            class="w-full text-left px-4 py-3 border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            :class="{ 'bg-primary-50/50 dark:bg-primary-950/30': !n.is_read }"
            @click="handleClick(n)"
          >
            <div class="flex items-start gap-2">
              <span
                v-if="!n.is_read"
                class="mt-1.5 w-2 h-2 rounded-full bg-primary-500 flex-shrink-0"
              />
              <div class="min-w-0 flex-1">
                <p class="text-sm text-gray-900 dark:text-gray-100 truncate">{{ n.title }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ formatTime(n.created_at) }}</p>
              </div>
            </div>
          </button>
        </div>

        <!-- Footer -->
        <div class="px-4 py-2 border-t border-gray-100 dark:border-gray-800 text-center">
          <NuxtLink
            to="/app/notifications"
            class="text-xs text-primary-600 dark:text-primary-400 hover:underline"
            @click="open = false"
          >
            查看全部通知
          </NuxtLink>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
const { unreadCount, notifications, fetchRecent, markRead, markAllRead, startPolling, stopPolling } = useNotifications()

const open = ref(false)
const containerRef = ref<HTMLElement | null>(null)

function togglePanel() {
  open.value = !open.value
  if (open.value) fetchRecent()
}

function handleClick(n: (typeof notifications.value)[0]) {
  if (!n.is_read) markRead(n.id)
  if (n.source_issue_id) {
    navigateTo(`/app/issues/${n.source_issue_id}`)
  }
  open.value = false
}

async function handleMarkAllRead() {
  await markAllRead()
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString('zh-CN')
}

// Close on outside click
function onClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => {
  startPolling()
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  stopPolling()
  document.removeEventListener('click', onClickOutside)
})
</script>
```

- [ ] **Step 2: Replace the static bell button in AppHeader**

In `frontend/app/components/AppHeader.vue`, replace the existing bell UButton (lines 24-26):

```html
      <UButton icon="i-heroicons-bell" variant="ghost" color="neutral" size="sm" class="relative">
        <span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-crystal-500 rounded-full" />
      </UButton>
```

with:

```html
      <NotificationBell />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/NotificationBell.vue frontend/app/components/AppHeader.vue
git commit -m "feat(notifications): add bell icon with dropdown panel in header"
```

---

### Task 7: Frontend — notifications page

**Files:**
- Create: `frontend/app/pages/app/notifications.vue`

- [ ] **Step 1: Create the notifications page**

Create `frontend/app/pages/app/notifications.vue`:

```vue
<template>
  <div class="max-w-3xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">通知中心</h1>
      <UButton
        v-if="unreadCount > 0"
        variant="soft"
        size="sm"
        @click="handleMarkAllRead"
      >
        全部已读
      </UButton>
    </div>

    <!-- Filter tabs -->
    <div class="flex gap-1 mb-4">
      <UButton
        v-for="tab in tabs"
        :key="tab.value"
        :variant="activeTab === tab.value ? 'solid' : 'ghost'"
        size="xs"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </UButton>
    </div>

    <!-- Notification list -->
    <div class="space-y-2">
      <div v-if="loading" class="py-12 text-center text-sm text-gray-400">加载中...</div>
      <div v-else-if="data && data.results.length === 0" class="py-12 text-center text-sm text-gray-400">
        暂无通知
      </div>
      <div
        v-for="n in data?.results"
        :key="n.id"
        class="flex items-start gap-3 p-4 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl transition-colors"
        :class="{ 'border-l-2 border-l-primary-500': !n.is_read }"
      >
        <!-- Unread dot -->
        <span
          v-if="!n.is_read"
          class="mt-1.5 w-2 h-2 rounded-full bg-primary-500 flex-shrink-0"
        />
        <div v-else class="w-2 flex-shrink-0" />

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ n.title }}</span>
            <span class="text-xs text-gray-400">{{ formatTime(n.created_at) }}</span>
          </div>
          <div
            v-if="n.content"
            class="mt-1 text-sm text-gray-600 dark:text-gray-400 markdown-body-inline"
            v-html="renderMarkdown(n.content)"
          />
          <NuxtLink
            v-if="n.source_issue_id"
            :to="`/app/issues/${n.source_issue_id}`"
            class="inline-block mt-1 text-xs text-primary-600 dark:text-primary-400 hover:underline"
          >
            查看问题 #{{ n.source_issue_id }}
          </NuxtLink>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 flex-shrink-0">
          <UButton
            v-if="!n.is_read"
            icon="i-heroicons-check"
            variant="ghost"
            color="neutral"
            size="xs"
            title="标记已读"
            @click="handleMarkRead(n)"
          />
          <UButton
            icon="i-heroicons-trash"
            variant="ghost"
            color="neutral"
            size="xs"
            title="删除"
            @click="handleDelete(n)"
          />
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="data && data.count > 20" class="flex justify-center mt-6">
      <UPagination
        :model-value="page"
        :total="data.count"
        :items-per-page="20"
        @update:model-value="page = $event"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'

const { unreadCount, fetchNotifications, markRead, markAllRead, deleteNotification, fetchUnreadCount } = useNotifications()

const md = new MarkdownIt({ html: false, linkify: true })

const tabs = [
  { label: '全部', value: 'all' },
  { label: '未读', value: 'unread' },
  { label: '已读', value: 'read' },
]

const activeTab = ref('all')
const page = ref(1)
const loading = ref(false)
const data = ref<Awaited<ReturnType<typeof fetchNotifications>> | null>(null)

async function load() {
  loading.value = true
  const params: { is_read?: string; page?: number } = {}
  if (activeTab.value === 'unread') params.is_read = 'false'
  if (activeTab.value === 'read') params.is_read = 'true'
  if (page.value > 1) params.page = page.value
  data.value = await fetchNotifications(params)
  loading.value = false
}

async function handleMarkRead(n: { id: string; is_read: boolean }) {
  await markRead(n.id)
  n.is_read = true
}

async function handleMarkAllRead() {
  await markAllRead()
  await load()
}

async function handleDelete(n: { id: string }) {
  await deleteNotification(n.id)
  await fetchUnreadCount()
  await load()
}

function renderMarkdown(text: string): string {
  return md.renderInline(text)
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString('zh-CN')
}

watch(activeTab, () => {
  page.value = 1
  load()
})

watch(page, load)

onMounted(load)
</script>

<style scoped>
.markdown-body-inline :deep(a) { color: #2563eb; text-decoration: none; }
.markdown-body-inline :deep(a:hover) { text-decoration: underline; }
.markdown-body-inline :deep(code) { background: #f3f4f6; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.85em; }
:root.dark .markdown-body-inline :deep(a) { color: #60a5fa; }
:root.dark .markdown-body-inline :deep(code) { background: #1f2937; }
</style>
```

- [ ] **Step 2: Add standalone page entry for breadcrumbs**

In `frontend/app/composables/useNavigation.ts`, add to the `standalonePages` object:

```typescript
  const standalonePages: Record<string, string> = {
    '/app/profile': '个人资料',
    '/app/about': '关于系统',
    '/app/notifications': '通知中心',
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/notifications.vue frontend/app/composables/useNavigation.ts
git commit -m "feat(notifications): add full notifications page with filters and pagination"
```

---

### Task 8: Manual integration test

- [ ] **Step 1: Start backend and frontend**

```bash
cd backend && uv run python manage.py runserver &
cd frontend && npm run dev &
```

- [ ] **Step 2: Create a test notification via Django Admin**

Open `http://localhost:8000/api/admin/notifications/notification/add/`, create a broadcast notification with target_type=`all`.

- [ ] **Step 3: Verify**

- Bell icon shows unread count
- Clicking bell shows the dropdown with the notification
- Clicking "查看全部通知" navigates to `/app/notifications`
- Mark read and delete work correctly
- Unread count updates after 30 seconds

- [ ] **Step 4: Run full test suite**

```bash
cd backend && uv run pytest -x
```

Expected: All tests PASS.

- [ ] **Step 5: Commit if any fixes were needed**

```bash
git add -A && git commit -m "fix(notifications): integration fixes"
```
