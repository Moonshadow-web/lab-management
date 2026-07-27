"""pH(血气) 与 白蛋白(A) 质量目标回归测试。

1) pH 质量目标 = 0.02 / 靶值（逐水平按靶值算相对允许误差），由后端 _ph_relative_goal 计算：
   靶值 7.40 -> 约 0.27%；靶值为 0 时退回空串（交由查表兜底）。
2) 白蛋白(A)（糖化白蛋白 GA 的配套试剂测试项目，本身非糖化白蛋白）质量目标 = 6.7%，
   LIS 名为半角括号「白蛋白(A)」，须精确匹配不被血清「白蛋白」(2.5%) 串扰。
"""
import sys, os, json

sys.path.insert(0, os.getcwd())
import app.services.qc_service as qc
from app.services.quality_requirements_seed import all_seed
from app.api.v1.qc_summaries import _ph_relative_goal
from app.models.test_item import TestItem
from app.models.quality_requirement import QualityRequirement

BACKUP = r"d:/workbuddyprojects/网页版-生免速查工具/online_backup.json"

data = json.load(open(BACKUP, encoding="utf-8"))
ti_rows = []
for r in data["test_items"]:
    o = TestItem()
    o.id = r.get("id"); o.name = r.get("name") or ""; o.aliases = r.get("aliases") or ""
    o.instrument = r.get("instrument") or ""; o.instrument_group = r.get("instrument_group") or ""
    ti_rows.append(o)
qr_rows = []
for r in all_seed():
    o = QualityRequirement()
    o.source = r["source"]; o.item_name = r["item_name"]
    o.category = r.get("category", ""); o.cv = r.get("cv", "")
    o.bias = r.get("bias", ""); o.tea = r.get("tea", ""); o.unit = r.get("unit", "")
    qr_rows.append(o)


class FakeQuery:
    def __init__(self, rows): self._r = rows
    def all(self): return self._r


class DB:
    def query(self, cls):
        if cls is TestItem: return FakeQuery(ti_rows)
        if cls is QualityRequirement: return FakeQuery(qr_rows)
        return FakeQuery([])


db = DB()
ok = True

print("=== 1) _ph_relative_goal 计算（0.02 / 靶值 * 100，保留两位小数）===")
CASES = [(7.40, "0.27%"), (7.35, "0.27%"), (7.45, "0.27%"), (0, ""), (None, "")]
for tm, exp in CASES:
    got = _ph_relative_goal(tm)
    flag = "OK " if got == exp else "FAIL"
    if got != exp:
        ok = False
    print(f"  {flag} 靶值={tm} -> {got!r:8s} (期望 {exp!r})")

print("\n=== 2) 白蛋白(A) 精确匹配 6.7%，不被血清白蛋白(2.5%) 串扰 ===")
ALB = {
    "白蛋白(A)": "6.7%",        # LIS 实际名（半角括号）
    "白蛋白（A）": "6.7%",      # 全角括号写法
    "白蛋白": "2.5%",           # 血清白蛋白保持 2.5%
    "糖化白蛋白": "6.7%",       # 糖化白蛋白本身 6.7%（独立项）
}
for item, exp in ALB.items():
    got = qc.lookup_quality_goal(item, "", db, level="水平1")
    flag = "OK " if got == exp else "FAIL"
    if got != exp:
        ok = False
    print(f"  {flag} {item!r:12s} -> {got!r:8s} (期望 {exp!r})")

print("\n=== 3) pH 查表返回标记串（实际值由 _ph_relative_goal 计算）===")
got_ph = qc.lookup_quality_goal("pH", "", db, level="水平1")
exp_ph = "0.02/靶值"
fph = "OK " if got_ph == exp_ph else "FAIL"
if got_ph != exp_ph:
    ok = False
print(f"  {fph} pH -> {got_ph!r} (期望 {exp_ph!r})")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
