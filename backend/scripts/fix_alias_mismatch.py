"""修复上一轮 backfill_aliases 中 ID 不符导致的别名错配。"""
import urllib.request
import json
import sys

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1/test-items"
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# 加载全量 items
items = {}
for p in range(1, 20):
    req = urllib.request.Request(f"{BASE}?page_size=50&page={p}", headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=10)
    d = json.loads(resp.read())
    for item in d["items"]:
        items[item["id"]] = item
    if p >= d["pages"]:
        break
print(f"Loaded {len(items)} items")

by_name = {item["name"]: item for item in items.values()}

# 需要修复的错配：{正确项目名: {add:[], remove:[]}}
# remove 是从错误分配到该项目上的别名中移除
# add 是该项目真正应该有的别名
FIXES = [
    # ── GGT 系列 ──
    ("γ-谷氨酰基转移酶", ["GGT", "γ-GT", "γ-谷氨酸氨基转移酶"], []),
    ("总胆固醇", [], ["GGT", "γ-GT"]),
    ("同型半胱氨酸", [], ["GGT", "γ-GT", "γ-谷氨酸氨基转移酶"]),
    # ── ADA 系列 ──
    ("腺苷脱氨酶", ["ADA"], []),
    ("腺苷脱氨酶（脑脊液）", ["ADA"], []),
    ("总胆汁酸", [], ["ADA"]),
    # ── CK 系列 ──
    ("肌酸激酶", ["CK", "CPK"], []),
    ("脂肪酶", [], ["CK", "CPK"]),
    # ── RF 系列 ──
    ("类风湿因子", ["RF"], []),
    ("肌酸激酶", [], ["RF", "类风湿因子"]),
    # ── CysC 系列 ──
    ("胱抑素C", ["CysC"], []),
    ("超敏肌钙蛋白Ⅰ", [], ["CysC", "胱抑素C"]),
    # ── β2MG 系列 ──
    ("β2-微球蛋白", ["β2微球蛋白", "B2M"], []),
    ("胱抑素C", [], ["β2微球蛋白", "B2M"]),
]

# 应用修复
for name, add_list, remove_list in FIXES:
    item = by_name.get(name)
    if not item:
        print(f"  SKIP: '{name}' not found")
        continue
    tid = item["id"]
    current = (item.get("aliases") or "").replace("，", ",")
    aliases = set(a.strip() for a in current.split(",") if a.strip())

    removed = [a for a in remove_list if a in aliases]
    for a in removed:
        aliases.discard(a)

    added = [a for a in add_list if a not in aliases]
    for a in added:
        aliases.add(a)

    new_val = ", ".join(sorted(aliases))
    old_val = item.get("aliases", "")
    if new_val != old_val:
        # 通过 diag SQL 端点更新
        print(f"  FIX id={tid} '{name[:25]}': -{removed} +{added}")
        # TODO: call backfill endpoint with specific fix
    else:
        print(f"  OK  id={tid} '{name[:25]}': no change")

print("\nDone. Run fix_aliases_via_diag endpoint to apply changes.")
