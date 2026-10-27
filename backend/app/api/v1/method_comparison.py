"""方法学比对（EP9-A3）：CRUD + 统计计算 + docx 报告生成/下载 + 汇总。

- 统计引擎：services/method_comparison_calc.py（纯标准库）
- 报告生成：services/method_comparison_report_gen.py（python-docx + Pillow 图表）
- 报告落盘：core.storage.persist_save（本地 + COS 双写）

注意：静态路由 /summary* 放在独立 summary_router，且必须在 router.py 中先于本模块的
make_router router 注册，否则会被 /{item_id} 抢先匹配。
"""
import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ...core._auth_helpers import get_current_group
from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import persist_get_path, persist_save
from ...models.method_comparison import MethodComparisonRecord
from ...models.report_archive import ReportArchive
from ...models.user import User
from ...schemas import MethodComparisonCreate, MethodComparisonRead, MethodComparisonUpdate
from ...services.method_comparison_calc import compute_comparison

_JSON_FIELDS = ("pairs", "result_summary")

router = make_router(
    MethodComparisonRecord,
    MethodComparisonRead,
    MethodComparisonCreate,
    MethodComparisonUpdate,
    search_fields=["project_name", "batch_name", "ref_instrument", "test_instrument"],
    json_fields=list(_JSON_FIELDS),
    prefix="/method-comparison",
    order_by=[MethodComparisonRecord.id.desc()],
    write_roles=("admin", "specialty_leader"),
    group_scoped=True,
)

# 静态路由（汇总）独立注册，需在 router.py 中先 include
summary_router = APIRouter(prefix="/method-comparison", tags=["method-comparison"])


def _serialize(rec: MethodComparisonRecord) -> dict:
    d = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for f in _JSON_FIELDS:
        raw = d.get(f)
        if isinstance(raw, str) and raw.strip():
            try:
                d[f] = json.loads(raw)
            except Exception:
                d[f] = [] if f == "pairs" else {}
        elif raw is None:
            d[f] = [] if f == "pairs" else {}
    return d


def _check_group(rec: MethodComparisonRecord, group: str):
    """组隔离：非本组记录一律 404，避免暴露存在性。

    与 crud_base._visible 口径对齐：本组可见；group_code 为空视为兼容历史数据。
    """
    if not rec:
        raise HTTPException(404, "比对记录不存在")
    if rec.group_code and rec.group_code != group:
        raise HTTPException(404, "比对记录不存在")


def _compute(rec: MethodComparisonRecord, persist: bool = True) -> dict:
    """重算并（可选）回写 result_summary / conclusion，返回带 details 的字典。"""
    d = _serialize(rec)
    res = compute_comparison(d)
    # 关键：必须回填重算后的 result_summary，否则报告生成器会用到旧结果
    d["result_summary"] = res.get("result_summary") or {}
    d["details"] = res.get("details") or {}
    if persist:
        rec.result_summary = json.dumps(d["result_summary"], ensure_ascii=False)
        rec.conclusion = d["result_summary"].get("conclusion", "") or ""
    return d


@router.post("/{rid}/compute")
def compute_one(
    rid: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    """重算统计（离群值/回归/一致性/结论），回写结果。"""
    rec = db.get(MethodComparisonRecord, rid)
    _check_group(rec, group)
    d = _compute(rec, persist=True)
    db.commit()
    db.refresh(rec)
    rs = d["result_summary"]
    if not rs.get("valid"):
        raise HTTPException(400, rs.get("message") or "计算失败，请检查样本数据")
    write_audit(db, user, "compute", "method_comparison_records", rec.id,
                {"n_used": rs.get("n_used"), "outliers": rs.get("outliers")},
                request.client.host if request.client else None)
    return d


@router.post("/{rid}/generate")
def generate_report(
    rid: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    """生成单项目 docx 报告并存档（本地 + COS）。"""
    rec = db.get(MethodComparisonRecord, rid)
    _check_group(rec, group)
    d = _compute(rec, persist=True)
    if not d["result_summary"].get("valid"):
        db.commit()
        raise HTTPException(400, d["result_summary"].get("message") or "比对结果无效，无法生成报告")
    db.commit()
    db.refresh(rec)

    from ...services.method_comparison_report_gen import build_single_report
    try:
        content = build_single_report(d)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"生成报告失败：{e}")

    fname = f"{rec.project_name or '项目'}_方法学比对_{rec.ref_instrument or 'A'}vs{rec.test_instrument or 'B'}.docx"
    rel = persist_save("method_comparison_reports", fname, content)
    rec.report_file_path = rel
    arch = ReportArchive(
        project_name=rec.project_name,
        report_type="method_comparison",
        source_type="generated",
        ref_report_id=rec.id,
        ref_archive_kind="method_comparison",
        original_name=fname,
        file_path=rel,
        description=f"方法学比对（EP9-A3，{rec.ref_instrument} vs {rec.test_instrument}）",
        created_by_id=user.id,
    )
    db.add(arch)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "generate", "method_comparison_records", rec.id,
                {"file": rel, "archive_id": arch.id},
                request.client.host if request.client else None)
    return {"ok": True, "report_file_path": rel, "archive_id": arch.id, "record": _serialize(rec)}


@router.get("/{rid}/download")
def download_report(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    """下载单项目 docx 报告（走 Authorization 头，前端 blob 下载）。"""
    rec = db.get(MethodComparisonRecord, rid)
    _check_group(rec, group)
    if not rec.report_file_path:
        raise HTTPException(404, "报告尚未生成")
    path = persist_get_path(rec.report_file_path)
    if not path.exists():
        raise HTTPException(404, "报告文件不存在（本地+COS 均未找到）")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{rec.project_name or '项目'}_方法学比对报告.docx",
    )


@router.get("/{rid}/charts")
def charts(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    """返回该记录的图表 PNG（base64），供详情页直接展示。"""
    rec = db.get(MethodComparisonRecord, rid)
    _check_group(rec, group)
    d = _compute(rec, persist=False)
    from ...services.method_comparison_report_gen import build_charts_for
    imgs = build_charts_for(d)
    return {"charts": [{"key": k, "png": base64.b64encode(v).decode("ascii")} for k, v in imgs.items()]}


# ─────────────────────────── 汇总（静态路由） ───────────────────────────
def _query_records(db: Session, group: str, ids: str = "", batch: str = "", limit: int = 200):
    q = db.query(MethodComparisonRecord)
    if group != "all_group_view":
        from sqlalchemy import or_
        q = q.filter(or_(MethodComparisonRecord.group_code == group,
                         MethodComparisonRecord.group_code == "sm",
                         MethodComparisonRecord.group_code.is_(None),
                         MethodComparisonRecord.group_code == ""))
    if ids:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(400, "ids 参数格式错误")
        q = q.filter(MethodComparisonRecord.id.in_(id_list))
    elif batch:
        q = q.filter(MethodComparisonRecord.batch_name == batch)
    return q.order_by(MethodComparisonRecord.id.asc()).limit(limit).all()


@summary_router.get("/summary")
def summary(
    ids: str = "",
    batch: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    """汇总表 JSON（前端表格用），不生成文件。"""
    recs = _query_records(db, group, ids, batch)
    items = []
    for r in recs:
        rs = _serialize(r).get("result_summary") or {}
        items.append({
            "id": r.id,
            "batch_name": r.batch_name,
            "project_name": r.project_name,
            "unit": r.unit,
            "ref_instrument": r.ref_instrument,
            "test_instrument": r.test_instrument,
            "sample_count": r.sample_count,
            "compare_date": r.compare_date,
            "operator": r.operator,
            "reviewer": r.reviewer,
            "report_file_path": r.report_file_path,
            "valid": rs.get("valid"),
            "n_used": rs.get("n_used"),
            "outliers": rs.get("outliers"),
            "systematic_bias": rs.get("systematic_bias"),
            "proportional_bias_pct": rs.get("proportional_bias_pct"),
            "acceptable": rs.get("acceptable"),
            "ba_p": rs.get("ba_p"),
            "ba_consistent": rs.get("ba_consistent"),
            "ba_max_abs_within": rs.get("ba_max_abs_within"),
            "can_replace": rs.get("can_replace"),
            "conclusion": rs.get("conclusion"),
        })
    return {"items": items, "total": len(items)}


@summary_router.get("/summary/download")
def summary_download(
    ids: str = "",
    batch: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    """生成并下载汇总 docx（汇总表 + 各项目原始结果）。"""
    recs = _query_records(db, group, ids, batch)
    if not recs:
        raise HTTPException(404, "无可汇总的比对记录")
    ctx = []
    for r in recs:
        d = _compute(r, persist=True)
        if d["result_summary"].get("valid"):
            ctx.append(d)
    db.commit()
    if not ctx:
        raise HTTPException(400, "所选记录均无有效比对结果")

    from ...services.method_comparison_report_gen import build_summary_report
    try:
        content = build_summary_report(ctx)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"生成汇总报告失败：{e}")
    name = f"方法学比对汇总_{ctx[0].get('batch_name') or ctx[0].get('compare_date') or '汇总'}.docx"
    rel = persist_save("method_comparison_reports", name, content)
    path = persist_get_path(rel)
    write_audit(db, user, "summary", "method_comparison_records", 0,
                {"count": len(ctx), "file": rel}, None)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=name,
    )
