import json
from pathlib import Path

from django.db import migrations


SEED_DIR = Path(__file__).resolve().parent.parent / "seed_prompts"
V1_SLUGS = ("wizard_classify", "wizard_extract", "wizard_generate")
V2_SLUG = "wizard_oneshot"


def seed_oneshot_and_deactivate_v1(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    data = json.loads((SEED_DIR / f"{V2_SLUG}.json").read_text(encoding="utf-8"))
    Prompt.objects.update_or_create(
        slug=V2_SLUG,
        defaults={
            "name": data["name"],
            "system_prompt": data["system_prompt"],
            "user_prompt_template": data["user_prompt_template"],
            "llm_model": data["llm_model"],
            "temperature": data["temperature"],
            "is_active": data["is_active"],
        },
    )
    # v1 rows preserved for 7-day rollback window; only flip is_active off.
    Prompt.objects.filter(slug__in=V1_SLUGS).update(is_active=False)


def reverse_oneshot_and_reactivate_v1(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug=V2_SLUG).delete()
    Prompt.objects.filter(slug__in=V1_SLUGS).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0006_update_wizard_generate_prompt"),
    ]

    operations = [
        migrations.RunPython(
            seed_oneshot_and_deactivate_v1,
            reverse_code=reverse_oneshot_and_reactivate_v1,
        ),
    ]
