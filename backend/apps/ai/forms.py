import json

from django import forms
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from unfold.widgets import UnfoldAdminTextInputWidget

from .models import LLMConfig, Prompt


class DataListInput(UnfoldAdminTextInputWidget):
    """<input list="..."> + paired <datalist>，浏览器原生 typeahead。
    继承 unfold 的 widget 以保留管理后台一致的样式。"""

    def __init__(self, datalist_id, choices=(), attrs=None):
        attrs = {**(attrs or {}), "list": datalist_id, "autocomplete": "off"}
        super().__init__(attrs=attrs)
        self.datalist_id = datalist_id
        self.choices = list(choices)

    def render(self, name, value, attrs=None, renderer=None):
        input_html = super().render(name, value, attrs, renderer)
        datalist_html = format_html(
            '<datalist id="{0}">{1}</datalist>',
            self.datalist_id,
            format_html_join("", '<option value="{0}"></option>', ((m,) for m in self.choices)),
        )
        return mark_safe(input_html + datalist_html)


class PromptAdminForm(forms.ModelForm):
    """提示词管理表单。

    - `llm_model` 用 <input list> + <datalist>,浏览器自带自动补全。
    - 所有 LLMConfig.available_models 以 data-models-map JSON 注到 <input>,
      静态 JS 在 llm_config 变化时重建 <datalist>,无需 AJAX。
    """

    class Meta:
        model = Prompt
        fields = "__all__"

    class Media:
        js = ("ai/prompt_admin.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        models_by_config: dict[str, list[str]] = {
            str(cfg.pk): list(cfg.available_models or [])
            for cfg in LLMConfig.objects.filter(is_active=True)
        }

        initial_cfg_key = ""
        if self.instance and self.instance.pk and self.instance.llm_config_id:
            initial_cfg_key = str(self.instance.llm_config_id)
        initial_choices = models_by_config.get(initial_cfg_key, [])

        self.fields["llm_model"] = forms.CharField(
            label="模型",
            required=True,
            max_length=100,
            widget=DataListInput(
                datalist_id="id_llm_model_options",
                choices=initial_choices,
                attrs={"data-models-map": json.dumps(models_by_config, ensure_ascii=False)},
            ),
            help_text="可输入或从下拉选择;不在所选 LLM 配置可用列表内的值保存时会被校验拒绝。",
        )
