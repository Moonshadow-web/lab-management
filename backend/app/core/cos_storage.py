"""COS（腾讯云对象存储）后端——替代 MySQL LONGBLOB，根治内存告警。

用法：配置环境变量 COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET / COS_REGION
存储后在 DB 只保存 cloud_key（相对路径字符串），不存二进制字节。
"""

import io
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError

from .config import COS_BUCKET, COS_REGION, COS_SECRET_ID, COS_SECRET_KEY, COS_URL_EXPIRES

logger = logging.getLogger("cos_storage")


def _safe_filename(name: str) -> str:
    """保留中文和常见安全字符，其余替换为下划线。"""
    name = (name or "file").strip()
    name = re.sub(r"[^\w\u4e00-\u9fff.\-]", "_", name)
    return name or "file"


def _make_key(module: str, safe_name: str) -> str:
    """生成唯一 COS 对象键：{module}/{uuid8}_{safe_name}"""
    uid = uuid.uuid4().hex[:8]
    return f"{module}/{uid}_{safe_name}"


class CosStorageBackend:
    """腾讯云 COS 对象存储后端。

    - 上传时对象键为 `{module}/{uuid}_{safe_filename}`
    - 下载时返回文件字节
    - url() 返回临时签名链接（默认 1 小时有效）
    """

    def __init__(self):
        if not COS_SECRET_ID or not COS_SECRET_KEY:
            self._client: Optional[CosS3Client] = None
            self._ready = False
            logger.warning("COS 凭据未配置，回退本地磁盘")
            return
        config = CosConfig(
            Region=COS_REGION,
            SecretId=COS_SECRET_ID,
            SecretKey=COS_SECRET_KEY,
            Scheme="https",
        )
        self._client = CosS3Client(config)
        self._bucket = COS_BUCKET
        self._ready = True
        logger.info("COS 存储后端就绪 bucket=%s region=%s", COS_BUCKET, COS_REGION)

    @property
    def ready(self) -> bool:
        return self._ready

    def save(self, module: str, filename: str, content: bytes) -> str:
        """上传文件到 COS，返回 cloud_key。"""
        if not self._ready:
            raise RuntimeError("COS 未配置")
        safe = _safe_filename(filename)
        key = _make_key(module, safe)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=io.BytesIO(content),
            # SDK 要求 header 必须是 str/bytes（不是 int）
            ContentLength=str(len(content)),
        )
        logger.info("COS uploaded key=%s size=%d", key, len(content))
        return key

    def get_bytes(self, key: str) -> Optional[bytes]:
        """从 COS 读取文件字节。不存在返回 None。"""
        if not self._ready:
            return None
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            fp = resp["Body"].get_raw_stream()
            # 分块读取全量，避免某些 SDK 版本 read() 截断
            chunks = []
            while True:
                chunk = fp.read(8192)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        except CosServiceError as e:
            if e.get_status_code() == 404:
                return None
            logger.error("COS get_bytes error: %s", e)
            return None
        except CosClientError as e:
            logger.error("COS client error: %s", e)
            return None

    def url(self, key: str, filename: str = "") -> str:
        """生成临时签名 URL（默认 1 小时有效）。"""
        if not self._ready:
            return ""
        try:
            params = {}
            if filename:
                safe = _safe_filename(filename)
                # RFC 5987 编码中文文件名
                from urllib.parse import quote
                params["response-content-disposition"] = (
                    f"attachment; "
                    f"filename*=UTF-8''{quote(safe)}"
                )
            return self._client.get_presigned_url(
                Bucket=self._bucket,
                Key=key,
                Method="GET",
                Expired=COS_URL_EXPIRES,
                Params=params,
            )
        except Exception as e:
            logger.error("COS presigned_url error: %s", e)
            return ""

    def delete(self, key: str) -> bool:
        """删除 COS 文件。"""
        if not self._ready:
            return False
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except Exception as e:
            logger.error("COS delete error: %s", e)
            return False

    def exists(self, key: str) -> bool:
        """检查 COS 文件是否存在。"""
        if not self._ready:
            return False
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except CosServiceError as e:
            if e.get_status_code() == 404:
                return False
            logger.error("COS head error: %s", e)
            return False
        except Exception:
            return False


# 全局单例
cos_storage = CosStorageBackend()
