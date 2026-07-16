import sqlite3, re

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
免疫球蛋白轻链κ（尿液）
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

user_items = [l.strip() for l in USER_LIST.strip().splitlines() if l.strip()]
print("用户清单项目数:", len(user_items))

db = sqlite3.connect(DB); cur = db.cursor()
cur.execute('SELECT id, program, org, "group", item FROM eqa_plans')
plans = cur.fetchall()

# 收集 DB 中所有 analyte -> 它所在的 (group, programs)
name_info = {}  # name -> {"groups": set(), "programs": set()}
for pid, prog, org, grp, item in plans:
    cat = category_of(grp)
    for s in split_items(item):
        info = name_info.setdefault(s, {"groups": set(), "programs": set()})
        info["groups"].add(grp)
        info["programs"].add(prog)

# 用户每项 -> 在 DB 的归类
print("\n=== 用户清单每项在 DB 中的归类 ===")
label_issue = []  # 用户认为是生化，但 DB 不在 生化+凝血
missing = []      # 用户清单里 DB 完全没有的项
for u in user_items:
    if u in name_info:
        info = name_info[u]
        cats = set(category_of(g) for g in info["groups"])
        if "生化+凝血" not in cats:
            label_issue.append((u, info["groups"], sorted(info["programs"])))
    else:
        missing.append(u)

print("  用户清单中 DB 完全没有的项 (missing):", missing)
print("\n  用户清单中归类非 生化+凝血 的项 (可能错归):")
for u, groups, progs in label_issue:
    print("    %s  group=%s  programs=%s" % (u, groups, progs))

# DB 生化+凝血 去重项里，用户没列的（extra in DB vs user list）
db_bc = {n for n, info in name_info.items() if "生化+凝血" in set(category_of(g) for g in info["groups"])}
user_set = set(user_items)
extra_in_db = sorted(db_bc - user_set)
print("\n=== DB 生化+凝血 有、但用户清单没列的项 (%d) ===" % len(extra_in_db))
for n in extra_in_db:
    info = name_info[n]
    print("    %s  group=%s" % (n, sorted(info["groups"])))

print("\n=== 汇总 ===")
print("  用户清单项数:", len(user_items))
print("  DB 生化+凝血 去重项数:", len(db_bc))
print("  用户在 DB 缺失项:", len(missing))
print("  用户清单中错归(非生化+凝血)项:", len(label_issue))
print("  DB 有但用户未列项:", len(extra_in_db))
