import csv
import io
import os
import re
import tempfile
import datetime

from fastapi import Depends, File, HTTPException, Request, UploadFile, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import storage
from ...models.qc import QCMonthlySummary, QCDailyValue, QCMonthlyReport
from ...models.instrument import Instrument
from ...models.user import User
from ...schemas import (
    QCMonthlySummaryCreate,
    QCMonthlySummaryRead,
    QCMonthlySummaryUpdate,
    QCDailyValueRead,
    QCMonthlyReportRead,
    QCMonthlyReportUpdate,
)
from ...services.qc_service import aggregate, lookup_quality_goal, draft_report

router = make_router(
    QCMonthlySummary,
    QCMonthlySummaryRead,
    QCMonthlySummaryCreate,
    QCMonthlySummaryUpdate,
    search_fields=["test_item", "lot_no", "level", "instrument"],
    filter_fields=["year", "month", "instrument", "instrument_id", "test_item", "lot_no"],
    prefix="/qc-summaries",
    write_roles=("admin", "qc_manager", "member"),
    delete_roles=("admin", "qc_manager"),
)


@router.get("/instruments")
def qc_instruments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """月结下拉专用：仅返回室内质控受控仪器（instruments.qc_instrument=True），
    按科室编号自然序返回 {id, name, dept_no, model}。"""
    from sqlalchemy import func as _func
    rows = (
        db.query(Instrument)
        .filter(Instrument.qc_instrument == True)  # noqa: E712
        .order_by(_func.doc_number_sort(Instrument.dept_no), Instrument.dept_no)
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "dept_no": r.dept_no, "model": r.model}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 列名别名（兼容不同 LIS 导出）
# ---------------------------------------------------------------------------
_COLUMN_ALIASES = {
    # 注意 test_item 优先取 itemName（中文全名，如「艾滋病」），其次 testCommon（代码，如 HIV）
    "test_item": ["项目", "检验项目", "项目名称", "item", "test_item", "name",
                  "itemname", "testcommon", "检验名称", "测试项目"],
    "lot_no": ["批号", "质控批号", "lot", "lot_no", "批", "batch"],
    "level": ["水平", "level", "浓度水平", "testname"],
    "unit": ["单位", "unit"],
    "instrument": ["仪器", "instrument", "设备", "deviceid", "仪器代码", "设备编号"],
    "qc_date": ["日期", "质控日期", "测定日期", "date", "qc_date", "testdate", "测定时间", "检测时间"],
    # 注意：爱康导出的 averageValue 是「靶值/定值」（同一项目-水平为常量），逐次实测值在
    # result 列；故 value 取 result，averageValue 归入 target_mean，standardDeviation 归入 target_sd。
    "value": ["测值", "测定值", "浓度", "value", "结果", "result"],
    "target_mean": ["靶值", "定值", "靶值均值", "target", "target_mean", "averagevalue"],
    "target_sd": ["靶值sd", "靶值sd", "sd", "标准差", "target_sd", "standarddeviation"],
    # 失控元数据（来自 LIS 导出）：operatorPersonName→操作人，violateReason→失控原因，violateDeal→失控处理
    "operator": ["操作人", "操作者", "operator", "operatorpersonname", "operatorname", "检验者"],
    "violate_reason": ["失控原因", "violatereason", "失控理由", "reason"],
    "violate_deal": ["失控处理", "violatedeal", "处理", "deal", "处置"],
}


def _norm_header(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "")


def _build_header_map(headers):
    """返回 {标准字段名: 列索引}。"""
    norm = {_norm_header(h): i for i, h in enumerate(headers)}
    mapping = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for al in aliases:
            key = _norm_header(al)
            if key in norm:
                mapping[field] = norm[key]
                break
    return mapping


def _to_float(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m", "%Y/%m", "%Y.%m"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    m = re.search(r"(\d{4})[^\d]*(\d{1,2})", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return datetime.datetime(y, mo, 1)
    return None


def _read_rows(file_bytes: bytes, filename: str):
    """返回 list[dict]，键为标准化字段名。

    解析策略：
    - 真实 xlsx（zip 包，magic=PK）走 openpyxl；
    - 其它情况（含伪装成 .xls 的 TSV/CSV 文本、乃至非法的 .xls）一律降级为文本解析，
      自动探测分隔符（Tab 优先于逗号）并按 utf-8/utf-8-sig/gbk 容错解码。
    """
    name = (filename or "").lower()
    is_zip = file_bytes[:2] == b"PK"
    if name.endswith(".xlsx") or is_zip:
        try:
            import openpyxl
        except ImportError:
            raise HTTPException(status_code=400, detail="服务器未安装 openpyxl，无法解析 xlsx")
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            headers = [str(h) if h is not None else "" for h in rows[0]]
            out = []
            for r in rows[1:]:
                if r is None:
                    continue
                out.append({headers[i]: (r[i] if i < len(r) else None) for i in range(len(headers))})
            return out
        except Exception:
            # 不是合法 xlsx（例如 .xls 后缀实为文本），落到下方文本解析分支
            pass
    # 文本解析（utf-8 / utf-8-sig / gbk 容错）
    text = None
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(
            status_code=400,
            detail="无法解码文件（请使用 UTF-8、GBK 编码的 CSV/TSV 或标准 xlsx）",
        )
    lines = text.splitlines()
    sample = lines[0] if lines else ""
    delim = "\t" if ("\t" in sample and sample.count("\t") >= sample.count(",")) else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return [dict(row) for row in reader]


def _find_report(db: Session, instrument_id, instrument: str, year: int, month: int):
    q = db.query(QCMonthlyReport).filter_by(year=year, month=month)
    if instrument_id:
        q = q.filter_by(instrument_id=instrument_id)
    else:
        q = q.filter_by(instrument=(instrument or ""))
    return q.first()


def _fetch_report(db: Session, instrument_id, instrument: str, year: int, month: int):
    return _find_report(db, instrument_id, instrument, year, month)


def _ensure_report_draft(db: Session, instrument_id, instrument: str, year: int, month: int):
    """若报告不存在则按当前数据草拟一份（不覆盖已有编辑）。"""
    if _find_report(db, instrument_id, instrument, year, month):
        return
    q = db.query(QCMonthlySummary).filter_by(year=year, month=month)
    if instrument_id:
        q = q.filter_by(instrument_id=instrument_id)
    else:
        q = q.filter_by(instrument=(instrument or ""))
    summaries = q.all()
    if not summaries:
        rep = QCMonthlyReport(instrument_id=instrument_id, instrument=instrument or "", year=year, month=month)
        db.add(rep)
        db.commit()
        return
    sids = [s.id for s in summaries]
    dvs = db.query(QCDailyValue).filter(QCDailyValue.summary_id.in_(sids)).all()
    daily = {}
    for dv in dvs:
        daily.setdefault(dv.summary_id, []).append(dv)
    drafted = draft_report(instrument or summaries[0].instrument, year, month, summaries, daily)
    rep = QCMonthlyReport(
        instrument_id=instrument_id,
        instrument=instrument or summaries[0].instrument,
        instrument_no=summaries[0].instrument_no,
        year=year, month=month, **drafted,
    )
    db.add(rep)
    db.commit()


@router.post("/upload", status_code=201)
def upload_qc_summary(
    file: UploadFile = File(...),
    instrument_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传 LIS 导出的 CSV/XLSX（含每日测值），解析并按 (年,月,项目,批号,水平)
    分组聚合，自动跑 Westgard 判定失控点，存入 qc_monthly_summaries + qc_daily_values。
    同名(同维度)月结自动覆盖重算。

    instrument_id（必填）：受控仪器（绑定 instruments 表）。该文件全部数据归于此仪器，
    文件中的仪器代码（deviceId 等）一律忽略，不会单独作为仪器生成总结。
    """
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    rows = _read_rows(content, file.filename)
    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有数据行")

    headers = list(rows[0].keys())
    hmap = _build_header_map(headers)
    if "value" not in hmap or "qc_date" not in hmap:
        raise HTTPException(
            status_code=400,
            detail="未识别到必要列（测值/日期）。当前识别映射：" + str(hmap),
        )
    if "test_item" not in hmap:
        raise HTTPException(status_code=400, detail="未识别到「项目」列。当前识别映射：" + str(hmap))

    # 受控仪器（必填）：文件中的仪器代码不允许单独成一台仪器出总结
    if not instrument_id:
        raise HTTPException(
            status_code=400,
            detail="请先在『质控仪器』下拉中选择真实受控仪器后再上传；文件中的仪器代码不会单独作为仪器生成总结。",
        )
    sel_inst = db.get(Instrument, instrument_id)
    if not sel_inst:
        raise HTTPException(status_code=400, detail=f"instrument_id={instrument_id} 对应的仪器不存在")
    sel_inst_no = sel_inst.dept_no or ""

    groups: dict[tuple, list[float]] = {}
    meta: dict[tuple, dict] = {}
    daily_meta: dict[tuple, list] = {}
    block_keys: set[tuple] = set()  # (instrument_id, instrument, year, month)

    for row in rows:
        def get(field):
            idx = hmap.get(field)
            return row.get(headers[idx]) if idx is not None else None

        d = _parse_date(get("qc_date"))
        v = _to_float(get("value"))
        if d is None or v is None:
            continue
        ti = (get("test_item") or "").strip()
        lot = (get("lot_no") or "").strip()
        lvl = (get("level") or "").strip()
        # 仪器只取用户选定的真实受控仪器；文件中的仪器代码忽略，不单独成仪器
        inst = sel_inst.name
        inst_no = sel_inst_no
        key = (d.year, d.month, ti, lot, lvl, inst)
        groups.setdefault(key, [])
        groups[key].append(v)
        op = (get("operator") or "").strip()
        vreason = (get("violate_reason") or "").strip()
        vdeal = (get("violate_deal") or "").strip()
        daily_meta.setdefault(key, []).append((d.strftime("%Y-%m-%d"), v, op, vreason, vdeal))
        if key not in meta:
            meta[key] = {
                "unit": (get("unit") or "").strip(),
                "target_mean": _to_float(get("target_mean")) or 0.0,
                "target_sd": _to_float(get("target_sd")) or 0.0,
                "instrument_no": inst_no,
            }
        block_keys.add((instrument_id if sel_inst else None, inst, d.year, d.month))

    created = 0
    updated = 0
    items = []
    for key, values in groups.items():
        year, month, test_item, lot_no, level, instrument = key
        m = meta[key]
        tm = m["target_mean"]
        ts = m["target_sd"]
        agg = aggregate(values, tm, ts)
        if not tm and not ts:
            # 未提供靶值：用本批实测均值/标准差回填，保证报表可读
            tm = agg["mean"]
            ts = agg["sd"]
        target_cv = (ts / tm * 100) if tm else 0.0
        quality_goal = lookup_quality_goal(test_item)
        existing = (
            db.query(QCMonthlySummary)
            .filter_by(year=year, month=month, test_item=test_item, lot_no=lot_no, level=level, instrument=instrument)
            .first()
        )
        if existing:
            summ = existing
            updated += 1
        else:
            summ = QCMonthlySummary()
            db.add(summ)
            created += 1
        summ.year = year
        summ.month = month
        summ.test_item = test_item
        summ.unit = m["unit"]
        summ.lot_no = lot_no
        summ.level = level
        summ.instrument = instrument
        summ.instrument_id = instrument_id if sel_inst else None
        summ.instrument_no = m["instrument_no"]
        summ.target_mean = tm
        summ.target_sd = ts
        summ.target_cv = target_cv
        summ.mean = agg["mean"]
        summ.sd = agg["sd"]
        summ.cv = agg["cv"]
        summ.n = agg["n"]
        summ.out_of_control_count = agg["out_of_control_count"]
        summ.in_control_rate = agg["in_control_rate"]
        summ.quality_goal = quality_goal
        db.flush()
        # 重写每日测值（daily_meta[key] 与 values 同序，索引对齐 ooc）
        db.query(QCDailyValue).filter_by(summary_id=summ.id).delete()
        operators = set()
        ooc_details = []
        for idx, (qc_date, val, op, vreason, vdeal) in enumerate(daily_meta[key]):
            rule = agg["ooc"].get(idx, "")
            if op:
                operators.add(op)
            if rule:
                parts = []
                if vreason:
                    parts.append(f"原因：{vreason}")
                if vdeal:
                    parts.append(f"处理：{vdeal}")
                detail = f"{qc_date} {test_item}({level}) 失控「{rule}」"
                if parts:
                    detail += "；" + "；".join(parts)
                ooc_details.append(detail)
            db.add(
                QCDailyValue(
                    summary_id=summ.id,
                    qc_date=qc_date,
                    value=val,
                    is_out_of_control=bool(rule),
                    rule_violated=rule,
                    operator=(op or ""),
                    violate_reason=(vreason or "") if rule else "",
                    violate_deal=(vdeal or "") if rule else "",
                )
            )
        summ.operator = "、".join(sorted(operators))
        summ.handling_note = "\n".join(ooc_details)
        items.append({
            "id": summ.id, "year": year, "month": month, "test_item": test_item,
            "lot_no": lot_no, "level": level, "instrument": instrument,
            "instrument_id": summ.instrument_id, "instrument_no": summ.instrument_no,
            "n": agg["n"], "out_of_control_count": agg["out_of_control_count"],
            "in_control_rate": round(agg["in_control_rate"], 4),
        })

    db.commit()
    write_audit(db, user, "import", "qc_monthly_summaries", 0,
                {"file": file.filename, "created": created, "updated": updated})
    # 为每个 (仪器, 年, 月) 块确保存在文字报告草稿（不覆盖已有编辑）
    for (bid, inst, y, mo) in block_keys:
        try:
            _ensure_report_draft(db, bid, inst, y, mo)
        except Exception:
            db.rollback()
    return {
        "ok": True,
        "created": created,
        "updated": updated,
        "groups": len(groups),
        "items": items,
    }


@router.get("/{summary_id}/daily", response_model=list[QCDailyValueRead])
def list_daily(
    summary_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(QCDailyValue)
        .filter(QCDailyValue.summary_id == summary_id)
        .order_by(QCDailyValue.qc_date)
        .all()
    )


@router.post("/{summary_id}/pdf", status_code=201)
def upload_qc_pdf(
    summary_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """为某月结上传/替换质控图 PDF（源文件存档，月结页内嵌预览）。"""
    summ = db.get(QCMonthlySummary, summary_id)
    if not summ:
        raise HTTPException(status_code=404, detail="未找到月结记录")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    rel = storage.save("qc_qccharts", file.filename or "qcchart.pdf", content)
    if summ.pdf_path:
        storage.delete(summ.pdf_path)
    summ.pdf_path = rel
    summ.pdf_filename = file.filename or "qcchart.pdf"
    db.commit()
    write_audit(db, user, "create", "qc_monthly_summaries", summ.id, {"pdf": rel})
    return {"id": summ.id, "pdf_path": summ.pdf_path, "pdf_filename": summ.pdf_filename}


@router.get("/{summary_id}/pdf")
def download_qc_pdf(
    summary_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    summ = db.get(QCMonthlySummary, summary_id)
    if not summ or not summ.pdf_path:
        raise HTTPException(status_code=404, detail="未找到质控图")
    p = storage.get_path(summ.pdf_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(p, filename=summ.pdf_filename or p.name, headers={"Cache-Control": "no-store"})


@router.delete("/{summary_id}/pdf")
def delete_qc_pdf(
    summary_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    summ = db.get(QCMonthlySummary, summary_id)
    if not summ:
        raise HTTPException(status_code=404, detail="未找到月结记录")
    if summ.pdf_path:
        storage.delete(summ.pdf_path)
    summ.pdf_path = ""
    summ.pdf_filename = ""
    db.commit()
    return {"ok": True}


@router.get("/report", response_model=QCMonthlyReportRead)
def get_qc_report(
    instrument_id: int | None = None,
    instrument: str = "",
    year: int = 0,
    month: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取某(仪器,年,月)的月结文字报告；不存在则按当前数据自动草拟并保存。"""
    rep = _find_report(db, instrument_id, instrument, year, month)
    if rep:
        return rep
    # 自动草拟
    q = db.query(QCMonthlySummary).filter_by(year=year, month=month)
    if instrument_id:
        q = q.filter_by(instrument_id=instrument_id)
    else:
        q = q.filter_by(instrument=(instrument or ""))
    summaries = q.all()
    if not summaries:
        rep = QCMonthlyReport(instrument_id=instrument_id, instrument=instrument or "", year=year, month=month)
        db.add(rep)
        db.commit()
        db.refresh(rep)
        return rep
    sids = [s.id for s in summaries]
    dvs = db.query(QCDailyValue).filter(QCDailyValue.summary_id.in_(sids)).all()
    daily = {}
    for dv in dvs:
        daily.setdefault(dv.summary_id, []).append(dv)
    drafted = draft_report(instrument or summaries[0].instrument, year, month, summaries, daily)
    rep = QCMonthlyReport(
        instrument_id=instrument_id,
        instrument=instrument or summaries[0].instrument,
        instrument_no=summaries[0].instrument_no,
        year=year, month=month, **drafted,
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


@router.put("/report", response_model=QCMonthlyReportRead)
def upsert_qc_report(
    body: QCMonthlyReportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新建或更新月结文字报告（检验人编辑后保存）。"""
    rep = _find_report(db, body.instrument_id, body.instrument, body.year, body.month)
    if not rep:
        rep = QCMonthlyReport()
        db.add(rep)
    rep.instrument_id = body.instrument_id
    rep.instrument = body.instrument
    rep.instrument_no = body.instrument_no
    rep.year = body.year
    rep.month = body.month
    rep.operation_status = body.operation_status or ""
    rep.drift_trend = body.drift_trend or ""
    rep.cv_setting_ok = body.cv_setting_ok or ""
    rep.cv_calc_ok = body.cv_calc_ok or ""
    rep.freq_ok = body.freq_ok or ""
    db.commit()
    db.refresh(rep)
    return rep


@router.get("/export")
def export_qc_summary(
    year: int | None = None,
    month: int | None = None,
    instrument: str | None = None,
    instrument_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出 CZ-012 室内质控月小结 Excel（14 列表格 + 文字部分），按 仪器/年/月 分块。

    - instrument_id / instrument：仅导出该台仪器的分块（逐台留档/上交）。
    - 每块表格之后附加「文字部分」：仪器运行情况、漂移趋势、CV%设置达标、
      计算CV%达标、质控频次达标。
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side

    q = db.query(QCMonthlySummary)
    if year is not None:
        q = q.filter(QCMonthlySummary.year == year)
    if month is not None:
        q = q.filter(QCMonthlySummary.month == month)
    if instrument_id:
        q = q.filter(QCMonthlySummary.instrument_id == instrument_id)
    elif instrument:
        q = q.filter(QCMonthlySummary.instrument == instrument)
    summaries = q.order_by(
        QCMonthlySummary.instrument, QCMonthlySummary.year,
        QCMonthlySummary.month, QCMonthlySummary.test_item, QCMonthlySummary.level,
    ).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "室内质控月小结"
    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_font = Font(bold=True)
    title_font = Font(bold=True, size=14)
    center = Alignment(horizontal="center", vertical="center")
    left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)

    headers = ["项目", "质控批号", "单位", "水平", "靶值", "靶值SD", "靶值CV%",
               "均值", "SD", "CV%", "n", "失控数", "在控率", "质量目标（允许不精密度）"]

    # 按 (仪器, 年, 月) 分块
    blocks: dict[tuple, list] = {}
    for s in summaries:
        blocks.setdefault((s.instrument, s.year, s.month), []).append(s)

    row = 1
    for (instrument, y, mo), items in blocks.items():
        inst_no = items[0].instrument_no or ""
        ws.cell(row=row, column=1, value="生化免疫组室内质控月小结").font = title_font
        row += 1
        ws.cell(row=row, column=1,
                value=f"{y or '—'}年{str(mo).zfill(2) if mo else '—'}月　　仪器：{instrument or '—'}{('（编号：' + inst_no + '）') if inst_no else ''}")
        row += 1
        # 质控批号已在表格列中体现，不单独成句
        # 表头
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.font = header_font
            cell.alignment = center
            cell.border = border
        row += 1
        for s in items:
            vals = [
                s.test_item, s.lot_no, s.unit, s.level,
                round(s.target_mean, 4), round(s.target_sd, 4), f"{s.target_cv:.2f}%",
                round(s.mean, 4), round(s.sd, 4), f"{s.cv:.2f}%",
                s.n, s.out_of_control_count, f"{s.in_control_rate*100:.1f}%",
                s.quality_goal,
            ]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(row=row, column=c, value=v)
                cell.alignment = center
                cell.border = border
            row += 1
        # 文字部分
        rep = _fetch_report(db, items[0].instrument_id, instrument, y, mo)
        text_sections = [
            ("一、仪器运行情况", rep.operation_status if rep else ""),
            ("二、各项目是否出现漂移或趋势性改变", rep.drift_trend if rep else ""),
            ("三、各项目CV%设置是否达标", rep.cv_setting_ok if rep else ""),
            ("四、各项目计算CV%是否达标", rep.cv_calc_ok if rep else ""),
            ("五、各项目质控频次是否达标", rep.freq_ok if rep else ""),
        ]
        for label, text in text_sections:
            ws.cell(row=row, column=1, value=label).font = Font(bold=True)
            ws.cell(row=row, column=1).alignment = left_wrap
            tc = ws.cell(row=row, column=2, value=text or "（未填写）")
            tc.alignment = left_wrap
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=14)
            row += 1
        row += 1  # 块间空行

    # 列宽
    widths = [16, 12, 8, 8, 10, 10, 10, 10, 10, 10, 6, 8, 10, 22]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    fname = f"室内质控月小结_{year or 'ALL'}_{month or 'ALL'}"
    if instrument_id:
        fname += f"_{instrument_id}"
    elif instrument:
        fname += f"_{instrument}"
    fname += ".xlsx"
    from urllib.parse import quote
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"},
    )


# ---------------------------------------------------------------------------
# 路由重排（必须放在所有路由定义之后）：把不含路径参数（{...}）的静态路由
# （/upload、/export、/report）排到最前，避免被 make_router 生成的
# GET /{item_id} 等参数路由吞掉（否则 /export、/report 被当成 int 解析 → 422）。
# sort 稳定，保持组内相对顺序。
# ---------------------------------------------------------------------------
router.routes.sort(key=lambda r: ("{" in getattr(r, "path", ""),))


@router.get("/report/docx")
def export_qc_report_docx(
    year: int = 0,
    month: int = 0,
    instrument_id: int | None = None,
    instrument: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出 CZ-012 室内质控月小结 Word（A4 横向，含 14 列表格 + 五段文字部分）。

    - instrument_id / instrument：仅导出该台仪器的月小结（逐台留档/上交）。
    - 文字部分取自 qc_monthly_reports（无则留空，由人工补录）。
    """
    from ...services.qc_report import build_docx
    from types import SimpleNamespace

    q = db.query(QCMonthlySummary).filter_by(year=year, month=month)
    if instrument_id:
        q = q.filter(QCMonthlySummary.instrument_id == instrument_id)
    elif instrument:
        q = q.filter(QCMonthlySummary.instrument == instrument)
    summaries = q.order_by(QCMonthlySummary.test_item, QCMonthlySummary.level).all()
    if not summaries:
        raise HTTPException(status_code=404, detail="该(仪器,年,月)暂无月结数据")

    inst_name = summaries[0].instrument or ""
    inst_no = summaries[0].instrument_no or ""
    rep = _find_report(db, instrument_id, instrument, year, month)
    if rep is None:
        # 报告尚未保存时，按当前数据临时草拟一份（不持久化）供导出，避免 build_docx 接收 None
        dvs = db.query(QCDailyValue).filter(QCDailyValue.summary_id.in_([s.id for s in summaries])).all()
        daily = {}
        for dv in dvs:
            daily.setdefault(dv.summary_id, []).append(dv)
        drafted = draft_report(inst_name or summaries[0].instrument, year, month, summaries, daily)
        rep = SimpleNamespace(**drafted)

    fd, out_path = tempfile.mkstemp(suffix=".docx", prefix=f"cz012_{year}_{month}_")
    os.close(fd)
    try:
        build_docx(out_path, summaries, rep, inst_name, inst_no, year, month)
        fname = f"室内质控月小结_{year}年{str(month).zfill(2)}月"
        if instrument_id:
            fname += f"_{instrument_id}"
        elif instrument:
            fname += f"_{instrument}"
        fname += ".docx"
        from urllib.parse import quote
        return FileResponse(
            out_path,
            filename=fname,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"},
        )
    except Exception:
        if os.path.exists(out_path):
            os.remove(out_path)
        raise
