from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Create default permission groups"

    def handle(self, *args, **options):
        groups_config = {
            "管理员": Permission.objects.filter(
                content_type__app_label__in=["projects", "issues", "settings"]
            ),
            "开发者": Permission.objects.filter(
                codename__in=[
                    "view_project",
                    "view_issue", "add_issue", "change_issue",
                    "view_activity", "view_dashboard",
                ]
            ),
            "产品经理": Permission.objects.filter(
                codename__in=[
                    "view_project", "add_project", "change_project",
                    "view_issue", "add_issue", "change_issue",
                    "view_activity", "view_dashboard",
                    "manage_project_members",
                ]
            ),
            "只读成员": Permission.objects.filter(
                codename__startswith="view_"
            ),
        }

        for group_name, perms in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(perms)
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} group: {group_name} ({perms.count()} permissions)")
