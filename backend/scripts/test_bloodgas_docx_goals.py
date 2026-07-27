"""血气分析仪质量目标（docx 月小结 2026-06-13）回归测试。

用 online_backup.json 的 test_items + 当前 all_seed() 实跑 lookup_quality_goal，
核对《室内质控月小结_2026年06月_13.docx》中每个血气项目（LIS 原名）的
允许不精密度是否都等于 docx 标注值；pH 的 docx 目标列为空，按用户要求=靶值*0.02（相对 2%）。
并确认血清同名电解质不被污染（钾2.5%/钠1.5%/钙2.0%/氯1.5% 不变）。
"""
import zipfile, json, sys, os
from xml.etree import ElementTree as ET

sys.path.insert(0, os.getcwd())
import app.services.qc_service as qc
from app.services.quality_requirements_seed import all_seed
from app.models.test_item import TestItem
from app.models.quality_requirement import QualityRequirement
from app.api.v1.qc_summaries import QC_UNIT_OVERRIDES

DOCX = r"C:/Users/81526/Desktop/室内质控月小结_2026年06月_13.docx"
BACKUP = r"d:/workbuddyprojects/网页版-生免速查工具/online_backup.json"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _ct(tc):
    return "".join(t.text or "" for t in tc.iter(W + "t"))


def load_docx(path):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml").decode("utf-8"))
    tbl = next(root.iter(W + "tbl"))
    rows = [[_ct(tc) for tc in tr.iter(W + "tc")] for tr in tbl.iter(W + "tr")]
    hdr = rows[0]
    out = {}
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        item = d["项目"].strip()
        if item not in out:
            out[item] = (d["单位"].strip(), d["质量目标（允许不精密度）"].strip())
    return out


docx = load_docx(DOCX)

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

# pH docx 目标列为空，按用户要求 = 0.02/靶值（逐水平相对值）；查表返回标记串，
# 实际「质量目标」列由后端 _ph_relative_goal 按靶值计算（见 test_ph_albumin_goals.py）
EXPECT_OVERRIDE = {"pH": "0.02/靶值"}

ok = True
print("=== 血气 docx 目标核对（LIS 原名）===")
for item, (unit, goal) in docx.items():
    exp = EXPECT_OVERRIDE.get(item, goal)
    got = qc.lookup_quality_goal(item, "", db, level="水平1")
    flag = "OK " if got == exp else "FAIL"
    if got != exp:
        ok = False
    print(f"  {flag} {item!r:14s} -> {got!r:8s} (期望 {exp!r})")

print("\n=== tHb 单位纠正（QC_UNIT_OVERRIDES）===")
exp_u = "g/L"
got_u = QC_UNIT_OVERRIDES.get("tHb")
fu = "OK " if got_u == exp_u else "FAIL"
if got_u != exp_u:
    ok = False
print(f"  {fu} tHb 单位 -> {got_u!r} (期望 {exp_u!r})")

print("\n=== 血清电解质不应被血气项污染 ===")
SERUM = {"钾": "2.5%", "钠": "1.5%", "钙": "2.0%", "氯": "1.5%"}
for item, exp in SERUM.items():
    got = qc.lookup_quality_goal(item, "", db, level="水平1")
    flag = "OK " if got == exp else "FAIL"
    if got != exp:
        ok = False
    print(f"  {flag} 血清 {item!r:4s} -> {got!r:8s} (期望 {exp!r})")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
