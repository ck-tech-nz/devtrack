import json
from django.forms import Widget


class JsonSchemaWidget(Widget):
    """
    将 JSONField 按 schema 定义拆分为独立的表单控件。

    用法:
        schema = {
            "sidebar_auto_collapse": {"type": "boolean", "label": "侧边栏自动折叠"},
            "issues_view_mode": {"type": "select", "label": "问题视图", "choices": ["kanban", "table"]},
            "theme": {"type": "select", "label": "主题", "choices": ["light", "dark", "auto"]},
        }
        widget = JsonSchemaWidget(schema=schema)

    支持的 type:
        - "text": 文本输入
        - "number": 数字输入
        - "boolean": 复选框
        - "select": 下拉选择 (需提供 choices)
    """

    template_name = "widgets/json_schema.html"

    def __init__(self, schema=None, attrs=None):
        super().__init__(attrs)
        self.schema = schema or {}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = {}
        if not isinstance(value, dict):
            value = {}

        fields = []
        for key, conf in self.schema.items():
            fields.append(
                {
                    "key": key,
                    "type": conf.get("type", "text"),
                    "label": conf.get("label", key),
                    "choices": conf.get("choices", []),
                    "value": value.get(key, conf.get("default", "")),
                }
            )

        context["widget"]["fields"] = fields
        context["widget"]["json_name"] = name
        return context

    def value_from_datadict(self, data, files, name):
        # 如果隐藏字段有值（由 JS 组装），直接使用
        raw = data.get(name)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

        # 降级：从各子字段收集值
        result = {}
        prefix = f"{name}__"
        for key, conf in self.schema.items():
            field_name = f"{prefix}{key}"
            field_type = conf.get("type", "text")

            if field_type == "boolean":
                result[key] = field_name in data
            elif field_type == "number":
                val = data.get(field_name, "")
                result[key] = float(val) if val else conf.get("default", 0)
            else:
                result[key] = data.get(field_name, conf.get("default", ""))
        return result
