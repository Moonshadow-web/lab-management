"""凝血项目质量目标：水平1/水平2 区分回归测试。

用线上 online_backup.json 的 test_items + 当前 all_seed() 的 quality_requirements
实跑真实函数（find_test_item_by_name → resolved name → lookup_quality_goal(level)），
核对每个凝血 LIS 标签在水平1/水平2（及 FDP 水平3）下的允许不精密度是否等于
《室内质控月小结》docx 中标注的目标。
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

import app.services.qc_service as qc
from app.services.quality_requirements_seed import all_seed
from app.models.test_item import TestItem
from app.models.quality_requirement import QualityRequirement

BACKUP = r"d:/workbuddyprojects/网页版-生免速查工具/online_backup.json"
data = json.load(open(BACKUP, encoding="utf-8"))


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self, ti_rows, qr_rows):
        self._ti = ti_rows
        self._qr = qr_rows

    def query(self, cls):
        if cls is TestItem:
            return FakeQuery(self._ti)
        if cls is QualityRequirement:
            return FakeQuery(self._qr)
        return FakeQuery([])


# 构造 test_items（来自线上备份）
ti_rows = []
for r in data["test_items"]:
    o = TestItem()
    o.id = r.get("id")
    o.name = r.get("name") or ""
    o.aliases = r.get("aliases") or ""
    o.instrument = r.get("instrument") or ""
    o.instrument_group = r.get("instrument_group") or ""
    ti_rows.append(o)

# 构造 quality_requirements（来自当前 all_seed —— 含本次新增 6 项）
qr_rows = []
for r in all_seed():
    o = QualityRequirement()
    o.source = r["source"]
    o.item_name = r["item_name"]
    o.category = r.get("category", "")
    o.cv = r.get("cv", "")
    o.bias = r.get("bias", "")
    o.tea = r.get("tea", "")
    o.unit = r.get("unit", "")
    qr_rows.append(o)

DB = FakeDB(ti_rows, qr_rows)


def resolve_goal(lis_token: str, level: str) -> str:
    """模拟上传路径：解析项目 → 取规范名 + 别名 → 按水平查质量目标。"""
    matched = qc.find_test_item_by_name(DB, lis_token)
    aliases = matched.aliases if matched else ""
    resolved = matched.name if matched else lis_token
    return qc.lookup_quality_goal(resolved, aliases, DB, level=level)


# 期望：(LIS标签, [(水平, 期望目标), ...])
EXPECT = {
    "APTT":               [("水平1", "6.5%"), ("水平2", "10%")],
    "D-二聚体":            [("水平1", "10%"), ("水平2", "10%")],
    "dRVVT标准化比值":      [("水平1", "10%"), ("水平2", "10%")],
    "FDP":                [("水平3", "11.7%"), ("水平1", "11.7%")],
    "FIB":                [("水平1", "9%"), ("水平2", "12%")],
    "INR":                [("水平1", "6.5%"), ("水平2", "10%")],
    "PT":                 [("水平1", "6.5%"), ("水平2", "10%")],
    "PT%":                [("水平1", "6.5%"), ("水平2", "10%")],
    "RATIO":              [("水平1", "6.5%"), ("水平2", "10%")],
    "SCT 标准化比值":       [("水平1", "10%"), ("水平2", "10%")],
    "TT":                 [("水平1", "10%"), ("水平2", "12%")],
    "抗凝血酶III":         [("水平1", "6.7%"), ("水平2", "6.7%")],
    "纤溶酶原活性":        [("水平1", "10%"), ("水平2", "10%")],
    "蛋白C":              [("水平1", "5.0%"), ("水平2", "5.0%")],
    "蛋白S":              [("水平1", "8.3%"), ("水平2", "8.3%")],
}

# 单元校验：正常/异常 解析
assert qc._parse_cv_levels("正常6.5%/异常10.0%") == {"正常": 6.5, "异常": 10.0}
assert qc._extract_level_pct("正常6.5%/异常10.0%", "水平1") == 6.5
assert qc._extract_level_pct("正常6.5%/异常10.0%", "水平2") == 10.0
assert qc._extract_level_pct("11.7%", "水平3") == 11.7
assert qc._is_level2("水平2") is True
assert qc._is_level2("水平1") is False
assert qc._is_level2("水平3") is False

ok = True
print("=== 凝血质量目标 按水平核对（上传路径实跑）===")
for token, cases in EXPECT.items():
    for level, exp in cases:
        got = resolve_goal(token, level)
        flag = "OK " if got == exp else "FAIL"
        if got != exp:
            ok = False
        print(f"  {flag} {token!r:16s} {level:5s} -> {got!r:8s} (期望 {exp!r})")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
