"""本地验证 interlab_report 多平台逻辑（无需 DB）。构造 mock plan/items/levels 调用 compute_data + build_docx + build_html。"""
import sys, types
sys.path.insert(0, "backend")
from app.services import interlab_report as svc


def mk_plan(**kw):
    d = dict(id=2, year=2026, half=1, instrument_id=73, reference_lab="安贞医院(通州院区)",
             compared_instrument2="DxI800-线上3号机", compared_at="2026-06-22",
             operator="金子铮", reviewer="杨静",
             summary="使用5例样本与安贞医院进行室间比对，一致性可接受。",
             handle_plan="无", conclusion="可接受")
    d.update(kw)
    return types.SimpleNamespace(**d)


def mk_level(item_id, n, our, ref1, ref2=""):
    return types.SimpleNamespace(item_id=item_id, level_num=n, our_value=our,
                                 ref1_y1=ref1, ref1_y2="", ref1_mean=ref1,
                                 ref2_y1=ref2, ref2_y2="", ref2_mean=ref2)


def mk_item(iid, item, kind, te="30", mode="relative"):
    return types.SimpleNamespace(id=iid, item=item, unit="", te=te, mode=mode, kind=kind, note="")


# IFAb 定性（有比较系统2）
ifab = mk_item(1, "IFAb", "定性", te="0")
ifab_levels = [
    mk_level(1, n, s1, ref, s2) for n, ref, s1, s2 in [
        (1, "阳性(6.78)", "阳性(6.42)", "阳性(5.82)"),
        (2, "阴性(1.05)", "阴性(1.09)", "阴性(1.00)"),
        (3, "阴性(1.10)", "阴性(1.08)", "阴性(1.14)"),
        (4, "阴性(1.11)", "阴性(1.13)", "阴性(1.11)"),
        (5, "阴性(1.14)", "阴性(1.08)", "阴性(1.02)"),
    ]
]
# EPO 定量（无比较系统2）
epo = mk_item(2, "EPO", "定量", te="30")
epo_levels = [
    mk_level(2, n, s1, ref) for n, ref, s1 in [
        (1, "174.51", "194.02"),
        (2, "41.62", "46.50"),
        (3, "293.9", "312.07"),
        (4, "75.08", "77.23"),
        (5, "27.36", "28.22"),
    ]
]
# p2PSA 定量（无比较系统2）
p2 = mk_item(3, "p2PSA", "定量", te="30")
p2_levels = [
    mk_level(3, n, s1, ref) for n, ref, s1 in [
        (1, "18.73", "18.74"),
        (2, "13.12", "15.05"),
        (3, "13.21", "12.53"),
        (4, "6.26", "5.84"),
        (5, "2.03", "1.72"),
    ]
]

items = [ifab, epo, p2]
levels_map = {1: ifab_levels, 2: epo_levels, 3: p2_levels}
plan = mk_plan()

data = svc.compute_data(None, plan, items, levels_map)
print("has_qual=", data["has_qual"], "has_quan=", data["has_quan"], "all_ok=", data["all_ok"])
for p in data["projects"]:
    print(f"  {p['item']} kind={p['kind']} has2={p['has2']} levels={len(p['levels'])}")
    for lv in p["levels"][:1]:
        print("    sample level keys:", sorted(lv.keys()))

# 生成 docx
out = "./test_interlab_report.docx"
svc.build_docx(None, plan, data, out, "贝克曼DXI800 急", plan.reference_lab)
print("DOCX written:", out)

# 生成 html
html = svc.build_html(plan, data, "贝克曼DXI800 急", plan.reference_lab)
print("HTML length:", len(html))
assert "比较系统2" in html, "HTML 应含 比较系统2"
assert "DxI800-线上3号机" in html, "HTML 应含比较系统2机器名"
print("OK: HTML 含双比较系统与机器名")
