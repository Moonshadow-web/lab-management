"""尿液分析质量目标（docx 月小结 2026-06-12）回归测试。

用线上 online_backup.json 的 test_items + 当前 all_seed() 实跑 lookup_quality_goal，
核对《室内质控月小结_2026年06月_12.docx》中每个尿液项目在「LIS 原名」与
「test_items 规范名（尿液）」两种 key 下，允许不精密度是否都等于 docx 标注值；
并确认血清同名项目不被污染（如 肌酐=4.0% / 尿素=3.0% / 钠=1.5%）。
"""
import zipfile, json, sys, os
from xml.etree import ElementTree as ET

sys.path.insert(0, os.getcwd())
import app.services.qc_service as qc
from app.services.quality_requirements_seed import all_seed
from app.models.test_item import TestItem
from app.models.quality_requirement import QualityRequirement

DOCX = r"C:/Users/81526/Desktop/室内质控月小结_2026年06月_12.docx"
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

# LIS 原名 -> test_items 规范名（尿液）
CANON = {
    "尿尿素": "尿素（尿液）", "尿尿酸": "尿酸（尿液）", "尿氯": "氯（尿液）",
    "尿淀粉酶": "淀粉酶（尿液）", "尿磷": "磷（尿液）", "尿糖": "葡萄糖（尿液）",
    "尿肌酐": "肌酐（尿液）", "尿钙": "总钙（尿液）", "尿钠": "钠（尿液）",
    "尿钾": "钾（尿液）", "尿镁": "镁（尿液）", "尿微量总蛋白": "微量总蛋白（尿液）",
    "尿ɑ1微球蛋白": "尿α1微球蛋白", "尿球蛋白G": "尿IgG",
    "尿香草扁桃酸": "香草扁桃酸", "NAG": "N-乙酰-β-D-氨基葡萄糖苷酶（尿液）",
    "微量白蛋白": "尿微量白蛋白",
}

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
print("=== 尿液 docx 目标核对（原名 + 规范名）===")
for item, (unit, goal) in docx.items():
    got = qc.lookup_quality_goal(item, "", db, level="水平1")
    flag = "OK " if got == goal else "FAIL"
    if got != goal:
        ok = False
    print(f"  {flag} {item!r:18s} -> {got!r:8s} (期望 {goal!r})")
    canon = CANON.get(item)
    if canon:
        gotc = qc.lookup_quality_goal(canon, "", db, level="水平1")
        fc = "OK " if gotc == goal else "FAIL"
        if gotc != goal:
            ok = False
        print(f"    {fc} {canon!r:30s} -> {gotc!r:8s} (期望 {goal!r})")

print("\n=== 血清同名项目不应被污染 ===")
SERUM = {"肌酐": "4.0%", "尿素": "3.0%", "钠": "1.5%", "钾": "2.5%",
         "氯": "1.5%", "钙": "2.0%", "尿酸": "4.5%", "总蛋白": "2.0%",
         "磷": "4.0%", "总钙": "2.0%"}
for item, exp in SERUM.items():
    got = qc.lookup_quality_goal(item, "", db, level="水平1")
    flag = "OK " if got == exp else "FAIL"
    if got != exp:
        ok = False
    print(f"  {flag} 血清 {item!r:6s} -> {got!r:8s} (期望 {exp!r})")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
