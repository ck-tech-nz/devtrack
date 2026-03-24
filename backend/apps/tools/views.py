from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.tools.storage as tools_storage

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "未提供文件"}, status=400)
        if file.content_type not in ALLOWED_TYPES:
            return Response(
                {"detail": f"不支持的文件类型: {file.content_type}，仅支持 PNG/JPEG/GIF/WebP"},
                status=400,
            )
        if file.size > MAX_SIZE:
            return Response(
                {"detail": f"文件大小 ({file.size // 1024 // 1024}MB) 超过限制 (5MB)"},
                status=400,
            )
        url = tools_storage.upload_image(file)
        return Response({"url": url, "filename": file.name})
