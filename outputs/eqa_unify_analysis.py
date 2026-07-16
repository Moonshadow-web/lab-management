"""分析：以项目查询(test_items)标准名为基准，对照所有质评计划(eqa_plans)的 item 字段分析物，
找出「写法不一致、可统一改写」的 token。只读、不写库。
复用 backend/app/api/v1/eqa_associations.py 的匹配算法（纯函数复刻，去掉 FastAPI/DB 依赖）。
"""
import sqlite3, re, json
from collections import defaultdict

DB = "data/app.db"

# ---- 复刻 eqa_associations.py 的常量与算法 ----
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
        index.append({
            "id": tid, "name": name, "category": category or "", "specimen": specimen or "",
            "unit": unit or "", "instrument": instrument or "", "brand": brand or "",
            "keys": keys, "norm_name": _norm(name),
            "base": _norm(name.split("-")[0].strip()) if "-" in name else _norm(name),
        })
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

# ---- 主流程 ----
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# test_items 索引
ti_rows = cur.execute("SELECT id,name,aliases,category,specimen,unit,instrument,brand FROM test_items").fetchall()
index = _build_test_item_index([tuple(r) for r in ti_rows])
normname_to_item = {it["norm_name"]: it for it in index}

plans = cur.execute("SELECT id,year,org,program,item,round_no,result_data FROM eqa_plans ORDER BY id").fetchall()

records = []          # 每行一个 (plan_id, program, token, status, canonical, plan_has_result)
need_rewrite = []     # 可改写
unmatched = []        # 无法自动匹配
already_ok = []       # 已一致

for p in plans:
    pid, year, org, program, item, round_no, result_data = (p["id"], p["year"], p["org"], p["program"], p["item"], p["round_no"], p["result_data"])
    has_result = bool(result_data and result_data.strip())
    if not item:
        continue
    for token in _split_eqa_items(item):
        it, score = _match_eqa_token(token, index)
        if not it:
            unmatched.append({"plan_id": pid, "program": program, "token": token, "org": org, "year": year, "round_no": round_no})
            records.append((pid, program, token, "UNMATCHED", "", has_result))
            continue
        canonical = it["name"]
        if _norm(token) == _norm(canonical):
            already_ok.append({"plan_id": pid, "program": program, "token": token, "canonical": canonical})
            records.append((pid, program, token, "OK", canonical, has_result))
        else:
            need_rewrite.append({"plan_id": pid, "program": program, "token": token, "canonical": canonical, "org": org, "year": year, "round_no": round_no, "has_result": has_result})
            records.append((pid, program, token, "REWRITE", canonical, has_result))

# 统计
print("=" * 70)
print("质评 item 字段 vs 项目查询(test_items) 一致性分析（只读）")
print("=" * 70)
print(f"可统一改写(写法不同,能匹配): {len(need_rewrite)}")
print(f"已一致(写法相同):            {len(already_ok)}")
print(f"无法自动匹配(需人工/别名):   {len(unmatched)}")
print(f"合计分析 token:              {len(records)}")

# 风险：可改写里有多少条 plan 已录入结果（改写 item 会破坏 result_data 的 key）
rw_with_result = [r for r in need_rewrite if r["has_result"]]
print(f"  ⚠ 其中所在 plan 已录入结果(改写有风险): {len(rw_with_result)}")

print("\n--- 可统一改写清单 (前60) ---")
for r in need_rewrite[:60]:
    flag = " [已录入!]" if r["has_result"] else ""
    print(f"  plan#{r['plan_id']} {r['org']} {r['program']} | 「{r['token']}」→「{r['canonical']}」{flag}")

print("\n--- 无法自动匹配 token (需人工处理) ---")
for r in unmatched:
    print(f"  plan#{r['plan_id']} {r['org']} {r['program']} | 「{r['token']}」")

# 导出 JSON 供后续改写脚本使用
out = {
    "need_rewrite": need_rewrite,
    "unmatched": unmatched,
    "already_ok_count": len(already_ok),
}
with open("outputs/eqa_unify_preview.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已写出 outputs/eqa_unify_preview.json")
conn.close()
