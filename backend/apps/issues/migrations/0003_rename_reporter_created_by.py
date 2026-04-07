import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("issues", "0002_issue_source_issue_source_meta"),
    ]

    operations = [
        migrations.RenameField(
            model_name="issue",
            old_name="reporter",
            new_name="created_by",
        ),
        migrations.AlterField(
            model_name="issue",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_issues",
                to=settings.AUTH_USER_MODEL,
                verbose_name="创建人",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updated_issues",
                to=settings.AUTH_USER_MODEL,
                verbose_name="更新人",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="reporter",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="提出人",
            ),
        ),
    ]
