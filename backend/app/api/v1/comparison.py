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
    ComparisonAttachment,
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

ATTACH_DIR = DATA_DIR / "comparison_attachments"
os.makedirs(ATTACH_DIR, exist_ok=True)

# 权限分层：
#   CREATE = 新建计划 + 在新计划上录入结果（technical_support 也可做）
#   EDIT   = 编辑/删除既有计划 + 生成报告 + 编辑已生成报告的计划
# 既有的 WRITE 别名保留向后兼容
CREATE = require_roles("admin", "qc_manager", "technical_support")
EDIT = require_roles("admin", "qc_manager")
WRITE = EDIT  # 向后兼容（旧调用方仍用 WRITE）


def _ensure_can_edit_results(db: Session, pid: int, user: User):
    """在 PUT results 时检查：草稿状态可用 CREATE 权限；已完成报告的计划必须 EDIT 权限。"""
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    if p.status == "done":
        # 既有报告的计划：必须是 qc_manager 或 admin
        if user.role != "admin" and (user.roles or "").find("qc_manager") == -1:
            raise HTTPException(403, "该计划已生成报告，仅质控管理员可修改结果")
    return p


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
        "status": p.status, "only_uncompared": bool(p.only_uncompared),
        "report_path": p.report_path, "report_filename": p.report_filename,
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
    body: ComparisonGroupCreate, db: Session = Depends(get_db), user: User = Depends(CREATE),
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


@router.get("/groups/{gid}/uncompared")
def uncompared_items(
    gid: int, year: int, half: int, exclude_plan_id: int = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """返回该分组在 (年份, 半年) 下尚未比对的项目，用于同半年补录计划快速锁定待做项。"""
    g = db.get(ComparisonGroup, gid)
    if not g:
        raise HTTPException(404, "未找到分组")
    group_items = json.loads(g.items) if g.items else []
    # 同分组同半年、其它计划里已录入结果的项 = 已比对
    done = set()
    q = db.query(ComparisonPlan).filter_by(group_id=gid, year=year, half=half)
    if exclude_plan_id is not None:
        q = q.filter(ComparisonPlan.id != exclude_plan_id)
    plan_ids = [p.id for p in q.all()]
    if plan_ids:
        rows = db.query(ComparisonResult.item).filter(
            ComparisonResult.plan_id.in_(plan_ids)).distinct().all()
        done = {r.item for r in rows}
    items = [{"name": it.get("name"), "done": it.get("name") in done} for it in group_items]
    uncompared = [it["name"] for it in items if not it["done"]]
    return {
        "items": items, "uncompared": uncompared,
        "total": len(group_items), "done_count": len(done),
    }


@router.put("/groups/{gid}")
def update_group(
    gid: int, body: ComparisonGroupUpdate, db: Session = Depends(get_db), user: User = Depends(EDIT),
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
def delete_group(gid: int, db: Session = Depends(get_db), user: User = Depends(EDIT)):
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
    plans = q.order_by(ComparisonPlan.year.desc(), ComparisonPlan.half.desc(), ComparisonPlan.id.desc()).all()
    # 预取：分组、参照仪器、每计划实际录入的项目
    group_ids = {p.group_id for p in plans}
    groups_by_id = {g.id: g for g in db.query(ComparisonGroup).filter(ComparisonGroup.id.in_(group_ids)).all()} if group_ids else {}
    ref_inst_ids = {g.reference_instrument_id for g in groups_by_id.values() if g and g.reference_instrument_id}
    ref_insts = {i.id: i for i in db.query(Instrument).filter(Instrument.id.in_(ref_inst_ids)).all()} if ref_inst_ids else {}
    plan_ids = [p.id for p in plans]
    # 定量项目
    quant_items = {}
    if plan_ids:
        for r in db.query(ComparisonResult.item, ComparisonResult.plan_id).filter(ComparisonResult.plan_id.in_(plan_ids)).all():
            quant_items.setdefault(r.plan_id, set()).add(r.item)
    # 定性项目
    qual_items = {}
    if plan_ids:
        for r in db.query(ComparisonQualResult.item, ComparisonQualResult.plan_id).filter(ComparisonQualResult.plan_id.in_(plan_ids)).all():
            qual_items.setdefault(r.plan_id, set()).add(r.item)
    # 附件数
    attach_counts = {}
    if plan_ids:
        for aid, pid in db.query(ComparisonAttachment.id, ComparisonAttachment.plan_id).filter(ComparisonAttachment.plan_id.in_(plan_ids)).all():
            attach_counts[pid] = attach_counts.get(pid, 0) + 1

    items = []
    for p in plans:
        s = _ser_plan(p)
        g = groups_by_id.get(p.group_id)
        # 参照仪器（靶机）
        ref = ref_insts.get(g.reference_instrument_id) if g else None
        s["reference_instrument_id"] = g.reference_instrument_id if g else 0
        s["reference_instrument_name"] = (svc.disp_name(ref) if ref else "")
        s["reference_instrument_model"] = (ref.model if ref else "")
        # 比对项目：定量 ∪ 定性
        involved = sorted((quant_items.get(p.id, set()) | qual_items.get(p.id, set())))
        s["compared_items"] = involved
        s["compared_count"] = len(involved)
        s["group_total"] = len(json.loads(g.items) if g and g.items else [])
        # 附件数
        s["attachment_count"] = attach_counts.get(p.id, 0)
        items.append(s)
    return {"items": items, "total": len(items)}


@_plan_router.get("/{pid}", response_model=ComparisonPlanRead)
def get_plan(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    return p


@_plan_router.post("", response_model=ComparisonPlanRead, status_code=201)
def create_plan(body: ComparisonPlanCreate, db: Session = Depends(get_db), user: User = Depends(CREATE)):
    p = ComparisonPlan(**body.model_dump(), created_by=user.username)
    db.add(p); db.commit(); db.refresh(p)
    return p


@_plan_router.put("/{pid}", response_model=ComparisonPlanRead)
def update_plan(pid: int, body: ComparisonPlanUpdate, db: Session = Depends(get_db), user: User = Depends(EDIT)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return p


@_plan_router.delete("/{pid}")
def delete_plan(pid: int, db: Session = Depends(get_db), user: User = Depends(EDIT)):
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
        "global_ref_id": g.reference_instrument_id,
        "quant": quant, "qual": qual,
    }


def _apply_results(db: Session, pid: int, quant: list, qual: list):
    """定量/定性结果 upsert（保存与导入共用）。quant: [{item,level,reference_value,values}]；
    qual: [{item,results}]。入参既可能是 dict（导入），也可能是 pydantic 模型（在线保存）。"""
    def _norm(row):
        return row.model_dump() if hasattr(row, "model_dump") else row
    for row in (quant or []):
        r = _norm(row)
        existing = db.query(ComparisonResult).filter_by(
            plan_id=pid, item=r["item"], level=r["level"]).first()
        vals_json = json.dumps(r.get("values", {}))
        if existing:
            existing.reference_value = r.get("reference_value", "")
            existing.values_json = vals_json
            existing.updated_at = datetime.utcnow()
        else:
            db.add(ComparisonResult(
                plan_id=pid, item=r["item"], level=r["level"],
                reference_value=r.get("reference_value", ""), values_json=vals_json,
            ))
    for row in (qual or []):
        r = _norm(row)
        existing = db.query(ComparisonQualResult).filter_by(plan_id=pid, item=r["item"]).first()
        rj = json.dumps(r.get("results", {}))
        if existing:
            existing.results_json = rj
            existing.updated_at = datetime.utcnow()
        else:
            db.add(ComparisonQualResult(
                plan_id=pid, item=r["item"], results_json=rj))


@router.put("/plans/{pid}/results")
def save_results(
    pid: int, body: ComparisonResultsPayload, db: Session = Depends(get_db), user: User = Depends(CREATE),
):
    # 草稿状态可用 CREATE 权限；已完成报告的计划必须 EDIT 权限（只 qc_manager）
    p = _ensure_can_edit_results(db, pid, user)
    _apply_results(db, pid, body.quant, body.qual)
    db.commit()
    return {"ok": True}


@router.post("/plans/{pid}/results/import")
async def import_results(
    pid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(CREATE),
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
def generate_report(pid: int, db: Session = Depends(get_db), user: User = Depends(EDIT)):
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
    p.report_filename = f"BG-SM-CZ-022_{g.form_code}_{p.year}_半年{p.half}.docx"
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


# ---------------------------------------------------------------------------
# 原始结果附件（图片 / PDF / Word / Excel 等）
# ---------------------------------------------------------------------------
_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
_PDF_EXTS = {"pdf"}
_DOC_EXTS = {"doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx"}


def _classify_ext(ext: str) -> str:
    e = (ext or "").lstrip(".").lower()
    if e in _IMAGE_EXTS:
        return "image"
    if e in _PDF_EXTS:
        return "pdf"
    if e in _DOC_EXTS:
        return "doc"
    return "other"


def _ser_attachment(a: ComparisonAttachment):
    return {
        "id": a.id, "plan_id": a.plan_id, "file_type": a.file_type,
        "original_name": a.original_name, "stored_name": a.stored_name,
        "size_bytes": a.size_bytes,
        "uploaded_by": a.uploaded_by,
        "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
    }


@_plan_router.get("/{pid}/attachments")
def list_attachments(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    items = db.query(ComparisonAttachment).filter_by(plan_id=pid).order_by(ComparisonAttachment.id.desc()).all()
    return {"items": [_ser_attachment(a) for a in items], "total": len(items)}


@_plan_router.post("/{pid}/attachments", status_code=201)
async def upload_attachments(
    pid: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    """一次性上传 1~N 个文件（同一计划）。"""
    p = db.get(ComparisonPlan, pid)
    if not p:
        raise HTTPException(404, "未找到计划")
    out = []
    for f in files:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1] or ""
        safe = f"plan_{pid}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{len(out)}{ext}"
        full = ATTACH_DIR / safe
        content = await f.read()
        with open(full, "wb") as fp:
            fp.write(content)
        a = ComparisonAttachment(
            plan_id=pid,
            file_type=_classify_ext(ext),
            original_name=f.filename,
            stored_name=safe,
            rel_path=f"comparison_attachments/{safe}",
            size_bytes=len(content),
            uploaded_by=user.username,
        )
        db.add(a)
        out.append(a)
    db.commit()
    for a in out:
        db.refresh(a)
    return {"items": [_ser_attachment(a) for a in out], "total": len(out)}


@router.get("/attachments/{aid}")
def get_attachment(aid: int, inline: bool = True, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """inline=True（默认）→ 预览（Content-Disposition: inline）；inline=False → 下载。"""
    a = db.get(ComparisonAttachment, aid)
    if not a:
        raise HTTPException(404, "附件不存在")
    full = DATA_DIR / a.rel_path
    if not full.exists():
        raise HTTPException(404, "文件已丢失")
    media = "application/octet-stream"
    if a.file_type == "image":
        media = f"image/{os.path.splitext(a.stored_name)[1].lstrip('.').lower() or 'jpeg'}"
        if media == "image/jpg":
            media = "image/jpeg"
    elif a.file_type == "pdf":
        media = "application/pdf"
    disp = "inline" if inline else "attachment"
    return FileResponse(
        str(full), media_type=media, filename=a.original_name,
        headers={"Content-Disposition": f'{disp}; filename="{a.original_name}"'},
    )


@router.delete("/attachments/{aid}")
def delete_attachment(aid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    a = db.get(ComparisonAttachment, aid)
    if not a:
        raise HTTPException(404, "附件不存在")
    try:
        full = DATA_DIR / a.rel_path
        if full.exists():
            full.unlink()
    except Exception:
        pass
    db.delete(a)
    db.commit()
    return {"ok": True}


router.include_router(_plan_router)
