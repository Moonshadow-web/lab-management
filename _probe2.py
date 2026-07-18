import os, openpyxl, urllib.request, urllib.parse, json

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"

def req(method, path, tok=None):
    h = {"Content-Type": "application/json"}
    if tok: h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(BASE + path, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, json.loads(resp.read())

r = urllib.request.Request(BASE + "/auth/login", data=urllib.parse.urlencode({"username":"jinzizheng","password":"Jzz6827556"}).encode(), headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
TOK = json.loads(urllib.request.urlopen(r, timeout=30).read())["access_token"]

# group configs
for gid in (1, 2, 4):
    st, g = req("GET", f"/comparison/groups/{gid}", TOK)
    print(f"=== GROUP {gid} {g.get('name')} ===")
    print("  ref_id:", g.get("reference_instrument_id"), "insts:", g.get("instrument_ids"), "levels:", g.get("levels"), "form_code:", g.get("form_code"))
    print("  items:", [(it.get("name"), it.get("te")) for it in g.get("items", [])][:8], "...total", len(g.get("items", [])))

# plan 1 (生化) results: show items count per level + a few samples
st, res = req("GET", "/comparison/plans/1/results", TOK)
print("=== PLAN1 (生化) quant count:", len(res.get("quant", [])))
from collections import Counter
lvl = Counter(q.get("level") for q in res.get("quant", []))
print("  levels distribution:", dict(lvl))
print("  sample:", res.get("quant", [])[:3])

# Dump 生化 Excel data structure (horizontal multi-level)
d = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
wb = openpyxl.load_workbook(os.path.join(d, "BG-SM-CZ-025-定量室内比对结果分析表（生化分析仪）.xlsx"), data_only=True)
ws = wb.active
print("=== 生化 EXCEL structure ===")
print("row3:", [ws.cell(row=3, column=c).value for c in range(1, 28)])
print("row4:", [ws.cell(row=4, column=c).value for c in range(1, 28)])
# scan rows 5..15 to see item rows
for rr in range(5, 16):
    vals = [ws.cell(row=rr, column=c).value for c in range(1, 28)]
    # only print non-empty-ish
    if any(v is not None for v in vals):
        print(f"  row{rr}:", vals)
