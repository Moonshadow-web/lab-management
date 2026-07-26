"""回归测试：凝血 LIS 标签 → test_items 项目 + 质量目标 的解析。

用线上 test_items / quality_requirements 备份(online_backup.json) 实跑真实函数，
验证 8 个凝血 token 都能对应到正确的项目，且质量目标不再落到默认 10%（SCT 无标准目标除外）。
"""
import json
import sys

BACKEND = "d:/workbuddyprojects/网页版-生免速查工具/backend"
ROOT = "d:/workbuddyprojects/网页版-生免速查工具"
sys.path.insert(0, BACKEND)

import app.services.qc_service as qc
from app.models.test_item import TestItem
from app.models.quality_requirement import QualityRequirement

BACKUP = f"{ROOT}/online_backup.json"


def load_rows():
    data = json.load(open(BACKUP, encoding="utf-8"))
    rows = []
    for r in data["test_items"]:
        t = TestItem()
        t.id = r.get("id")
        t.name = r.get("name") or ""
        t.aliases = r.get("aliases") or ""
        t.instrument = r.get("instrument") or ""
        t.instrument_group = r.get("instrument_group") or ""
        rows.append(t)
    return rows, data


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, qr_rows=None):
        self.qr_rows = qr_rows or []

    def query(self, cls):
        if cls is QualityRequirement:
            return FakeQuery(self.qr_rows)
        return FakeQuery(ROWS)


ROWS, DATA = load_rows()
QR = []
for r in DATA["quality_requirements"]:
    o = QualityRequirement()
    o.item_name = r.get("item_name") or ""
    o.source = r.get("src") or r.get("source") or r.get("category") or ""
    o.cv = r.get("cv") or ""
    o.tea = r.get("tea") or ""
    o.unit = r.get("unit") or ""
    QR.append(o)
DB = FakeDB(QR)

# token -> (期望 id, 期望 name, [解析用别名])
EXPECT = {
    "PT": (125, "凝血酶原时间", "PT, INR"),
    "PT%": (125, "凝血酶原时间", "PT, INR"),
    "APTT": (126, "活化部分凝血活酶时间", "APTT"),
    "TT": (127, "凝血酶时间", "TT"),
    "INR RATIO": (125, "凝血酶原时间", "PT, INR"),
    "蛋白C": (132, "血浆蛋白C活性", "PC, 蛋白C"),
    "抗凝血酶III": (131, "抗凝血酶III", "ATIII"),
    "SCT标准化比值": (135, "狼疮抗凝物SCT试验", "LA"),
}

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("  FAIL", msg)
    else:
        print("  OK  ", msg)


print("=== 1) 项目解析（无仪器过滤）===")
for tok, (eid, ename, _) in EXPECT.items():
    hit = qc.find_test_item_by_name(DB, tok)
    check(hit and hit.id == eid, f"{tok!r} -> id={hit.id if hit else None} {hit.name if hit else ''!r} (期望 {eid} {ename!r})")

print("=== 2) 项目解析（instrument='ACL TOP700'）===")
for tok, (eid, ename, _) in EXPECT.items():
    hit = qc.find_test_item_by_name(DB, tok, instrument="ACL TOP700")
    check(hit and hit.id == eid, f"{tok!r} -> id={hit.id if hit else None} (期望 {eid})")

print("=== 3) 质量目标解析（应非默认 10%；SCT 无标准目标，允许 10%）===")
for tok, (eid, ename, aliases) in EXPECT.items():
    g = qc.lookup_quality_goal(tok, aliases=aliases, db=DB)
    if tok == "SCT标准化比值":
        check(g is not None, f"{tok!r} 质量目标={g!r} (SCT 无标准目标，10% 可接受)")
    else:
        check(g and g != "10%", f"{tok!r} 质量目标={g!r} (期望非默认)")

print("=== 4) 生化回归 ===")
BIO = {
    "ALT": "丙氨酸氨基转移酶", "谷丙转氨酶": "丙氨酸氨基转移酶",
    "GGT": "γ-谷氨酰基转移酶", "转肽酶": "γ-谷氨酰基转移酶",
    "AST": "天门冬氨酸氨基转移酶", "谷草转氨酶": "天门冬氨酸氨基转移酶",
    "直胆红素": "直接胆红素", "LDL": "低密度脂蛋白胆固醇",
    "HDL": "高密度脂蛋白胆固醇",
}
for tok, ename in BIO.items():
    hit = qc.find_test_item_by_name(DB, tok)
    check(hit and hit.name == ename, f"{tok!r} -> {hit.name if hit else None!r} (期望 {ename!r})")

print("=== 5) 反向误命中（凝血 token 不应落到非凝血项目）===")
NON_COAG = {27, 40, 60, 77, 111, 112, 115, 188, 24, 82, 208, 175}
for tok in EXPECT:
    hit = qc.find_test_item_by_name(DB, tok)
    check(not (hit and hit.id in NON_COAG), f"{tok!r} 未误命中非凝血 id={hit.id if hit else None}")

print()
if fails:
    print(f"RESULT: {len(fails)} FAILURES")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("RESULT: ALL PASS")
