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
