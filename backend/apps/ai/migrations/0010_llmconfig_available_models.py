from django.db import migrations, models


def backfill_available_models(apps, schema_editor):
    """从已有 Prompt.llm_model 反推 LLMConfig.available_models。

    实际生效的 LLMConfig 取决于 Prompt.llm_config(为空时落回默认配置),
    所以默认配置要把所有无 FK 的 Prompt 的模型也并进来。
    若 LLMConfig 已经手工填过 available_models 则不覆盖。
    """
    LLMConfig = apps.get_model("ai", "LLMConfig")
    Prompt = apps.get_model("ai", "Prompt")

    default_cfg = LLMConfig.objects.filter(is_default=True, is_active=True).first()

    for cfg in LLMConfig.objects.all():
        if cfg.available_models:
            continue
        used = set(
            Prompt.objects.filter(llm_config=cfg).values_list("llm_model", flat=True)
        )
        if default_cfg and cfg.pk == default_cfg.pk:
            used.update(
                Prompt.objects.filter(llm_config__isnull=True).values_list("llm_model", flat=True)
            )
        used = sorted(m for m in used if m)
        if used:
            cfg.available_models = used
            cfg.save(update_fields=["available_models"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0009_seed_auto_assign_prompt"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmconfig",
            name="available_models",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="该配置可用的模型 ID 列表。留空时不校验;非空时提示词的「模型」字段必须在此列表内。",
                verbose_name="可用模型",
            ),
        ),
        migrations.RunPython(backfill_available_models, reverse_code=noop_reverse),
    ]
