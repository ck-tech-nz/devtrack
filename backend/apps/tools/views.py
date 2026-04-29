from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.tools.storage as tools_storage
from .models import Attachment

MAX_SIZE = 20 * 1024 * 1024  # 20MB

# Mirror this allowlist with frontend/app/components/MarkdownEditor.vue (ALLOWED_TYPES + EXTENSION_FALLBACK).
ALLOWED_TYPES = {
    # Images
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    # PDF
    "application/pdf",
    # Word
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Excel
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # PowerPoint
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Text / data
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    # Archive
    "application/zip",
    "application/x-zip-compressed",
}

# Extensions that are allowed even when the browser reports an unusual MIME type
# (e.g. some browsers report .md as text/plain or empty).
EXTENSION_FALLBACK = {
    "md", "txt", "csv", "json", "zip",
}


def _is_allowed(file) -> bool:
    if file.content_type in ALLOWED_TYPES:
        return True
    name = file.name or ""
    if "." in name:
        ext = name.rsplit(".", 1)[-1].lower()
        if ext in EXTENSION_FALLBACK:
            return True
    return False


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "未提供文件"}, status=400)
        if not _is_allowed(file):
            return Response(
                {"detail": f"不支持的文件类型: {file.content_type}"},
                status=400,
            )
        if file.size > MAX_SIZE:
            return Response(
                {"detail": "文件大小超过限制 (20MB)"},
                status=400,
            )

        url, key = tools_storage.upload_image(file)

        attachment = Attachment.objects.create(
            uploaded_by=request.user,
            file_name=file.name,
            file_key=key,
            file_url=url,
            file_size=file.size,
            mime_type=file.content_type,
        )

        return Response({"url": url, "filename": file.name, "id": str(attachment.id)})


class AttachmentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        attachment = Attachment.objects.filter(pk=pk).first()
        if not attachment:
            return Response({"detail": "附件不存在"}, status=404)
        if attachment.uploaded_by != request.user and not request.user.is_staff:
            return Response({"detail": "无权限删除此附件"}, status=403)
        tools_storage.delete_object(attachment.file_key)
        attachment.delete()
        return Response(status=204)
