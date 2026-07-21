"""验证 #5：R-4s 不应由已失控点级联；aggregate 须剔除失控点重算 mean/sd/cv。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.qc_service import evaluate_westgard, aggregate, _robust_stats

print("=== 用例1：中间点 1-3s 失控，其前后点不应被 R-4s 牵连 ===")
# 10 个测值，第 5 个点明显偏离（1-3s），其余围绕均值 1.0
vals = [1.00, 1.02, 0.98, 1.01, 1.85, 0.99, 1.00, 1.03, 0.97, 1.01]
mean, sd = 1.0, 0.03
ooc = evaluate_westgard(vals, mean, sd)
print("失控点:", {i: r for i, r in ooc.items()})
# 期望：index4 因 1-3s 失控；index3 与 index4 差值大但 index4 已失控→index3 不应出现 R-4s
# index4 与 index5 差值也大，但 index4 已失控→index5 不应出现 R-4s
assert 4 in ooc and "1-3s" in ooc[4], "index4 应判 1-3s"
assert 3 not in ooc, f"index3 不应失控（不应被 R-4s 牵连），实际={ooc.get(3)}"
assert 5 not in ooc, f"index5 不应失控（不应被 R-4s 牵连），实际={ooc.get(5)}"
print("PASS 用例1：R-4s 未级联相邻点")

print("\n=== 用例2：真实 R-4s（两个相邻在控点差值>4sd）仍应判 ===")
# mean=1.0, sd=0.03 → 3sd∈[0.91,1.09]，4sd=0.12。index5=1.085、index6=0.96 均在 3sd 内，
# 但二者差值=0.125 > 0.12 → 真实 R-4s（且二者都未先失控，故应判）。
vals2 = [1.00, 1.01, 0.99, 1.02, 1.04, 1.085, 0.96, 1.00, 0.98, 1.02]
ooc2 = evaluate_westgard(vals2, 1.0, 0.03)
assert 5 in ooc2 and "R-4s" in ooc2[5], f"index5 应判 R-4s，实际={ooc2.get(5)}"
assert 6 in ooc2 and "R-4s" in ooc2[6], f"index6 应判 R-4s，实际={ooc2.get(6)}"
print("PASS 用例2：真实相邻 R-4s 仍正确判定")

print("\n=== 用例3：aggregate 须剔除失控点重算 mean/sd/cv（无靶值也要能检出）===")
# 601 HBsAg 水平1 模拟：靶值≈1.0，多数点 0.9~1.1，一个失控点 1.8
series = [0.98, 1.02, 1.00, 0.97, 1.80, 1.03, 0.99, 1.01, 0.96, 1.02]
agg = aggregate(series, 0.0, 0.0)  # 无靶值 → 走 _robust_stats
print("失控点:", agg["ooc"], "失控数:", agg["out_of_control_count"])
print(f"剔除后 mean={agg['mean']:.4f} sd={agg['sd']:.4f} cv={agg['cv']:.2f}%")
print(f"全量   mean={agg['all_mean']:.4f} sd={agg['all_sd']:.4f} cv={agg['all_cv']:.2f}%")
assert agg["out_of_control_count"] >= 1, "应检出至少 1 个失控点"
assert abs(agg["mean"] - 1.0) < 0.05, f"剔除后均值应≈1.0，实际={agg['mean']}"
assert agg["sd"] < 0.06, f"剔除后 SD 应明显小于全量，实际={agg['sd']}"
print("PASS 用例3：失控点被检出并剔除重算")

print("\n全部用例通过 ✅")
