from django.db import migrations


PROMPT_SLUG = "issue_duplicate_check"
OLD_MODEL = "gpt-4o-mini"
NEW_MODEL = "deepseek-v4-flash"


def fix_model(apps, schema_editor):
    """The 0003 seed used gpt-4o-mini, which the default DeepSeek LLMConfig
    rejects with HTTP 400. Flip to a DeepSeek-supported model, but only if
    the row is still on the original seeded value (so admin overrides win).
    """
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug=PROMPT_SLUG, llm_model=OLD_MODEL).update(llm_model=NEW_MODEL)


def revert_model(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug=PROMPT_SLUG, llm_model=NEW_MODEL).update(llm_model=OLD_MODEL)


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0003_seed_duplicate_check_prompt"),
    ]

    operations = [
        migrations.RunPython(fix_model, reverse_code=revert_model),
    ]
