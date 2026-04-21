# Improvement Plan Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a monthly personal improvement plan system with AI-generated action items, manager review workflow, employee execution tracking, and scoring.

**Architecture:** New models (ImprovementPlan, ActionItem, ActionItemComment) in the existing `kpi` app. New API endpoints under `/api/kpi/plans/`. Navigation restructured: "AI 洞察" → "AI 分析" group containing 团队分析 + 我的提升计划 + 团队计划管理. Plan generator creates structured action items from KPI gap analysis.

**Tech Stack:** Django REST Framework, Nuxt 4 (Vue 3), PostgreSQL JSONField, MinIO file uploads, Celery beat

---

## File Structure

### Backend (new files)
- `backend/apps/kpi/models.py` — add ImprovementPlan, ActionItem, ActionItemComment models
- `backend/apps/kpi/plan_generator.py` — AI draft generation engine (KPI gap → action items)
- `backend/apps/kpi/plan_views.py` — all plan/action-item/comment API views
- `backend/apps/kpi/plan_serializers.py` — DRF serializers for plan models
- `backend/apps/kpi/migrations/0004_improvement_plan.py` — auto-generated migration

### Backend (modified files)
- `backend/apps/kpi/urls.py` — add plan routes
- `backend/apps/kpi/tasks.py` — add monthly plan generation task
- `backend/config/settings.py` — update PAGE_PERMS routes and groups
- `backend/tests/factories.py` — add ImprovementPlanFactory, ActionItemFactory, ActionItemCommentFactory
- `backend/tests/test_plan_api.py` — new test file for plan endpoints

### Frontend (new files)
- `frontend/app/pages/app/ai/team-analysis.vue` — migrated from ai-insights.vue
- `frontend/app/pages/app/ai/my-plan.vue` — employee plan view
- `frontend/app/pages/app/ai/plans.vue` — manager team plans list
- `frontend/app/pages/app/ai/plans/[id].vue` — manager plan edit/review page

### Frontend (modified files)
- `frontend/app/composables/useNavigation.ts` — add "AI 分析" group
- `frontend/app/pages/app/home.vue` — add improvement plan card
- `frontend/app/pages/app/ai-insights.vue` — delete (replaced by team-analysis.vue)

---

## Task 1: Models & Migration

**Files:**
- Modify: `backend/apps/kpi/models.py`
- Create: `backend/apps/kpi/migrations/0004_improvement_plan.py` (auto-generated)
- Modify: `backend/tests/factories.py`
- Create: `backend/tests/test_plan_models.py`

- [ ] **Step 1: Write model tests**

Create `backend/tests/test_plan_models.py`:

```python
import pytest
from django.utils import timezone
from tests.factories import UserFactory, ImprovementPlanFactory, ActionItemFactory

pytestmark = pytest.mark.django_db


class TestImprovementPlan:
    def test_create_plan(self):
        plan = ImprovementPlanFactory()
        assert plan.status == "draft"
        assert plan.period  # e.g. "2026-04"
        assert plan.user is not None

    def test_unique_user_period(self):
        plan = ImprovementPlanFactory(period="2026-04")
        with pytest.raises(Exception):
            ImprovementPlanFactory(user=plan.user, period="2026-04")

    def test_plan_str(self):
        plan = ImprovementPlanFactory()
        assert plan.user.name in str(plan)
        assert plan.period in str(plan)


class TestActionItem:
    def test_create_action_item(self):
        item = ActionItemFactory()
        assert item.status == "pending"
        assert item.points > 0
        assert item.plan is not None

    def test_earned_points_verified(self):
        item = ActionItemFactory(status="verified", points=100, quality_factor=1.2)
        assert item.earned_points == 120

    def test_earned_points_not_verified(self):
        item = ActionItemFactory(status="pending", points=100)
        assert item.earned_points == 0

    def test_status_choices(self):
        for status in ("pending", "in_progress", "submitted", "verified", "not_achieved"):
            item = ActionItemFactory(status=status)
            assert item.status == status
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_plan_models.py -v`
Expected: ImportError (factories don't exist yet)

- [ ] **Step 3: Add models to kpi/models.py**

Append to `backend/apps/kpi/models.py` after the KPISnapshot class:

```python
# ---------------------------------------------------------------------------
# 提升计划
# ---------------------------------------------------------------------------

class ImprovementPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草案"
        PUBLISHED = "published", "已发布"
        ARCHIVED = "archived", "已归档"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="improvement_plans", verbose_name="员工",
    )
    period = models.CharField(max_length=7, verbose_name="月度周期", help_text="格式: 2026-04")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, verbose_name="状态")
    source_kpi_scores = models.JSONField(default=dict, verbose_name="KPI 评分快照")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="创建人",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="审核人",
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="发布时间")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="归档时间")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "提升计划"
        verbose_name_plural = "提升计划"
        unique_together = ("user", "period")
        ordering = ["-period", "-created_at"]
        permissions = [
            ("view_own_plan", "Can view own improvement plan"),
        ]

    def __str__(self):
        return f"{self.user.name} | {self.period}"


class ActionItem(models.Model):
    class Source(models.TextChoices):
        AI = "ai_generated", "AI 生成"
        MANAGER = "manager_added", "管理员添加"

    class Priority(models.TextChoices):
        HIGH = "high", "高"
        MEDIUM = "medium", "中"
        LOW = "low", "低"

    class Status(models.TextChoices):
        PENDING = "pending", "待执行"
        IN_PROGRESS = "in_progress", "进行中"
        SUBMITTED = "submitted", "已提交"
        VERIFIED = "verified", "已验收"
        NOT_ACHIEVED = "not_achieved", "未达成"

    QUALITY_FACTORS = [("0.50", "0.5"), ("0.80", "0.8"), ("1.00", "1.0"), ("1.20", "1.2")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        ImprovementPlan, on_delete=models.CASCADE,
        related_name="action_items", verbose_name="所属计划",
    )
    source = models.CharField(max_length=15, choices=Source.choices, default=Source.MANAGER)
    dimension = models.CharField(max_length=20, default="general", verbose_name="KPI 维度")
    title = models.CharField(max_length=200, verbose_name="标题")
    description = models.TextField(blank=True, default="", verbose_name="描述")
    measurable_target = models.CharField(max_length=200, blank=True, default="", verbose_name="可量化目标")
    points = models.PositiveIntegerField(default=10, verbose_name="分值")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    quality_factor = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, verbose_name="完成质量系数")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "行动项"
        verbose_name_plural = "行动项"
        ordering = ["sort_order", "-priority", "created_at"]

    def __str__(self):
        return self.title

    @property
    def earned_points(self) -> int:
        if self.status == self.Status.VERIFIED and self.quality_factor:
            return round(self.points * float(self.quality_factor))
        return 0


class ActionItemComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_item = models.ForeignKey(
        ActionItem, on_delete=models.CASCADE,
        related_name="comments", verbose_name="行动项",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="+", verbose_name="作者",
    )
    content = models.TextField(verbose_name="内容")
    attachment_url = models.URLField(blank=True, default="", verbose_name="附件 URL")
    attachment_key = models.CharField(max_length=200, blank=True, default="", verbose_name="附件 Key")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "行动项评论"
        verbose_name_plural = "行动项评论"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author.name}: {self.content[:30]}"
```

- [ ] **Step 4: Add factories**

Append to `backend/tests/factories.py`:

```python
from apps.kpi.models import ImprovementPlan, ActionItem, ActionItemComment


class ImprovementPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImprovementPlan

    user = factory.SubFactory(UserFactory)
    period = factory.LazyFunction(lambda: tz.now().strftime("%Y-%m"))
    status = "draft"
    source_kpi_scores = factory.LazyFunction(lambda: {"efficiency": 70, "output": 75, "overall": 72})
    computed_at = factory.LazyFunction(tz.now)


class ActionItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ActionItem

    plan = factory.SubFactory(ImprovementPlanFactory)
    source = "ai_generated"
    dimension = "efficiency"
    title = factory.Sequence(lambda n: f"改进行动 {n}")
    description = "具体改进建议"
    measurable_target = "达到目标值"
    points = 20
    priority = "medium"
    status = "pending"


class ActionItemCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ActionItemComment

    action_item = factory.SubFactory(ActionItemFactory)
    author = factory.SubFactory(UserFactory)
    content = "完成情况说明"
```

- [ ] **Step 5: Generate and apply migration**

Run:
```bash
cd backend
uv run python manage.py makemigrations kpi --name improvement_plan
uv run python manage.py migrate kpi
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_plan_models.py -v`
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/kpi/models.py backend/apps/kpi/migrations/0004_*.py backend/tests/factories.py backend/tests/test_plan_models.py
git commit -m "feat(kpi): add ImprovementPlan, ActionItem, ActionItemComment models"
```

---

## Task 2: Plan Generator Engine

**Files:**
- Create: `backend/apps/kpi/plan_generator.py`
- Create: `backend/tests/test_plan_generator.py`

- [ ] **Step 1: Write generator tests**

Create `backend/tests/test_plan_generator.py`:

```python
import pytest
from tests.factories import UserFactory
from apps.kpi.plan_generator import generate_action_items

pytestmark = pytest.mark.django_db


def _sample_scores(**overrides):
    base = {"efficiency": 70, "output": 75, "quality": 80, "capability": 65, "growth": 50, "overall": 72}
    base.update(overrides)
    return base


def _sample_issue_metrics(**overrides):
    base = {
        "assigned_count": 10, "resolved_count": 8, "resolution_rate": 0.8,
        "avg_resolution_hours": 12.0, "daily_resolved_avg": 1.5,
        "weighted_issue_value": 30, "as_helper_count": 0,
        "priority_breakdown": {"P0": {"assigned": 2, "resolved": 1, "avg_hours": 8}},
    }
    base.update(overrides)
    return base


def _sample_commit_metrics(**overrides):
    base = {
        "total_commits": 50, "additions": 3000, "deletions": 1000,
        "self_introduced_bug_rate": 0.05, "churn_rate": 0.1,
        "conventional_ratio": 0.7, "avg_commit_size": 100,
        "repo_coverage": [{"repo_name": "repo1"}],
        "file_type_breadth": 5,
    }
    base.update(overrides)
    return base


class TestGenerateActionItems:
    def test_generates_items_for_low_efficiency(self):
        scores = _sample_scores(efficiency=40)
        team_avgs = {"efficiency": 70, "output": 70, "quality": 70, "capability": 70}
        items = generate_action_items(scores, _sample_issue_metrics(), _sample_commit_metrics(), team_avgs)
        dims = [i["dimension"] for i in items]
        assert "efficiency" in dims

    def test_generates_items_for_high_bug_rate(self):
        cm = _sample_commit_metrics(self_introduced_bug_rate=0.15)
        items = generate_action_items(_sample_scores(), _sample_issue_metrics(), cm, {})
        dims = [i["dimension"] for i in items]
        assert "quality" in dims

    def test_max_8_items(self):
        scores = _sample_scores(efficiency=10, output=10, quality=10, capability=10)
        team_avgs = {"efficiency": 70, "output": 70, "quality": 70, "capability": 70}
        cm = _sample_commit_metrics(
            self_introduced_bug_rate=0.2, churn_rate=0.3,
            conventional_ratio=0.3, avg_commit_size=400,
        )
        im = _sample_issue_metrics(as_helper_count=0)
        items = generate_action_items(scores, im, cm, team_avgs)
        assert len(items) <= 8

    def test_returns_structured_items(self):
        items = generate_action_items(
            _sample_scores(efficiency=30),
            _sample_issue_metrics(),
            _sample_commit_metrics(),
            {"efficiency": 70},
        )
        assert len(items) > 0
        item = items[0]
        assert "title" in item
        assert "description" in item
        assert "measurable_target" in item
        assert "points" in item
        assert "priority" in item
        assert "dimension" in item

    def test_no_items_when_all_good(self):
        scores = _sample_scores(efficiency=90, output=90, quality=90, capability=90)
        cm = _sample_commit_metrics(
            self_introduced_bug_rate=0.02, churn_rate=0.05,
            conventional_ratio=0.9, avg_commit_size=80,
            repo_coverage=[{"repo_name": "r1"}, {"repo_name": "r2"}, {"repo_name": "r3"}],
        )
        im = _sample_issue_metrics(as_helper_count=5)
        items = generate_action_items(scores, im, cm, {"efficiency": 70, "output": 70})
        assert len(items) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_plan_generator.py -v`
Expected: ImportError

- [ ] **Step 3: Implement plan_generator.py**

Create `backend/apps/kpi/plan_generator.py`:

```python
"""
提升计划行动项生成引擎

根据 KPI 评分差距和指标短板，生成结构化的行动项。
"""

from __future__ import annotations

MAX_ITEMS = 8

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def generate_action_items(
    scores: dict,
    issue_metrics: dict,
    commit_metrics: dict,
    team_avgs: dict | None,
) -> list[dict]:
    """根据 KPI 数据生成结构化行动项列表。

    Returns
    -------
    list[dict]
        每项包含 dimension, title, description, measurable_target, points, priority, source
    """
    team_avgs = team_avgs or {}
    items: list[dict] = []
    im = issue_metrics
    cm = commit_metrics

    # 1) 效率低于团队均值
    team_eff = team_avgs.get("efficiency")
    if team_eff and scores.get("efficiency", 100) < team_eff:
        daily_avg = im.get("daily_resolved_avg", 0)
        target = round(daily_avg * 1.5, 1) if daily_avg > 0 else 2.0
        items.append({
            "dimension": "efficiency",
            "title": f"提高日均解决量至 {target} 个",
            "description": "关注问题分解和时间管理，优先处理高优先级问题",
            "measurable_target": f"日均解决 ≥ {target}",
            "points": 30,
            "priority": "high",
            "source": "ai_generated",
        })

    # 2) P0/P1 响应慢
    pb = im.get("priority_breakdown", {})
    p0_hours = pb.get("P0", {}).get("avg_hours", 0)
    p1_hours = pb.get("P1", {}).get("avg_hours", 0)
    max_p0p1 = max(p0_hours, p1_hours)
    if max_p0p1 > 24:
        items.append({
            "dimension": "efficiency",
            "title": "P0/P1 响应时间控制在 24h 内",
            "description": "建立紧急响应机制，P0 问题收到后立即处理",
            "measurable_target": "P0/P1 平均解决时间 < 24h",
            "points": 30,
            "priority": "high",
            "source": "ai_generated",
        })

    # 3) Bug 率过高
    bug_rate = cm.get("self_introduced_bug_rate", 0)
    if bug_rate > 0.1:
        pct = round(bug_rate * 100, 1)
        items.append({
            "dimension": "quality",
            "title": "自引 Bug 率降至 10% 以下",
            "description": f"当前 Bug 率 {pct}%，建议加强代码自测和 Code Review",
            "measurable_target": "自引 Bug 率 < 10%",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 4) Churn 率过高
    churn = cm.get("churn_rate", 0)
    if churn > 0.2:
        pct = round(churn * 100, 1)
        items.append({
            "dimension": "quality",
            "title": "代码 Churn 率控制在 20% 以下",
            "description": f"当前 Churn 率 {pct}%，建议加强需求理解和设计评审",
            "measurable_target": "Churn 率 < 20%",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 5) 规范提交率低
    conv = cm.get("conventional_ratio", 0)
    total_commits = cm.get("total_commits", 0)
    if total_commits > 0 and conv < 0.5:
        items.append({
            "dimension": "quality",
            "title": "Conventional Commits 比率提升至 50%",
            "description": f"当前规范提交率 {round(conv * 100)}%，使用 feat:/fix:/refactor: 等前缀",
            "measurable_target": "规范提交比率 ≥ 50%",
            "points": 10,
            "priority": "low",
            "source": "ai_generated",
        })

    # 6) 提交过大
    avg_size = cm.get("avg_commit_size", 0)
    if avg_size > 300:
        items.append({
            "dimension": "quality",
            "title": "单次提交控制在 150 行以内",
            "description": f"当前平均 {round(avg_size)} 行/次，建议拆分为更小的原子提交",
            "measurable_target": "平均提交大小 < 150 行",
            "points": 10,
            "priority": "low",
            "source": "ai_generated",
        })

    # 7) 仓库覆盖不足
    repo_count = len(cm.get("repo_coverage", []))
    if repo_count < 2:
        items.append({
            "dimension": "capability",
            "title": "参与至少 2 个仓库的开发",
            "description": "拓展技术广度，参与不同项目的开发",
            "measurable_target": "有提交的仓库数 ≥ 2",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 8) 无协助
    helper_count = im.get("as_helper_count", 0)
    if helper_count == 0:
        items.append({
            "dimension": "capability",
            "title": "本月协助处理至少 2 个他人问题",
            "description": "提升团队协作能力，主动协助同事解决问题",
            "measurable_target": "协助问题数 ≥ 2",
            "points": 20,
            "priority": "medium",
            "source": "ai_generated",
        })

    # 按优先级排序，截断至 MAX_ITEMS
    items.sort(key=lambda x: PRIORITY_ORDER.get(x["priority"], 99))
    return items[:MAX_ITEMS]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_plan_generator.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/kpi/plan_generator.py backend/tests/test_plan_generator.py
git commit -m "feat(kpi): add plan generator engine for AI action items"
```

---

## Task 3: Serializers

**Files:**
- Create: `backend/apps/kpi/plan_serializers.py`

- [ ] **Step 1: Create serializers**

Create `backend/apps/kpi/plan_serializers.py`:

```python
from rest_framework import serializers
from .models import ImprovementPlan, ActionItem, ActionItemComment


class ActionItemCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    author_avatar = serializers.CharField(source="author.avatar", default="", read_only=True)

    class Meta:
        model = ActionItemComment
        fields = [
            "id", "author", "author_name", "author_avatar",
            "content", "attachment_url", "created_at",
        ]
        read_only_fields = ["id", "author", "author_name", "author_avatar", "created_at"]


class ActionItemSerializer(serializers.ModelSerializer):
    earned_points = serializers.IntegerField(read_only=True)
    comments = ActionItemCommentSerializer(many=True, read_only=True)

    class Meta:
        model = ActionItem
        fields = [
            "id", "source", "dimension", "title", "description",
            "measurable_target", "points", "priority", "status",
            "quality_factor", "earned_points", "sort_order",
            "comments", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "source", "earned_points", "created_at", "updated_at"]


class ActionItemBriefSerializer(serializers.ModelSerializer):
    """行动项简要信息（用于计划列表和工作台）。"""
    earned_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = ActionItem
        fields = ["id", "title", "points", "priority", "status", "earned_points", "dimension"]


class PlanDetailSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_avatar = serializers.CharField(source="user.avatar", default="", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.name", default="", read_only=True)
    action_items = ActionItemSerializer(many=True, read_only=True)
    total_points = serializers.SerializerMethodField()
    earned_points = serializers.SerializerMethodField()

    class Meta:
        model = ImprovementPlan
        fields = [
            "id", "user", "user_name", "user_avatar", "period", "status",
            "source_kpi_scores", "reviewed_by", "reviewed_by_name",
            "published_at", "archived_at", "action_items",
            "total_points", "earned_points", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_total_points(self, obj):
        return sum(item.points for item in obj.action_items.all())

    def get_earned_points(self, obj):
        return sum(item.earned_points for item in obj.action_items.all())


class PlanListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_avatar = serializers.CharField(source="user.avatar", default="", read_only=True)
    item_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    earned_points = serializers.SerializerMethodField()

    class Meta:
        model = ImprovementPlan
        fields = [
            "id", "user", "user_name", "user_avatar", "period", "status",
            "item_count", "total_points", "earned_points",
            "published_at", "created_at",
        ]
        read_only_fields = fields

    def get_item_count(self, obj):
        return obj.action_items.count()

    def get_total_points(self, obj):
        return sum(item.points for item in obj.action_items.all())

    def get_earned_points(self, obj):
        return sum(item.earned_points for item in obj.action_items.all())
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/kpi/plan_serializers.py
git commit -m "feat(kpi): add plan serializers"
```

---

## Task 4: Plan API Views & Tests

**Files:**
- Create: `backend/apps/kpi/plan_views.py`
- Modify: `backend/apps/kpi/urls.py`
- Create: `backend/tests/test_plan_api.py`

- [ ] **Step 1: Write API tests**

Create `backend/tests/test_plan_api.py`:

```python
import pytest
from django.utils import timezone
from tests.factories import (
    UserFactory, ImprovementPlanFactory, ActionItemFactory,
    ActionItemCommentFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def manager_client(api_client):
    from django.contrib.auth.models import Group, Permission
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="管理员")
    group.permissions.set(
        Permission.objects.filter(
            content_type__app_label__in=["kpi", "ai"]
        )
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def employee_client(api_client):
    from django.contrib.auth.models import Group, Permission
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="开发者")
    group.permissions.set(
        Permission.objects.filter(codename__in=["view_own_plan", "view_own_kpi"])
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client, user


class TestPlanListAPI:
    def test_manager_sees_all_plans(self, manager_client):
        client, _ = manager_client
        ImprovementPlanFactory(period="2026-04")
        ImprovementPlanFactory(period="2026-04")
        resp = client.get("/api/kpi/plans/?period=2026-04")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_employee_cannot_list_all(self, employee_client):
        client, _ = employee_client
        resp = client.get("/api/kpi/plans/")
        assert resp.status_code == 403


class TestMyPlanAPI:
    def test_employee_sees_own_published_plan(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published", period="2026-04")
        ActionItemFactory(plan=plan, title="提高效率")
        resp = client.get("/api/kpi/plans/me/")
        assert resp.status_code == 200
        assert resp.data["current"] is not None
        assert resp.data["current"]["period"] == "2026-04"

    def test_employee_cannot_see_draft(self, employee_client):
        client, user = employee_client
        ImprovementPlanFactory(user=user, status="draft", period="2026-04")
        resp = client.get("/api/kpi/plans/me/")
        assert resp.data["current"] is None


class TestPlanDetailAPI:
    def test_manager_sees_plan_detail(self, manager_client):
        client, _ = manager_client
        plan = ImprovementPlanFactory()
        ActionItemFactory(plan=plan)
        resp = client.get(f"/api/kpi/plans/{plan.id}/")
        assert resp.status_code == 200
        assert len(resp.data["action_items"]) == 1


class TestPlanPublishAPI:
    def test_publish_plan(self, manager_client):
        client, manager = manager_client
        plan = ImprovementPlanFactory(status="draft")
        resp = client.post(f"/api/kpi/plans/{plan.id}/publish/")
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.status == "published"
        assert plan.reviewed_by == manager
        assert plan.published_at is not None


class TestPlanArchiveAPI:
    def test_archive_plan(self, manager_client):
        client, _ = manager_client
        plan = ImprovementPlanFactory(status="published")
        resp = client.post(f"/api/kpi/plans/{plan.id}/archive/")
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.status == "archived"


class TestActionItemStatusAPI:
    def test_employee_updates_own_item_status(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published")
        item = ActionItemFactory(plan=plan, status="pending")
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/status/",
            {"status": "in_progress"}, format="json"
        )
        assert resp.status_code == 200
        item.refresh_from_db()
        assert item.status == "in_progress"

    def test_employee_cannot_verify(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published")
        item = ActionItemFactory(plan=plan, status="submitted")
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/status/",
            {"status": "verified"}, format="json"
        )
        assert resp.status_code == 400


class TestActionItemVerifyAPI:
    def test_manager_verifies_item(self, manager_client):
        client, _ = manager_client
        item = ActionItemFactory(status="submitted", points=100)
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/verify/",
            {"status": "verified", "quality_factor": "1.20"}, format="json"
        )
        assert resp.status_code == 200
        item.refresh_from_db()
        assert item.status == "verified"
        assert float(item.quality_factor) == 1.2


class TestCommentAPI:
    def test_employee_adds_comment(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published")
        item = ActionItemFactory(plan=plan)
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/comments/",
            {"content": "已完成截图见附件"}, format="json"
        )
        assert resp.status_code == 201
        assert item.comments.count() == 1


class TestGeneratePlanAPI:
    def test_manager_generates_plan(self, manager_client):
        client, _ = manager_client
        user = UserFactory(is_active=True, is_bot=False)
        resp = client.post(
            "/api/kpi/plans/generate/",
            {"user_id": user.id}, format="json"
        )
        assert resp.status_code == 201
        assert resp.data["status"] == "draft"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_plan_api.py -v`
Expected: ImportError (views don't exist yet)

- [ ] **Step 3: Implement plan_views.py**

Create `backend/apps/kpi/plan_views.py`:

```python
"""
提升计划 API 视图
"""
from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions
from apps.tools.storage import upload_image
from .models import ImprovementPlan, ActionItem, ActionItemComment
from .plan_serializers import (
    PlanListSerializer, PlanDetailSerializer,
    ActionItemSerializer, ActionItemCommentSerializer,
)


class PlanListView(APIView):
    """GET /api/kpi/plans/ — 管理员查看团队计划列表。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def get(self, request):
        period = request.query_params.get("period", timezone.now().strftime("%Y-%m"))
        plans = (
            ImprovementPlan.objects.filter(period=period)
            .select_related("user", "reviewed_by")
            .prefetch_related("action_items")
            .order_by("user__name")
        )
        serializer = PlanListSerializer(plans, many=True)
        return Response(serializer.data)


class MyPlanView(APIView):
    """GET /api/kpi/plans/me/ — 员工查看自己的计划。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        current_period = now.strftime("%Y-%m")

        current = (
            ImprovementPlan.objects.filter(
                user=request.user,
                period=current_period,
                status__in=["published", "archived"],
            )
            .prefetch_related("action_items__comments")
            .select_related("reviewed_by")
            .first()
        )

        history = (
            ImprovementPlan.objects.filter(
                user=request.user,
                status="archived",
            )
            .exclude(period=current_period)
            .prefetch_related("action_items")
            .order_by("-period")[:12]
        )

        return Response({
            "current": PlanDetailSerializer(current).data if current else None,
            "history": PlanListSerializer(history, many=True).data,
        })


class PlanDetailView(APIView):
    """GET /api/kpi/plans/{id}/ — 计划详情。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def get(self, request, pk):
        try:
            plan = (
                ImprovementPlan.objects.select_related("user", "reviewed_by")
                .prefetch_related("action_items__comments__author")
                .get(pk=pk)
            )
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlanDetailSerializer(plan).data)


class PlanPublishView(APIView):
    """POST /api/kpi/plans/{id}/publish/ — 发布计划。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request, pk):
        try:
            plan = ImprovementPlan.objects.get(pk=pk)
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)

        if plan.status != ImprovementPlan.Status.DRAFT:
            return Response({"detail": "只能发布草案状态的计划"}, status=status.HTTP_400_BAD_REQUEST)

        plan.status = ImprovementPlan.Status.PUBLISHED
        plan.reviewed_by = request.user
        plan.published_at = timezone.now()
        plan.save(update_fields=["status", "reviewed_by", "published_at", "updated_at"])
        return Response(PlanDetailSerializer(plan).data)


class PlanArchiveView(APIView):
    """POST /api/kpi/plans/{id}/archive/ — 归档计划。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request, pk):
        try:
            plan = ImprovementPlan.objects.get(pk=pk)
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)

        if plan.status != ImprovementPlan.Status.PUBLISHED:
            return Response({"detail": "只能归档已发布的计划"}, status=status.HTTP_400_BAD_REQUEST)

        plan.status = ImprovementPlan.Status.ARCHIVED
        plan.archived_at = timezone.now()
        plan.save(update_fields=["status", "archived_at", "updated_at"])
        return Response(PlanDetailSerializer(plan).data)


class PlanGenerateView(APIView):
    """POST /api/kpi/plans/generate/ — 为指定用户生成 AI 草案。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request):
        from django.contrib.auth import get_user_model
        from .plan_generator import generate_action_items
        from .services import KPIService

        User = get_user_model()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "缺少 user_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)

        period = timezone.now().strftime("%Y-%m")
        if ImprovementPlan.objects.filter(user=target_user, period=period).exists():
            return Response({"detail": "该用户本月已有计划"}, status=status.HTTP_409_CONFLICT)

        # 计算 KPI 数据
        today = timezone.now().date()
        month_start = today.replace(day=1)
        svc = KPIService()
        kpi_data = svc.compute_for_user(target_user, month_start, today)

        # 获取团队均值
        users = svc._get_target_users()
        team_scores = [svc.compute_for_user(u, month_start, today)["scores"] for u in users]
        dims = ("efficiency", "output", "quality", "capability")
        team_avgs = {}
        if team_scores:
            for d in dims:
                vals = [s.get(d, 0) for s in team_scores]
                team_avgs[d] = round(sum(vals) / len(vals), 1)

        # 生成行动项
        items_data = generate_action_items(
            kpi_data["scores"],
            kpi_data["issue_metrics"],
            kpi_data["commit_metrics"],
            team_avgs,
        )

        # 创建计划
        plan = ImprovementPlan.objects.create(
            user=target_user,
            period=period,
            status=ImprovementPlan.Status.DRAFT,
            source_kpi_scores=kpi_data["scores"],
        )

        for i, item_data in enumerate(items_data):
            ActionItem.objects.create(
                plan=plan,
                sort_order=i,
                **item_data,
            )

        return Response(PlanDetailSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlanEditView(APIView):
    """PUT /api/kpi/plans/{id}/ — 管理员编辑计划（行动项增删改）。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def put(self, request, pk):
        try:
            plan = ImprovementPlan.objects.get(pk=pk)
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)

        items_data = request.data.get("action_items", [])

        # 获取现有 item IDs
        existing_ids = set(str(item.id) for item in plan.action_items.all())
        incoming_ids = set(str(item["id"]) for item in items_data if item.get("id"))

        # 删除被移除的
        to_delete = existing_ids - incoming_ids
        if to_delete:
            ActionItem.objects.filter(id__in=to_delete, plan=plan).delete()

        # 更新或新增
        for i, item_data in enumerate(items_data):
            item_id = item_data.get("id")
            defaults = {
                "title": item_data.get("title", ""),
                "description": item_data.get("description", ""),
                "measurable_target": item_data.get("measurable_target", ""),
                "points": item_data.get("points", 10),
                "priority": item_data.get("priority", "medium"),
                "dimension": item_data.get("dimension", "general"),
                "sort_order": i,
            }
            if item_id and str(item_id) in existing_ids:
                ActionItem.objects.filter(id=item_id, plan=plan).update(**defaults)
            else:
                ActionItem.objects.create(
                    plan=plan, source=ActionItem.Source.MANAGER, **defaults,
                )

        plan.refresh_from_db()
        return Response(PlanDetailSerializer(plan).data)


# ------------------------------------------------------------------
# Action Item operations
# ------------------------------------------------------------------

class ActionItemStatusView(APIView):
    """POST /api/kpi/action-items/{id}/status/ — 员工更新行动项状态。"""
    permission_classes = [IsAuthenticated]

    EMPLOYEE_TRANSITIONS = {
        "pending": ["in_progress"],
        "in_progress": ["submitted"],
    }

    def post(self, request, pk):
        try:
            item = ActionItem.objects.select_related("plan").get(pk=pk)
        except ActionItem.DoesNotExist:
            return Response({"detail": "行动项不存在"}, status=status.HTTP_404_NOT_FOUND)

        if item.plan.user != request.user:
            return Response({"detail": "只能操作自己的行动项"}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get("status")
        allowed = self.EMPLOYEE_TRANSITIONS.get(item.status, [])
        if new_status not in allowed:
            return Response(
                {"detail": f"不允许从 {item.status} 变更为 {new_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.status = new_status
        item.save(update_fields=["status", "updated_at"])
        return Response(ActionItemSerializer(item).data)


class ActionItemVerifyView(APIView):
    """POST /api/kpi/action-items/{id}/verify/ — 管理员验收。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request, pk):
        try:
            item = ActionItem.objects.get(pk=pk)
        except ActionItem.DoesNotExist:
            return Response({"detail": "行动项不存在"}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status not in ("verified", "not_achieved"):
            return Response({"detail": "状态必须为 verified 或 not_achieved"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status == "verified":
            qf = request.data.get("quality_factor")
            if qf is None:
                return Response({"detail": "验收需要提供 quality_factor"}, status=status.HTTP_400_BAD_REQUEST)
            item.quality_factor = qf

        item.status = new_status
        item.save(update_fields=["status", "quality_factor", "updated_at"])
        return Response(ActionItemSerializer(item).data)


# ------------------------------------------------------------------
# Comments
# ------------------------------------------------------------------

class ActionItemCommentListView(APIView):
    """GET/POST /api/kpi/action-items/{id}/comments/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        comments = ActionItemComment.objects.filter(action_item_id=pk).select_related("author")
        serializer = ActionItemCommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        try:
            item = ActionItem.objects.select_related("plan").get(pk=pk)
        except ActionItem.DoesNotExist:
            return Response({"detail": "行动项不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 权限：只能在自己的计划或管理员可以评论
        if item.plan.user != request.user and not request.user.has_perm("kpi.change_improvementplan"):
            return Response({"detail": "无权评论"}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get("content", "").strip()
        if not content:
            return Response({"detail": "评论内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        attachment_url = ""
        attachment_key = ""
        if "attachment" in request.FILES:
            attachment_url, attachment_key = upload_image(request.FILES["attachment"])

        comment = ActionItemComment.objects.create(
            action_item=item,
            author=request.user,
            content=content,
            attachment_url=attachment_url,
            attachment_key=attachment_key,
        )
        return Response(ActionItemCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
```

- [ ] **Step 4: Add URL routes**

Append to `backend/apps/kpi/urls.py`:

```python
from .plan_views import (
    PlanListView, MyPlanView, PlanDetailView, PlanEditView,
    PlanPublishView, PlanArchiveView, PlanGenerateView,
    ActionItemStatusView, ActionItemVerifyView, ActionItemCommentListView,
)
```

Add to `urlpatterns`:

```python
    # 提升计划
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("plans/me/", MyPlanView.as_view(), name="plan-me"),
    path("plans/generate/", PlanGenerateView.as_view(), name="plan-generate"),
    path("plans/<uuid:pk>/", PlanDetailView.as_view(), name="plan-detail"),
    path("plans/<uuid:pk>/edit/", PlanEditView.as_view(), name="plan-edit"),
    path("plans/<uuid:pk>/publish/", PlanPublishView.as_view(), name="plan-publish"),
    path("plans/<uuid:pk>/archive/", PlanArchiveView.as_view(), name="plan-archive"),
    # 行动项
    path("action-items/<uuid:pk>/status/", ActionItemStatusView.as_view(), name="action-item-status"),
    path("action-items/<uuid:pk>/verify/", ActionItemVerifyView.as_view(), name="action-item-verify"),
    path("action-items/<uuid:pk>/comments/", ActionItemCommentListView.as_view(), name="action-item-comments"),
```

Note: `plans/me/` and `plans/generate/` must come BEFORE `plans/<uuid:pk>/` to avoid UUID matching "me" or "generate".

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_plan_api.py -v`
Expected: All 11 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/kpi/plan_views.py backend/apps/kpi/plan_serializers.py backend/apps/kpi/urls.py backend/tests/test_plan_api.py
git commit -m "feat(kpi): add plan CRUD, action item status/verify, comment API"
```

---

## Task 5: Navigation Restructure & Route Config

**Files:**
- Modify: `backend/config/settings.py`
- Create: `frontend/app/pages/app/ai/team-analysis.vue`
- Delete: `frontend/app/pages/app/ai-insights.vue`
- Modify: `frontend/app/composables/useNavigation.ts`

- [ ] **Step 1: Update PAGE_PERMS in settings.py**

In `backend/config/settings.py`, replace the ai-insights route and add new routes:

Replace:
```python
{"path": "/app/ai-insights", "label": "AI 洞察", "icon": "i-heroicons-cpu-chip", "permission": "ai.view_analysis", "sort_order": 4, "meta": {"serviceKey": "ai"}},
```

With:
```python
{"path": "/app/ai/team-analysis", "label": "团队分析", "icon": "i-heroicons-cpu-chip", "permission": "ai.view_analysis", "sort_order": 4, "meta": {"serviceKey": "ai"}},
{"path": "/app/ai/my-plan", "label": "我的提升计划", "icon": "i-heroicons-clipboard-document-check", "permission": None, "sort_order": 5},
{"path": "/app/ai/plans", "label": "团队计划管理", "icon": "i-heroicons-clipboard-document-list", "permission": "kpi.change_improvementplan", "sort_order": 6},
```

Update sort_order for subsequent routes (users → 7, kpi → 8, etc.).

Also update SEED_GROUPS — add `view_own_plan` to 开发者 and 产品经理 permissions lists.

- [ ] **Step 2: Create team-analysis.vue**

Copy the content of `frontend/app/pages/app/ai-insights.vue` to `frontend/app/pages/app/ai/team-analysis.vue`. No content changes needed — just the file path moves.

- [ ] **Step 3: Delete old ai-insights.vue**

Delete `frontend/app/pages/app/ai-insights.vue`.

- [ ] **Step 4: Update useNavigation.ts**

In `frontend/app/composables/useNavigation.ts`, update GROUP_DEFS:

Replace:
```typescript
{ label: '用户管理', icon: 'i-heroicons-users', paths: ['/app/users', '/app/kpi', '/app/permissions'] },
```

With:
```typescript
{ label: 'AI 分析', icon: 'i-heroicons-cpu-chip', paths: ['/app/ai/team-analysis', '/app/ai/my-plan', '/app/ai/plans'] },
{ label: '用户管理', icon: 'i-heroicons-users', paths: ['/app/users', '/app/kpi', '/app/permissions'] },
```

- [ ] **Step 5: Run sync_page_perms and verify**

```bash
cd backend && uv run python manage.py sync_page_perms
```

Expected: New routes created, groups updated.

- [ ] **Step 6: Commit**

```bash
git add backend/config/settings.py frontend/app/pages/app/ai/ frontend/app/composables/useNavigation.ts
git rm frontend/app/pages/app/ai-insights.vue
git commit -m "refactor: restructure AI navigation — AI 洞察 → AI 分析 group"
```

---

## Task 6: Celery Task for Monthly Plan Generation

**Files:**
- Modify: `backend/apps/kpi/tasks.py`
- Modify: `backend/apps/kpi/migrations/0004_improvement_plan.py` (or create 0005 for periodic task seed)

- [ ] **Step 1: Add task to tasks.py**

Append to `backend/apps/kpi/tasks.py`:

```python
@shared_task(ignore_result=False)
def generate_monthly_plans():
    """每月 1 号自动生成提升计划草案。"""
    from django.contrib.auth import get_user_model
    from apps.kpi.models import ImprovementPlan, ActionItem
    from apps.kpi.plan_generator import generate_action_items
    from apps.kpi.services import KPIService

    User = get_user_model()
    today = timezone.now().date()
    current_period = today.strftime("%Y-%m")
    prev_month_start = (today.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
    month_start = today.replace(day=1)

    # 1) 刷新上月 KPI 快照
    svc = KPIService()
    try:
        svc.refresh(period_start=prev_month_start, period_end=month_start - timezone.timedelta(days=1))
    except Exception:
        logger.exception("Failed to refresh previous month KPI")

    # 2) 归档上月 published 计划
    prev_period = prev_month_start.strftime("%Y-%m")
    archived = ImprovementPlan.objects.filter(
        period=prev_period, status=ImprovementPlan.Status.PUBLISHED,
    ).update(status=ImprovementPlan.Status.ARCHIVED, archived_at=timezone.now())
    logger.info("Archived %d plans for %s", archived, prev_period)

    # 3) 为每个活跃用户生成草案
    users = svc._get_target_users()
    team_scores = [svc.compute_for_user(u, month_start, today)["scores"] for u in users]
    dims = ("efficiency", "output", "quality", "capability")
    team_avgs = {}
    if team_scores:
        for d in dims:
            vals = [s.get(d, 0) for s in team_scores]
            team_avgs[d] = round(sum(vals) / len(vals), 1)

    created = 0
    for user in users:
        if ImprovementPlan.objects.filter(user=user, period=current_period).exists():
            continue

        kpi_data = svc.compute_for_user(user, month_start, today)
        items_data = generate_action_items(
            kpi_data["scores"], kpi_data["issue_metrics"],
            kpi_data["commit_metrics"], team_avgs,
        )

        plan = ImprovementPlan.objects.create(
            user=user, period=current_period,
            status=ImprovementPlan.Status.DRAFT,
            source_kpi_scores=kpi_data["scores"],
        )
        for i, item_data in enumerate(items_data):
            ActionItem.objects.create(plan=plan, sort_order=i, **item_data)
        created += 1

    logger.info("Generated %d plans for %s", created, current_period)
```

- [ ] **Step 2: Create migration to seed periodic task**

Create `backend/apps/kpi/migrations/0005_seed_monthly_plan_task.py`:

```python
from django.db import migrations


def seed_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="9", day_of_month="1",
        month_of_year="*", day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="月初生成提升计划草案",
        defaults={
            "task": "apps.kpi.tasks.generate_monthly_plans",
            "crontab": schedule,
            "enabled": True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="apps.kpi.tasks.generate_monthly_plans").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("kpi", "0004_improvement_plan"),
        ("django_celery_beat", "__latest__"),
    ]

    operations = [
        migrations.RunPython(seed_periodic_task, remove_periodic_task),
    ]
```

- [ ] **Step 3: Apply migration and commit**

```bash
cd backend && uv run python manage.py migrate kpi
git add backend/apps/kpi/tasks.py backend/apps/kpi/migrations/0005_*.py
git commit -m "feat(kpi): add Celery task for monthly plan generation"
```

---

## Task 7: Frontend — My Plan Page

**Files:**
- Create: `frontend/app/pages/app/ai/my-plan.vue`

- [ ] **Step 1: Create the page**

Create `frontend/app/pages/app/ai/my-plan.vue` with:

- Top summary cards: item count, total points, earned points, progress bar
- Action item list with priority badge, title, points, status badge
- Click to expand: description, measurable target, comment section
- Status update buttons: pending → in_progress → submitted
- Comment form with file upload for evidence
- History section (collapsed) showing archived plans

Key API calls:
- `GET /api/kpi/plans/me/` — load current plan + history
- `POST /api/kpi/action-items/{id}/status/` — update status
- `POST /api/kpi/action-items/{id}/comments/` — add comment (multipart for attachment)

Use existing patterns from `frontend/app/pages/app/kpi/[id].vue` for card/layout styling.

- [ ] **Step 2: Verify page loads in browser**

Navigate to `http://localhost:3004/app/ai/my-plan` and verify the page renders.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/ai/my-plan.vue
git commit -m "feat: add 我的提升计划 page"
```

---

## Task 8: Frontend — Manager Plans Page

**Files:**
- Create: `frontend/app/pages/app/ai/plans.vue`
- Create: `frontend/app/pages/app/ai/plans/[id].vue`

- [ ] **Step 1: Create team plans list page**

Create `frontend/app/pages/app/ai/plans.vue` with:

- Month picker at top
- "批量生成草案" button
- Table: avatar, name, status badge, item count, total points, earned points, actions
- Action buttons per row: 编辑 / 发布 / 归档 (contextual by status)

Key API calls:
- `GET /api/kpi/plans/?period=2026-04` — list plans
- `POST /api/kpi/plans/generate/` — generate for a user
- `POST /api/kpi/plans/{id}/publish/` — publish
- `POST /api/kpi/plans/{id}/archive/` — archive

- [ ] **Step 2: Create plan edit/review page**

Create `frontend/app/pages/app/ai/plans/[id].vue` with:

- Plan header: user info, period, status
- Editable action item list (add/remove/edit fields inline)
- For each item: title, description, target, points, priority, dimension
- Comment thread view with attachments
- Verify buttons: verified (with quality_factor selector) / not_achieved
- Save button (PUT /api/kpi/plans/{id}/edit/)

Key API calls:
- `GET /api/kpi/plans/{id}/` — load plan detail
- `PUT /api/kpi/plans/{id}/edit/` — save edits
- `POST /api/kpi/action-items/{id}/verify/` — verify item

- [ ] **Step 3: Test both pages in browser**

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/ai/plans.vue frontend/app/pages/app/ai/plans/\[id\].vue
git commit -m "feat: add 团队计划管理 and plan edit pages"
```

---

## Task 9: Frontend — Dashboard Card

**Files:**
- Modify: `frontend/app/pages/app/home.vue`

- [ ] **Step 1: Add improvement plan card to home page**

In the right column of `home.vue`, add a new card after the existing stats section:

```vue
<!-- 我的提升计划 -->
<div v-if="planData" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
  <div class="flex items-center justify-between mb-3">
    <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">我的提升计划</h3>
    <NuxtLink to="/app/ai/my-plan" class="text-xs text-crystal-500 hover:text-crystal-700">
      查看全部 →
    </NuxtLink>
  </div>
  <div class="flex items-center gap-4 mb-3 text-sm">
    <span class="text-gray-500">{{ planData.done }}/{{ planData.total }} 已完成</span>
    <span class="text-gray-500">{{ planData.earned }} / {{ planData.total_points }} 分</span>
  </div>
  <UProgress :value="planData.total > 0 ? planData.done / planData.total * 100 : 0" size="xs" class="mb-3" />
  <div class="space-y-2">
    <div v-for="item in planData.pending_items" :key="item.id" class="flex items-center justify-between text-sm">
      <span class="text-gray-700 dark:text-gray-300 truncate">{{ item.title }}</span>
      <span class="text-gray-400 flex-shrink-0 ml-2">{{ item.points }}分</span>
    </div>
  </div>
</div>
```

Fetch plan data in the script section:

```typescript
const planData = ref<any>(null)

async function fetchPlanSummary() {
  try {
    const res = await api<any>('/api/kpi/plans/me/')
    if (res.current) {
      const items = res.current.action_items || []
      const done = items.filter((i: any) => i.status === 'verified').length
      const earned = items.reduce((s: number, i: any) => s + (i.earned_points || 0), 0)
      const total_points = items.reduce((s: number, i: any) => s + i.points, 0)
      const pending_items = items
        .filter((i: any) => !['verified', 'not_achieved'].includes(i.status))
        .slice(0, 3)
      planData.value = { done, total: items.length, earned, total_points, pending_items }
    }
  } catch { /* plan not available */ }
}
```

Call `fetchPlanSummary()` in `onMounted`.

- [ ] **Step 2: Test in browser**

Navigate to home page, verify the card shows when a published plan exists and hides when it doesn't.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/home.vue
git commit -m "feat: add improvement plan card to dashboard"
```

---

## Task 10: Full Integration Test

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest tests/ -x --tb=short -q
```

Expected: All tests pass (including new plan tests).

- [ ] **Step 2: Run frontend type check**

```bash
cd frontend && npx nuxi typecheck
```

- [ ] **Step 3: Manual smoke test**

1. Login as admin
2. Navigate to AI 分析 → 团队分析 (verify old AI insights work)
3. Navigate to AI 分析 → 团队计划管理
4. Generate a plan for a user
5. Edit the plan (add/modify action items)
6. Publish the plan
7. Login as that user
8. Check 工作台 for the plan card
9. Navigate to AI 分析 → 我的提升计划
10. Update an action item status
11. Leave a comment with screenshot
12. Login as admin, verify the item, set quality factor
13. Check earned points calculation

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: integration fixes for improvement plan"
```
