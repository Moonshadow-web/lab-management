import sqlite3, re

DB = "data/app.db"

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

db = sqlite3.connect(DB); cur = db.cursor()

# 1) group 字段分布
cur.execute("SELECT \"group\", count(*) FROM eqa_plans GROUP BY \"group\" ORDER BY \"group\"")
print("=== eqa_plans group 分布 ===")
for r in cur.fetchall():
    print("  group=%r count=%d" % r)

# 2) 每个 program 的 group 值（看生化项目是否有归错类的）
print("\n=== 各 program 的 group 取值 ===")
cur.execute("SELECT DISTINCT program, \"group\" FROM eqa_plans ORDER BY program")
prog_group = {}
for prog, grp in cur.fetchall():
    prog_group.setdefault(prog, set()).add(grp)
    print("  %-40s -> %s" % (prog, grp))

# 3) 原始生化 analyte 计数（group in 生化/凝血 的计划，所有 item token）
cur.execute("SELECT id, program, org, \"group\", item FROM eqa_plans")
plans = cur.fetchall()

# 3a) 不去重：原始 token 总数
# 3b) 按名称去重（跨所有生化/凝血计划）
raw_tokens = []
dedup_names = set()
# 也按 (name, program) 统计重复出现在多个 program 的次数
name_programs = {}
bc_plans = 0
for pid, prog, org, grp, item in plans:
    cat = category_of(grp)
    if cat != "生化+凝血":
        continue
    bc_plans += 1
    subs = split_items(item)
    for s in subs:
        raw_tokens.append(s)
        dedup_names.add(s)
        name_programs.setdefault(s, set()).add(prog)

print("\n=== 生化+凝血 原始统计 ===")
print("  纳入计划数(plan_count):", bc_plans)
print("  不去重 analyte token 总数:", len(raw_tokens))
print("  按名称去重后 distinct analyte 数:", len(dedup_names))

# 4) 模拟 summary 的 half=0 全年的 items_total（按 _compute_summary_by_category 逻辑：
#    按 group 分桶，桶内 items 字典 key=name 去重）
#    这里 full year (half=0, 不过滤 due_date)
cats = {}
for pid, prog, org, grp, item in plans:
    cat = category_of(grp)
    if cat not in ("生化+凝血", "免疫"):
        continue
    b = cats.setdefault(cat, {"programs": set(), "items": {}})
    b["programs"].add(prog)
    for s in split_items(item):
        b["items"].setdefault(s, set()).add(prog)

print("\n=== 模拟 summary (half=0, 全部门) items_total ===")
for cat in ("生化+凝血", "免疫", "其他"):
    if cat in cats:
        b = cats[cat]
        print("  %s: programs=%d items_total(去重)=%d" % (cat, len(b["programs"]), len(b["items"])))

# 5) 列出在多个 program 出现、会被去重的 analyte（这些造成 原始>去重）
print("\n=== 跨多 program 重复出现的生化 analyte（去重会合并） ===")
multi = {n: ps for n, ps in name_programs.items() if len(ps) > 1}
print("  重复 analyte 数:", len(multi))
for n, ps in sorted(multi.items(), key=lambda x: -len(x[1])):
    print("  %s  -> %d个program: %s" % (n, len(ps), sorted(ps)))
