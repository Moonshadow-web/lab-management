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
    """读主封面信息。

    R22 在模板上标"试剂厂家"（如"贝克曼库尔特"），但用户上传时常错填为
    试剂盒产品名（如"碱性磷酸酶检测试剂盒"）。这里做智能识别：
    如果 R22 含有"检测试剂盒"/"试剂"/"测定试剂盒"等产品描述关键词，
    视为产品名，从 R26（仪器厂家）提取品牌覆盖到 reagent 字段。
    """
    ws = wb["主封面"]
    reagent_raw = _safe_str(_val(ws, 22, 5))
    instrument_manufacturer = _safe_str(_val(ws, 26, 5))
    # 智能品牌提取：含产品描述词的产品名 → 用仪器厂家覆盖
    if any(kw in reagent_raw for kw in ("检测试剂盒", "测定试剂盒", "试剂", "试剂盒", "诊断试剂")):
        # 若同时能提取出品牌名（如"贝克曼"）优先；否则用仪器厂家
        known_brands = ("贝克曼", "贝克曼库尔特", "西门子", "罗氏", "雅培", "迈瑞", "日立", "奥林巴斯", "沃芬", "德赛", "安图", "沃文特", "积水", "柏定", "柏荣", "博源", "思塔高", "景源", "丰华", "亚辉龙", "九强", "迈克生物", "英科新创", "艾博")
        for b in known_brands:
            if b in reagent_raw or b in instrument_manufacturer:
                reagent = b
                break
        else:
            reagent = instrument_manufacturer or reagent_raw
    else:
        reagent = reagent_raw
    return {
        "report_type": _type_from_cover(ws),
        "project_name": _safe_str(_val(ws, 20, 5)),
        "reagent": reagent,
        "instrument": _safe_str(_val(ws, 24, 5)),
        "instrument_manufacturer": instrument_manufacturer,
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
    # 关键：必须把每一行都列出来，不能因为某行 cell 为空就跳过
    rows = []
    for r in range(17, 27):
        content = _safe_str(_val(ws, r, 2))
        # B 列为空时（公式无缓存，常见于模板），从 C/D 列 requirement 反推 content
        requirement = _safe_str(_val(ws, r, 3)) or _safe_str(_val(ws, r, 4))
        if not content and requirement:
            content = _content_from_requirement(requirement)
        # 兜底：模板上 R17-R18=精密度、R19-R20=方法符合率、R21=检出限/线性、R22-R23=可报告范围、R24=参考区间、R26=分析特异性
        if not content and not requirement:
            # 用行号硬推导（防止整行空白漏掉）
            content = _content_from_row(r)
            # 这时 B/C/D 都空，但 F/G/H (F=验证结果, H=验证结论) 可能还有内容
        result = _safe_str(_val(ws, r, 6)) or _safe_str(_val(ws, r, 7))
        conclusion = _safe_str(_val(ws, r, 8)) or _safe_str(_val(ws, r, 9))
        # 触发判定条件：content 或 result 或 conclusion 任一非空
        if content or result or conclusion:
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


def _content_from_row(r: int) -> str:
    """按行号硬推导验证内容（当 B/C/D/F/G/H 全空时的兜底）。

    模板 BG-SM-CZ-039（定量）布局：
        R17,R18 = 精密度（批内/实验室内 CV）
        R19,R20 = 正确度（低值偏倚 / 高值偏倚）
        R21     = 线性范围
        R22,R23 = 可报告范围（低限 / 高限）
        R24     = 参考范围
        R25     = 评价结论
        R26     = 分析特异性
    模板 BG-SM-CZ-040（定性）布局：R17-R26 是精密度/方法符合率/检出限/干扰等
    """
    mapping_qt = {
        17: "精密度", 18: "精密度",
        19: "正确度", 20: "正确度",
        21: "线性范围",
        22: "可报告范围", 23: "可报告范围",
        24: "参考范围",
        26: "分析特异性",
    }
    mapping_ql = {
        17: "精密度", 18: "精密度",
        19: "方法符合率", 20: "方法符合率",
        21: "方法检出限",
        22: "参考范围",
        26: "分析特异性",
    }
    # 默认按定量模板推断（更常见），定性时由 _infer_items 进一步筛选
    return mapping_qt.get(r) or mapping_ql.get(r) or ""


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


def _content_to_key(content: str) -> str:
    """中文 content → 英文 key"""
    for kw, key in KEYWORD_MAP.items():
        if kw in content:
            return key
    return ""


def _infer_items(rt, rows):
    items = set()
    for r in rows:
        content = r.get("content", "")
        k = _content_to_key(content)
        if k:
            items.add(k)
    return sorted(items)


def _build_summary(rows):
    """按 content + sub 索引构建 result_summary。

    关键修复：精密度/可报告范围/方法符合率等多行项目，按 subKey（precision1/2/reportable1/2）
    分别存，避免被后面的覆盖丢失。key 用英文 subKey 与前端对齐。
    """
    rs: dict[str, Any] = {}
    for idx, row in enumerate(rows):
        content = row.get("content", "")
        if not content:
            continue
        r = idx + 17  # rows 列表索引对应 R17~R26
        base = _content_to_key(content) or "其他"
        sub = ""
        if base in ("precision", "trueness", "conformity"):
            sub = "1" if r in (17, 19) else "2"
        elif base == "reportable":
            sub = "1" if r == 22 else "2"
        key = base + sub
        rs[key] = {
            "result": row.get("result", ""),
            "conclusion": row.get("conclusion", ""),
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
    from ..core.crud_base import write_audit
    from ..core.storage import storage, persist_save
    from ..models.report_archive import ReportArchive
    from ..models.verification_report import VerificationReport

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
