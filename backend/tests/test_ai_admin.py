"""LLMConfigAdmin readonly 字段渲染回归测试。

Django 6.0 起 format_html() 不再接受零参数调用(会抛 TypeError:
"args or kwargs must be provided.")。available_models_display 在
available_models 为空时曾用零参数 format_html 渲染静态文案,导致
/admin/ai/llmconfig/<pk>/change/ 在该配置无可用模型时整页 500。
"""

from django.contrib import admin
from django.utils.safestring import SafeString

from apps.ai.admin import LLMConfigAdmin
from apps.ai.models import LLMConfig


def _model_admin() -> LLMConfigAdmin:
    return LLMConfigAdmin(LLMConfig, admin.site)


def test_available_models_display_empty_does_not_crash():
    """空 available_models 必须正常渲染占位文案,而不是抛 TypeError。"""
    # 内存对象即可,不触达数据库:该方法只读 obj.available_models。
    html = _model_admin().available_models_display(LLMConfig(name="x", available_models=[]))
    assert isinstance(html, SafeString)
    assert "留空" in html


def test_available_models_display_with_models_renders_chips():
    """有可用模型时渲染数量摘要与每个模型的 chip。"""
    html = _model_admin().available_models_display(
        LLMConfig(name="x", available_models=["gpt-4o", "gpt-4o-mini"])
    )
    assert isinstance(html, SafeString)
    assert "共 2 个模型" in html
    assert "gpt-4o-mini" in html
