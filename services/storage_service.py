"""
Storage service: S3/R2 when configured, local filesystem fallback.

Set these env vars to enable S3:
  S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_KEY,
  S3_ENDPOINT_URL (optional, for Cloudflare R2 or other S3-compatible)
  S3_PUBLIC_BASE_URL (public CDN prefix, e.g. https://pub-xxx.r2.dev)
"""
import os
import uuid
import aiofiles
from typing import Optional

from config.settings import settings


def _s3_client():
    try:
        import boto3
        return boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            region_name=settings.S3_REGION or "auto",
        )
    except Exception:
        return None


async def upload_audio(audio_bytes: bytes, filename: str) -> str:
    """Upload audio bytes; return public URL."""
    return await upload_file(audio_bytes, "music", filename, "audio/mpeg")


async def upload_file(data: bytes, folder: str, filename: str, content_type: str) -> str:
    """Upload to S3/R2 under folder/filename (local disk fallback); return URL."""
    if settings.S3_BUCKET_NAME and settings.S3_ACCESS_KEY:
        return await _upload_to_s3(data, f"{folder}/{filename}", content_type)
    return await _save_local(data, folder, filename)


async def _upload_to_s3(data: bytes, key: str, content_type: str) -> str:
    import asyncio
    s3 = _s3_client()

    def _put():
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    await asyncio.get_event_loop().run_in_executor(None, _put)

    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    # Presigned URL valid for 7 days (for private buckets)
    def _presign():
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=604800,
        )
    return await asyncio.get_event_loop().run_in_executor(None, _presign)


async def _save_local(data: bytes, subdir: str, filename: str) -> str:
    path = os.path.join(settings.UPLOAD_DIR, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)
    return f"/{subdir}/{filename}"
