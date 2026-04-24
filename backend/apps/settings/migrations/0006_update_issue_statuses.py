from django.db import migrations


NEW_STATUSES = ["未计划", "待处理", "进行中", "已解决", "已发布", "已关闭"]
OLD_STATUSES = ["积压", "待处理", "进行中", "已解决", "已关闭"]


def update_to_new(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    obj = SiteSettings.objects.first()
    if obj is None:
        return
    obj.issue_statuses = NEW_STATUSES
    obj.save(update_fields=["issue_statuses"])


def revert_to_old(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    obj = SiteSettings.objects.first()
    if obj is None:
        return
    obj.issue_statuses = OLD_STATUSES
    obj.save(update_fields=["issue_statuses"])


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0005_add_backlog_status"),
    ]

    operations = [
        migrations.RunPython(update_to_new, revert_to_old),
    ]
