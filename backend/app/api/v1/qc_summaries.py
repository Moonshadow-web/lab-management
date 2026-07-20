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
from ...services.qc_service import aggregate, lookup_quality_goal, draft_report, find_test_item_by_name

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
        .order_by(Instrument.dept_no)
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
    # 标准格式（允许 0/1 开头、带时间）
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y-%m",
        "%Y/%m",
        "%Y.%m",
    ):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    # 爱康 LIS 常见格式：2026-6-1 10:10 / 2026/6/1 10:10 / 2026.6.1
    m = re.search(r"(\d{4})[^\d]*(\d{1,2})[^\d]*(\d{1,2})(?:[^\d]*(\d{1,2})[^\d]*(\d{1,2})(?:[^\d]*(\d{1,2}))?)?", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h = int(m.group(4) or 0)
        mi = int(m.group(5) or 0)
        sec = int(m.group(6) or 0)
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime.datetime(y, mo, d, h, mi, sec)
            except ValueError:
                pass
    # 仅年月
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


def _count_summary_lines(text: str | None) -> int:
    """按草稿文本中「；」分隔的条目数，估算当前文字覆盖了多少个（项目×水平）。"""
    if not text:
        return 0
    return len([x for x in text.split("；") if x.strip()])


def _ensure_report_draft(db: Session, instrument_id, instrument: str, year: int, month: int):
    """若报告不存在、五段文字全为空，或当前月结明细数多于文字覆盖数，则按当前数据草拟并落库。

    修复：
    1. 之前只判「报告不存在」，导致历史遗留的空文本报告永远不会被补字。
    2. 之前只回填空字段，导致先上传部分数据、后补充数据时，文字报告不会随明细自动更新。
       现增加「明细条目数 > 文字条目数」判定，检测到遗漏时整段重生成（覆盖原有自动文字，
       保护用户编辑的尽力而为：若用户未删行，仅新增项目时触发更新；若用户手动精简过文字，
       只要条目数未少于明细数，就不会被覆盖）。
    """
    q = db.query(QCMonthlySummary).filter_by(year=year, month=month)
    if instrument_id:
        q = q.filter_by(instrument_id=instrument_id)
    else:
        q = q.filter_by(instrument=(instrument or ""))
    summaries = q.all()

    rep = _find_report(db, instrument_id, instrument, year, month)
    if not summaries:
        if not rep:
            rep = QCMonthlyReport(instrument_id=instrument_id, instrument=instrument or "", year=year, month=month)
            db.add(rep)
            db.commit()
        return

    expected = len(summaries)
    needs_draft = False
    if not rep:
        needs_draft = True
    else:
        has_any = any((getattr(rep, f, "") or "").strip() for f in
                      ("operation_status", "drift_trend", "cv_setting_ok", "cv_calc_ok", "freq_ok"))
        stored_lines = max(
            _count_summary_lines(rep.cv_setting_ok),
            _count_summary_lines(rep.cv_calc_ok),
        )
        if not has_any:
            needs_draft = True
        elif expected > stored_lines:
            # 月结明细比文字覆盖的多 → 自动文字已过时，需要重生成
            needs_draft = True

    if not needs_draft:
        return

    sids = [s.id for s in summaries]
    dvs = db.query(QCDailyValue).filter(QCDailyValue.summary_id.in_(sids)).all()
    daily = {}
    for dv in dvs:
        daily.setdefault(dv.summary_id, []).append(dv)
    drafted = draft_report(instrument or summaries[0].instrument, year, month, summaries, daily)
    if not rep:
        rep = QCMonthlyReport(
            instrument_id=instrument_id,
            instrument=instrument or summaries[0].instrument,
            instrument_no=summaries[0].instrument_no,
            year=year, month=month, **drafted,
        )
        db.add(rep)
    else:
        # 重生成时覆盖全部五段文字（仅在有需要时进入此分支）
        for k, v in drafted.items():
            setattr(rep, k, v)
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
            ti_name = (get("test_item") or "").strip()
            matched = find_test_item_by_name(db, ti_name) if ti_name else None
            file_unit = (get("unit") or "").strip()
            unit = file_unit or (matched.unit if matched else "")
            meta[key] = {
                "unit": unit,
                "target_mean": _to_float(get("target_mean")) or 0.0,
                "target_sd": _to_float(get("target_sd")) or 0.0,
                "instrument_no": inst_no,
                "test_item_aliases": matched.aliases if matched else "",
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
        quality_goal = lookup_quality_goal(test_item, m.get("test_item_aliases", ""), db)
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


@router.get("/daily/project")
def list_project_daily(
    year: int,
    month: int,
    instrument_id: int,
    test_item: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按（仪器,年,月,项目）取所有水平(level)的每日测值，用于 LJ 质控图。

    返回每个测值的日期、测值、水平、靶值均值、靶值SD、失控标记及触发规则。
    """
    summaries = (
        db.query(QCMonthlySummary)
        .filter_by(year=year, month=month, instrument_id=instrument_id, test_item=test_item)
        .order_by(QCMonthlySummary.level)
        .all()
    )
    if not summaries:
        return []
    sids = [s.id for s in summaries]
    summary_map = {s.id: s for s in summaries}
    rows = (
        db.query(QCDailyValue)
        .filter(QCDailyValue.summary_id.in_(sids))
        .order_by(QCDailyValue.qc_date, QCDailyValue.summary_id)
        .all()
    )
    result = []
    for dv in rows:
        s = summary_map[dv.summary_id]
        result.append({
            "qc_date": dv.qc_date,
            "value": dv.value,
            "level": s.level,
            "target_mean": s.target_mean,
            "target_sd": s.target_sd,
            "is_out_of_control": dv.is_out_of_control,
            "rule_violated": dv.rule_violated,
        })
    return result


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


# 注：质控图 PDF 上传/预览/下载/删除 已在 2026-07-19 移除（d3e93eb）—— 前端按钮 + 后端三路由
# （POST/GET/DELETE /{summary_id}/pdf）一并删除。月结改用 build_docx 内嵌 14 列表格 + 5 段文字。

@router.get("/report", response_model=QCMonthlyReportRead)
def get_qc_report(
    instrument_id: int | None = None,
    instrument: str = "",
    year: int = 0,
    month: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取某(仪器,年,月)的月结文字报告；不存在/为空/明细增加时自动按当前数据重生成。"""
    _ensure_report_draft(db, instrument_id, instrument, year, month)
    rep = _find_report(db, instrument_id, instrument, year, month)
    if not rep:
        rep = QCMonthlyReport(instrument_id=instrument_id, instrument=instrument or "", year=year, month=month)
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


@router.post("/report/regenerate")
def regenerate_qc_report(
    instrument_id: int | None = None,
    instrument: str = "",
    year: int = 0,
    month: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """强制按当前月结明细重新生成 CZ-012 五段文字（覆盖原有文字，请谨慎使用）。"""
    q = db.query(QCMonthlySummary).filter_by(year=year, month=month)
    if instrument_id:
        q = q.filter_by(instrument_id=instrument_id)
    else:
        q = q.filter_by(instrument=(instrument or ""))
    summaries = q.all()
    if not summaries:
        raise HTTPException(status_code=404, detail="未找到月结明细，无法生成文字报告")
    sids = [s.id for s in summaries]
    dvs = db.query(QCDailyValue).filter(QCDailyValue.summary_id.in_(sids)).all()
    daily = {}
    for dv in dvs:
        daily.setdefault(dv.summary_id, []).append(dv)
    drafted = draft_report(instrument or summaries[0].instrument, year, month, summaries, daily)
    rep = _find_report(db, instrument_id, instrument, year, month)
    if not rep:
        rep = QCMonthlyReport()
        db.add(rep)
    rep.instrument_id = instrument_id
    rep.instrument = instrument or summaries[0].instrument
    rep.instrument_no = summaries[0].instrument_no
    rep.year = year
    rep.month = month
    for k, v in drafted.items():
        setattr(rep, k, v)
    db.commit()
    db.refresh(rep)
    return rep


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
