import asyncio
import os
from datetime import datetime

from django.conf import settings as django_settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.generics import ListAPIView, DestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .backup_serializers import DatabaseBackupSerializer
from .models import DatabaseBackup


def get_backup_dir():
    d = getattr(django_settings, "BACKUP_DIR", "/data/backups")
    os.makedirs(d, exist_ok=True)
    return d


async def run_pg_dump(filepath):
    """Run pg_dump. Returns (success, file_size, error_message)."""
    db = django_settings.DATABASES["default"]
    env = os.environ.copy()
    env["PGPASSWORD"] = db.get("PASSWORD", "")

    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h", db.get("HOST", "127.0.0.1"),
        "-p", str(db.get("PORT", "5432")),
        "-U", db.get("USER", "postgres"),
        "-Fc", db.get("NAME", "devtrack"),
        "-f", filepath,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode == 0:
        return True, os.path.getsize(filepath), ""
    return False, 0, stderr.decode().strip()


class BackupListView(ListAPIView):
    queryset = DatabaseBackup.objects.all()
    serializer_class = DatabaseBackupSerializer
    permission_classes = [IsAdminUser]


class BackupCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        if DatabaseBackup.objects.filter(status="running").exists():
            return Response(
                {"detail": "已有备份任务正在运行"},
                status=status.HTTP_409_CONFLICT,
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = django_settings.DATABASES["default"].get("NAME", "devtrack")
        filename = f"{db_name}_{timestamp}.dump"
        filepath = os.path.join(get_backup_dir(), filename)

        backup = DatabaseBackup.objects.create(
            filename=filename,
            status="running",
            created_by=request.user,
        )

        try:
            success, file_size, error_msg = asyncio.run(run_pg_dump(filepath))
            if success:
                backup.status = "success"
                backup.file_size = file_size
            else:
                backup.status = "failed"
                backup.error_message = error_msg
                if os.path.exists(filepath):
                    os.remove(filepath)
        except Exception as e:
            backup.status = "failed"
            backup.error_message = str(e)

        backup.save()
        return Response(
            DatabaseBackupSerializer(backup).data,
            status=status.HTTP_201_CREATED,
        )


class BackupDownloadView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            backup = DatabaseBackup.objects.get(pk=pk)
        except DatabaseBackup.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        filepath = os.path.join(get_backup_dir(), backup.filename)
        if not os.path.exists(filepath):
            return Response(
                {"detail": "备份文件不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(filepath, "rb"),
            content_type="application/octet-stream",
            as_attachment=True,
            filename=backup.filename,
        )


class BackupDeleteView(DestroyAPIView):
    queryset = DatabaseBackup.objects.all()
    serializer_class = DatabaseBackupSerializer
    permission_classes = [IsAdminUser]

    def perform_destroy(self, instance):
        filepath = os.path.join(get_backup_dir(), instance.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        instance.delete()
