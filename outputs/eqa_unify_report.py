"""生成「质评 item 字段 → 项目库标准名」一致性对照表（只读，不写库）。
输出：
  outputs/eqa_unify_report.csv  (Excel 可打开，含风险标记列)
  outputs/eqa_unify_report.md   (按风险分组的可读报告)
复用 backend/app/api/v1/eqa_associations.py 的匹配算法（纯函数复刻）。
"""
import sqlite3, re, json, csv

DB = "data/app.db"

_CURATED_EQA_ALIASES = {
    "tpab": "梅毒螺旋体抗体", "tppa": "梅毒螺旋体抗体", "trust": "梅毒甲苯胺红不加热血清试验",
    "inr": "凝血酶原时间国际标准化比值", "aptt": "活化部分凝血活酶时间", "pt": "凝血酶原时间",
    "fib": "纤维蛋白原", "tt": "凝血酶时间", "d-二聚体": "血浆d-二聚体", "fdp": "纤维蛋白（原）降解产物",
    "atiii": "抗凝血酶iii", "ck-mb": "肌酸激酶-mb", "ckmb": "肌酸激酶-mb", "肌酸激酶-mb": "肌酸激酶-mb",
    "ctni": "肌钙蛋白i", "肌钙蛋白i": "肌钙蛋白i", "ctnt": "肌钙蛋白t",
    "nt-probnp": "n末端b型钠尿肽前体", "probnp": "n末端b型钠尿肽前体", "bnp": "b型钠尿肽",
    "pct": "降钙素原", "il-6": "白介素-6", "cys-c": "胱抑素c", "cysc": "胱抑素c", "saa": "血清淀粉样蛋白a",
    "hba1c": "糖化血红蛋白", "ga": "糖化白蛋白", "清蛋白": "白蛋白", "血清蛋白电泳-清蛋白": "血清蛋白电泳-白蛋白",
}

def _norm(s):
    s = (s or "").strip().replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "")
    return s.lower()

def _split_eqa_items(raw):
    raw = re.sub(r"^(具体项目|项目|检测项目)[：:]\s*", "", raw or "")
    return [p.strip() for p in re.split(r"[、,，/]", raw) if p.strip()]

def _build_test_item_index(rows):
    index = []
    for (tid, name, aliases, category, specimen, unit, instrument, brand) in rows:
        keys = {_norm(name)}
        for part in re.split(r"[、,，/]", name):
            p = part.strip()
            if p:
                keys.add(_norm(p))
        for seg in (aliases or "").replace("，", ",").split(","):
            seg = seg.strip()
            if seg:
                keys.add(_norm(seg))
                for w in seg.split():
                    w = w.strip()
                    if len(_norm(w)) >= 2:
                        keys.add(_norm(w))
        index.append({"id": tid, "name": name, "category": category or "",
                      "keys": keys, "norm_name": _norm(name)})
    return index

def _match_eqa_token(token, index):
    nn = _norm(token)
    nn2 = _norm(re.sub(r"[（(](尿液|脑脊液|胸腹水|胸水|腹水|血浆|血清)[)）]", "", token or "").strip())
    forms = [nn] + ([nn2] if nn2 != nn else [])
    for form in forms:
        curated = _CURATED_EQA_ALIASES.get(form)
        if curated:
            form = _norm(curated)
        for it in index:
            if form in it["keys"]:
                return it, "exact"
    for form in forms:
        if len(form) < 2:
            continue
        for it in index:
            for k in it["keys"]:
                if len(k) >= 2 and (k in form or form in k):
                    return it, "substring"
    return None, ""

# ---- 风险标记 ----
def risk_flags(token, canonical, has_result):
    flags = []
    if has_result:
        flags.append("⚠已录入成绩-改写会丢失")
    if "/" in canonical:
        flags.append("canonical含/-会二次拆分")
    tok_ascii = bool(re.search(r'[a-zA-Z]', token))
    can_all_cn = not bool(re.search(r'[a-zA-Z]', canonical))
    if tok_ascii and can_all_cn:
        flags.append("缩写→中文-请确认映射正确")
    return flags

# ---- 主流程 ----
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
ti_rows = cur.execute("SELECT id,name,aliases,category,specimen,unit,instrument,brand FROM test_items").fetchall()
index = _build_test_item_index([tuple(r) for r in ti_rows])
plans = cur.execute("SELECT id,year,org,program,item,round_no,result_data FROM eqa_plans ORDER BY id").fetchall()

rows_out = []   # CSV/MD 行
safe = []       # 低风险可改
review = []     # 需复核

for p in plans:
    pid, year, org, program, item, round_no, result_data = (p["id"], p["year"], p["org"], p["program"], p["item"], p["round_no"], p["result_data"])
    has_result = bool(result_data and result_data.strip())
    if not item:
        continue
    if "正确度" in (program or ""):
        continue
    for token in _split_eqa_items(item):
        it, score = _match_eqa_token(token, index)
        if not it:
            rows_out.append({"plan_id": pid, "org": org, "program": program, "token": token,
                             "canonical": "(无法匹配)", "score": "-", "has_result": has_result,
                             "risk": "未匹配-需人工或补别名"})
            review.append(rows_out[-1])
            continue
        canonical = it["name"]
        if _norm(token) == _norm(canonical):
            continue  # 已一致，不列入改写清单
        flags = risk_flags(token, canonical, has_result)
        rec = {"plan_id": pid, "org": org, "program": program, "token": token,
               "canonical": canonical, "score": score, "has_result": has_result,
               "risk": "；".join(flags) if flags else "安全可改"}
        rows_out.append(rec)
        (review if flags else safe).append(rec)

# 排序：需复核优先
review.sort(key=lambda r: (not r["risk"].startswith("⚠"), r["plan_id"]))
safe.sort(key=lambda r: r["plan_id"])

# ---- 写 CSV ----
csv_path = "outputs/eqa_unify_report.csv"
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["plan_id", "机构", "质评项目组", "质评原写法", "项目库标准名", "匹配方式", "是否已录入成绩", "风险标记"])
    for r in review + safe:
        w.writerow([r["plan_id"], r["org"], r["program"], r["token"], r["canonical"], r["score"],
                    "是" if r["has_result"] else "否", r["risk"]])

# ---- 写 MD ----
md_path = "outputs/eqa_unify_report.md"
lines = []
lines.append("# 质评 item 字段 → 项目库标准名 一致性对照表\n")
lines.append(f"- 统计：可统一改写 **{len(rows_out)}** 处（安全可改 {len(safe)} / 需复核 {len(review)}）；已一致项未列入。\n")
lines.append("> 说明：本表只读，未改动数据库。请以「项目查询(test_items)标准名」为基准，逐条确认是否将质评原写法统一为项目库标准名。\n")
lines.append("\n## 一、需复核（{0} 处，优先看）\n".format(len(review)))
lines.append("| plan_id | 机构 | 质评项目组 | 质评原写法 | 项目库标准名 | 匹配 | 已录入 | 风险 |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in review:
    lines.append(f"| {r['plan_id']} | {r['org']} | {r['program']} | {r['token']} | {r['canonical']} | {r['score']} | {'是' if r['has_result'] else '否'} | {r['risk']} |")
lines.append("\n## 二、安全可改（{0} 处，批量确认即可）\n".format(len(safe)))
lines.append("| plan_id | 机构 | 质评项目组 | 质评原写法 | 项目库标准名 | 匹配 | 已录入 |")
lines.append("|---|---|---|---|---|---|---|")
for r in safe:
    lines.append(f"| {r['plan_id']} | {r['org']} | {r['program']} | {r['token']} | {r['canonical']} | {r['score']} | {'是' if r['has_result'] else '否'} |")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"可统一改写总数: {len(rows_out)} (安全 {len(safe)} / 需复核 {len(review)})")
print(f"已写出: {csv_path}  ({len(review)+len(safe)} 行)")
print(f"已写出: {md_path}")
conn.close()
