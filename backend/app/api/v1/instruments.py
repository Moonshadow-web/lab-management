from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
import os
import re
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from ...core.config import ALGORITHM, SECRET_KEY
from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import decode_token, get_current_user
from ...core.storage import storage
from ...core.doc_convert import convert_doc_bytes_to_docx
from ...models.instrument import CalibrationRecord, Instrument, InstrumentRepair
from ...models.instrument_archive import InstrumentArchive
from ...models.document import Document
from ...models.document_instrument import DocumentInstrument
from ...models.test_item import TestItem
from ...models.user import User
from ...core.instrument_link import (
    build_family_map,
    build_instrument_test_items_map,
    resolve_family_instruments,
)
from ...schemas import (
    CalibrationRecordCreate,
    CalibrationRecordRead,
    InstrumentCreate,
    InstrumentRead,
    InstrumentRepairCreate,
    InstrumentRepairRead,
    InstrumentRepairUpdate,
    InstrumentUpdate,
    TestItemRead,
)
from ...services.notification_service import (
    compute_calibration_alerts,
    refresh_calibration_notifications,
)

# 仪器台账 CRUD（通用路由），校准记录在其上扩展
# 排序：日常管理人(空值排最后) → 科室编号自然升序
_instrument_order = [
    case((or_(Instrument.daily_manager.is_(None), Instrument.daily_manager == ""), 1), else_=0),
    # doc_number_sort 仅在 SQLite 存在，MySQL 用原生排序
    Instrument.dept_no,
]
router = make_router(
    Instrument,
    InstrumentRead,
    InstrumentCreate,
    InstrumentUpdate,
    search_fields=["name", "dept_no", "model", "manufacturer", "serial_no", "owner", "location"],
    filter_fields=["status", "category"],
    order_by=_instrument_order,
    prefix="/instruments",
    write_roles=("admin", "specialty_leader"),
)


@router.get("/family-map")
def instrument_family_map(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """项目「使用仪器」总型号 → 对应仪器档案清单。

    返回 { 总型号: [ {id,name,model,dept_no,has_archive}, ... ] }，供项目查询页
    渲染「关联仪器」芯片并跳转档案。一对多（如 罗氏 Cobas6000 → e601/e602/e411）。
    """
    # 遍历全部已登记的总型号 / 仪器组 token 家族（instrument_families 表），
    # 不再局限于 test_items.instrument，从而支持「仪器组」精确关联。
    return build_family_map(db)


# 路由重排：/family-map 静态路由必须排在 /{id} 之前，否则会被参数路由吞掉
_family_routes = [r for r in router.routes if getattr(r, "path", None) == "/family-map"]
_other_routes = [r for r in router.routes if getattr(r, "path", None) != "/family-map"]
router.routes = _family_routes + _other_routes


@router.get("/{instrument_id}/test-items", response_model=list[TestItemRead])
def instrument_test_items(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """反向索引：返回引用了该仪器的项目列表（与项目查询页「关联仪器」芯片对称）。

    项目通过 instrument_group 中的 token（如 AU58-1 / 急诊）或总型号 instrument
    命中某个 family，进而关联到本仪器；此处把该关系反转，列出所有落在本仪器上的项目。
    """
    if not db.get(Instrument, instrument_id):
        raise HTTPException(status_code=404, detail="未找到仪器")
    m = build_instrument_test_items_map(db)
    items = list(m.get(instrument_id, []))
    items.sort(key=lambda x: (x.code or ""))
    return items


@router.get("/{instrument_id}/documents")
def instrument_documents(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回关联到该仪器的文档（如操作+保养记录），供仪器档案页反向展示。

    关联关系存于 document_instruments 表（多对多）。默认排除「作废」文档，
    按编号自然序返回精简字段。
    """
    if not db.get(Instrument, instrument_id):
        raise HTTPException(status_code=404, detail="未找到仪器")
    rows = (
        db.query(Document)
        .join(DocumentInstrument, DocumentInstrument.document_id == Document.id)
        .filter(DocumentInstrument.instrument_id == instrument_id)
        .filter(Document.status != "作废")
        .all()
    )
    rows.sort(key=lambda d: (d.doc_number or ""))
    return [
        {
            "id": d.id,
            "doc_number": d.doc_number or "",
            "title": d.title or "",
            "category": d.category or "",
            "version": d.version or "",
            "status": d.status or "",
            "original_filename": d.original_filename or "",
        }
        for d in rows
    ]


@router.get("/{instrument_id}/sop-documents")
def instrument_sop_documents(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回该仪器对应的 SOP 文件（仪器作业指导书）。

    匹配规则：取仪器 dept_no（如 MHZYY-JYK-SM-1005），在末段数字前插入
    「-SOP-」得到 SOP 编号（MHZYY-JYK-SM-SOP-1005），再模糊匹配 documents 表的
    doc_number 字段。同一编号只保留最新版本（按 id 倒序取首条）。
    返回字段不含版本号，供仪器档案页直接展示预览/下载。
    """
    inst = db.get(Instrument, instrument_id)
    if not inst:
        raise HTTPException(status_code=404, detail="未找到仪器")

    dept_no = (inst.dept_no or "").strip()
    if not dept_no:
        return []

    # 在末段数字前插入 -SOP-：MHZYY-JYK-SM-1005 → MHZYY-JYK-SM-SOP-1005
    m = re.match(r"^(.*?)(\d+)$", dept_no)
    if m:
        sop_prefix = m.group(1) + "SOP-" + m.group(2)
    else:
        # 无纯数字尾段，直接追加 -SOP
        sop_prefix = dept_no + "-SOP"

    # 模糊匹配：doc_number 以该前缀开头（兼容带后缀的情况）
    all_docs = (
        db.query(Document)
        .filter(Document.doc_number.like(f"{sop_prefix}%"))
        .filter(Document.status == "生效")
        .order_by(Document.id.desc())
        .all()
    )

    # 按 doc_number 分组，每组只保留最新一条（已按 id desc 排序，首条即最新）
    seen = set()
    latest = []
    for d in all_docs:
        key = d.doc_number or ""
        if key not in seen:
            seen.add(key)
            latest.append(d)

    return [
        {
            "id": d.id,
            "doc_number": d.doc_number or "",
            "title": d.title or "",
            "category": d.category or "",
            "original_filename": d.original_filename or "",
        }
        for d in latest
    ]


@router.get("/{instrument_id}/calibrations", response_model=list[CalibrationRecordRead])
def list_calibrations(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(CalibrationRecord)
        .filter(CalibrationRecord.instrument_id == instrument_id)
        .order_by(CalibrationRecord.id.desc())
        .all()
    )


@router.post("/{instrument_id}/calibrations", response_model=CalibrationRecordRead, status_code=201)
def create_calibration(
    instrument_id: int,
    item: CalibrationRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not db.get(Instrument, instrument_id):
        raise HTTPException(status_code=404, detail="未找到仪器")
    rec = CalibrationRecord(instrument_id=instrument_id, **item.model_dump(exclude={"instrument_id"}))
    db.add(rec)
    db.commit()
    db.refresh(rec)
    refresh_calibration_notifications(db)
    write_audit(db, user, "create", "calibration_records", rec.id, item.model_dump(), request.client.host if request.client else None)
    return rec


@router.delete("/{instrument_id}/calibrations/{rec_id}")
def delete_calibration(
    instrument_id: int,
    rec_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(CalibrationRecord, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到校准记录")
    db.delete(rec)
    db.commit()
    refresh_calibration_notifications(db)
    write_audit(db, user, "delete", "calibration_records", rec_id, "", request.client.host if request.client else None)
    return {"ok": True}


# ---------------------------------------------------------------------------
# 仪器维修记录（BG-KS-CZ-909 仪器维修记录表）
# 字段：故障描述 / 影响项目 / 发现人 / 发现时间 / 通知维修时间 / 处理时间 /
#       故障原因及维修过程 / 维修人 / 排查后质控验证结果 / 恢复使用时间 / 签字
# ---------------------------------------------------------------------------

@router.post("/{instrument_id}/repairs/invite")
def create_repair_invite(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成「维修记录扫码填写」邀请链接 token（有效期 30 天，免登录填写）。

    二维码内容 = 前端拼接：<公网地址>/#/repair-fill?token=<token>
    """
    if not db.get(Instrument, instrument_id):
        raise HTTPException(status_code=404, detail="未找到仪器")
    exp = datetime.now(timezone.utc) + timedelta(days=30)
    token = jwt.encode(
        {"sub": "repair-invite", "type": "invite", "iid": instrument_id, "exp": exp},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"ok": True, "token": token, "expires_at": exp.isoformat()}


@router.get("/{instrument_id}/repairs", response_model=list[InstrumentRepairRead])
def list_repairs(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按仪器列出维修记录（按 id 倒序，最新在前）。"""
    return (
        db.query(InstrumentRepair)
        .filter(InstrumentRepair.instrument_id == instrument_id)
        .order_by(InstrumentRepair.id.desc())
        .all()
    )


@router.post("/{instrument_id}/repairs", response_model=InstrumentRepairRead, status_code=201)
def create_repair(
    instrument_id: int,
    item: InstrumentRepairCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新增一条维修记录。签字默认登录人（前端已填，但服务端兜底）。"""
    if not db.get(Instrument, instrument_id):
        raise HTTPException(status_code=404, detail="未找到仪器")
    data = item.model_dump(exclude={"instrument_id"})
    if not data.get("signer"):
        data["signer"] = user.full_name or user.username
    data["created_by_id"] = user.id
    if not data.get("signer_id"):
        data["signer_id"] = user.id
    rec = InstrumentRepair(instrument_id=instrument_id, **data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "create", "instrument_repairs", rec.id, item.model_dump(), request.client.host if request.client else None)
    return rec


@router.put("/{instrument_id}/repairs/{rec_id}", response_model=InstrumentRepairRead)
def update_repair(
    instrument_id: int,
    rec_id: int,
    item: InstrumentRepairUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """编辑维修记录（场景：故障仍在处理中、后续补充维修过程/质控验证）。"""
    rec = db.get(InstrumentRepair, rec_id)
    if not rec or rec.instrument_id != instrument_id:
        raise HTTPException(status_code=404, detail="未找到维修记录")
    data = item.model_dump(exclude_unset=True, exclude={"instrument_id"})
    if not data.get("signer"):
        data["signer"] = user.full_name or user.username
    if not data.get("signer_id"):
        data["signer_id"] = user.id
    for k, v in data.items():
        setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "update", "instrument_repairs", rec.id, item.model_dump(), request.client.host if request.client else None)
    return rec


@router.delete("/{instrument_id}/repairs/{rec_id}")
def delete_repair(
    instrument_id: int,
    rec_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(InstrumentRepair, rec_id)
    if not rec or rec.instrument_id != instrument_id:
        raise HTTPException(status_code=404, detail="未找到维修记录")
    db.delete(rec)
    db.commit()
    write_audit(db, user, "delete", "instrument_repairs", rec_id, "", request.client.host if request.client else None)
    return {"ok": True}


# ---------------------------------------------------------------------------
# 维修记录「扫码免登录填写」公开端点（工程师无需登录）
# 校验 invite token（JWT，30 天有效）→ 返回仪器信息 / 提交维修记录
# ---------------------------------------------------------------------------
public_router = APIRouter(tags=["public-repairs"])


def _decode_repair_invite(token: str) -> int | None:
    """校验邀请 token，返回 instrument_id；无效/过期返回 None。"""
    try:
        payload = decode_token(token, "invite")
    except Exception:
        return None
    if payload.get("sub") != "repair-invite":
        return None
    try:
        return int(payload.get("iid") or 0)
    except (TypeError, ValueError):
        return None


@public_router.get("/public/repairs/invite/{token}")
def repair_invite_info(token: str, db: Session = Depends(get_db)):
    """扫码后免登录读取仪器信息（用于填写页展示设备名称等）。"""
    iid = _decode_repair_invite(token)
    if not iid:
        raise HTTPException(status_code=401, detail="链接无效或已过期，请联系仪器管理员重新生成")
    inst = db.get(Instrument, iid)
    if not inst:
        raise HTTPException(status_code=404, detail="仪器不存在")
    return {
        "instrument_id": inst.id,
        "name": inst.name,
        "dept_no": inst.dept_no,
        "model": inst.model,
        "location": inst.location,
        "owner": inst.owner,
    }


@public_router.post("/public/repairs/invite/{token}", status_code=201)
def repair_invite_submit(token: str, item: InstrumentRepairCreate, db: Session = Depends(get_db)):
    """工程师免登录提交维修记录（instrument_id 取自 token，不允许前端指定）。"""
    iid = _decode_repair_invite(token)
    if not iid:
        raise HTTPException(status_code=401, detail="链接无效或已过期，请联系仪器管理员重新生成")
    if not db.get(Instrument, iid):
        raise HTTPException(status_code=404, detail="仪器不存在")
    data = item.model_dump(exclude={"instrument_id", "signer_id", "created_by_id"})
    rec = InstrumentRepair(instrument_id=iid, **data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"ok": True, "id": rec.id, "instrument_id": iid}


def _get_calibration(db: Session, instrument_id: int, rec_id: int):
    rec = db.get(CalibrationRecord, rec_id)
    if not rec or rec.instrument_id != instrument_id:
        return None
    return rec


def _report_storage_path(rec: CalibrationRecord) -> Path | None:
    if not rec.report_file_path:
        return None
    p = storage.get_path(rec.report_file_path)
    return p if p.exists() else None


@router.post("/{instrument_id}/calibrations/{rec_id}/report", status_code=201)
def upload_calibration_report(
    instrument_id: int,
    rec_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """为某条校准记录上传/替换电子版校准报告（.docx/.pdf/.doc，自动转 doc→docx）。"""
    rec = _get_calibration(db, instrument_id, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到校准记录")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    content, stored_name, file_ext, original_filename = _maybe_convert_doc(file.filename, content)
    rel = storage.save("calibration_reports", stored_name, content)
    # 替换旧报告文件
    if rec.report_file_path:
        storage.delete(rec.report_file_path)
    rec.report_file_path = rel
    rec.report_filename = original_filename
    db.commit()
    refresh_calibration_notifications(db)
    write_audit(db, user, "create", "calibration_records", rec.id, {"report": rel})
    return {
        "id": rec.id,
        "report_file_path": rec.report_file_path,
        "report_filename": rec.report_filename,
        "file_ext": file_ext,
    }


@router.get("/{instrument_id}/calibrations/{rec_id}/report")
def download_calibration_report(
    instrument_id: int,
    rec_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """下载 / 预览校准报告（返回文件流，前端按扩展名决定预览或下载）。"""
    rec = _get_calibration(db, instrument_id, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到校准记录")
    p = _report_storage_path(rec)
    if not p:
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return FileResponse(
        p, filename=rec.report_filename or p.name,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/{instrument_id}/calibrations/{rec_id}/report")
def delete_calibration_report(
    instrument_id: int,
    rec_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = _get_calibration(db, instrument_id, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到校准记录")
    if rec.report_file_path:
        storage.delete(rec.report_file_path)
    rec.report_file_path = ""
    rec.report_filename = ""
    db.commit()
    refresh_calibration_notifications(db)
    return {"ok": True}


@router.get("/calibrations/status")
def calibrations_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回所有在用仪器的校准预警状态（供列表快速标记：下次校准日期 / 逾期 / 即将到期 / 是否有报告）。"""
    return compute_calibration_alerts(db)


# ----------------------------------------------------------------------------
# 仪器档案文件：每个仪器对应一个档案文件（.docx/.pdf/.doc），支持上传/下载/预览/删除
# ----------------------------------------------------------------------------

def _get_archive(db: Session, instrument_id: int):
    return db.query(InstrumentArchive).filter(InstrumentArchive.instrument_id == instrument_id).first()


def _maybe_convert_doc(filename, content):
    """返回 (content, stored_filename, file_ext, original_filename)。

    旧版 .doc（OLE2 复合文档）无法在浏览器内预览，尝试通过 Word COM 转换为
    .docx。判定依据是文件头魔数（而非扩展名），因此即便是「伪装成 .docx」的
    旧 .doc 也能被识别并转换。转换失败则保留原文件（预览时回退下载）。
    """
    base = filename or "archive.docx"
    ext = Path(base).suffix.lower()
    # 真实 .docx（ZIP 包）直接放行
    if content[:2] == b"PK":
        return content, base, ext, (filename or "")
    # OLE2 复合文档（旧版 .doc，可能顶着 .docx 扩展名）→ 转 docx
    if content and content[:4] == b"\xd0\xcf\x11\xe0":
        converted = convert_doc_bytes_to_docx(content)
        if converted:
            stem = Path(base).stem
            new_name = stem + ".docx"
            return converted, new_name, ".docx", new_name
    return content, base, ext, (filename or "")


@router.get("/archives/status")
def archives_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回所有仪器的建档状态（用于列表快速标记已建档/未建档）。"""
    rows = db.query(
        InstrumentArchive.instrument_id,
        InstrumentArchive.original_filename,
        InstrumentArchive.file_ext,
    ).all()
    return [
        {"instrument_id": r[0], "has_archive": True, "original_filename": r[1], "file_ext": r[2]}
        for r in rows
    ]


@router.post("/{instrument_id}/archive", status_code=201)
def upload_archive(
    instrument_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """为指定仪器上传/替换档案文件（同名覆盖旧文件）。"""
    inst = db.get(Instrument, instrument_id)
    if not inst:
        raise HTTPException(status_code=404, detail="未找到仪器")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    content, stored_name, file_ext, original_filename = _maybe_convert_doc(file.filename, content)
    rel = storage.save("instrument_archives", stored_name, content)
    old = _get_archive(db, instrument_id)
    if old:
        storage.delete(old.filename)
        db.delete(old)
        db.commit()
    rec = InstrumentArchive(
        instrument_id=instrument_id,
        filename=rel,
        original_filename=original_filename,
        file_size=len(content),
        file_ext=file_ext,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "create", "instrument_archives", rec.id, {"instrument_id": instrument_id})
    return {
        "id": rec.id,
        "has_archive": True,
        "original_filename": rec.original_filename,
        "file_size": rec.file_size,
        "file_ext": rec.file_ext,
        "uploaded_at": rec.uploaded_at,
    }


@router.get("/{instrument_id}/archive/info")
def archive_info(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = _get_archive(db, instrument_id)
    if not rec:
        return {"has_archive": False}
    return {
        "has_archive": True,
        "original_filename": rec.original_filename,
        "file_size": rec.file_size,
        "file_ext": rec.file_ext,
        "uploaded_at": rec.uploaded_at,
    }


@router.get("/{instrument_id}/archive")
def download_archive(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = _get_archive(db, instrument_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到档案")
    p = storage.get_path(rec.filename)
    if not p.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        p, filename=rec.original_filename or p.name,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/{instrument_id}/archive")
def delete_archive(
    instrument_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = _get_archive(db, instrument_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到档案")
    storage.delete(rec.filename)
    db.delete(rec)
    db.commit()
    return {"ok": True}


@router.post("/archives/import-folder")
def import_archives_folder(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按目录批量导入仪器档案：用文件名中的科室编号(dept_no)匹配仪器。"""
    folder = (body.get("path") or "").strip()
    if not folder or not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail="目录不存在或无法访问")
    dept_list = [(inst.dept_no, inst) for inst in db.query(Instrument).all() if inst.dept_no]
    matched_ids = set()
    imported = 0
    skipped = []
    files = [
        f for f in sorted(os.listdir(folder))
        if f.lower().endswith((".docx", ".doc", ".pdf"))
    ]
    for f in files:
        stem = Path(f).stem
        m = re.search(r"SM-\d+", stem)
        if not m:
            skipped.append(f)
            continue
        code = m.group(0)
        matched = next((inst for dept_no, inst in dept_list if dept_no and dept_no.endswith(code)), None)
        if not matched:
            skipped.append(f"{f}（未匹配到仪器 {code}）")
            continue
        if matched.id in matched_ids:
            skipped.append(f"{f}（重复匹配到同一仪器，已跳过）")
            continue
        fpath = os.path.join(folder, f)
        try:
            with open(fpath, "rb") as fh:
                content = fh.read()
        except Exception:
            skipped.append(f"{f}（读取失败）")
            continue
        if not content:
            skipped.append(f"{f}（空文件）")
            continue
        content, stored_name, file_ext, original_filename = _maybe_convert_doc(f, content)
        rel = storage.save("instrument_archives", stored_name, content)
        old = _get_archive(db, matched.id)
        if old:
            storage.delete(old.filename)
            db.delete(old)
            db.commit()
        db.add(
            InstrumentArchive(
                instrument_id=matched.id,
                filename=rel,
                original_filename=original_filename,
                file_size=len(content),
                file_ext=file_ext,
            )
        )
        db.commit()
        imported += 1
        matched_ids.add(matched.id)
    return {"imported": imported, "skipped": skipped, "total_files": len(files)}


# ============ 临时诊断接口（排查线上 /instruments 500，修复后删除）============
# 用两段路径 /_debug/raw 规避与 /{instrument_id} 单段路由的参数匹配冲突
@router.get("/_debug/raw")
def debug_instruments_raw(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    import traceback as _tb
    try:
        rows = db.query(Instrument).order_by(*_instrument_order).all()
    except Exception as e:
        return {"stage": "query", "error": repr(e), "tb": _tb.format_exc()}
    problems = []
    for r in rows:
        try:
            InstrumentRead.model_validate(r, from_attributes=True)
        except Exception as e:
            problems.append({
                "id": r.id,
                "name": r.name,
                "created_at": repr(r.created_at),
                "updated_at": repr(r.updated_at),
                "qc_instrument": repr(r.qc_instrument),
                "error": repr(e),
            })
    return {"total": len(rows), "problems": problems}
