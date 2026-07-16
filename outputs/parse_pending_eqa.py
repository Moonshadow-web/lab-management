"""批量解析库内「成绩待填」的质评报告 PDF 并回填成绩/合格/得分。

判定规则（与 backend/app/api/v1/eqa.py::parse_eqa_report 保持一致）：
  - 卫健委：评价词「通过/不通过」+ 末行「成绩NN％」
  - 北京市：汇总表「满意/不满意」+ 「及格数 总数 得分%」
离线、纯文本（PyMuPDF），无需外部多模态 API。
qualified 仅在明确时给出；含不合格项标 medium 并置 False，避免误判整体合格。
低置信（无关键词）不写入，保留待人工处理。
"""
import sqlite3, os, re, fitz, json, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "app.db")
REP = os.path.join(ROOT, "backend", "data", "eqa_reports")


_NONAME = re.compile(
    r"室间质量评价|实验室编码|实验室名称|测定日期|统计日期|报表打印日期|打印日期|"
    r"统计结果|国家卫生|卫生健康委|第\d+次|页|"
    r"你室结果|所有实验室稳健均值|允许范围|下限靶值上限评价结果|样本编号|偏倚|"
    r"所属组|方法|仪器|试剂|本组实验室数|校准物|建议|项目：|"
    r"成绩汇总|成绩解释|成绩说明|科室|"
    r"成功|当前解释|及格数|总数|得分%|解释|评价结果|成绩|汇总"
)


def _is_name_line(l: str) -> bool:
    l = l.strip()
    if not l:
        return False
    if "%" in l:
        return False
    if re.fullmatch(r"[\d.]+", l):
        return False
    if re.fullmatch(r"[\d\s\-]+", l):
        return False
    if re.fullmatch(r"[A-Za-z/μ·]+", l):
        return False
    if re.search(r"^\d{4}[-/年]", l):
        return False
    if _NONAME.search(l):
        return False
    return True


def _extract_nhc_blocks(lines):
    anchors = []
    for i, l in enumerate(lines):
        if l.startswith("成绩") and not re.search(r"汇总|解释|说明|备注|标题", l):
            is_na = bool(re.search(r"不适用|不评价", l))
            m = re.search(r"(\d{1,3})\s*[％%]", l)
            if not m and i + 1 < len(lines):
                m = re.search(r"(\d{1,3})\s*[％%]", lines[i + 1])
            score = m.group(1) if m else None
            anchors.append((i, score, is_na))
    if not anchors:
        return []
    blocks = []
    for k, (ai, score, is_na) in enumerate(anchors):
        start = anchors[k - 1][0] + 1 if k > 0 else 0
        name = None
        for j in range(start, ai):
            if _is_name_line(lines[j]):
                name = lines[j].strip()
                break
        blocks.append((name, score, is_na))
    return blocks


def _extract_bj_lines(lines):
    anchors = []
    for i, l in enumerate(lines):
        if l == "满意" or l == "不满意" or re.match(r"^(满意|不满意)$", l):
            anchors.append((i, l == "不满意"))
    if not anchors:
        return []
    blocks = []
    for k, (ai, unsat) in enumerate(anchors):
        start = anchors[k - 1][0] + 1 if k > 0 else 0
        name = None
        for j in range(start, ai):
            if _is_name_line(lines[j]):
                name = lines[j].strip()
                break
        score_pct = None
        for j in range(ai - 1, start - 1, -1):
            bl = lines[j].strip()
            if re.fullmatch(r"\d+", bl):
                score_pct = bl
                break
        blocks.append((name, not unsat, score_pct))
    return blocks


def parse_eqa_report(pdf_path: str, item_text: str = None) -> dict:
    """卫健委/北京市报告逐项解析，点名不适用或非满分(不满意)子项。"""
    try:
        doc = fitz.open(pdf_path)
        txt = "\n".join(pg.get_text() for pg in doc)
    except Exception:
        return {}
    if not txt.strip():
        return {}
    lines = [l.strip() for l in txt.splitlines()]
    evidence = re.sub(r"\s+", " ", txt[:80])

    nhc = [b for b in _extract_nhc_blocks(lines) if b[0]]
    bj = [b for b in _extract_bj_lines(lines) if b[0]]

    if nhc:
        na_items = [n for n, s, na in nhc if na]
        non100 = [(n, s) for n, s, na in nhc if s is not None and s != "100"]
        if na_items and not non100 and len(na_items) < len(nhc):
            note = "（" + "、".join(f"{n}不适用" for n in na_items) + "）"
            return {"result": "成绩100%" + note, "qualified": True, "score": "100",
                    "confidence": "high", "evidence": evidence}
        if non100:
            notes = [f"{n}不适用" for n in na_items] + [f"{n}({s}分)" for n, s in non100]
            note = "（" + "、".join(notes) + "）"
            return {"result": "成绩未达标" + note, "qualified": False, "score": non100[0][1],
                    "confidence": "high", "evidence": evidence}
        if na_items and len(na_items) == len(nhc):
            return {"result": "成绩不适用(不予评价)", "qualified": None, "score": "",
                    "confidence": "high", "evidence": evidence}
        return {"result": "成绩100%", "qualified": True, "score": "100",
                "confidence": "high", "evidence": evidence}

    if bj:
        unsat = [n for n, sat, _ in bj if sat is False]
        non100 = [(n, s) for n, sat, s in bj if s is not None and s != "100"]
        if unsat and not non100:
            note = "（" + "、".join(f"{n}不满意" for n in unsat) + "）"
            return {"result": "不合格" + note, "qualified": False, "score": "",
                    "confidence": "high", "evidence": evidence}
        if non100 and not unsat:
            note = "（" + "、".join(f"{n}({s}分)" for n, s in non100) + "）"
            return {"result": "合格" + note, "qualified": True, "score": "",
                    "confidence": "high", "evidence": evidence}
        if unsat and non100:
            note = "（" + "、".join(f"{n}不满意" for n in unsat) + \
                   "｜非100：" + "、".join(f"{n}({s}分)" for n, s in non100) + "）"
            return {"result": "不合格" + note, "qualified": False, "score": "",
                    "confidence": "high", "evidence": evidence}
        return {"result": "合格", "qualified": True, "score": "",
                "confidence": "high", "evidence": evidence}

    has_fail = bool(re.search(r"不通过|不合格|不及格|不满意|未通过|不达标", txt))
    has_pass = bool(re.search(r"通过|合格|满意|及格", txt))
    score = ""
    m = re.search(r"成绩\s*[:：]?\s*(\d{1,3})\s*[％%]?", txt)
    if m:
        score = m.group(1)
    if not score:
        m2 = re.search(r"得分\s*[:：]?\s*(\d{1,3})", txt)
        if m2:
            score = m2.group(1)
    if has_fail and not has_pass:
        return {"result": "不合格", "qualified": False, "score": score, "confidence": "high", "evidence": evidence}
    if has_fail and has_pass:
        return {"result": "含不合格项(待复核)", "qualified": False, "score": score, "confidence": "medium", "evidence": evidence}
    if has_pass and not has_fail:
        result = f"成绩{score}%" if score else "合格"
        return {"result": result, "qualified": True, "score": score, "confidence": "high", "evidence": evidence}
    return {"result": "", "qualified": None, "score": "", "confidence": "low", "evidence": evidence}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""SELECT id, item, report_file FROM eqa_plans
                   WHERE report_file<>'' AND report_file IS NOT NULL
                     AND (score IS NULL OR score='') AND (result IS NULL OR result='')""")
    rows = cur.fetchall()
    backup_ids = [r[0] for r in rows]
    stats = {"total": len(rows), "high": 0, "medium": 0, "low": 0, "written": 0}
    preview = []
    for pid, item, rf in rows:
        path = os.path.join(REP, os.path.basename(rf))
        parsed = parse_eqa_report(path, item_text=item) if os.path.exists(path) else {}
        res = parsed.get("result", "")
        qual = parsed.get("qualified")
        sc = parsed.get("score", "")
        conf = parsed.get("confidence", "low")
        stats[conf] = stats.get(conf, 0) + 1
        if res or sc or qual is not None:
            cur.execute(
                "UPDATE eqa_plans SET result=?, score=?, qualified=? WHERE id=?",
                (res, sc, 1 if qual else 0, pid),
            )
            stats["written"] += 1
        preview.append({
            "id": pid, "file": rf, "result": res,
            "qualified": "" if qual is None else bool(qual),
            "score": sc, "confidence": conf, "evidence": parsed.get("evidence", ""),
        })
    con.commit()
    con.close()

    with open(os.path.join(ROOT, "outputs", "eqa_pending_backup.json"), "w", encoding="utf-8") as f:
        json.dump({"ids": backup_ids, "note": "原 score/result/qualified 均为空，回退即 UPDATE ... SET result='',score='',qualified=0 WHERE id IN (ids)"}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(ROOT, "outputs", "eqa_parse_preview.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "file", "result", "qualified", "score", "confidence", "evidence"])
        w.writeheader()
        w.writerows(preview)
    print(json.dumps(stats, ensure_ascii=False))
    print("preview -> outputs/eqa_parse_preview.csv ; backup -> outputs/eqa_pending_backup.json")


if __name__ == "__main__":
    main()
