import json
from django.forms import Widget


class JsonReadonlyToggleWidget(Widget):
    """JSON field that defaults to a prettified readonly view with an edit button."""

    template_name = "widgets/json_readonly_toggle.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = {}
        if value is None:
            value = {}
        pretty = json.dumps(value, ensure_ascii=False, indent=2)
        context["widget"]["pretty_json"] = pretty
        context["widget"]["raw_json"] = pretty
        return context

    def value_from_datadict(self, data, files, name):
        raw = data.get(name)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        return {}
