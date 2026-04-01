from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SiteSettings
from .serializers import SiteSettingsSerializer, LabelSettingsSerializer


class SiteSettingsView(RetrieveAPIView):
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return SiteSettings.get_solo()


class LabelSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = LabelSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settings = SiteSettings.get_solo()
        settings.labels = serializer.validated_data["labels"]
        settings.save(update_fields=["labels"])
        return Response({"labels": settings.labels})
