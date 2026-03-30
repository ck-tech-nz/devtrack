from django.db import migrations


SYSTEM_PROMPT = """\
你是代码分析专家。分析代码仓库，返回JSON（不含markdown标记）：
{"cause": "根因分析", "solution": "IDE可执行的修改指令"}

规则：
- cause：1-3句话说清根因，引用具体文件路径和行号
- solution：写成可以直接复制粘贴到IDE（如Claude Code）执行的修改提示词。用自然语言指令说清：改哪些文件、改什么、怎么改。不要贴代码片段
- 用中文"""

USER_PROMPT = """\
问题: {title}
描述: {description}
优先级: {priority}
标签: {labels}"""


def forwards(apps, schema_editor):
    Prompt = apps.get_model("ai", "Prompt")
    Prompt.objects.filter(slug="issue_code_analysis").update(
        system_prompt=SYSTEM_PROMPT,
        user_prompt_template=USER_PROMPT,
    )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0004_seed_generate_nickname_prompt"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
