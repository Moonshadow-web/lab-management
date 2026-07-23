"""验证 Westgard 规则：
- 单水平：1-3s / 2-2s / 10-x（失控），1-2s（警告，不计入失控）；
- 跨水平 R-4s（2026-07-24 新规则）：把同一项目全部水平的每日测值按 (date, level)
  排成一条时间线，任意『相邻两点』（同天不同水平、或跨天同/不同水平）都判定；
  |前点 - 后点| > 4×max(前sd, 后sd) 即触发 → 后点判失控(R-4s)、前点判警告(R-4s)；
  互不级联（前点已失控不会因后续 pair 被降级为警告）。
- aggregate_project 统计量剔除失控点（含 R-4s 失控点）。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.qc_service import evaluate_westgard, aggregate_project, _robust_stats


print("=== 用例1：单水平 1-3s 失控判定 ===")
ooc, warn = evaluate_westgard([1.00, 1.02, 0.98, 1.01, 1.85, 0.99, 1.00], 1.0, 0.03)
print("ooc:", ooc, "warn:", warn)
assert 4 in ooc and "1-3s" in ooc[4], "index4 应判 1-3s"
print("PASS 用例1：1-3s")

print("\n=== 用例2：单水平 2-2s 失控判定 ===")
ooc2, warn2 = evaluate_westgard([1.00, 1.08, 1.09, 1.01], 1.0, 0.03)
print("ooc:", ooc2, "warn:", warn2)
assert 1 in ooc2 and 2 in ooc2 and "2-2s" in ooc2[1], "连续两点超 +2SD 应判 2-2s"
assert 1 not in warn2 and 2 not in warn2, "已被 2-2s 判失控的点不应再标 1-2s 警告"
print("PASS 用例2：2-2s")

print("\n=== 用例3：1-2s 警告（孤立超 ±2SD 未超 ±3SD），不计入失控 ===")
# 注意：相邻两点同时超 +2SD 会触发 2-2s（两者均失控），故 1-2s 警告须是孤立点。
# 序列 [1.00, 1.07, 1.00, 1.10, 1.00]：1.07 孤立超+2SD→1-2s 警告；1.10 孤立超+3SD→1-3s 失控。
ooc3, warn3 = evaluate_westgard([1.00, 1.07, 1.00, 1.10, 1.00], 1.0, 0.03)
print("ooc:", ooc3, "warn:", warn3)
assert 1 in warn3 and "1-2s" in warn3[1], "1.07 孤立超+2SD 应标 1-2s 警告"
assert 1 not in ooc3, "1.07 不应判失控"
assert 3 in ooc3 and "1-3s" in ooc3[3], "1.10 孤立超+3SD 应判 1-3s 失控"
assert 3 not in warn3, "1.10 已失控不应再标 1-2s"
for i in (0, 2, 4):
    assert i not in warn3, f"点 {i} 不应警告"
print("PASS 用例3：1-2s 警告（孤立）")

print("\n=== 用例4：跨水平 R-4s（同天两水平差大→后点失控、前点警告）===")
# 6-29 同天 L1=10、L2=60，差 50 > 4×max(1,1)=4 → R-4s；L2(后,按 level 序)=失控，L1(前)=警告
levels = [
    {"level": "L1", "values": [10, 10, 10],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
    {"level": "L2", "values": [10, 10, 60],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
]
res = aggregate_project(levels)
print("L1 ooc:", res["L1"]["ooc"], "L1 warn:", res["L1"]["warnings"])
print("L2 ooc:", res["L2"]["ooc"], "L2 warn:", res["L2"]["warnings"])
assert "R-4s" in res["L2"]["ooc"].get(2, ""), "6-03 L2=60 应判 R-4s（与同日 L1 跨水平，后点失控）"
assert "R-4s" in res["L1"]["warnings"].get(2, ""), "6-03 L1=10 应判 R-4s 警告（前点）"
assert 2 not in res["L1"]["ooc"], "前点 L1 不应判失控（仅警告）"
# 其余相邻对差值均为 0，不应触发 R-4s
for lv in ("L1", "L2"):
    for i in (0, 1):
        assert "R-4s" not in res[lv]["ooc"].get(i, ""), f"{lv} idx{i} 不应 R-4s"
print("PASS 用例4：同天跨水平 R-4s（后点失控/前点警告）")

print("\n=== 用例5：跨水平 R-4s（跨天不同水平相邻）→ 后点失控、前点警告 ===")
# 周一三五各做一个水平：L1 在 d1/d3，L2 在 d2/d4；d3 L1=10 与 d4 L2=60 相邻跨天 → R-4s
levels5 = [
    {"level": "L1", "values": [10, 10],
     "dates": ["2026-06-01", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
    {"level": "L2", "values": [10, 60],
     "dates": ["2026-06-02", "2026-06-04"],
     "target_mean": 10, "target_sd": 1},
]
res5 = aggregate_project(levels5)
print("L1 ooc:", res5["L1"]["ooc"], "L1 warn:", res5["L1"]["warnings"])
print("L2 ooc:", res5["L2"]["ooc"], "L2 warn:", res5["L2"]["warnings"])
assert "R-4s" in res5["L2"]["ooc"].get(1, ""), "d4 L2=60 应判 R-4s（与 d3 L1 跨天相邻，后点失控）"
assert "R-4s" in res5["L1"]["warnings"].get(1, ""), "d3 L1=10 应判 R-4s 警告（前点）"
assert 1 not in res5["L1"]["ooc"], "前点 L1 不应判失控"
print("PASS 用例5：跨天相邻不同水平 R-4s")

print("\n=== 用例6：R-4s 不级联/不降级（连续大跳：前点已失控保持失控）===")
# 单水平连续三测值 10,60,10，sd=1；相邻差均 50>4 → 触发两次 R-4s
# d2 作为「前点」时已是失控，后续作为 pair 前点不应被降级为警告
levels6 = [
    {"level": "L1", "values": [10, 60, 10],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
]
res6 = aggregate_project(levels6)
print("L1 ooc:", res6["L1"]["ooc"], "L1 warn:", res6["L1"]["warnings"])
assert "R-4s" in res6["L1"]["ooc"].get(1, ""), "d2=60 应判 R-4s 失控"
assert "R-4s" in res6["L1"]["ooc"].get(2, ""), "d3=10 应判 R-4s 失控（与 d2 相邻）"
assert "R-4s" in res6["L1"]["warnings"].get(0, ""), "d1=10 应判 R-4s 警告（作为 d2 的前点）"
assert 2 not in res6["L1"]["warnings"], "d3 已失控，不应再被标为警告"
print("PASS 用例6：R-4s 不级联/不降级")

print("\n=== 用例7：用户 6 月 1-3 日示例（验证所有相邻对都被计算，且未达阈值的不误判）===")
# 6/1 L1=5, L2=8；6/2 L1=6, L2=8；6/3 L2=9, L3=18。SD 取较大值使这些差值不触发 R-4s（仅验证配对逻辑）。
levels7 = [
    {"level": "L1", "values": [5, 6],
     "dates": ["2026-06-01", "2026-06-02"], "target_mean": 5, "target_sd": 5},
    {"level": "L2", "values": [8, 8, 9],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"], "target_mean": 8, "target_sd": 5},
    {"level": "L3", "values": [18],
     "dates": ["2026-06-03"], "target_mean": 18, "target_sd": 5},
]
res7 = aggregate_project(levels7)
print("L1:", {k: (res7['L1']['ooc'].get(k), res7['L1']['warnings'].get(k)) for k in (0, 1)})
print("L2:", {k: (res7['L2']['ooc'].get(k), res7['L2']['warnings'].get(k)) for k in (0, 1, 2)})
print("L3:", {k: (res7['L3']['ooc'].get(k), res7['L3']['warnings'].get(k)) for k in (0,)})
# 该示例下所有相邻差（3/1/2/1/9）均 <= 4×max(5,5)=20，不应触发 R-4s
for lv in ("L1", "L2", "L3"):
    assert not any("R-4s" in v for v in res7[lv]["ooc"].values()), f"{lv} 不应有 R-4s 失控"
    assert not any("R-4s" in v for v in res7[lv]["warnings"].values()), f"{lv} 不应有 R-4s 警告"
print("PASS 用例7：6月1-3日示例配对逻辑正确（未达阈值不误判）")

print("\n=== 用例8：aggregate_project 剔除失控点重算统计量（含 R-4s 失控点）===")
levels8 = [
    {"level": "L1", "values": [0.98, 1.02, 1.00, 0.97, 1.80, 1.03, 0.99],
     "dates": [f"2026-06-{i:02d}" for i in range(1, 8)],
     "target_mean": 0.0, "target_sd": 0.0},  # 无靶值 → 稳健估计
]
res8 = aggregate_project(levels8)
print("L1 ooc:", res8["L1"]["ooc"], "失控数:", res8["L1"]["out_of_control_count"])
print(f"剔除后 mean={res8['L1']['mean']:.4f} sd={res8['L1']['sd']:.4f} cv={res8['L1']['cv']:.2f}%")
assert res8["L1"]["out_of_control_count"] >= 1, "应检出至少 1 个失控点"
print("PASS 用例8：失控点被检出并剔除重算")

print("\n全部用例通过 ✅")
