import uuid
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings


def get_s3_client():
    scheme = "https" if settings.MINIO_USE_SSL else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def upload_image(file) -> str:
    """Upload a file to MinIO and return the public URL."""
    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "bin"
    now = datetime.now()
    key = f"{now.year}/{now.month:02d}/{now.day:02d}/{uuid.uuid4().hex}.{ext}"

    client = get_s3_client()
    client.upload_fileobj(
        file,
        settings.MINIO_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )
    return f"{settings.MINIO_PUBLIC_URL}/{key}"
