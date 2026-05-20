from django.db import migrations


WIZARD_ONESHOT_SLUG = "wizard_oneshot"
DASHSCOPE_URL_FRAGMENT = "dashscope"


def link_wizard_oneshot_to_dashscope(apps, schema_editor):
    """wizard_oneshot 用 qwen-vl-max-latest(阿里 DashScope 的视觉模型),但历史
    Prompt 数据没绑定 llm_config,运行时落回默认配置。若默认配置是 DeepSeek,
    DeepSeek 服务器不识别 qwen-* 名称,SSE 调用会以 HTTP 400 失败。

    本迁移做最小修复:仅当数据满足以下全部条件才改:
      - Prompt slug=wizard_oneshot 存在
      - 它当前没有显式 llm_config(避免覆盖管理员手工设置)
      - 数据库里存在 base_url 含 'dashscope' 的 LLMConfig
    任一条件不满足则跳过,管理员仍需到 /api/admin/ai/prompt/ 手工绑定。
    """
    LLMConfig = apps.get_model("ai", "LLMConfig")
    Prompt = apps.get_model("ai", "Prompt")

    prompt = Prompt.objects.filter(slug=WIZARD_ONESHOT_SLUG).first()
    if prompt is None or prompt.llm_config_id is not None:
        return

    dashscope_cfg = (
        LLMConfig.objects
        .filter(is_active=True, base_url__icontains=DASHSCOPE_URL_FRAGMENT)
        .order_by("-is_default", "id")
        .first()
    )
    if dashscope_cfg is None:
        return

    prompt.llm_config = dashscope_cfg
    prompt.save(update_fields=["llm_config", "updated_at"])


def unlink_wizard_oneshot(apps, schema_editor):
    """Reverse 只清理在被本迁移设置的 llm_config 的情形。
    无法精确还原(无标记),所以只在 llm_config 仍指向 DashScope 配置时清空。
    """
    LLMConfig = apps.get_model("ai", "LLMConfig")
    Prompt = apps.get_model("ai", "Prompt")

    prompt = Prompt.objects.filter(slug=WIZARD_ONESHOT_SLUG).first()
    if prompt is None or prompt.llm_config_id is None:
        return
    if DASHSCOPE_URL_FRAGMENT in (prompt.llm_config.base_url or "").lower():
        prompt.llm_config = None
        prompt.save(update_fields=["llm_config", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0010_llmconfig_available_models"),
    ]

    operations = [
        migrations.RunPython(link_wizard_oneshot_to_dashscope, reverse_code=unlink_wizard_oneshot),
    ]
