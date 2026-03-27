from django.db import migrations


def migrate_linked_repos(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Repo = apps.get_model("repos", "Repo")
    for project in Project.objects.all():
        if not project.linked_repos:
            continue
        for repo_id in project.linked_repos:
            try:
                repo = Repo.objects.get(pk=repo_id)
                project.repos.add(repo)
            except Repo.DoesNotExist:
                pass


def reverse_migrate(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    for project in Project.objects.all():
        project.linked_repos = list(project.repos.values_list("id", flat=True))
        project.save(update_fields=["linked_repos"])


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0003_add_repos_m2m"),
    ]
    operations = [
        migrations.RunPython(migrate_linked_repos, reverse_migrate),
    ]
