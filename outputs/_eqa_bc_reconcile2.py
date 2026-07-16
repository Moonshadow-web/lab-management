import sqlite3, re
from collections import defaultdict

DB = "data/app.db"
USER_LIST = open("outputs/_eqa_bc_reconcile.py", encoding="utf-8").read().split('USER_LIST = """',1)[1].split('"""',1)[0]

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

# 去标本后缀，用于跨标本归并
def base(s):
    return re.sub(r"[（(].*?[)）]", "", s).strip()

# 同物异名（短代码/汉字）
PAIRS = [
    ("凝血酶原时间","PT"),("INR","INR"),("活化部分凝血活酶时间","APTT"),
    ("凝血酶时间","TT"),("纤维蛋白原","FIB"),("血浆D-二聚体","D-Dimer"),
    ("纤维蛋白（原）降解产物","FDP"),("抗Xa活性","抗FXa活性"),("vWF因子","vWF"),
    ("血浆蛋白C活性","蛋白C"),("血浆蛋白S活性","蛋白S"),
    ("葡萄糖","血糖"),("总钙","钙"),("总钙","离子钙"),("离子钙","离子钙"),
    ("γ－谷氨酰基转移酶","γ-谷氨酰基转移酶"),("γ-谷氨酰基转移酶","γ-谷氨酸氨基转移酶"),
    ("甘油三酯","甘油三脂"),("总胆固醇","胆固醇"),
    ("载脂蛋白A","载脂蛋白A1"),("脂蛋白a","脂蛋白（a）"),
    ("不饱和铁结合力","总铁结合力"),("铜","铜离子"),
    ("超敏C反应蛋白","CRP"),("抗链球菌溶素O","ASO"),("类风湿因子","RF"),
    ("补体3","C3"),("补体4","C4"),("免疫球蛋白A","IgA"),("免疫球蛋白M","IgM"),
    ("免疫球蛋白G","IgG"),("免疫球蛋白轻链κ（血清）","免疫球蛋白轻链κ"),
    ("免疫球蛋白轻链λ（血清）","免疫球蛋白轻链λ"),("免疫球蛋白G4（IgG4）","免疫球蛋白G4"),
    ("铜蓝蛋白CER","铜蓝蛋白"),("总二氧化碳","碳酸氢根"),("ADA","腺苷脱氨酶"),
    ("尿球蛋白G","尿IgG"),("尿ɑ1微球蛋白","尿α1微球蛋白"),
    ("肌酸激酶-MB同工酶质量","肌酸激酶-MB"),("肌钙蛋白I","肌钙蛋白-I"),
    ("B型钠尿肽","BNP"),("血清降钙素原","PCT"),("白介素-6","IL-6"),
    ("胱抑素C","Cys-C"),("血清淀粉样蛋白A","SAA"),("糖化血红蛋白","HbA1c"),
    ("糖化白蛋白","GA"),
]
adj = defaultdict(set)
for a,b in PAIRS: adj[a].add(b); adj[b].add(a)
def closure(s):
    seen={s}; st=[s]
    while st:
        x=st.pop()
        for y in adj[x]:
            if y not in seen: seen.add(y); st.append(y)
    return seen

db=sqlite3.connect(DB); cur=db.cursor()
cur.execute('SELECT id, program, org, "group", item FROM eqa_plans')
plans=cur.fetchall()
name_info={}
for pid,prog,org,grp,item in plans:
    for s in split_items(item):
        info=name_info.setdefault(s,{"groups":set(),"programs":set()})
        info["groups"].add(grp); info["programs"].add(prog)
db_bc={n for n,info in name_info.items()
       if "生化+凝血" in set(category_of(g) for g in info["groups"])}

user_items=[l.strip() for l in USER_LIST.strip().splitlines() if l.strip()]

# 用户项 -> 用 base+闭包 在 DB 找（不区分标本后缀）
print("=== 真缺口（库里任何 group 都没有，含跨标本归并）===")
true_missing=[]
for u in user_items:
    cl=closure(u)|{base(u)}
    hits=[n for n in name_info if n in cl or base(n) in cl or n==base(u)]
    if not hits:
        true_missing.append(u); print("  ",u)
print("真缺口数:", len(true_missing))

# DB 生化+凝血 中，来自『正确度验证』类 program 的项目（这些通常不算常规质评）
verify_progs={"代谢物、总蛋白正确度验证","电解质正确度验证","脂类正确度验证",
              "酶学正确度验证","同型半胱氨酸正确度","甲功相关项目检测及正确度验证",
              "类固醇激素正确度验证","脂类正确度验证"}
print("\n=== DB 生化+凝血 来自『正确度验证』类 program 的细项 ===")
verify_items=set()
for n,info in name_info.items():
    if "生化+凝血" in set(category_of(g) for g in info["groups"]):
        if info["programs"] & verify_progs:
            verify_items.add(n)
for n in sorted(verify_items):
    print("  %s  programs=%s" % (n, sorted(name_info[n]["programs"])))
print("正确度验证类细项数:", len(verify_items))

# 各 program 对 生化+凝血 去重项 的贡献（看重复/验证项目）
print("\n=== 生化+凝血 各 program 细项数（去重后归属）===")
prog_items=defaultdict(set)
for n,info in name_info.items():
    if "生化+凝血" in set(category_of(g) for g in info["groups"]):
        for p in info["programs"]:
            prog_items[p].add(n)
for p in sorted(prog_items, key=lambda x:-len(prog_items[x])):
    tag="  [正确度验证]" if p in verify_progs else ""
    print("  %-30s %2d 项%s" % (p, len(prog_items[p]), tag))

# 跨 program 重复（去重合并掉的项）
print("\n=== 跨多 program 重复、被去重合并的项（造成 原始数>去重数）===")
multi={n:info["programs"] for n,info in name_info.items()
       if "生化+凝血" in set(category_of(g) for g in info["groups"]) and len(info["programs"])>1}
for n,ps in sorted(multi.items(), key=lambda x:-len(x[1])):
    print("  %s  -> %d program: %s" % (n, len(ps), sorted(ps)))

print("\n=== 汇总 ===")
print("用户清单:", len(user_items), "| DB生化+凝血去重:", len(db_bc))
print("用户真缺口:", len(true_missing))
print("正确度验证类细项(虚增):", len(verify_items))
print("跨program重复(去重合并):", len(multi))
