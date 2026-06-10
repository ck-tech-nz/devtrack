import pytest
from datetime import timedelta
from django.utils import timezone
from apps.notifications.models import Bulletin

pytestmark = pytest.mark.django_db


class TestBulletinQuerySet:
    def test_currently_active_filters_inactive_and_out_of_window(self):
        now = timezone.now()
        active = Bulletin.objects.create(category="quote", content="active now")
        inactive = Bulletin.objects.create(category="quote", content="inactive", is_active=False)
        future = Bulletin.objects.create(
            category="announcement", content="future",
            starts_at=now + timedelta(days=1),
        )
        expired = Bulletin.objects.create(
            category="announcement", content="expired",
            ends_at=now - timedelta(days=1),
        )
        within = Bulletin.objects.create(
            category="value", content="within window",
            starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1),
        )

        result = list(Bulletin.objects.currently_active())

        # 断言成员关系而非绝对数量,对其它测试/夹具可能引入的额外行保持健壮。
        assert active in result
        assert within in result
        assert inactive not in result
        assert future not in result
        assert expired not in result

    def test_ordering_by_sort_order(self):
        # 用相对顺序断言而非绝对位置,对其它行的存在保持健壮。
        b_later = Bulletin.objects.create(category="quote", content="later", sort_order=102)
        b_earlier = Bulletin.objects.create(category="quote", content="earlier", sort_order=101)
        result = list(Bulletin.objects.currently_active())
        assert result.index(b_earlier) < result.index(b_later)

    def test_currently_active_includes_window_boundary(self):
        # 窗口边界是包含式的(starts_at__lte / ends_at__gte)。冻结 now 以避免
        # 真实时钟在测试与查询之间漂移导致的偶发失败。
        from unittest import mock

        fixed = timezone.now()
        edge = Bulletin.objects.create(
            category="value", content="boundary-edge",
            starts_at=fixed, ends_at=fixed,
        )
        with mock.patch(
            "apps.notifications.models.timezone.now", return_value=fixed
        ):
            result = list(Bulletin.objects.currently_active())
        assert edge in result


from tests.factories import BulletinFactory


class TestBulletinActiveEndpoint:
    URL = "/api/notifications/bulletins/active/"

    def test_returns_only_active_to_regular_user(self, regular_client):
        BulletinFactory(content="shown", is_active=True)
        BulletinFactory(content="hidden", is_active=False)
        res = regular_client.get(self.URL)
        assert res.status_code == 200
        contents = [b["content"] for b in res.data]
        assert "shown" in contents
        assert "hidden" not in contents

    def test_response_shape_is_lean(self, regular_client):
        BulletinFactory(content="shape-probe", category="quote", source="Linus")
        res = regular_client.get(self.URL)
        assert res.status_code == 200
        item = next(b for b in res.data if b["content"] == "shape-probe")
        assert set(item.keys()) == {"id", "category", "content", "source", "link_url"}

    def test_requires_authentication(self, api_client):
        res = api_client.get(self.URL)
        assert res.status_code in (401, 403)


class TestBulletinManageEndpoint:
    LIST = "/api/notifications/bulletins/manage/"

    def detail(self, pk):
        return f"/api/notifications/bulletins/manage/{pk}/"

    def test_list_forbidden_without_permission(self, regular_client):
        res = regular_client.get(self.LIST)
        assert res.status_code == 403

    def test_list_ok_with_permission(self, auth_client):
        BulletinFactory(content="manage-list-probe")
        res = auth_client.get(self.LIST)
        assert res.status_code == 200
        # Seeded rows are present too — assert our row is listed, not an exact count.
        assert any(r["content"] == "manage-list-probe" for r in res.data["results"])

    def test_create_sets_created_by(self, auth_client, auth_user):
        res = auth_client.post(self.LIST, {
            "category": "value", "content": "对用户诚实", "is_active": True,
        }, format="json")
        assert res.status_code == 201
        from apps.notifications.models import Bulletin
        b = Bulletin.objects.get(content="对用户诚实")
        assert b.created_by_id == auth_user.id

    def test_create_forbidden_without_permission(self, regular_client):
        res = regular_client.post(self.LIST, {"category": "quote", "content": "x"}, format="json")
        assert res.status_code == 403

    def test_update_and_delete(self, auth_client):
        b = BulletinFactory(content="old")
        res = auth_client.patch(self.detail(b.id), {"content": "new"}, format="json")
        assert res.status_code == 200
        assert res.data["content"] == "new"
        res = auth_client.delete(self.detail(b.id))
        assert res.status_code == 204

    def test_detail_forbidden_without_permission(self, regular_client):
        # 详情端点(GET/PATCH/DELETE)同样受 FullDjangoModelPermissions 保护,
        # 无权限用户全部应拿到 403。
        b = BulletinFactory(content="detail-guard")
        assert regular_client.get(self.detail(b.id)).status_code == 403
        assert regular_client.patch(
            self.detail(b.id), {"content": "y"}, format="json"
        ).status_code == 403
        assert regular_client.delete(self.detail(b.id)).status_code == 403
