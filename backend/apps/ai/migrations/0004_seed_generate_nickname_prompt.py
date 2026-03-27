from django.db import migrations

SYSTEM_PROMPT = (
    "你是一个开发者平台的昵称生成器。"
    "你需要根据用户名的字面意思、谐音、缩写或引申含义，生成一个与用户名有语义关联的昵称。"
    "昵称要简洁（2~6个字）、有趣、适合开发者，可以中文或英文。"
    "例如：用户名 'zhangwei' → 可生成「张大卫」「微码侠」；用户名 'starboy' → 可生成「星辰客」「星码人」。"
    '以 JSON 格式返回，格式为 {"nickname": "昵称"}。只生成一个昵称，不要解释，不要多余内容。'
)

USER_PROMPT_TEMPLATE = "用户名：{username}，请根据这个用户名的含义或谐音生成一个相关的昵称。"


def seed_prompt(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.update_or_create(
        slug="generate_nickname",
        defaults={
            "name": "昵称生成",
            "system_prompt": SYSTEM_PROMPT,
            "user_prompt_template": USER_PROMPT_TEMPLATE,
            "llm_model": "deepseek-chat",
            "temperature": 1.0,
            "llm_config": None,
            "is_active": True,
        },
    )


def unseed_prompt(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug="generate_nickname").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0003_analysis_issue_fk_auto_trigger"),
    ]

    operations = [
        migrations.RunPython(seed_prompt, reverse_code=unseed_prompt),
    ]
