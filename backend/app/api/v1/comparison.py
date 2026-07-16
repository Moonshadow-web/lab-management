"""仪器间比对（室间质评）接口：分组CRUD、计划CRUD、结果录入、报告生成/预览/下载/上传。"""
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.config import DATA_DIR
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.comparison import (
    ComparisonGroup, ComparisonPlan, ComparisonResult, ComparisonQualResult,
)
from ...models.instrument import Instrument
from ...models.user import User
from ...schemas.comparison import (
    ComparisonGroupCreate, ComparisonGroupUpdate, ComparisonPlanCreate,
    ComparisonPlanUpdate, ComparisonPlanRead, ComparisonResultsPayload,
    ResolveItemsPayload,
)
from ...services import comparison_report as svc

router = APIRouter(prefix="/comparison", tags=["comparison"])

REPORT_DIR = DATA_DIR / "comparison_reports"
os.makedirs(REPORT_DIR, exist_ok=True)

WRITE = require_roles("admin", "qc_manager")


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------
def _ser_group(g: ComparisonGroup):
    return {
        "id": g.id, "name": g.name, "category": g.category, "form_code": g.form_code,
        "form_title": g.form_title,
        "instrument_ids": json.loads(g.instrument_ids) if g.instrument_ids else [],
        "reference_instrument_id": g.reference_instrument_id,
        "levels": g.levels,
        "items": json.loads(g.items) if g.items else [],
        "sample_desc": g.sample_desc, "note": g.note,
        "created_by": g.created_by, "created_at": g.created_at, "updated_at": g.updated_at,
    }


def _ser_plan(p: ComparisonPlan):
    return {
        "id": p.id, "group_id": p.group_id, "year": p.year, "half": p.half,
        "form_code": p.form_code, "form_title": p.form_title,
        "compared_at": p.compared_at, "operator": p.operator, "reviewer": p.reviewer,
        "summary": p.summary, "conclusion": p.conclusion, "handle_plan": p.handle_plan,
        "status": p.status, "report_path": p.report_path, "report_filename": p.report_filename,
        "created_by": p.created_by, "created_at": p.created_at, "updated_at": p.updated_at,
    }


# ---------------------------------------------------------------------------
# 比对分组
# ---------------------------------------------------------------------------
@router.get("/groups")
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_ser_group(g) for g in db.query(ComparisonGroup).order_by(ComparisonGroup.id).all()]


@router.get("/instruments/options")
def instrument_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """比对分组用的仪器选择列表：显示可识别的型号(model)。默认只列在用仪器。"""
    out = []
    for inst in db.query(Instrument).order_by(Instrument.id).all():
        status = getattr(inst, "status", "") or ""
        out.append({
            "id": inst.id,
            "name": svc.disp_name(inst),          # 显示名（优先型号）
            "raw_name": inst.name or "",
            "model": inst.model or "",
            "status": status,
        })
    return out


@router.post("/groups/resolve-items")
def resolve_items(
    body: ResolveItemsPayload, db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    """按仪器档案里"项目↔仪器"关联，解析给定仪器组的共有项目（含每项适用仪器→遮蔽依据）。"""
    return svc.resolve_common_items(db, body.instrument_ids, body.category, body.min_count)


@router.post("/groups", status_code=201)
def create_group(
    body: ComparisonGroupCreate, db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    g = ComparisonGroup(
        name=body.name, category=body.category, form_code=body.form_code,
        form_title=body.form_title,
        instrument_ids=json.dumps(body.instrument_ids),
        reference_instrument_id=body.reference_instrument_id, levels=body.levels,
        items=json.dumps([i.model_dump() for i in body.items]),
        sample_desc=body.sample_desc, note=body.note, created_by=user.username,
    )
    db.add(g)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "分组名称已存在，请更换名称")
    db.refresh(g)
    return _ser_group(g)


@router.get("/groups/{gid}")
def get_group(gid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.get(ComparisonGroup, gid)
    if not g:
        raise HTTPException(404, "未找到分组")
    return _ser_group(g)


@router.put("/groups/{gid}")
def update_group(
    gid: int, body: ComparisonGroupUpdate, db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    g = db.get(ComparisonGroup, gid)
    if not g:
        raise HTTPException(404, "未找到分组")
    data = body.model_dump(exclude_unset=True)
    if "instrument_ids" in data:
        g.instrument_ids = json.dumps(data["instrument_ids"])
    if "items" in data:
        # data 已由 body.model_dump() 递归转为 dict，items 元素本身即 dict
        g.items = json.dumps(data["items"])
    for k, v in data.items():
        if k in ("instrument_ids", "items"):
            continue
        setattr(g, k, v)
    g.updated_at = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "分组名称已存在，请更换名称")
    db.refresh(g)
    return _ser_group(g)


@router.delete("/groups/{gid}")
def delete_group(gid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    g = db.get(ComparisonGroup, gid)
    if not g:
        raise HTTPException(404, "未找到分组")
    # 级联删除计划与结果
    for p in db.query(ComparisonPlan).filter_by(group_id=gid).all():
        db.query(ComparisonResult).filter_by(plan_id=p.id).delete()
        db.query(ComparisonQualResult).filter_by(plan_id=p.id).delete()
        db.delete(p)
    db.delete(g); db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 比对计划（通用 CRUD）
# ---------------------------------------------------------------------------
_plan_router = APIRouter(prefix="/plans", tags=["comparison-plans"])


@_plan_router.get("")
def list_plans(group_id: int = None, year: int = None, half: int = None,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(ComparisonPlan)
    if group_id is not None:
        q = q.filter_by(group_id=group_id)
    if year is not None:
        q = q.filter_by(year=year)
    if half is not None:
        q = q.filter_by(half=half)
    items = q.order_by(ComparisonPlan.year.desc(), ComparisonPlan.half.desc(), ComparisonPlan.id.desc()).all()
    return {"items": [_ser_plan(p) for p in items], "total": len(items)}


@_plan_router.get("/{pid}", response_model=ComparisonPlanRead)
def get_plan(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    return p


@_plan_router.post("", response_model=ComparisonPlanRead, status_code=201)
def create_plan(body: ComparisonPlanCreate, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = ComparisonPlan(**body.model_dump(), created_by=user.username)
    db.add(p); db.commit(); db.refresh(p)
    return p


@_plan_router.put("/{pid}", response_model=ComparisonPlanRead)
def update_plan(pid: int, body: ComparisonPlanUpdate, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return p


@_plan_router.delete("/{pid}")
def delete_plan(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    if p.report_path:
        _safe_remove(p.report_path)
    db.query(ComparisonResult).filter_by(plan_id=pid).delete()
    db.query(ComparisonQualResult).filter_by(plan_id=pid).delete()
    db.delete(p); db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 结果录入
# ---------------------------------------------------------------------------
@router.get("/plans/{pid}/results")
def get_results(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    g = db.get(ComparisonGroup, p.group_id)
    if not g:
        raise HTTPException(404, "未找到分组")
    instruments = svc._instruments_of(db, g)
    quant = []
    for r in db.query(ComparisonResult).filter_by(plan_id=pid).all():
        quant.append({
            "item": r.item, "level": r.level, "reference_value": r.reference_value,
            "values": json.loads(r.values_json) if r.values_json else {},
        })
    qual = []
    for r in db.query(ComparisonQualResult).filter_by(plan_id=pid).all():
        qual.append({"item": r.item, "results": json.loads(r.results_json) if r.results_json else {}})
    return {
        "category": g.category,
        "items": json.loads(g.items) if g.items else [],
        "levels": g.levels,
        "instruments": instruments,
        "quant": quant, "qual": qual,
    }


def _apply_results(db: Session, pid: int, quant: list, qual: list):
    """定量/定性结果 upsert（保存与导入共用）。quant: [{item,level,reference_value,values}]；
    qual: [{item,results}]。"""
    for row in (quant or []):
        existing = db.query(ComparisonResult).filter_by(
            plan_id=pid, item=row["item"], level=row["level"]).first()
        vals_json = json.dumps(row.get("values", {}))
        if existing:
            existing.reference_value = row.get("reference_value", "")
            existing.values_json = vals_json
            existing.updated_at = datetime.utcnow()
        else:
            db.add(ComparisonResult(
                plan_id=pid, item=row["item"], level=row["level"],
                reference_value=row.get("reference_value", ""), values_json=vals_json,
            ))
    for row in (qual or []):
        existing = db.query(ComparisonQualResult).filter_by(plan_id=pid, item=row["item"]).first()
        rj = json.dumps(row.get("results", {}))
        if existing:
            existing.results_json = rj
            existing.updated_at = datetime.utcnow()
        else:
            db.add(ComparisonQualResult(
                plan_id=pid, item=row["item"], results_json=rj))


@router.put("/plans/{pid}/results")
def save_results(
    pid: int, body: ComparisonResultsPayload, db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    _apply_results(db, pid, body.quant, body.qual)
    db.commit()
    return {"ok": True}


@router.post("/plans/{pid}/results/import")
async def import_results(
    pid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    """从填好的定量比对结果 Excel（如 BG-SM-CZ-025）导入结果，自动匹配仪器与项目。"""
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    g = db.get(ComparisonGroup, p.group_id)
    if not g:
        raise HTTPException(404, "未找到分组")
    data = await file.read()
    if not data:
        raise HTTPException(400, "文件为空")
    try:
        res = svc.import_quant_from_excel(db, g, p, data)
    except Exception as e:
        raise HTTPException(422, f"解析失败：{e}")
    if not res["quant"]:
        return {
            "ok": True, "imported": 0, "levels": 0,
            "matched_items": res["matched_items"],
            "unmatched_items": res["unmatched_items"],
            "instruments_matched": res["instruments_matched"],
            "message": "未解析到可匹配的结果，请检查 Excel 表头与仪器/项目命名",
        }
    _apply_results(db, pid, res["quant"], [])
    db.commit()
    return {
        "ok": True, "imported": len(res["quant"]), "levels": res["levels"],
        "matched_items": res["matched_items"],
        "unmatched_items": res["unmatched_items"],
        "instruments_matched": res["instruments_matched"],
    }


# ---------------------------------------------------------------------------
# 报告：生成 / 预览 / 下载 / 上传 / 删除
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
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    g = db.get(ComparisonGroup, p.group_id)
    if not g:
        raise HTTPException(404, "未找到分组")
    data = svc.compute_data(db, g, p)
    html = svc.build_html(g, p, data)
    return {"html": html}


@router.post("/plans/{pid}/report/generate")
def generate_report(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    g = db.get(ComparisonGroup, p.group_id)
    if not g:
        raise HTTPException(404, "未找到分组")
    data = svc.compute_data(db, g, p)
    safe = f"comparison_{pid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    out = REPORT_DIR / safe
    svc.build_docx(db, g, p, data, str(out))
    if p.report_path:
        _safe_remove(p.report_path)
    p.report_path = f"comparison_reports/{safe}"
    p.report_filename = f"{g.form_code}_{p.year}_半年{p.half}.docx"
    p.updated_at = datetime.utcnow()
    db.commit()
    return _ser_plan(p)


@router.get("/plans/{pid}/report")
def download_report(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(ComparisonPlan, pid)
    if not p or not p.report_path:
        raise HTTPException(404, "尚无报告文件")
    path = REPORT_DIR / os.path.basename(p.report_path)
    if not path.exists():
        raise HTTPException(404, "报告文件不存在，请重新生成")
    return FileResponse(str(path), filename=p.report_filename or os.path.basename(p.report_path))


@router.post("/plans/{pid}/report/upload")
def upload_report(pid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    ext = os.path.splitext(file.filename or "")[1] or ".docx"
    safe = f"comparison_{pid}_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    out = REPORT_DIR / safe
    with open(out, "wb") as f:
        f.write(file.file.read())
    if p.report_path:
        _safe_remove(p.report_path)
    p.report_path = f"comparison_reports/{safe}"
    p.report_filename = file.filename or safe
    p.updated_at = datetime.utcnow()
    db.commit()
    return _ser_plan(p)


@router.delete("/plans/{pid}/report")
def delete_report(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    if p.report_path:
        _safe_remove(p.report_path)
    p.report_path = ""
    p.report_filename = ""
    p.updated_at = datetime.utcnow()
    db.commit()
    return _ser_plan(p)


router.include_router(_plan_router)
