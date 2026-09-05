from __future__ import annotations

import asyncio
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def ensure_ready(self) -> None:
        return None

    async def healthcheck(self) -> bool:
        return True

    async def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        del content_type
        self._objects[key] = content

    async def get_bytes(self, key: str) -> bytes:
        return self._objects[key]

    async def exists(self, key: str) -> bool:
        return key in self._objects


class FileSystemObjectStorage:
    """Host-only object store with traversal-safe, immutable paths."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        if self._root not in candidate.parents:
            raise ValueError("object key escapes the configured storage root")
        return candidate

    async def ensure_ready(self) -> None:
        await asyncio.to_thread(self._root.mkdir, parents=True, exist_ok=True)

    async def healthcheck(self) -> bool:
        return self._root.is_dir()

    async def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        del content_type
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        if path.exists():
            if await asyncio.to_thread(path.read_bytes) != content:
                raise FileExistsError("immutable object key already contains different bytes")
            return
        await asyncio.to_thread(path.write_bytes, content)

    async def get_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class S3ObjectStorage:
    """S3 API adapter used by MinIO locally and AWS S3 later."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
    ) -> None:
        self._bucket = bucket
        credentials = (
            {"aws_access_key_id": access_key, "aws_secret_access_key": secret_key}
            if access_key and secret_key
            else {}
        )
        self._client = boto3.client(
            "s3", region_name=region, endpoint_url=endpoint_url, **credentials
        )

    async def ensure_ready(self) -> None:
        def ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code not in {"404", "NoSuchBucket"}:
                    raise
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(ensure)

    async def healthcheck(self) -> bool:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
            return True
        except ClientError:
            return False

    async def put_bytes(self, key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    async def get_bytes(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        return await asyncio.to_thread(response["Body"].read)

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey"}:
                return False
            raise
