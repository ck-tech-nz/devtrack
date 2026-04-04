from rest_framework.authentication import BaseAuthentication
from apps.settings.models import ExternalAPIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None

        key = auth_header[len(self.keyword) + 1 :]
        try:
            api_key = ExternalAPIKey.objects.select_related(
                "default_assignee", "project"
            ).get(key=key, is_active=True)
        except ExternalAPIKey.DoesNotExist:
            return None

        request.api_key = api_key
        return (api_key.default_assignee, api_key)
