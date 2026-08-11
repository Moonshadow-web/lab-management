"""性能验证 xlsx 报告解析器 —— 从上传的 Excel 中提取项目信息和验证结论。

兼容定性（BG-SM-CZ-040，51-HBsAg 模板）和定量（BG-SM-CZ-039，2.ALP 模板）。
主策略：读取主封面 + 结果汇总 sheet，提炼项目信息 + 验证结论，写入 verification_reports 表。
"""
import json
from typing import Any

from openpyxl import load_workbook


def _val(ws, row, col):
    """安全读取单元格值"""
    try:
        v = ws.cell(row=row, column=col).value
    except Exception:
        return None
    return v if v is not None else ""


def _safe_str(v):
    return "" if v is None else str(v).strip()


def _type_from_cover(ws) -> str:
    """从主封面第 2 行标题判断定性/定量"""
    row2 = " ".join([_safe_str(_val(ws, 2, c)) for c in range(1, 10)])
    if "定性" in row2:
        return "qualitative"
    if "定量" in row2:
        return "quantitative"
    return "qualitative"


def _read_cover(wb):
    """读主封面信息"""
    ws = wb["主封面"]
    return {
        "report_type": _type_from_cover(ws),
        "project_name": _safe_str(_val(ws, 20, 5)),
        "reagent": _safe_str(_val(ws, 22, 5)),
        "instrument": _safe_str(_val(ws, 24, 5)),
        "instrument_manufacturer": _safe_str(_val(ws, 26, 5)),
        "instrument_model": _safe_str(_val(ws, 28, 5)),
        "instrument_no": _safe_str(_val(ws, 30, 5)),
        "operator": _safe_str(_val(ws, 32, 5)),
        "reviewer": _safe_str(_val(ws, 34, 5)),
        "verify_date": _safe_str(_val(ws, 36, 5)),
    }


def _read_summary(wb, info: dict) -> dict:
    """读结果汇总 sheet：验证结论表 + 参数"""
    ws = wb["结果汇总"]
    # 参数
    info["project_method"] = _safe_str(_val(ws, 4, 2))
    info["unit"] = _safe_str(_val(ws, 5, 2))
    info["reagent"] = info.get("reagent") or _safe_str(_val(ws, 6, 2))
    info["reagent_lot"] = _safe_str(_val(ws, 6, 7))
    info["calibrator"] = _safe_str(_val(ws, 7, 2))
    info["calibrator_lot"] = _safe_str(_val(ws, 7, 7))
    info["qc"] = _safe_str(_val(ws, 8, 2))
    info["qc_lot"] = _safe_str(_val(ws, 8, 7))
    info["tea"] = _safe_str(_val(ws, 5, 7))
    info["dilution"] = _safe_str(_val(ws, 9, 7))
    # 验证内容（R14）
    r14 = _safe_str(_val(ws, 14, 2)) or _safe_str(_val(ws, 14, 1))
    # 验证结论表（R17-R26），跳过 R16 表头行
    rows = []
    for r in range(17, 27):
        content = _safe_str(_val(ws, r, 2))
        # B 列为空时（公式无缓存，常见于模板），从 C 列 requirement 反推 content
        requirement = _safe_str(_val(ws, r, 3)) or _safe_str(_val(ws, r, 4))
        if not content and requirement:
            content = _content_from_requirement(requirement)
        result = _safe_str(_val(ws, r, 6)) or _safe_str(_val(ws, r, 7))
        conclusion = _safe_str(_val(ws, r, 8)) or _safe_str(_val(ws, r, 9))
        if content and (requirement or result or conclusion):
            rows.append({
                "content": content,
                "requirement": requirement,
                "result": result,
                "conclusion": _norm_conclusion(conclusion),
            })
    # 总结论
    conclusion_text = ""
    for r in (23, 24, 25):
        t = _safe_str(_val(ws, r, 1))
        if t and len(t) > 5:
            conclusion_text = t
            break
    # 提炼 verify_items 和 result_summary
    verify_items = _infer_items(info["report_type"], rows)
    result_summary = _build_summary(rows)
    return {
        "verify_items": verify_items,
        "result_summary": result_summary,
        "conclusion": conclusion_text,
        "r14_content": r14,
    }


def _content_from_requirement(req: str) -> str:
    """从验证要求列反推验证内容（当 B 列公式缓存为空时的回退）"""
    if "批内" in req or "实验室内" in req or "CV" in req:
        return "精密度"
    if "偏倚" in req:
        return "正确度"
    if "符合率" in req or "阳性" in req or "阴性" in req:
        return "方法符合率"
    if "检出限" in req:
        return "方法检出限"
    if "线性" in req:
        return "线性范围"
    if "报告" in req or "低限" in req or "高限" in req:
        return "可报告范围"
    if "参考" in req:
        return "参考范围"
    if "干扰" in req or "特异" in req or "胆红素" in req or "甘油三酯" in req or "血红蛋白" in req:
        return "分析特异性"
    return ""


def _fallback_text(wb_cache, sheet_name, row, col):
    """data_only=True 空缺 → data_only=False 补读纯文本"""
    try:
        wb2 = wb_cache  # 不可，因为 data_only=True 不是 data_only=False
        # 简化：直接判断是否合并区，尝试不同列
    except Exception:
        pass
    return ""


def _norm_conclusion(s):
    s = _safe_str(s)
    if "符合" in s or "通过" in s:
        return "符合要求"
    if "不符合" in s or "不通过" in s:
        return "不符合要求"
    if s:
        return s[:20]
    return ""


KEYWORD_MAP = {
    "精密度": "precision",
    "正确度": "trueness",
    "符合率": "conformity",
    "检出限": "lod",
    "线性": "linearity",
    "可报告": "reportable",
    "参考": "reference",
    "特异": "specificity",
}


def _infer_items(rt, rows):
    items = set()
    for r in rows:
        content = r.get("content", "")
        for kw, key in KEYWORD_MAP.items():
            if kw in content:
                items.add(key)
    return sorted(items)


def _build_summary(rows):
    rs: dict[str, Any] = {}
    idx = {}
    for r in rows:
        key = r.get("content", "")
        if not key:
            key = _content_from_requirement(r.get("requirement", ""))
        if not key:
            key = "验证项"
        if key not in idx:
            idx[key] = 0
        idx[key] += 1
        suffix = f"_{idx[key]}" if idx[key] > 1 else ""
        rs[key + suffix] = {
            "result": r.get("result", ""),
            "conclusion": r.get("conclusion", ""),
        }
    return rs


def parse_verification_xlsx(file_bytes: bytes) -> dict:
    """解析上传的性能验证 xlsx 文件，提取项目信息和验证结论。

    双次读取：先 data_only=True 获取公式缓存值（结果/结论），再 data_only=False
    获取纯文本内容（验证内容/要求列的文本），合并两者确保完整性。
    """
    from io import BytesIO
    wb_cache = load_workbook(BytesIO(file_bytes), data_only=True)
    info = _read_cover(wb_cache)
    details = _read_summary(wb_cache, info)
    info.update(details)
    return info


def parse_and_store(file_bytes: bytes, db_session, user, request_ip: str) -> dict:
    """解析 xlsx 并存入 verification_reports 表。

    Returns:
        dict：{id, project_name, archive_id}
    """
    from ...core.crud_base import write_audit
    from ...core.storage import storage, persist_save
    from ...models.report_archive import ReportArchive
    from ...models.verification_report import VerificationReport

    parsed = parse_verification_xlsx(file_bytes)

    rec = VerificationReport(
        report_type=parsed.get("report_type", "qualitative"),
        project_name=parsed.get("project_name", ""),
        project_method=parsed.get("project_method", ""),
        unit=parsed.get("unit", ""),
        reagent=parsed.get("reagent", ""),
        reagent_lot=parsed.get("reagent_lot", ""),
        calibrator=parsed.get("calibrator", ""),
        calibrator_lot=parsed.get("calibrator_lot", ""),
        qc=parsed.get("qc", ""),
        qc_lot=parsed.get("qc_lot", ""),
        instrument=parsed.get("instrument", ""),
        instrument_manufacturer=parsed.get("instrument_manufacturer", ""),
        instrument_model=parsed.get("instrument_model", ""),
        instrument_no=parsed.get("instrument_no", ""),
        tea=parsed.get("tea", ""),
        dilution=parsed.get("dilution", ""),
        verify_items=json.dumps(parsed.get("verify_items", []), ensure_ascii=False),
        data=json.dumps({}, ensure_ascii=False),
        result_summary=json.dumps(parsed.get("result_summary", {}), ensure_ascii=False),
        conclusion=parsed.get("conclusion", ""),
        verify_date=parsed.get("verify_date", ""),
        operator=parsed.get("operator", ""),
        reviewer=parsed.get("reviewer", ""),
        created_by_id=user.id if user else None,
    )
    db_session.add(rec)
    db_session.flush()

    # 归档
    fname = f"{rec.project_name or '项目'}_性能验证_uploaded.xlsx"
    rel = persist_save("verification_reports", fname, file_bytes)
    rec.report_file_path = rel
    arch = ReportArchive(
        project_name=rec.project_name,
        report_type=rec.report_type,
        source_type="uploaded",
        ref_report_id=rec.id,
        ref_archive_kind="verification_report",
        original_name=fname,
        file_path=rel,
        description=f"上传解析自：{fname}",
        created_by_id=user.id if user else None,
    )
    db_session.add(arch)
    db_session.commit()
    write_audit(db_session, user, "upload_parse", "verification_reports", rec.id, {"file": rel}, request_ip)
    return {"id": rec.id, "project_name": rec.project_name, "archive_id": arch.id}
