from django.urls import path
from apps.tools.views import ImageUploadView, AttachmentDeleteView

urlpatterns = [
    path("upload/image/", ImageUploadView.as_view(), name="upload-image"),
    path("attachments/<uuid:pk>/", AttachmentDeleteView.as_view(), name="attachment-delete"),
]
