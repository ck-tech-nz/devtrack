from django.urls import path

from apps.tools.views import ImageUploadView

urlpatterns = [
    path("upload/image/", ImageUploadView.as_view(), name="upload-image"),
]
