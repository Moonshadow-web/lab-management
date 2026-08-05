"""CNAS / WS-T 医学实验室认可规范文件：列表 + 预览 + 下载。

文件字节优先存 COS（cloud_key），COS 不可用时回退 MySQL LONGBLOB（data）。
预览用浏览器原生 PDF 阅读器（inline），下载用附件（attachment）。
"""
import re
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...core.cos_storage import cos_storage
from ...models.user import User
from ...models.cnas_standard import CnasStandard

router = APIRouter(prefix="/cnas-standards", tags=["cnas-standards"])


def _content_disposition(disposition: str, filename: str) -> str:
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download"
    return f'{disposition}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


def _parse_filename(original: str):
    """从文件名解析 (sort_order, code, name, category)。

    约定命名：{NN}_{CODE}_{名称}.pdf
      - NN        前导序号 → 展示顺序
      - CODE      第一段（如 CNAS-CL02-2023 / WS-T415-2024）→ 代号
      - 名称      其后 → 名称
    例外：无下划线的（如 09_CNAS实验室认可规范文件清单-2025.pdf）整体作为名称。
    """
    stem = original or ""
    if stem.lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
        stem = stem.rsplit(".", 1)[0]
    sort_order = 999
    rest = stem
    m = re.match(r"^(\d+)[_．.\-]?\s*(.*)$", stem)
    if m:
        try:
            sort_order = int(m.group(1))
        except Exception:
            sort_order = 999
        rest = m.group(2) or stem
    # 拆分代号 / 名称
    parts = rest.split("_", 1)
    if len(parts) == 2 and parts[0].strip():
        code = parts[0].strip()
        name = parts[1].strip()
    else:
        code = ""
        name = rest.strip()
    # 类别推断
    head = (code or name).upper()
    if head.startswith("CNAS"):
        category = "CNAS认可规范"
    elif head.startswith("WS"):
        category = "卫生行业标准(WS/T)"
    else:
        category = "其他"
    return sort_order, code, name, category


def _get_file_bytes(s: CnasStandard) -> bytes | None:
    if s.cloud_key and cos_storage.ready:
        content = cos_storage.get_bytes(s.cloud_key)
        if content:
            return content
    if s.data:
        return s.data
    return None


@router.get("")
def list_standards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(CnasStandard).order_by(CnasStandard.sort_order, CnasStandard.code).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "category": r.category,
            "original_filename": r.original_filename,
            "file_size": r.file_size,
            "sort_order": r.sort_order,
            "uploader": r.uploader,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


@router.post("/upload", status_code=201)
def upload_standard(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "specialty_leader")),
):
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    original = file.filename or "standard.pdf"
    sort_order, code, name, category = _parse_filename(original)
    # COS 上传（失败则回退 BLOB）
    cloud_key = None
    if cos_storage.ready:
        try:
            cloud_key = cos_storage.save("cnas_standards", original, content)
        except Exception:
            cloud_key = None
    s = CnasStandard(
        code=code,
        name=name,
        category=category,
        original_filename=original,
        cloud_key=cloud_key,
        data=content if not cloud_key else None,
        file_size=len(content),
        sort_order=sort_order,
        uploader=user.full_name or user.username,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {
        "id": s.id, "code": s.code, "name": s.name, "category": s.category,
        "sort_order": s.sort_order, "file_size": s.file_size,
    }


@router.get("/{std_id}/preview")
def preview_standard(std_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.get(CnasStandard, std_id)
    if not s:
        raise HTTPException(status_code=404, detail="未找到文件")
    content = _get_file_bytes(s)
    if not content:
        raise HTTPException(status_code=404, detail="文件不存在")
    fname = s.original_filename or f"cnas-{std_id}.pdf"
    return Response(
        content, media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition("inline", fname)},
    )


@router.get("/{std_id}/download")
def download_standard(std_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.get(CnasStandard, std_id)
    if not s:
        raise HTTPException(status_code=404, detail="未找到文件")
    content = _get_file_bytes(s)
    if not content:
        raise HTTPException(status_code=404, detail="文件不存在")
    fname = s.original_filename or f"cnas-{std_id}.pdf"
    return Response(
        content, media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition("attachment", fname)},
    )


@router.post("/{std_id}/replace")
def replace_standard(
    std_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "specialty_leader")),
):
    """替换某条规范文件的二进制内容，保留 code/name/category/sort_order 等元数据。"""
    s = db.get(CnasStandard, std_id)
    if not s:
        raise HTTPException(status_code=404, detail="未找到文件")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    original = file.filename or s.original_filename
    # 清理旧 COS 对象
    if s.cloud_key and cos_storage.ready and hasattr(cos_storage, "delete"):
        try:
            cos_storage.delete(s.cloud_key)
        except Exception:
            pass
    # 写入新 COS（失败回退 BLOB）
    cloud_key = None
    if cos_storage.ready:
        try:
            cloud_key = cos_storage.save("cnas_standards", original, content)
        except Exception:
            cloud_key = None
    s.original_filename = original
    s.cloud_key = cloud_key
    s.data = content if not cloud_key else None
    s.file_size = len(content)
    s.uploader = user.full_name or user.username
    db.commit()
    db.refresh(s)
    return {
        "id": s.id, "code": s.code, "name": s.name,
        "original_filename": s.original_filename, "file_size": s.file_size,
    }
