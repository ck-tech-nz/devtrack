from django.conf import settings


def get_config():
    defaults = {
        "ROUTE_LIST_PERMISSION": "IsAuthenticated",
        "PROTECTED_PATHS": ["/app/permissions"],
        "SEED_ROUTES": [],
        "SEED_GROUPS": {},
    }
    user_config = getattr(settings, "PAGE_PERMS", {})
    return {**defaults, **user_config}
