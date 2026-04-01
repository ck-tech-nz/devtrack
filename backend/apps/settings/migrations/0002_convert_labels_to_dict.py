from django.db import migrations

PALETTE = [
    "#0075ca", "#e99695", "#d73a4a", "#a2eeef", "#7057ff",
    "#0e8a16", "#e4e669", "#f9d0c4", "#bfd4f2", "#c5def5",
]


def forwards(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    for settings in SiteSettings.objects.all():
        labels = settings.labels
        if isinstance(labels, list):
            new_labels = {}
            for i, name in enumerate(labels):
                new_labels[name] = {
                    "foreground": "#ffffff",
                    "background": PALETTE[i % len(PALETTE)],
                    "description": "",
                }
            settings.labels = new_labels
            settings.save(update_fields=["labels"])


def backwards(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    for settings in SiteSettings.objects.all():
        labels = settings.labels
        if isinstance(labels, dict):
            settings.labels = list(labels.keys())
            settings.save(update_fields=["labels"])


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
