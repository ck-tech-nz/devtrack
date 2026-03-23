import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestSyncPagePerms:
    def test_creates_routes_from_seed(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/test", "label": "Test", "sort_order": 0},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        assert PageRoute.objects.filter(path="/app/test", source="seed").exists()

    def test_idempotent_routes(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/test", "label": "Test", "sort_order": 0},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        call_command("sync_page_perms")
        assert PageRoute.objects.filter(path="/app/test").count() == 1

    def test_does_not_touch_manual_routes(self, settings):
        PageRoute.objects.create(path="/app/custom", label="Custom", source="manual")
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [
                {"path": "/app/test", "label": "Test", "sort_order": 0},
            ],
            "SEED_GROUPS": {},
        }
        call_command("sync_page_perms")
        assert PageRoute.objects.filter(path="/app/custom", source="manual").exists()

    def test_creates_groups(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [],
            "SEED_GROUPS": {
                "TestGroup": {"permissions_startswith": ["view_"]},
            },
        }
        call_command("sync_page_perms")
        group = Group.objects.get(name="TestGroup")
        assert group.permissions.count() > 0

    def test_inherit_snapshot_semantics(self, settings):
        settings.PAGE_PERMS = {
            "SEED_ROUTES": [],
            "SEED_GROUPS": {
                "Base": {"permissions": ["view_issue"]},
                "Extended": {"inherit": "Base", "permissions": ["add_issue"]},
            },
        }
        call_command("sync_page_perms")
        extended = Group.objects.get(name="Extended")
        codenames = set(extended.permissions.values_list("codename", flat=True))
        assert "view_issue" in codenames
        assert "add_issue" in codenames
