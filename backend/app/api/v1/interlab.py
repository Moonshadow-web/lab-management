"""室间比对（无室间质评项目 · 外部参比实验室比对）接口：
计划CRUD、结果录入、候选项目、报告生成/预览/下载/上传/删除。"""
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.config import DATA_DIR
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.interlab import InterlabPlan, InterlabItem
from ...models.instrument import Instrument
from ...models.user import User
from ...schemas.interlab import (
    InterlabPlanCreate, InterlabPlanUpdate, InterlabPlanRead,
    InterlabResultsPayload, InterlabProject,
)
from ...services import interlab_report as svc

router = APIRouter(prefix="/interlab", tags=["interlab"])

REPORT_DIR = DATA_DIR / "interlab_reports"
os.makedirs(REPORT_DIR, exist_ok=True)
svc.REPORT_DIR = REPORT_DIR

WRITE = require_roles("admin", "qc_manager")


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------
def _ser_plan(p: InterlabPlan):
    return {
        "id": p.id, "year": p.year, "half": p.half, "instrument_id": p.instrument_id,
        "reference_lab": p.reference_lab, "compared_at": p.compared_at,
        "operator": p.operator, "reviewer": p.reviewer, "summary": p.summary,
        "conclusion": p.conclusion, "handle_plan": p.handle_plan, "status": p.status,
        "report_path": p.report_path, "report_filename": p.report_filename,
        "created_by": p.created_by, "created_at": p.created_at, "updated_at": p.updated_at,
    }


# ---------------------------------------------------------------------------
# 仪器 / 候选项目
# ---------------------------------------------------------------------------
@router.get("/instruments")
def instrument_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """计划对话框用的仪器选择列表（显示型号）。排除已停用/停用的机器。"""
    out = []
    for inst in db.query(Instrument).filter(
        or_(Instrument.status.is_(None), ~Instrument.status.like("%停用%"))
    ).order_by(Instrument.id).all():
        out.append({"id": inst.id, "name": svc_disp(inst), "model": inst.model or "", "status": getattr(inst, "status", "") or ""})
    return out


@router.get("/mandatory")
def mandatory_list(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """指导用：返回所有「无室间质评、需做室间比对」的必做项目及其所属仪器。"""
    return svc.mandatory_projects(db)


def svc_disp(inst: Instrument) -> str:
    model = (inst.model or "").strip()
    name = (inst.name or "").strip()
    if model and len(model) <= 40:
        return model
    return name or model or f"仪器{inst.id}"


@router.get("/projects", response_model=list[InterlabProject])
def candidate_projects(instrument_id: int = 0, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """按仪器返回可参与室间比对的项目（has_interlab=1，排除无室间比对项目）。"""
    return svc.candidate_projects(db, instrument_id)


# ---------------------------------------------------------------------------
# 计划 CRUD
# ---------------------------------------------------------------------------
@router.get("/plans")
def list_plans(year: int = None, half: int = None, instrument_id: int = None,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(InterlabPlan)
    if year is not None:
        q = q.filter_by(year=year)
    if half is not None:
        q = q.filter_by(half=half)
    if instrument_id is not None:
        q = q.filter_by(instrument_id=instrument_id)
    items = q.order_by(InterlabPlan.year.desc(), InterlabPlan.half.desc(), InterlabPlan.id.desc()).all()
    return {"items": [_ser_plan(p) for p in items], "total": len(items)}


@router.get("/plans/{pid}", response_model=InterlabPlanRead)
def get_plan(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    return p


@router.post("/plans", response_model=InterlabPlanRead, status_code=201)
def create_plan(body: InterlabPlanCreate, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    payload = body.model_dump(exclude={"items", "auto_fill"})
    p = InterlabPlan(**payload, created_by=user.username)
    db.add(p); db.flush()
    # 自助列计划：未显式给出项目时，按仪器自动带出该仪器的全部必做室间比对项目
    if body.items:
        rows = body.items
    elif body.auto_fill and p.instrument_id:
        rows = svc.candidate_projects(db, p.instrument_id)
    else:
        rows = []
    for r in rows:
        if not getattr(r, "item", None):
            continue
        item = r.item if isinstance(r, InterlabItemRow) else r.get("item")
        unit = getattr(r, "unit", "") if isinstance(r, InterlabItemRow) else (r.get("unit") or "")
        kind = getattr(r, "kind", "定量") if isinstance(r, InterlabItemRow) else (r.get("kind") or "定量")
        db.add(InterlabItem(
            plan_id=p.id, item=item, unit=unit or "", our_value="", ref_value="",
            te=(getattr(r, "te", "0") if isinstance(r, InterlabItemRow) else (r.get("te") or "0")),
            mode=(getattr(r, "mode", "relative") if isinstance(r, InterlabItemRow) else (r.get("mode") or "relative")),
            kind=kind, note="",
        ))
    db.commit(); db.refresh(p)
    return p


@router.put("/plans/{pid}", response_model=InterlabPlanRead)
def update_plan(pid: int, body: InterlabPlanUpdate, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return p


@router.delete("/plans/{pid}")
def delete_plan(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    if p.report_path:
        _safe_remove(p.report_path)
    db.query(InterlabItem).filter_by(plan_id=pid).delete()
    db.delete(p); db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 结果录入
# ---------------------------------------------------------------------------
@router.get("/plans/{pid}/results")
def get_results(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    inst = db.get(Instrument, p.instrument_id)
    rows = []
    for it in db.query(InterlabItem).filter_by(plan_id=pid).order_by(InterlabItem.id).all():
        rows.append({
            "item": it.item, "unit": it.unit, "our_value": it.our_value,
            "ref_value": it.ref_value, "te": it.te, "mode": it.mode,
            "kind": it.kind or "定量", "note": it.note,
        })
    return {
        "instrument_name": svc_disp(inst) if inst else "",
        "reference_lab": p.reference_lab,
        "items": rows,
    }


@router.put("/plans/{pid}/results")
def save_results(pid: int, body: InterlabResultsPayload, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    # 全量覆盖该行项目
    db.query(InterlabItem).filter_by(plan_id=pid).delete()
    for row in body.items:
        if not row.item:
            continue
        db.add(InterlabItem(
            plan_id=pid, item=row.item, unit=row.unit, our_value=row.our_value,
            ref_value=row.ref_value, te=row.te, mode=row.mode, note=row.note,
        ))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 报告：预览 / 生成 / 下载 / 上传 / 删除
# ---------------------------------------------------------------------------
def _safe_remove(rel_path):
    try:
        p = REPORT_DIR / os.path.basename(rel_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass


@router.get("/plans/{pid}/report/preview")
def preview_report(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    items = db.query(InterlabItem).filter_by(plan_id=pid).order_by(InterlabItem.id).all()
    inst = db.get(Instrument, p.instrument_id)
    data = svc.compute_data(db, p, items)
    html = svc.build_html(p, data, svc_disp(inst) if inst else "", p.reference_lab)
    return {"html": html}


@router.post("/plans/{pid}/report/generate")
def generate_report(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    items = db.query(InterlabItem).filter_by(plan_id=pid).order_by(InterlabItem.id).all()
    inst = db.get(Instrument, p.instrument_id)
    data = svc.compute_data(db, p, items)
    safe = f"interlab_{pid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    out = REPORT_DIR / safe
    svc.build_docx(db, p, data, str(out), svc_disp(inst) if inst else "", p.reference_lab)
    if p.report_path:
        _safe_remove(p.report_path)
    half = "上半年" if p.half == 1 else "下半年"
    inst_name = svc_disp(inst) if inst else ""
    p.report_path = f"interlab_reports/{safe}"
    p.report_filename = f"室间比对_{p.year}_{half}_{inst_name}.docx"
    p.updated_at = datetime.utcnow()
    db.commit()
    return _ser_plan(p)


@router.get("/plans/{pid}/report")
def download_report(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(InterlabPlan, pid)
    if not p or not p.report_path:
        raise HTTPException(404, "尚无报告文件")
    path = REPORT_DIR / os.path.basename(p.report_path)
    if not path.exists():
        raise HTTPException(404, "报告文件不存在，请重新生成")
    return FileResponse(str(path), filename=p.report_filename or os.path.basename(p.report_path))


@router.post("/plans/{pid}/report/upload")
def upload_report(pid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    ext = os.path.splitext(file.filename or "")[1] or ".docx"
    safe = f"interlab_{pid}_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    out = REPORT_DIR / safe
    with open(out, "wb") as f:
        f.write(file.file.read())
    if p.report_path:
        _safe_remove(p.report_path)
    p.report_path = f"interlab_reports/{safe}"
    p.report_filename = file.filename or safe
    p.updated_at = datetime.utcnow()
    db.commit()
    return _ser_plan(p)


@router.delete("/plans/{pid}/report")
def delete_report(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(InterlabPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    if p.report_path:
        _safe_remove(p.report_path)
    p.report_path = ""
    p.report_filename = ""
    p.updated_at = datetime.utcnow()
    db.commit()
    return _ser_plan(p)
