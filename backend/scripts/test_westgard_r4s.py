"""验证 Westgard 规则：
- 单水平：1-3s / 2-2s / 10-x（失控），1-2s（警告，不计入失控）；警告仅由 1-2s 产生。
- 跨水平 R-4s（2026-07-24 新规则，2026-07-22 修订同天判定，2026-07-25 修订为 SD
  归一化 + 冻结）：把同一项目全部水平的每日测值按 (date, level) 排成一条时间线，
  任意『相邻两点』（同天不同水平、或跨天同/不同水平）都判定；每个测值先按各自水平
  靶值归一化为 z=(value-target_mean)/target_sd，再判 |z_前 - z_后| > 4 即触发；
  触发规则：同一天两水平 → 两个都判失控(R-4s)；跨天相邻 → 只标后点(当天)失控
  (R-4s)、前点不标任何 R-4s 标记（警告仅由 1-2s 产生）；
  已失控点冻结：单点规则已判失控(ooc)的点不参与 R-4s 相邻对及后续统计（互不级联）。
  归一化后高低浓度被拉到同一尺度，浓度差（如甲肝 IgM 水平1≠水平2）不再误报。
- aggregate_project 统计量剔除失控点（含 R-4s 失控点）。
- 10-x：已失控点打断连续同侧计数（失控点只留存、不参与后续统计）。
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

print("\n=== 用例4：跨水平 R-4s（同天两水平 z 差大、单点均不失控→两个都判失控）===")
# 6-03 同天 L1=12.5(z=+2.5)、L2=7.5(z=-2.5)，各自 |z|<3 不触发单点规则，但 |Δz|=5>4 → R-4s；
# 两个水平都判失控（同天规则）。12.5/7.5 虽超 ±2SD 会有 1-2s 警告（正常单点警告）。
levels = [
    {"level": "L1", "values": [10, 10, 12.5],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
    {"level": "L2", "values": [10, 10, 7.5],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
]
res = aggregate_project(levels)
print("L1 ooc:", res["L1"]["ooc"], "L1 warn:", res["L1"]["warnings"])
print("L2 ooc:", res["L2"]["ooc"], "L2 warn:", res["L2"]["warnings"])
assert "R-4s" in res["L2"]["ooc"].get(2, ""), "6-03 L2=7.5 应判 R-4s（与同日 L1 跨水平）"
assert "R-4s" in res["L1"]["ooc"].get(2, ""), "6-03 L1=12.5 同天触发也应判 R-4s 失控（两个水平都失控）"
assert "R-4s" not in res["L1"]["warnings"].get(2, ""), "同天前点 L1 不以 R-4s 警告（1-2s 警告属正常单点）"
# 其余相邻对 z 差均 <4，不应触发 R-4s
for lv in ("L1", "L2"):
    for i in (0, 1):
        assert "R-4s" not in res[lv]["ooc"].get(i, ""), f"{lv} idx{i} 不应 R-4s"
print("PASS 用例4：同天跨水平 R-4s（两个水平都失控）")

print("\n=== 用例5：跨水平 R-4s（跨天不同水平相邻）→ 只标后点失控，前点不标 R-4s ===")
# 周一三五各做一个水平：L1 在 d1/d3，L2 在 d2/d4；d3 L1=12.5(z=+2.5) 与 d4 L2=7.5(z=-2.5)
# 跨天相邻，|Δz|=5>4 → R-4s；两值单点均不失控（|z|<3），故只标后点(当天) L2 d4 失控。
levels5 = [
    {"level": "L1", "values": [10, 12.5],
     "dates": ["2026-06-01", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
    {"level": "L2", "values": [10, 7.5],
     "dates": ["2026-06-02", "2026-06-04"],
     "target_mean": 10, "target_sd": 1},
]
res5 = aggregate_project(levels5)
print("L1 ooc:", res5["L1"]["ooc"], "L1 warn:", res5["L1"]["warnings"])
print("L2 ooc:", res5["L2"]["ooc"], "L2 warn:", res5["L2"]["warnings"])
assert "R-4s" in res5["L2"]["ooc"].get(1, ""), "d4 L2=7.5 应判 R-4s（与 d3 L1 跨天相邻，后点失控）"
assert 1 not in res5["L1"]["ooc"], "前点 L1 不应判失控"
assert "R-4s" not in res5["L1"]["warnings"].get(1, ""), "跨天前点 L1 不标任何 R-4s 警告（警告仅 1-2s）"
print("PASS 用例5：跨天相邻不同水平 R-4s（只标后点）")

print("\n=== 用例6：R-4s 已失控点冻结，跨天相邻不牵连后续（不降级/不误判）===")
# 单水平连续三测值 12.5,7.5,10，mean=10,sd=1；z 分别为 +2.5,-2.5,0（单点均不失控，仅超±2SD有1-2s）。
# 相邻跨天 |Δz| 均 >4 → 触发；按冻结：(d1,d2) 跨天→d2 失控并冻结；(d2,d3) 因前点 d2 已冻结跳过，d3 不误判。
# 验证：d2 失控；d1、d3 均不被牵连/误判为失控或 R-4s 警告。
levels6 = [
    {"level": "L1", "values": [12.5, 7.5, 10],
     "dates": ["2026-06-01", "2026-06-02", "2026-06-03"],
     "target_mean": 10, "target_sd": 1},
]
res6 = aggregate_project(levels6)
print("L1 ooc:", res6["L1"]["ooc"], "L1 warn:", res6["L1"]["warnings"])
assert "R-4s" in res6["L1"]["ooc"].get(1, ""), "d2=7.5 应判 R-4s 失控（与 d1 跨天相邻，后点）"
assert "R-4s" not in res6["L1"]["ooc"].get(0, ""), "d1=12.5 在控（跨天相邻前点不判 R-4s）"
assert "R-4s" not in res6["L1"]["ooc"].get(2, ""), "d3=10 在控（因 d2 已冻结，跨天对跳过，不误判）"
assert "R-4s" not in res6["L1"]["warnings"].get(0, ""), "d1 不以 R-4s 警告"
assert "R-4s" not in res6["L1"]["warnings"].get(2, ""), "d3 不以 R-4s 警告"
print("PASS 用例6：R-4s 已失控点冻结，跨天相邻不牵连/不降级")

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
# 该示例下各测值归一化后 z 均很小（差值 3/1/2/1/9 相对各自靶值/SD 归一化后 <<4），不应触发 R-4s
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

print("\n=== 用例9：已失控(同天R-4s)点冻结，跨天相邻对跳过，后点不误判 ===")
# 6-01 同天 L1=12.5(z=+2.5)、L2=7.5(z=-2.5)（单点均不失控）→ 同天 R-4s 两个都失控并冻结；
# 6-02 L1=12.5(z=+2.5) 与 6-01 L2 跨天相邻，但前点 L2(6-01) 已冻结 → 本对跳过，L1(6-02) 不误判。
levels9 = [
    {"level": "L1", "values": [12.5, 10],
     "dates": ["2026-06-01", "2026-06-02"], "target_mean": 10, "target_sd": 1},
    {"level": "L2", "values": [7.5],
     "dates": ["2026-06-01"], "target_mean": 10, "target_sd": 1},
]
res9 = aggregate_project(levels9)
print("L1:", {k: (res9['L1']['ooc'].get(k), res9['L1']['warnings'].get(k)) for k in (0, 1)})
print("L2:", {k: (res9['L2']['ooc'].get(k), res9['L2']['warnings'].get(k)) for k in (0,)})
assert "R-4s" in res9["L1"]["ooc"].get(0, ""), "6-01 L1=12.5 同天 R-4s 应判失控"
assert "R-4s" in res9["L2"]["ooc"].get(0, ""), "6-01 L2=7.5 同天 R-4s 应判失控"
assert "R-4s" not in res9["L1"]["ooc"].get(1, ""), "6-02 L1=12.5 因前点已冻结、跨天对跳过，不应 R-4s 失控"
assert "R-4s" not in res9["L1"]["warnings"].get(1, ""), "6-02 L1 不应以 R-4s 警告"
print("PASS 用例9：同天失控点冻结后，跨天相邻对跳过、后点不误判")

print("\n=== 用例10：甲肝 IgM 跨水平 SD 归一化（浓度差不再误报 R-4s）===")
# 水平1 靶值0.24/SD0.02，值~0.24；水平2 靶值2.40/SD0.20，值~2.4。
# 旧逻辑（原始差）会把 ~2.1 的跨水平差当作 R-4s；归一化后各点 z 均很小（|z|<1），
# 相邻对 |z_前 - z_后| << 4，不应触发 R-4s（真实反映：波动幅度正常）。
levels10 = [
    {"level": "L1", "values": [0.246, 0.246, 0.243, 0.240],
     "dates": ["2026-06-02", "2026-06-09", "2026-06-23", "2026-06-30"],
     "target_mean": 0.24, "target_sd": 0.02},
    {"level": "L2", "values": [2.32, 2.56, 2.44, 2.49],
     "dates": ["2026-06-04", "2026-06-11", "2026-06-18", "2026-06-25"],
     "target_mean": 2.4, "target_sd": 0.2},
]
res10 = aggregate_project(levels10)
print("L1 ooc:", res10["L1"]["ooc"], "L2 ooc:", res10["L2"]["ooc"])
for lv in ("L1", "L2"):
    assert not any("R-4s" in v for v in res10[lv]["ooc"].values()), f"{lv} 不应有 R-4s 失控（甲肝浓度差）"
    assert not any("R-4s" in v for v in res10[lv]["warnings"].values()), f"{lv} 不应有 R-4s 警告"
print("PASS 用例10：甲肝 IgM 跨水平归一化后不误报 R-4s")

print("\n=== 用例11：用户示例 SD 归一化后触发 R-4s（两水平各偏离自己靶值>2SD）===")
# 水平1 靶3/SD1，测5.5 → z=+2.5；水平2 靶10/SD1，测7.5 → z=-2.5；|z1-z2|=5>4 → R-4s。
# 两水平同天相邻 → 两个都判失控。
levels11 = [
    {"level": "L1", "values": [5.5],
     "dates": ["2026-06-01"], "target_mean": 3, "target_sd": 1},
    {"level": "L2", "values": [7.5],
     "dates": ["2026-06-01"], "target_mean": 10, "target_sd": 1},
]
res11 = aggregate_project(levels11)
print("L1 ooc:", res11["L1"]["ooc"], "L2 ooc:", res11["L2"]["ooc"])
assert "R-4s" in res11["L1"]["ooc"].get(0, ""), "L1=5.5(z=+2.5) 归一化应判 R-4s 失控"
assert "R-4s" in res11["L2"]["ooc"].get(0, ""), "L2=7.5(z=-2.5) 归一化应判 R-4s 失控"
print("PASS 用例11：用户示例归一化后 R-4s 正常触发")

print("\n=== 用例12：已失控点冻结（用错质控品导致 1-3s 失控，不应再污染 R-4s 判后点）===")
# 表面抗原情景：水平1 同一天出现 0.441（用错质控品，相对靶值3.83 已 1-3s 失控）
# 与 3.6（接近靶值、在控）同天同水平相邻。按冻结规则：0.441 已 1-3s 失控 → 冻结，
# 不再作为 R-4s 的参与点，3.6 不应被误判 R-4s。
levels12 = [
    {"level": "L1", "values": [0.441, 3.6],
     "dates": ["2026-06-13", "2026-06-13"],
     "target_mean": 3.83, "target_sd": 0.3},
]
res12 = aggregate_project(levels12)
print("L1 ooc:", res12["L1"]["ooc"], "L1 warn:", res12["L1"]["warnings"])
assert "1-3s" in res12["L1"]["ooc"].get(0, ""), "0.441 应判 1-3s 失控（用错质控品，真实失控）"
assert "R-4s" not in res12["L1"]["ooc"].get(1, ""), "3.6 不应因已失控的 0.441 被误判 R-4s 失控"
assert "R-4s" not in res12["L1"]["warnings"].get(1, ""), "3.6 不应以 R-4s 警告"
print("PASS 用例12：已失控(1-3s)点冻结，同天 R-4s 不污染在控点")

print("\n=== 用例13：跨天 R-4s 只标后点(当天)，前点不标任何 R-4s 标记 ===")
# L1 d1=11.9(z=+1.9)、d2=7.1(z=-2.9)，mean=10, sd=1；|Δz|=4.8>4 跨天 → 只标 d2 失控。
# d1 虽超 +2SD 有 1-2s 警告（属正常单点警告），但绝不以 R-4s 标记/警告。
levels13 = [
    {"level": "L1", "values": [11.9, 7.1],
     "dates": ["2026-06-01", "2026-06-02"],
     "target_mean": 10, "target_sd": 1},
]
res13 = aggregate_project(levels13)
print("L1 ooc:", res13["L1"]["ooc"], "L1 warn:", res13["L1"]["warnings"])
assert "R-4s" in res13["L1"]["ooc"].get(1, ""), "d2=7.1 应判 R-4s 失控（后点/当天）"
assert "R-4s" not in res13["L1"]["ooc"].get(0, ""), "d1 不因 R-4s 失控"
assert "R-4s" not in res13["L1"]["warnings"].get(0, ""), "跨天前点 d1 不标任何 R-4s 标记"
print("PASS 用例13：跨天 R-4s 只标后点，前点无 R-4s 标记")

print("\n=== 用例14：10-x 已失控点冻结（打断连续同侧计数，重组后再统计）===")
# 子1：第0点 1-3s 失控，其后连续10个在控上侧点 → 重组后触发 10-x（点1..10 标记）
ooc14a, warn14a = evaluate_westgard(
    [14, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11], 10, 1)
print("子1 ooc:", ooc14a)
assert 0 in ooc14a and "1-3s" in ooc14a[0], "第0点应 1-3s 失控"
assert all(("10-x" in ooc14a.get(i, "")) for i in range(1, 11)), "失控点之后连续10个上侧应触发 10-x"
# 子2：第0点 1-3s 失控，其后仅9个在控上侧点 → 重组后不足10，不触发 10-x
ooc14b, warn14b = evaluate_westgard(
    [14, 11, 11, 11, 11, 11, 11, 11, 11, 11], 10, 1)
print("子2 ooc:", ooc14b)
assert all(("10-x" not in ooc14b.get(i, "")) for i in range(1, 10)), "重组后不足10个不触发 10-x"
print("PASS 用例14：10-x 已失控点冻结并打断/重组计数")

print("\n全部用例通过 ✅")
