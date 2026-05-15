import json
from pathlib import Path

from django.db import migrations


PROMPT_SLUG = "issue_duplicate_check"
SEED_FILE = Path(__file__).resolve().parent.parent / "seed_prompts" / "issue_duplicate_check.json"


def seed_prompt(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    Prompt.objects.get_or_create(
        slug=PROMPT_SLUG,
        defaults={
            "name": data["name"],
            "system_prompt": data["system_prompt"],
            "user_prompt_template": data["user_prompt_template"],
            "llm_model": data["llm_model"],
            "temperature": data["temperature"],
            "is_active": data["is_active"],
        },
    )


def unseed_prompt(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug=PROMPT_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0002_seed_celery_periodic_tasks"),
    ]

    operations = [
        migrations.RunPython(seed_prompt, reverse_code=unseed_prompt),
    ]
