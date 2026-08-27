"""性能验证报告归档：CRUD + 模板驱动生成 xlsx 报告。

生成逻辑见 services/verification_report_gen.py（openpyxl 填主封面 + 原始数据，
保留模板公式与格式，产出与 51-HBsAg/2.ALP 完全一致的报告）。
"""
import io
import json

from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import persist_get_path, persist_save, persist_delete
from ...models.report_archive import ReportArchive
from ...models.user import User
from ...models.verification_report import VerificationReport
from ...core.crud_base import paginate
from ...services.verification_calc import compute_verification, normalize_conclusion_summary, _extract_first_pct
from ...schemas import (
    VerificationReportCreate,
    VerificationReportRead,
    VerificationReportUpdate,
)

router = make_router(
    VerificationReport,
    VerificationReportRead,
    VerificationReportCreate,
    VerificationReportUpdate,
    search_fields=["project_name", "instrument", "instrument_model"],
    json_fields=["verify_items", "data", "result_summary"],
    prefix="/verification-reports",
    order_by=[VerificationReport.id.desc()],
    write_roles=("admin", "specialty_leader"),
)


def _serialize_report(rec: VerificationReport) -> dict:
    d = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for f in ("verify_items", "data", "result_summary"):
        raw = d.get(f)
        if isinstance(raw, str) and raw.strip():
            try:
                d[f] = json.loads(raw)
            except Exception:
                d[f] = [] if f == "verify_items" else {}
        elif raw is None:
            d[f] = [] if f == "verify_items" else {}
    return d


def _lookup_tea(db: Session, project_name: str) -> str:
    """按项目名从质量要求库（QualityRequirement）查 TEa，WS/T 403-2024 优先。

    返回首个干净百分比（如 "10"），未命中返回空串（由用户手填 TEA）。
    """
    if not db or not project_name:
        return ""
    from sqlalchemy import or_
    from ...models.quality_requirement import QualityRequirement
    from ...services.verification_calc import _extract_first_pct
    try:
        rows = db.query(QualityRequirement).filter(
            or_(
                QualityRequirement.item_name == project_name,
                QualityRequirement.item_name.like(f"%{project_name}%"),
            )
        ).all()
    except Exception:
        return ""
    for src in ("wst403-2024", "bj-hr-2025", "nccl-2026"):
        for r in rows:
            if r.source == src and r.tea:
                pct = _extract_first_pct(r.tea)
                if pct is not None:
                    return f"{pct:g}"
    return ""


def _recompute_summary(rec: VerificationReport, db: Session) -> dict:
    """用最新计算引擎重算 result_summary（不落库），保证老记录也按最新格式展示。

    上传解析的记录 data 为空，直接用已存的 result_summary。
    """
    d = _serialize_report(rec)
    d = _auto_fill_result_summary(d, db)
    return d.get("result_summary") or {}


# 验证项展示顺序：定量 精密度→正确度→线性→可报告→参考区间→分析特异性；
# 定性 精密度→方法符合率→检出限→参考区间→分析特异性
_CONCLUSION_ORDER = {
    "precision": 0, "trueness": 1, "linearity": 2, "reportable": 3,
    "reference": 4, "specificity": 5, "conformity": 6, "lod": 7,
}


def _build_ordered_conclusion(v_items, r_summary, unit=""):
    """按固定顺序构建「验证结论」行（与性能验证记录页一致）。

    返回 [{key, result, conclusion}]；precision/conformity 拆两行，
    reportable 合并为单行（含稀释倍数/单位/单位换算）。
    """
    ordered = sorted(v_items, key=lambda k: _CONCLUSION_ORDER.get(k, 99))
    rows = []
    unit_suffix = f" {unit}" if unit else ""
    for k in ordered:
        if k == "precision":
            for sk in ("precision1", "precision2"):
                it = r_summary.get(sk)
                if it and (it.get("result") or it.get("conclusion")):
                    rows.append({"key": k, "result": it.get("result", ""), "conclusion": it.get("conclusion", "")})
        elif k == "conformity":
            for sk in ("conformity1", "conformity2"):
                it = r_summary.get(sk)
                if it and (it.get("result") or it.get("conclusion")):
                    rows.append({"key": k, "result": it.get("result", ""), "conclusion": it.get("conclusion", "")})
        elif k == "reportable":
            it = r_summary.get("reportable")
            if it and (it.get("result") or it.get("conclusion")):
                rows.append({"key": k, "result": it.get("result", ""), "conclusion": it.get("conclusion", "")})
            else:
                # 旧数据回退：合并 reportable1/reportable2（去掉 低限/高限 前缀）
                r1 = r_summary.get("reportable1") or {}
                r2 = r_summary.get("reportable2") or {}
                low = (r1.get("result") or "").replace("低限", "", 1).strip()
                high = (r2.get("result") or "").replace("高限", "", 1).strip()
                if low and high:
                    cons = r1.get("conclusion") if r1.get("conclusion") == r2.get("conclusion") else f"{r1.get('conclusion','')}/{r2.get('conclusion','')}"
                    rows.append({"key": k, "result": f"{low}-{high}{unit_suffix}", "conclusion": cons})
                elif low:
                    rows.append({"key": k, "result": f"{low}{unit_suffix}", "conclusion": r1.get("conclusion", "")})
                elif high:
                    rows.append({"key": k, "result": f"{high}{unit_suffix}", "conclusion": r2.get("conclusion", "")})
        else:
            it = r_summary.get(k)
            if it and (it.get("result") or it.get("conclusion")):
                rows.append({"key": k, "result": it.get("result", ""), "conclusion": it.get("conclusion", "")})
    return rows


def _auto_fill_result_summary(data: dict, db: Session = None) -> dict:
    """用后端计算引擎（services/verification_calc.py）自动计算各验证项结果与结论。

    引擎覆盖：精密度 CV、正确度偏倚、线性范围、方法符合率、检出限、
    可报告范围、参考区间、分析特异性。TEA 未填时从质量要求库联动获取。
    计算出的 result_summary 写回 data，供报告生成器静态写入模板单元格。
    """
    rs = data.get("result_summary") or {}
    data_field = data.get("data") or {}
    items = data.get("verify_items") or []
    report_type = data.get("report_type", "qualitative")

    # 上传解析（vrf_parser）的记录：data 为空，result_summary 已由解析器算好，勿重算覆盖
    if not data_field:
        return data

    # 用户自定义判定标准（向导填写，存在 data._meta 中）
    meta = data_field.get("_meta") or {}
    tea = data.get("tea") or ""
    if not tea:
        tea = _lookup_tea(db, data.get("project_name", ""))
        if tea:
            data["tea"] = tea  # 联动质量目标库写回，报告封面/汇总可见

    within_target = _extract_first_pct(meta.get("precision_within_cv_target") or "") or None
    lab_target = _extract_first_pct(meta.get("precision_lab_cv_target") or "") or None

    res = compute_verification(
        data_field, items, report_type=report_type, tea=tea,
        within_cv_target=within_target, lab_cv_target=lab_target,
        linear_low=data.get("linear_low"), linear_high=data.get("linear_high"),
        dilution=data.get("dilution"), unit=data.get("unit"),
    )
    rs.update(res["result_summary"])
    data["result_summary"] = rs
    return data


@router.post("/{report_id}/generate")
def generate_report(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """基于模板生成 xlsx 报告并存档（COS），返回文件相对路径。"""
    rec = db.get(VerificationReport, report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="报告不存在")
    from ...services.verification_report_gen import build_verification_report
    try:
        data = _serialize_report(rec)
        data = _auto_fill_result_summary(data, db)
        # 自动填的新字段写回数据库
        rec.result_summary = json.dumps(data["result_summary"], ensure_ascii=False)
        if data.get("tea"):
            rec.tea = data["tea"]
        db.commit()
        xlsx_bytes = build_verification_report(data)
    except Exception as e:  # noqa: BLE001 模板/数据异常向上暴露
        raise HTTPException(status_code=400, detail=f"生成报告失败：{e}")
    fname = f"{rec.project_name or '项目'}_性能验证_{rec.report_type}.xlsx"
    rel = persist_save("verification_reports", fname, xlsx_bytes)
    rec.report_file_path = rel
    # 自动归档到 report_archives（生成来源）
    arch = ReportArchive(
        project_name=rec.project_name,
        report_type=rec.report_type,
        source_type="generated",
        ref_report_id=rec.id,
        ref_archive_kind="verification_report",
        original_name=fname,
        file_path=rel,
        description=f"性能验证（{rec.report_type}）",
        created_by_id=user.id,
    )
    db.add(arch)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "generate", "verification_reports", rec.id, {"file": rel, "archive_id": arch.id}, request.client.host if request.client else None)
    return _serialize_report(rec)


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    request: Request,
    token: str = "",
    db: Session = Depends(get_db),
):
    user = None
    if token:
        try:
            from jose import jwt as _jwt
            from ...core.security import SECRET_KEY, ALGORITHM
            payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            uid = int(payload.get("sub"))
            user = db.get(User, uid)
        except Exception:
            pass
    if not user:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                from jose import jwt as _jwt
                from ...core.security import SECRET_KEY, ALGORITHM
                payload = _jwt.decode(auth[7:], SECRET_KEY, algorithms=[ALGORITHM])
                uid = int(payload.get("sub"))
                user = db.get(User, uid)
            except Exception:
                pass
    if not user:
        raise HTTPException(401, "认证失败")
    rec = db.get(VerificationReport, report_id)
    if not rec or not rec.report_file_path:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    # 使用 persist_get_path：本地优先 + COS 兜底（容器重启本地磁盘被清时仍可下载）
    path = persist_get_path(rec.report_file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在（本地+COS 均未找到）")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{rec.project_name or '项目'}_性能验证.xlsx",
    )


# ─── 项目维度聚合接口（独立 APIRouter，避免与 make_router 的 {item_id} 路由冲突）───
from fastapi import APIRouter
project_archive_router = APIRouter(prefix="/project-verification-archive", tags=["performance"])

# 靶机判定：同型号多台仪器，指定一台做全套验证为「靶机」，其余只做精密度+正确度-比对
_TARGET_MODELS = {"AU5821B"}
_TARGET_NOS = {"MHZYY-JYK-SM-2003"}


def _is_target(model: str, no: str) -> bool:
    return ((model or "").strip() in _TARGET_MODELS) or ((no or "").strip() in _TARGET_NOS)


@project_archive_router.get("/list-by-project")
def list_by_project(
    keyword: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按项目名聚合：每个项目（同名）取最新一份验证报告 + 历史次数。

    返回结构：[{ project_name, latest_id, latest_date, latest_instrument,
                 latest_is_target, verify_items, latest_summary, history_count,
                 all_records: [{..., is_target}], ...}]
    """
    q = db.query(VerificationReport)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(VerificationReport.project_name.like(kw))
    rows = q.order_by(VerificationReport.id.desc()).limit(2000).all()

    # 按 project_name 聚合
    grouped: dict[str, list] = {}
    for r in rows:
        key = (r.project_name or "未命名").strip()
        if not key:
            key = "未命名"
        grouped.setdefault(key, []).append(r)

    archive = []
    for pname, recs in sorted(grouped.items()):
        # 排序：靶机优先（靶机的全套结论才是代表该型号的"标准结果"），再按 id desc 取最新
        recs.sort(key=lambda x: (0 if _is_target(x.instrument_model, x.instrument_no) else 1, -x.id))
        latest = recs[0]
        try:
            v_items = json.loads(latest.verify_items) if latest.verify_items else []
        except Exception:
            v_items = []
        # 验证项按固定顺序展示（精密度→正确度→线性→可报告→参考区间→分析特异性…）
        v_items = sorted(v_items, key=lambda k: _CONCLUSION_ORDER.get(k, 99))
        try:
            r_summary = json.loads(latest.result_summary) if latest.result_summary else {}
        except Exception:
            r_summary = {}
        # 用最新计算引擎重算（不落库），再规范化为统一展示格式
        # （兼容后端计算格式与 vrf_parser 上传解析格式），保证老记录也按最新格式/顺序展示
        r_summary = _recompute_summary(latest, db)
        # 保留一份原始 r_summary：normalize 会丢 reportable1/2，糖化血红蛋白特例读取它们
        _orig_rs = r_summary
        r_summary = normalize_conclusion_summary(
            r_summary, unit=latest.unit or "", dilution=latest.dilution,
            linear_low=latest.linear_low, linear_high=latest.linear_high,
            report_type=latest.report_type, tea=latest.tea,
        )
        latest_items_summary = _build_ordered_conclusion(v_items, r_summary, latest.unit or "")
        # 可报告范围：稀释倍数 "/" 或为空（不稀释）→ 一般等同线性范围；糖化血红蛋白特殊按报告值显示
        try:
            data_field = json.loads(latest.data) if latest.data else {}
            rep_dilution = (data_field.get("reportable") or {}).get("dilution") or ""
            is_hba1c = ('糖化' in (latest.project_name or '')) or ('HbA1c' in (latest.project_name or ''))
            if rep_dilution.strip() in ("/", ""):
                if is_hba1c:
                    # 糖化血红蛋白（高效液相法）：稀释=不稀释也按报告值显示，单位「出峰面积」
                    r1 = (_orig_rs.get("reportable1") or {}) if isinstance(_orig_rs, dict) else {}
                    r2 = (_orig_rs.get("reportable2") or {}) if isinstance(_orig_rs, dict) else {}
                    low = (r1.get("result") or "").replace("低限", "", 1).strip()
                    high = (r2.get("result") or "").replace("高限", "", 1).strip()
                    if low and high:
                        cons = r1.get("conclusion") if r1.get("conclusion") == r2.get("conclusion") else (r1.get("conclusion") or r2.get("conclusion") or "")
                        latest_items_summary = [
                            {
                                "key": "reportable",
                                "result": f"{low}-{high}（出峰面积）",
                                "conclusion": cons or "符合要求",
                            } if r["key"] == "reportable" else r
                            for r in latest_items_summary
                        ]
                else:
                    lo = (latest.linear_low or "").strip()
                    hi = (latest.linear_high or "").strip()
                    unit_suffix = f" {latest.unit.strip()}" if (latest.unit or "").strip() else ""
                    if lo and hi:
                        latest_items_summary = [
                            {
                                "key": "reportable",
                                "result": f"等同线性范围{lo}-{hi}{unit_suffix}",
                                "conclusion": "无",
                            } if r["key"] == "reportable" else r
                            for r in latest_items_summary
                        ]
        except Exception:
            pass
        archive.append({
            "project_name": pname,
            "latest_id": latest.id,
            "latest_date": latest.verify_date,
            "latest_instrument": f"{latest.instrument_model or ''} {latest.instrument_no or ''}".strip(),
            "latest_is_target": _is_target(latest.instrument_model, latest.instrument_no),
            "latest_reagent": latest.reagent,
            "latest_report_type": latest.report_type,
            "verify_items": v_items,
            "latest_summary": r_summary,
            "latest_conclusion": latest.conclusion or "",
            "latest_items_summary": latest_items_summary,
            "history_count": len(recs),
            "all_records": [
                {
                    "id": r.id, "verify_date": r.verify_date,
                    "instrument_model": r.instrument_model, "instrument_no": r.instrument_no,
                    "is_target": _is_target(r.instrument_model, r.instrument_no),
                    "reagent": r.reagent, "report_type": r.report_type,
                    "verify_items": json.loads(r.verify_items) if r.verify_items else [],
                    "result_summary": json.loads(r.result_summary) if r.result_summary else {},
                }
                for r in recs
            ],
        })
    return archive


@project_archive_router.get("/conclusion-records")
def conclusion_records(
    request: Request,
    page: int = 1, page_size: int = 300,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按「记录」维度的验证列表（结构同 /verification-reports），但 result_summary 用最新引擎重算。

    用于「性能验证记录」页，保证老记录也按最新格式（前缀/单位/合并范围/稀释逻辑）展示。
    """
    query = db.query(VerificationReport)
    if q:
        query = query.filter(VerificationReport.project_name.ilike(f"%{q}%"))
    query = query.order_by(VerificationReport.id.desc())
    res = paginate(query, page, page_size)
    items = []
    for o in res["items"]:
        d = _serialize_report(o)
        raw = _recompute_summary(o, db)
        d["result_summary"] = normalize_conclusion_summary(
            raw, unit=o.unit or "", dilution=o.dilution,
            linear_low=o.linear_low, linear_high=o.linear_high,
            report_type=o.report_type, tea=o.tea,
        )
        items.append(d)
    res["items"] = items
    return res


