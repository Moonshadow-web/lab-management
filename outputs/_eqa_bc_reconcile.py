import sqlite3, re
from collections import defaultdict

DB = "data/app.db"

USER_LIST = """凝血酶原时间
活化部分凝血活酶时间
凝血酶时间
纤维蛋白原
血浆D-二聚体
纤维蛋白（原）降解产物
抗凝血酶III
血浆蛋白C活性
血浆蛋白S活性
抗Xa活性
sdLDL
vWF因子
钠
钾
氯
葡萄糖
尿素
肌酐
尿酸
总钙
镁
磷
丙氨酸氨基转移酶
天门冬氨酸氨基转移酶
总蛋白
白蛋白
总胆红素
直接胆红素
碱性磷酸酶
γ－谷氨酰基转移酶
淀粉酶
脂肪酶
肌酸激酶
乳酸脱氢酶
胆碱酯酶
铁
不饱和铁结合力
血清锌
铜
甘油三酯
总胆固醇
高密度脂蛋白胆固醇
低密度脂蛋白胆固醇
载脂蛋白A
载脂蛋白B
脂蛋白a
钠（尿液）
钾（尿液）
氯（尿液）
葡萄糖（尿液）
尿素（尿液）
肌酐（尿液）
尿酸（尿液）
总钙（尿液）
镁（尿液）
磷（尿液）
淀粉酶（尿液）
微量总蛋白（尿液）
微量白蛋白（尿液）
微量总蛋白（脑脊液）
氯（脑脊液）
葡萄糖（脑脊液）
微量白蛋白（脑脊液）
乳酸脱氢酶（脑脊液）
超敏C反应蛋白
前白蛋白
抗链球菌溶素O
类风湿因子
补体3
补体4
免疫球蛋白A
免疫球蛋白M
免疫球蛋白G
触珠蛋白
免疫球蛋白轻链κ（血清）
免疫球蛋白轻链λ（血清）
免疫球蛋白G4（IgG4）
铜蓝蛋白CER
总胆汁酸
乳酸
总二氧化碳
β-羟丁酸
ADA
血气和酸碱分析PH
尿球蛋白G
尿ɑ1微球蛋白
免疫球蛋白轻链κ（尿液）
免疫球蛋白轻链λ（尿液）
尿转铁蛋白
肌酸激酶-MB同工酶质量
肌钙蛋白I
肌红蛋白
同型半胱氨酸
B型钠尿肽
血清降钙素原
白介素-6
胱抑素C
血清淀粉样蛋白A
糖化血红蛋白
糖化白蛋白
血清蛋白电泳-清蛋白"""

def split_items(raw):
    raw = re.sub(r"^(具体项目|项目|检测项目)[：:]\s*", "", raw or "")
    return [p.strip() for p in re.split(r"[、,，/]", raw) if p.strip()]

def category_of(group):
    g = (group or "").strip()
    if g in ("生化", "凝血"):
        return "生化+凝血"
    if g == "免疫":
        return "免疫"
    return "其他"

# ---- 同物异名闭包（生化/凝血领域）----
PAIRS = [
    ("凝血酶原时间","PT"),("凝血酶原时间INR","INR"),("INR","INR"),
    ("活化部分凝血活酶时间","APTT"),("APTT","APTT"),
    ("凝血酶时间","TT"),("TT","TT"),
    ("纤维蛋白原","FIB"),("FIB","FIB"),
    ("血浆D-二聚体","D-Dimer"),("D-Dimer","D-Dimer"),
    ("纤维蛋白（原）降解产物","FDP"),("FDP","FDP"),
    ("抗Xa活性","抗FXa活性"),("抗FXa活性","抗FXa活性"),
    ("vWF因子","vWF"),("vWF","vWF"),
    ("血浆蛋白C活性","蛋白C"),("蛋白C","蛋白C"),
    ("血浆蛋白S活性","蛋白S"),("蛋白S","蛋白S"),
    ("葡萄糖","血糖"),("血糖","葡萄糖"),
    ("总钙","钙"),("钙","总钙"),("离子钙","离子钙"),("总钙","离子钙"),
    ("γ－谷氨酰基转移酶","γ-谷氨酰基转移酶"),("γ-谷氨酰基转移酶","γ-谷氨酸氨基转移酶"),
    ("甘油三酯","甘油三脂"),("甘油三脂","甘油三酯"),
    ("总胆固醇","胆固醇"),("胆固醇","总胆固醇"),
    ("载脂蛋白A","载脂蛋白A1"),("载脂蛋白A1","载脂蛋白A"),
    ("脂蛋白a","脂蛋白（a）"),("脂蛋白（a）","脂蛋白a"),
    ("不饱和铁结合力","总铁结合力"),("总铁结合力","不饱和铁结合力"),
    ("铜","铜离子"),("铜离子","铜"),
    ("超敏C反应蛋白","CRP"),("CRP","超敏C反应蛋白"),
    ("抗链球菌溶素O","ASO"),("ASO","抗链球菌溶素O"),
    ("类风湿因子","RF"),("RF","类风湿因子"),
    ("补体3","C3"),("C3","补体3"),
    ("补体4","C4"),("C4","补体4"),
    ("免疫球蛋白A","IgA"),("IgA","免疫球蛋白A"),
    ("免疫球蛋白M","IgM"),("IgM","免疫球蛋白M"),
    ("免疫球蛋白G","IgG"),("IgG","免疫球蛋白G"),
    ("免疫球蛋白轻链κ（血清）","免疫球蛋白轻链κ"),("免疫球蛋白轻链κ","免疫球蛋白轻链κ（血清）"),
    ("免疫球蛋白轻链λ（血清）","免疫球蛋白轻链λ"),("免疫球蛋白轻链λ","免疫球蛋白轻链λ（血清）"),
    ("免疫球蛋白G4（IgG4）","免疫球蛋白G4"),("免疫球蛋白G4","免疫球蛋白G4（IgG4）"),
    ("铜蓝蛋白CER","铜蓝蛋白"),("铜蓝蛋白","铜蓝蛋白CER"),
    ("总二氧化碳","碳酸氢根"),("碳酸氢根","总二氧化碳"),
    ("ADA","腺苷脱氨酶"),("腺苷脱氨酶","ADA"),
    ("尿球蛋白G","尿IgG"),("尿IgG","尿球蛋白G"),
    ("尿ɑ1微球蛋白","尿α1微球蛋白"),("尿α1微球蛋白","尿ɑ1微球蛋白"),
    ("免疫球蛋白轻链κ（尿液）","免疫球蛋白轻链κ（尿液）"),
    ("免疫球蛋白轻链λ（尿液）","免疫球蛋白轻链λ（尿液）"),
    ("肌酸激酶-MB同工酶质量","肌酸激酶-MB"),("肌酸激酶-MB","肌酸激酶-MB同工酶质量"),
    ("肌钙蛋白I","肌钙蛋白-I"),("肌钙蛋白-I","肌钙蛋白I"),
    ("B型钠尿肽","BNP"),("BNP","B型钠尿肽"),
    ("血清降钙素原","PCT"),("PCT","血清降钙素原"),
    ("白介素-6","IL-6"),("IL-6","白介素-6"),
    ("胱抑素C","Cys-C"),("Cys-C","胱抑素C"),
    ("血清淀粉样蛋白A","SAA"),("SAA","血清淀粉样蛋白A"),
    ("糖化血红蛋白","HbA1c"),("HbA1c","糖化血红蛋白"),
    ("糖化白蛋白","GA"),("GA","糖化白蛋白"),
    ("微量白蛋白","微量白蛋白"),("微量总蛋白","微量总蛋白"),
    ("血气和酸碱分析PH","Ph"),("Ph","血气和酸碱分析PH"),
    ("血气和酸碱分析PH","PO2"),("PO2","血气和酸碱分析PH"),
    ("血气和酸碱分析PH","pCO2"),("pCO2","血气和酸碱分析PH"),
    ("血清蛋白电泳-清蛋白","血清蛋白电泳（M蛋白）"),
    ("sdLDL","sdLDL"),
]
adj = defaultdict(set)
for a, b in PAIRS:
    adj[a].add(b); adj[b].add(a)
def closure(s):
    seen = {s}; st = [s]
    while st:
        x = st.pop()
        for y in adj[x]:
            if y not in seen:
                seen.add(y); st.append(y)
    return seen

db = sqlite3.connect(DB); cur = db.cursor()
cur.execute('SELECT id, program, org, "group", item FROM eqa_plans')
plans = cur.fetchall()

# DB: name -> {groups, programs}
name_info = {}
for pid, prog, org, grp, item in plans:
    for s in split_items(item):
        info = name_info.setdefault(s, {"groups": set(), "programs": set()})
        info["groups"].add(grp)
        info["programs"].add(prog)

# DB 生化+凝血 distinct names (按 group 归类)
db_bc = {n for n, info in name_info.items()
         if "生化+凝血" in set(category_of(g) for g in info["groups"])}

user_items = [l.strip() for l in USER_LIST.strip().splitlines() if l.strip()]

# 对每个用户项，构建闭包，去 DB 找命中（任何 group），记录命中的 group
print("=== 逐项核对（用户清单 -> DB 命中情况）===")
true_missing = []      # 用户项 DB 任何 group 都无
mislabeled = []        # 用户项只在 免疫/其他 group 命中（应属生化但被错归）
for u in user_items:
    cl = closure(u)
    hits = [n for n in name_info if n in cl]
    if not hits:
        true_missing.append(u)
        print("  [缺] %s" % u)
        continue
    # 收集命中项的 group
    groups_hit = set()
    for n in hits:
        groups_hit |= set(category_of(g) for g in name_info[n]["groups"])
    if "生化+凝血" not in groups_hit:
        mislabeled.append((u, sorted(hits), sorted(groups_hit)))
        print("  [错归] %s -> DB名%s groups=%s" % (u, hits, sorted(groups_hit)))
    # else: OK（匹配到生化+凝血）

print("\n=== 用户项 DB 完全缺失(真缺口): %d ===" % len(true_missing))
for u in true_missing: print("  ", u)

print("\n=== 用户项被归到非生化+凝血(错归/被总结漏掉): %d ===" % len(mislabeled))
for u, hits, gs in mislabeled: print("  %s -> %s %s" % (u, hits, gs))

# DB 生化+凝血 有、但用户清单未列的（需看是否命名差或真多余）
user_closures = [closure(u) for u in user_items]
user_norm = set()
for cl in user_closures:
    user_norm |= cl
extra_db = []
for n in db_bc:
    if n not in user_norm:
        extra_db.append(n)
print("\n=== DB 生化+凝血 有、用户清单经同物异名仍无对应: %d ===" % len(extra_db))
for n in sorted(extra_db):
    info = name_info[n]
    print("  %s  groups=%s  programs=%s" % (n, sorted(info["groups"]), sorted(info["programs"])))

print("\n=== 数字汇总 ===")
print("  用户清单项数:", len(user_items))
print("  DB 生化+凝血 去重项数:", len(db_bc))
print("  用户真缺口(库无):", len(true_missing))
print("  用户错归(非生化+凝血):", len(mislabeled))
print("  DB多出于用户(经命名仍无对应):", len(extra_db))
