from django.db import migrations


def seed_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    hourly, _ = IntervalSchedule.objects.get_or_create(
        every=1, period="hours",
    )

    PeriodicTask.objects.get_or_create(
        name="KPI 数据刷新（每小时）",
        defaults={
            "task": "apps.kpi.tasks.refresh_all_kpi",
            "interval": hourly,
            "enabled": True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="apps.kpi.tasks.refresh_all_kpi").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("kpi", "0001_initial"),
        ("django_celery_beat", "__latest__"),
    ]

    operations = [
        migrations.RunPython(seed_periodic_task, remove_periodic_task),
    ]
