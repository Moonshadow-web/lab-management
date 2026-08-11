import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi.responses import FileResponse

from .config import STORAGE_BACKEND, UPLOAD_ROOT


def _safe_filename(name: str) -> str:
    name = (name or "file").strip()
    name = re.sub(r'[^\w\u4e00-\u9fff\.\-]', '_', name)
    return name or "file"


def _unique_path(directory: Path, safe_name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stem, ext = os.path.splitext(safe_name)
    target = directory / safe_name
    n = 1
    while target.exists():
        target = directory / f"{stem}_{n}{ext}"
        n += 1
    return target


class StorageBackend(ABC):
    """文件存储抽象层。本地用 LocalStorageBackend；上云切换 CloudStorageBackend 业务不动。"""

    @abstractmethod
    def save(self, module: str, filename: str, content: bytes) -> str:
        """保存文件，返回相对路径（如 manuals/xxx.pdf），供数据库存储。"""

    @abstractmethod
    def get_path(self, relative: str) -> Path:
        """返回本地可读取的文件路径（本地后端用）。"""

    @abstractmethod
    def url(self, relative: str) -> str:
        """返回可访问的 URL（本地挂载 /uploads；云存储返回临时签名 URL）。"""

    @abstractmethod
    def delete(self, relative: str) -> None:
        ...

    @abstractmethod
    def exists(self, relative: str) -> bool:
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, module: str, filename: str, content: bytes) -> str:
        target = _unique_path(self.root / module, _safe_filename(filename))
        target.write_bytes(content)
        return f"{module}/{target.name}"

    def get_path(self, relative: str) -> Path:
        return self.root / relative

    def url(self, relative: str) -> str:
        return f"/uploads/{relative}"

    def delete(self, relative: str) -> None:
        p = self.root / relative
        if p.exists():
            p.unlink()

    def exists(self, relative: str) -> bool:
        return (self.root / relative).exists()


# 根据配置选择后端（上云时在此切换为 CloudStorageBackend）
storage: StorageBackend = LocalStorageBackend(UPLOAD_ROOT)


# ═══════════════════════════════════════════════════════════════
#  持久化安全助手 —— 本地 + COS 双写 / COS 兜底
#  防止容器重启时本地磁盘清空导致文件丢失（2026-08-11 血泪教训）
# ═══════════════════════════════════════════════════════════════

def _cos():
    """按需导入 cos_storage，避免循环引用。"""
    from .cos_storage import cos_storage
    return cos_storage


def persist_save(module: str, filename: str, content: bytes) -> str:
    """本地存储 + COS 同步双写。返回本地相对路径。"""
    rel = storage.save(module, filename, content)
    cs = _cos()
    if cs.ready:
        try:
            cs.save(module, Path(rel).name, content)
        except Exception:
            pass
    return rel


def persist_get_path(relative: str) -> Path:
    """读取本地路径 → 不存在则从 COS 恢复。"""
    p = storage.get_path(relative)
    if p.exists():
        return p
    cs = _cos()
    if cs.ready:
        content = cs.get_bytes(relative)
        if content:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
    return p


def persist_delete(relative: str) -> None:
    """删除本地 + COS 双清。"""
    storage.delete(relative)
    cs = _cos()
    if cs.ready:
        try:
            cs.delete(relative)
        except Exception:
            pass
