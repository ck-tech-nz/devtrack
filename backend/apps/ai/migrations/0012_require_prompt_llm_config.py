from django.db import migrations, models


def backfill_llm_config(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    LLMConfig = apps.get_model("ai", "LLMConfig")

    orphans = Prompt.objects.filter(llm_config__isnull=True)
    if not orphans.exists():
        return

    # Existing config to assign — prefer default → any active → any.
    fallback = (
        LLMConfig.objects.filter(is_default=True, is_active=True).first()
        or LLMConfig.objects.filter(is_active=True).first()
        or LLMConfig.objects.first()
    )
    # Fresh installs hit this migration before any admin has set up an
    # LLMConfig (seed Prompt migrations 0003/0005/0007/0009 created rows
    # without one, relying on a runtime fallback that's now gone). Create
    # an obviously-placeholder config so the constraint can be enforced;
    # is_active=False keeps it from being picked up by runtime lookups
    # until an admin replaces or activates it.
    if fallback is None:
        fallback = LLMConfig.objects.create(
            name="[未配置 - 请在管理后台设置]",
            api_key="",
            base_url="",
            available_models=[],
            supports_json_mode=True,
            is_default=False,
            is_active=False,
        )
    orphans.update(llm_config=fallback)


def noop_reverse(apps, schema_editor):
    # Backfilled values can't be distinguished from manually-set ones, so we
    # leave them in place on reverse — the AlterField below restores the
    # nullable column, but rows keep their pointers.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0011_fix_wizard_oneshot_llm_config"),
    ]

    operations = [
        migrations.RunPython(backfill_llm_config, noop_reverse),
        migrations.AlterField(
            model_name="prompt",
            name="llm_config",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                to="ai.llmconfig",
                verbose_name="LLM 配置",
            ),
        ),
    ]
