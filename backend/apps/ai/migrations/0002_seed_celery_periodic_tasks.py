from django.db import migrations


def seed_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Create "every 1 hour" interval
    hourly, _ = IntervalSchedule.objects.get_or_create(
        every=1, period="hours",
    )

    tasks = [
        {
            "name": "AI 团队洞察分析（每小时）",
            "task": "apps.ai.tasks.run_team_insights",
        },
        {
            "name": "拉取所有仓库代码（每小时）",
            "task": "apps.repos.tasks.pull_all_repos",
        },
        {
            "name": "同步所有 GitHub Issues（每小时）",
            "task": "apps.repos.tasks.sync_all_repos",
        },
    ]

    for task_def in tasks:
        PeriodicTask.objects.get_or_create(
            name=task_def["name"],
            defaults={
                "task": task_def["task"],
                "interval": hourly,
                "enabled": True,
            },
        )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task__in=[
            "apps.ai.tasks.run_team_insights",
            "apps.repos.tasks.pull_all_repos",
            "apps.repos.tasks.sync_all_repos",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        ("django_celery_beat", "__latest__"),
    ]

    operations = [
        migrations.RunPython(seed_periodic_tasks, remove_periodic_tasks),
    ]
