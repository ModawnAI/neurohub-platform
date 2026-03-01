"""S3-compatible storage service (MinIO / Supabase Storage)."""

import asyncio
import logging

import boto3
from botocore.client import Config

from app.config import settings

logger = logging.getLogger("neurohub.storage")


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name=settings.minio_region,
    )


def _s3_client_sync():
    """Return a sync S3 client for use in Celery tasks."""
    return _s3_client()


async def create_presigned_upload(
    bucket: str,
    path: str,
    *,
    expires_in: int = 900,
) -> str:
    """Generate a presigned upload URL."""
    client = _s3_client()
    url = await asyncio.to_thread(
        client.generate_presigned_url,
        "put_object",
        Params={"Bucket": bucket, "Key": path},
        ExpiresIn=expires_in,
    )
    return url


async def create_presigned_download(
    bucket: str,
    path: str,
    *,
    expires_in: int = 900,
) -> str:
    """Generate a presigned download URL."""
    client = _s3_client()
    url = await asyncio.to_thread(
        client.generate_presigned_url,
        "get_object",
        Params={"Bucket": bucket, "Key": path},
        ExpiresIn=expires_in,
    )
    return url


async def put_object(
    bucket: str,
    path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Upload bytes directly to storage."""
    client = _s3_client()
    await asyncio.to_thread(
        client.put_object,
        Bucket=bucket,
        Key=path,
        Body=data,
        ContentType=content_type,
    )


async def get_object(bucket: str, path: str) -> bytes:
    """Download bytes from storage."""
    client = _s3_client()
    resp = await asyncio.to_thread(client.get_object, Bucket=bucket, Key=path)
    return resp["Body"].read()


# Sync variants for use in Celery workers (non-async context)
def put_object_sync(
    bucket: str,
    path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    client = _s3_client_sync()
    client.put_object(Bucket=bucket, Key=path, Body=data, ContentType=content_type)


def get_object_sync(bucket: str, path: str) -> bytes:
    client = _s3_client_sync()
    resp = client.get_object(Bucket=bucket, Key=path)
    return resp["Body"].read()


def create_presigned_download_sync(bucket: str, path: str, *, expires_in: int = 900) -> str:
    client = _s3_client_sync()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": path},
        ExpiresIn=expires_in,
    )


async def download_file(bucket: str, path: str, local_path: str) -> None:
    """Download a file from storage to local disk."""
    client = _s3_client()
    await asyncio.to_thread(
        client.download_file,
        Bucket=bucket,
        Key=path,
        Filename=local_path,
    )


def download_file_sync(bucket: str, path: str, local_path: str) -> None:
    """Sync variant: download a file from storage to local disk."""
    client = _s3_client_sync()
    client.download_file(Bucket=bucket, Key=path, Filename=local_path)
