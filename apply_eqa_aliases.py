"""按用户决策，一次性修好室间质评单位对应：
1. 重命名 不饱和铁结合力 -> 不饱和铁结合力/总铁结合力（别名 UIBC,TIBC,总铁结合力），单位 µmol/L，参考范围注 UIBC
2. 离子钙 -> 别名挂到「血气和酸碱分析」行（panel，含 mmol/L）
3. 给库里已有但别名没对上的 38 个项目加逗号分隔别名（EQA 项目名 -> 库项目名）
4. EQA 计划 item 字段：TGAg->TgAb；甲功五项->5 单项；乙肝五项->5 单项
5. 暂不动：京津冀鲁盲样、代谢物、电解质/酶学/脂类正确度
"""
import re
import sqlite3
from pathlib import Path

DB = Path(r"d:\workbuddyprojects\网页版-生免速查工具\data\app.db")

def _norm(s):
    s = (s or "").strip()
    s = s.replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "")
    return s.lower()

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

def show(name):
    r = cur.execute("SELECT name, aliases, unit, reference FROM test_items WHERE name=?", (name,)).fetchone()
    print(f"   [{name}] -> {r}")

# ---------------------------------------------------------------------------
# 1) 重命名 不饱和铁结合力
# ---------------------------------------------------------------------------
print("== 1) 不饱和铁结合力 重命名 ==")
show("不饱和铁结合力")
cur.execute(
    """UPDATE test_items
       SET name='不饱和铁结合力/总铁结合力',
           aliases='UIBC, TIBC, 总铁结合力',
           unit='µmol/L',
           reference='UIBC（总铁结合力 TIBC 并入此行，参考范围以 UIBC 计）'
       WHERE name='不饱和铁结合力'"""
)
show("不饱和铁结合力/总铁结合力")

# ---------------------------------------------------------------------------
# 2) 离子钙 别名挂到血气和酸碱分析行
# ---------------------------------------------------------------------------
print("\n== 2) 离子钙 别名 -> 血气和酸碱分析 ==")
bg_name = "血气和酸碱分析（pH、PO2、PCO2、K、Na、Cl、Ca）"
show(bg_name)
old = cur.execute("SELECT aliases FROM test_items WHERE name=?", (bg_name,)).fetchone()[0] or ""
toks = [a.strip() for a in old.split(",") if a.strip()]
if "离子钙" not in toks:
    toks.append("离子钙")
cur.execute("UPDATE test_items SET aliases=? WHERE name=?", (",".join(toks), bg_name))
show(bg_name)

# ---------------------------------------------------------------------------
# 3) 给库里已有项目加 EQA 项目别名（EQA名 -> 库项目名）
# ---------------------------------------------------------------------------
ALIAS_MAP = {
    "CMV G": "巨细胞病毒IgG抗体",
    "CMV M": "巨细胞病毒IgM抗体",
    "Cys-C": "胱抑素C",
    "HCVAb": "丙型肝炎病毒抗体",
    "HCV（胶体金）": "快速抗丙型肝炎病毒抗体(仅复检）",
    "HEV-IgM": "戊肝抗体IgM抗体",
    "HSV-1 G": "I型单纯疱疹病毒IgG抗体",
    "HSV-1 M": "I型单纯疱疹病毒IgM抗体",
    "HSV-2 G": "II型单纯疱疹病毒IgG抗体",
    "HSV-2 M": "II型单纯疱疹病毒IgM抗体",
    "RV G": "风疹病毒IgG抗体",
    "RV M": "风疹病毒IgM抗体",
    "TOX G": "弓形虫IgG抗体",
    "TOX M": "弓形虫IgM抗体",
    "VD": "维生素D",
    "β2微球蛋白": "β2-微球蛋白",
    "βHCG": "β人绒毛膜促性腺激素",
    "总βHCG": "β人绒毛膜促性腺激素",
    "γ-谷氨酸氨基转移酶": "γ-谷氨酰基转移酶",
    "免疫球蛋白轻链κ": "κ轻链（血清）",
    "免疫球蛋白轻链κ（尿液）": "尿κ轻链",
    "免疫球蛋白轻链λ": "λ轻链（血清）",
    "免疫球蛋白轻链λ（尿液）": "尿λ轻链",
    "总T3": "三碘甲状腺原氨酸",
    "游离T3": "游离三碘甲状腺原氨酸",
    "总T4": "甲状腺素",
    "游离T4": "游离甲状腺素",
    "抗FXa活性": "抗Xa活性",
    "甘油三脂": "甘油三酯",
    "碳酸氢根": "二氧化碳",
    "磷": "无机磷",
    "肌钙蛋白-I": "超敏肌钙蛋白Ⅰ",
    "脂蛋白（a）": "脂蛋白a",
    "血清蛋白电泳（M蛋白）": "血清蛋白电泳-白蛋白/α1球蛋白/α2球蛋白/β1球蛋白//β2球蛋白/γ球蛋白/M蛋白/M蛋白定性",
    "血糖": "葡萄糖",
    "钙": "总钙",
    "铜离子": "铜",
    "总铁结合力": "不饱和铁结合力/总铁结合力",
    "TGAg": "抗甲状腺球蛋白抗体",  # 用户确认 TGAg 实际是 TgAb
}

print("\n== 3) 加 EQA 项目别名 ==")
added = 0
for eqa_item, target in ALIAS_MAP.items():
    row = cur.execute("SELECT name, aliases FROM test_items WHERE name=?", (target,)).fetchone()
    if not row:
        print(f"  !! 目标行不存在: {target}  (EQA项 {eqa_item})")
        continue
    old = row[1] or ""
    toks = [a.strip() for a in old.split(",") if a.strip()]
    if _norm(eqa_item) in {_norm(a) for a in toks}:
        continue
    toks.append(eqa_item)
    cur.execute("UPDATE test_items SET aliases=? WHERE name=?", (",".join(toks), target))
    added += 1
print(f"  共新增/更新别名 {added} 行")

# ---------------------------------------------------------------------------
# 4) EQA 计划 item 字段修正
# ---------------------------------------------------------------------------
print("\n== 4) EQA 计划 item 字段修正 ==")
# TGAg -> TgAb
r = cur.execute("UPDATE eqa_plans SET item=REPLACE(item,'TGAg','TgAb') WHERE item LIKE '%TGAg%'")
print(f"   TGAg->TgAb 影响行数: {r.rowcount}")
# 甲功五项 -> 5 单项（单位单列）
r = cur.execute("UPDATE eqa_plans SET item=REPLACE(item,'甲功五项','游离T3、总T3、游离T4、总T4、TSH') WHERE item LIKE '%甲功五项%'")
print(f"   甲功五项 展开 影响行数: {r.rowcount}")
# 乙肝五项 -> 5 单项（定性，单位无）
r = cur.execute("UPDATE eqa_plans SET item=REPLACE(item,'乙肝五项','HBsAg、HBsAb、HBeAg、HBeAb、HBcAb') WHERE item LIKE '%乙肝五项%'")
print(f"   乙肝五项 展开 影响行数: {r.rowcount}")

conn.commit()
print("\n全部更新已提交。")

# ---------------------------------------------------------------------------
# 5) 复跑未匹配检查（复刻 eqa.py 逻辑）
# ---------------------------------------------------------------------------
def _split_items(raw):
    raw = re.sub(r"^(具体项目|项目|检测项目)[：:]\s*", "", raw or "")
    return [p.strip() for p in re.split(r"[、,，/]", raw) if p.strip()]

def build_index():
    rows = cur.execute("SELECT name, aliases, unit FROM test_items").fetchall()
    index = []
    for name, aliases, unit in rows:
        keys = {_norm(name)}
        for a in (aliases or "").split(","):
            a = a.strip()
            if a:
                keys.add(_norm(a))
        index.append((keys, unit or ""))
    return index

def lookup(n, index):
    nn = _norm(n)
    if not nn:
        return ""
    for keys, u in index:
        if nn in keys:
            return u
    for keys, u in index:
        for k in keys:
            if k and len(k) >= 2 and len(nn) >= 2 and (k in nn or nn in k):
                return u
    return ""

index = build_index()
plans = cur.execute("SELECT id, item FROM eqa_plans").fetchall()
item_count = {}
for pid, item in plans:
    for it in _split_items(item):
        item_count[it] = item_count.get(it, 0) + 1

unmatched = {it: c for it, c in item_count.items() if not lookup(it, index)}
print(f"\n去重项目名: {len(item_count)}，仍未匹配(单位空): {len(unmatched)}")
for it in sorted(unmatched):
    print(f"  ✗ {it}  (×{unmatched[it]})")

conn.close()
