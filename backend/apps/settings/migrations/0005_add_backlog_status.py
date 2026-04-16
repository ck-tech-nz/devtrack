from django.db import migrations


def add_backlog_status(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    settings = SiteSettings.objects.filter(id=1).first()
    if settings and "积压" not in settings.issue_statuses:
        settings.issue_statuses = ["积压"] + list(settings.issue_statuses)
        settings.save()


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0004_externalapikey"),
    ]

    operations = [
        migrations.RunPython(add_backlog_status, migrations.RunPython.noop),
    ]
