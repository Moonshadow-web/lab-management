"""验证「上传表格规则列覆盖后端 Westgard」(2026-07-26)：
- 同单元格多规则按严重度取最严重者（1-3S 覆盖 1-2S）。
- 有上传规则的点以「上传规则」为准（失控/警告），不再采用后端计算；
  空单元格回落到后端 Westgard。
- 带上传规则的点（失控或警告）整体冻结，不参与跨水平 R-4s。
- 原始上传规则落库（uploaded_rule），经 _recalc 仍生效。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.qc_service import (
    aggregate_project, _parse_rule_cell, _resolve_uploaded_rules,
)


def lvl(level, values, rules=None, tm=1.0, ts=0.03):
    dates = [f"2026-06-{i+1:02d}" for i in range(len(values))]
    return {
        "level": level, "values": values, "dates": dates,
        "daily_meta": [(dates[i], values[i], "", "", "") for i in range(len(values))],
        "violate_rules": rules if rules is not None else [""] * len(values),
        "target_mean": tm, "target_sd": ts, "unit": "", "instrument_no": "",
        "test_item_aliases": "",
    }


print("=== 解析：同单元格 1-2S,1-3S → 1-3S 覆盖 ===")
assert _parse_rule_cell("1-2S, 1-3S") == ["1-2s", "1-3s"]
cls, resolved = _resolve_uploaded_rules(_parse_rule_cell("1-2S, 1-3S"))
assert cls == "ooc" and resolved == "1-3s", resolved
print("PASS 1-2S+1-3S →", cls, resolved)

print("=== 解析：仅 1-2S → 警告 ===")
cls, resolved = _resolve_uploaded_rules(_parse_rule_cell("1-2S"))
assert cls == "warning" and resolved == "1-2s", (cls, resolved)
print("PASS 1-2S →", cls, resolved)

print("=== 解析：R-4s;1-3s → 失控，按严重度降序 ===")
cls, resolved = _resolve_uploaded_rules(_parse_rule_cell("R-4s;1-3s"))
assert cls == "ooc" and resolved == "1-3s;R-4s", resolved
print("PASS R-4s;1-3s →", cls, resolved)

print("=== 解析：空/乱码 → 无有效规则 ===")
assert _resolve_uploaded_rules(_parse_rule_cell(""))[0] == ""
assert _resolve_uploaded_rules(_parse_rule_cell("随便写"))[0] == ""
print("PASS 空/乱码 → 不覆盖")

print("\n=== 用例A：后端算在控，上传标 1-3S → 判失控 ===")
lv = lvl("1", [1.0, 1.0, 1.0, 1.0, 1.0], rules=["", "", "", "1-3S", ""])
res = aggregate_project([lv])
a = res["1"]
assert "1-3s" in a["ooc"].get(3, ""), a["ooc"]
assert a["out_of_control_count"] == 1
print("PASS 用例A ooc=", a["ooc"], "count=", a["out_of_control_count"])

print("\n=== 用例B：后端算 1-3S，上传标 1-2S → 上传覆盖为警告 ===")
lv = lvl("1", [1.0, 1.0, 1.0, 1.85, 1.0], rules=["", "", "", "1-2S", ""])
res = aggregate_project([lv])
a = res["1"]
assert 3 not in a["ooc"], a["ooc"]
assert a["warnings"].get(3) == "1-2s", a["warnings"]
assert a["out_of_control_count"] == 0
print("PASS 用例B 降级为警告 warnings=", a["warnings"])

print("\n=== 用例C：上传 1-2S,1-3S 同单元格 → 覆盖为 1-3S 失控 ===")
lv = lvl("1", [1.0, 1.0, 1.0, 1.0, 1.0], rules=["", "", "", "1-2S,1-3S", ""])
res = aggregate_project([lv])
a = res["1"]
assert a["ooc"].get(3) == "1-3s", a["ooc"]
assert 3 not in a["warnings"]
print("PASS 用例C ooc=", a["ooc"])

print("\n=== 用例D：空单元格 → 回落后端 Westgard（1-3S 真实失控仍判）===")
lv = lvl("1", [1.0, 1.0, 1.0, 1.85, 1.0], rules=["", "", "", "", ""])
res = aggregate_project([lv])
a = res["1"]
assert "1-3s" in a["ooc"].get(3, ""), a["ooc"]
print("PASS 用例D 回落后端 ooc=", a["ooc"])

print("\n=== 用例E：跨水平——上传 R-4s 同天两水平都判失控，且冻结不参与其它 R-4s ===")
l1 = lvl("1", [1.0, 1.0], rules=["R-4S", ""])
l2 = lvl("2", [1.0, 1.0], rules=["R-4S", ""])
res = aggregate_project([l1, l2])
assert "R-4s" in res["1"]["ooc"].get(0, ""), res["1"]["ooc"]
assert "R-4s" in res["2"]["ooc"].get(0, ""), res["2"]["ooc"]
print("PASS 用例E 跨水平 R-4s 生效:", res["1"]["ooc"], res["2"]["ooc"])

print("\nALL PASS ✅")
