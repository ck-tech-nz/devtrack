# PageRoute 父子分组 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让侧边栏菜单层级 (分组 → 子项) 由数据库驱动 — `PageRoute` 自引用 `parent`，分组行用 `#group:xxx` 占位 path；JSON seed 扁平存储 + `parent` 引用；删除前端写死的 `GROUP_DEFS`。

**Architecture:**
- 后端 `PageRoute` 新增 `parent` 自引用外键 + `is_group` 布尔字段。分组行 `path` 形如 `#group:project-mgmt`，`is_group=True`，没有 `permission`/`meta`/`icon` 之外的语义；叶子行通过 `parent` FK 挂到某个分组下。
- JSON seed 仍是扁平的 `seed_routes` 数组，每行可带 `"parent": "#group:xxx"` 字段；`sync_page_perms` 分两遍处理 (先建组，再挂叶子)。
- 前端 `usePagePerms` 返回扁平列表 + `parent` 路径；`useNavigation.groupedNavItems` 根据 `parent` 字段自己建树，`GROUP_DEFS` 删除。

**Tech Stack:** Django 6 + DRF + `django-page-perms` (in `packages/`)，Nuxt 4 + Vue 3 + TS，pytest-django，uv。

**Out of scope:** UI 拖拽排序、admin inline、超过两级的层级 (Task 9 会硬约束 `parent.parent IS NULL`)。

---

## Task 1: 加 `is_group` 字段 + `parent` 自引用外键 (model + migration)

**Files:**
- Modify: `packages/django-page-perms/page_perms/models.py`
- Create: `packages/django-page-perms/page_perms/migrations/0002_pageroute_parent_is_group.py`
- Test: `backend/tests/test_page_perms_models.py`

- [ ] **Step 1: 写失败的测试**

追加到 `backend/tests/test_page_perms_models.py`:

```python
class TestPageRouteHierarchy:
    def test_group_row_can_be_created(self):
        group = PageRoute.objects.create(
            path="#group:project-mgmt",
            label="项目管理",
            icon="i-heroicons-folder",
            is_group=True,
        )
        assert group.is_group is True
        assert group.parent is None

    def test_leaf_can_reference_parent(self):
        group = PageRoute.objects.create(
            path="#group:project-mgmt", label="项目管理", is_group=True,
        )
        leaf = PageRoute.objects.create(
            path="/app/projects", label="项目列表", parent=group,
        )
        leaf.refresh_from_db()
        assert leaf.parent == group
        assert list(group.children.all()) == [leaf]

    def test_parent_set_null_on_delete(self):
        group = PageRoute.objects.create(
            path="#group:tmp", label="临时", is_group=True,
        )
        leaf = PageRoute.objects.create(
            path="/app/x", label="X", parent=group,
        )
        group.delete()
        leaf.refresh_from_db()
        assert leaf.parent is None

    def test_leaf_defaults_to_not_group(self):
        leaf = PageRoute.objects.create(path="/app/x", label="X")
        assert leaf.is_group is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest backend/tests/test_page_perms_models.py::TestPageRouteHierarchy -v
```
Expected: 全部 FAIL，错误形如 `TypeError: PageRoute() got unexpected keyword arguments: 'is_group'` 或 `'parent'`。

- [ ] **Step 3: 修改 model**

`packages/django-page-perms/page_perms/models.py` 完整内容:

```python
from django.contrib.auth.models import Permission
from django.db import models


class PageRoute(models.Model):
    path = models.CharField(max_length=255, unique=True, verbose_name="路由路径")
    label = models.CharField(max_length=100, verbose_name="显示名称")
    icon = models.CharField(max_length=100, blank=True, default="", verbose_name="图标")
    permission = models.ForeignKey(
        Permission,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_routes",
        verbose_name="所需权限",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父级菜单",
    )
    is_group = models.BooleanField(default=False, verbose_name="是分组")
    show_in_nav = models.BooleanField(default=True, verbose_name="显示在导航栏")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    meta = models.JSONField(default=dict, blank=True, verbose_name="元数据")
    source = models.CharField(
        max_length=20, default="manual", verbose_name="来源",
        help_text="seed = sync command, manual = UI",
    )

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "页面路由"
        verbose_name_plural = "页面路由"

    def __str__(self):
        if self.is_group:
            return f"[分组] {self.label}"
        return f"{self.path} → {self.permission or '(无权限要求)'}"
```

- [ ] **Step 4: 生成迁移**

```bash
cd backend && uv run python manage.py makemigrations page_perms --name pageroute_parent_is_group
```

确认生成 `packages/django-page-perms/page_perms/migrations/0002_pageroute_parent_is_group.py`，其中包含 `AddField(name='parent', ...)` 和 `AddField(name='is_group', ...)`。

- [ ] **Step 5: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_page_perms_models.py::TestPageRouteHierarchy -v
```
Expected: 全部 PASS (4 tests)。

- [ ] **Step 6: 也跑老的 model 测试，确保没回归**

```bash
cd backend && uv run pytest tests/test_page_perms_models.py -v
```
Expected: 全部 PASS。

- [ ] **Step 7: Commit**

```bash
git add packages/django-page-perms/page_perms/models.py \
        packages/django-page-perms/page_perms/migrations/0002_pageroute_parent_is_group.py \
        backend/tests/test_page_perms_models.py
git commit -m "feat(page_perms): add parent FK + is_group on PageRoute"
```

---

## Task 2: serializer 暴露 `parent` + `is_group`

**Files:**
- Modify: `packages/django-page-perms/page_perms/serializers.py:28-56` (PageRouteSerializer)
- Test: `backend/tests/test_page_perms_routes_api.py`

- [ ] **Step 1: 写失败的测试**

追加到 `backend/tests/test_page_perms_routes_api.py` (假设已有 `auth_client` fixture，路由列表接口是 `/api/page-perms/routes/`):

```python
class TestRoutesAPIHierarchy:
    def test_list_returns_parent_path_and_is_group(self, auth_client):
        from page_perms.models import PageRoute
        group = PageRoute.objects.create(
            path="#group:proj", label="项目管理", is_group=True, source="manual",
        )
        PageRoute.objects.create(
            path="/app/projects", label="项目", parent=group, source="manual",
        )
        resp = auth_client.get("/api/page-perms/routes/")
        assert resp.status_code == 200
        data = resp.json()
        rows = data if isinstance(data, list) else data["results"]
        by_path = {r["path"]: r for r in rows}
        assert by_path["#group:proj"]["is_group"] is True
        assert by_path["#group:proj"]["parent"] is None
        assert by_path["/app/projects"]["is_group"] is False
        assert by_path["/app/projects"]["parent"] == "#group:proj"

    def test_create_leaf_with_parent_path(self, auth_client):
        from page_perms.models import PageRoute
        PageRoute.objects.create(
            path="#group:proj", label="项目管理", is_group=True, source="manual",
        )
        resp = auth_client.post(
            "/api/page-perms/routes/",
            {
                "path": "/app/repos",
                "label": "仓库",
                "parent": "#group:proj",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        leaf = PageRoute.objects.get(path="/app/repos")
        assert leaf.parent and leaf.parent.path == "#group:proj"

    def test_create_with_missing_parent_returns_400(self, auth_client):
        resp = auth_client.post(
            "/api/page-perms/routes/",
            {"path": "/app/x", "label": "X", "parent": "#group:nope"},
            format="json",
        )
        assert resp.status_code == 400
        assert "parent" in resp.json()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_page_perms_routes_api.py::TestRoutesAPIHierarchy -v
```
Expected: FAIL，原因可能是返回里没有 `parent`/`is_group`，或 POST 时这两个字段被丢弃。

- [ ] **Step 3: 修改 serializer**

`packages/django-page-perms/page_perms/serializers.py` 中 `PageRouteSerializer` 替换为:

```python
class PageRouteSerializer(serializers.ModelSerializer):
    permission = serializers.CharField(allow_null=True, required=False, default=None)
    parent = serializers.CharField(allow_null=True, required=False, default=None)

    class Meta:
        model = PageRoute
        fields = [
            "id", "path", "label", "icon", "permission",
            "parent", "is_group",
            "show_in_nav", "sort_order", "is_active", "meta", "source",
        ]
        read_only_fields = ["source"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.permission:
            ct = instance.permission.content_type
            data["permission"] = f"{ct.app_label}.{instance.permission.codename}"
        else:
            data["permission"] = None
        data["parent"] = instance.parent.path if instance.parent_id else None
        return data

    def validate_permission(self, value):
        return resolve_permission(value)

    def validate_parent(self, value):
        if not value:
            return None
        try:
            return PageRoute.objects.get(path=value)
        except PageRoute.DoesNotExist:
            raise serializers.ValidationError(
                f"Parent route '{value}' does not exist."
            )

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_page_perms_routes_api.py -v
```
Expected: 新 class 通过，原有用例仍然 PASS。

- [ ] **Step 5: Commit**

```bash
git add packages/django-page-perms/page_perms/serializers.py \
        backend/tests/test_page_perms_routes_api.py
git commit -m "feat(page_perms): expose parent + is_group via API"
```

---

## Task 3: admin 显示 parent / is_group / 过滤

**Files:**
- Modify: `packages/django-page-perms/page_perms/admin.py`

- [ ] **Step 1: 修改 admin**

`packages/django-page-perms/page_perms/admin.py` 完整内容:

```python
from django.contrib import admin
from .models import PageRoute


@admin.register(PageRoute)
class PageRouteAdmin(admin.ModelAdmin):
    list_display = (
        "path", "label", "is_group", "parent",
        "permission", "show_in_nav", "is_active", "sort_order", "source",
    )
    list_filter = ("is_group", "is_active", "show_in_nav", "source")
    search_fields = ("path", "label")
    list_select_related = ("parent", "permission__content_type")
    autocomplete_fields = ("parent",)
    fieldsets = (
        ("基础", {"fields": ("path", "label", "icon", "is_group")}),
        ("层级", {"fields": ("parent", "sort_order")}),
        ("权限/可见性", {"fields": ("permission", "show_in_nav", "is_active", "meta")}),
        ("来源", {"fields": ("source",)}),
    )
    readonly_fields = ("source",)
```

- [ ] **Step 2: 手动验证 admin 页面**

```bash
cd backend && uv run python manage.py runserver
```

打开 `http://localhost:8000/admin/page_perms/pageroute/`，确认：
- 列表中出现 `is_group`、`parent` 两列
- 左侧 filter 多了 "是分组" 筛选项
- 进入某条详情，分四个 fieldset 显示，`parent` 是 autocomplete 选择器

(无自动化测试 —  admin 配置是声明性的，价值有限；眼检即可。)

- [ ] **Step 3: Commit**

```bash
git add packages/django-page-perms/page_perms/admin.py
git commit -m "feat(page_perms): show parent/is_group in admin"
```

---

## Task 4: `sync_page_perms` 支持 `parent` + `is_group`

**Files:**
- Modify: `packages/django-page-perms/page_perms/management/commands/sync_page_perms.py:41-67` (`_sync_routes`)
- Test: `backend/tests/test_page_perms_sync.py`

- [ ] **Step 1: 写失败的测试**

追加到 `backend/tests/test_page_perms_sync.py`:

```python
class TestSyncHierarchy:
    def test_sync_creates_group_with_is_group(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {
                    "path": "#group:proj",
                    "label": "项目管理",
                    "icon": "i-heroicons-folder",
                    "is_group": True,
                    "sort_order": 10,
                },
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        group = PageRoute.objects.get(path="#group:proj")
        assert group.is_group is True
        assert group.label == "项目管理"

    def test_sync_links_leaf_to_parent(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "#group:proj", "label": "项目管理",
                 "is_group": True, "sort_order": 10},
                {"path": "/app/projects", "label": "项目列表",
                 "parent": "#group:proj", "sort_order": 11},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        leaf = PageRoute.objects.get(path="/app/projects")
        assert leaf.parent and leaf.parent.path == "#group:proj"

    def test_sync_handles_child_before_parent_in_json(self, settings):
        # Child 行在 parent 之前出现 —— 两遍 sync 必须能搞定
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/projects", "label": "项目列表",
                 "parent": "#group:proj", "sort_order": 11},
                {"path": "#group:proj", "label": "项目管理",
                 "is_group": True, "sort_order": 10},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        leaf = PageRoute.objects.get(path="/app/projects")
        assert leaf.parent and leaf.parent.path == "#group:proj"

    def test_sync_clears_parent_when_removed_from_seed(self, settings):
        # 先 sync 出 parent 关系
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "#group:proj", "label": "项目管理",
                 "is_group": True, "sort_order": 10},
                {"path": "/app/projects", "label": "项目列表",
                 "parent": "#group:proj", "sort_order": 11},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        # 再次 sync，叶子的 parent 字段被显式置空
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "#group:proj", "label": "项目管理",
                 "is_group": True, "sort_order": 10},
                {"path": "/app/projects", "label": "项目列表",
                 "parent": None, "sort_order": 11},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        leaf = PageRoute.objects.get(path="/app/projects")
        assert leaf.parent is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_page_perms_sync.py::TestSyncHierarchy -v
```
Expected: FAIL —  现有 `_sync_routes` 不认 `parent`/`is_group`。

- [ ] **Step 3: 改 `_sync_routes` 为两遍**

`packages/django-page-perms/page_perms/management/commands/sync_page_perms.py` 中 `_sync_routes` 方法替换为:

```python
def _sync_routes(self, seed_routes):
    self.stdout.write("Syncing page routes...")

    # Pass 1: upsert 所有行（不设 parent，避免 forward reference）
    for route_data in seed_routes:
        path = route_data["path"]
        perm_string = route_data.get("permission")
        permission = self._resolve_permission(perm_string) if perm_string else None

        defaults = {
            "label": route_data["label"],
            "icon": route_data.get("icon", ""),
            "permission": permission,
            "is_group": route_data.get("is_group", False),
            "show_in_nav": route_data.get("show_in_nav", True),
            "sort_order": route_data.get("sort_order", 0),
            "is_active": route_data.get("is_active", True),
            "meta": route_data.get("meta", {}),
            "source": route_data.get("source", "seed"),
        }

        route, created = PageRoute.objects.update_or_create(
            path=path, defaults=defaults
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action}: {path}")

    # Pass 2: 设 parent，等所有行都已存在
    for route_data in seed_routes:
        path = route_data["path"]
        parent_path = route_data.get("parent")
        if parent_path:
            try:
                parent = PageRoute.objects.get(path=parent_path)
            except PageRoute.DoesNotExist:
                self.stderr.write(
                    f"  Warning: parent '{parent_path}' not found for '{path}', skipping link"
                )
                continue
            PageRoute.objects.filter(path=path).update(parent=parent)
        elif "parent" in route_data:
            # 显式 null —— 清掉 parent
            PageRoute.objects.filter(path=path).update(parent=None)

    self.stdout.write(self.style.SUCCESS(f"  Synced {len(seed_routes)} routes"))
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_page_perms_sync.py -v
```
Expected: 新 class 和老的 7 个用例都 PASS。

- [ ] **Step 5: Commit**

```bash
git add packages/django-page-perms/page_perms/management/commands/sync_page_perms.py \
        backend/tests/test_page_perms_sync.py
git commit -m "feat(page_perms): sync_page_perms understands parent + is_group"
```

---

## Task 5: `dump_page_perms` 输出 `parent` + `is_group`

**Files:**
- Modify: `packages/django-page-perms/page_perms/management/commands/dump_page_perms.py:75-96` (`_dump_routes`)
- Test: 新增 `backend/tests/test_page_perms_dump.py`

- [ ] **Step 1: 写失败的测试**

新建 `backend/tests/test_page_perms_dump.py`:

```python
import json
import tempfile
from pathlib import Path

import pytest
from django.core.management import call_command

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestDumpRoundTrip:
    def test_dump_includes_parent_and_is_group(self, tmp_path):
        group = PageRoute.objects.create(
            path="#group:proj", label="项目管理",
            is_group=True, sort_order=10, source="manual",
        )
        PageRoute.objects.create(
            path="/app/projects", label="项目列表",
            parent=group, sort_order=11, source="manual",
        )
        out = tmp_path / "out.json"
        call_command("dump_page_perms", output=str(out))
        data = json.loads(out.read_text())
        rows = {r["path"]: r for r in data["seed_routes"]}
        assert rows["#group:proj"]["is_group"] is True
        assert rows["#group:proj"]["parent"] is None
        assert rows["/app/projects"]["is_group"] is False
        assert rows["/app/projects"]["parent"] == "#group:proj"

    def test_round_trip_preserves_hierarchy(self, tmp_path, settings):
        group = PageRoute.objects.create(
            path="#group:proj", label="项目管理",
            is_group=True, sort_order=10, source="seed",
        )
        PageRoute.objects.create(
            path="/app/projects", label="项目列表",
            parent=group, sort_order=11, source="seed",
        )
        out = tmp_path / "out.json"
        call_command("dump_page_perms", output=str(out))

        # 清库，再从 dump 出来的 JSON 跑 sync
        PageRoute.objects.all().delete()
        settings.PAGE_PERMS_SEED_FILE = str(out)
        call_command("sync_page_perms")

        leaf = PageRoute.objects.get(path="/app/projects")
        assert leaf.parent and leaf.parent.path == "#group:proj"
        assert leaf.parent.is_group is True
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_page_perms_dump.py -v
```
Expected: FAIL — dump 输出里没有 `parent`/`is_group`。

- [ ] **Step 3: 改 `_dump_routes`**

`packages/django-page-perms/page_perms/management/commands/dump_page_perms.py` 中 `_dump_routes` 替换为:

```python
def _dump_routes(self):
    rows = []
    qs = PageRoute.objects.select_related(
        "permission__content_type", "parent"
    ).order_by("sort_order", "pk")
    for route in qs:
        perm = route.permission
        perm_ref = (
            f"{perm.content_type.app_label}.{perm.codename}" if perm else None
        )
        rows.append({
            "path": route.path,
            "label": route.label,
            "icon": route.icon,
            "permission": perm_ref,
            "parent": route.parent.path if route.parent_id else None,
            "is_group": route.is_group,
            "sort_order": route.sort_order,
            "show_in_nav": route.show_in_nav,
            "is_active": route.is_active,
            "meta": route.meta or {},
            "source": route.source,
        })
    return rows
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_page_perms_dump.py -v
```
Expected: 两个用例 PASS。

- [ ] **Step 5: Commit**

```bash
git add packages/django-page-perms/page_perms/management/commands/dump_page_perms.py \
        backend/tests/test_page_perms_dump.py
git commit -m "feat(page_perms): dump_page_perms emits parent + is_group"
```

---

## Task 6: 重写 `backend/page_perms.json` 加入 4 个分组

**Files:**
- Modify: `backend/page_perms.json`

> 分组层级要与前端旧的 `GROUP_DEFS` 对齐：
> - 项目管理: `/app/projects`、`/app/repos`
> - 团队效能: `/app/ai/team-analysis`、`/app/ai/plans`
> - 用户管理: `/app/users`、`/app/kpi`、`/app/permissions`
> - 系统管理: `/app/settings/kpi-scoring`、`/app/settings/backups`、`/app/api-docs`、`/app/about`
>
> 其他根级条目 (roadmap、issues、dashboard、ai-insights、ai/my-plan、notifications/manage) 保持顶级，不挂分组。

- [ ] **Step 1: 编辑 JSON**

把 `backend/page_perms.json` 的 `seed_routes` 数组替换为 (其余 `seed_groups` 等键保持不变):

```json
"seed_routes": [
  {
    "path": "/app/roadmap",
    "label": "产品路线图",
    "icon": "i-heroicons-map",
    "permission": null,
    "parent": null,
    "is_group": false,
    "sort_order": 0,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/issues",
    "label": "问题跟踪",
    "icon": "i-heroicons-bug-ant",
    "permission": "issues.view_issue",
    "parent": null,
    "is_group": false,
    "sort_order": 1,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/dashboard",
    "label": "项目概览",
    "icon": "i-heroicons-squares-2x2",
    "permission": "issues.view_dashboard",
    "parent": null,
    "is_group": false,
    "sort_order": 2,
    "show_in_nav": true,
    "is_active": false,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "#group:project-mgmt",
    "label": "项目管理",
    "icon": "i-heroicons-folder",
    "permission": null,
    "parent": null,
    "is_group": true,
    "sort_order": 3,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/projects",
    "label": "项目管理",
    "icon": "i-heroicons-folder-open",
    "permission": "projects.view_project",
    "parent": "#group:project-mgmt",
    "is_group": false,
    "sort_order": 4,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/repos",
    "label": "GitHub 仓库",
    "icon": "i-heroicons-code-bracket",
    "permission": "repos.view_repo",
    "parent": "#group:project-mgmt",
    "is_group": false,
    "sort_order": 5,
    "show_in_nav": true,
    "is_active": true,
    "meta": { "serviceKey": "github" },
    "source": "seed"
  },
  {
    "path": "/app/ai-insights",
    "label": "AI 洞察",
    "icon": "i-heroicons-cpu-chip",
    "permission": "ai.view_analysis",
    "parent": null,
    "is_group": false,
    "sort_order": 6,
    "show_in_nav": false,
    "is_active": false,
    "meta": { "serviceKey": "ai" },
    "source": "seed"
  },
  {
    "path": "#group:team-perf",
    "label": "团队效能",
    "icon": "i-heroicons-chart-bar",
    "permission": null,
    "parent": null,
    "is_group": true,
    "sort_order": 7,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/ai/team-analysis",
    "label": "团队分析",
    "icon": "i-heroicons-cpu-chip",
    "permission": "ai.view_analysis",
    "parent": "#group:team-perf",
    "is_group": false,
    "sort_order": 8,
    "show_in_nav": true,
    "is_active": true,
    "meta": { "adminOnly": true, "serviceKey": "ai" },
    "source": "seed"
  },
  {
    "path": "/app/ai/my-plan",
    "label": "我的提升计划",
    "icon": "i-heroicons-clipboard-document-check",
    "permission": null,
    "parent": null,
    "is_group": false,
    "sort_order": 9,
    "show_in_nav": false,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/ai/plans",
    "label": "团队计划管理",
    "icon": "i-heroicons-clipboard-document-list",
    "permission": "kpi.change_improvementplan",
    "parent": "#group:team-perf",
    "is_group": false,
    "sort_order": 10,
    "show_in_nav": true,
    "is_active": true,
    "meta": { "adminOnly": true },
    "source": "seed"
  },
  {
    "path": "#group:user-mgmt",
    "label": "用户管理",
    "icon": "i-heroicons-users",
    "permission": null,
    "parent": null,
    "is_group": true,
    "sort_order": 11,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/users",
    "label": "用户管理",
    "icon": "i-heroicons-users",
    "permission": "users.view_user",
    "parent": "#group:user-mgmt",
    "is_group": false,
    "sort_order": 12,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/kpi",
    "label": "KPI 分析",
    "icon": "i-heroicons-chart-bar-square",
    "permission": "kpi.view_kpisnapshot",
    "parent": "#group:user-mgmt",
    "is_group": false,
    "sort_order": 13,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/notifications/manage",
    "label": "通知管理",
    "icon": "i-heroicons-bell-alert",
    "permission": "notifications.view_notification",
    "parent": null,
    "is_group": false,
    "sort_order": 14,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "#group:system",
    "label": "系统管理",
    "icon": "i-heroicons-cog-6-tooth",
    "permission": null,
    "parent": null,
    "is_group": true,
    "sort_order": 15,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/settings/kpi-scoring",
    "label": "KPI 评分规则",
    "icon": "i-heroicons-adjustments-horizontal",
    "permission": null,
    "parent": "#group:system",
    "is_group": false,
    "sort_order": 16,
    "show_in_nav": true,
    "is_active": true,
    "meta": { "superuserOnly": true },
    "source": "seed"
  },
  {
    "path": "/app/settings/backups",
    "label": "数据库备份",
    "icon": "i-heroicons-circle-stack",
    "permission": null,
    "parent": "#group:system",
    "is_group": false,
    "sort_order": 17,
    "show_in_nav": true,
    "is_active": true,
    "meta": { "superuserOnly": true },
    "source": "seed"
  },
  {
    "path": "/app/permissions",
    "label": "权限管理",
    "icon": "i-heroicons-shield-check",
    "permission": null,
    "parent": "#group:user-mgmt",
    "is_group": false,
    "sort_order": 18,
    "show_in_nav": true,
    "is_active": true,
    "meta": { "superuserOnly": true },
    "source": "seed"
  },
  {
    "path": "/app/api-docs",
    "label": "接口文档",
    "icon": "i-heroicons-document-text",
    "permission": "settings.view_externalapikey",
    "parent": "#group:system",
    "is_group": false,
    "sort_order": 19,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  },
  {
    "path": "/app/about",
    "label": "关于系统",
    "icon": "i-heroicons-information-circle",
    "permission": null,
    "parent": "#group:system",
    "is_group": false,
    "sort_order": 20,
    "show_in_nav": true,
    "is_active": true,
    "meta": {},
    "source": "seed"
  }
],
```

- [ ] **Step 2: Sync 进 DB 验证**

```bash
cd backend && uv run python manage.py sync_page_perms
```

确认输出列出全部 21 条路由 (含 4 个 `#group:*`)，无 warning。

- [ ] **Step 3: 跑 `test_roadmap_route_seeded_from_production_config` 等 prod 配置依赖测试**

```bash
cd backend && uv run pytest tests/test_page_perms_sync.py -v
```
Expected: 全部 PASS，特别确认 `test_roadmap_route_seeded_from_production_config` 仍然通过。

- [ ] **Step 4: Commit**

```bash
git add backend/page_perms.json
git commit -m "feat(page_perms): seed groups for project/team/user/system menus"
```

---

## Task 7: 前端 `usePagePerms` 暴露 `parent` + `is_group`

**Files:**
- Modify: `frontend/app/composables/usePagePerms.ts`

- [ ] **Step 1: 改接口定义**

`frontend/app/composables/usePagePerms.ts` 中 `PageRouteConfig` 接口替换为:

```ts
export interface PageRouteConfig {
  id: number
  path: string
  label: string
  icon: string
  permission: string | null
  parent: string | null
  is_group: boolean
  show_in_nav: boolean
  sort_order: number
  is_active: boolean
  meta: Record<string, any>
}
```

`routePermissions` 计算属性不需要改 (分组行 `permission` 为 null，自然被跳过)。

- [ ] **Step 2: 类型检查**

```bash
cd frontend && npx nuxi typecheck
```
Expected: 0 errors。如果 `useNavigation.ts` 报错，是预期的，Task 8 会改。

- [ ] **Step 3: Commit**

```bash
git add frontend/app/composables/usePagePerms.ts
git commit -m "feat(usePagePerms): include parent + is_group fields"
```

---

## Task 8: 前端 `useNavigation` 改为按 `parent` 建树，删除 `GROUP_DEFS`

**Files:**
- Modify: `frontend/app/composables/useNavigation.ts`

- [ ] **Step 1: 全量替换 `useNavigation.ts`**

```ts
export interface NavItem {
  label: string
  icon: string
  to?: string
  permission?: string
  meta?: Record<string, any>
}

export interface NavGroup {
  label: string
  icon: string
  children: NavItem[]
}

export type NavEntry = NavItem | NavGroup

export function isNavGroup(entry: NavEntry): entry is NavGroup {
  return 'children' in entry
}

export const useNavigation = () => {
  const { can, hasGroup, user } = useAuth()
  const { routes, loaded } = usePagePerms()
  const isAdmin = computed(() => user.value?.is_superuser || hasGroup('管理员'))

  const homeItem: NavItem = { label: '工作台', icon: 'i-heroicons-home', to: '/app/home' }

  // navItems: 所有可见叶子，仅按 show_in_nav / is_active 过滤
  // (breadcrumbs 消费这个 list，需要 resolve 跨角色的 label，所以不在这里做用户级 filter)
  const navItems = computed<NavItem[]>(() => {
    if (!loaded.value) return []
    return routes.value
      .filter(r => !r.is_group && r.show_in_nav && r.is_active)
      .map(r => ({
        label: r.label,
        icon: r.icon,
        to: r.path,
        permission: r.permission ?? undefined,
        meta: r.meta,
      }))
  })

  // filteredNavItems: navItems + 用户级 filter —— AppBottomTabBar / forbidden 在用
  const filteredNavItems = computed(() => {
    if (!user.value) return []
    const items = navItems.value.filter(item => {
      if (item.meta?.superuserOnly && !user.value?.is_superuser) return false
      if (item.meta?.adminOnly && !isAdmin.value) return false
      if (item.permission && !can(item.permission)) return false
      return true
    })
    return [homeItem, ...items]
  })

  // 按 DB 里 parent 字段建两级树
  const groupedNavItems = computed<NavEntry[]>(() => {
    if (!loaded.value || !user.value) return [homeItem]

    const visibleLeavesByParent = new Map<string, NavItem[]>()
    const topLevelLeaves: NavItem[] = []
    const leafByPath = new Map<string, ReturnType<typeof routes.value[number]>>()
    for (const r of routes.value) leafByPath.set(r.path, r)

    // 用同样的可见性规则过滤叶子
    const canShowLeaf = (r: typeof routes.value[number]) => {
      if (r.is_group) return false
      if (!r.show_in_nav || !r.is_active) return false
      if (r.meta?.superuserOnly && !user.value?.is_superuser) return false
      if (r.meta?.adminOnly && !isAdmin.value) return false
      if (r.permission && !can(r.permission)) return false
      return true
    }

    const toNavItem = (r: typeof routes.value[number]): NavItem => ({
      label: r.label,
      icon: r.icon,
      to: r.path,
      permission: r.permission ?? undefined,
      meta: r.meta,
    })

    for (const r of routes.value) {
      if (!canShowLeaf(r)) continue
      if (r.parent) {
        const arr = visibleLeavesByParent.get(r.parent) ?? []
        arr.push(toNavItem(r))
        visibleLeavesByParent.set(r.parent, arr)
      } else {
        topLevelLeaves.push(toNavItem(r))
      }
    }

    // 遍历 routes 顺序（已按 sort_order 来自后端）合成最终列表
    const result: NavEntry[] = [homeItem]
    const emittedGroups = new Set<string>()

    for (const r of routes.value) {
      if (r.is_group) {
        if (emittedGroups.has(r.path)) continue
        if (!r.show_in_nav || !r.is_active) continue
        const children = visibleLeavesByParent.get(r.path) ?? []
        if (children.length === 0) continue  // 空分组不显示
        result.push({ label: r.label, icon: r.icon, children })
        emittedGroups.add(r.path)
      } else if (!r.parent && canShowLeaf(r)) {
        result.push(toNavItem(r))
      }
    }

    return result
  })

  const route = useRoute()
  const currentPath = computed(() => route.path)

  // 不在 navItems 中的独立页面
  const standalonePages: Record<string, string> = {
    '/app/profile': '个人资料',
    '/app/notifications': '通知中心',
  }

  const breadcrumbs = computed(() => {
    const path = route.path
    const crumbs: { label: string; to?: string }[] = [{ label: '首页', to: '/app/home' }]

    const standaloneName = standalonePages[path]
    if (standaloneName) {
      return [{ label: standaloneName }]
    }

    for (const item of navItems.value) {
      if (item.to === path) {
        crumbs.push({ label: item.label })
        return crumbs
      }
    }

    for (const item of navItems.value) {
      if (item.to && path.startsWith(item.to + '/')) {
        crumbs.push({ label: item.label, to: item.to })
        crumbs.push({ label: '详情' })
        return crumbs
      }
    }

    return crumbs
  })

  return { navItems, filteredNavItems, groupedNavItems, currentPath, breadcrumbs }
}
```

- [ ] **Step 2: 类型检查**

```bash
cd frontend && npx nuxi typecheck
```
Expected: 0 errors。

- [ ] **Step 3: 启动前端 + 浏览器验证**

```bash
cd frontend && npm run dev
```

打开 `http://localhost:3004/app/home`，登录后用 Chrome DevTools (或眼检) 确认：
- 侧边栏顺序: 工作台 / 产品路线图 / 问题跟踪 / 项目管理(可展开:项目/仓库) / 团队效能(团队分析/团队计划管理) / 用户管理(用户/KPI/权限管理) / 通知管理 / 系统管理(KPI评分/数据库备份/接口文档/关于系统)
- 点开当前路径所在的分组应该自动展开（`AppSidebar.vue` 的 watch 没改，应该自动生效）
- 退出登录回到登录页，再用一个非管理员账号登录，确认 `adminOnly` / `superuserOnly` 标记的路由被隐藏
- 路线图（无权限）对所有人可见

- [ ] **Step 4: Commit**

```bash
git add frontend/app/composables/useNavigation.ts
git commit -m "feat(useNavigation): build menu hierarchy from PageRoute.parent (drop GROUP_DEFS)"
```

---

## Task 9: 加防护测试 —— 阻止三级嵌套

**Files:**
- Modify: `packages/django-page-perms/page_perms/models.py` (clean 方法)
- Test: `backend/tests/test_page_perms_safety.py`

> 我们刻意只支持两级（分组 → 叶子）。三级嵌套既无 UI 支撑也是未来负担。在模型层 `clean()` 加约束。

- [ ] **Step 1: 写失败的测试**

追加到 `backend/tests/test_page_perms_safety.py`:

```python
from django.core.exceptions import ValidationError

class TestHierarchyDepthGuard:
    def test_parent_cannot_have_parent(self):
        from page_perms.models import PageRoute
        a = PageRoute.objects.create(path="#group:a", label="A", is_group=True)
        b = PageRoute.objects.create(path="#group:b", label="B", is_group=True, parent=a)
        # b 已挂在 a 下面 —— 不允许再当某个 c 的 parent
        c = PageRoute(path="/app/c", label="C", parent=b)
        with pytest.raises(ValidationError):
            c.full_clean()

    def test_leaf_cannot_become_parent(self):
        from page_perms.models import PageRoute
        leaf = PageRoute.objects.create(path="/app/leaf", label="Leaf")
        # 叶子不能当父
        c = PageRoute(path="/app/c", label="C", parent=leaf)
        with pytest.raises(ValidationError):
            c.full_clean()

    def test_route_cannot_be_its_own_parent(self):
        from page_perms.models import PageRoute
        g = PageRoute.objects.create(path="#group:g", label="G", is_group=True)
        g.parent = g
        with pytest.raises(ValidationError):
            g.full_clean()
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd backend && uv run pytest tests/test_page_perms_safety.py::TestHierarchyDepthGuard -v
```
Expected: FAIL — 没有 clean 逻辑。

- [ ] **Step 3: 给 model 加 `clean`**

在 `packages/django-page-perms/page_perms/models.py` 的 `PageRoute` 类里追加:

```python
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError({"parent": "Route cannot be its own parent."})
        if self.parent:
            if not self.parent.is_group:
                raise ValidationError({"parent": "Parent must be a group row (is_group=True)."})
            if self.parent.parent_id:
                raise ValidationError({"parent": "Only one level of nesting is supported."})
```

注意：admin (Task 3) 走 ModelForm 默认会调用 `full_clean()`，所以会拦下违规录入。`sync_page_perms` 和 DRF 不会自动跑 `clean` —— 它们的不变量靠 seed JSON / API 调用方保证 (前者来自我们写的 JSON 文件，后者 Task 2 已经校验 parent 路径存在)。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_page_perms_safety.py -v
```
Expected: 新 class + 原有 safety 测试都 PASS。

- [ ] **Step 5: Commit**

```bash
git add packages/django-page-perms/page_perms/models.py \
        backend/tests/test_page_perms_safety.py
git commit -m "feat(page_perms): enforce single-level nesting in clean()"
```

---

## Task 10: 跑完整测试 + 手测 + 最终 commit/push 前的清单

**Files:** (无新增；这是 verification step)

- [ ] **Step 1: 后端全量测试**

```bash
cd backend && uv run pytest
```
Expected: 全部 PASS。

- [ ] **Step 2: 前端 typecheck + build**

```bash
cd frontend && npx nuxi typecheck && npm run build
```
Expected: 0 errors，build 成功。

- [ ] **Step 3: 浏览器手测清单**

启动后端 (`uv run python manage.py runserver`) + 前端 (`npm run dev`)，按以下清单验证:

1. **超级管理员视角** (admin)
   - 侧边栏顺序符合 Task 8 验证步骤里描述的层级
   - 点开"系统管理"分组，能看到 4 个子项；任意点击一个，分组保持展开、子项高亮
   - 收起/展开侧边栏（点头部那个按钮）正常
2. **普通开发者视角** (没有 superuser、不在管理员组)
   - "系统管理"分组消失 (没有任何子项可见)
   - "团队效能"分组只显示有权限的子项 (`adminOnly` 的 `团队分析`、`团队计划管理` 应隐藏 → 分组应为空 → 整个分组隐藏)
   - "用户管理"分组里 `权限管理`（superuserOnly）应消失
3. **Django admin 后台** (`http://localhost:8000/admin/page_perms/pageroute/`)
   - 列表中 `is_group=True` 的 4 行可以用左侧 filter 单独查看
   - 编辑某个叶子，能用 autocomplete 改它的 parent
   - 尝试把某叶子的 parent 指向另一个叶子，提交时 form 报"Parent must be a group row"

- [ ] **Step 4: dump → sync round-trip 完整性**

```bash
cd backend && uv run python manage.py dump_page_perms --output /tmp/dumped.json
diff <(jq -S . backend/page_perms.json) <(jq -S . /tmp/dumped.json)
```
Expected: 只有可忽略的字段顺序差异，无语义差异。如果有差异，需要核对哪个 source-of-truth 走偏。

- [ ] **Step 5: 没有 commit 漏网**

```bash
git status
```
Expected: working tree clean (除非有故意保留的本地改动)。

- [ ] **Step 6: 通知用户完成**

到这一步整套改动落地。提醒用户后续运维注意:
- 改动菜单时直接改 `backend/page_perms.json` 或 admin 后台 → 跑 `sync_page_perms`
- 想新增一级分组就在 JSON 加一行 `is_group: true` 的占位 `#group:xxx`
- 三级嵌套被禁止；要做的话需要先放开 Task 9 的 `clean` 校验 + 改前端 `groupedNavItems` 的递归
