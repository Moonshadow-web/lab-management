"""批号累积靶值接口：
- batches 的增删改查（make_router 工厂）
- 录入结果 / 查明细 / 删结果 / 切换失控标记 / 手动确立 / 上传存档 / 预览存档
"""
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ...core.config import DATA_DIR
from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.qc_target import QCTargetBatch, QCTargetResult, QC_MATERIAL_PRESETS
from ...models.qc_material import QcMaterial
from ...models.user import User
from ...services import qc_target as svc

router = APIRouter(prefix="/qc-target-batches", tags=["qc_target_batches"])

ARCHIVE_DIR = DATA_DIR / "qc_target_archives"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

WRITE = require_roles("admin", "qc_manager")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class QCTargetBatchBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    qc_material: str = ""
    qc_material_id: int | None = None  # 关联注册质控品（主数据）；空=未关联
    lot_no: str = ""
    level: int = 0  # 水平 1/2/3，0=未指定
    instrument: str = ""
    method: str = ""        # conventional / immediate（archive 模式为空）
    mode: str = ""          # archive / entry（前端可传；后端按质控品归一化）
    note: str = ""


class QCTargetBatchCreate(QCTargetBatchBase):
    pass


class QCTargetBatchUpdate(QCTargetBatchBase):
    established: bool | None = None


class QCTargetBatchRead(QCTargetBatchBase):
    id: int
    established: bool = False
    targets_json: str = ""
    archive_filename: str = ""
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# 质控品下拉预设
# ---------------------------------------------------------------------------
@router.get("/materials/presets")
def material_presets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """返回质控品预设 + 历史用过的（去重）。"""
    used = [r[0] for r in db.query(QCTargetBatch.qc_material).distinct().all() if r[0]]
    merged = []
    for m in QC_MATERIAL_PRESETS + used:
        if m and m not in merged:
            merged.append(m)
    return merged


# ---------------------------------------------------------------------------
# batches CRUD（含 mode 归一化）
# ---------------------------------------------------------------------------
def _normalize_mode(db, action, obj):
    """建批/改批时：
    - 若传了 qc_material_id，回填质控品名称（来自主数据）；
    - 按质控品归一化 mode 与 method：生化多项质控品→仅存档，其余→录入。
    """
    mid = getattr(obj, "qc_material_id", None)
    if mid:
        reg = db.get(QcMaterial, mid)
        if reg:
            obj.qc_material = reg.name
    mat = (obj.qc_material or "").strip()
    if mat == "生化多项质控品":
        obj.mode = "archive"
        obj.method = ""
        if action == "create":
            obj.established = True
    else:
        if obj.mode != "archive":
            obj.mode = "entry"
        if obj.method not in ("conventional", "immediate"):
            obj.method = "conventional"
    db.commit()


batch_router = make_router(
    QCTargetBatch,
    QCTargetBatchRead,
    QCTargetBatchCreate,
    QCTargetBatchUpdate,
    search_fields=["qc_material", "lot_no", "instrument"],
    filter_fields=["method", "mode", "established"],
    prefix="",
    after_write=_normalize_mode,
    write_roles=("admin", "qc_manager"),
)
# 重写路径带上本 router 前缀后并入（避免 include_router 重复前缀 / 空路径报错）
for _r in batch_router.routes:
    _r.path = "/qc-target-batches" + (_r.path if _r.path != "/" else "")
    router.routes.append(_r)


# ---------------------------------------------------------------------------
# 统计辅助
# ---------------------------------------------------------------------------
def _active_values(db, batch_id, analyte):
    """返回参与靶值累计的测定值：
    - is_out=False（在控）
    - 或 manual=True（人工确认）
    """
    rows = (
        db.query(QCTargetResult)
        .filter(QCTargetResult.batch_id == batch_id, QCTargetResult.analyte == analyte,
                (QCTargetResult.is_out == False) | (QCTargetResult.manual == True))
        .order_by(QCTargetResult.id)
        .all()
    )
    return [r.value for r in rows]


def _has_manual(db, batch_id, analyte):
    """该分析物是否有任何人工确认的记录。"""
    return db.query(QCTargetResult).filter(
        QCTargetResult.batch_id == batch_id, QCTargetResult.analyte == analyte,
        QCTargetResult.manual == True
    ).first() is not None


def _build_stats(db, batch):
    """返回 per-analyte 统计 + 批次级状态。"""
    results = db.query(QCTargetResult).filter(QCTargetResult.batch_id == batch.id).all()
    analytes = []
    for r in results:
        if r.analyte and r.analyte not in analytes:
            analytes.append(r.analyte)
    per = {}
    for a in analytes:
        vals = _active_values(db, batch.id, a)
        per[a] = svc.compute_analyte(vals, batch.method, batch.established)
        # 人工确认覆盖自动判定
        if _has_manual(db, batch.id, a):
            per[a]["status"] = "在控(人工)"
            per[a]["manual"] = True
    # 批次级状态
    has_out = any(r.is_out for r in results)
    if batch.mode == "archive":
        batch_status = "已存档"
    elif batch.established:
        batch_status = "已确立"
    elif has_out:
        batch_status = "有失控"
    else:
        batch_status = "累积中"
    # 关联质控品的项目清单（供录入分析物下拉预填）
    material_items = []
    if batch.qc_material_id:
        reg = db.get(QcMaterial, batch.qc_material_id)
        if reg and reg.items_json:
            try:
                material_items = json.loads(reg.items_json) or []
            except Exception:
                material_items = []
    return {
        "analytes": analytes,
        "per_analyte": per,
        "batch_status": batch_status,
        "total_entries": len(results),
        "out_count": sum(1 for r in results if r.is_out),
        "established_analytes": sum(1 for a in per.values() if a["established"]),
        "material_items": material_items,
    }


# ---------------------------------------------------------------------------
# 结果录入 / 查询
# ---------------------------------------------------------------------------
class ResultIn(BaseModel):
    analyte: str
    value: float
    qc_date: str = ""
    operator: str = ""
    remark: str = ""


@router.post("/{batch_id}/results", response_model=None)
def add_result(
    batch_id: int,
    payload: ResultIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(WRITE),
):
    batch = db.get(QCTargetBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批号不存在")
    if batch.mode != "entry":
        raise HTTPException(status_code=400, detail="存档模式（生化多项）不录入结果")
    analyte = (payload.analyte or "").strip()
    if not analyte:
        raise HTTPException(status_code=400, detail="请填写项目/分析物")
    # 该 analyte 现有在控值 + 新值
    active = _active_values(db, batch_id, analyte)
    new_vals = active + [payload.value]

    manual_atomic = _has_manual(db, batch_id, analyte)

    si_up = si_lo = None
    status = "累计中"
    is_out = False
    if manual_atomic:
        # 已有手工确认记录 → 跳过自动判定，新值直接纳入
        status = "累计中"
        si_up = si_lo = None
    elif batch.method == "immediate":
        info = svc.classify_immediate(new_vals)
        status = info["status"]
        si_up = info.get("si_upper")
        si_lo = info.get("si_lower")
        is_out = (status == "失控")
    else:  # conventional
        if batch.established:
            # 用已确立靶值判定新值
            tgt = {}
            try:
                tgt = json.loads(batch.targets_json or "{}").get(analyte, {})
            except Exception:
                tgt = {}
            tm = tgt.get("mean", (sum(new_vals) / len(new_vals)) if new_vals else 0.0)
            ts = tgt.get("sd", 0.0)
            status = svc.classify_conventional(payload.value, tm, ts)
            is_out = (status == "失控")
        else:
            status = "累计中"

    seq = db.query(QCTargetResult).filter(
        QCTargetResult.batch_id == batch_id, QCTargetResult.analyte == analyte
    ).count() + 1
    row = QCTargetResult(
        batch_id=batch_id, analyte=analyte, value=payload.value, qc_date=payload.qc_date,
        seq=seq, si_upper=si_up if si_up is not None else 0.0,
        si_lower=si_lo if si_lo is not None else 0.0, status=status, is_out=is_out,
        operator=payload.operator, remark=payload.remark,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "qc_target_results", row.id, payload.model_dump(), _ip(request))

    # 自动确立：active 数达 20
    if not batch.established:
        est_n = svc.IMMEDIATE_ESTABLISH if batch.method == "immediate" else svc.CONVENTIONAL_ESTABLISH
        if len(new_vals) >= est_n:
            _do_establish(db, batch)

    return {"row": _ser_result(row), "stats": _build_stats(db, batch)}


@router.get("/{batch_id}/results", response_model=None)
def list_results(batch_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    batch = db.get(QCTargetBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批号不存在")
    rows = db.query(QCTargetResult).filter(QCTargetResult.batch_id == batch_id).order_by(
        QCTargetResult.analyte, QCTargetResult.id
    ).all()
    return {"rows": [_ser_result(r) for r in rows], "stats": _build_stats(db, batch)}


@router.delete("/{batch_id}/results/{rid}", response_model=None)
def delete_result(batch_id: int, rid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    row = db.get(QCTargetResult, rid)
    if not row or row.batch_id != batch_id:
        raise HTTPException(status_code=404, detail="结果不存在")
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "qc_target_results", rid, {}, _ip(request))
    batch = db.get(QCTargetBatch, batch_id)
    # 若已无结果，撤销确立
    remain = db.query(QCTargetResult).filter(QCTargetResult.batch_id == batch_id).count()
    if remain == 0 and batch.mode != "archive":
        batch.established = False
        batch.targets_json = ""
        db.commit()
    return {"stats": _build_stats(db, batch)}


@router.post("/{batch_id}/results/{rid}/toggle", response_model=None)
def toggle_out(batch_id: int, rid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    """切换失控/人工标记：
    - 失控→在控：设为 manual=True（人工确认），is_out=False，系统不再自动判失控
    - 在控→失控：取消 manual，设为 is_out=True
    """
    row = db.get(QCTargetResult, rid)
    if not row or row.batch_id != batch_id:
        raise HTTPException(status_code=404, detail="结果不存在")
    if row.is_out:
        # 失控→人工认领
        row.is_out = False
        row.manual = True
        row.status = "在控(人工)"
    else:
        # 在控→标回失控
        row.is_out = True
        row.manual = False
        row.status = "失控"
    db.commit()
    write_audit(db, user, "update", "qc_target_results", rid, {"is_out": row.is_out, "manual": row.manual}, _ip(request))
    batch = db.get(QCTargetBatch, batch_id)
    return {"row": _ser_result(row), "stats": _build_stats(db, batch)}


@router.post("/{batch_id}/establish", response_model=None)
def establish(batch_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    """手动确立靶值（≥10 次允许）。按各 analyte 在控值计算均值/SD/CV 存档。"""
    batch = db.get(QCTargetBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批号不存在")
    if batch.mode != "entry":
        raise HTTPException(status_code=400, detail="存档模式无需确立")
    _do_establish(db, batch, force=True)
    return {"stats": _build_stats(db, batch), "targets_json": batch.targets_json}


# ---------------------------------------------------------------------------
# 存档 PDF 上传 / 预览
# ---------------------------------------------------------------------------
@router.post("/{batch_id}/archive", response_model=None)
async def upload_archive(
    batch_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(WRITE),
):
    batch = db.get(QCTargetBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批号不存在")
    fname = (file.filename or "").lower()
    if not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 存档文件")
    safe = f"{batch_id}_{int(datetime.utcnow().timestamp())}.pdf"
    dest = ARCHIVE_DIR / safe
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    # 删除旧文件
    if batch.archive_file:
        old = ARCHIVE_DIR / os.path.basename(batch.archive_file)
        if old.exists():
            try:
                old.unlink()
            except Exception:
                pass
    batch.archive_file = f"qc_target_archives/{safe}"
    batch.archive_filename = file.filename or safe
    if batch.mode == "archive":
        batch.established = True
    db.commit()
    db.refresh(batch)
    return {"archive_file": batch.archive_file, "archive_filename": batch.archive_filename}


@router.get("/{batch_id}/archive")
def download_archive(batch_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    batch = db.get(QCTargetBatch, batch_id)
    if not batch or not batch.archive_file:
        raise HTTPException(status_code=404, detail="无存档文件")
    path = ARCHIVE_DIR / os.path.basename(batch.archive_file)
    if not path.exists():
        raise HTTPException(status_code=404, detail="存档文件丢失")
    return FileResponse(str(path), media_type="application/pdf", filename=batch.archive_filename or "archive.pdf")


# ---------------------------------------------------------------------------
# 序列化 / 工具
# ---------------------------------------------------------------------------
def _ser_result(r: QCTargetResult):
    return {
        "id": r.id, "batch_id": r.batch_id, "analyte": r.analyte, "value": r.value,
        "qc_date": r.qc_date, "seq": r.seq, "si_upper": r.si_upper, "si_lower": r.si_lower,
        "status": r.status, "is_out": r.is_out, "manual": r.manual,
        "operator": r.operator, "remark": r.remark,
        "created_at": r.created_at,
        "created_at": r.created_at,
    }


def _do_establish(db, batch, force=False):
    need = svc.IMMEDIATE_ESTABLISH if batch.method == "immediate" else svc.CONVENTIONAL_ESTABLISH
    min_n = svc.CONVENTIONAL_MIN if force else need
    results = db.query(QCTargetResult).filter(QCTargetResult.batch_id == batch.id).all()
    analytes = []
    for r in results:
        if r.analyte and r.analyte not in analytes:
            analytes.append(r.analyte)
    targets = {}
    for a in analytes:
        vals = _active_values(db, batch.id, a)
        if len(vals) < min_n:
            continue
        info = svc.compute_analyte(vals, batch.method, True)
        targets[a] = {"mean": info["mean"], "sd": info["sd"], "cv": info["cv"], "n": info["n"]}
    batch.targets_json = json.dumps(targets, ensure_ascii=False)
    batch.established = True
    db.commit()


def _ip(request: Request) -> str:
    try:
        return request.client.host if request.client else ""
    except Exception:
        return ""
