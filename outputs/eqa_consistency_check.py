# -*- coding: utf-8 -*-
"""
EQA 与 项目查询(test_items) 一致性对照分析（只读，不改库）
以 test_items 为基准，检查 eqa_plans 里录入的每个分析物是否能对上标准项目名。
输出对照报告 CSV。
"""
import sqlite3, json, re, csv, os

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.db')
OUT = os.path.join(os.path.dirname(__file__), 'eqa_consistency_report.csv')

db = sqlite3.connect(DB)
c = db.cursor()

# ---------- 1. 建立 test_items 标准名 & 别名索引 ----------
def norm(s):
    """归一化：去空白/全角空格/制表，转小写，去常见标点差异"""
    if not s: return ''
    s = str(s).strip()
    s = s.replace('\t', '').replace('\u3000', '').replace(' ', '')
    s = s.replace('（', '(').replace('）', ')')
    s = s.replace('Ⅰ', 'I').replace('Ⅱ', 'II').replace('Ⅲ', 'III').replace('Ⅳ', 'IV')
    return s.lower()

std = {}       # norm(name) -> (id, name, category)
alias_idx = {} # norm(alias) -> (id, name, category)
name_list = []
for r in c.execute('select id,name,aliases,category from test_items'):
    tid, name, aliases, cat = r
    name_list.append((tid, name, cat))
    std[norm(name)] = (tid, name, cat)
    if aliases:
        for a in re.split(r'[、,，/;；|\s]+', aliases):
            a = a.strip()
            if a:
                alias_idx.setdefault(norm(a), (tid, name, cat))

# ---------- 2. 提取 EQA 所有分析物 ----------
SPLIT = re.compile(r'[、,，;；]+')  # 顿号/逗号/分号

def split_items(item_str):
    if not item_str: return []
    parts = SPLIT.split(item_str.replace('\t', '、'))
    return [p.strip() for p in parts if p.strip()]

# 收集：analyte -> set of (plan_id, program)
rows = []
analyte_occ = {}  # norm(analyte) -> {'raw':原名集合, 'plans':set}
for r in c.execute('select id,program,item,result_data,\"group\",year from eqa_plans'):
    pid, program, item, rdata, grp, year = r
    analytes = []
    # 优先用 result_data.items（真正录入的分析物名）
    used_rd = False
    if rdata:
        try:
            d = json.loads(rdata)
            if isinstance(d, dict) and d.get('items'):
                analytes = [str(x).strip() for x in d['items'] if str(x).strip()]
                used_rd = True
        except Exception:
            pass
    if not analytes:
        analytes = split_items(item)
    for a in analytes:
        key = norm(a)
        rec = analyte_occ.setdefault(key, {'raw': set(), 'plans': set(), 'programs': set(), 'src': set()})
        rec['raw'].add(a)
        rec['plans'].add(pid)
        rec['programs'].add(program)
        rec['src'].add('result_data' if used_rd else 'item字段')

# ---------- 3. 对照 ----------
matched, alias_matched, unmatched = [], [], []
for key, rec in sorted(analyte_occ.items()):
    raw = ' / '.join(sorted(rec['raw']))
    plans = ','.join(str(p) for p in sorted(rec['plans']))
    programs = ' | '.join(sorted(rec['programs']))
    src = ','.join(sorted(rec['src']))
    if key in std:
        tid, sname, cat = std[key]
        matched.append((raw, sname, tid, cat, plans, programs, src))
    elif key in alias_idx:
        tid, sname, cat = alias_idx[key]
        alias_matched.append((raw, sname, tid, cat, plans, programs, src))
    else:
        unmatched.append((raw, plans, programs, src))

# ---------- 4. 反向：test_items 里有、但 EQA 从未出现的项目（仅统计，不一定要改） ----------
eqa_keys = set(analyte_occ.keys())
ti_not_in_eqa = []
for tid, name, cat in name_list:
    if norm(name) not in eqa_keys:
        # 也检查别名是否命中
        hit = False
        # (name 的别名若在 eqa 中也算命中——简化：只按 name)
        ti_not_in_eqa.append((tid, name, cat))

# ---------- 输出 ----------
print('=== 汇总 ===')
print(f'test_items 项目数: {len(name_list)}')
print(f'EQA 去重分析物数: {len(analyte_occ)}')
print(f'  精确命中标准名: {len(matched)}')
print(f'  命中别名(名称写法不同,建议统一): {len(alias_matched)}')
print(f'  完全对不上(EQA有/项目查询无): {len(unmatched)}')
print()
print('=== [A] 命中别名——EQA写法与标准名不同(建议在EQA端改用标准名) ===')
for raw, sname, tid, cat, plans, programs, src in alias_matched:
    print(f'  EQA「{raw}」 → 标准名「{sname}」(id={tid},{cat}) | plans={plans}')
print()
print('=== [B] 完全对不上(EQA有,项目查询里既无同名也无别名) ===')
for raw, plans, programs, src in unmatched:
    print(f'  「{raw}」 | plans={plans} | {programs[:60]}')

with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['对照类型', 'EQA分析物(原写法)', '项目查询标准名', 'test_item_id', '分类', '涉及plan_id', '来源', '涉及质评项目'])
    for raw, sname, tid, cat, plans, programs, src in matched:
        w.writerow(['精确一致', raw, sname, tid, cat, plans, src, programs])
    for raw, sname, tid, cat, plans, programs, src in alias_matched:
        w.writerow(['别名(写法不同)', raw, sname, tid, cat, plans, src, programs])
    for raw, plans, programs, src in unmatched:
        w.writerow(['对不上', raw, '', '', '', plans, src, programs])
print(f'\n报告已写: {OUT}')
db.close()
