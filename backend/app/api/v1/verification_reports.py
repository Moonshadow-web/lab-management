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


def _auto_fill_result_summary(data: dict) -> dict:
    """从 data 自动计算缺失的 result_summary 字段（让结论表无空值）。

    - precision1：批内 CV（每个水平的天内 3 次重复 SD/均值，再跨天平均；分别按水平报）
    - precision2：实验室内 CV（每个水平全部数据 SD/均值；分别按水平报）
    - reportable1/reportable2：可报告低/高限靶值
    - reference：参考区间每组超出统计
    - specificity：从 items 拼出"干扰物 名 ≤限量 实测偏倚"细分（取代笼统的"符合厂家声明"）
    """
    import statistics as _stats

    rs = data.get("result_summary") or {}
    data_field = data.get("data") or {}
    items = data.get("verify_items") or []

    # ─── 精密度：按水平分别算批内 CV / 实验室内 CV，拼成"低值 X 高值 Y" ───
    # 重算条件：老格式是"CV X%"开头（解析器写的），新格式以"低值"开头；若已是新格式则跳过
    _prec_old = rs.get("precision1", {}).get("result", "")
    _need_prec = "precision" in items and (not _prec_old or _prec_old.startswith("CV "))
    if _need_prec:
        prec_levels = (data_field.get("precision") or {}).get("levels") or []
        runs_in = []   # 水平1 批内CV
        days_in = []   # 水平1 实验室内CV
        runs_in2 = []  # 水平2 批内CV
        days_in2 = []  # 水平2 实验室内CV
        for idx, lv in enumerate(prec_levels[:2]):
            # 兼容两种字段名：days（解析器）和 rows（前端向导）
            days = lv.get("days") or lv.get("rows") or []
            if not days:
                continue
            day_means = []
            day_cv_list = []
            for day in days:
                nums = [float(v) for v in day if v not in (None, "")]
                if len(nums) >= 2:
                    m = sum(nums) / len(nums)
                    sd = _stats.pstdev(nums) if len(nums) >= 2 else 0
                    if m:
                        day_cv_list.append(sd / m * 100)
                    day_means.append(m)
            all_nums = [float(v) for d in days for v in d if v not in (None, "")]
            if len(all_nums) >= 2:
                m_all = sum(all_nums) / len(all_nums)
                sd_all = _stats.pstdev(all_nums)
                cv_lab = (sd_all / m_all * 100) if m_all else 0
            else:
                cv_lab = 0
            cv_run = sum(day_cv_list) / len(day_cv_list) if day_cv_list else 0
            if idx == 0:
                runs_in.append(cv_run); days_in.append(cv_lab)
            else:
                runs_in2.append(cv_run); days_in2.append(cv_lab)

        def _fmt(r1, r2):
            a = f"低值{r1:.2f}%" if r1 else ""
            b = f"高值{r2:.2f}%" if r2 else ""
            if a and b: return f"{a} {b}"
            return a or b or ""

        # precision1 = 批内 CV；precision2 = 实验室内 CV
        if runs_in or runs_in2:
            rs["precision1"] = {
                "result": _fmt(runs_in[0] if runs_in else 0, runs_in2[0] if runs_in2 else 0),
                "conclusion": "符合要求",
            }
        if days_in or days_in2:
            rs["precision2"] = {
                "result": _fmt(days_in[0] if days_in else 0, days_in2[0] if days_in2 else 0),
                "conclusion": "符合要求",
            }

    # 可报告范围：低限/高限
    if "reportable" in items and not rs.get("reportable1"):
        rep = data_field.get("reportable") or {}
        low = (rep.get("low") or {}).get("target", "")
        high = (rep.get("high") or {}).get("target", "")
        if low:
            rs["reportable1"] = {"result": f"低限 {low}", "conclusion": "符合要求"}
        if high:
            rs["reportable2"] = {"result": f"高限 {high}", "conclusion": "符合要求"}

    # 参考区间：每组超出统计
    if "reference" in items and not rs.get("reference"):
        ref = data_field.get("reference") or {}
        groups = ref.get("groups") or []
        if groups:
            outs = [g.get("out", "0") for g in groups]
            txt = "、".join([f"{g.get('name','')}超出{out}" for g, out in zip(groups, outs)])
            rs["reference"] = {
                "result": f"{txt}，每组≤2个",
                "conclusion": "符合要求",
            }

    # ─── 分析特异性：从 items 拼出具体阈值（细到每个干扰物） ───
    # 重算条件：当前是兜底"符合厂家声明"或没值时，重算为"物品名 限量 实测"明细
    _spec_old = rs.get("specificity", {}).get("result", "")
    _need_spec = (
        "specificity" in items
        and (not _spec_old or "符合厂家声明" in _spec_old or "符合" == _spec_old.strip())
    )
    if _need_spec:
        spec_items = (data_field.get("specificity") or {}).get("items") or []
        # 过滤掉空行（只有名字没用）
        filled = [it for it in spec_items if (it.get("limit") or it.get("measured"))]
        if filled:
            parts = []
            for it in filled:
                nm = (it.get("name") or "").strip()
                lm = (it.get("limit") or "").strip()
                ms = (it.get("measured") or "").strip()
                seg = nm
                if lm:
                    seg += f" {lm}"
                if ms and ms != "符合要求" and ms != "不符合要求":
                    seg += f"  实测{ms}"
                parts.append(seg)
            rs["specificity"] = {
                "result": "；".join(parts) or "抗干扰能力符合厂家声明",
                "conclusion": "符合要求",
            }

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
        data = _auto_fill_result_summary(data)
        # 自动填的新字段写回数据库
        rec.result_summary = json.dumps(data["result_summary"], ensure_ascii=False)
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


# ─── 项目维度聚合接口（独立 prefix 避免与 {item_id} 路由冲突）───
project_archive_router = make_router(
    VerificationReport, VerificationReportRead, VerificationReportCreate,
    VerificationReportUpdate,
    search_fields=["project_name", "instrument", "instrument_model"],
    prefix="/project-verification-archive",
    order_by=[VerificationReport.id.desc()],
)


@project_archive_router.get("/list-by-project")
def list_by_project(
    keyword: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按项目名聚合：每个项目（同名）取最新一份验证报告 + 历史次数。

    返回结构：[{ project_name, latest_id, latest_date, latest_instrument,
                 verify_items, latest_summary, history_count, all_records: [...] }, ...]
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
        recs.sort(key=lambda x: x.id, reverse=True)
        latest = recs[0]
        try:
            v_items = json.loads(latest.verify_items) if latest.verify_items else []
        except Exception:
            v_items = []
        try:
            r_summary = json.loads(latest.result_summary) if latest.result_summary else {}
        except Exception:
            r_summary = {}
        latest_items_summary = []
        for k in v_items:
            if k in r_summary and r_summary[k].get("result"):
                latest_items_summary.append({
                    "key": k, "result": r_summary[k]["result"],
                    "conclusion": r_summary[k].get("conclusion", ""),
                })
        archive.append({
            "project_name": pname,
            "latest_id": latest.id,
            "latest_date": latest.verify_date,
            "latest_instrument": f"{latest.instrument_model or ''} {latest.instrument_no or ''}".strip(),
            "latest_reagent": latest.reagent,
            "latest_report_type": latest.report_type,
            "verify_items": v_items,
            "latest_summary": r_summary,
            "latest_items_summary": latest_items_summary,
            "history_count": len(recs),
            "all_records": [
                {
                    "id": r.id, "verify_date": r.verify_date,
                    "instrument_model": r.instrument_model, "instrument_no": r.instrument_no,
                    "reagent": r.reagent, "report_type": r.report_type,
                    "verify_items": json.loads(r.verify_items) if r.verify_items else [],
                    "result_summary": json.loads(r.result_summary) if r.result_summary else {},
                }
                for r in recs
            ],
        })
    return archive


