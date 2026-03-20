from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from .models import SiteSettings
from .serializers import SiteSettingsSerializer


class SiteSettingsView(RetrieveAPIView):
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return SiteSettings.get_solo()
